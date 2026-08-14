#!/usr/bin/env python3
"""Validate a portable, domain-sliced product requirement package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

PACKAGE_DIR = Path("docs/产品需求")
MANIFEST_NAME = "需求包清单.yaml"
PRD_NAME = "PRD需求文档.md"
BEHAVIOR_INDEX = Path("行为样例/产品行为样例集.yaml")

ROOT_HEADINGS = (
    "## 产品定位与范围",
    "## 产品现状与目标",
    "## 功能域地图",
    "## 跨域用户旅程",
    "## 全局输入与输出约定",
)
DOMAIN_HEADINGS = (
    "## 功能域范围",
    "## 用户能力与旅程",
    "## 功能详细设计",
)
FEATURE_HEADINGS = (
    "#### 作用与目标",
    "#### 适用角色、入口与前置条件",
    "#### 用户输入契约",
    "#### 输出契约",
    "#### 设计依据",
    "#### 行为样例",
    "#### 验收标准",
)
INPUT_COLUMNS = (
    "输入项",
    "提供者",
    "必填",
    "格式与范围",
    "示例",
)
OUTPUT_COLUMNS = (
    "输出内容",
    "呈现形式",
    "触发条件",
    "语义要求",
    "完整示例",
)
COPY_COLUMNS = ("状态", "触发条件", "最终文案", "后续动作")

FEATURE_RE = re.compile(r"(?m)^###\s+(F-\d{3})\s+(.+?)\s*$")
AC_RE = re.compile(r"`(F-\d{3}-AC-\d{2})`")
SAMPLE_REF_RE = re.compile(r"`([A-Z][A-Z0-9-]*SAMPLE[A-Z0-9-]*|SAMPLE-[A-Z0-9-]+)`")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
PACKAGE_ID_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
URL_RE = re.compile(r"https://[^\s|]+")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")

UNRESOLVED_RE = re.compile(
    r"\b(?:TODO|TBD|TBC|FIXME)\b"
    r"|待确认|待定|开放问题|未决项|阻塞项|未知项|假设[：:\s]"
)
PLACEHOLDER_RE = re.compile(r"\{\{[^}\n]+\}\}|\[\s*(?:待填写|填写)\s*\]")
INTERNAL_IMPLEMENTATION_HEADING_RE = re.compile(
    r"(?m)^#{1,6}\s*(?:内部技术架构|内部系统架构|内部技术栈|内部技术选型|"
    r"数据库实现|内部数据模型|代码结构|内部模块设计|工程任务|实现步骤|部署实现)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    line: Optional[int] = None


@dataclass
class Report:
    path: str
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return self.issues

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "status": "pass" if not self.errors else "fail",
            "error_count": len(self.errors),
            "issues": [asdict(issue) for issue in self.issues],
        }


@dataclass(frozen=True)
class DomainContract:
    domain_id: str
    name: str
    requirements: Path
    examples: Path
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class PackageSnapshot:
    root: Path
    manifest: dict[str, Any]
    files: dict[str, str]
    domains: tuple[DomainContract, ...]


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def add_issue(
    issues: list[Issue],
    code: str,
    message: str,
    *,
    text: Optional[str] = None,
    offset: Optional[int] = None,
) -> None:
    line = line_number(text, offset) if text is not None and offset is not None else None
    issues.append(Issue(code=code, message=message, line=line))


def _display(package: Path, path: Path) -> str:
    try:
        return path.relative_to(package).as_posix()
    except ValueError:
        return str(path)


def _is_legacy_prd(path: Path) -> bool:
    return path.name == PRD_NAME and path.parent.name == "docs"


def resolve_package_root(target: Path) -> tuple[Path, list[Issue]]:
    expanded = target.expanduser()
    issues: list[Issue] = []

    def reject_link(path: Path) -> tuple[Path, list[Issue]]:
        add_issue(issues, "NON_REGULAR_FILE", "docs/产品需求/ 必须是目标项目内的真实目录，不能是符号链接。")
        return path.absolute(), issues

    if _is_legacy_prd(expanded):
        add_issue(issues, "LEGACY_OUTPUT_PATH", "旧路径 docs/PRD需求文档.md 已停用；请迁移到 docs/产品需求/。")
        return expanded.resolve(strict=False), issues
    if expanded.name == PRD_NAME and expanded.parent.name == "产品需求":
        if expanded.parent.is_symlink():
            return reject_link(expanded.parent)
        return expanded.parent.resolve(strict=False), issues
    if expanded.name == "产品需求":
        if expanded.is_symlink():
            return reject_link(expanded)
        return expanded.resolve(strict=False), issues
    candidate = expanded / PACKAGE_DIR
    if candidate.is_symlink() or candidate.parent.is_symlink():
        return reject_link(candidate)
    if candidate.is_dir() or (expanded.is_dir() and (expanded / "docs").exists()):
        return candidate.resolve(strict=False), issues
    add_issue(issues, "OUTPUT_PATH", "目标必须是项目根目录、docs/产品需求/，或其中的 PRD需求文档.md。")
    return expanded.resolve(strict=False), issues


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_yaml(path: Path, package: Path, issues: list[Issue], *, code: str) -> Optional[dict[str, Any]]:
    """Read the dependency-free JSON representation accepted by YAML 1.2."""
    if path.is_symlink() or not path.is_file():
        add_issue(
            issues,
            "NON_REGULAR_FILE" if path.exists() or path.is_symlink() else "FILE_REQUIRED",
            f"{_display(package, path)} 必须是包内普通文件，不能是软链接。",
        )
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        add_issue(issues, code, f"{_display(package, path)} 必须使用 YAML 1.2 兼容的 JSON 对象格式：{exc}")
        return None
    if not isinstance(value, dict):
        add_issue(issues, code, f"{_display(package, path)} 顶层必须是对象。")
        return None
    return value


def _safe_relative(raw: Any) -> Optional[Path]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or path == Path("."):
        return None
    return path


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_nonempty_string(x) for x in value)


def _source_is_portable(value: str) -> bool:
    return not Path(value).is_absolute() and WINDOWS_ABSOLUTE_RE.match(value) is None


def _validate_manifest(
    manifest: dict[str, Any], package: Path, issues: list[Issue]
) -> tuple[list[DomainContract], dict[str, str]]:
    if manifest.get("schema_version") != "1.0":
        add_issue(issues, "SCHEMA_VERSION", "需求包 schema_version 必须为 1.0。")

    package_id = manifest.get("package_id")
    if not isinstance(package_id, str) or PACKAGE_ID_RE.fullmatch(package_id) is None:
        add_issue(issues, "PACKAGE_ID", "package_id 必须是稳定的小写连字符标识。")
    package_version = manifest.get("package_version")
    if not isinstance(package_version, str) or SEMVER_RE.fullmatch(package_version) is None:
        add_issue(issues, "PACKAGE_VERSION", "package_version 必须使用完整 SemVer，例如 0.1.0、1.2.3-rc.1 或 1.2.3+build.5。")
    if manifest.get("status") != "confirmed":
        add_issue(issues, "PACKAGE_STATUS", "只有 status=confirmed 的需求包可以实施。")

    package_type = manifest.get("package_type")
    if package_type not in {"full", "stage"}:
        add_issue(issues, "PACKAGE_TYPE", "package_type 必须是 full 或 stage。")
    generated_at = manifest.get("generated_at")
    try:
        if not isinstance(generated_at, str):
            raise ValueError
        date.fromisoformat(generated_at)
    except ValueError:
        add_issue(issues, "GENERATED_AT", "generated_at 必须是 YYYY-MM-DD 日期。")

    source = manifest.get("source")
    if not isinstance(source, dict) or not all(_nonempty_string(source.get(key)) for key in ("project", "revision")):
        add_issue(issues, "SOURCE", "source 必须记录 project 和 revision。")
    elif not _source_is_portable(str(source["project"])):
        add_issue(issues, "SOURCE_PORTABILITY", "source.project 必须使用仓库标识、仓库 URL 或产品想法标识，不能保存宿主机绝对路径。")

    domains_raw = manifest.get("domains")
    if not isinstance(domains_raw, list) or not domains_raw:
        add_issue(issues, "DOMAINS_REQUIRED", "需求包至少需要一个已确认功能域。")
        domains_raw = []

    domains: list[DomainContract] = []
    domain_ids: set[str] = set()
    for index, raw in enumerate(domains_raw):
        if not isinstance(raw, dict):
            add_issue(issues, "DOMAIN_ENTRY", f"domains[{index}] 必须是对象。")
            continue
        domain_id = raw.get("id")
        name = raw.get("name")
        requirements = _safe_relative(raw.get("requirements"))
        examples = _safe_relative(raw.get("examples"))
        dependencies = raw.get("dependencies")
        if not isinstance(domain_id, str) or PACKAGE_ID_RE.fullmatch(domain_id) is None:
            add_issue(issues, "DOMAIN_ID", f"domains[{index}].id 格式无效。")
            continue
        if domain_id in domain_ids:
            add_issue(issues, "DOMAIN_ID_DUPLICATE", f"功能域 ID 重复：{domain_id}。")
            continue
        domain_ids.add(domain_id)
        if not _nonempty_string(name):
            add_issue(issues, "DOMAIN_NAME", f"{domain_id} 缺少名称。")
            name = domain_id
        if raw.get("status") != "confirmed":
            add_issue(issues, "DOMAIN_STATUS", f"{domain_id} 尚未标记为 confirmed。")
        if requirements is None or requirements.parts[:1] != ("功能域",) or requirements.suffix != ".md":
            add_issue(issues, "DOMAIN_REQUIREMENTS_PATH", f"{domain_id} 的需求文件必须位于 功能域/*.md。")
            continue
        if examples is None or examples.parts[:1] != ("行为样例",) or examples.suffix != ".yaml":
            add_issue(issues, "DOMAIN_EXAMPLES_PATH", f"{domain_id} 的样例文件必须位于 行为样例/*.yaml。")
            continue
        if requirements.stem != str(name) or examples.stem != str(name):
            add_issue(issues, "DOMAIN_FILE_NAME", f"{domain_id} 的需求与行为样例文件名必须都与功能域名称 {name!r} 一致。")
        if not isinstance(dependencies, list) or not all(isinstance(x, str) for x in dependencies):
            add_issue(issues, "DOMAIN_DEPENDENCY", f"{domain_id}.dependencies 必须是字符串数组。")
            dependencies = []
        if domain_id in dependencies:
            add_issue(issues, "DOMAIN_DEPENDENCY", f"{domain_id} 不能依赖自身。")
        domains.append(DomainContract(domain_id, str(name), requirements, examples, tuple(str(x) for x in dependencies)))

    external_raw = manifest.get("external_dependencies", [])
    external: dict[str, str] = {}
    if not isinstance(external_raw, list):
        add_issue(issues, "EXTERNAL_DEPENDENCY", "external_dependencies 必须是数组。")
        external_raw = []
    for raw in external_raw:
        if not isinstance(raw, dict) or not _nonempty_string(raw.get("id")) or not _nonempty_string(raw.get("contract")):
            add_issue(issues, "EXTERNAL_DEPENDENCY", "外部依赖必须包含 id 和完整 contract。")
            continue
        external[str(raw["id"])] = str(raw["contract"])

    if package_type == "full" and external:
        add_issue(issues, "DOMAIN_DEPENDENCY", "完整需求包不能把功能域依赖留在包外。")
    if package_type == "stage":
        stage = manifest.get("stage")
        required = ("included_scope", "deferred_scope", "acceptance")
        if not isinstance(stage, dict) or not all(_nonempty_string(stage.get(key)) for key in required):
            add_issue(issues, "STAGE_CONTRACT", "阶段需求包必须明确 included_scope、deferred_scope 和 acceptance。")

    for domain in domains:
        for dependency in domain.dependencies:
            if dependency not in domain_ids and dependency not in external:
                add_issue(issues, "DOMAIN_DEPENDENCY", f"{domain.domain_id} 的依赖 {dependency} 既不在包内，也没有外部契约。")

    graph = {item.domain_id: [x for x in item.dependencies if x in domain_ids] for item in domains}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in graph.get(node, [])):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    if any(visit(node) for node in graph if node not in visited):
        add_issue(issues, "DOMAIN_DEPENDENCY_CYCLE", "功能域依赖不能形成环。")

    files_raw = manifest.get("files")
    if not isinstance(files_raw, list) or not files_raw:
        add_issue(issues, "FILES_REQUIRED", "需求包清单必须声明所有内容文件及 SHA-256。")
        files_raw = []
    declared: dict[str, str] = {}
    for raw in files_raw:
        if not isinstance(raw, dict):
            add_issue(issues, "FILE_ENTRY", "files 中的每项必须是对象。")
            continue
        relative = _safe_relative(raw.get("path"))
        digest = raw.get("sha256")
        if relative is None:
            add_issue(issues, "FILE_PATH", f"不安全的需求包路径：{raw.get('path')!r}。")
            continue
        name = relative.as_posix()
        if name in declared:
            add_issue(issues, "FILE_PATH_DUPLICATE", f"重复声明文件：{name}。")
            continue
        if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
            add_issue(issues, "FILE_HASH", f"{name} 缺少有效 SHA-256。")
            continue
        declared[name] = digest

    required_paths = {PRD_NAME, BEHAVIOR_INDEX.as_posix()}
    required_paths.update(item.requirements.as_posix() for item in domains)
    required_paths.update(item.examples.as_posix() for item in domains)
    for missing in sorted(required_paths - set(declared)):
        add_issue(issues, "FILE_NOT_DECLARED", f"需求包清单未声明必需文件：{missing}。")
    return domains, declared


def _walk_package_files(package: Path, issues: list[Issue]) -> set[str]:
    actual: set[str] = set()
    if not package.is_dir():
        add_issue(issues, "FILE_REQUIRED", f"找不到需求包目录：{package}")
        return actual
    for directory, dirs, files in os.walk(package, followlinks=False):
        base = Path(directory)
        for name in list(dirs):
            path = base / name
            if path.is_symlink():
                add_issue(issues, "NON_REGULAR_FILE", f"{_display(package, path)} 不能是软链接目录。")
                dirs.remove(name)
        for name in files:
            path = base / name
            relative = _display(package, path)
            if path.is_symlink() or not path.is_file():
                add_issue(issues, "NON_REGULAR_FILE", f"{relative} 必须是普通文件，不能是软链接。")
                continue
            if relative != MANIFEST_NAME:
                actual.add(relative)
    return actual


def _validate_declared_files(package: Path, declared: dict[str, str], actual: set[str], issues: list[Issue]) -> None:
    for extra in sorted(actual - set(declared)):
        add_issue(issues, "UNDECLARED_FILE", f"需求包存在未声明文件：{extra}。")
    for missing in sorted(set(declared) - actual):
        path = package / missing
        code = "NON_REGULAR_FILE" if path.is_symlink() else "FILE_REQUIRED"
        add_issue(issues, code, f"清单中的文件缺失或不是普通文件：{missing}。")
    for relative in sorted(actual & set(declared)):
        path = package / relative
        try:
            digest = sha256_file(path)
        except OSError as exc:
            add_issue(issues, "FILE_READ", f"无法读取 {relative}：{exc}")
            continue
        if digest != declared[relative]:
            add_issue(issues, "FILE_HASH", f"{relative} 与需求包清单中的 SHA-256 不一致。")


def _read_markdown(path: Path, package: Path, issues: list[Issue]) -> Optional[str]:
    if path.is_symlink() or not path.is_file():
        add_issue(issues, "NON_REGULAR_FILE", f"{_display(package, path)} 必须是包内普通文件。")
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        add_issue(issues, "FILE_READ", f"无法读取 {_display(package, path)}：{exc}")
        return None
    if not text.strip():
        add_issue(issues, "FILE_EMPTY", f"{_display(package, path)} 不能为空。")
        return None
    return text


def _validate_heading_order(text: str, headings: Iterable[str], label: str, issues: list[Issue]) -> None:
    positions: list[int] = []
    headings_tuple = tuple(headings)
    for heading in headings_tuple:
        matches = list(re.finditer(rf"(?m)^{re.escape(heading)}\s*$", text))
        if not matches:
            add_issue(issues, "HEADING_REQUIRED", f"{label} 缺少章节：{heading}")
            continue
        if len(matches) > 1:
            add_issue(issues, "HEADING_DUPLICATE", f"{label} 重复章节：{heading}")
        positions.append(matches[0].start())
    if len(positions) == len(headings_tuple) and positions != sorted(positions):
        add_issue(issues, "HEADING_ORDER", f"{label} 的核心章节顺序不正确。")


def _validate_prohibited(text: str, label: str, issues: list[Issue]) -> None:
    for match in UNRESOLVED_RE.finditer(text):
        add_issue(issues, "UNRESOLVED_CONTENT", f"{label} 发现未确定内容：{match.group(0)!r}。", text=text, offset=match.start())
    for match in PLACEHOLDER_RE.finditer(text):
        add_issue(issues, "PLACEHOLDER_CONTENT", f"{label} 存在模板占位内容。", text=text, offset=match.start())
    for match in INTERNAL_IMPLEMENTATION_HEADING_RE.finditer(text):
        add_issue(issues, "INTERNAL_IMPLEMENTATION_SECTION", f"{label} 不得包含内部实现章节：{match.group(0).strip()}。", text=text, offset=match.start())


def _has_columns(section: str, columns: Iterable[str]) -> bool:
    return any(line.lstrip().startswith("|") and all(column in line for column in columns) for line in section.splitlines())


def _subsection(section: str, heading: str) -> str:
    match = re.search(rf"(?m)^{re.escape(heading)}\s*$", section)
    if match is None:
        return ""
    tail = section[match.end() :]
    next_heading = re.search(r"(?m)^####\s+", tail)
    return tail[: next_heading.start()] if next_heading else tail


def _validate_root_prd(text: str, manifest: dict[str, Any], package: Path, issues: list[Issue]) -> None:
    label = PRD_NAME
    if len(re.findall(r"(?m)^# PRD需求文档\s*$", text)) != 1:
        add_issue(issues, "TITLE", "PRD需求文档.md 必须有唯一主标题。")
    if not re.search(r"(?m)^- 文档状态：已确认\s*$", text):
        add_issue(issues, "DOCUMENT_STATUS", "PRD 总入口必须标记为已确认。")
    metadata = {
        "需求包 ID": manifest.get("package_id"),
        "需求包版本": manifest.get("package_version"),
        "需求包类型": "完整" if manifest.get("package_type") == "full" else "阶段",
    }
    for key, expected in metadata.items():
        if not isinstance(expected, str) or not re.search(rf"(?m)^- {re.escape(key)}：{re.escape(expected)}\s*$", text):
            add_issue(issues, "PACKAGE_METADATA", f"PRD 总入口的 {key} 与清单不一致。")
    _validate_heading_order(text, ROOT_HEADINGS, label, issues)
    _validate_prohibited(text, label, issues)
    _validate_research(text, issues)


def _feature_sections(text: str) -> list[tuple[re.Match[str], str]]:
    matches = list(FEATURE_RE.finditer(text))
    sections: list[tuple[re.Match[str], str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match, text[match.start() : end]))
    return sections


def _validate_domain_markdown(
    text: str,
    domain: DomainContract,
    global_features: set[str],
    global_acceptance: set[str],
    issues: list[Issue],
) -> tuple[set[str], dict[str, set[str]]]:
    label = domain.requirements.as_posix()
    if len(re.findall(rf"(?m)^# 功能域：{re.escape(domain.name)}\s*$", text)) != 1:
        add_issue(issues, "DOMAIN_TITLE", f"{label} 的主标题必须与功能域名称一致。")
    if not re.search(r"(?m)^- 文档状态：已确认\s*$", text):
        add_issue(issues, "DOMAIN_STATUS", f"{label} 必须标记为已确认。")
    if not re.search(rf"(?m)^- 功能域 ID：{re.escape(domain.domain_id)}\s*$", text):
        add_issue(issues, "DOMAIN_METADATA", f"{label} 的功能域 ID 与清单不一致。")
    _validate_heading_order(text, DOMAIN_HEADINGS, label, issues)
    _validate_prohibited(text, label, issues)

    sections = _feature_sections(text)
    if not sections:
        add_issue(issues, "FEATURE_REQUIRED", f"{label} 至少需要一项 F-NNN 功能。")
        return set(), {}
    local_features: set[str] = set()
    refs_by_feature: dict[str, set[str]] = {}
    for match, section in sections:
        feature_id = match.group(1)
        if feature_id in global_features or feature_id in local_features:
            add_issue(issues, "FEATURE_ID_DUPLICATE", f"功能编号重复：{feature_id}。")
        local_features.add(feature_id)
        for heading in FEATURE_HEADINGS:
            if not re.search(rf"(?m)^{re.escape(heading)}\s*$", section):
                add_issue(issues, "FEATURE_SECTION_REQUIRED", f"{feature_id} 缺少子章节：{heading}。")
        input_section = _subsection(section, "#### 用户输入契约")
        if input_section and not _has_columns(input_section, INPUT_COLUMNS):
            add_issue(issues, "INPUT_TABLE", f"{feature_id} 的用户输入契约表格缺少规定列。")
        copy_section = _subsection(section, "#### 状态与提示文案")
        if copy_section and not _has_columns(copy_section, COPY_COLUMNS):
            add_issue(issues, "COPY_TABLE", f"{feature_id} 的状态与提示文案表格缺少规定列。")
        output_section = _subsection(section, "#### 输出契约")
        if output_section and not _has_columns(output_section, OUTPUT_COLUMNS):
            add_issue(issues, "OUTPUT_TABLE", f"{feature_id} 的输出契约表格缺少规定列。")

        acceptance = list(AC_RE.finditer(_subsection(section, "#### 验收标准")))
        if not acceptance:
            add_issue(issues, "AC_REQUIRED", f"{feature_id} 至少需要一条关联验收标准。")
        for ac_match in acceptance:
            acceptance_id = ac_match.group(1)
            if not acceptance_id.startswith(f"{feature_id}-AC-"):
                add_issue(issues, "AC_FEATURE_MISMATCH", f"{acceptance_id} 不属于 {feature_id}。")
            if acceptance_id in global_acceptance:
                add_issue(issues, "AC_ID_DUPLICATE", f"验收编号重复：{acceptance_id}。")
            global_acceptance.add(acceptance_id)
            line_start = section.rfind("\n", 0, section.find(acceptance_id)) + 1
            line_end = section.find("\n", line_start)
            line = section[line_start : line_end if line_end >= 0 else len(section)]
            if not all(token in line for token in ("Given", "When", "Then")):
                add_issue(issues, "AC_FORMAT", f"{acceptance_id} 必须包含 Given、When 和 Then。")

        refs = set(SAMPLE_REF_RE.findall(_subsection(section, "#### 行为样例")))
        if not refs:
            add_issue(issues, "SAMPLE_REFERENCE", f"{feature_id} 必须引用行为样例 ID。")
        refs_by_feature[feature_id] = refs
    global_features.update(local_features)
    return local_features, refs_by_feature


def _validate_samples(
    data: dict[str, Any],
    domain: DomainContract,
    features: set[str],
    refs_by_feature: dict[str, set[str]],
    global_sample_ids: set[str],
    issues: list[Issue],
) -> dict[str, set[str]]:
    label = domain.examples.as_posix()
    if data.get("schema_version") != "1.0":
        add_issue(issues, "SAMPLE_SCHEMA", f"{label} 的 schema_version 必须为 1.0。")
    if data.get("domain_id") != domain.domain_id:
        add_issue(issues, "SAMPLE_DOMAIN", f"{label} 的 domain_id 与清单不一致。")
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        add_issue(issues, "SAMPLES_REQUIRED", f"{label} 至少需要一个行为样例。")
        return {}

    kinds_by_feature: dict[str, set[str]] = {feature: set() for feature in features}
    sample_ids_by_feature: dict[str, set[str]] = {feature: set() for feature in features}
    allowed_kinds = {"normal", "clarification", "invalid", "not_applicable", "boundary"}
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            add_issue(issues, "SAMPLE_ENTRY", f"{label}.samples[{index}] 必须是对象。")
            continue
        sample_id = sample.get("id")
        feature_id = sample.get("feature_id")
        kind = sample.get("kind")
        if not _nonempty_string(sample_id):
            add_issue(issues, "SAMPLE_ID", f"{label}.samples[{index}] 缺少 ID。")
            continue
        sample_id = str(sample_id)
        if sample_id in global_sample_ids:
            add_issue(issues, "SAMPLE_ID_DUPLICATE", f"行为样例 ID 重复：{sample_id}。")
        global_sample_ids.add(sample_id)
        if feature_id not in features:
            add_issue(issues, "SAMPLE_FEATURE", f"{sample_id} 指向当前功能域不存在的 {feature_id}。")
            continue
        feature_id = str(feature_id)
        sample_ids_by_feature[feature_id].add(sample_id)
        if kind not in allowed_kinds:
            add_issue(issues, "SAMPLE_KIND", f"{sample_id} 的 kind 无效：{kind!r}。")
        else:
            kinds_by_feature[feature_id].add(str(kind))

        if "user_input" not in sample:
            add_issue(issues, "SAMPLE_FIELD", f"{sample_id} 缺少 user_input；该字段必须保存真实输入值，空字符串或 null 等边界值也应原样保留。")
        if not _nonempty_string(sample.get("expected_output")):
            add_issue(issues, "SAMPLE_FIELD", f"{sample_id} 缺少有效 expected_output。")
        for key, code in (
            ("starting_state", "SAMPLE_STARTING_STATE"),
            ("expected_behavior", "SAMPLE_BEHAVIOR"),
            ("assertions", "SAMPLE_ASSERTIONS"),
        ):
            if not _nonempty_list(sample.get(key)):
                add_issue(issues, code, f"{sample_id} 的 {key} 必须是非空字符串数组。")
        if "forbidden" in sample and sample.get("forbidden") != [] and not _nonempty_list(sample.get("forbidden")):
            add_issue(issues, "SAMPLE_FORBIDDEN", f"{sample_id} 的 forbidden 如存在，必须是字符串数组。")
        output_contract = sample.get("output_contract")
        if not isinstance(output_contract, dict) or not _nonempty_list(output_contract.get("semantic")):
            add_issue(issues, "OUTPUT_CONTRACT", f"{sample_id} 必须声明 semantic 输出约束。")
        elif any(
            key in output_contract
            and output_contract.get(key) != []
            and not _nonempty_list(output_contract.get(key))
            for key in ("exact", "runtime")
        ):
            add_issue(issues, "OUTPUT_CONTRACT", f"{sample_id} 的 exact 和 runtime 如存在，必须是字符串数组。")
        if sample.get("sensitive_data") not in {"none", "sanitized"}:
            add_issue(issues, "SENSITIVE_DATA", f"{sample_id} 必须声明敏感数据为空或已脱敏。")

    for feature in sorted(features):
        kinds = kinds_by_feature.get(feature, set())
        if "normal" not in kinds:
            add_issue(issues, "SAMPLE_KIND_COVERAGE", f"{feature} 缺少 normal 行为样例。")
        referenced = refs_by_feature.get(feature, set())
        actual = sample_ids_by_feature.get(feature, set())
        if referenced != actual:
            add_issue(issues, "SAMPLE_REFERENCE", f"{feature} 的文档引用与样例文件不一致：引用={sorted(referenced)}，实际={sorted(actual)}。")
    return sample_ids_by_feature


def _validate_behavior_index(
    data: dict[str, Any],
    manifest: dict[str, Any],
    domains: list[DomainContract],
    sample_ids: dict[str, set[str]],
    issues: list[Issue],
) -> None:
    if data.get("schema_version") != "1.0":
        add_issue(issues, "BEHAVIOR_INDEX_SCHEMA", "产品行为样例集的 schema_version 必须为 1.0。")
    if data.get("package_id") != manifest.get("package_id"):
        add_issue(issues, "BEHAVIOR_INDEX_PACKAGE", "产品行为样例集的 package_id 与清单不一致。")
    entries = data.get("domains")
    if not isinstance(entries, list):
        add_issue(issues, "BEHAVIOR_INDEX_DOMAINS", "产品行为样例集必须声明 domains 数组。")
        return
    by_id = {entry.get("id"): entry for entry in entries if isinstance(entry, dict)}
    expected_ids = {domain.domain_id for domain in domains}
    if set(by_id) != expected_ids:
        add_issue(issues, "BEHAVIOR_INDEX_DOMAINS", "产品行为样例集的功能域与需求包清单不一致。")
    for domain in domains:
        entry = by_id.get(domain.domain_id)
        if not isinstance(entry, dict):
            continue
        if entry.get("file") != domain.examples.name:
            add_issue(issues, "BEHAVIOR_INDEX_FILE", f"{domain.domain_id} 的样例索引文件名不一致。")
        listed = entry.get("sample_ids")
        if not isinstance(listed, list) or set(listed) != sample_ids.get(domain.domain_id, set()):
            add_issue(issues, "BEHAVIOR_INDEX_SAMPLES", f"{domain.domain_id} 的样例 ID 索引不完整。")


def _parse_source_rows(text: str) -> list[list[str]]:
    heading = re.search(r"(?m)^## 设计依据与来源\s*$", text)
    if heading is None:
        return []
    rows: list[list[str]] = []
    for line in text[heading.end() :].splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] == "类型":
            continue
        if all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
            continue
        rows.append(cells)
    return rows


def _validate_research(text: str, issues: list[Issue]) -> None:
    source_types = {"竞品", "开源项目", "官方规范"}
    for cells in _parse_source_rows(text):
        if len(cells) < 5:
            add_issue(issues, "SOURCE_ROW", "调研来源表格的每行必须包含五列。")
            continue
        source_type, name, url, accessed, adopted = cells[:5]
        if source_type not in source_types:
            continue
        if not name or not adopted:
            add_issue(issues, "SOURCE_DETAIL", f"{source_type} 来源必须填写名称和借鉴点。")
        if URL_RE.fullmatch(url) is None:
            add_issue(issues, "SOURCE_URL", f"{source_type} 来源必须使用 https URL：{url!r}。")
        if DATE_RE.fullmatch(accessed) is None:
            add_issue(issues, "SOURCE_DATE", f"{source_type} 来源日期格式无效：{accessed!r}。")


def validate_requirement_package(target: Path) -> Report:
    package, initial = resolve_package_root(target)
    issues = list(initial)
    if initial:
        return Report(str(package), issues)

    actual = _walk_package_files(package, issues)
    manifest_path = package / MANIFEST_NAME
    manifest = read_json_yaml(manifest_path, package, issues, code="MANIFEST_FORMAT")
    if manifest is None:
        return Report(str(package), issues)
    domains, declared = _validate_manifest(manifest, package, issues)
    _validate_declared_files(package, declared, actual, issues)

    prd_text = _read_markdown(package / PRD_NAME, package, issues)
    if prd_text is not None:
        _validate_root_prd(prd_text, manifest, package, issues)

    global_features: set[str] = set()
    global_acceptance: set[str] = set()
    global_samples: set[str] = set()
    samples_by_domain: dict[str, set[str]] = {}
    for domain in domains:
        domain_text = _read_markdown(package / domain.requirements, package, issues)
        if domain_text is None:
            continue
        features, refs = _validate_domain_markdown(domain_text, domain, global_features, global_acceptance, issues)
        sample_data = read_json_yaml(package / domain.examples, package, issues, code="SAMPLE_FORMAT")
        if sample_data is None:
            continue
        per_feature = _validate_samples(sample_data, domain, features, refs, global_samples, issues)
        samples_by_domain[domain.domain_id] = set().union(*per_feature.values()) if per_feature else set()

    index = read_json_yaml(package / BEHAVIOR_INDEX, package, issues, code="BEHAVIOR_INDEX_FORMAT")
    if index is not None:
        _validate_behavior_index(index, manifest, domains, samples_by_domain, issues)
    return Report(str(package), issues)


def load_validated_snapshot(target: Path) -> tuple[PackageSnapshot | None, Report]:
    report = validate_requirement_package(target)
    if report.errors:
        return None, report
    package, _ = resolve_package_root(target)
    manifest = json.loads((package / MANIFEST_NAME).read_text(encoding="utf-8"))
    domains = tuple(
        DomainContract(
            str(item["id"]),
            str(item["name"]),
            Path(str(item["requirements"])),
            Path(str(item["examples"])),
            tuple(str(value) for value in item.get("dependencies", [])),
        )
        for item in manifest["domains"]
    )
    files = {str(item["path"]): str(item["sha256"]) for item in manifest["files"]}
    return PackageSnapshot(package, manifest, files, domains), report


def validate_prd(path: Path) -> Report:
    """Compatibility alias for callers; validation now covers the complete package."""
    return validate_requirement_package(path)


def print_human(report: Report) -> None:
    for issue in report.issues:
        location = f":{issue.line}" if issue.line is not None else ""
        print(f"ERROR   {issue.code:32} {report.path}{location}: {issue.message}")
    if report.errors:
        print(f"FAIL: {len(report.errors)} error(s) — {report.path}")
    else:
        print(f"PASS: 0 error(s) — {report.path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验 docs/产品需求/ 下的完整或正式阶段需求包。")
    parser.add_argument("target", type=Path, help="项目根目录、docs/产品需求/，或 docs/产品需求/PRD需求文档.md")
    parser.add_argument("--strict", action="store_true", help="启用完整契约校验")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_requirement_package(args.target)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

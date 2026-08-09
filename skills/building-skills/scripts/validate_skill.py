#!/usr/bin/env python3
"""Deterministic structural validator for Agent Skills.

This validator intentionally implements a conservative subset of YAML parsing so
it can run with Python's standard library only. It validates the portable Agent
Skills fields and a small, explicit set of Claude Code extensions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

STANDARD_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
CLAUDE_EXTENSION_KEYS = {
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "disallowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "background",
    "hooks",
    "paths",
    "shell",
}
REQUIRED_HEADINGS = (
    "# Outcome",
    "## Routing",
    "## Steps",
    "## Delivery",
    "## Guardrails",
    "## References",
)
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$")
NESTED_KEY_RE = re.compile(r"^\s+([A-Za-z0-9_.-]+):(?:\s*(.*))?$")
LOCAL_REFERENCE_RE = re.compile(
    r"`((?:workflows|templates|examples|rules|scripts|checklists|prompts|references|assets|agents)/[^`\s]+)`"
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
WORKFLOW_RE = re.compile(r"^§(\d{2})-[^/]+\.md$")

Scalar = Union[str, Dict[str, str]]


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    path: str
    message: str


@dataclass
class Report:
    skill_dir: str
    profile: str
    issues: List[Issue]

    @property
    def errors(self) -> List[Issue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    def to_dict(self) -> Dict[str, object]:
        return {
            "skill_dir": self.skill_dir,
            "profile": self.profile,
            "status": "pass" if not self.errors else "fail",
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [asdict(issue) for issue in self.issues],
        }


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> Tuple[Mapping[str, Scalar], int, Optional[str]]:
    """Parse simple top-level scalars, nested maps, and block scalars."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0, "缺少起始 Frontmatter 分隔符。"

    try:
        closing = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        return {}, 0, "缺少结束 Frontmatter 分隔符。"

    data: Dict[str, Scalar] = {}
    current_parent: Optional[str] = None
    index = 1
    while index < closing:
        raw = lines[index]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue

        top_match = TOP_LEVEL_KEY_RE.match(raw)
        if top_match and not raw.startswith((" ", "\t")):
            key, raw_value = top_match.groups()
            value = (raw_value or "").strip()
            current_parent = None

            if value in {"|", ">", "|-", ">-", "|+", ">+"}:
                block_lines: List[str] = []
                index += 1
                while index < closing and (not lines[index].strip() or lines[index].startswith((" ", "\t"))):
                    block_lines.append(lines[index].strip())
                    index += 1
                data[key] = ("\n" if value.startswith("|") else " ").join(block_lines).strip()
                continue

            if value == "":
                data[key] = {}
                current_parent = key
            else:
                data[key] = unquote(value)
            index += 1
            continue

        if raw.startswith((" ", "\t")) and current_parent is not None:
            nested_match = NESTED_KEY_RE.match(raw)
            if nested_match and isinstance(data.get(current_parent), dict):
                nested_key, nested_value = nested_match.groups()
                nested_map = data[current_parent]
                assert isinstance(nested_map, dict)
                # Preserve simple nested metadata while tolerating deeper YAML
                # structures (lists/maps) that this dependency-free parser does
                # not need to interpret.
                if nested_value and nested_value.strip():
                    nested_map[nested_key] = unquote(nested_value.strip())
            index += 1
            continue

        return data, closing, f"无法解析 Frontmatter 第 {index + 1} 行：{raw!r}"

    return data, closing, None


def add_issue(issues: List[Issue], severity: str, code: str, path: Path, message: str, root: Path) -> None:
    try:
        display_path = str(path.relative_to(root)) or "."
    except ValueError:
        display_path = str(path)
    issues.append(Issue(severity, code, display_path, message))


def validate_frontmatter(
    *,
    data: Mapping[str, Scalar],
    profile: str,
    skill_dir: Path,
    skill_md: Path,
    issues: List[Issue],
) -> None:
    allowed = set(STANDARD_KEYS)
    if profile == "claude":
        allowed.update(CLAUDE_EXTENSION_KEYS)

    for key in data:
        if key not in allowed:
            add_issue(
                issues,
                "error",
                "FRONTMATTER_KEY",
                skill_md,
                f"{profile} 配置不允许 Frontmatter 字段 {key!r}。",
                skill_dir,
            )

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        add_issue(issues, "error", "NAME_REQUIRED", skill_md, "缺少非空 name。", skill_dir)
    else:
        if len(name) > 64 or not NAME_RE.fullmatch(name):
            add_issue(
                issues,
                "error",
                "NAME_FORMAT",
                skill_md,
                "name 必须为 1–64 个小写字母、数字或单个连字符，且不能以连字符开头或结尾。",
                skill_dir,
            )
        if name != skill_dir.name:
            add_issue(
                issues,
                "error",
                "NAME_DIRECTORY_MISMATCH",
                skill_md,
                f"name {name!r} 必须与父目录 {skill_dir.name!r} 一致。",
                skill_dir,
            )

    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        add_issue(issues, "error", "DESCRIPTION_REQUIRED", skill_md, "缺少非空 description。", skill_dir)
    elif len(description) > 1024:
        add_issue(
            issues,
            "error",
            "DESCRIPTION_LENGTH",
            skill_md,
            f"description 长度为 {len(description)}，超过 1024 字符。",
            skill_dir,
        )

    compatibility = data.get("compatibility")
    if isinstance(compatibility, str) and len(compatibility) > 500:
        add_issue(
            issues,
            "error",
            "COMPATIBILITY_LENGTH",
            skill_md,
            "compatibility 超过 500 字符。",
            skill_dir,
        )

    if profile == "claude":
        manual = data.get("disable-model-invocation")
        if manual is not None and str(manual).lower() not in {"true", "false"}:
            add_issue(
                issues,
                "error",
                "CLAUDE_BOOLEAN",
                skill_md,
                "disable-model-invocation 必须是 true 或 false。",
                skill_dir,
            )


def validate_headings(text: str, skill_dir: Path, skill_md: Path, issues: List[Issue]) -> None:
    positions: List[int] = []
    for heading in REQUIRED_HEADINGS:
        matches = [match.start() for match in re.finditer(rf"(?m)^{re.escape(heading)}\s*$", text)]
        if not matches:
            add_issue(
                issues,
                "error",
                "HEADING_REQUIRED",
                skill_md,
                f"缺少核心章节 {heading!r}。",
                skill_dir,
            )
            continue
        if len(matches) > 1:
            add_issue(
                issues,
                "error",
                "HEADING_DUPLICATE",
                skill_md,
                f"核心章节 {heading!r} 出现多次。",
                skill_dir,
            )
        positions.append(matches[0])

    if len(positions) == len(REQUIRED_HEADINGS) and positions != sorted(positions):
        add_issue(
            issues,
            "error",
            "HEADING_ORDER",
            skill_md,
            "核心章节顺序必须为 Outcome、Routing、Steps、Delivery、Guardrails、References。",
            skill_dir,
        )


def iter_local_references(text: str) -> Iterable[str]:
    yielded = set()
    for match in LOCAL_REFERENCE_RE.finditer(text):
        reference = match.group(1).strip()
        if reference not in yielded:
            yielded.add(reference)
            yield reference

    for match in MARKDOWN_LINK_RE.finditer(text):
        reference = match.group(1).strip().split(maxsplit=1)[0]
        if reference.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if reference not in yielded:
            yielded.add(reference)
            yield reference


def validate_references(text: str, skill_dir: Path, skill_md: Path, issues: List[Issue]) -> None:
    root = skill_dir.resolve()
    for reference in iter_local_references(text):
        normalized = reference.split("#", 1)[0]
        if not normalized:
            continue
        candidate = (skill_dir / normalized).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            add_issue(
                issues,
                "error",
                "REF_OUTSIDE_SKILL",
                skill_md,
                f"引用越过 Skill 根目录：{reference}",
                skill_dir,
            )
            continue
        if not candidate.exists():
            add_issue(
                issues,
                "error",
                "REF_NOT_FOUND",
                skill_md,
                f"引用的路径不存在：{reference}",
                skill_dir,
            )


def validate_workflows(skill_dir: Path, skill_md_text: str, issues: List[Issue]) -> None:
    workflow_dir = skill_dir / "workflows"
    if not workflow_dir.exists():
        return
    if not workflow_dir.is_dir():
        add_issue(issues, "error", "WORKFLOW_NOT_DIR", workflow_dir, "workflows 必须是目录。", skill_dir)
        return

    numbered: List[Tuple[int, Path]] = []
    for path in sorted(workflow_dir.iterdir(), key=lambda item: item.name):
        if not path.is_file():
            continue
        match = WORKFLOW_RE.fullmatch(path.name)
        if not match:
            add_issue(
                issues,
                "error",
                "WORKFLOW_NAME",
                path,
                "工作流文件必须使用 §NN-name.md 格式。",
                skill_dir,
            )
            continue
        numbered.append((int(match.group(1)), path))
        relative = path.relative_to(skill_dir).as_posix()
        if f"`{relative}`" not in skill_md_text:
            add_issue(
                issues,
                "warning",
                "WORKFLOW_UNREFERENCED",
                path,
                "该工作流没有在 SKILL.md 中被反引号路径引用。",
                skill_dir,
            )

    numbers = [number for number, _ in numbered]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        add_issue(
            issues,
            "error",
            "WORKFLOW_SEQUENCE",
            workflow_dir,
            f"工作流编号必须从 01 连续递增；实际为 {numbers}。",
            skill_dir,
        )


def validate_directory_conventions(skill_dir: Path, issues: List[Issue]) -> None:
    template_dir = skill_dir / "templates"
    if template_dir.is_dir():
        for path in template_dir.iterdir():
            if path.is_file() and ".template." not in path.name:
                add_issue(
                    issues,
                    "error",
                    "TEMPLATE_NAME",
                    path,
                    "模板文件名必须包含 .template.。",
                    skill_dir,
                )

    example_dir = skill_dir / "examples"
    if example_dir.is_dir():
        for path in example_dir.iterdir():
            if path.is_file() and ".example." not in path.name:
                add_issue(
                    issues,
                    "error",
                    "EXAMPLE_NAME",
                    path,
                    "示例文件名必须包含 .example.。",
                    skill_dir,
                )

    for path in skill_dir.rglob("*"):
        if path.is_symlink():
            add_issue(
                issues,
                "error",
                "SYMLINK_FORBIDDEN",
                path,
                "Skill 中不允许符号链接，以免引用越界或安装结果不一致。",
                skill_dir,
            )
            continue
        if path.is_file():
            try:
                size = path.stat().st_size
            except OSError as exc:
                add_issue(issues, "error", "FILE_STAT", path, f"无法读取文件信息：{exc}", skill_dir)
                continue
            if size == 0:
                add_issue(issues, "error", "EMPTY_FILE", path, "文件为空。", skill_dir)
            if " " in path.name:
                add_issue(issues, "warning", "FILENAME_SPACE", path, "文件名包含空格。", skill_dir)


def validate_openai_adapter(skill_dir: Path, issues: List[Issue]) -> None:
    adapter = skill_dir / "agents" / "openai.yaml"
    if not adapter.exists():
        return
    try:
        text = adapter.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        add_issue(issues, "error", "OPENAI_ADAPTER_READ", adapter, f"无法读取适配文件：{exc}", skill_dir)
        return

    for match in re.finditer(r"(?m)^\s*allow_implicit_invocation\s*:\s*(\S+)\s*$", text):
        if match.group(1).lower() not in {"true", "false"}:
            add_issue(
                issues,
                "error",
                "OPENAI_POLICY_BOOLEAN",
                adapter,
                "allow_implicit_invocation 必须是 true 或 false。",
                skill_dir,
            )


def validate_skill(skill_dir: Path, profile: str = "portable") -> Report:
    skill_dir = skill_dir.expanduser().resolve()
    issues: List[Issue] = []

    if not skill_dir.is_dir():
        issues.append(Issue("error", "SKILL_DIR", str(skill_dir), "Skill 目录不存在或不是目录。"))
        return Report(str(skill_dir), profile, issues)

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        add_issue(issues, "error", "SKILL_MD", skill_md, "缺少 SKILL.md。", skill_dir)
        return Report(str(skill_dir), profile, issues)

    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        add_issue(issues, "error", "SKILL_MD_READ", skill_md, f"无法以 UTF-8 读取：{exc}", skill_dir)
        return Report(str(skill_dir), profile, issues)

    line_count = len(text.splitlines())
    if line_count > 500:
        add_issue(
            issues,
            "warning",
            "SKILL_MD_LENGTH",
            skill_md,
            f"SKILL.md 共 {line_count} 行，建议保持在 500 行以内并拆分细节。",
            skill_dir,
        )

    frontmatter, _closing, parse_error = parse_frontmatter(text)
    if parse_error:
        add_issue(issues, "error", "FRONTMATTER_PARSE", skill_md, parse_error, skill_dir)
    else:
        validate_frontmatter(
            data=frontmatter,
            profile=profile,
            skill_dir=skill_dir,
            skill_md=skill_md,
            issues=issues,
        )

    validate_headings(text, skill_dir, skill_md, issues)
    validate_references(text, skill_dir, skill_md, issues)
    validate_workflows(skill_dir, text, issues)
    validate_directory_conventions(skill_dir, issues)
    validate_openai_adapter(skill_dir, issues)

    return Report(str(skill_dir), profile, issues)


def print_human(report: Report) -> None:
    for issue in report.issues:
        print(f"{issue.severity.upper():7} {issue.code:28} {issue.path}: {issue.message}")

    if report.errors:
        print(
            f"FAIL: {len(report.errors)} error(s), {len(report.warnings)} warning(s) — {report.skill_dir}"
        )
    else:
        print(f"PASS: 0 error(s), {len(report.warnings)} warning(s) — {report.skill_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验 Agent Skill 的结构、Frontmatter 和本地引用。")
    parser.add_argument("skill_dir", type=Path, help="包含 SKILL.md 的 Skill 目录")
    parser.add_argument(
        "--profile",
        choices=("portable", "claude", "codex"),
        default="portable",
        help="按目标配置允许对应 Frontmatter 字段",
    )
    parser.add_argument("--strict", action="store_true", help="将 warning 视为失败")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_skill(args.skill_dir, args.profile)

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_human(report)

    if report.errors or (args.strict and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

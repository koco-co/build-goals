#!/usr/bin/env python3
"""Dependency-free validator for Claude Code and Codex plugin packages."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union

SKILLS_VALIDATOR_DIR = Path(__file__).resolve().parent
if str(SKILLS_VALIDATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_VALIDATOR_DIR))

from validate_skill import Report as SkillReport  # noqa: E402
from validate_skill import validate_skill  # noqa: E402

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    path: str
    message: str


@dataclass
class Report:
    plugin_dir: str
    platform: str
    issues: List[Issue]
    skills_checked: List[str]

    @property
    def errors(self) -> List[Issue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    def to_dict(self) -> Dict[str, object]:
        return {
            "plugin_dir": self.plugin_dir,
            "platform": self.platform,
            "status": "pass" if not self.errors else "fail",
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "skills_checked": self.skills_checked,
            "issues": [asdict(issue) for issue in self.issues],
        }


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)) or "."
    except ValueError:
        return str(path)


def add_issue(
    issues: List[Issue],
    severity: str,
    code: str,
    path: Path,
    message: str,
    root: Path,
) -> None:
    issues.append(Issue(severity, code, display_path(path, root), message))


def load_json(path: Path, plugin_root: Path, issues: List[Issue]) -> Optional[Mapping[str, object]]:
    if not path.is_file():
        add_issue(issues, "error", "MANIFEST_REQUIRED", path, "缺少 Manifest。", plugin_root)
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeError as exc:
        add_issue(
            issues,
            "error",
            "JSON_ENCODING",
            path,
            f"无法以 UTF-8 读取：{exc}",
            plugin_root,
        )
        return None
    except json.JSONDecodeError as exc:
        add_issue(
            issues,
            "error",
            "JSON_PARSE",
            path,
            f"JSON 无法解析：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}",
            plugin_root,
        )
        return None
    except OSError as exc:
        add_issue(
            issues,
            "error",
            "JSON_READ",
            path,
            f"无法读取文件：{exc}",
            plugin_root,
        )
        return None

    if not isinstance(data, dict):
        add_issue(
            issues,
            "error",
            "JSON_OBJECT",
            path,
            "顶层 JSON 必须是对象。",
            plugin_root,
        )
        return None
    return data


def validate_identity(
    data: Mapping[str, object],
    path: Path,
    plugin_root: Path,
    issues: List[Issue],
) -> Tuple[Optional[str], Optional[str]]:
    name = data.get("name")
    version = data.get("version")
    description = data.get("description")

    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        add_issue(
            issues,
            "error",
            "PLUGIN_NAME",
            path,
            "name 必须是 kebab-case，且只能包含小写字母、数字和单个连字符。",
            plugin_root,
        )
        normalized_name: Optional[str] = None
    else:
        normalized_name = name

    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        add_issue(
            issues,
            "error",
            "PLUGIN_VERSION",
            path,
            "version 必须使用 SemVer，例如 1.0.0。",
            plugin_root,
        )
        normalized_version: Optional[str] = None
    else:
        normalized_version = version

    if not isinstance(description, str) or not description.strip():
        add_issue(
            issues,
            "error",
            "PLUGIN_DESCRIPTION",
            path,
            "description 必须是非空字符串。",
            plugin_root,
        )

    return normalized_name, normalized_version


def iter_component_paths(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                yield item


def validate_component_path(
    *,
    raw_path: str,
    field: str,
    manifest_path: Path,
    plugin_root: Path,
    issues: List[Issue],
    expect: Optional[str] = None,
) -> Optional[Path]:
    if not raw_path.startswith("./"):
        add_issue(
            issues,
            "error",
            "COMPONENT_PATH_PREFIX",
            manifest_path,
            f"{field} 路径必须以 ./ 开头：{raw_path}",
            plugin_root,
        )
        return None

    lexical = Path(os.path.abspath(plugin_root / raw_path))
    if not is_within(lexical, plugin_root.absolute()):
        add_issue(
            issues,
            "error",
            "COMPONENT_PATH_TRAVERSAL",
            manifest_path,
            f"{field} 路径越过 Plugin 根目录：{raw_path}",
            plugin_root,
        )
        return None

    try:
        resolved = (plugin_root / raw_path).resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        add_issue(
            issues,
            "error",
            "COMPONENT_PATH_RESOLVE",
            manifest_path,
            f"无法解析 {field} 路径 {raw_path}：{exc}",
            plugin_root,
        )
        return None

    if not is_within(resolved, plugin_root.resolve()):
        add_issue(
            issues,
            "error",
            "COMPONENT_PATH_OUTSIDE",
            manifest_path,
            f"{field} 最终目标越过 Plugin 根目录：{raw_path}",
            plugin_root,
        )
        return None

    candidate = plugin_root / raw_path
    if not candidate.exists():
        add_issue(
            issues,
            "error",
            "COMPONENT_PATH_MISSING",
            manifest_path,
            f"{field} 路径不存在：{raw_path}",
            plugin_root,
        )
        return None

    if expect == "dir" and not candidate.is_dir():
        add_issue(
            issues,
            "error",
            "COMPONENT_PATH_NOT_DIR",
            manifest_path,
            f"{field} 必须指向目录：{raw_path}",
            plugin_root,
        )
        return None
    if expect == "file" and not candidate.is_file():
        add_issue(
            issues,
            "error",
            "COMPONENT_PATH_NOT_FILE",
            manifest_path,
            f"{field} 必须指向文件：{raw_path}",
            plugin_root,
        )
        return None

    return candidate.resolve()


def validate_manifest_directory(
    config_dir: Path,
    plugin_root: Path,
    issues: List[Issue],
) -> None:
    if not config_dir.is_dir():
        return
    for child in config_dir.iterdir():
        if child.name != "plugin.json":
            add_issue(
                issues,
                "error",
                "MANIFEST_DIRECTORY_CONTENT",
                child,
                f"{config_dir.name}/ 只应包含 plugin.json。",
                plugin_root,
            )


def validate_manifest(
    *,
    platform: str,
    manifest_path: Path,
    plugin_root: Path,
    issues: List[Issue],
) -> Tuple[Optional[Mapping[str, object]], Optional[str], Optional[str], Set[Path]]:
    data = load_json(manifest_path, plugin_root, issues)
    if data is None:
        return None, None, None, set()

    name, version = validate_identity(data, manifest_path, plugin_root, issues)
    skill_roots: Set[Path] = set()

    skills_value = data.get("skills")
    if skills_value is None:
        default_skills = plugin_root / "skills"
        if default_skills.is_dir():
            skill_roots.add(default_skills.resolve())
    else:
        paths = list(iter_component_paths(skills_value))
        if not paths:
            add_issue(
                issues,
                "error",
                "SKILLS_FIELD_TYPE",
                manifest_path,
                "skills 必须是字符串或字符串数组。",
                plugin_root,
            )
        for raw_path in paths:
            resolved = validate_component_path(
                raw_path=raw_path,
                field="skills",
                manifest_path=manifest_path,
                plugin_root=plugin_root,
                issues=issues,
                expect="dir",
            )
            if resolved is not None:
                skill_roots.add(resolved)

    component_fields = {
        "hooks": "file",
        "mcpServers": "file",
        "apps": "file",
        "agents": None,
        "commands": None,
        "outputStyles": None,
        "lspServers": "file",
    }
    for field, expected in component_fields.items():
        if field not in data:
            continue
        for raw_path in iter_component_paths(data[field]):
            validate_component_path(
                raw_path=raw_path,
                field=field,
                manifest_path=manifest_path,
                plugin_root=plugin_root,
                issues=issues,
                expect=expected,
            )

    if platform == "codex":
        interface = data.get("interface")
        if interface is not None and not isinstance(interface, dict):
            add_issue(
                issues,
                "error",
                "CODEX_INTERFACE",
                manifest_path,
                "Codex interface 必须是对象。",
                plugin_root,
            )
    if platform == "claude":
        schema = data.get("$schema")
        if schema is not None and not isinstance(schema, str):
            add_issue(
                issues,
                "error",
                "CLAUDE_SCHEMA",
                manifest_path,
                "$schema 必须是字符串。",
                plugin_root,
            )

    return data, name, version, skill_roots


def validate_symlinks(plugin_root: Path, issues: List[Issue]) -> None:
    for path in plugin_root.rglob("*"):
        if not path.is_symlink():
            continue

        try:
            target = os.readlink(path)
        except OSError as exc:
            add_issue(
                issues,
                "error",
                "SYMLINK_READ",
                path,
                f"无法读取软链接：{exc}",
                plugin_root,
            )
            continue

        if Path(target).is_absolute():
            add_issue(
                issues,
                "error",
                "SYMLINK_ABSOLUTE",
                path,
                "软链接必须使用相对路径。",
                plugin_root,
            )
            continue

        try:
            resolved = path.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            add_issue(
                issues,
                "error",
                "SYMLINK_RESOLVE",
                path,
                f"无法解析软链接：{exc}",
                plugin_root,
            )
            continue

        if not is_within(resolved, plugin_root.resolve()):
            add_issue(
                issues,
                "error",
                "SYMLINK_OUTSIDE_PLUGIN",
                path,
                f"软链接目标越过 Plugin 根目录：{target}",
                plugin_root,
            )
            continue

        if not path.exists():
            add_issue(
                issues,
                "error",
                "SYMLINK_BROKEN",
                path,
                f"软链接目标不存在：{target}",
                plugin_root,
            )


def validate_marketplace(plugin_root: Path, issues: List[Issue]) -> None:
    path = plugin_root / ".agents" / "plugins" / "marketplace.json"
    if not path.exists():
        return
    data = load_json(path, plugin_root, issues)
    if data is None:
        return

    name = data.get("name")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        add_issue(
            issues,
            "error",
            "MARKETPLACE_NAME",
            path,
            "Marketplace name 必须是 kebab-case。",
            plugin_root,
        )

    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        add_issue(
            issues,
            "error",
            "MARKETPLACE_PLUGINS",
            path,
            "Marketplace plugins 必须是非空数组。",
            plugin_root,
        )
        return

    for index, item in enumerate(plugins):
        if not isinstance(item, dict):
            add_issue(
                issues,
                "error",
                "MARKETPLACE_ENTRY",
                path,
                f"plugins[{index}] 必须是对象。",
                plugin_root,
            )
            continue
        source = item.get("source")
        raw_path: Optional[str] = None
        if isinstance(source, str):
            raw_path = source
        elif isinstance(source, dict):
            candidate = source.get("path")
            if isinstance(candidate, str):
                raw_path = candidate

        if raw_path is None:
            add_issue(
                issues,
                "error",
                "MARKETPLACE_SOURCE",
                path,
                f"plugins[{index}] 缺少 source.path。",
                plugin_root,
            )
        else:
            validate_component_path(
                raw_path=raw_path,
                field=f"plugins[{index}].source.path",
                manifest_path=path,
                plugin_root=plugin_root,
                issues=issues,
                expect="dir",
            )

        policy = item.get("policy")
        if not isinstance(policy, dict):
            add_issue(
                issues,
                "error",
                "MARKETPLACE_POLICY",
                path,
                f"plugins[{index}] 缺少 policy 对象。",
                plugin_root,
            )
        else:
            if not isinstance(policy.get("installation"), str):
                add_issue(
                    issues,
                    "error",
                    "MARKETPLACE_INSTALLATION",
                    path,
                    f"plugins[{index}].policy.installation 必须是字符串。",
                    plugin_root,
                )
            if not isinstance(policy.get("authentication"), str):
                add_issue(
                    issues,
                    "error",
                    "MARKETPLACE_AUTH",
                    path,
                    f"plugins[{index}].policy.authentication 必须是字符串。",
                    plugin_root,
                )

        if not isinstance(item.get("category"), str):
            add_issue(
                issues,
                "error",
                "MARKETPLACE_CATEGORY",
                path,
                f"plugins[{index}].category 必须是字符串。",
                plugin_root,
            )


def merge_skill_report(
    report: SkillReport,
    skill_dir: Path,
    plugin_root: Path,
    issues: List[Issue],
) -> None:
    prefix = display_path(skill_dir, plugin_root)
    for issue in report.issues:
        relative = issue.path
        path = f"{prefix}/{relative}" if relative != "." else prefix
        issues.append(
            Issue(
                issue.severity,
                f"SKILL_{issue.code}",
                path,
                issue.message,
            )
        )


def collect_skill_dirs(skill_roots: Iterable[Path]) -> List[Path]:
    discovered: Set[Path] = set()
    for root in skill_roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if child.is_dir() and (child / "SKILL.md").is_file():
                discovered.add(child.resolve())
    return sorted(discovered, key=lambda item: str(item))


def validate_plugin(plugin_dir: Path, platform: str = "dual") -> Report:
    plugin_root = plugin_dir.expanduser().resolve()
    issues: List[Issue] = []
    skills_checked: List[str] = []

    if not plugin_root.is_dir():
        issues.append(
            Issue(
                "error",
                "PLUGIN_DIR",
                str(plugin_root),
                "Plugin 根目录不存在或不是目录。",
            )
        )
        return Report(str(plugin_root), platform, issues, skills_checked)

    validate_symlinks(plugin_root, issues)

    codex_result = (None, None, None, set())
    claude_result = (None, None, None, set())

    if platform in {"codex", "dual"}:
        codex_dir = plugin_root / ".codex-plugin"
        validate_manifest_directory(codex_dir, plugin_root, issues)
        codex_result = validate_manifest(
            platform="codex",
            manifest_path=codex_dir / "plugin.json",
            plugin_root=plugin_root,
            issues=issues,
        )

    if platform in {"claude", "dual"}:
        claude_dir = plugin_root / ".claude-plugin"
        validate_manifest_directory(claude_dir, plugin_root, issues)
        claude_result = validate_manifest(
            platform="claude",
            manifest_path=claude_dir / "plugin.json",
            plugin_root=plugin_root,
            issues=issues,
        )

    if platform == "dual":
        _c_data, c_name, c_version, c_skills = codex_result
        _a_data, a_name, a_version, a_skills = claude_result
        if c_name and a_name and c_name != a_name:
            add_issue(
                issues,
                "error",
                "DUAL_NAME_MISMATCH",
                plugin_root,
                f"两个 Manifest 的 name 不一致：{c_name!r} != {a_name!r}。",
                plugin_root,
            )
        if c_version and a_version and c_version != a_version:
            add_issue(
                issues,
                "error",
                "DUAL_VERSION_MISMATCH",
                plugin_root,
                f"两个 Manifest 的 version 不一致：{c_version!r} != {a_version!r}。",
                plugin_root,
            )
        if c_skills and a_skills and c_skills != a_skills:
            add_issue(
                issues,
                "error",
                "DUAL_SKILLS_MISMATCH",
                plugin_root,
                "两个 Manifest 必须指向同一组 Skills 规范源。",
                plugin_root,
            )

    all_skill_roots: Set[Path] = set(codex_result[3]) | set(claude_result[3])
    skill_dirs = collect_skill_dirs(all_skill_roots)
    if not skill_dirs:
        add_issue(
            issues,
            "warning",
            "NO_SKILLS",
            plugin_root / "skills",
            "没有发现包含 SKILL.md 的 Skill。",
            plugin_root,
        )

    skill_profile = "dual" if platform == "dual" else platform
    for skill_dir in skill_dirs:
        report = validate_skill(skill_dir, skill_profile, plugin_root)
        skills_checked.append(display_path(skill_dir, plugin_root))
        merge_skill_report(report, skill_dir, plugin_root, issues)

    if platform in {"codex", "dual"}:
        validate_marketplace(plugin_root, issues)

    return Report(str(plugin_root), platform, issues, skills_checked)


def print_human(report: Report) -> None:
    for issue in report.issues:
        print(f"{issue.severity.upper():7} {issue.code:32} {issue.path}: {issue.message}")

    if report.skills_checked:
        print("SKILLS: " + ", ".join(report.skills_checked))

    if report.errors:
        print(
            f"FAIL: {len(report.errors)} error(s), "
            f"{len(report.warnings)} warning(s) — {report.plugin_dir}"
        )
    else:
        print(
            f"PASS: 0 error(s), {len(report.warnings)} warning(s) — "
            f"{report.plugin_dir}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="校验 Claude Code、Codex 或双平台 Plugin 的结构与 Skills。"
    )
    parser.add_argument("plugin_dir", type=Path, help="Plugin 根目录")
    parser.add_argument(
        "--platform",
        choices=("dual", "claude", "codex"),
        default="dual",
    )
    parser.add_argument("--strict", action="store_true", help="将 warning 视为失败")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_plugin(args.plugin_dir, args.platform)

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_human(report)

    if report.errors or (args.strict and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

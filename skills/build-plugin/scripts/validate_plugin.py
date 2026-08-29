#!/usr/bin/env python3
"""Strict-status aware Plugin validator with Claude Marketplace coverage."""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_plugin_core as _core  # noqa: E402

Report = _core.Report
build_parser = _core.build_parser


def _report_to_dict(report: _core.Report, strict: bool = False) -> dict[str, object]:
    failed = bool(report.errors or (strict and report.warnings))
    return {
        "plugin_dir": report.plugin_dir,
        "platform": report.platform,
        "status": "fail" if failed else "pass",
        "error_count": len(report.errors),
        "warning_count": len(report.warnings),
        "strict": strict,
        "skills_checked": report.skills_checked,
        "issues": [_core.asdict(issue) for issue in report.issues],
    }


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_claude_marketplace(plugin_root: Path, report: _core.Report) -> None:
    path = plugin_root / ".claude-plugin" / "marketplace.json"
    if not path.exists():
        return
    data = _core.load_json(path, plugin_root, report.issues)
    if data is None:
        return

    schema = data.get("$schema")
    if schema is not None and not _nonempty(schema):
        _core.add_issue(
            report.issues,
            "error",
            "CLAUDE_MARKETPLACE_SCHEMA",
            path,
            "$schema 存在时必须是非空字符串。",
            plugin_root,
        )

    name = data.get("name")
    if not isinstance(name, str) or _core.NAME_RE.fullmatch(name) is None:
        _core.add_issue(
            report.issues,
            "error",
            "CLAUDE_MARKETPLACE_NAME",
            path,
            "Marketplace name 必须是 kebab-case。",
            plugin_root,
        )

    owner = data.get("owner")
    if not isinstance(owner, dict) or not _nonempty(owner.get("name")):
        _core.add_issue(
            report.issues,
            "error",
            "CLAUDE_MARKETPLACE_OWNER",
            path,
            "Marketplace owner 必须包含非空 name。",
            plugin_root,
        )

    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    manifest_name: str | None = None
    manifest_version: str | None = None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        manifest = None
    if isinstance(manifest, dict):
        if isinstance(manifest.get("name"), str):
            manifest_name = str(manifest["name"])
        if isinstance(manifest.get("version"), str):
            manifest_version = str(manifest["version"])

    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        _core.add_issue(
            report.issues,
            "error",
            "CLAUDE_MARKETPLACE_PLUGINS",
            path,
            "Marketplace plugins 必须是非空数组。",
            plugin_root,
        )
        return

    matched_manifest = False
    for index, item in enumerate(plugins):
        if not isinstance(item, dict):
            _core.add_issue(
                report.issues,
                "error",
                "CLAUDE_MARKETPLACE_ENTRY",
                path,
                f"plugins[{index}] 必须是对象。",
                plugin_root,
            )
            continue
        entry_name = item.get("name")
        if (
            not isinstance(entry_name, str)
            or _core.NAME_RE.fullmatch(entry_name) is None
        ):
            _core.add_issue(
                report.issues,
                "error",
                "CLAUDE_MARKETPLACE_PLUGIN_NAME",
                path,
                f"plugins[{index}].name 必须是 kebab-case。",
                plugin_root,
            )
        if entry_name == manifest_name:
            matched_manifest = True

        version = item.get("version")
        if version is not None:
            if (
                not isinstance(version, str)
                or _core.SEMVER_RE.fullmatch(version) is None
            ):
                _core.add_issue(
                    report.issues,
                    "error",
                    "CLAUDE_MARKETPLACE_VERSION",
                    path,
                    f"plugins[{index}].version 存在时必须使用 SemVer。",
                    plugin_root,
                )
            elif (
                entry_name == manifest_name
                and manifest_version
                and version != manifest_version
            ):
                _core.add_issue(
                    report.issues,
                    "error",
                    "CLAUDE_MARKETPLACE_VERSION_MISMATCH",
                    path,
                    f"Marketplace 中 {entry_name!r} 的版本 {version!r} 与 Claude Plugin Manifest {manifest_version!r} 不一致。",
                    plugin_root,
                )

        if "description" in item and not _nonempty(item.get("description")):
            _core.add_issue(
                report.issues,
                "error",
                "CLAUDE_MARKETPLACE_DESCRIPTION",
                path,
                f"plugins[{index}].description 存在时必须是非空字符串。",
                plugin_root,
            )
        if "author" in item:
            author = item.get("author")
            if not isinstance(author, dict) or not _nonempty(author.get("name")):
                _core.add_issue(
                    report.issues,
                    "error",
                    "CLAUDE_MARKETPLACE_AUTHOR",
                    path,
                    f"plugins[{index}].author 存在时必须包含非空 name。",
                    plugin_root,
                )

        source = item.get("source")
        if isinstance(source, str) and source.startswith("./"):
            _core.validate_component_path(
                raw_path=source,
                field=f"plugins[{index}].source",
                manifest_path=path,
                plugin_root=plugin_root,
                issues=report.issues,
                expect="dir",
            )
        elif not isinstance(source, (str, dict)):
            _core.add_issue(
                report.issues,
                "error",
                "CLAUDE_MARKETPLACE_SOURCE",
                path,
                f"plugins[{index}].source 必须是字符串或对象。",
                plugin_root,
            )

        for field in ("homepage", "repository"):
            if field in item and not _nonempty(item.get(field)):
                _core.add_issue(
                    report.issues,
                    "error",
                    "CLAUDE_MARKETPLACE_URL",
                    path,
                    f"plugins[{index}].{field} 存在时必须是非空字符串。",
                    plugin_root,
                )

    if manifest_name and not matched_manifest:
        _core.add_issue(
            report.issues,
            "error",
            "CLAUDE_MARKETPLACE_MANIFEST_MISSING",
            path,
            f"Marketplace 没有声明当前 Claude Plugin {manifest_name!r}。",
            plugin_root,
        )


def validate_plugin(plugin_dir: Path, platform: str = "dual") -> _core.Report:
    report = _core.validate_plugin(plugin_dir, platform)
    if platform in {"claude", "dual", "all"} and Path(report.plugin_dir).is_dir():
        _validate_claude_marketplace(Path(report.plugin_dir), report)
    return report


def print_human(report: _core.Report, *, strict: bool = False) -> None:
    for issue in report.issues:
        print(
            f"{issue.severity.upper():7} {issue.code:32} {issue.path}: {issue.message}"
        )
    if report.skills_checked:
        print("SKILLS: " + ", ".join(report.skills_checked))
    failed = bool(report.errors or (strict and report.warnings))
    prefix = "FAIL" if failed else "PASS"
    print(
        f"{prefix}: {len(report.errors)} error(s), "
        f"{len(report.warnings)} warning(s) — {report.plugin_dir}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_plugin(args.plugin_dir, args.platform)
    failed = bool(report.errors or (args.strict and report.warnings))

    if args.json:
        print(
            json.dumps(
                _report_to_dict(report, strict=args.strict),
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_human(report, strict=args.strict)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())

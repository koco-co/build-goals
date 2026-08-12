#!/usr/bin/env python3
"""Validate vibe-coding architecture, planning, readiness, and delivery evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from vibe_validation import Report, validate_project


def print_human(report: Report) -> None:
    for item in report.issues:
        print(f"{item.severity.upper():7} {item.code:28} {item.path}: {item.message}")
    if report.errors:
        print(
            f"FAIL: {len(report.errors)} error(s), {len(report.warnings)} warning(s), "
            f"{len(report.infos)} info item(s) — "
            f"{report.project_root}"
        )
    else:
        print(
            f"PASS: 0 error(s), {len(report.warnings)} warning(s), "
            f"{len(report.infos)} info item(s) — "
            f"{report.project_root}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="校验 vibe-coding 的架构、任务追踪、开发就绪和交付产物。"
    )
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--mode", choices=("greenfield", "migration"), required=True)
    parser.add_argument(
        "--phase",
        choices=("architecture", "plan", "readiness", "delivery"),
        default="delivery",
    )
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--strict", action="store_true", help="将 warning 视为失败")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_project(
        args.project_root,
        args.mode,
        args.phase,
        require_clean=args.require_clean,
    )
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return int(bool(report.errors or (args.strict and report.warnings)))


if __name__ == "__main__":
    raise SystemExit(main())

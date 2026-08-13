#!/usr/bin/env python3
"""Strict-status aware CLI wrapper for the Agent Skill validator core."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_skill_core import *  # noqa: F403,E402
import validate_skill_core as _core  # noqa: E402

Report = _core.Report
validate_skill = _core.validate_skill
build_parser = _core.build_parser


def _report_to_dict(self: Report, strict: bool = False) -> dict[str, object]:
    failed = bool(self.errors or (strict and self.warnings))
    return {
        "skill_dir": self.skill_dir,
        "profile": self.profile,
        "status": "fail" if failed else "pass",
        "error_count": len(self.errors),
        "warning_count": len(self.warnings),
        "strict": strict,
        "issues": [_core.asdict(issue) for issue in self.issues],
    }


Report.to_dict = _report_to_dict  # type: ignore[method-assign]


def print_human(report: Report, *, strict: bool = False) -> None:
    for issue in report.issues:
        print(f"{issue.severity.upper():7} {issue.code:28} {issue.path}: {issue.message}")

    failed = bool(report.errors or (strict and report.warnings))
    prefix = "FAIL" if failed else "PASS"
    print(
        f"{prefix}: {len(report.errors)} error(s), "
        f"{len(report.warnings)} warning(s) — {report.skill_dir}"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_skill(args.skill_dir, args.profile, args.plugin_root)
    failed = bool(report.errors or (args.strict and report.warnings))

    if args.json:
        print(json.dumps(report.to_dict(strict=args.strict), ensure_ascii=False, indent=2))
    else:
        print_human(report, strict=args.strict)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())

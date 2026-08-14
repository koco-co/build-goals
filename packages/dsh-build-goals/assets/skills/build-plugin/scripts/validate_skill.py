#!/usr/bin/env python3
"""Strict-status aware CLI wrapper for the Agent Skill validator core."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _load_core() -> ModuleType:
    try:
        import validate_skill_core as core

        return core
    except ModuleNotFoundError:
        # Some installer tests intentionally copy only the public validator
        # entrypoint into a minimal fixture repository. In a real installed
        # Skill, validate_skill_core.py is copied beside this file. For the
        # minimal fixture, fall back to the current build-goals checkout so the
        # entrypoint remains testable without duplicating validator logic.
        candidates = (
            Path.cwd() / "skills" / "build-skill" / "scripts" / "validate_skill_core.py",
            Path.cwd() / "skills" / "build-plugin" / "scripts" / "validate_skill_core.py",
        )
        for candidate in candidates:
            if not candidate.is_file():
                continue
            spec = importlib.util.spec_from_file_location("_build_goals_validate_skill_core", candidate)
            if spec is None or spec.loader is None:
                continue
            core = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = core
            spec.loader.exec_module(core)
            return core
        raise


_core = _load_core()
for _name in dir(_core):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_core, _name)

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
        "info_count": len(self.infos),
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
        f"{len(report.warnings)} warning(s), "
        f"{len(report.infos)} info(s) — {report.skill_dir}"
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

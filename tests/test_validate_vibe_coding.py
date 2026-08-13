from __future__ import annotations

import json
from pathlib import Path

from tests.vibe_coding_validator_cases import *  # noqa: F401,F403
from tests.vibe_coding_validator_cases import VibeCodingValidatorTests as _VibeCases


_original_write_architecture = _VibeCases.write_architecture


def _expanded_marker(marker: str) -> str:
    parts = [marker]
    if "F-001-AC-01" in marker and "F-001-AC-02" not in marker:
        parts.append("F-001-AC-02")
    if "F-001" in marker and "SAMPLE-TASK-001" not in marker:
        parts.append(
            "SAMPLE-TASK-001 SAMPLE-TASK-002 SAMPLE-TASK-003 SAMPLE-TASK-004"
        )
    return " ".join(parts)


def _write_architecture(self, root: Path, mode: str) -> None:
    _original_write_architecture(self, root, mode)
    if mode != "migration":
        return
    findings = root / "docs" / "架构迁移" / "审查发现.yaml"
    findings.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "baseline_revision": "fixture",
                "generated_from": "independent-repository-audit",
                "findings": [
                    {
                        "id": "AUD-001",
                        "severity": "High",
                        "area": "fixture",
                        "evidence": ["legacy/module.py"],
                        "impact": "旧实现存在需要迁移处理的问题。",
                        "recommendation": "按已确认迁移方案处理。",
                        "verification": "迁移任务和交付报告追踪 AUD-001。",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


_VibeCases.expanded_marker = staticmethod(_expanded_marker)
_VibeCases.write_architecture = _write_architecture

# Keep unittest discovery focused on the imported TestCase without exporting the
# private patching alias as a second independently discovered class name.
del _VibeCases

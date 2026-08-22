from __future__ import annotations

from typing import Any
from datetime import datetime

from .curriculum import ContractError, EVIDENCE_PROFILES


PROGRESS = {"未开始", "学习中", "阻塞", "已完成"}
MASTERY = {"未证明", "已独立应用", "已迁移", "已保持"}
ORIGINS = {"host-tool", "user-ci", "user-supplied"}
LEVELS = {"independent", "transfer", "retention"}
REQUIRED_LEVEL = {"已独立应用": "independent", "已迁移": "transfer", "已保持": "retention"}


def normalize_learning_state(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ContractError("learning state must be an object")
    progress = value.get("progress_status")
    mastery = value.get("mastery_status")
    if progress not in PROGRESS:
        raise ContractError("progress_status is invalid")
    if mastery not in MASTERY:
        raise ContractError("mastery_status is invalid")
    return {"progress_status": progress, "mastery_status": mastery}


def can_graduate(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    try:
        state = normalize_learning_state(record)
    except ContractError:
        return False
    if state["progress_status"] != "已完成" or state["mastery_status"] == "未证明":
        return False
    if record.get("evidence_profile") not in EVIDENCE_PROFILES:
        return False
    evidence = record.get("mastery_evidence")
    if not isinstance(evidence, list) or not evidence:
        return False
    required_level = REQUIRED_LEVEL[state["mastery_status"]]
    accepted_levels = {
        "independent": {"independent", "transfer", "retention"},
        "transfer": {"transfer", "retention"},
        "retention": {"retention"},
    }[required_level]
    for item in evidence:
        if not isinstance(item, dict):
            continue
        required_text = ("evidence_id", "summary", "verification_ref", "observed_at")
        if not all(isinstance(item.get(field), str) and item[field].strip() for field in required_text):
            continue
        try:
            datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00"))
        except ValueError:
            continue
        if (
            item.get("origin") in ORIGINS
            and item.get("verified") is True
            and item.get("evidence_profile") == record.get("evidence_profile")
            and item.get("capability_level") in LEVELS
            and item.get("capability_level") in accepted_levels
            and (
                item.get("origin") in {"host-tool", "user-ci"}
                or item.get("verified_by") in {"host-tool", "user-ci"}
            )
        ):
            return True
    return False

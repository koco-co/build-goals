from __future__ import annotations

from typing import Any
from pathlib import PurePosixPath

from .curriculum import ContractError, EVIDENCE_PROFILES, validate_curriculum


PROGRESS_MAP = {
    "未开始": "未开始", "学习中": "学习中", "阻塞": "阻塞",
    "待复习": "已完成", "已掌握": "已完成", "已完成": "已完成",
}
HISTORY_FIELDS = ("answers", "practice", "reviews", "attempts", "mastery_evidence")
IDENTITY_FIELDS = ("title", "content_note", "created_at", "updated_at")


def migrate_record(old: Any, *, evidence_profile: str | None, target_unit_id: str | None = None) -> dict[str, Any]:
    if not isinstance(old, dict) or not isinstance(old.get("unit_id"), str):
        raise ContractError("legacy record must have an unambiguous unit_id")
    if evidence_profile not in EVIDENCE_PROFILES:
        raise ContractError("legacy record requires one unambiguous evidence_profile")
    legacy_status = old.get("learning_status", "未开始")
    if legacy_status not in PROGRESS_MAP:
        raise ContractError(f"unsupported legacy learning_status: {legacy_status}")
    migrated = {
        key: old[key]
        for key in (*IDENTITY_FIELDS, *HISTORY_FIELDS)
        if key in old
    }
    migrated["schema_version"] = 3
    migrated["unit_id"] = old["unit_id"]
    if target_unit_id:
        migrated["legacy_unit_id"] = migrated["unit_id"]
        migrated["unit_id"] = target_unit_id
    migrated["progress_status"] = PROGRESS_MAP[legacy_status]
    migrated["mastery_status"] = "未证明"
    migrated["evidence_profile"] = evidence_profile
    return migrated


def build_migration_preview(
    records: list[dict[str, Any]],
    *,
    target_curriculum: dict[str, Any],
    unit_mappings: list[dict[str, Any]],
) -> dict[str, Any]:
    curriculum = validate_curriculum(target_curriculum)
    target_units = {unit["unit_id"]: unit for unit in curriculum["units"]}
    if not isinstance(unit_mappings, list) or not unit_mappings:
        raise ContractError("migration requires explicit unit and content mappings")
    mappings: dict[str, dict[str, Any]] = {}
    target_ids: set[str] = set()
    legacy_paths: set[str] = set()
    for index, mapping in enumerate(unit_mappings):
        if not isinstance(mapping, dict):
            raise ContractError(f"unit_mappings[{index}] must be an object")
        legacy_id = mapping.get("legacy_unit_id")
        target_id = mapping.get("target_unit_id")
        legacy_content = mapping.get("legacy_content")
        target_note_path = mapping.get("target_note_path")
        legacy_ownership = mapping.get("legacy_knowledge_ownership")
        if not all(isinstance(item, str) and item.strip() for item in (legacy_id, target_id, legacy_content, target_note_path)):
            raise ContractError(f"unit_mappings[{index}] must define legacy unit, target unit, and content paths")
        legacy_path = PurePosixPath(legacy_content)
        if legacy_content.startswith("/") or "\\" in legacy_content or any(part in {"", ".", "..", ".obsidian"} for part in legacy_path.parts):
            raise ContractError(f"unit_mappings[{index}].legacy_content must be a safe Vault-relative path")
        if legacy_id in mappings:
            raise ContractError(f"ambiguous split mapping for legacy unit_id: {legacy_id}")
        if target_id in target_ids:
            raise ContractError(f"ambiguous merge mapping for target unit_id: {target_id}")
        if legacy_content in legacy_paths:
            raise ContractError(f"legacy content is mapped more than once: {legacy_content}")
        if target_id not in target_units or target_note_path != target_units[target_id]["note_path"]:
            raise ContractError(f"unit_mappings[{index}] does not match target curriculum")
        if legacy_ownership != target_units[target_id]["knowledge_ownership"]:
            raise ContractError(f"unit_mappings[{index}] knowledge ownership does not match target curriculum")
        mappings[legacy_id] = mapping
        target_ids.add(target_id)
        legacy_paths.add(legacy_content)
    migrated = []
    seen: set[str] = set()
    for record in records:
        unit_id = record.get("unit_id")
        if unit_id in seen:
            raise ContractError(f"ambiguous duplicate legacy unit_id: {unit_id}")
        seen.add(unit_id)
        mapping = mappings.get(str(unit_id))
        if mapping is None:
            raise ContractError(f"legacy unit_id has no content mapping: {unit_id}")
        target = target_units[mapping["target_unit_id"]]
        migrated.append(migrate_record(record, evidence_profile=target["evidence_profile"], target_unit_id=target["unit_id"]))
    unused = sorted(set(mappings) - seen)
    if unused:
        raise ContractError(f"unit mappings have no legacy record: {', '.join(unused)}")
    return {
        "schema_version": 3,
        "mode": "preview",
        "target_curriculum": curriculum,
        "unit_mappings": unit_mappings,
        "records": migrated,
        "rebuild_base": True,
        "dual_write": False,
    }

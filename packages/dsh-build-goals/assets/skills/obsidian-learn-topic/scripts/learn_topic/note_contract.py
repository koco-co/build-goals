from __future__ import annotations

import re
from pathlib import PurePosixPath
import json
from datetime import date
from typing import Any
from urllib.parse import urlparse

from .curriculum import ContractError, EVIDENCE_PROFILES
from .learning_state import can_graduate, normalize_learning_state
from .evidence_verification import match_record_evidence
from .safety import validate_persisted_value


KNOWLEDGE_REQUIRED = {
    "title", "tags", "date", "updated", "status", "category", "record_type",
    "document_type", "roadmap_topic", "roadmap_root", "learning_goal", "unit_id",
    "learning_outcome", "knowledge_ownership", "hard_prerequisites", "assessment_method",
    "evidence_profile", "evidence_note", "stage_title", "stage_order", "lesson_order",
    "verified_at", "version_scope", "sources", "coverage_status",
}
TYPE_SECTIONS = {
    "教程": ("贯穿案例", "为什么这样做", "边界、失败表现与排错", "独立练习"),
    "原理解释": ("核心问题", "心智模型", "工作机制", "错误心智模型", "新场景分析"),
    "操作指南": ("适用条件", "操作前检查", "操作步骤", "成功验证", "不适用场景"),
    "参考资料": ("适用范围", "速查索引", "参数与行为", "返回值与失败表现", "兼容性"),
}
LEARNING_RECORD_REQUIRED = {
    "title", "tags", "date", "updated", "status", "category", "record_type",
    "schema_version", "roadmap_topic", "roadmap_root", "learning_goal", "unit_id",
    "content_note", "stage_title", "stage_order", "lesson_order", "progress_status",
    "mastery_status", "evidence_profile", "mastery_evidence", "version_scope",
}
CURRICULUM_MAP_REQUIRED = {
    "title", "tags", "date", "updated", "status", "category", "record_type",
    "schema_version", "roadmap_topic", "roadmap_kind", "roadmap_root", "roadmap_status",
    "learning_goal", "stage_title", "stage_order", "lesson_order", "version_baseline",
    "version_scope", "source_checked_at", "upstream_status", "verified_at", "sources",
}


def parse_frontmatter(note: str) -> dict[str, Any]:
    match = re.match(r"\A---\n(.*?)\n---\n", note, re.DOTALL)
    if not match:
        raise ContractError("note must start with YAML frontmatter")
    lines = match.group(1).splitlines()
    values: dict[str, Any] = {}

    def scalar(raw: str) -> Any:
        raw = raw.strip()
        if not raw:
            return None
        if raw in {"[]", "{}"}:
            return json.loads(raw)
        if raw.casefold() in {"true", "false"}:
            return raw.casefold() == "true"
        if raw.casefold() in {"null", "none", "~"}:
            return None
        if re.fullmatch(r"-?\d+", raw):
            return int(raw)
        if raw.startswith('"') and raw.endswith('"'):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw[1:-1]
        if raw.startswith("'") and raw.endswith("'"):
            return raw[1:-1]
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            return [] if not inner else [scalar(item) for item in inner.split(",")]
        return raw

    index = 0
    while index < len(lines):
        line = lines[index]
        if not line or line[0].isspace() or ":" not in line:
            index += 1
            continue
        key, raw = line.split(":", 1)
        key = key.strip(); raw = raw.strip()
        if raw:
            values[key] = scalar(raw)
            index += 1
            continue
        block = []
        cursor = index + 1
        while cursor < len(lines) and (not lines[cursor] or lines[cursor][0].isspace()):
            if lines[cursor].strip():
                block.append(lines[cursor])
            cursor += 1
        if block and block[0].lstrip().startswith("- "):
            items: list[Any] = []
            current: dict[str, Any] | None = None
            for block_line in block:
                stripped = block_line.strip()
                if stripped.startswith("- "):
                    item = stripped[2:].strip()
                    if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:(?:\s|$)", item):
                        item_key, item_value = item.split(":", 1)
                        current = {item_key.strip(): scalar(item_value)}
                        items.append(current)
                    else:
                        current = None
                        items.append(scalar(item))
                elif current is not None and ":" in stripped:
                    item_key, item_value = stripped.split(":", 1)
                    current[item_key.strip()] = scalar(item_value)
                else:
                    raise ContractError(f"unsupported YAML block for {key}")
            values[key] = items
        elif block:
            mapping: dict[str, Any] = {}
            for block_line in block:
                stripped = block_line.strip()
                if ":" not in stripped:
                    raise ContractError(f"unsupported YAML mapping for {key}")
                item_key, item_value = stripped.split(":", 1)
                mapping[item_key.strip()] = scalar(item_value)
            values[key] = mapping
        else:
            values[key] = None
        index = cursor
    return values


def validate_sources(value: Any, label: str) -> None:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{label} sources must be non-empty")
    for index, source in enumerate(value):
        if isinstance(source, str):
            url = source
        elif isinstance(source, dict) and set(source) == {"title", "url", "verified_at"}:
            if not isinstance(source["title"], str) or not source["title"].strip():
                raise ContractError(f"{label} sources[{index}].title is invalid")
            try:
                date.fromisoformat(str(source["verified_at"]))
            except ValueError as error:
                raise ContractError(f"{label} sources[{index}].verified_at must be an ISO date") from error
            url = source["url"]
        else:
            raise ContractError(f"{label} sources[{index}] must be an HTTPS URL or a verified source object")
        if not isinstance(url, str):
            raise ContractError(f"{label} sources[{index}].url is invalid")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ContractError(f"{label} sources[{index}] must use a public HTTPS URL")


def without_fenced_code(markdown: str) -> str:
    lines = []
    fence: tuple[str, int] | None = None
    for line in markdown.splitlines():
        if fence is None:
            opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
            if opening:
                marker = opening.group(1)
                if marker[0] == "`" and "`" in opening.group(2):
                    lines.append(line)
                    continue
                fence = (marker[0], len(marker))
                continue
            lines.append(line)
            continue
        character, minimum = fence
        if re.fullmatch(rf" {{0,3}}{re.escape(character)}{{{minimum},}}[ \t]*", line):
            fence = None
    if fence is not None:
        raise ContractError("knowledge note contains an unclosed fenced code block")
    return "\n".join(lines)


def _section_content(note: str, heading: str, *, allow_table: bool = False) -> str:
    match = re.search(rf"(?ms)^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", note)
    if not match:
        raise ContractError(f"knowledge note is missing section: {heading}")
    content = re.sub(r"[`#>*_|\-]", " ", match.group(1))
    content = re.sub(r"\s+", " ", content).strip()
    if len(content) < 20:
        raise ContractError(f"knowledge note section is not substantive: {heading}")
    substantive_lines = [
        line.strip() for line in match.group(1).splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "- ", "* ", ">", "```"))
        and (allow_table or not line.lstrip().startswith("|"))
    ]
    if not any(len(line) >= 20 for line in substantive_lines):
        raise ContractError(f"knowledge note section is only a heading, list, or placeholder: {heading}")
    return content


def validate_knowledge_note(note: str) -> dict[str, Any]:
    if re.search(r"\{\{[^{}]+\}\}", note):
        raise ContractError("knowledge note contains unresolved placeholders")
    values = parse_frontmatter(note)
    missing = sorted(field for field in KNOWLEDGE_REQUIRED if field not in values or values[field] is None or values[field] == "")
    if missing:
        raise ContractError(f"knowledge note is missing required properties: {', '.join(missing)}")
    if values.get("record_type") != "knowledge-note" or values.get("document_type") not in TYPE_SECTIONS:
        raise ContractError("knowledge note record_type or document_type is invalid")
    if not isinstance(values.get("tags"), list) or not values["tags"]:
        raise ContractError("knowledge note tags must be non-empty")
    validate_sources(values.get("sources"), "knowledge note")
    if not isinstance(values.get("knowledge_ownership"), list) or not values["knowledge_ownership"]:
        raise ContractError("knowledge note knowledge_ownership must be non-empty")
    if not isinstance(values.get("hard_prerequisites"), list):
        raise ContractError("knowledge note hard_prerequisites must be an array")
    body = note.split("\n---\n", 1)[1] if "\n---\n" in note else ""
    body = without_fenced_code(body)
    meaningful = re.sub(r"[`#>*_|\-]", " ", body)
    meaningful = re.sub(r"\s+", " ", meaningful).strip()
    if len(meaningful) < 240:
        raise ContractError("knowledge note body is not substantive")
    for heading in TYPE_SECTIONS[values["document_type"]]:
        _section_content(body, heading, allow_table=values["document_type"] == "参考资料")
    return values


def validate_curriculum_map_properties(properties: dict[str, Any], plan: dict[str, Any]) -> None:
    missing = sorted(field for field in CURRICULUM_MAP_REQUIRED if field not in properties or properties[field] is None or properties[field] == "")
    if missing:
        raise ContractError(f"curriculum-map is missing required properties: {', '.join(missing)}")
    if not isinstance(properties.get("tags"), list) or not properties["tags"]:
        raise ContractError("curriculum-map tags must be non-empty")
    validate_sources(properties.get("sources"), "curriculum-map")
    expected = {
        "record_type": "curriculum-map", "schema_version": 3,
        "roadmap_kind": plan["roadmap_kind"], "roadmap_root": plan["roadmap_root"],
        "roadmap_topic": plan["topic"], "learning_goal": plan["learning_goal"],
        "version_baseline": plan["version_baseline"], "source_checked_at": plan["source_checked_at"],
    }
    for field, value in expected.items():
        if properties.get(field) != value:
            raise ContractError(f"curriculum-map {field} does not match the machine contract")
    if plan["roadmap_kind"] != "repository":
        return
    repository = plan["repository"]
    repository_projection = {
        "repository_provider": repository["provider"], "repository_name": repository["name"],
        "repository_url": repository["url"], "repository_default_branch": repository["default_branch"],
        "repository_target_ref": repository["target_ref"], "repository_commit": repository["commit"],
        "repository_license_spdx": repository["license_spdx"], "repository_verified_at": repository["verified_at"],
        "repository_scope": repository["scope"], "core_slice": repository["core_slice"],
        "upstream_checked_at": repository["upstream_checked_at"], "upstream_status": repository["upstream_status"],
        "graduation_status": repository["graduation_status"],
    }
    for field, value in repository_projection.items():
        if properties.get(field) != value:
            raise ContractError(f"curriculum-map {field} does not match repository authority")


def validate_repository_visible_projection(note: str, plan: dict[str, Any]) -> None:
    if plan["roadmap_kind"] != "repository":
        return
    repository = plan["repository"]
    required_lines = (
        f"- Provider：`{repository['provider']}`",
        f"- 仓库：`{repository['name']}`",
        f"- Canonical URL：`{repository['url']}`",
        f"- 默认分支：`{repository['default_branch']}`",
        f"- 目标 ref：`{repository['target_ref']}`",
        f"- Commit：`{repository['commit']}`",
        f"- 许可证：`{repository['license_spdx']}`",
        f"- 学习范围：{repository['scope']}",
        f"- 核心切片：{repository['core_slice']}",
        f"- 上游检查：`{repository['upstream_checked_at']}`",
        f"- 上游状态：`{repository['upstream_status']}`",
        f"- 仓库核验：`{repository['verified_at']}`",
        f"- 毕业状态：`{repository['graduation_status']}`",
    )
    if any(note.count(line) != 1 for line in required_lines):
        raise ContractError("repository visible baseline does not match the machine contract")


def validate_learning_record(note: str, *, trusted_receipts: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    values = parse_frontmatter(note)
    missing = sorted(field for field in LEARNING_RECORD_REQUIRED if field not in values or values[field] is None or values[field] == "")
    if missing:
        raise ContractError(f"learning record is missing required properties: {', '.join(missing)}")
    if not isinstance(values.get("tags"), list) or not values["tags"]:
        raise ContractError("learning record tags must be non-empty")
    if values.get("record_type") != "learning-evidence":
        raise ContractError("learning record must set record_type: learning-evidence")
    state = normalize_learning_state(values)
    if values.get("evidence_profile") not in EVIDENCE_PROFILES:
        raise ContractError("learning record evidence_profile is invalid")
    if "mastery_score" in values or "learning_status" in values:
        raise ContractError("legacy learning state fields are forbidden in v3")
    evidence = values.get("mastery_evidence")
    if not isinstance(evidence, list):
        raise ContractError("mastery_evidence must be an array")
    evidence_ids: set[str] = set()
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise ContractError(f"mastery_evidence[{index}] must be an object")
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip() or evidence_id in evidence_ids:
            raise ContractError(f"mastery_evidence[{index}].evidence_id is missing or duplicate")
        evidence_ids.add(evidence_id)
        if item.get("evidence_profile") != values.get("evidence_profile"):
            raise ContractError(f"mastery_evidence[{index}] profile does not match the learning record")
        if item.get("origin") not in {"host-tool", "user-ci", "user-supplied"} or not isinstance(item.get("verified"), bool):
            raise ContractError(f"mastery_evidence[{index}] origin or verified flag is invalid")
        for field in ("summary", "verification_ref", "observed_at"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ContractError(f"mastery_evidence[{index}].{field} is required")
        validate_persisted_value(item, f"mastery_evidence[{index}]")
    if state["mastery_status"] != "未证明" and not can_graduate(values):
        raise ContractError("supported mastery status requires matching verified evidence")
    if state["mastery_status"] != "未证明":
        if not trusted_receipts:
            raise ContractError("mastery promotion requires signed verification receipts")
        matched_evidence = []
        for item in evidence:
            receipt = trusted_receipts.get(str(item.get("evidence_id")))
            if receipt is not None:
                match_record_evidence(item, receipt)
                matched_evidence.append(item)
        trusted_record = {**values, "mastery_evidence": matched_evidence}
        if not can_graduate(trusted_record):
            raise ContractError("mastery promotion has no sufficient evidence bound to a signed receipt")
    return values


def validate_planned_note(
    properties: dict[str, Any],
    *,
    target_path: str,
    unit: dict[str, Any],
    roadmap_root: str,
    records_directory: str,
    roadmap_topic: str,
    learning_goal: str,
    version_scope: str,
    paired_evidence_path: str,
) -> None:
    record_type = properties.get("record_type")
    if properties.get("unit_id") != unit.get("unit_id"):
        raise ContractError("note unit_id does not match curriculum")
    if properties.get("evidence_profile") != unit.get("evidence_profile"):
        raise ContractError("note evidence_profile does not match curriculum")
    if properties.get("roadmap_root") != roadmap_root:
        raise ContractError("note roadmap_root does not match curriculum")
    if properties.get("roadmap_topic") != roadmap_topic or properties.get("learning_goal") != learning_goal:
        raise ContractError("note topic or learning_goal does not match curriculum")
    if properties.get("version_scope") != version_scope:
        raise ContractError("note version_scope does not match curriculum baseline")
    lesson_match = re.match(r"^§(\d{2})-", PurePosixPath(target_path).name)
    if not lesson_match or properties.get("lesson_order") != int(lesson_match.group(1)):
        raise ContractError("note lesson_order does not match its filename")
    if record_type == "knowledge-note":
        if target_path != f"{roadmap_root}/{unit['note_path']}":
            raise ContractError("knowledge note path does not match curriculum")
        for property_name, unit_name in (
            ("title", "title"),
            ("document_type", "document_type"),
            ("learning_outcome", "learning_outcome"),
            ("assessment_method", "assessment"),
        ):
            if properties.get(property_name) != unit.get(unit_name):
                raise ContractError(f"knowledge note {property_name} does not match curriculum")
        if properties.get("knowledge_ownership") != unit.get("knowledge_ownership"):
            raise ContractError("knowledge note knowledge_ownership does not match curriculum")
        if properties.get("hard_prerequisites") != unit.get("prerequisites"):
            raise ContractError("knowledge note hard_prerequisites does not match curriculum")
        stage = unit["stage"]
        if properties.get("stage_title") != stage or properties.get("stage_order") != int(stage.split("-", 1)[0]):
            raise ContractError("knowledge note stage fields do not match curriculum")
        expected_evidence = f"[[{PurePosixPath(paired_evidence_path).with_suffix('').as_posix()}]]"
        if properties.get("evidence_note") != expected_evidence:
            raise ContractError("knowledge note evidence_note does not link the paired learning record")
        return
    if record_type == "learning-evidence":
        if PurePosixPath(target_path).parent.as_posix() != records_directory:
            raise ContractError("learning evidence must be directly inside the records directory")
        content_note = str(properties.get("content_note", ""))
        expected_stem = f"{roadmap_root}/{PurePosixPath(unit['note_path']).with_suffix('').as_posix()}"
        if content_note != f"[[{expected_stem}]]":
            raise ContractError("learning evidence content_note does not link the planned knowledge note")
        records_stage = PurePosixPath(records_directory).name
        if properties.get("stage_title") != records_stage or properties.get("stage_order") != int(records_stage.split("-", 1)[0]):
            raise ContractError("learning evidence stage fields do not match the records directory")
        if target_path != paired_evidence_path:
            raise ContractError("learning evidence path does not match the paired evidence path")
        if properties.get("title") != f"{unit['title']}学习记录":
            raise ContractError("learning evidence title does not match curriculum")
        return
    raise ContractError("planned note must be knowledge-note or learning-evidence")

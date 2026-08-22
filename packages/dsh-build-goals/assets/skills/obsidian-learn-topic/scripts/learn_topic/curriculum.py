from __future__ import annotations

import json
import re
from datetime import date
from pathlib import PurePosixPath
from typing import Any

from .spdx_license_ids import SPDX_LICENSE_IDS


DOCUMENT_TYPES = {"教程", "原理解释", "操作指南", "参考资料"}
EVIDENCE_PROFILES = {
    "concept-explanation", "tutorial-reproduction", "task-operation",
    "reference-application", "code-practice", "repository-reading",
    "repository-patch", "custom",
}
UNIT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
DIRECTORY = re.compile(r"^(\d{2})-([^/\\\x00-\x1f\x7f]+)$")
START = "<!-- learn-topic-curriculum:start -->"
END = "<!-- learn-topic-curriculum:end -->"
REPOSITORY_DIRECTORIES = [
    ("01-项目概述", "overview"), ("02-运行与测试基线", "formal"),
    ("03-架构与模块地图", "formal"), ("04-核心调用链", "formal"),
    ("05-测试与质量体系", "formal"), ("06-Issue与PR考古", "formal"),
    ("07-最小修复实践", "formal"), ("08-深入与拓展", "extension"),
    ("09-复习与贡献准备", "review"), ("10-学习记录", "records"),
    ("99-assets", "assets"),
]
UPSTREAM_STATES = {"unchanged", "fixed-baseline", "changed", "blocked", "archived"}
GRADUATION_STATES = {"pending-evidence", "blocked", "passed"}
SPDX_LICENSE_VALUES = SPDX_LICENSE_IDS | {"NONE", "NOASSERTION"}


class ContractError(RuntimeError):
    pass


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ContractError(f"{label} must be a normalized non-empty string")
    return value


def _path(value: Any, label: str) -> str:
    value = text(value, label)
    path = PurePosixPath(value)
    if value.startswith("/") or "\\" in value or any(part in {"", ".", ".."} for part in path.parts):
        raise ContractError(f"{label} must be a safe route-relative path")
    if not all(DIRECTORY.fullmatch(part) for part in path.parts[:-1]) or not re.match(r"^§\d{2}-.*\.md$", path.name):
        raise ContractError(f"{label} must use numbered route and note names")
    if path.parts[0].endswith("学习记录") or path.parts[0] == "99-assets":
        raise ContractError(f"{label} cannot be in records or assets")
    return path.as_posix()


def _root(value: Any) -> str:
    value = text(value, "roadmap_root")
    path = PurePosixPath(value)
    if value.startswith("/") or "\\" in value or any(part in {"", ".", "..", ".obsidian"} for part in path.parts):
        raise ContractError("roadmap_root must be a safe Vault-relative path")
    return path.as_posix()


def validate_directories(value: Any, *, roadmap_kind: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) < 3:
        raise ContractError("directories must include learning stages, records, and 99-assets")
    normalized = []
    seen_numbers: set[int] = set()
    allowed_roles = {"overview", "formal", "extension", "review", "records", "assets"}
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ContractError(f"directories[{index}] must be an object")
        name = text(item.get("name"), f"directories[{index}].name")
        role = text(item.get("role"), f"directories[{index}].role")
        match = DIRECTORY.fullmatch(name)
        if not match or role not in allowed_roles:
            raise ContractError(f"directories[{index}] has an invalid name or role")
        number = int(match.group(1))
        if number in seen_numbers:
            raise ContractError(f"duplicate directory number: {number:02d}")
        seen_numbers.add(number)
        normalized.append({"name": name, "role": role})
    if roadmap_kind == "repository":
        if [(item["name"], item["role"]) for item in normalized] != REPOSITORY_DIRECTORIES:
            raise ContractError("repository route must use the fixed 01-10 and 99 outer directories")
        return normalized
    ordinary = normalized[:-1]
    if normalized[-1] != {"name": "99-assets", "role": "assets"}:
        raise ContractError("the final directory must be 99-assets")
    if [int(DIRECTORY.fullmatch(item["name"]).group(1)) for item in ordinary] != list(range(1, len(ordinary) + 1)):
        raise ContractError("topic route directories must be continuously numbered from 01")
    if ordinary[0]["role"] != "overview" or "概述" not in ordinary[0]["name"]:
        raise ContractError("the first topic directory must be the topic overview")
    records = [item for item in ordinary if item["role"] == "records"]
    if len(records) != 1 or records[0] != ordinary[-1] or not records[0]["name"].endswith("学习记录"):
        raise ContractError("the records directory must be the final continuously numbered topic stage")
    reviews = [item for item in ordinary if item["role"] == "review"]
    if len(reviews) != 1 or "复习与综合应用" not in reviews[0]["name"]:
        raise ContractError("topic route requires one review-and-integration directory")
    return normalized


def validate_repository(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ContractError("repository curriculum requires repository identity")
    required = (
        "provider", "name", "url", "default_branch", "target_ref", "commit",
        "license_spdx", "verified_at", "scope", "core_slice", "upstream_checked_at",
        "upstream_status", "graduation_status",
    )
    result = {key: text(value.get(key), f"repository.{key}") for key in required}
    if result["provider"] != "github" or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", result["name"]):
        raise ContractError("repository.name must be owner/repo")
    if result["url"] != f"https://github.com/{result['name']}":
        raise ContractError("repository.url must be the canonical GitHub URL")
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", result["commit"]):
        raise ContractError("repository.commit must be a full lowercase commit")
    ref_forbidden = re.compile(r"(?:\.\.|//|@\{|[ ~^:?*\[\\])")
    branch = result["default_branch"]
    if (
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", branch)
        or ref_forbidden.search(branch) or branch.endswith(("/", ".", ".lock"))
        or any(part.startswith(".") or part.endswith(".lock") for part in branch.split("/"))
    ):
        raise ContractError("repository.default_branch is not a safe branch name")
    if not (
        re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", result["target_ref"])
        or re.fullmatch(r"refs/(?:heads|tags)/[A-Za-z0-9][A-Za-z0-9._/-]*", result["target_ref"])
    ) or ref_forbidden.search(result["target_ref"]):
        raise ContractError("repository.target_ref must be a full commit or safe canonical ref")
    if result["license_spdx"] not in SPDX_LICENSE_VALUES:
        raise ContractError("repository.license_spdx must be a supported SPDX license identifier")
    for field in ("verified_at", "upstream_checked_at"):
        try:
            date.fromisoformat(result[field])
        except ValueError as error:
            raise ContractError(f"repository.{field} must be an ISO date") from error
    if result["upstream_status"] not in UPSTREAM_STATES:
        raise ContractError("repository.upstream_status is invalid")
    if result["graduation_status"] not in GRADUATION_STATES:
        raise ContractError("repository.graduation_status is invalid")
    return result


def validate_subdirectories(value: Any, *, directories: list[dict[str, str]]) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ContractError("subdirectories must be an array")
    top = {item["name"]: item for item in directories if item["role"] not in {"records", "assets"}}
    declared: set[str] = set()
    normalized = []
    siblings: dict[str, list[int]] = {}
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ContractError(f"subdirectories[{index}] must be an object")
        path_value = text(item.get("path"), f"subdirectories[{index}].path")
        path = PurePosixPath(path_value)
        if path_value.startswith("/") or "\\" in path_value or len(path.parts) < 2 or any(not DIRECTORY.fullmatch(part) for part in path.parts):
            raise ContractError(f"subdirectories[{index}].path must use numbered route-relative directories")
        if path.parts[0] not in top:
            raise ContractError(f"subdirectories[{index}] is outside a learning stage")
        parent = PurePosixPath(*path.parts[:-1]).as_posix()
        if len(path.parts) > 2 and parent not in declared:
            raise ContractError(f"subdirectories[{index}] parent must be declared first")
        if path_value in declared:
            raise ContractError(f"duplicate subdirectory: {path_value}")
        role = text(item.get("role"), f"subdirectories[{index}].role")
        if role not in {"section", "practice", "reference"}:
            raise ContractError(f"subdirectories[{index}].role is invalid")
        declared.add(path_value)
        number = int(DIRECTORY.fullmatch(path.name).group(1))
        siblings.setdefault(parent, []).append(number)
        normalized.append({"path": path_value, "role": role})
    for parent, numbers in siblings.items():
        if numbers != list(range(1, len(numbers) + 1)):
            raise ContractError(f"subdirectories below {parent} must be declared continuously from 01")
    return normalized


def validate_curriculum(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != 3:
        raise ContractError("curriculum schema_version must be 3")
    roadmap_kind = value.get("roadmap_kind")
    if roadmap_kind not in {"topic", "repository"}:
        raise ContractError("roadmap_kind must be topic or repository")
    roadmap_root = _root(value.get("roadmap_root"))
    directories = validate_directories(value.get("directories"), roadmap_kind=roadmap_kind)
    subdirectories = validate_subdirectories(value.get("subdirectories", []), directories=directories)
    records_directory = next(item["name"] for item in directories if item["role"] == "records")
    if value.get("records_directory") != records_directory:
        raise ContractError("records_directory must match the unique records directory")
    stages = {item["name"] for item in directories if item["role"] not in {"records", "assets"}}
    declared_subdirectories = {item["path"] for item in subdirectories}
    units = value.get("units")
    if not isinstance(units, list) or not units:
        raise ContractError("curriculum units must be a non-empty array")
    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    paths: set[str] = set()
    owners: dict[str, str] = {}
    required = {
        "unit_id", "stage", "note_path", "title", "document_type",
        "learning_outcome", "prerequisites", "knowledge_ownership",
        "evidence_profile", "assessment",
    }
    for index, raw in enumerate(units):
        if not isinstance(raw, dict) or not required.issubset(raw):
            raise ContractError(f"units[{index}] is missing required fields")
        unit_id = text(raw["unit_id"], f"units[{index}].unit_id")
        if not UNIT_ID.fullmatch(unit_id) or unit_id in ids:
            raise ContractError(f"units[{index}].unit_id is invalid or duplicate")
        ids.add(unit_id)
        path = _path(raw["note_path"], f"units[{index}].note_path")
        if path in paths:
            raise ContractError(f"duplicate note_path: {path}")
        paths.add(path)
        stage = text(raw["stage"], f"units[{index}].stage")
        if stage != PurePosixPath(path).parts[0]:
            raise ContractError(f"units[{index}].stage must match note_path")
        if stage not in stages:
            raise ContractError(f"units[{index}].stage is not present in directories")
        note_parent = PurePosixPath(path).parent.as_posix()
        if len(PurePosixPath(path).parts) > 2 and note_parent not in declared_subdirectories:
            raise ContractError(f"units[{index}].note_path uses an undeclared subdirectory")
        document_type = text(raw["document_type"], f"units[{index}].document_type")
        if document_type not in DOCUMENT_TYPES:
            raise ContractError(f"units[{index}].document_type is unsupported")
        profile = text(raw["evidence_profile"], f"units[{index}].evidence_profile")
        if profile not in EVIDENCE_PROFILES:
            raise ContractError(f"units[{index}].evidence_profile is unsupported")
        prerequisites = raw["prerequisites"]
        ownership = raw["knowledge_ownership"]
        if not isinstance(prerequisites, list) or not all(isinstance(item, str) for item in prerequisites):
            raise ContractError(f"units[{index}].prerequisites must be an array of ids")
        if not isinstance(ownership, list) or not ownership:
            raise ContractError(f"units[{index}].knowledge_ownership must be non-empty")
        for point in ownership:
            point = text(point, f"units[{index}].knowledge_ownership")
            if point in owners:
                raise ContractError(f"knowledge ownership {point} is duplicated by {owners[point]} and {unit_id}")
            owners[point] = unit_id
        normalized.append({
            "unit_id": unit_id, "stage": stage, "note_path": path,
            "title": text(raw["title"], f"units[{index}].title"),
            "document_type": document_type,
            "learning_outcome": text(raw["learning_outcome"], f"units[{index}].learning_outcome"),
            "prerequisites": prerequisites, "knowledge_ownership": ownership,
            "evidence_profile": profile,
            "assessment": text(raw["assessment"], f"units[{index}].assessment"),
        })
    order = {unit["unit_id"]: index for index, unit in enumerate(normalized)}
    for unit in normalized:
        for dependency in unit["prerequisites"]:
            if dependency not in order:
                raise ContractError(f"unknown prerequisite {dependency}")
            if order[dependency] >= order[unit["unit_id"]]:
                raise ContractError(f"prerequisite {dependency} must precede {unit['unit_id']}")
    source_checked_at = text(value.get("source_checked_at"), "source_checked_at")
    try:
        date.fromisoformat(source_checked_at)
    except ValueError as error:
        raise ContractError("source_checked_at must be an ISO date") from error
    normalized_plan = {
        "schema_version": 3,
        "roadmap_kind": roadmap_kind,
        "roadmap_root": roadmap_root,
        "directories": directories,
        "subdirectories": subdirectories,
        "records_directory": records_directory,
        "topic": text(value.get("topic"), "topic"),
        "learning_goal": text(value.get("learning_goal"), "learning_goal"),
        "version_baseline": text(value.get("version_baseline"), "version_baseline"),
        "source_checked_at": source_checked_at,
        "units": normalized,
    }
    if roadmap_kind == "repository":
        normalized_plan["repository"] = validate_repository(value.get("repository"))
    return normalized_plan


def extract_curriculum(note: str) -> dict[str, Any]:
    if note.count(START) != 1 or note.count(END) != 1:
        raise ContractError("route note must contain exactly one curriculum contract")
    body = note.split(START, 1)[1].split(END, 1)[0].strip()
    match = re.fullmatch(r"```json\s*(\{.*\})\s*```", body, re.DOTALL)
    if not match:
        raise ContractError("curriculum contract must be one fenced JSON object")
    try:
        raw = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise ContractError(f"curriculum JSON is invalid: {error}") from error
    return validate_curriculum(raw)


def render_curriculum(plan: dict[str, Any]) -> str:
    normalized = validate_curriculum(plan)
    return f"{START}\n```json\n{json.dumps(normalized, ensure_ascii=False, indent=2)}\n```\n{END}"


def _section(note: str, heading: str) -> str:
    pattern = rf"(?ms)^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)"
    matches = re.findall(pattern, note)
    if len(matches) != 1:
        raise ContractError(f"route note must contain exactly one {heading} section")
    return matches[0]


def _table_rows(section: str, columns: int, label: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped[1:-1].split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    if not rows or len(rows[0]) != columns:
        raise ContractError(f"{label} table header is invalid")
    for row in rows[1:]:
        if len(row) != columns:
            raise ContractError(f"{label} table has an invalid column count")
    return rows[1:]


def validate_visible_projection(note: str, plan: dict[str, Any]) -> None:
    plan = validate_curriculum(plan)
    unit_rows = _table_rows(_section(note, "单元目录"), 7, "unit directory")
    if len(unit_rows) != len(plan["units"]):
        raise ContractError("visible unit directory row count does not match curriculum")
    for row, unit in zip(unit_rows, plan["units"]):
        prerequisites = "、".join(f"`{item}`" for item in unit["prerequisites"]) or "无"
        expected = [
            f"`{unit['unit_id']}`", f"`{unit['note_path']}`", unit["document_type"],
            unit["learning_outcome"], prerequisites, f"`{unit['evidence_profile']}`", unit["assessment"],
        ]
        if row != expected:
            raise ContractError(f"visible unit row drifted for {unit['unit_id']}")
    ownership_rows = _table_rows(_section(note, "知识点唯一归属"), 2, "knowledge ownership")
    expected_ownership = [
        [f"`{point}`", f"`{unit['unit_id']}`"]
        for unit in plan["units"] for point in unit["knowledge_ownership"]
    ]
    if ownership_rows != expected_ownership:
        raise ContractError("visible knowledge ownership does not match curriculum")
    graph = _section(note, "知识依赖图")
    units = set(re.findall(r"(?m)^\s*%% unit: ([A-Za-z0-9_.-]+)\s*$", graph))
    dependencies = set(re.findall(r"(?m)^\s*%% dependency: ([A-Za-z0-9_.-]+) -> ([A-Za-z0-9_.-]+)\s*$", graph))
    expected_units = {unit["unit_id"] for unit in plan["units"]}
    expected_dependencies = {(dependency, unit["unit_id"]) for unit in plan["units"] for dependency in unit["prerequisites"]}
    if units != expected_units or dependencies != expected_dependencies:
        raise ContractError("visible dependency graph does not match curriculum")

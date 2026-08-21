#!/usr/bin/env python3
"""Safely scaffold, write, validate, renumber, and acceptance-test learning roadmaps.

Vault mutations are performed exclusively through the Obsidian CLI.  This
driver intentionally treats CLI exit codes as insufficient evidence because
Obsidian 1.12 can report command failures with exit status zero.
"""

from __future__ import annotations

import argparse
import base64
from datetime import date
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import uuid
from typing import Any, Iterable


SENTINEL = "LEARN_TOPIC_JSON:"
PLACEHOLDER_RE = re.compile(
    r"\{\{(?:[A-Z][A-Z0-9_]*|"
    r"本单元最重要的结论。|"
    r"一句话定义主题及其价值。|"
    r"给出类比，并明确不能类推的部分。|"
    r"一句话说明开始学习前必须具备和准备什么。|"
    r"说明需要稳定回忆、迁移和表达的核心能力。)\}\}"
)
NUMBERED_DIRECTORY_RE = re.compile(r"^(0[1-9]|[1-9][0-9])-.+")
NUMBERED_NOTE_RE = re.compile(r"^§(0[1-9]|[1-9][0-9])-.+\.md$")
TAG_SEGMENT_RE = re.compile(
    r"^[A-Za-z_\u3400-\u4dbf\u4e00-\u9fff][A-Za-z0-9_\-\u3400-\u4dbf\u4e00-\u9fff]*$"
)
PROTECTED_ROOTS = {
    ".agents",
    ".claude",
    ".obsidian",
    "koco-co",
    "clippings",
}
PROTECTED_SEGMENTS = {"attachments", "attachment", "附件"}
SHELL_UNSAFE_CHARACTERS = {'"', "`", "$"}
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
GITHUB_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
FULL_COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
CANONICAL_REPOSITORY_REF_RE = re.compile(r"^refs/(?:heads|tags)/[^\s~^:?*\[\\]+$")
REPOSITORY_STAGE_CONTRACT = (
    ("01-项目概述", "overview"),
    ("02-运行与测试基线", "formal"),
    ("03-架构与模块地图", "formal"),
    ("04-核心调用链", "formal"),
    ("05-测试与质量体系", "formal"),
    ("06-Issue与PR考古", "formal"),
    ("07-最小修复实践", "formal"),
    ("08-深入与拓展", "extension"),
    ("09-复习与贡献准备", "review"),
    ("99-assets", "assets"),
)
REPOSITORY_UPSTREAM_STATES = {
    "unchanged",
    "fixed-baseline",
    "changed",
    "blocked",
    "archived",
}


class ContractError(RuntimeError):
    """Raised when an input, CLI result, or postcondition violates the contract."""


def json_report(ok: bool, op: str, **details: Any) -> dict[str, Any]:
    return {"ok": ok, "op": op, **details}


def emit(report: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=stream)


def has_control_characters(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def validate_vault_path(value: Any, *, label: str = "path") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise ContractError(f"{label} must not have leading or trailing whitespace")
    if "\\" in value or has_control_characters(value):
        raise ContractError(f"{label} contains a backslash or control character")
    if any(character in value for character in SHELL_UNSAFE_CHARACTERS):
        raise ContractError(f"{label} contains a shell-unsafe character")
    raw_parts = value.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise ContractError(f"{label} contains an unsafe segment")
    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith("/"):
        raise ContractError(f"{label} must be Vault-relative")
    if value.endswith("/") or "//" in value:
        raise ContractError(f"{label} is not normalized")
    if not path.parts:
        raise ContractError(f"{label} is empty")
    if path.parts[0].casefold() in PROTECTED_ROOTS:
        raise ContractError(f"{label} targets protected root {path.parts[0]}")
    if any(part.casefold() in PROTECTED_SEGMENTS for part in path.parts):
        raise ContractError(f"{label} targets a protected attachment directory")
    return path.as_posix()


def roadmap_base_path(root: str) -> str:
    """Return the canonical Base path for a learning-roadmap root."""
    return f"{root}/{PurePosixPath(root).name}-Roadmap.base"


def ensure_descendant(path: str, root: str, *, label: str) -> None:
    try:
        relative = PurePosixPath(path).relative_to(PurePosixPath(root))
    except ValueError as error:
        raise ContractError(f"{label} must be below the roadmap root") from error
    if not relative.parts:
        raise ContractError(f"{label} must be below the roadmap root")


def ensure_no_placeholders(value: str, *, label: str) -> None:
    match = PLACEHOLDER_RE.search(value)
    if match:
        raise ContractError(f"{label} contains unfilled placeholder {match.group(0)}")


def markdown_frontmatter_lines(content: str, *, label: str) -> list[str]:
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        raise ContractError(f"{label} must start with YAML frontmatter")
    try:
        closing_index = lines.index("---", 1)
    except ValueError as error:
        raise ContractError(f"{label} frontmatter is not closed") from error
    if closing_index == 1:
        raise ContractError(f"{label} frontmatter must not be empty")
    return lines[1:closing_index]


def frontmatter_top_level_raw(
    lines: list[str], *, label: str
) -> dict[str, str | None]:
    """Read simple top-level scalar spellings and reject duplicate keys.

    Obsidian's YAML parser remains the semantic authority before every Vault
    write.  This lightweight pass lets the offline plan loader enforce the
    canonical state gates without importing a second YAML implementation.
    """

    values: dict[str, str | None] = {}
    for line in lines:
        if not line or line[0].isspace():
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*):(?:\s*(.*))?", line)
        if not match:
            continue
        key = match.group(1)
        if key in values:
            raise ContractError(f"{label} contains duplicate frontmatter key: {key}")
        raw_value = match.group(2)
        values[key] = raw_value.strip() if raw_value not in {None, ""} else None
    return values


def frontmatter_list_has_item(lines: list[str], key: str) -> bool:
    prefix = f"{key}:"
    try:
        start = next(index for index, line in enumerate(lines) if line.startswith(prefix))
    except StopIteration:
        return False
    for line in lines[start + 1 :]:
        if line and not line[0].isspace():
            break
        item_match = re.fullmatch(r"\s+-\s+(.+)", line)
        if item_match:
            value = item_match.group(1).strip()
            normalized = frontmatter_scalar(value)
            if normalized is not None and normalized.strip():
                return True
    return False


def frontmatter_scalar(value: str | None) -> str | None:
    if value is None or value in {"null", "~", '""', "''"}:
        return None
    if value.startswith('"') and value.endswith('"'):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value
        return decoded if isinstance(decoded, str) else value
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def require_iso_date(value: str | None, *, label: str) -> None:
    normalized = frontmatter_scalar(value)
    if normalized is None or not ISO_DATE_RE.fullmatch(normalized):
        raise ContractError(f"{label} must be an ISO date in YYYY-MM-DD format")
    try:
        date.fromisoformat(normalized)
    except ValueError as error:
        raise ContractError(f"{label} must be a valid calendar date") from error


def read_json_object(path: str, *, label: str) -> dict[str, Any]:
    file_path = Path(path).expanduser()
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot read {label}: {error}") from error
    if not isinstance(data, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return data


def require_keys(mapping: dict[str, Any], keys: Iterable[str], *, label: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ContractError(f"{label} missing keys: {', '.join(missing)}")


def read_external_content(
    path_value: Any,
    *,
    label: str,
    vault_path: str,
    content_root: Path,
    content_root_label: str = "scaffold spec directory",
    reject_placeholders: bool = True,
) -> str:
    if not isinstance(path_value, str) or not path_value:
        raise ContractError(f"{label} must be a non-empty path")
    content_path = Path(path_value).expanduser()
    if not content_path.is_absolute():
        raise ContractError(f"{label} must be an absolute path outside the Vault")
    if content_path.is_symlink():
        raise ContractError(f"{label} must not be a symbolic link")
    try:
        resolved = content_path.resolve(strict=True)
    except OSError as error:
        raise ContractError(f"cannot resolve {label}: {error}") from error
    if not resolved.is_file():
        raise ContractError(f"{label} is not a regular file")
    try:
        resolved.relative_to(content_root)
    except ValueError as error:
        raise ContractError(f"{label} must stay inside the {content_root_label}") from error
    vault = Path(vault_path).resolve()
    try:
        resolved.relative_to(vault)
    except ValueError:
        pass
    else:
        raise ContractError(f"{label} must be outside the Vault")
    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError as error:
        raise ContractError(f"cannot read {label}: {error}") from error
    if reject_placeholders:
        ensure_no_placeholders(content, label=label)
    return content


def resolve_external_plan_file(
    path_value: Any,
    *,
    label: str,
    vault_path: str,
    content_root: Path,
) -> Path:
    if not isinstance(path_value, str) or not path_value:
        raise ContractError(f"{label} must be a non-empty path")
    candidate = Path(path_value).expanduser()
    if not candidate.is_absolute() or candidate.is_symlink():
        raise ContractError(f"{label} must be an absolute regular file")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise ContractError(f"cannot resolve {label}: {error}") from error
    if not resolved.is_file():
        raise ContractError(f"{label} is not a regular file")
    try:
        resolved.relative_to(content_root)
    except ValueError as error:
        raise ContractError(f"{label} must stay inside the note plan directory") from error
    try:
        resolved.relative_to(Path(vault_path).resolve())
    except ValueError:
        return resolved
    raise ContractError(f"{label} must be outside the Vault")


def normalize_vault_identity(data: dict[str, Any], *, label: str) -> tuple[str, str]:
    require_keys(data, ("vault_name", "vault_path"), label=label)
    vault_name = data["vault_name"]
    vault_path = data["vault_path"]
    if not isinstance(vault_name, str) or not vault_name.strip():
        raise ContractError(f"{label}.vault_name must be a non-empty string")
    if vault_name != vault_name.strip() or has_control_characters(vault_name):
        raise ContractError(f"{label}.vault_name is not normalized")
    if any(character in vault_name for character in SHELL_UNSAFE_CHARACTERS):
        raise ContractError(f"{label}.vault_name contains a shell-unsafe character")
    if not isinstance(vault_path, str) or not Path(vault_path).is_absolute():
        raise ContractError(f"{label}.vault_path must be absolute")
    return vault_name, str(Path(vault_path).resolve())


def normalize_topic_metadata(raw: dict[str, Any]) -> dict[str, str]:
    topic = raw.get("topic")
    if not isinstance(topic, dict):
        raise ContractError("scaffold spec topic must be an object")
    require_keys(topic, ("display", "path_segment", "tag"), label="topic")
    normalized: dict[str, str] = {}
    for key in ("display", "path_segment", "tag"):
        value = topic[key]
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ContractError(f"topic.{key} must be a normalized non-empty string")
        if has_control_characters(value):
            raise ContractError(f"topic.{key} contains a control character")
        ensure_no_placeholders(value, label=f"topic.{key}")
        normalized[key] = value
    if (
        normalized["path_segment"] in {".", ".."}
        or "/" in normalized["path_segment"]
        or "\\" in normalized["path_segment"]
        or normalized["path_segment"].startswith(".")
        or any(
            character in normalized["path_segment"]
            for character in SHELL_UNSAFE_CHARACTERS
        )
    ):
        raise ContractError("topic.path_segment is not a safe directory segment")
    if not TAG_SEGMENT_RE.fullmatch(normalized["tag"]):
        raise ContractError(
            "topic.tag must be one Obsidian-safe segment beginning with a letter, CJK character or _"
        )
    return normalized


def normalize_repository_metadata(raw: dict[str, Any]) -> dict[str, str]:
    repository = raw.get("repository")
    if not isinstance(repository, dict):
        raise ContractError("repository roadmap requires a repository object")
    required = (
        "provider",
        "name",
        "url",
        "default_branch",
        "target_ref",
        "commit",
        "license_spdx",
        "verified_at",
        "scope",
        "core_slice",
        "upstream_checked_at",
        "upstream_status",
    )
    require_keys(repository, required, label="repository")
    normalized: dict[str, str] = {}
    for key in required:
        value = repository[key]
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ContractError(f"repository.{key} must be a normalized non-empty string")
        if has_control_characters(value):
            raise ContractError(f"repository.{key} contains a control character")
        ensure_no_placeholders(value, label=f"repository.{key}")
        normalized[key] = value
    if normalized["provider"] != "github":
        raise ContractError("repository.provider must be github")
    if not GITHUB_REPOSITORY_RE.fullmatch(normalized["name"]):
        raise ContractError("repository.name must use canonical owner/repo form")
    expected_url = f"https://github.com/{normalized['name']}"
    if normalized["url"] != expected_url:
        raise ContractError(f"repository.url must be {expected_url}")
    if not FULL_COMMIT_RE.fullmatch(normalized["commit"]):
        raise ContractError("repository.commit must be a full lowercase commit object id")
    target_ref = normalized["target_ref"]
    if not (
        FULL_COMMIT_RE.fullmatch(target_ref)
        or (
            CANONICAL_REPOSITORY_REF_RE.fullmatch(target_ref)
            and ".." not in target_ref
            and "//" not in target_ref
            and "@{" not in target_ref
            and not target_ref.endswith(("/", ".", ".lock"))
        )
    ):
        raise ContractError(
            "repository.target_ref must be a full commit or canonical refs/heads/... or refs/tags/..."
        )
    require_iso_date(normalized["verified_at"], label="repository.verified_at")
    require_iso_date(
        normalized["upstream_checked_at"], label="repository.upstream_checked_at"
    )
    if normalized["upstream_status"] not in REPOSITORY_UPSTREAM_STATES:
        raise ContractError(
            "repository.upstream_status must be unchanged, fixed-baseline, changed, blocked, or archived"
        )
    return normalized


def load_scaffold_spec(path: str, *, actual_vault_path: str | None = None) -> dict[str, Any]:
    spec_path = Path(path).expanduser()
    if spec_path.is_symlink():
        raise ContractError("scaffold spec must not be a symbolic link")
    try:
        resolved_spec_path = spec_path.resolve(strict=True)
    except OSError as error:
        raise ContractError(f"cannot resolve scaffold spec: {error}") from error
    content_root = resolved_spec_path.parent
    raw = read_json_object(path, label="scaffold spec")
    vault_name, vault_path = normalize_vault_identity(raw, label="scaffold spec")
    if actual_vault_path and Path(vault_path) != Path(actual_vault_path).resolve():
        raise ContractError("scaffold spec vault_path does not match the selected Vault")
    require_keys(
        raw,
        ("topic", "learning_goal", "version_scope", "root", "base", "directories", "notes"),
        label="scaffold spec",
    )
    topic = normalize_topic_metadata(raw)
    roadmap_kind = raw.get("roadmap_kind", "topic")
    if roadmap_kind not in {"topic", "repository"}:
        raise ContractError("roadmap_kind must be topic or repository")
    repository = (
        normalize_repository_metadata(raw) if roadmap_kind == "repository" else None
    )
    try:
        resolved_spec_path.relative_to(Path(vault_path).resolve())
    except ValueError:
        pass
    else:
        raise ContractError("scaffold spec must be outside the Vault")
    learning_goal = raw["learning_goal"]
    version_scope = raw["version_scope"]
    for key, value in (("learning_goal", learning_goal), ("version_scope", version_scope)):
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ContractError(f"{key} must be a normalized non-empty string")
        if has_control_characters(value):
            raise ContractError(f"{key} contains a control character")
        ensure_no_placeholders(value, label=key)
    root = validate_vault_path(raw["root"], label="root")
    ensure_no_placeholders(root, label="root")

    base = raw["base"]
    if not isinstance(base, dict):
        raise ContractError("base must be an object")
    require_keys(base, ("path", "content_file"), label="base")
    base_path = validate_vault_path(base["path"], label="base.path")
    ensure_no_placeholders(base_path, label="base.path")
    expected_base = roadmap_base_path(root)
    if base_path != expected_base:
        raise ContractError(f"base.path must be {expected_base}")
    base_content = read_external_content(
        base["content_file"],
        label="base.content_file",
        vault_path=vault_path,
        content_root=content_root,
    )
    base_filter_expression = f"file.inFolder({json.dumps(root, ensure_ascii=False)})"
    required_base_fragments = (
        json.dumps('file.ext == "md"'),
        json.dumps(base_filter_expression, ensure_ascii=False),
        "route_order:",
        "name: 学习路线",
        "name: 学习中",
        "name: 阻塞",
        "name: 待复习",
        "name: 已掌握",
        "name: 待核验",
        "sort:",
        "property: formula.route_order",
        "note.learning_status:",
        "note.roadmap_status:",
        "note.mastery_evidence:",
    )
    for fragment in required_base_fragments:
        if fragment not in base_content:
            raise ContractError(f"base content missing required fragment: {fragment}")

    directories = raw["directories"]
    if not isinstance(directories, list) or not directories:
        raise ContractError("directories must be a non-empty array")
    normalized_directories: list[dict[str, Any]] = []
    seen_paths: set[str] = {base_path}
    top_level_numbers: set[str] = set()
    top_level_roles: dict[str, list[tuple[int, str]]] = {}
    overview_directory: str | None = None
    for index, item in enumerate(directories):
        if not isinstance(item, dict):
            raise ContractError(f"directories[{index}] must be an object")
        require_keys(item, ("path", "keep"), label=f"directories[{index}]")
        directory_path = validate_vault_path(item["path"], label=f"directories[{index}].path")
        ensure_no_placeholders(directory_path, label=f"directories[{index}].path")
        ensure_descendant(directory_path, root, label=f"directories[{index}].path")
        relative_parts = PurePosixPath(directory_path).relative_to(PurePosixPath(root)).parts
        for part in relative_parts:
            if not NUMBERED_DIRECTORY_RE.fullmatch(part):
                raise ContractError(f"directory segment must use 01-99 prefix: {part}")
        role = item.get("role")
        if len(relative_parts) == 1:
            if role not in {"overview", "formal", "extension", "review", "assets"}:
                raise ContractError(
                    f"directories[{index}].role must classify the top-level stage"
                )
            number = relative_parts[0][:2]
            if number in top_level_numbers:
                raise ContractError(f"duplicate top-level directory number {number}")
            top_level_numbers.add(number)
            top_level_roles.setdefault(role, []).append((int(number), directory_path))
            if role == "overview":
                if number != "01":
                    raise ContractError("overview role must use directory number 01")
                expected_overview = (
                    "01-项目概述"
                    if roadmap_kind == "repository"
                    else f"01-{topic['path_segment']}概述"
                )
                if relative_parts[0] != expected_overview:
                    raise ContractError(f"01 directory must be named {expected_overview}")
                overview_directory = directory_path
            if role == "assets" and relative_parts[0] != "99-assets":
                raise ContractError("assets role must use top-level directory 99-assets")
        elif role not in {None, "module"}:
            raise ContractError(f"directories[{index}].role must be module for nested directories")
        if directory_path in seen_paths:
            raise ContractError(f"duplicate target path {directory_path}")
        seen_paths.add(directory_path)
        keep = item["keep"]
        if not isinstance(keep, bool):
            raise ContractError(f"directories[{index}].keep must be boolean")
        if len(relative_parts) == 1 and role == "overview":
            if keep:
                raise ContractError("overview directory contains notes and must not use .gitkeep")
        elif not keep:
            raise ContractError(f"empty initialized directory must use .gitkeep: {directory_path}")
        normalized_item: dict[str, Any] = {"path": directory_path, "keep": keep}
        if role is not None:
            normalized_item["role"] = role
        normalized_directories.append(normalized_item)
    if roadmap_kind == "repository":
        actual_outer_route = tuple(
            (PurePosixPath(item["path"]).name, item.get("role"))
            for item in normalized_directories
            if PurePosixPath(item["path"]).parent.as_posix() == root
        )
        if actual_outer_route != REPOSITORY_STAGE_CONTRACT:
            raise ContractError(
                "repository outer route must use the fixed 01-09 and 99-assets contract"
            )
    if overview_directory is None:
        raise ContractError("directories must contain an overview stage")
    for required_role in ("overview", "extension", "review", "assets"):
        if len(top_level_roles.get(required_role, [])) != 1:
            raise ContractError(f"directories must contain exactly one {required_role} stage")
    formal_stages = top_level_roles.get("formal", [])
    if not formal_stages:
        raise ContractError("directories must contain at least one formal stage")
    overview_number = top_level_roles["overview"][0][0]
    extension_number = top_level_roles["extension"][0][0]
    review_number = top_level_roles["review"][0][0]
    asset_number = top_level_roles["assets"][0][0]
    formal_numbers = sorted(number for number, _path in formal_stages)
    if not (
        overview_number == 1
        and formal_numbers[0] == 2
        and max(formal_numbers) < extension_number < review_number < asset_number
        and asset_number == 99
    ):
        raise ContractError(
            "stage roles must follow overview, formal, extension, review, then 99-assets"
        )
    if sorted(top_level_numbers)[0] != "01":
        raise ContractError("top-level directory numbering must start at 01")
    directory_paths = {item["path"] for item in normalized_directories}
    groups: dict[str, list[str]] = {}
    for directory_path in directory_paths:
        parent = PurePosixPath(directory_path).parent.as_posix()
        if parent != root and parent not in directory_paths:
            raise ContractError(f"directory parent is not declared: {parent}")
        groups.setdefault(parent, []).append(PurePosixPath(directory_path).name)
    for parent, names in groups.items():
        ordered_numbers = sorted(int(name[:2]) for name in names if name[:2] != "99")
        if ordered_numbers and ordered_numbers != list(range(1, max(ordered_numbers) + 1)):
            raise ContractError(f"directory numbering under {parent} must be contiguous from 01")
        for name in names:
            if name.startswith("99-") and parent == root and name != "99-assets":
                raise ContractError("top-level 99 directory must be named 99-assets")

    notes = raw["notes"]
    if not isinstance(notes, list) or not notes:
        raise ContractError("notes must be a non-empty array")
    normalized_notes: list[dict[str, str]] = []
    note_numbers: set[str] = set()
    for index, item in enumerate(notes):
        if not isinstance(item, dict):
            raise ContractError(f"notes[{index}] must be an object")
        require_keys(item, ("path", "content_file"), label=f"notes[{index}]")
        note_path = validate_vault_path(item["path"], label=f"notes[{index}].path")
        ensure_no_placeholders(note_path, label=f"notes[{index}].path")
        ensure_descendant(note_path, overview_directory, label=f"notes[{index}].path")
        if PurePosixPath(note_path).parent.as_posix() not in directory_paths:
            raise ContractError(f"notes[{index}] parent directory is not declared")
        filename = PurePosixPath(note_path).name
        match = NUMBERED_NOTE_RE.fullmatch(filename)
        if not match:
            raise ContractError(f"Markdown note must use §01-§99 prefix: {filename}")
        if match.group(1) in note_numbers:
            raise ContractError(f"duplicate overview note number {match.group(1)}")
        note_numbers.add(match.group(1))
        if note_path in seen_paths:
            raise ContractError(f"duplicate target path {note_path}")
        seen_paths.add(note_path)
        content = read_external_content(
            item["content_file"],
            label=f"notes[{index}].content_file",
            vault_path=vault_path,
            content_root=content_root,
        )
        frontmatter_lines = markdown_frontmatter_lines(
            content, label=f"notes[{index}].content_file"
        )
        frontmatter_keys = {
            line.split(":", 1)[0]
            for line in frontmatter_lines
            if line and not line[0].isspace() and ":" in line
        }
        for required_property in (
            "title",
            "aliases",
            "tags",
            "date",
            "updated",
            "status",
            "category",
            "note_type",
            "difficulty",
            "roadmap_root",
            "roadmap_topic",
            "learning_goal",
            "knowledge_points_total",
            "knowledge_points_covered",
            "knowledge_points_pending",
            "stage_title",
            "stage_order",
            "lesson_order",
            "learning_status",
            "mastery_score",
            "hard_prerequisites",
            "soft_prerequisites",
            "blocked_by",
            "mastery_evidence",
            "assessment_type",
            "assessment_at",
            "last_reviewed",
            "next_review",
            "review_count",
            "verified_at",
            "version_scope",
            "sources",
        ):
            if required_property not in frontmatter_keys:
                raise ContractError(
                    f"notes[{index}] content missing property {required_property}"
                )
        canonical_lines = (
            f"roadmap_topic: {json.dumps(topic['display'], ensure_ascii=False)}",
            f"roadmap_root: {json.dumps(root, ensure_ascii=False)}",
            f"learning_goal: {json.dumps(learning_goal, ensure_ascii=False)}",
            f"version_scope: {json.dumps(version_scope, ensure_ascii=False)}",
            f"stage_title: {json.dumps(PurePosixPath(overview_directory).name, ensure_ascii=False)}",
            f"  - {json.dumps('学习路线/' + topic['tag'], ensure_ascii=False)}",
        )
        content_lines = set(frontmatter_lines)
        for canonical_line in canonical_lines:
            if canonical_line not in content_lines:
                raise ContractError(
                    f"notes[{index}] content is inconsistent with canonical metadata: {canonical_line}"
                )
        if roadmap_kind == "repository" and "roadmap_kind: repository" not in content_lines:
            raise ContractError(
                f"notes[{index}] content missing canonical roadmap_kind: repository"
            )
        required_initial_lines = {
            "status: 待核验",
            "knowledge_points_total: 0",
            "knowledge_points_covered: 0",
            "knowledge_points_pending: 0",
            "mastery_score: 0",
            "mastery_evidence: []",
            "assessment_type:",
            "assessment_at:",
            "last_reviewed:",
            "next_review:",
            "review_count: 0",
        }
        missing_initial = sorted(required_initial_lines - content_lines)
        if missing_initial:
            raise ContractError(
                "initial scaffold note must use an unmastered publication state: "
                f"{missing_initial[0]}"
            )
        try:
            knowledge_total = int(frontmatter_top_level_raw(frontmatter_lines, label=f"notes[{index}] content").get("knowledge_points_total") or "")
            knowledge_covered = int(frontmatter_top_level_raw(frontmatter_lines, label=f"notes[{index}] content").get("knowledge_points_covered") or "")
            knowledge_pending = int(frontmatter_top_level_raw(frontmatter_lines, label=f"notes[{index}] content").get("knowledge_points_pending") or "")
        except ValueError as error:
            raise ContractError(f"notes[{index}] knowledge point counts must be non-negative integers") from error
        if min(knowledge_total, knowledge_covered, knowledge_pending) < 0 or knowledge_covered + knowledge_pending != knowledge_total:
            raise ContractError(f"notes[{index}] knowledge point counts must satisfy covered + pending = total")
        normalized_notes.append({"path": note_path, "content": content})
    ordered_note_numbers = sorted(int(number) for number in note_numbers)
    if ordered_note_numbers[0] != 1:
        raise ContractError("overview note numbering must start at §01")
    if ordered_note_numbers != list(range(1, max(ordered_note_numbers) + 1)):
        raise ContractError("overview note numbering must be contiguous from §01")
    note_paths = {item["path"] for item in normalized_notes}
    required_overview_notes = {
        f"{overview_directory}/§01-前置准备.md",
        f"{overview_directory}/§02-{topic['path_segment']}概述.md",
    }
    missing_overview_notes = sorted(required_overview_notes - note_paths)
    if missing_overview_notes:
        raise ContractError(
            f"required overview notes are missing: {', '.join(missing_overview_notes)}"
        )
    expected_learning_states = {
        f"{overview_directory}/§01-前置准备.md": "学习中",
        f"{overview_directory}/§02-{topic['path_segment']}概述.md": "未开始",
    }
    for note in normalized_notes:
        expected_state = expected_learning_states.get(note["path"])
        note_frontmatter = set(
            markdown_frontmatter_lines(note["content"], label=f"{note['path']} content")
        )
        if expected_state and f"learning_status: {expected_state}" not in note_frontmatter:
            raise ContractError(
                f"{note['path']} must start with learning_status: {expected_state}"
            )
    anchor_path = f"{overview_directory}/§01-前置准备.md"
    anchor = next(note for note in normalized_notes if note["path"] == anchor_path)
    anchor_frontmatter = set(
        markdown_frontmatter_lines(anchor["content"], label="topic anchor content")
    )
    if "roadmap_status: 进行中" not in anchor_frontmatter:
        raise ContractError("topic anchor must start with roadmap_status: 进行中")
    if roadmap_kind == "repository":
        assert repository is not None
        repository_anchor_lines = {
            "repository_provider": repository["provider"],
            "repository_name": repository["name"],
            "repository_url": repository["url"],
            "repository_default_branch": repository["default_branch"],
            "repository_target_ref": repository["target_ref"],
            "repository_commit": repository["commit"],
            "repository_license_spdx": repository["license_spdx"],
            "repository_verified_at": repository["verified_at"],
            "repository_scope": repository["scope"],
            "core_slice": repository["core_slice"],
            "upstream_checked_at": repository["upstream_checked_at"],
            "upstream_status": repository["upstream_status"],
            "graduation_status": "pending",
        }
        for key, value in repository_anchor_lines.items():
            candidates = {
                f"{key}: {value}",
                f"{key}: {json.dumps(value, ensure_ascii=False)}",
            }
            if not candidates.intersection(anchor_frontmatter):
                raise ContractError(f"repository anchor missing canonical {key}")

    gitkeeps = [f"{item['path']}/.gitkeep" for item in normalized_directories if item["keep"]]
    for keep_path in gitkeeps:
        if keep_path in seen_paths:
            raise ContractError(f"duplicate target path {keep_path}")
        seen_paths.add(keep_path)

    return {
        "vault_name": vault_name,
        "vault_path": vault_path,
        "topic": topic,
        "roadmap_kind": roadmap_kind,
        "repository": repository,
        "learning_goal": learning_goal,
        "version_scope": version_scope,
        "root": root,
        "base": {"path": base_path, "content": base_content},
        "directories": normalized_directories,
        "notes": normalized_notes,
        "gitkeeps": gitkeeps,
    }


def load_write_note_plan(path: str, *, actual_vault_path: str | None = None) -> dict[str, Any]:
    plan_path = Path(path).expanduser()
    if plan_path.is_symlink():
        raise ContractError("note plan must not be a symbolic link")
    try:
        resolved_plan_path = plan_path.resolve(strict=True)
    except OSError as error:
        raise ContractError(f"cannot resolve note plan: {error}") from error
    content_root = resolved_plan_path.parent
    raw = read_json_object(path, label="note plan")
    vault_name, vault_path = normalize_vault_identity(raw, label="note plan")
    if actual_vault_path and Path(vault_path) != Path(actual_vault_path).resolve():
        raise ContractError("note plan vault_path does not match the selected Vault")
    try:
        resolved_plan_path.relative_to(Path(vault_path).resolve())
    except ValueError:
        pass
    else:
        raise ContractError("note plan must be outside the Vault")
    require_keys(
        raw,
        (
            "topic",
            "learning_goal",
            "version_scope",
            "root",
            "path",
            "content_file",
            "mode",
            "remove_gitkeep",
        ),
        label="note plan",
    )
    topic = normalize_topic_metadata(raw)
    roadmap_kind = raw.get("roadmap_kind", "topic")
    if roadmap_kind not in {"topic", "repository"}:
        raise ContractError("note plan roadmap_kind must be topic or repository")
    repository = (
        normalize_repository_metadata(raw) if roadmap_kind == "repository" else None
    )
    learning_goal = raw["learning_goal"]
    version_scope = raw["version_scope"]
    for key, value in (("learning_goal", learning_goal), ("version_scope", version_scope)):
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ContractError(f"note plan {key} must be a normalized non-empty string")
        if has_control_characters(value):
            raise ContractError(f"note plan {key} contains a control character")
        ensure_no_placeholders(value, label=f"note plan {key}")
    root = validate_vault_path(raw["root"], label="note plan root")
    note_path = validate_vault_path(raw["path"], label="note plan path")
    ensure_descendant(note_path, root, label="note plan path")
    relative = PurePosixPath(note_path).relative_to(PurePosixPath(root))
    if len(relative.parts) < 2:
        raise ContractError("note plan path must be inside a numbered stage directory")
    for directory in relative.parts[:-1]:
        if not NUMBERED_DIRECTORY_RE.fullmatch(directory):
            raise ContractError(f"note plan directory must use 01-99 prefix: {directory}")
    filename = relative.parts[-1]
    filename_match = NUMBERED_NOTE_RE.fullmatch(filename)
    if not filename_match:
        raise ContractError("note plan path must use a §01-§99 Markdown filename")
    stage_directory = relative.parts[0]
    stage_order = int(stage_directory[:2])
    lesson_order = int(filename_match.group(1))
    if stage_directory == "99-assets":
        raise ContractError("note plan cannot write course Markdown into reserved 99-assets")
    mode = raw["mode"]
    if mode not in {"create", "replace"}:
        raise ContractError("note plan mode must be create or replace")
    remove_gitkeep = raw["remove_gitkeep"]
    if not isinstance(remove_gitkeep, bool):
        raise ContractError("note plan remove_gitkeep must be boolean")
    if mode == "replace" and remove_gitkeep:
        raise ContractError("replace mode must not remove .gitkeep")
    content = read_external_content(
        raw["content_file"],
        label="note plan content_file",
        vault_path=vault_path,
        content_root=content_root,
        content_root_label="note plan directory",
    )
    frontmatter_lines = markdown_frontmatter_lines(content, label="note plan content_file")
    frontmatter_values = frontmatter_top_level_raw(
        frontmatter_lines, label="note plan content_file"
    )
    frontmatter_keys = {
        line.split(":", 1)[0]
        for line in frontmatter_lines
        if line and not line[0].isspace() and ":" in line
    }
    required_properties = {
        "title",
        "aliases",
        "tags",
        "date",
        "updated",
        "status",
        "category",
        "note_type",
        "difficulty",
        "roadmap_root",
        "roadmap_topic",
        "learning_goal",
        "knowledge_points_total",
        "knowledge_points_covered",
        "knowledge_points_pending",
        "stage_title",
        "stage_order",
        "lesson_order",
        "learning_status",
        "mastery_score",
        "hard_prerequisites",
        "soft_prerequisites",
        "blocked_by",
        "mastery_evidence",
        "assessment_type",
        "assessment_at",
        "last_reviewed",
        "next_review",
        "review_count",
        "verified_at",
        "version_scope",
        "sources",
    }
    missing_properties = sorted(required_properties - frontmatter_keys)
    if missing_properties:
        raise ContractError(
            f"note plan content missing properties: {', '.join(missing_properties)}"
        )
    canonical_lines = {
        f"roadmap_topic: {json.dumps(topic['display'], ensure_ascii=False)}",
        f"roadmap_root: {json.dumps(root, ensure_ascii=False)}",
        f"learning_goal: {json.dumps(learning_goal, ensure_ascii=False)}",
        f"version_scope: {json.dumps(version_scope, ensure_ascii=False)}",
        f"stage_title: {json.dumps(stage_directory, ensure_ascii=False)}",
        f"stage_order: {stage_order}",
        f"lesson_order: {lesson_order}",
        f"  - {json.dumps('学习路线/' + topic['tag'], ensure_ascii=False)}",
    }
    missing_canonical = sorted(canonical_lines - set(frontmatter_lines))
    if missing_canonical:
        raise ContractError(
            f"note plan content has inconsistent canonical metadata: {missing_canonical[0]}"
        )
    if roadmap_kind == "repository" and "roadmap_kind: repository" not in frontmatter_lines:
        raise ContractError("repository note must preserve roadmap_kind: repository")
    frontmatter_set = set(frontmatter_lines)
    if mode == "create":
        required_initial_lines = {
            "status: 待核验",
            "learning_status: 学习中",
            "mastery_score: 0",
            "review_count: 0",
            "mastery_evidence: []",
            "assessment_type:",
            "assessment_at:",
            "last_reviewed:",
            "next_review:",
        }
        missing_initial = sorted(required_initial_lines - frontmatter_set)
        if missing_initial:
            raise ContractError(
                "create mode requires an unmastered initial status, score, review, "
                f"and evidence state: {missing_initial[0]}"
            )
    status_value = frontmatter_scalar(frontmatter_values.get("status"))
    learning_status_value = frontmatter_scalar(frontmatter_values.get("learning_status"))
    try:
        mastery_score = int(frontmatter_values.get("mastery_score") or "")
    except ValueError as error:
        raise ContractError("mastery_score must be an integer between 0 and 100") from error
    if mastery_score < 0 or mastery_score > 100:
        raise ContractError("mastery_score must be an integer between 0 and 100")
    try:
        knowledge_total = int(frontmatter_values.get("knowledge_points_total") or "")
        knowledge_covered = int(frontmatter_values.get("knowledge_points_covered") or "")
        knowledge_pending = int(frontmatter_values.get("knowledge_points_pending") or "")
    except ValueError as error:
        raise ContractError("knowledge point counts must be non-negative integers") from error
    if min(knowledge_total, knowledge_covered, knowledge_pending) < 0:
        raise ContractError("knowledge point counts must be non-negative integers")
    if knowledge_covered + knowledge_pending != knowledge_total:
        raise ContractError("knowledge point counts must satisfy covered + pending = total")
    try:
        review_count = int(frontmatter_values.get("review_count") or "")
    except ValueError as error:
        raise ContractError("review_count must be a non-negative integer") from error
    if review_count < 0:
        raise ContractError("review_count must be a non-negative integer")
    if status_value == "已发布":
        if not frontmatter_list_has_item(frontmatter_lines, "sources"):
            raise ContractError("已发布 requires at least one meaningful source")
        require_iso_date(
            frontmatter_values.get("verified_at"), label="已发布 verified_at"
        )
    if mode == "replace" and learning_status_value == "已掌握":
        if status_value != "已发布":
            raise ContractError("已掌握 requires published content status: 已发布")
        if not frontmatter_list_has_item(frontmatter_lines, "mastery_evidence"):
            raise ContractError("已掌握 requires non-empty mastery evidence")
        for property_name in ("assessment_type", "assessment_at"):
            value = frontmatter_scalar(frontmatter_values.get(property_name))
            if value is None or not value.strip():
                raise ContractError(f"已掌握 requires non-empty {property_name}")
        for property_name in ("assessment_at", "last_reviewed", "next_review"):
            require_iso_date(
                frontmatter_values.get(property_name), label=f"已掌握 {property_name}"
            )
    is_anchor = stage_order == 1 and lesson_order == 1
    roadmap_status = frontmatter_scalar(frontmatter_values.get("roadmap_status"))
    if is_anchor:
        if roadmap_status not in {"进行中", "阻塞", "已完成", "已归档"}:
            raise ContractError("topic anchor requires a valid roadmap_status")
        if roadmap_kind == "repository":
            assert repository is not None
            repository_anchor_values = {
                "repository_provider": repository["provider"],
                "repository_name": repository["name"],
                "repository_url": repository["url"],
                "repository_default_branch": repository["default_branch"],
                "repository_target_ref": repository["target_ref"],
                "repository_commit": repository["commit"],
                "repository_license_spdx": repository["license_spdx"],
                "repository_verified_at": repository["verified_at"],
                "repository_scope": repository["scope"],
                "core_slice": repository["core_slice"],
                "upstream_checked_at": repository["upstream_checked_at"],
                "upstream_status": repository["upstream_status"],
            }
            for property_name, expected in repository_anchor_values.items():
                actual = frontmatter_scalar(frontmatter_values.get(property_name))
                if actual != expected:
                    raise ContractError(
                        f"repository anchor requires canonical {property_name}"
                    )
            graduation_status = frontmatter_scalar(
                frontmatter_values.get("graduation_status")
            )
            if graduation_status not in {"pending", "blocked", "passed"}:
                raise ContractError(
                    "repository anchor requires graduation_status pending, blocked, or passed"
                )
            if mode == "create" and graduation_status != "pending":
                raise ContractError(
                    "new repository roadmap must start with graduation_status: pending"
                )
            if graduation_status == "passed" and (
                repository["license_spdx"].casefold()
                in {"noassertion", "none", "unknown"}
                or repository["upstream_status"] not in {"unchanged", "fixed-baseline"}
            ):
                raise ContractError(
                    "repository graduation cannot pass without a known license and unchanged upstream"
                )
            if roadmap_status == "已完成" and graduation_status != "passed":
                raise ContractError(
                    "completed repository roadmap requires graduation_status: passed"
                )
            if graduation_status == "passed":
                patch_path = resolve_external_plan_file(
                    raw.get("repository_patch_file"),
                    label="repository_patch_file",
                    vault_path=vault_path,
                    content_root=content_root,
                )
                evidence_path = resolve_external_plan_file(
                    raw.get("repository_evidence_file"),
                    label="repository_evidence_file",
                    vault_path=vault_path,
                    content_root=content_root,
                )
                patch_bytes = patch_path.read_bytes()
                if not patch_bytes.strip():
                    raise ContractError("repository Patch evidence must not be empty")
                try:
                    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as error:
                    raise ContractError(f"repository evidence is invalid: {error}") from error
                if not isinstance(evidence, dict):
                    raise ContractError("repository evidence must be a JSON object")
                evidence_checks = {
                    "repository": repository["name"],
                    "repository_url": repository["url"],
                    "baseline_commit": repository["commit"],
                    "target_ref": repository["target_ref"],
                    "license_spdx": repository["license_spdx"],
                    "upstream_status": repository["upstream_status"],
                    "graduation_status": "passed",
                    "patch_sha256": hashlib.sha256(patch_bytes).hexdigest(),
                }
                for key, expected in evidence_checks.items():
                    if evidence.get(key) != expected:
                        raise ContractError(
                            f"repository evidence does not match canonical {key}"
                        )
                changed_files = evidence.get("changed_files")
                approved_files = evidence.get("approved_files")
                test_evidence = evidence.get("test")
                if (
                    not isinstance(changed_files, list)
                    or not changed_files
                    or not all(isinstance(item, str) and item for item in changed_files)
                    or not isinstance(approved_files, list)
                    or not approved_files
                    or not set(changed_files).issubset(set(approved_files))
                    or not isinstance(test_evidence, dict)
                    or test_evidence.get("returncode") != 0
                    or not isinstance(test_evidence.get("argv"), list)
                    or not test_evidence["argv"]
                    or not all(
                        isinstance(item, str) and item for item in test_evidence["argv"]
                    )
                ):
                    raise ContractError(
                        "repository evidence requires changed files and a passing argv test"
                    )
    elif "roadmap_status" in frontmatter_values:
        raise ContractError("roadmap_status is reserved for the §01 topic anchor")
    if not re.search(r"(?m)^# \S", content):
        raise ContractError("note plan content must contain a non-empty H1")
    expected_current: str | None = None
    if mode == "replace":
        expected_file = raw.get("expected_current_file")
        if not expected_file:
            raise ContractError("replace mode requires expected_current_file")
        expected_current = read_external_content(
            expected_file,
            label="note plan expected_current_file",
            vault_path=vault_path,
            content_root=content_root,
            content_root_label="note plan directory",
            reject_placeholders=False,
        )
    elif raw.get("expected_current_file") not in {None, ""}:
        raise ContractError("create mode must not set expected_current_file")
    return {
        "vault_name": vault_name,
        "vault_path": vault_path,
        "topic": topic,
        "roadmap_kind": roadmap_kind,
        "repository": repository,
        "learning_goal": learning_goal,
        "version_scope": version_scope,
        "root": root,
        "path": note_path,
        "content": content,
        "mode": mode,
        "expected_current": expected_current,
        "remove_gitkeep": remove_gitkeep,
        "gitkeep_path": f"{PurePosixPath(note_path).parent.as_posix()}/.gitkeep",
    }


def load_renumber_plan(path: str, *, actual_vault_path: str | None = None) -> dict[str, Any]:
    raw = read_json_object(path, label="renumber plan")
    vault_name, vault_path = normalize_vault_identity(raw, label="renumber plan")
    if actual_vault_path and Path(vault_path) != Path(actual_vault_path).resolve():
        raise ContractError("renumber plan vault_path does not match the selected Vault")
    require_keys(raw, ("root", "moves"), label="renumber plan")
    root = validate_vault_path(raw["root"], label="root")
    ensure_no_placeholders(root, label="root")
    moves = raw["moves"]
    if not isinstance(moves, list) or not moves:
        raise ContractError("moves must be a non-empty array")
    normalized_moves: list[dict[str, str]] = []
    sources: set[str] = set()
    targets: set[str] = set()
    for index, item in enumerate(moves):
        if not isinstance(item, dict):
            raise ContractError(f"moves[{index}] must be an object")
        require_keys(item, ("from", "to"), label=f"moves[{index}]")
        source = validate_vault_path(item["from"], label=f"moves[{index}].from")
        target = validate_vault_path(item["to"], label=f"moves[{index}].to")
        ensure_no_placeholders(source, label=f"moves[{index}].from")
        ensure_no_placeholders(target, label=f"moves[{index}].to")
        if PurePosixPath(source).parent.as_posix() != root:
            raise ContractError(f"moves[{index}].from must be an immediate child of root")
        if PurePosixPath(target).parent.as_posix() != root:
            raise ContractError(f"moves[{index}].to must be an immediate child of root")
        if not NUMBERED_DIRECTORY_RE.fullmatch(PurePosixPath(source).name):
            raise ContractError(f"moves[{index}].from must use a 01-99 prefix")
        if not NUMBERED_DIRECTORY_RE.fullmatch(PurePosixPath(target).name):
            raise ContractError(f"moves[{index}].to must use a 01-99 prefix")
        source_number = PurePosixPath(source).name[:2]
        target_number = PurePosixPath(target).name[:2]
        if "01" in {source_number, target_number} and source_number != target_number:
            raise ContractError("the 01 overview stage cannot change its ordinal")
        if "99" in {source_number, target_number}:
            raise ContractError("99-assets is reserved and cannot be renumbered")
        if source == target:
            raise ContractError(f"moves[{index}] does not change the path")
        if source in sources:
            raise ContractError(f"duplicate move source {source}")
        if target in targets:
            raise ContractError(f"duplicate move target {target}")
        sources.add(source)
        targets.add(target)
        normalized_moves.append({"from": source, "to": target})

    add_directories = raw.get("add_directories", [])
    if not isinstance(add_directories, list):
        raise ContractError("add_directories must be an array")
    normalized_additions: list[dict[str, Any]] = []
    for index, item in enumerate(add_directories):
        if not isinstance(item, dict):
            raise ContractError(f"add_directories[{index}] must be an object")
        require_keys(item, ("path", "keep"), label=f"add_directories[{index}]")
        added_path = validate_vault_path(item["path"], label=f"add_directories[{index}].path")
        ensure_no_placeholders(added_path, label=f"add_directories[{index}].path")
        if PurePosixPath(added_path).parent.as_posix() != root:
            raise ContractError(f"add_directories[{index}].path must be an immediate child of root")
        if not NUMBERED_DIRECTORY_RE.fullmatch(PurePosixPath(added_path).name):
            raise ContractError(f"add_directories[{index}].path must use a 01-99 prefix")
        if not isinstance(item["keep"], bool):
            raise ContractError(f"add_directories[{index}].keep must be boolean")
        if item["keep"] is not True:
            raise ContractError(f"add_directories[{index}] must set keep: true")
        if added_path in sources or added_path in targets:
            raise ContractError(f"added directory collides with move path {added_path}")
        if any(existing["path"] == added_path for existing in normalized_additions):
            raise ContractError(f"duplicate added directory {added_path}")
        normalized_additions.append({"path": added_path, "keep": item["keep"]})

    expected_links = raw.get("expected_links", [])
    if not isinstance(expected_links, list):
        raise ContractError("expected_links must be an array")
    normalized_links: list[dict[str, Any]] = []
    for index, item in enumerate(expected_links):
        if not isinstance(item, dict):
            raise ContractError(f"expected_links[{index}] must be an object")
        require_keys(item, ("source", "target"), label=f"expected_links[{index}]")
        source = validate_vault_path(item["source"], label=f"expected_links[{index}].source")
        target = validate_vault_path(item["target"], label=f"expected_links[{index}].target")
        ensure_descendant(source, root, label=f"expected_links[{index}].source")
        ensure_descendant(target, root, label=f"expected_links[{index}].target")
        minimum_count = item.get("minimum_count", 1)
        if isinstance(minimum_count, bool) or not isinstance(minimum_count, int):
            raise ContractError(f"expected_links[{index}].minimum_count must be an integer")
        normalized_links.append(
            {
                "source": source,
                "target": target,
                "minimum_count": minimum_count,
                "require_no_unresolved": item.get("require_no_unresolved", False),
                "old_targets": [
                    validate_vault_path(old, label=f"expected_links[{index}].old_targets")
                    for old in item.get("old_targets", [])
                ],
            }
        )
        if normalized_links[-1]["minimum_count"] < 1:
            raise ContractError(f"expected_links[{index}].minimum_count must be at least 1")
        if not isinstance(normalized_links[-1]["require_no_unresolved"], bool):
            raise ContractError(f"expected_links[{index}].require_no_unresolved must be boolean")
        for old_target in normalized_links[-1]["old_targets"]:
            ensure_descendant(old_target, root, label=f"expected_links[{index}].old_targets")

    property_updates = raw.get("property_updates", [])
    if not isinstance(property_updates, list):
        raise ContractError("property_updates must be an array")
    normalized_property_updates: list[dict[str, Any]] = []
    updated_paths: set[str] = set()
    for index, item in enumerate(property_updates):
        if not isinstance(item, dict):
            raise ContractError(f"property_updates[{index}] must be an object")
        require_keys(item, ("path", "stage_title", "stage_order"), label=f"property_updates[{index}]")
        update_path = validate_vault_path(item["path"], label=f"property_updates[{index}].path")
        ensure_descendant(update_path, root, label=f"property_updates[{index}].path")
        if PurePosixPath(update_path).suffix != ".md":
            raise ContractError(f"property_updates[{index}].path must be Markdown")
        if update_path in updated_paths:
            raise ContractError(f"duplicate property update path {update_path}")
        updated_paths.add(update_path)
        relative = PurePosixPath(update_path).relative_to(PurePosixPath(root))
        if len(relative.parts) < 2 or not NUMBERED_DIRECTORY_RE.fullmatch(relative.parts[0]):
            raise ContractError(f"property_updates[{index}].path must be inside a numbered stage")
        expected_stage_title = relative.parts[0]
        stage_title = item["stage_title"]
        stage_order = item["stage_order"]
        if stage_title != expected_stage_title:
            raise ContractError(
                f"property_updates[{index}].stage_title must be {expected_stage_title}"
            )
        if isinstance(stage_order, bool) or not isinstance(stage_order, int):
            raise ContractError(f"property_updates[{index}].stage_order must be an integer")
        if stage_order != int(expected_stage_title[:2]):
            raise ContractError(
                f"property_updates[{index}].stage_order must match directory number"
            )
        normalized_update: dict[str, Any] = {
            "path": update_path,
            "stage_title": stage_title,
            "stage_order": stage_order,
        }
        if "updated" in item:
            updated = item["updated"]
            if not isinstance(updated, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated):
                raise ContractError(f"property_updates[{index}].updated must be YYYY-MM-DD")
            normalized_update["updated"] = updated
        normalized_property_updates.append(normalized_update)

    base = raw.get("base")
    normalized_base: dict[str, Any] | None = None
    if base is not None:
        if not isinstance(base, dict):
            raise ContractError("base must be an object")
        require_keys(base, ("path", "view"), label="base")
        base_path = validate_vault_path(base["path"], label="base.path")
        expected_base_path = roadmap_base_path(root)
        if base_path != expected_base_path:
            raise ContractError(f"base.path must be {expected_base_path}")
        expected_paths = base.get("expected_paths", [])
        if not isinstance(expected_paths, list):
            raise ContractError("base.expected_paths must be an array")
        normalized_base = {
            "path": base_path,
            "view": str(base["view"]),
            "expected_paths": [
                validate_vault_path(value, label="base.expected_paths") for value in expected_paths
            ],
        }

    return {
        "vault_name": vault_name,
        "vault_path": vault_path,
        "root": root,
        "moves": normalized_moves,
        "add_directories": normalized_additions,
        "expected_links": normalized_links,
        "property_updates": normalized_property_updates,
        "base": normalized_base,
        "run_id": uuid.uuid4().hex,
    }


class ObsidianCLI:
    def __init__(self, vault_name: str | None = None) -> None:
        self.vault_name = vault_name
        executable = shutil.which("obsidian")
        if not executable:
            raise ContractError("obsidian CLI is not available")
        self.executable = executable

    def command(self, *arguments: str, target_vault: bool = True) -> subprocess.CompletedProcess[str]:
        command = [self.executable]
        if target_vault and self.vault_name:
            command.append(f"vault={self.vault_name}")
        command.extend(arguments)
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        if completed.returncode != 0:
            raise ContractError(
                f"obsidian command failed ({completed.returncode}): {' '.join(arguments)}: {combined.strip()}"
            )
        if "Error:" in combined or "Unknown command" in combined:
            raise ContractError(f"obsidian command reported an error: {combined.strip()}")
        return completed

    def text(self, *arguments: str, target_vault: bool = True) -> str:
        return self.command(*arguments, target_vault=target_vault).stdout.strip()

    def eval(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = base64.b64encode(
            json.dumps({"op": operation, **payload}, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        code = EVAL_DRIVER.replace("__LEARN_TOPIC_PAYLOAD__", encoded)
        output = self.text("eval", f"code={code}")
        matches = re.findall(rf"{re.escape(SENTINEL)}(\{{.*\}})", output)
        if len(matches) != 1:
            raise ContractError(
                f"obsidian eval returned {len(matches)} structured sentinels; expected exactly one"
            )
        try:
            result = json.loads(matches[0])
        except json.JSONDecodeError as error:
            raise ContractError(f"obsidian eval sentinel is not valid JSON: {error}") from error
        if not isinstance(result, dict) or result.get("learnTopic") is not True:
            raise ContractError("obsidian eval sentinel has the wrong contract marker")
        if result.get("ok") is not True:
            raise ContractError(f"obsidian eval {operation} failed: {result.get('error', result)}")
        return result

    def identity(self) -> dict[str, str]:
        self.command("help", target_vault=False)
        name = self.text("vault", "info=name")
        path = self.text("vault", "info=path")
        version = self.text("version", target_vault=False)
        if not name or not path:
            raise ContractError("obsidian CLI did not return a Vault identity")
        return {"name": name, "path": str(Path(path).resolve()), "version": version}


def assert_selected_vault(
    cli: ObsidianCLI, *, expected_name: str, expected_path: str
) -> dict[str, str]:
    identity = cli.identity()
    if identity["name"] != expected_name:
        raise ContractError(
            f"selected Vault name {identity['name']!r} does not match plan {expected_name!r}"
        )
    if Path(identity["path"]) != Path(expected_path).resolve():
        raise ContractError(
            f"selected Vault path {identity['path']!r} does not match plan {expected_path!r}"
        )
    return identity


def base_query(
    cli: ObsidianCLI, base: dict[str, Any], *, exact: bool = False
) -> dict[str, Any]:
    output = cli.text(
        "base:query",
        f"path={base['path']}",
        f"view={base['view']}",
        "format=paths",
    )
    returned_paths = {line.strip() for line in output.splitlines() if line.strip()}
    missing = [path for path in base.get("expected_paths", []) if path not in returned_paths]
    if missing:
        raise ContractError(f"Base query is missing expected paths: {', '.join(missing)}")
    if exact:
        expected_paths = set(base.get("expected_paths", []))
        extra = sorted(returned_paths - expected_paths)
        if extra:
            raise ContractError(f"Base query returned unexpected paths: {', '.join(extra)}")
    if base.get("expected_paths") and not output.strip():
        raise ContractError("Base query unexpectedly returned no rows")
    return {"path": base["path"], "view": base["view"], "output": output}


def command_probe(args: argparse.Namespace) -> dict[str, Any]:
    cli = ObsidianCLI(args.vault)
    identity = cli.identity()
    probe = cli.eval("probe", {})
    return json_report(True, "probe", vault=identity, capabilities=probe["capabilities"])


def command_scaffold(args: argparse.Namespace) -> dict[str, Any]:
    raw = read_json_object(args.spec, label="scaffold spec")
    expected_name, expected_path = normalize_vault_identity(raw, label="scaffold spec")
    selected_name = args.vault or expected_name
    cli = ObsidianCLI(selected_name)
    identity = assert_selected_vault(cli, expected_name=expected_name, expected_path=expected_path)
    spec = load_scaffold_spec(args.spec, actual_vault_path=identity["path"])
    operation = "scaffold" if args.apply else "scaffold_preflight"
    result = cli.eval(operation, spec)
    return json_report(
        True,
        "scaffold",
        mode="apply" if args.apply else "dry-run",
        vault=identity,
        root=spec["root"],
        directories=[item["path"] for item in spec["directories"]],
        files=[spec["base"]["path"], *[item["path"] for item in spec["notes"]]],
        gitkeeps=spec["gitkeeps"],
        postconditions=result.get("postconditions", []),
    )


def command_validate(args: argparse.Namespace) -> dict[str, Any]:
    raw = read_json_object(args.spec, label="scaffold spec")
    expected_name, expected_path = normalize_vault_identity(raw, label="scaffold spec")
    selected_name = args.vault or expected_name
    cli = ObsidianCLI(selected_name)
    identity = assert_selected_vault(cli, expected_name=expected_name, expected_path=expected_path)
    spec = load_scaffold_spec(args.spec, actual_vault_path=identity["path"])
    structural = cli.eval("validate_scaffold", spec)
    query = base_query(
        cli,
        {
            "path": spec["base"]["path"],
            "view": "学习路线",
            "expected_paths": [item["path"] for item in spec["notes"]],
        },
        exact=True,
    )
    cli.text("open", f"path={spec['base']['path']}")
    opened = cli.eval("validate_base_open", {"base": spec["base"]})
    return json_report(
        True,
        "validate",
        vault=identity,
        root=spec["root"],
        structural=structural.get("postconditions", []),
        base_query=query,
        base_open=opened.get("baseOpen"),
    )


def command_write_note(args: argparse.Namespace) -> dict[str, Any]:
    raw = read_json_object(args.plan, label="note plan")
    expected_name, expected_path = normalize_vault_identity(raw, label="note plan")
    selected_name = args.vault or expected_name
    cli = ObsidianCLI(selected_name)
    identity = assert_selected_vault(cli, expected_name=expected_name, expected_path=expected_path)
    plan = load_write_note_plan(args.plan, actual_vault_path=identity["path"])
    operation = "write_note_apply" if args.apply else "write_note_preflight"
    result = cli.eval(operation, plan)
    return json_report(
        True,
        "write-note",
        mode="apply" if args.apply else "dry-run",
        vault=identity,
        root=plan["root"],
        path=plan["path"],
        write_mode=plan["mode"],
        remove_gitkeep=plan["remove_gitkeep"],
        postconditions=result.get("postconditions", []),
    )


def command_renumber(args: argparse.Namespace) -> dict[str, Any]:
    raw = read_json_object(args.plan, label="renumber plan")
    expected_name, expected_path = normalize_vault_identity(raw, label="renumber plan")
    selected_name = args.vault or expected_name
    cli = ObsidianCLI(selected_name)
    identity = assert_selected_vault(cli, expected_name=expected_name, expected_path=expected_path)
    plan = load_renumber_plan(args.plan, actual_vault_path=identity["path"])
    operation = "renumber" if args.apply else "renumber_preflight"
    result = cli.eval(operation, plan)
    query = None
    if args.apply and plan.get("base"):
        query = base_query(cli, plan["base"])
    if args.apply:
        for expected in plan["expected_links"]:
            links_output = cli.text("links", f"path={expected['source']}")
            if PurePosixPath(expected["target"]).stem not in links_output and expected["target"] not in links_output:
                raise ContractError(
                    f"CLI links output for {expected['source']} is missing {expected['target']}"
                )
            cli.text("backlinks", f"path={expected['target']}", "format=json")
    return json_report(
        True,
        "renumber",
        mode="apply" if args.apply else "dry-run",
        vault=identity,
        root=plan["root"],
        moves=plan["moves"],
        add_directories=plan["add_directories"],
        property_updates=plan["property_updates"],
        postconditions=result.get("postconditions", []),
        base_query=query,
    )


def expected_scaffold_inventory(spec: dict[str, Any]) -> list[str]:
    return sorted(
        [
            spec["base"]["path"],
            *[item["path"] for item in spec["directories"]],
            *[item["path"] for item in spec["notes"]],
            *spec["gitkeeps"],
        ]
    )


def command_trash_validation(args: argparse.Namespace) -> dict[str, Any]:
    raw = read_json_object(args.spec, label="scaffold spec")
    expected_name, expected_path = normalize_vault_identity(raw, label="scaffold spec")
    selected_name = args.vault or expected_name
    cli = ObsidianCLI(selected_name)
    identity = assert_selected_vault(cli, expected_name=expected_name, expected_path=expected_path)
    spec = load_scaffold_spec(args.spec, actual_vault_path=identity["path"])
    expected_basename = f"99-Learn-Topic-Validation-{args.run_id}"
    if PurePosixPath(spec["root"]).name != expected_basename:
        raise ContractError(
            f"validation root basename must be exactly {expected_basename}; refusing cleanup"
        )
    marker_path = args.marker_path or spec["notes"][0]["path"]
    marker_path = validate_vault_path(marker_path, label="marker_path")
    ensure_descendant(marker_path, spec["root"], label="marker_path")
    extra_paths: list[str] = []
    for index, value in enumerate(args.extra_path):
        extra_path = validate_vault_path(value, label=f"extra_path[{index}]")
        ensure_descendant(extra_path, spec["root"], label=f"extra_path[{index}]")
        if extra_path in extra_paths:
            raise ContractError(f"duplicate extra cleanup path {extra_path}")
        extra_paths.append(extra_path)
    inventory = expected_scaffold_inventory(spec)
    for extra_path in extra_paths:
        if extra_path in inventory:
            raise ContractError(f"extra cleanup path is already in scaffold inventory: {extra_path}")
        inventory.append(extra_path)
    payload = {
        "root": spec["root"],
        "run_id": args.run_id,
        "marker_path": marker_path,
        "expected_inventory": sorted(inventory),
    }
    operation = "trash_validation" if args.apply else "trash_validation_preflight"
    result = cli.eval(operation, payload)
    return json_report(
        True,
        "trash-validation",
        mode="apply" if args.apply else "dry-run",
        vault=identity,
        root=spec["root"],
        postconditions=result.get("postconditions", []),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", help="Obsidian Vault name; must match the plan")
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe", help="check CLI, Vault identity, APIs, and settings")
    probe.set_defaults(handler=command_probe)

    scaffold = subparsers.add_parser("scaffold", help="preflight or create a roadmap scaffold")
    scaffold.add_argument("--spec", required=True, help="absolute or relative path to scaffold JSON")
    scaffold.add_argument("--apply", action="store_true", help="perform the confirmed mutation")
    scaffold.set_defaults(handler=command_scaffold)

    validate = subparsers.add_parser("validate", help="validate a created roadmap and its Base")
    validate.add_argument("--spec", required=True, help="path to the applied scaffold JSON")
    validate.set_defaults(handler=command_validate)

    write_note = subparsers.add_parser(
        "write-note", help="preflight or safely create/replace one learning note"
    )
    write_note.add_argument("--plan", required=True, help="path to the note write JSON plan")
    write_note.add_argument("--apply", action="store_true", help="perform the confirmed note write")
    write_note.set_defaults(handler=command_write_note)

    renumber = subparsers.add_parser("renumber", help="preflight or apply collision-safe renumbering")
    renumber.add_argument("--plan", required=True, help="path to the confirmed renumber JSON")
    renumber.add_argument("--apply", action="store_true", help="perform the confirmed mutation")
    renumber.set_defaults(handler=command_renumber)

    trash = subparsers.add_parser(
        "trash-validation", help="trash only a marker-verified acceptance-test roadmap"
    )
    trash.add_argument("--spec", required=True, help="path to the acceptance scaffold JSON")
    trash.add_argument("--run-id", required=True, help="exact acceptance run identifier")
    trash.add_argument("--marker-path", help="marker note path; defaults to the first overview note")
    trash.add_argument(
        "--extra-path",
        action="append",
        default=[],
        help="extra acceptance fixture path below the marked root; may be repeated",
    )
    trash.add_argument("--apply", action="store_true", help="move the verified test root to trash")
    trash.set_defaults(handler=command_trash_validation)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = args.handler(args)
    except ContractError as error:
        emit(json_report(False, args.command, error=str(error)), stream=sys.stderr)
        return 1
    except KeyboardInterrupt:
        emit(json_report(False, args.command, error="interrupted"), stream=sys.stderr)
        return 130
    emit(report)
    return 0


EVAL_DRIVER = r'''
(async () => {
  const marker = "LEARN_TOPIC_JSON:";
  const emit = (result) => marker + JSON.stringify({learnTopic: true, ...result});
  const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  try {
    const bytes = Uint8Array.from(atob("__LEARN_TOPIC_PAYLOAD__"), (character) => character.charCodeAt(0));
    const payload = JSON.parse(new TextDecoder().decode(bytes));
    const operation = payload.op;
    const adapter = app.vault.adapter;
    const getFolder = (path) => app.vault.getFolderByPath(path);
    const getFile = (path) => app.vault.getFileByPath(path);
    const getAbstract = (path) => app.vault.getAbstractFileByPath(path);
    const trashOption = app.vault.getConfig("trashOption");
    const alwaysUpdateLinks = app.vault.getConfig("alwaysUpdateLinks");
    const requiredFunctions = {
      createFolder: app.vault.createFolder,
      create: app.vault.create,
      renameFile: app.fileManager.renameFile,
      trashFile: app.fileManager.trashFile,
      processFrontMatter: app.fileManager.processFrontMatter,
      adapterExists: adapter.exists,
      adapterWrite: adapter.write,
      adapterRead: adapter.read,
      adapterList: adapter.list,
    };
    const missingFunctions = Object.entries(requiredFunctions)
      .filter(([, value]) => typeof value !== "function")
      .map(([name]) => name);
    if (missingFunctions.length > 0) {
      throw new Error(`missing required APIs: ${missingFunctions.join(", ")}`);
    }
    const assertTrashIsRecoverable = () => {
      if (trashOption !== "system" && trashOption !== "local") {
        throw new Error(`trashOption=${trashOption} is not recoverable`);
      }
    };
    const pathExists = async (path) => Boolean(getAbstract(path)) || await adapter.exists(path);
    const assertMissing = async (path, label) => {
      if (await pathExists(path)) throw new Error(`${label} already exists: ${path}`);
    };
    const ensureFolder = async (path, created) => {
      let current = "";
      for (const segment of path.split("/")) {
        current = current ? `${current}/${segment}` : segment;
        const folder = getFolder(current);
        if (folder) continue;
        if (await adapter.exists(current)) throw new Error(`non-folder path collision: ${current}`);
        await app.vault.createFolder(current);
        if (!getFolder(current)) throw new Error(`folder postcondition failed: ${current}`);
        created.push(current);
      }
    };
    const getYamlParser = () => {
      if (typeof globalThis.parseYaml === "function") return globalThis.parseYaml;
      try {
        const parser = require("obsidian")?.parseYaml;
        return typeof parser === "function" ? parser : null;
      } catch (_error) {
        return null;
      }
    };
    const parseYamlObject = (source, label) => {
      const parser = getYamlParser();
      if (!parser) throw new Error("Obsidian YAML parser is unavailable");
      let value;
      try {
        value = parser(source);
      } catch (error) {
        throw new Error(`${label} is invalid YAML: ${error.message}`);
      }
      if (!value || typeof value !== "object" || Array.isArray(value)) {
        throw new Error(`${label} must parse to a YAML object`);
      }
      return value;
    };
    const isMeaningfulString = (value) => typeof value === "string" && value.trim().length > 0;
    const isMeaningfulStringList = (value) => Array.isArray(value)
      && value.length > 0
      && value.every((item) => isMeaningfulString(item));
    const isIsoDate = (value) => {
      if (!isMeaningfulString(value) || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
      const parsed = new Date(`${value}T00:00:00Z`);
      return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
    };
    const validateScaffoldDocuments = () => {
      const baseDocument = parseYamlObject(payload.base.content, "Base document");
      const requiredViews = ["学习路线", "学习中", "阻塞", "待复习", "已掌握", "待核验"];
      if (!Array.isArray(baseDocument.views)) {
        throw new Error("Base document views must be an array");
      }
      const expectedRootFilter = `file.inFolder(${JSON.stringify(payload.root)})`;
      const expectedFilters = ['file.ext == "md"', expectedRootFilter];
      if (!Array.isArray(baseDocument.filters?.and)
        || Object.keys(baseDocument.filters).length !== 1
        || baseDocument.filters.and.length !== expectedFilters.length
        || !expectedFilters.every((filter) => baseDocument.filters.and.includes(filter))) {
        throw new Error("Base document root filter does not match the roadmap root");
      }
      const expectedRouteFormula = "if(stage_order && lesson_order, stage_order * 100 + lesson_order, 0)";
      if (baseDocument.formulas?.route_order !== expectedRouteFormula) {
        throw new Error("Base route_order formula does not match the learning contract");
      }
      const expectedReviewFormula = "if(next_review, date(next_review) <= today(), false)";
      if (baseDocument.formulas?.review_due !== expectedReviewFormula) {
        throw new Error("Base review_due formula does not match the review contract");
      }
      const expectedMasteryFormula = 'if(mastery_score >= 85, "稳固", if(mastery_score >= 60, "需巩固", "未掌握"))';
      if (baseDocument.formulas?.mastery_label !== expectedMasteryFormula) {
        throw new Error("Base mastery_label formula does not match the mastery contract");
      }
      const viewNames = baseDocument.views.map((view) => view?.name);
      for (const name of requiredViews) {
        if (viewNames.filter((candidate) => candidate === name).length !== 1) {
          throw new Error(`Base document must contain one required view: ${name}`);
        }
      }
      if (new Set(viewNames).size !== viewNames.length) {
        throw new Error("Base document view names must be unique");
      }
      const requireFlatViewFilters = (name, expectedFilters) => {
        const view = baseDocument.views.find((candidate) => candidate?.name === name);
        const filters = view?.filters?.and;
        if (!Array.isArray(filters)
          || filters.length !== expectedFilters.length
          || !expectedFilters.every((filter) => filters.includes(filter))) {
          throw new Error(`Base view has the wrong filters: ${name}`);
        }
      };
      requireFlatViewFilters("学习中", ['learning_status == "学习中"']);
      requireFlatViewFilters("阻塞", ['learning_status == "阻塞"']);
      requireFlatViewFilters(
        "已掌握",
        [
          'learning_status == "已掌握"',
          'status == "已发布"',
          'list(mastery_evidence).length > 0',
        ],
      );
      requireFlatViewFilters("待核验", ['status == "待核验"']);
      const reviewView = baseDocument.views.find((view) => view?.name === "待复习");
      const reviewFilters = reviewView?.filters?.and;
      const reviewStateGroup = Array.isArray(reviewFilters)
        ? reviewFilters.find((filter) => filter && typeof filter === "object" && Array.isArray(filter.or))
        : null;
      const expectedReviewStates = [
        'learning_status == "已掌握"',
        'learning_status == "待复习"',
      ];
      if (!Array.isArray(reviewFilters)
        || reviewFilters.length !== 2
        || !reviewFilters.includes("formula.review_due == true")
        || !reviewStateGroup
        || reviewStateGroup.or.length !== expectedReviewStates.length
        || !expectedReviewStates.every((filter) => reviewStateGroup.or.includes(filter))) {
        throw new Error("Base view has the wrong filters: 待复习");
      }
      const routeView = baseDocument.views.find((view) => view?.name === "学习路线");
      if (routeView?.groupBy?.property !== "note.stage_title"
        || routeView?.groupBy?.direction !== "ASC") {
        throw new Error("Base learning route must group by note.stage_title ASC");
      }
      if (!Array.isArray(routeView?.sort)
        || !routeView.sort.some((item) => item?.property === "formula.route_order" && item?.direction === "ASC")) {
        throw new Error("Base learning route must sort by formula.route_order ASC");
      }
      if (!baseDocument.properties?.["note.learning_status"]
        || !baseDocument.properties?.["note.roadmap_status"]
        || !baseDocument.properties?.["note.mastery_evidence"]) {
        throw new Error("Base document is missing required learning properties");
      }
      const requiredProperties = [
        "title", "aliases", "tags", "date", "updated", "status", "category",
        "note_type", "difficulty", "roadmap_topic", "roadmap_root", "learning_goal",
        "stage_title", "stage_order", "lesson_order", "learning_status", "mastery_score",
        "hard_prerequisites", "soft_prerequisites", "blocked_by", "mastery_evidence",
        "assessment_type", "assessment_at", "last_reviewed", "next_review", "review_count",
        "verified_at", "version_scope", "sources",
      ];
      const arrayProperties = [
        "aliases", "tags", "hard_prerequisites", "soft_prerequisites", "blocked_by",
        "mastery_evidence", "sources",
      ];
      for (const note of payload.notes) {
        const match = note.content.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
        if (!match) throw new Error(`note frontmatter delimiters are invalid: ${note.path}`);
        const frontmatter = parseYamlObject(match[1], `note frontmatter ${note.path}`);
        for (const property of requiredProperties) {
          if (!Object.prototype.hasOwnProperty.call(frontmatter, property)) {
            throw new Error(`note frontmatter ${note.path} is missing property: ${property}`);
          }
        }
        for (const property of arrayProperties) {
          if (!Array.isArray(frontmatter[property])) {
            throw new Error(`note frontmatter ${note.path} property must be an array: ${property}`);
          }
        }
        if (frontmatter.status !== "待核验"
          || frontmatter.mastery_score !== 0
          || frontmatter.mastery_evidence.length !== 0
          || frontmatter.review_count !== 0
          || frontmatter.assessment_type != null
          || frontmatter.assessment_at != null
          || frontmatter.last_reviewed != null
          || frontmatter.next_review != null) {
          throw new Error(`initial scaffold note has invalid mastery or publication state: ${note.path}`);
        }
        const relativePath = note.path.slice(payload.root.length + 1);
        const stageDirectory = relativePath.split("/")[0];
        const filename = relativePath.split("/").pop();
        const lessonMatch = filename.match(/^§(\d{2})-/);
        if (!lessonMatch) throw new Error(`note filename has no lesson order: ${note.path}`);
        const lessonOrder = Number(lessonMatch[1]);
        const expectedLearningStatus = lessonOrder === 1 ? "学习中" : "未开始";
        const canonicalChecks = [
          ["roadmap_topic", payload.topic?.display],
          ["roadmap_root", payload.root],
          ["learning_goal", payload.learning_goal],
          ["version_scope", payload.version_scope],
          ["stage_title", stageDirectory],
          ["stage_order", Number(stageDirectory.slice(0, 2))],
          ["lesson_order", lessonOrder],
          ["learning_status", expectedLearningStatus],
        ];
        for (const [property, expected] of canonicalChecks) {
          if (frontmatter[property] !== expected) {
            throw new Error(
              `note frontmatter canonical value mismatch ${note.path}: ${property}`,
            );
          }
        }
        const expectedTag = `学习路线/${payload.topic?.tag}`;
        if (!frontmatter.tags.includes(expectedTag)) {
          throw new Error(`note frontmatter canonical tag mismatch: ${note.path}`);
        }
        if (payload.roadmap_kind === "repository") {
          if (frontmatter.roadmap_kind !== "repository") {
            throw new Error(`repository note must preserve roadmap_kind: ${note.path}`);
          }
          if (lessonOrder === 1) {
            const repositoryChecks = [
              ["repository_provider", payload.repository?.provider],
              ["repository_name", payload.repository?.name],
              ["repository_url", payload.repository?.url],
              ["repository_default_branch", payload.repository?.default_branch],
              ["repository_target_ref", payload.repository?.target_ref],
              ["repository_commit", payload.repository?.commit],
              ["repository_license_spdx", payload.repository?.license_spdx],
              ["repository_verified_at", payload.repository?.verified_at],
              ["repository_scope", payload.repository?.scope],
              ["core_slice", payload.repository?.core_slice],
              ["upstream_checked_at", payload.repository?.upstream_checked_at],
              ["upstream_status", payload.repository?.upstream_status],
              ["graduation_status", "pending"],
            ];
            for (const [property, expected] of repositoryChecks) {
              if (frontmatter[property] !== expected) {
                throw new Error(
                  `repository anchor canonical value mismatch ${note.path}: ${property}`,
                );
              }
            }
          }
        }
        if (lessonOrder === 1 && frontmatter.roadmap_status !== "进行中") {
          throw new Error(`topic anchor must have roadmap_status: 进行中: ${note.path}`);
        }
      }
    };
    const validateWriteNoteDocument = () => {
      const match = payload.content.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
      if (!match) throw new Error(`note frontmatter delimiters are invalid: ${payload.path}`);
      const frontmatter = parseYamlObject(match[1], `note frontmatter ${payload.path}`);
      const requiredProperties = [
        "title", "aliases", "tags", "date", "updated", "status", "category",
        "note_type", "difficulty", "roadmap_topic", "roadmap_root", "learning_goal",
        "stage_title", "stage_order", "lesson_order", "learning_status", "mastery_score",
        "hard_prerequisites", "soft_prerequisites", "blocked_by", "mastery_evidence",
        "assessment_type", "assessment_at", "last_reviewed", "next_review", "review_count",
        "verified_at", "version_scope", "sources",
      ];
      for (const property of requiredProperties) {
        if (!Object.prototype.hasOwnProperty.call(frontmatter, property)) {
          throw new Error(`note frontmatter ${payload.path} is missing property: ${property}`);
        }
      }
      for (const property of [
        "aliases", "tags", "hard_prerequisites", "soft_prerequisites", "blocked_by",
        "mastery_evidence", "sources",
      ]) {
        if (!Array.isArray(frontmatter[property])) {
          throw new Error(`note frontmatter ${payload.path} property must be an array: ${property}`);
        }
      }
      const relativePath = payload.path.slice(payload.root.length + 1);
      const stageDirectory = relativePath.split("/")[0];
      const filename = relativePath.split("/").pop();
      const lessonMatch = filename.match(/^§(\d{2})-/);
      if (!lessonMatch) throw new Error(`note filename has no lesson order: ${payload.path}`);
      const canonicalChecks = [
        ["roadmap_topic", payload.topic?.display],
        ["roadmap_root", payload.root],
        ["learning_goal", payload.learning_goal],
        ["version_scope", payload.version_scope],
        ["stage_title", stageDirectory],
        ["stage_order", Number(stageDirectory.slice(0, 2))],
        ["lesson_order", Number(lessonMatch[1])],
      ];
      for (const [property, expected] of canonicalChecks) {
        if (frontmatter[property] !== expected) {
          throw new Error(`note frontmatter canonical value mismatch ${payload.path}: ${property}`);
        }
      }
      const allowedContentStates = ["草稿", "待核验", "已发布", "已归档"];
      const allowedLearningStates = ["未开始", "学习中", "已掌握", "阻塞", "待复习", "已归档"];
      if (!allowedContentStates.includes(frontmatter.status)) {
        throw new Error(`note frontmatter has an invalid status: ${payload.path}`);
      }
      if (!allowedLearningStates.includes(frontmatter.learning_status)) {
        throw new Error(`note frontmatter has an invalid learning_status: ${payload.path}`);
      }
      if (typeof frontmatter.mastery_score !== "number"
        || !Number.isFinite(frontmatter.mastery_score)
        || frontmatter.mastery_score < 0
        || frontmatter.mastery_score > 100) {
        throw new Error(`note frontmatter mastery_score must be between 0 and 100: ${payload.path}`);
      }
      if (!Number.isInteger(frontmatter.review_count) || frontmatter.review_count < 0) {
        throw new Error(`note frontmatter review_count must be a non-negative integer: ${payload.path}`);
      }
      if (frontmatter.status === "已发布"
        && (!isMeaningfulStringList(frontmatter.sources) || !isIsoDate(frontmatter.verified_at))) {
        throw new Error(`published note requires sources and verified_at: ${payload.path}`);
      }
      if (payload.mode === "create"
        && (frontmatter.status !== "待核验"
          || frontmatter.learning_status !== "学习中"
          || frontmatter.mastery_score !== 0
          || frontmatter.mastery_evidence.length !== 0
          || frontmatter.review_count !== 0
          || frontmatter.assessment_type != null
          || frontmatter.assessment_at != null
          || frontmatter.last_reviewed != null
          || frontmatter.next_review != null)) {
        throw new Error(`create note must use the unmastered initial learning state: ${payload.path}`);
      }
      if (frontmatter.learning_status === "已掌握"
        && (frontmatter.status !== "已发布"
          || !isMeaningfulStringList(frontmatter.mastery_evidence)
          || !isMeaningfulString(frontmatter.assessment_type)
          || !isIsoDate(frontmatter.assessment_at)
          || !isIsoDate(frontmatter.last_reviewed)
          || !isIsoDate(frontmatter.next_review))) {
        throw new Error(`mastered note requires published content, evidence, assessment and review dates: ${payload.path}`);
      }
      const isAnchor = Number(frontmatter.stage_order) === 1
        && Number(frontmatter.lesson_order) === 1;
      const allowedRoadmapStates = ["进行中", "阻塞", "已完成", "已归档"];
      if (isAnchor && !allowedRoadmapStates.includes(frontmatter.roadmap_status)) {
        throw new Error(`topic anchor requires a valid roadmap_status: ${payload.path}`);
      }
      if (!isAnchor && Object.prototype.hasOwnProperty.call(frontmatter, "roadmap_status")) {
        throw new Error(`roadmap_status is reserved for the topic anchor: ${payload.path}`);
      }
      if (!frontmatter.tags.includes(`学习路线/${payload.topic?.tag}`)) {
        throw new Error(`note frontmatter canonical tag mismatch: ${payload.path}`);
      }
      if (payload.roadmap_kind === "repository") {
        if (frontmatter.roadmap_kind !== "repository") {
          throw new Error(`repository note must preserve roadmap_kind: ${payload.path}`);
        }
        if (isAnchor) {
          const repositoryChecks = [
            ["repository_provider", payload.repository?.provider],
            ["repository_name", payload.repository?.name],
            ["repository_url", payload.repository?.url],
            ["repository_default_branch", payload.repository?.default_branch],
            ["repository_target_ref", payload.repository?.target_ref],
            ["repository_commit", payload.repository?.commit],
            ["repository_license_spdx", payload.repository?.license_spdx],
            ["repository_verified_at", payload.repository?.verified_at],
            ["repository_scope", payload.repository?.scope],
            ["core_slice", payload.repository?.core_slice],
            ["upstream_checked_at", payload.repository?.upstream_checked_at],
            ["upstream_status", payload.repository?.upstream_status],
          ];
          for (const [property, expected] of repositoryChecks) {
            if (frontmatter[property] !== expected) {
              throw new Error(`repository anchor canonical value mismatch: ${property}`);
            }
          }
          if (!["pending", "blocked", "passed"].includes(frontmatter.graduation_status)) {
            throw new Error("repository anchor has an invalid graduation_status");
          }
          if (frontmatter.graduation_status === "passed"
            && (["noassertion", "none", "unknown"].includes(
              String(payload.repository?.license_spdx || "").toLowerCase(),
            ) || !["unchanged", "fixed-baseline"].includes(
              payload.repository?.upstream_status,
            ))) {
            throw new Error(
              "repository graduation cannot pass without a known license and unchanged upstream",
            );
          }
          if (frontmatter.roadmap_status === "已完成"
            && frontmatter.graduation_status !== "passed") {
            throw new Error(
              "completed repository roadmap requires graduation_status: passed",
            );
          }
        }
      }
      if (!/^# \S/m.test(payload.content)) {
        throw new Error(`note content must contain a non-empty H1: ${payload.path}`);
      }
      return frontmatter;
    };
    const readRoadmapAnchor = async () => {
      if (typeof app.vault.getMarkdownFiles !== "function"
        || typeof app.vault.read !== "function") {
        throw new Error("missing required API: app.vault.getMarkdownFiles/read");
      }
      const escapedRoot = payload.root.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const anchorPattern = new RegExp(
        `^${escapedRoot}/01-[^/]+/§01-[^/]+\\.md$`,
      );
      const candidates = app.vault.getMarkdownFiles().filter(
        (file) => file?.path && anchorPattern.test(file.path),
      );
      if (candidates.length !== 1) {
        throw new Error(`roadmap must contain exactly one §01 anchor: ${payload.root}`);
      }
      const source = await app.vault.read(candidates[0]);
      const match = source.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
      if (!match) throw new Error(`roadmap anchor frontmatter is invalid: ${candidates[0].path}`);
      return parseYamlObject(match[1], `roadmap anchor ${candidates[0].path}`);
    };
    const validateRoadmapIdentity = async () => {
      const rootName = payload.root.split("/").pop();
      const basePath = `${payload.root}/${rootName}-Roadmap.base`;
      const baseFile = getFile(basePath);
      if (!baseFile) throw new Error(`roadmap Base is missing: ${basePath}`);
      const baseContent = await app.vault.read(baseFile);
      const baseDocument = parseYamlObject(baseContent, `roadmap Base ${basePath}`);
      const expectedFilters = [
        'file.ext == "md"',
        `file.inFolder(${JSON.stringify(payload.root)})`,
      ];
      if (!Array.isArray(baseDocument.filters?.and)
        || Object.keys(baseDocument.filters).length !== 1
        || baseDocument.filters.and.length !== expectedFilters.length
        || !expectedFilters.every((filter) => baseDocument.filters.and.includes(filter))) {
        throw new Error(`roadmap Base root filter does not match: ${basePath}`);
      }
      const requiredViews = ["学习路线", "学习中", "阻塞", "待复习", "已掌握", "待核验"];
      if (!Array.isArray(baseDocument.views)) {
        throw new Error(`roadmap Base views are missing: ${basePath}`);
      }
      const viewNames = baseDocument.views.map((view) => view?.name);
      for (const name of requiredViews) {
        if (viewNames.filter((candidate) => candidate === name).length !== 1) {
          throw new Error(`roadmap Base required view is missing or duplicated: ${name}`);
        }
      }
      const anchor = await readRoadmapAnchor();
      const actualKind = anchor.roadmap_kind === "repository" ? "repository" : "topic";
      if (payload.roadmap_kind !== actualKind) {
        throw new Error(`note plan roadmap_kind does not match the Vault anchor: ${actualKind}`);
      }
      if (actualKind === "repository") {
        const repositoryChecks = [
          ["repository_provider", payload.repository?.provider],
          ["repository_name", payload.repository?.name],
          ["repository_url", payload.repository?.url],
          ["repository_commit", payload.repository?.commit],
          ["core_slice", payload.repository?.core_slice],
        ];
        for (const [property, expected] of repositoryChecks) {
          if (anchor[property] !== expected) {
            throw new Error(`repository note plan does not match Vault anchor: ${property}`);
          }
        }
      }
      return {basePath, anchor};
    };
    const assertNoOtherActiveUnit = async () => {
      if (typeof app.vault.getMarkdownFiles !== "function") {
        throw new Error("missing required API: app.vault.getMarkdownFiles");
      }
      const prefix = `${payload.root}/`;
      for (const file of app.vault.getMarkdownFiles()) {
        if (!file?.path?.startsWith(prefix) || file.path === payload.path) continue;
        const relativeParts = file.path.slice(prefix.length).split("/");
        const filename = relativeParts.pop();
        const directoryParts = relativeParts;
        const isRouteNote = directoryParts.length > 0
          && directoryParts[0] !== "99-assets"
          && directoryParts.every((part) => /^(0[1-9]|[1-9][0-9])-.+/.test(part))
          && /^§(0[1-9]|[1-9][0-9])-.+\.md$/.test(filename);
        if (!isRouteNote) continue;
        const source = await app.vault.read(file);
        const match = source.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
        if (!match) throw new Error(`roadmap note frontmatter is invalid: ${file.path}`);
        const frontmatter = parseYamlObject(match[1], `roadmap note ${file.path}`);
        if (frontmatter.roadmap_root !== payload.root) {
          throw new Error(`roadmap note has the wrong roadmap_root: ${file.path}`);
        }
        if (frontmatter.learning_status === "学习中") {
          throw new Error(`another learning unit is already active: ${file.path}`);
        }
      }
    };
    const validateWriteNotePreflight = async () => {
      assertTrashIsRecoverable();
      if (typeof app.vault.modify !== "function" || typeof app.vault.read !== "function") {
        throw new Error("missing required API: app.vault.read/modify");
      }
      if (payload.remove_gitkeep && typeof adapter.remove !== "function") {
        throw new Error("missing required API: adapter.remove");
      }
      const frontmatter = validateWriteNoteDocument();
      if (!getFolder(payload.root)) throw new Error(`roadmap root is not a folder: ${payload.root}`);
      await validateRoadmapIdentity();
      if (frontmatter.learning_status === "学习中") await assertNoOtherActiveUnit();
      const parentPath = payload.path.split("/").slice(0, -1).join("/");
      const parentFolder = getFolder(parentPath);
      if (!parentFolder) throw new Error(`note parent is not a folder: ${parentPath}`);
      const existing = getFile(payload.path);
      if (payload.mode === "create") {
        if (existing || await adapter.exists(payload.path)) {
          throw new Error(`note already exists: ${payload.path}`);
        }
        const siblingNumbers = [];
        for (const child of parentFolder.children || []) {
          if (child?.extension !== "md") continue;
          const siblingName = child.path.split("/").pop();
          const siblingMatch = siblingName.match(/^§(\d{2})-.+\.md$/);
          if (!siblingMatch) continue;
          siblingNumbers.push(Number(siblingMatch[1]));
        }
        siblingNumbers.sort((left, right) => left - right);
        const expectedExisting = Array.from(
          {length: siblingNumbers.length},
          (_, index) => index + 1,
        );
        if (JSON.stringify(siblingNumbers) !== JSON.stringify(expectedExisting)) {
          throw new Error(`existing lesson numbering is not contiguous in ${parentPath}`);
        }
        const targetName = payload.path.split("/").pop();
        const targetOrder = Number(targetName.slice(1, 3));
        const expectedOrder = siblingNumbers.length + 1;
        if (targetOrder !== expectedOrder) {
          throw new Error(`next lesson must be §${String(expectedOrder).padStart(2, "0")} in ${parentPath}`);
        }
        const gitkeepExists = await adapter.exists(payload.gitkeep_path);
        if (siblingNumbers.length === 0) {
          if (!gitkeepExists || !payload.remove_gitkeep) {
            throw new Error(`first lesson requires existing gitkeep and remove_gitkeep=true: ${payload.gitkeep_path}`);
          }
        } else if (gitkeepExists || payload.remove_gitkeep) {
          throw new Error(`non-empty stage must not retain or remove gitkeep: ${payload.gitkeep_path}`);
        }
      } else {
        if (!existing) throw new Error(`note does not exist for replace: ${payload.path}`);
        const current = await app.vault.read(existing);
        if (current !== payload.expected_current) {
          throw new Error(`note changed since it was read: ${payload.path}`);
        }
      }
      return [
        "note YAML and canonical metadata are valid",
        payload.mode === "create" ? "create target is absent" : "replace snapshot matches",
      ];
    };
    const validateScaffoldPreflight = async () => {
      assertTrashIsRecoverable();
      validateScaffoldDocuments();
      await assertMissing(payload.root, "roadmap root");
      await assertMissing(payload.base.path, "Base");
      for (const directory of payload.directories) await assertMissing(directory.path, "directory");
      for (const note of payload.notes) await assertMissing(note.path, "note");
      for (const keep of payload.gitkeeps) await assertMissing(keep, "gitkeep");
      return ["required APIs available", "trash is recoverable", "all targets are absent"];
    };
    const collectAdapterInventory = async (root) => {
      const inventory = [];
      const walk = async (folder) => {
        const listing = await adapter.list(folder);
        for (const file of listing.files) inventory.push(file);
        for (const child of listing.folders) {
          inventory.push(child);
          await walk(child);
        }
      };
      await walk(root);
      return inventory.sort();
    };
    const waitForMetadata = async () => {
      if (typeof app.metadataCache.isCacheClean !== "function") return;
      for (let index = 0; index < 100; index += 1) {
        if (app.metadataCache.isCacheClean()) return;
        await delay(50);
      }
      throw new Error("metadata cache did not become clean");
    };
    const validateLinkExpectations = async () => {
      await waitForMetadata();
      for (const expected of payload.expected_links || []) {
        const count = app.metadataCache.resolvedLinks?.[expected.source]?.[expected.target] || 0;
        if (count < expected.minimum_count) {
          throw new Error(`resolved link missing: ${expected.source} -> ${expected.target}`);
        }
        for (const oldTarget of expected.old_targets || []) {
          const oldCount = app.metadataCache.resolvedLinks?.[expected.source]?.[oldTarget] || 0;
          if (oldCount > 0) throw new Error(`old resolved link remains: ${oldTarget}`);
        }
        if (expected.require_no_unresolved) {
          const unresolved = app.metadataCache.unresolvedLinks?.[expected.source] || {};
          if (Object.keys(unresolved).length > 0) {
            throw new Error(`unresolved links remain in ${expected.source}`);
          }
        }
        const sourceFile = getFile(expected.source);
        if (!sourceFile) throw new Error(`link source is missing: ${expected.source}`);
        const body = await app.vault.read(sourceFile);
        if (body.includes("__lt_tmp_") || body.includes("__lt_rollback_")) {
          throw new Error(`temporary rename path leaked into ${expected.source}`);
        }
        for (const oldTarget of expected.old_targets || []) {
          if (body.includes(oldTarget)) throw new Error(`old path remains in ${expected.source}`);
        }
      }
    };
    const validateRenumberPreflight = async () => {
      assertTrashIsRecoverable();
      if (alwaysUpdateLinks !== true) throw new Error("alwaysUpdateLinks must be enabled");
      const root = getFolder(payload.root);
      if (!root) throw new Error(`roadmap root is not a folder: ${payload.root}`);
      const anchor = await readRoadmapAnchor();
      if (anchor.roadmap_kind === "repository") {
        throw new Error("repository outer route is fixed and cannot be renumbered");
      }
      const sourcePaths = new Set(payload.moves.map((move) => move.from));
      const targetPaths = new Set(payload.moves.map((move) => move.to));
      for (const move of payload.moves) {
        const sourceNumber = move.from.split("/").pop().slice(0, 2);
        const targetNumber = move.to.split("/").pop().slice(0, 2);
        if ((sourceNumber === "01" || targetNumber === "01") && sourceNumber !== targetNumber) {
          throw new Error("the 01 overview stage cannot change its ordinal");
        }
        if (sourceNumber === "99" || targetNumber === "99") {
          throw new Error("99-assets is reserved and cannot be renumbered");
        }
        if (!getFolder(move.from)) throw new Error(`move source is not a folder: ${move.from}`);
        const target = getAbstract(move.to);
        if (target && !sourcePaths.has(move.to)) throw new Error(`move target collision: ${move.to}`);
      }
      for (const addition of payload.add_directories || []) {
        await assertMissing(addition.path, "added directory");
      }
      const requiredPropertyUpdates = new Set();
      const collectMovedMarkdown = (folder, sourceRoot, targetRoot) => {
        for (const child of folder.children || []) {
          if (child.children) {
            collectMovedMarkdown(child, sourceRoot, targetRoot);
          } else if (child.extension === "md" || child.path.endsWith(".md")) {
            requiredPropertyUpdates.add(targetRoot + child.path.slice(sourceRoot.length));
          }
        }
      };
      for (const move of payload.moves) {
        collectMovedMarkdown(getFolder(move.from), move.from, move.to);
      }
      const plannedPropertyUpdates = new Set(
        (payload.property_updates || []).map((update) => update.path),
      );
      for (const path of requiredPropertyUpdates) {
        if (!plannedPropertyUpdates.has(path)) {
          throw new Error(`property_updates is missing moved Markdown: ${path}`);
        }
      }
      for (const update of payload.property_updates || []) {
        let originalPath = update.path;
        for (const move of payload.moves) {
          if (update.path === move.to || update.path.startsWith(`${move.to}/`)) {
            originalPath = move.from + update.path.slice(move.to.length);
            break;
          }
        }
        if (!getFile(originalPath)) throw new Error(`property update source is missing: ${originalPath}`);
      }
      const currentFolders = root.children.filter((child) => child.children).map((child) => child.path);
      const finalFolders = currentFolders
        .map((path) => payload.moves.find((move) => move.from === path)?.to || path)
        .concat((payload.add_directories || []).map((item) => item.path));
      if (new Set(finalFolders).size !== finalFolders.length) throw new Error("duplicate final directory path");
      const ordinals = new Map();
      for (const path of finalFolders) {
        const name = path.split("/").pop();
        const match = name.match(/^(\d{2})-/);
        if (!match) throw new Error(`final directory is not numbered: ${path}`);
        if (ordinals.has(match[1])) throw new Error(`duplicate final directory number ${match[1]}`);
        ordinals.set(match[1], path);
      }
      const normalOrdinals = [...ordinals.keys()]
        .filter((number) => number !== "99")
        .map(Number)
        .sort((left, right) => left - right);
      const expectedOrdinals = Array.from(
        {length: normalOrdinals.length},
        (_, index) => index + 1,
      );
      if (JSON.stringify(normalOrdinals) !== JSON.stringify(expectedOrdinals)) {
        throw new Error("final directory numbering must be contiguous from 01");
      }
      if (!ordinals.has("99") || !ordinals.get("99").endsWith("/99-assets")) {
        throw new Error("final directories must retain top-level 99-assets");
      }
      for (let index = 0; index < payload.moves.length; index += 1) {
        await assertMissing(`${payload.root}/__lt_tmp_${payload.run_id}_${index}`, "temporary path");
        await assertMissing(`${payload.root}/__lt_rollback_${payload.run_id}_${index}`, "rollback path");
      }
      return ["automatic link updates enabled", "move sources and targets are collision-free", "final numbers are unique"];
    };

    if (operation === "probe") {
      if (!getYamlParser()) throw new Error("Obsidian YAML parser is unavailable");
      return emit({
        ok: true,
        op: operation,
        capabilities: {
          requiredFunctions: true,
          yamlParser: true,
          alwaysUpdateLinks,
          trashOption,
        },
      });
    }
    if (operation === "write_note_preflight") {
      const postconditions = await validateWriteNotePreflight();
      return emit({ok: true, op: operation, postconditions});
    }
    if (operation === "write_note_apply") {
      await validateWriteNotePreflight();
      let createdFile = null;
      let gitkeepRemoved = false;
      const existingFile = getFile(payload.path);
      try {
        if (payload.mode === "create") {
          createdFile = await app.vault.create(payload.path, payload.content);
          if (!createdFile || !getFile(payload.path)) {
            throw new Error(`note create postcondition failed: ${payload.path}`);
          }
          if (payload.remove_gitkeep) {
            await adapter.remove(payload.gitkeep_path);
            gitkeepRemoved = true;
            if (await adapter.exists(payload.gitkeep_path)) {
              throw new Error(`gitkeep removal postcondition failed: ${payload.gitkeep_path}`);
            }
          }
        } else {
          await app.vault.modify(existingFile, payload.content);
        }
        const writtenFile = getFile(payload.path);
        if (!writtenFile || await app.vault.read(writtenFile) !== payload.content) {
          throw new Error(`note content postcondition failed: ${payload.path}`);
        }
        return emit({
          ok: true,
          op: operation,
          postconditions: [
            `${payload.mode} wrote exact note content`,
            payload.remove_gitkeep ? "removed and verified .gitkeep" : "left .gitkeep unchanged",
          ],
        });
      } catch (error) {
        const rollbackErrors = [];
        if (payload.mode === "replace" && existingFile) {
          try {
            await app.vault.modify(existingFile, payload.expected_current);
          } catch (rollbackError) {
            rollbackErrors.push(`restore note: ${rollbackError.message}`);
          }
        }
        if (createdFile && getFile(payload.path)) {
          try {
            await app.fileManager.trashFile(createdFile);
          } catch (rollbackError) {
            rollbackErrors.push(`trash created note: ${rollbackError.message}`);
          }
        }
        if (gitkeepRemoved) {
          try {
            await adapter.write(payload.gitkeep_path, "");
          } catch (rollbackError) {
            rollbackErrors.push(`restore gitkeep: ${rollbackError.message}`);
          }
        }
        return emit({
          ok: false,
          op: operation,
          error: error.message,
          rolled_back: rollbackErrors.length === 0,
          rollback_errors: rollbackErrors,
        });
      }
    }
    if (operation === "scaffold_preflight") {
      const postconditions = await validateScaffoldPreflight();
      return emit({ok: true, op: operation, postconditions});
    }
    if (operation === "scaffold") {
      await validateScaffoldPreflight();
      const createdFolders = [];
      const createdFiles = [];
      try {
        await ensureFolder(payload.root, createdFolders);
        for (const directory of [...payload.directories].sort((left, right) => left.path.localeCompare(right.path))) {
          await ensureFolder(directory.path, createdFolders);
        }
        const base = await app.vault.create(payload.base.path, payload.base.content);
        createdFiles.push(base.path);
        if (!getFile(payload.base.path)) throw new Error(`Base postcondition failed: ${payload.base.path}`);
        for (const note of payload.notes) {
          const file = await app.vault.create(note.path, note.content);
          createdFiles.push(file.path);
          if (!getFile(note.path)) throw new Error(`note postcondition failed: ${note.path}`);
        }
        for (const keep of payload.gitkeeps) {
          await adapter.write(keep, "");
          if (!await adapter.exists(keep) || (await adapter.read(keep)).trim() !== "") {
            throw new Error(`gitkeep postcondition failed: ${keep}`);
          }
        }
        return emit({
          ok: true,
          op: operation,
          postconditions: [
            `created ${createdFolders.length} folders`,
            `created ${createdFiles.length} indexed files`,
            `created ${payload.gitkeeps.length} empty gitkeeps`,
          ],
        });
      } catch (error) {
        let rollback = "not-attempted";
        const rollbackRoot = createdFolders[0];
        if (rollbackRoot && getFolder(rollbackRoot) && (trashOption === "system" || trashOption === "local")) {
          try {
            await app.fileManager.trashFile(getFolder(rollbackRoot));
            rollback = await adapter.exists(rollbackRoot) ? "failed" : "complete";
          } catch (rollbackError) {
            rollback = `failed: ${rollbackError.message}`;
          }
        }
        return emit({ok: false, op: operation, error: error.message, rollback});
      }
    }
    if (operation === "validate_scaffold") {
      validateScaffoldDocuments();
      const root = getFolder(payload.root);
      if (!root) throw new Error(`roadmap root is missing: ${payload.root}`);
      const expectedFiles = new Map([[payload.base.path, payload.base.content]]);
      for (const note of payload.notes) expectedFiles.set(note.path, note.content);
      const visibleFiles = [];
      const walk = (folder) => {
        for (const child of folder.children) {
          if (child.children) walk(child);
          else visibleFiles.push(child.path);
        }
      };
      walk(root);
      visibleFiles.sort();
      const expectedVisible = [...expectedFiles.keys()].sort();
      if (JSON.stringify(visibleFiles) !== JSON.stringify(expectedVisible)) {
        throw new Error(`visible inventory mismatch: ${JSON.stringify(visibleFiles)}`);
      }
      const rootFiles = root.children.filter((child) => !child.children).map((child) => child.path);
      if (rootFiles.length !== 1 || rootFiles[0] !== payload.base.path) {
        throw new Error(`roadmap root must contain only its Base file: ${JSON.stringify(rootFiles)}`);
      }
      for (const directory of payload.directories) {
        if (!getFolder(directory.path)) throw new Error(`directory is missing: ${directory.path}`);
      }
      for (const [path, expectedContent] of expectedFiles) {
        const file = getFile(path);
        if (!file) throw new Error(`file is missing: ${path}`);
        if (await app.vault.read(file) !== expectedContent) throw new Error(`file content mismatch: ${path}`);
      }
      for (const keep of payload.gitkeeps) {
        if (!await adapter.exists(keep)) throw new Error(`gitkeep is missing: ${keep}`);
        if ((await adapter.read(keep)).trim() !== "") throw new Error(`gitkeep is not empty: ${keep}`);
      }
      return emit({
        ok: true,
        op: operation,
        postconditions: ["visible inventory is exact", "root contains only one Base", "contents match the confirmed spec", "gitkeeps are empty"],
      });
    }
    if (operation === "validate_base_open") {
      const leaves = app.workspace.getLeavesOfType("bases");
      const open = leaves.some((leaf) => leaf.view?.file?.path === payload.base.path);
      if (!open) throw new Error(`Base is not open in a bases view: ${payload.base.path}`);
      return emit({ok: true, op: operation, baseOpen: true});
    }
    if (operation === "renumber_preflight") {
      const postconditions = await validateRenumberPreflight();
      return emit({ok: true, op: operation, postconditions});
    }
    if (operation === "renumber") {
      await validateRenumberPreflight();
      const items = payload.moves.map((move, index) => ({
        ...move,
        folder: getFolder(move.from),
        temporary: `${payload.root}/__lt_tmp_${payload.run_id}_${index}`,
        rollback: `${payload.root}/__lt_rollback_${payload.run_id}_${index}`,
      }));
      const added = [];
      const metadataSnapshots = [];
      try {
        for (const item of items) {
          await app.fileManager.renameFile(item.folder, item.temporary);
          if (item.folder.path !== item.temporary || !getFolder(item.temporary)) {
            throw new Error(`temporary rename postcondition failed: ${item.from}`);
          }
        }
        for (const item of items) {
          await app.fileManager.renameFile(item.folder, item.to);
          if (item.folder.path !== item.to || !getFolder(item.to)) {
            throw new Error(`final rename postcondition failed: ${item.to}`);
          }
        }
        for (const addition of payload.add_directories || []) {
          await app.vault.createFolder(addition.path);
          added.push(addition.path);
          if (!getFolder(addition.path)) throw new Error(`added directory postcondition failed: ${addition.path}`);
          if (addition.keep) {
            const keep = `${addition.path}/.gitkeep`;
            await adapter.write(keep, "");
            if (!await adapter.exists(keep) || (await adapter.read(keep)).trim() !== "") {
              throw new Error(`added gitkeep postcondition failed: ${keep}`);
            }
          }
        }
        for (const update of payload.property_updates || []) {
          const file = getFile(update.path);
          if (!file) throw new Error(`property update target is missing: ${update.path}`);
          const values = {stage_title: update.stage_title, stage_order: update.stage_order};
          if (update.updated !== undefined) values.updated = update.updated;
          const snapshot = {file, values: {}};
          metadataSnapshots.push(snapshot);
          await app.fileManager.processFrontMatter(file, (frontmatter) => {
            for (const [key, value] of Object.entries(values)) {
              snapshot.values[key] = Object.prototype.hasOwnProperty.call(frontmatter, key)
                ? {present: true, value: frontmatter[key]}
                : {present: false};
              frontmatter[key] = value;
            }
          });
        }
        await validateLinkExpectations();
        await waitForMetadata();
        for (const update of payload.property_updates || []) {
          const file = getFile(update.path);
          const frontmatter = file ? app.metadataCache.getFileCache(file)?.frontmatter : null;
          if (!frontmatter || frontmatter.stage_title !== update.stage_title || Number(frontmatter.stage_order) !== update.stage_order) {
            throw new Error(`property update postcondition failed: ${update.path}`);
          }
          if (update.updated !== undefined && String(frontmatter.updated) !== update.updated) {
            throw new Error(`updated property postcondition failed: ${update.path}`);
          }
        }
        for (const item of items) {
          if (!getFolder(item.to)) throw new Error(`final target missing: ${item.to}`);
          if (!payload.moves.some((move) => move.to === item.from) && getFolder(item.from)) {
            throw new Error(`old source remains: ${item.from}`);
          }
          if (getFolder(item.temporary) || getFolder(item.rollback)) {
            throw new Error(`temporary rename directory remains for ${item.from}`);
          }
        }
        return emit({
          ok: true,
          op: operation,
          postconditions: [
            `renamed ${items.length} directories in two phases`,
            `added ${added.length} directories`,
            `updated ${metadataSnapshots.length} note property sets`,
            `validated ${(payload.expected_links || []).length} link expectations`,
            "no temporary directories remain",
          ],
        });
      } catch (error) {
        const rollbackErrors = [];
        for (const snapshot of [...metadataSnapshots].reverse()) {
          try {
            await app.fileManager.processFrontMatter(snapshot.file, (frontmatter) => {
              for (const [key, prior] of Object.entries(snapshot.values)) {
                if (prior.present) frontmatter[key] = prior.value;
                else delete frontmatter[key];
              }
            });
          } catch (rollbackError) {
            rollbackErrors.push(`properties ${snapshot.file.path}: ${rollbackError.message}`);
          }
        }
        for (const path of [...added].reverse()) {
          try {
            const folder = getFolder(path);
            if (folder) await app.fileManager.trashFile(folder);
          } catch (rollbackError) {
            rollbackErrors.push(`trash ${path}: ${rollbackError.message}`);
          }
        }
        for (const item of items) {
          try {
            if (item.folder.path !== item.from) await app.fileManager.renameFile(item.folder, item.rollback);
          } catch (rollbackError) {
            rollbackErrors.push(`stage ${item.from}: ${rollbackError.message}`);
          }
        }
        for (const item of items) {
          try {
            if (item.folder.path === item.rollback) await app.fileManager.renameFile(item.folder, item.from);
          } catch (rollbackError) {
            rollbackErrors.push(`restore ${item.from}: ${rollbackError.message}`);
          }
        }
        const rolledBack = rollbackErrors.length === 0 && items.every((item) => item.folder.path === item.from);
        return emit({ok: false, op: operation, error: error.message, rolled_back: rolledBack, rollback_errors: rollbackErrors});
      }
    }
    if (operation === "trash_validation_preflight" || operation === "trash_validation") {
      assertTrashIsRecoverable();
      const root = getFolder(payload.root);
      if (!root) throw new Error(`validation root is missing: ${payload.root}`);
      const markerFile = getFile(payload.marker_path);
      if (!markerFile) throw new Error(`validation marker note is missing: ${payload.marker_path}`);
      const markerBody = await app.vault.read(markerFile);
      if (!markerBody.includes("learn_topic_test_run:") || !markerBody.includes(payload.run_id)) {
        throw new Error("validation marker does not match run_id");
      }
      const actualInventory = await collectAdapterInventory(payload.root);
      const expectedInventory = [...payload.expected_inventory].sort();
      if (JSON.stringify(actualInventory) !== JSON.stringify(expectedInventory)) {
        throw new Error(`validation inventory mismatch: ${JSON.stringify(actualInventory)}`);
      }
      if (operation === "trash_validation") {
        await app.fileManager.trashFile(root);
        if (getFolder(payload.root) || await adapter.exists(payload.root)) {
          throw new Error(`validation root still exists after trash: ${payload.root}`);
        }
        return emit({ok: true, op: operation, postconditions: ["marker and inventory matched", "validation root moved to recoverable trash"]});
      }
      return emit({ok: true, op: operation, postconditions: ["marker and inventory matched", "trash is recoverable"]});
    }
    throw new Error(`unsupported operation: ${operation}`);
  } catch (error) {
    return emit({ok: false, op: "unknown", error: error?.message || String(error)});
  }
})()
'''


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Create and run ordinary learn-topic code exercises outside an Obsidian Vault.

The driver is intentionally separate from repository_cli.py. It never creates
the user-selected workspace root, never writes Vault content, never invokes a
shell, and records each execution as an append-only evidence file.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
import platform
from typing import Any, Iterable


DIRECTORY_RE = re.compile(r"^\d{2}-[^/\\\x00-\x1f\x7f]+$")
EXERCISE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
COMMAND_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ATTEMPT_RE = re.compile(r"^attempt-(\d{2,})\.json$")
SHELLS = {"bash", "cmd", "fish", "powershell", "pwsh", "sh", "zsh"}
SECRET_KEYS = ("TOKEN", "SECRET", "PASSWORD", "PASSWD", "API_KEY", "AUTHORIZATION", "COOKIE")
SECRET_VALUES = ("authorization:", "bearer ", "sk-", "ghp_", "github_pat_")
FILE_ROLES = {"starter", "core_test", "config", "fixture", "support", "variant_test"}
COMMAND_KINDS = {"test", "lint", "format", "typecheck", "variant"}
STATUS_VALUES = {"passed", "failed", "timeout", "blocked"}


class ContractError(RuntimeError):
    """Raised when an exercise plan, package, or execution violates policy."""


def emit(value: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True), file=stream)


def require_keys(mapping: dict[str, Any], keys: Iterable[str], *, label: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ContractError(f"{label} missing keys: {', '.join(missing)}")


def ensure_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ContractError(f"{label} must be a normalized non-empty string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ContractError(f"{label} contains a control character")
    return value


def resolve_existing_directory(value: Any, *, label: str) -> Path:
    text = ensure_text(value, label=label)
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        raise ContractError(f"{label} must be absolute")
    if candidate.is_symlink():
        raise ContractError(f"{label} must not be a symbolic link")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise ContractError(f"{label} must already exist: {error}") from error
    if not resolved.is_dir():
        raise ContractError(f"{label} must be an existing directory")
    return resolved


def ensure_outside(path: Path, boundary: Path, *, label: str) -> None:
    try:
        path.relative_to(boundary)
    except ValueError:
        return
    raise ContractError(f"{label} must stay outside the Vault")


def safe_relative_path(value: Any, *, label: str, allow_dot: bool = False) -> str:
    text = ensure_text(value, label=label)
    if text == "." and allow_dot:
        return text
    if "\\" in text or text.startswith("/"):
        raise ContractError(f"{label} must be a POSIX package-relative path")
    parts = PurePosixPath(text).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ContractError(f"{label} contains an unsafe segment")
    if parts[0] == ".learn-topic":
        raise ContractError(f"{label} must not target .learn-topic")
    return PurePosixPath(*parts).as_posix()


def ensure_plan_local_file(value: Any, *, plan_dir: Path, label: str) -> Path:
    text = ensure_text(value, label=label)
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = plan_dir / candidate
    if candidate.is_symlink():
        raise ContractError(f"{label} must not be a symbolic link")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(plan_dir)
    except (OSError, ValueError) as error:
        raise ContractError(f"{label} must be an existing file inside the plan directory") from error
    if not resolved.is_file():
        raise ContractError(f"{label} must be a regular file")
    return resolved


def validate_env(value: Any, *, label: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    result: dict[str, str] = {}
    for key, item in value.items():
        normalized_key = ensure_text(key, label=f"{label} key")
        normalized_value = ensure_text(item, label=f"{label}.{normalized_key}")
        upper = normalized_key.upper()
        if any(marker in upper for marker in SECRET_KEYS):
            raise ContractError(f"{label} must not contain secret-like key {normalized_key}")
        lowered = normalized_value.casefold()
        if any(marker in lowered for marker in SECRET_VALUES):
            raise ContractError(f"{label}.{normalized_key} appears to contain a secret")
        result[normalized_key] = normalized_value
    return result


def normalize_argv(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{label} must be a non-empty argv array")
    argv = [ensure_text(item, label=f"{label}[{index}]") for index, item in enumerate(value)]
    executable = Path(argv[0]).name.casefold()
    if executable in SHELLS and any(argument.casefold() in {"-c", "/c"} for argument in argv[1:]):
        raise ContractError(f"{label} must not execute a shell command string")
    flattened = " ".join(argv).casefold()
    if any(marker in flattened for marker in SECRET_VALUES):
        raise ContractError(f"{label} appears to contain a secret")
    return argv


def normalize_command(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    require_keys(
        value,
        ("id", "kind", "argv", "cwd", "env", "timeout_seconds", "required", "visible", "effects"),
        label=label,
    )
    command_id = ensure_text(value["id"], label=f"{label}.id")
    if not COMMAND_ID_RE.fullmatch(command_id):
        raise ContractError(f"{label}.id must use lowercase letters, digits, and hyphens")
    kind = ensure_text(value["kind"], label=f"{label}.kind")
    if kind not in COMMAND_KINDS:
        raise ContractError(f"{label}.kind is unsupported")
    if value["visible"] is not True:
        raise ContractError("hidden exercise commands and tests are forbidden")
    if not isinstance(value["required"], bool):
        raise ContractError(f"{label}.required must be boolean")
    timeout = value["timeout_seconds"]
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 900:
        raise ContractError(f"{label}.timeout_seconds must be an integer from 1 to 900")
    effects = value["effects"]
    if not isinstance(effects, list):
        raise ContractError(f"{label}.effects must be an array")
    normalized_effects: list[str] = []
    for index, effect in enumerate(effects):
        text = ensure_text(effect, label=f"{label}.effects[{index}]")
        if text in normalized_effects:
            raise ContractError(f"{label}.effects contains duplicate {text}")
        normalized_effects.append(text)
    return {
        "id": command_id,
        "kind": kind,
        "argv": normalize_argv(value["argv"], label=f"{label}.argv"),
        "cwd": safe_relative_path(value["cwd"], label=f"{label}.cwd", allow_dot=True),
        "env": validate_env(value["env"], label=f"{label}.env"),
        "timeout_seconds": timeout,
        "required": value["required"],
        "visible": True,
        "effects": normalized_effects,
    }


def validate_exercise(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("exercise must be an object")
    require_keys(
        value,
        (
            "id", "version", "topic", "lesson_id", "title", "language", "version_scope",
            "goal", "layout", "core_requirements", "explanation_prompts", "rubric", "hints",
            "optional_challenges",
        ),
        label="exercise",
    )
    exercise_id = ensure_text(value["id"], label="exercise.id")
    if not EXERCISE_ID_RE.fullmatch(exercise_id):
        raise ContractError("exercise.id contains unsupported characters")
    if not isinstance(value["version"], int) or isinstance(value["version"], bool) or value["version"] < 1:
        raise ContractError("exercise.version must be a positive integer")
    layout = ensure_text(value["layout"], label="exercise.layout")
    if layout not in {"standalone", "project"}:
        raise ContractError("exercise.layout must be standalone or project")
    for field in ("core_requirements", "explanation_prompts"):
        items = value[field]
        if not isinstance(items, list) or not items:
            raise ContractError(f"exercise.{field} must be a non-empty array")
        for index, item in enumerate(items):
            ensure_text(item, label=f"exercise.{field}[{index}]")
    rubric = value["rubric"]
    if not isinstance(rubric, list) or not rubric:
        raise ContractError("exercise.rubric must be a non-empty array")
    points = 0
    for index, item in enumerate(rubric):
        if not isinstance(item, dict):
            raise ContractError(f"exercise.rubric[{index}] must be an object")
        require_keys(item, ("criterion", "points"), label=f"exercise.rubric[{index}]")
        ensure_text(item["criterion"], label=f"exercise.rubric[{index}].criterion")
        if not isinstance(item["points"], int) or isinstance(item["points"], bool) or item["points"] <= 0:
            raise ContractError(f"exercise.rubric[{index}].points must be a positive integer")
        points += item["points"]
    if points != 100:
        raise ContractError("exercise.rubric points must total 100")
    hints = value["hints"]
    if not isinstance(hints, list) or [item.get("level") if isinstance(item, dict) else None for item in hints] != [1, 2, 3]:
        raise ContractError("exercise.hints must contain exactly levels 1, 2, and 3")
    for index, item in enumerate(hints):
        ensure_text(item.get("content"), label=f"exercise.hints[{index}].content")
    challenges = value["optional_challenges"]
    if not isinstance(challenges, list) or len(challenges) > 2:
        raise ContractError("exercise.optional_challenges must contain at most two items")
    for index, challenge in enumerate(challenges):
        ensure_text(challenge, label=f"exercise.optional_challenges[{index}]")
    return {
        "id": exercise_id,
        "version": value["version"],
        "topic": ensure_text(value["topic"], label="exercise.topic"),
        "lesson_id": ensure_text(value["lesson_id"], label="exercise.lesson_id"),
        "title": ensure_text(value["title"], label="exercise.title"),
        "language": ensure_text(value["language"], label="exercise.language"),
        "version_scope": ensure_text(value["version_scope"], label="exercise.version_scope"),
        "goal": ensure_text(value["goal"], label="exercise.goal"),
        "layout": layout,
        "core_requirements": value["core_requirements"],
        "explanation_prompts": value["explanation_prompts"],
        "rubric": rubric,
        "hints": hints,
        "optional_challenges": challenges,
        "answer_policy": {
            "user_attempt_required": True,
            "full_solution_after": "verified-attempt-or-explicit-request",
            "model_written_result_counts_as_mastery": False,
        },
    }


def load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise ContractError(f"{label} must not be a symbolic link")
    try:
        resolved = path.resolve(strict=True)
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot read {label}: {error}") from error
    if not isinstance(raw, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return raw


def load_scaffold_plan(path_value: str) -> dict[str, Any]:
    plan_path = Path(path_value).expanduser().resolve(strict=True)
    raw = load_json_object(plan_path, label="exercise plan")
    require_keys(
        raw,
        (
            "schema_version", "vault_root", "workspace_root", "exercise_directory", "exercise",
            "files", "commands", "runtime_write_paths", "cleanup_paths",
        ),
        label="exercise plan",
    )
    if raw["schema_version"] != 1:
        raise ContractError("exercise plan schema_version must be 1")
    vault_root = resolve_existing_directory(raw["vault_root"], label="vault_root")
    workspace_root = resolve_existing_directory(raw["workspace_root"], label="workspace_root")
    ensure_outside(workspace_root, vault_root, label="workspace_root")
    directory = ensure_text(raw["exercise_directory"], label="exercise_directory")
    if not DIRECTORY_RE.fullmatch(directory) or directory.startswith("99-"):
        raise ContractError("exercise_directory must use NN-name and must not be 99-assets")
    exercise = validate_exercise(raw["exercise"])
    files = raw["files"]
    if not isinstance(files, list) or not files:
        raise ContractError("files must be a non-empty array")
    normalized_files: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for index, item in enumerate(files):
        label = f"files[{index}]"
        if not isinstance(item, dict):
            raise ContractError(f"{label} must be an object")
        require_keys(item, ("path", "role", "content_file", "user_editable"), label=label)
        relative = safe_relative_path(item["path"], label=f"{label}.path")
        if relative in seen_paths:
            raise ContractError(f"duplicate exercise file {relative}")
        seen_paths.add(relative)
        role = ensure_text(item["role"], label=f"{label}.role")
        if role not in FILE_ROLES:
            raise ContractError(f"{label}.role is unsupported")
        if "solution" in role.casefold() or "solution" in relative.casefold() or "answer" in relative.casefold():
            raise ContractError("scaffold must not include a solution or answer file")
        if not isinstance(item["user_editable"], bool):
            raise ContractError(f"{label}.user_editable must be boolean")
        content = ensure_plan_local_file(item["content_file"], plan_dir=plan_path.parent, label=f"{label}.content_file")
        normalized_files.append(
            {"path": relative, "role": role, "content_file": str(content), "user_editable": item["user_editable"]}
        )
    if not any(item["role"] == "starter" and item["user_editable"] for item in normalized_files):
        raise ContractError("files must include a user-editable starter")
    if not any(item["role"] == "core_test" and not item["user_editable"] for item in normalized_files):
        raise ContractError("files must include a non-editable public core_test")
    if exercise["layout"] == "standalone":
        editable = [PurePosixPath(item["path"]).name for item in normalized_files if item["user_editable"]]
        if len(editable) != 1 or not re.match(r"^\d{2}-[^/]+\.[A-Za-z0-9]+$", editable[0]):
            raise ContractError("standalone layout requires one numbered user-editable script")
    commands_raw = raw["commands"]
    if not isinstance(commands_raw, list) or not commands_raw:
        raise ContractError("commands must be a non-empty array")
    commands = [normalize_command(item, label=f"commands[{index}]") for index, item in enumerate(commands_raw)]
    ids = [item["id"] for item in commands]
    if len(ids) != len(set(ids)):
        raise ContractError("command ids must be unique")
    if not any(item["kind"] == "test" and item["required"] for item in commands):
        raise ContractError("commands must include a required public core test")
    runtime_paths = normalize_relative_list(raw["runtime_write_paths"], label="runtime_write_paths")
    cleanup_paths = normalize_relative_list(raw["cleanup_paths"], label="cleanup_paths")
    if not set(cleanup_paths).issubset(runtime_paths):
        raise ContractError("cleanup_paths must be a subset of runtime_write_paths")
    validate_runtime_scope(normalized_files, runtime_paths)
    validate_cleanup_scope(normalized_files, cleanup_paths)
    return {
        "schema_version": 1,
        "vault_root": str(vault_root),
        "workspace_root": str(workspace_root),
        "exercise_directory": directory,
        "exercise": exercise,
        "files": normalized_files,
        "commands": commands,
        "runtime_write_paths": runtime_paths,
        "cleanup_paths": cleanup_paths,
        "plan_path": str(plan_path),
    }


def normalize_relative_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be an array")
    result: list[str] = []
    for index, item in enumerate(value):
        relative = safe_relative_path(item, label=f"{label}[{index}]")
        if relative in result:
            raise ContractError(f"{label} contains duplicate {relative}")
        result.append(relative)
    return result


def validate_cleanup_scope(files: list[dict[str, Any]], cleanup_paths: list[str]) -> None:
    protected = [PurePosixPath(item["path"]) for item in files]
    for cleanup in cleanup_paths:
        cleanup_path = PurePosixPath(cleanup)
        for managed in protected:
            if cleanup_path == managed or cleanup_path in managed.parents or managed in cleanup_path.parents:
                raise ContractError(f"cleanup path overlaps protected exercise file: {cleanup}")


def validate_runtime_scope(files: list[dict[str, Any]], runtime_paths: list[str]) -> None:
    protected = [PurePosixPath(item["path"]) for item in files if not item["user_editable"]]
    for runtime in runtime_paths:
        runtime_path = PurePosixPath(runtime)
        for managed in protected:
            if runtime_path == managed or runtime_path in managed.parents or managed in runtime_path.parents:
                raise ContractError(f"runtime path overlaps confirmed non-user file: {runtime}")


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest_sha256(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(manifest_bytes(manifest)).hexdigest()


def atomic_write_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def atomic_replace(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(content)
    temporary.replace(path)


def public_manifest(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "vault_root": plan["vault_root"],
        "workspace_root": plan["workspace_root"],
        "exercise": plan["exercise"],
        "exercise_directory": plan["exercise_directory"],
        "files": [
            {
                "path": item["path"],
                "role": item["role"],
                "user_editable": item["user_editable"],
                "sha256": hashlib.sha256(Path(item["content_file"]).read_bytes()).hexdigest(),
            }
            for item in plan["files"]
        ],
        "commands": plan["commands"],
        "runtime_write_paths": plan["runtime_write_paths"],
        "cleanup_paths": plan["cleanup_paths"],
    }


def scaffold(plan: dict[str, Any], *, apply: bool) -> dict[str, Any]:
    package = Path(plan["workspace_root"]) / plan["exercise_directory"]
    if package.exists():
        raise ContractError("exercise package already exists; scaffold never overwrites it")
    preview = {
        "ok": True,
        "op": "scaffold",
        "mode": "apply" if apply else "dry-run",
        "exercise_id": plan["exercise"]["id"],
        "workspace_root": plan["workspace_root"],
        "exercise_directory": plan["exercise_directory"],
        "files": [item["path"] for item in plan["files"]],
        "commands": [command_preview(item) for item in plan["commands"]],
    }
    if not apply:
        return preview
    package.mkdir(mode=0o755)
    try:
        for item in plan["files"]:
            target = package / PurePosixPath(item["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_new(target, Path(item["content_file"]).read_bytes())
        metadata = package / ".learn-topic"
        (metadata / "evidence").mkdir(parents=True)
        atomic_write_new(metadata / "manifest.json", manifest_bytes(public_manifest(plan)))
    except Exception:
        shutil.rmtree(package)
        raise
    preview["manifest_sha256"] = manifest_sha256(public_manifest(plan))
    return preview


def command_preview(command: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": command["id"],
        "kind": command["kind"],
        "argv": command["argv"],
        "cwd": command["cwd"],
        "env": command["env"],
        "timeout_seconds": command["timeout_seconds"],
        "required": command["required"],
        "effects": command["effects"],
    }


def load_manifest(path_value: str) -> tuple[Path, Path, dict[str, Any]]:
    path = Path(path_value).expanduser()
    raw = load_json_object(path, label="exercise manifest")
    resolved = path.resolve(strict=True)
    if resolved.name != "manifest.json" or resolved.parent.name != ".learn-topic":
        raise ContractError("manifest must be <exercise>/.learn-topic/manifest.json")
    package = resolved.parent.parent.resolve(strict=True)
    require_keys(
        raw,
        (
            "schema_version", "vault_root", "workspace_root", "exercise", "exercise_directory",
            "files", "commands", "runtime_write_paths", "cleanup_paths",
        ),
        label="exercise manifest",
    )
    if raw["schema_version"] != 1 or package.name != raw["exercise_directory"]:
        raise ContractError("manifest identity does not match the exercise directory")
    vault_root = resolve_existing_directory(raw["vault_root"], label="manifest vault_root")
    workspace_root = resolve_existing_directory(raw["workspace_root"], label="manifest workspace_root")
    ensure_outside(workspace_root, vault_root, label="manifest workspace_root")
    if package.parent != workspace_root:
        raise ContractError("exercise package must be a direct child of manifest workspace_root")
    exercise = validate_exercise(raw["exercise"])
    files = raw["files"]
    if not isinstance(files, list) or not files:
        raise ContractError("manifest files must be a non-empty array")
    normalized_files: list[dict[str, Any]] = []
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise ContractError(f"manifest files[{index}] must be an object")
        require_keys(item, ("path", "role", "user_editable", "sha256"), label=f"manifest files[{index}]")
        relative = safe_relative_path(item["path"], label=f"manifest files[{index}].path")
        role = ensure_text(item["role"], label=f"manifest files[{index}].role")
        if role not in FILE_ROLES or not isinstance(item["user_editable"], bool):
            raise ContractError(f"manifest files[{index}] is invalid")
        target = package / PurePosixPath(relative)
        if not target.is_file() or target.is_symlink():
            raise ContractError(f"manifest file is missing or unsafe: {relative}")
        expected_hash = ensure_text(item["sha256"], label=f"manifest files[{index}].sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ContractError(f"manifest files[{index}].sha256 must be lowercase SHA-256")
        if not item["user_editable"] and hash_file(target) != expected_hash:
            raise ContractError(f"confirmed non-user file changed: {relative}")
        normalized_files.append(
            {
                "path": relative,
                "role": role,
                "user_editable": item["user_editable"],
                "sha256": expected_hash,
            }
        )
    commands = raw["commands"]
    if not isinstance(commands, list) or not commands:
        raise ContractError("manifest commands must be a non-empty array")
    normalized_commands = [normalize_command(item, label=f"manifest commands[{index}]") for index, item in enumerate(commands)]
    ids = [item["id"] for item in normalized_commands]
    if len(ids) != len(set(ids)):
        raise ContractError("manifest command ids must be unique")
    if not any(item["role"] == "starter" and item["user_editable"] for item in normalized_files):
        raise ContractError("manifest must retain a user-editable starter")
    if not any(item["role"] == "core_test" and not item["user_editable"] for item in normalized_files):
        raise ContractError("manifest must retain a public core_test")
    if not any(item["kind"] == "test" and item["required"] for item in normalized_commands):
        raise ContractError("manifest must retain a required public core test command")
    normalized = {
        "schema_version": 1,
        "vault_root": str(vault_root),
        "workspace_root": str(workspace_root),
        "exercise": exercise,
        "exercise_directory": raw["exercise_directory"],
        "files": normalized_files,
        "commands": normalized_commands,
        "runtime_write_paths": normalize_relative_list(raw["runtime_write_paths"], label="manifest runtime_write_paths"),
        "cleanup_paths": normalize_relative_list(raw["cleanup_paths"], label="manifest cleanup_paths"),
    }
    if not set(normalized["cleanup_paths"]).issubset(normalized["runtime_write_paths"]):
        raise ContractError("manifest cleanup_paths must be a subset of runtime_write_paths")
    validate_runtime_scope(normalized_files, normalized["runtime_write_paths"])
    validate_cleanup_scope(normalized_files, normalized["cleanup_paths"])
    return resolved, package, normalized


def get_command(manifest: dict[str, Any], command_id: str) -> dict[str, Any]:
    normalized = ensure_text(command_id, label="command")
    for command in manifest["commands"]:
        if command["id"] == normalized:
            return command
    raise ContractError(f"manifest has no command {normalized}")


def authorize(
    manifest_path: Path,
    package: Path,
    manifest: dict[str, Any],
    *,
    command_id: str,
    confirmed_at: str,
    apply: bool,
) -> dict[str, Any]:
    command = get_command(manifest, command_id)
    try:
        datetime.fromisoformat(ensure_text(confirmed_at, label="confirmed_at").replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError("confirmed_at must be an ISO datetime") from error
    digest = manifest_sha256(manifest)
    authorization = {
        "schema_version": 1,
        "manifest_sha256": digest,
        "confirmed_at": confirmed_at,
        "commands": {command_id: command_preview(command)},
    }
    destination = package / ".learn-topic" / "authorization.json"
    if destination.exists():
        current = load_json_object(destination, label="exercise authorization")
        if current.get("manifest_sha256") == digest and isinstance(current.get("commands"), dict):
            authorization["commands"] = {**current["commands"], command_id: command_preview(command)}
    result = {
        "ok": True,
        "op": "authorize",
        "mode": "apply" if apply else "dry-run",
        "manifest_sha256": digest,
        "command": command_preview(command),
        "runtime_write_paths": manifest["runtime_write_paths"],
        "cleanup_paths": manifest["cleanup_paths"],
        "isolation": "macos-sandbox-exec-or-blocked",
    }
    if apply:
        atomic_replace(destination, manifest_bytes(authorization))
    return result


def clean_environment(package: Path, command: dict[str, Any]) -> tuple[dict[str, str], tempfile.TemporaryDirectory[str]]:
    temporary_home = tempfile.TemporaryDirectory(prefix="learn-topic-exercise-")
    environment: dict[str, str] = {}
    for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "SYSTEMROOT", "PATHEXT"):
        value = os.environ.get(key)
        if value:
            environment[key] = value
    browser_cache_candidates = (
        Path.home() / "Library" / "Caches" / "ms-playwright",
        Path.home() / ".cache" / "ms-playwright",
    )
    browser_cache = next(
        (candidate.resolve() for candidate in browser_cache_candidates if candidate.is_dir()),
        None,
    )
    environment.update(
        {
            "HOME": temporary_home.name,
            "TMPDIR": temporary_home.name,
            "XDG_CONFIG_HOME": str(Path(temporary_home.name) / ".config"),
            "CI": "true",
            "PYTHONDONTWRITEBYTECODE": "1",
            **command["env"],
        }
    )
    if browser_cache is not None:
        # Keep the clean HOME while allowing Playwright to read preinstalled
        # browser binaries; the sandbox still denies writes to this cache.
        environment["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_cache)
    return environment, temporary_home


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_under(relative: str, roots: list[str]) -> bool:
    path = PurePosixPath(relative)
    for root in roots:
        root_path = PurePosixPath(root)
        if path == root_path or root_path in path.parents:
            return True
    return False


def workspace_snapshot(workspace_root: Path, package: Path) -> dict[str, str]:
    """Hash the user-approved external root outside the active package."""
    result: dict[str, str] = {}
    for path in sorted(workspace_root.rglob("*")):
        try:
            path.relative_to(package)
            continue
        except ValueError:
            pass
        relative = path.relative_to(workspace_root).as_posix()
        if path.is_symlink():
            result[relative] = "L:" + hashlib.sha256(os.readlink(path).encode("utf-8")).hexdigest()
        elif path.is_file():
            result[relative] = "F:" + hash_file(path)
        elif path.is_dir():
            result[relative] = "D"
        else:
            result[relative] = "O"
    return result


def metadata_snapshot(package: Path) -> dict[str, bytes]:
    metadata = package / ".learn-topic"
    if not metadata.is_dir() or metadata.is_symlink():
        raise ContractError("exercise metadata directory is missing or unsafe")
    result: dict[str, bytes] = {}
    for path in sorted(metadata.rglob("*")):
        if path.is_symlink():
            raise ContractError("exercise metadata must not contain symbolic links")
        if path.is_file():
            result[path.relative_to(metadata).as_posix()] = path.read_bytes()
    return result


def restore_metadata(package: Path, expected: dict[str, bytes]) -> None:
    """Restore only the protected metadata tree after a command violates scope."""
    metadata = package / ".learn-topic"
    if metadata.is_symlink() or (metadata.exists() and not metadata.is_dir()):
        metadata.unlink()
    metadata.mkdir(parents=True, exist_ok=True)
    current_files = []
    for root, directories, files in os.walk(metadata, topdown=True, followlinks=False):
        root_path = Path(root)
        for directory in list(directories):
            child = root_path / directory
            if child.is_symlink():
                child.unlink()
                directories.remove(directory)
        current_files.extend(root_path / name for name in files)
    for path in current_files:
        relative = path.relative_to(metadata).as_posix()
        if relative not in expected:
            path.unlink()
    for relative, content in expected.items():
        atomic_replace(metadata / PurePosixPath(relative), content)
    for root, directories, files in os.walk(metadata, topdown=False, followlinks=False):
        path = Path(root)
        if path != metadata and not any(path.iterdir()):
            path.rmdir()


def sandbox_argv(
    package: Path,
    manifest: dict[str, Any],
    command: dict[str, Any],
    temporary_home: str,
) -> list[str] | None:
    """Return a macOS sandboxed argv, or None when safe isolation is unavailable."""
    if platform.system() != "Darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        return None
    # macOS commonly exposes temporary directories through symlinks such as
    # /var -> /private/var.  sandbox-exec matches the kernel's canonical path,
    # so every writable path must be resolved before embedding it in the profile.
    # pytest and a few standard-library handlers open /dev/null for output;
    # allowing that device does not expose a user-data path.
    writable = [Path(temporary_home).resolve(), Path('/dev/null')]
    writable.extend(
        (package / PurePosixPath(relative)).resolve()
        for relative in manifest["runtime_write_paths"]
    )
    clauses = ["(version 1)", "(allow default)", "(deny file-write*)"]
    if "network" not in command["effects"]:
        clauses.append("(deny network*)")
    for path in writable:
        encoded = json.dumps(str(path), ensure_ascii=False)
        clauses.append(f"(allow file-write* (literal {encoded}) (subpath {encoded}))")
    profile = " ".join(clauses)
    return ["/usr/bin/sandbox-exec", "-p", profile, "--", *command["argv"]]


def looks_like_sandbox_violation(stderr: bytes) -> bool:
    text = stderr.decode("utf-8", "replace").casefold()
    return any(marker in text for marker in ("operation not permitted", "sandbox", "permissionerror"))


def package_snapshot(package: Path, manifest: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(package.rglob("*")):
        if path.is_symlink():
            raise ContractError("exercise package must not contain symbolic links")
        if not path.is_file():
            continue
        relative = path.relative_to(package).as_posix()
        if relative.startswith(".learn-topic/") or is_under(relative, manifest["runtime_write_paths"]):
            continue
        result[relative] = hash_file(path)
    return result


def code_hashes(package: Path, manifest: dict[str, Any]) -> dict[str, str]:
    return {
        item["path"]: hash_file(package / PurePosixPath(item["path"]))
        for item in manifest["files"]
        if item["user_editable"]
    }


def parse_test_counts(output: str) -> dict[str, int | None]:
    result: dict[str, int | None] = {"passed": None, "failed": None, "errors": None, "skipped": None}
    patterns = {
        "passed": r"(?i)\b(\d+)\s+passed\b",
        "failed": r"(?i)\b(\d+)\s+failed\b",
        "errors": r"(?i)\b(\d+)\s+errors?\b",
        "skipped": r"(?i)\b(\d+)\s+skipped\b",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, output)
        if match:
            result[key] = int(match.group(1))
    unittest = re.search(r"Ran\s+(\d+)\s+tests?", output)
    if unittest and "OK" in output and result["passed"] is None:
        result["passed"] = int(unittest.group(1))
        result["failed"] = 0
        result["errors"] = 0
    return result


def next_attempt_path(evidence_dir: Path) -> tuple[str, Path]:
    numbers = []
    if evidence_dir.exists():
        for path in evidence_dir.iterdir():
            match = ATTEMPT_RE.fullmatch(path.name)
            if match:
                numbers.append(int(match.group(1)))
    number = max(numbers, default=0) + 1
    attempt_id = f"attempt-{number:02d}"
    return attempt_id, evidence_dir / f"{attempt_id}.json"


def cleanup_declared(package: Path, manifest: dict[str, Any]) -> list[str]:
    removed: list[str] = []
    validate_cleanup_scope(manifest["files"], manifest["cleanup_paths"])
    for relative in manifest["cleanup_paths"]:
        if relative.startswith(".learn-topic"):
            raise ContractError(f"cleanup path targets protected content: {relative}")
        target = package / PurePosixPath(relative)
        if not target.exists() and not target.is_symlink():
            continue
        if target.is_symlink():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        removed.append(relative)
    return removed


def run_exercise(
    manifest_path: Path,
    package: Path,
    manifest: dict[str, Any],
    *,
    command_id: str,
    apply: bool,
) -> dict[str, Any]:
    command = get_command(manifest, command_id)
    preview = {
        "ok": True,
        "op": "run",
        "mode": "apply" if apply else "dry-run",
        "exercise_id": manifest["exercise"]["id"],
        "manifest_sha256": manifest_sha256(manifest),
        "command": command_preview(command),
        "runtime_write_paths": manifest["runtime_write_paths"],
        "cleanup_paths": manifest["cleanup_paths"],
    }
    if not apply:
        return preview
    authorization_path = package / ".learn-topic" / "authorization.json"
    authorization = load_json_object(authorization_path, label="exercise authorization")
    digest = manifest_sha256(manifest)
    if authorization.get("manifest_sha256") != digest:
        raise ContractError("exercise authorization is stale because manifest changed")
    authorized = authorization.get("commands", {}).get(command_id)
    if authorized != command_preview(command):
        raise ContractError("command does not match the confirmed authorization")
    cwd = package if command["cwd"] == "." else package / PurePosixPath(command["cwd"])
    if not cwd.is_dir() or cwd.is_symlink():
        raise ContractError("command cwd is missing or unsafe")
    # Re-check immutable public tests/config immediately before execution even
    # when a caller retained an earlier in-memory manifest object.
    for item in manifest["files"]:
        if not item["user_editable"]:
            target = package / PurePosixPath(item["path"])
            if not target.is_file() or target.is_symlink() or hash_file(target) != item["sha256"]:
                raise ContractError(f"confirmed non-user file changed: {item['path']}")
    workspace_root = Path(manifest["workspace_root"])
    before = package_snapshot(package, manifest)
    workspace_before = workspace_snapshot(workspace_root, package)
    metadata_before = metadata_snapshot(package)
    source_hashes = code_hashes(package, manifest)
    environment, temporary_home = clean_environment(package, command)
    isolated_argv = sandbox_argv(package, manifest, command, temporary_home.name)
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    started = time.monotonic()
    returncode: int | None = None
    stdout = b""
    stderr = b""
    status = "failed"
    try:
        if isolated_argv is None:
            status = "blocked"
            stderr = b"safe write isolation unavailable"
        else:
            completed = subprocess.run(
                isolated_argv,
                cwd=str(cwd),
                env=environment,
                capture_output=True,
                text=False,
                check=False,
                shell=False,
                timeout=command["timeout_seconds"],
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
            if returncode == 0:
                status = "passed"
            elif looks_like_sandbox_violation(stderr):
                status = "blocked"
            else:
                status = "failed"
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or b""
        stderr = error.stderr or b""
        status = "timeout"
    except OSError as error:
        stderr = type(error).__name__.encode("ascii", "replace")
        status = "blocked"
    finally:
        temporary_home.cleanup()
    duration_ms = int((time.monotonic() - started) * 1000)
    post_scope_error = False
    try:
        after = package_snapshot(package, manifest)
    except (ContractError, OSError):
        after = {}
        post_scope_error = True
    try:
        workspace_after = workspace_snapshot(workspace_root, package)
    except (ContractError, OSError):
        workspace_after = {}
        post_scope_error = True
    try:
        metadata_changed = metadata_snapshot(package) != metadata_before
    except ContractError:
        metadata_changed = True
    if metadata_changed:
        restore_metadata(package, metadata_before)
    immutable_changed = any(
        not item["user_editable"]
        and (
            not (package / PurePosixPath(item["path"])).is_file()
            or hash_file(package / PurePosixPath(item["path"])) != item["sha256"]
        )
        for item in manifest["files"]
    )
    try:
        final_source_hashes = code_hashes(package, manifest)
    except (ContractError, OSError):
        final_source_hashes = source_hashes
        post_scope_error = True
    if (
        post_scope_error
        or before != after
        or workspace_before != workspace_after
        or metadata_changed
        or immutable_changed
    ):
        status = "blocked"
    combined = (stdout + b"\n" + stderr).decode("utf-8", "replace")
    attempt_id, evidence_path = next_attempt_path(package / ".learn-topic" / "evidence")
    evidence = {
        "schema_version": 1,
        "exercise_id": manifest["exercise"]["id"],
        "exercise_version": manifest["exercise"]["version"],
        "attempt_id": attempt_id,
        "manifest_sha256": digest,
        "command_id": command_id,
        "argv": command["argv"],
        "status": status,
        "returncode": returncode,
        "duration_ms": duration_ms,
        "started_at": started_at,
        "code_sha256": final_source_hashes,
        "code_sha256_before": source_hashes,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "test_counts": parse_test_counts(combined),
    }
    atomic_write_new(evidence_path, manifest_bytes(evidence))
    removed = cleanup_declared(package, manifest)
    preview.update(
        {
            "ok": status == "passed",
            "attempt_id": attempt_id,
            "status": status,
            "returncode": returncode,
            "duration_ms": duration_ms,
            "test_counts": evidence["test_counts"],
            "cleaned": removed,
        }
    )
    return preview


def load_variant_plan(path_value: str) -> dict[str, Any]:
    plan_path = Path(path_value).expanduser().resolve(strict=True)
    raw = load_json_object(plan_path, label="variant plan")
    require_keys(raw, ("manifest", "challenge", "files", "command"), label="variant plan")
    manifest_path, package, manifest = load_manifest(raw["manifest"])
    ensure_text(raw["challenge"], label="challenge")
    if len(manifest["exercise"]["optional_challenges"]) >= 2:
        raise ContractError("an exercise may contain at most two optional challenges")
    files = raw["files"]
    if not isinstance(files, list) or not files:
        raise ContractError("variant files must be a non-empty array")
    normalized_files: list[dict[str, Any]] = []
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise ContractError(f"variant files[{index}] must be an object")
        require_keys(item, ("path", "content_file"), label=f"variant files[{index}]")
        relative = safe_relative_path(item["path"], label=f"variant files[{index}].path")
        if any(existing["path"] == relative for existing in manifest["files"]):
            raise ContractError(f"variant file already exists in manifest: {relative}")
        content = ensure_plan_local_file(item["content_file"], plan_dir=plan_path.parent, label=f"variant files[{index}].content_file")
        normalized_files.append({"path": relative, "content_file": str(content)})
    command = normalize_command(raw["command"], label="variant command")
    if command["kind"] != "variant" or command["required"]:
        raise ContractError("variant command must use kind variant and required false")
    if any(existing["id"] == command["id"] for existing in manifest["commands"]):
        raise ContractError("variant command id already exists")
    evidence_dir = package / ".learn-topic" / "evidence"
    if not any(ATTEMPT_RE.fullmatch(path.name) for path in evidence_dir.glob("attempt-*.json")):
        raise ContractError("a public variant can be added only after a recorded user attempt")
    return {
        "plan_path": str(plan_path),
        "manifest_path": str(manifest_path),
        "package": str(package),
        "manifest": manifest,
        "challenge": raw["challenge"],
        "files": normalized_files,
        "command": command,
    }


def add_variant(plan: dict[str, Any], *, apply: bool) -> dict[str, Any]:
    package = Path(plan["package"])
    result = {
        "ok": True,
        "op": "add-variant",
        "mode": "apply" if apply else "dry-run",
        "challenge": plan["challenge"],
        "files": [item["path"] for item in plan["files"]],
        "command": command_preview(plan["command"]),
        "authorization_invalidated": True,
    }
    if not apply:
        return result
    created: list[Path] = []
    try:
        for item in plan["files"]:
            target = package / PurePosixPath(item["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_new(target, Path(item["content_file"]).read_bytes())
            created.append(target)
        manifest = plan["manifest"]
        manifest["exercise"]["optional_challenges"].append(plan["challenge"])
        manifest["exercise"]["version"] += 1
        for item in plan["files"]:
            manifest["files"].append(
                {
                    "path": item["path"],
                    "role": "variant_test",
                    "user_editable": False,
                    "sha256": hash_file(package / PurePosixPath(item["path"])),
                }
            )
        manifest["commands"].append(plan["command"])
        atomic_replace(Path(plan["manifest_path"]), manifest_bytes(manifest))
        (package / ".learn-topic" / "authorization.json").unlink(missing_ok=True)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    result["manifest_sha256"] = manifest_sha256(plan["manifest"])
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command_name", required=True)
    scaffold_parser = subparsers.add_parser("scaffold", help="preview or create one exercise package")
    scaffold_parser.add_argument("--plan", required=True)
    scaffold_parser.add_argument("--apply", action="store_true")
    authorize_parser = subparsers.add_parser("authorize", help="record explicit command authorization")
    authorize_parser.add_argument("--manifest", required=True)
    authorize_parser.add_argument("--command", required=True)
    authorize_parser.add_argument("--confirmed-at", required=True)
    authorize_parser.add_argument("--apply", action="store_true")
    run_parser = subparsers.add_parser("run", help="preview or run one confirmed command")
    run_parser.add_argument("--manifest", required=True)
    run_parser.add_argument("--command", required=True)
    run_parser.add_argument("--apply", action="store_true")
    variant_parser = subparsers.add_parser("add-variant", help="preview or add one public post-attempt variant")
    variant_parser.add_argument("--plan", required=True)
    variant_parser.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command_name == "scaffold":
            result = scaffold(load_scaffold_plan(arguments.plan), apply=arguments.apply)
        elif arguments.command_name == "authorize":
            manifest_path, package, manifest = load_manifest(arguments.manifest)
            result = authorize(
                manifest_path,
                package,
                manifest,
                command_id=arguments.command,
                confirmed_at=arguments.confirmed_at,
                apply=arguments.apply,
            )
        elif arguments.command_name == "run":
            manifest_path, package, manifest = load_manifest(arguments.manifest)
            result = run_exercise(
                manifest_path,
                package,
                manifest,
                command_id=arguments.command,
                apply=arguments.apply,
            )
        else:
            result = add_variant(load_variant_plan(arguments.plan), apply=arguments.apply)
        emit(result)
        return 0 if result.get("ok", False) else 1
    except (ContractError, OSError, ValueError) as error:
        emit({"ok": False, "error": str(error)}, stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

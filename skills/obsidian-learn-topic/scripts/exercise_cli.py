#!/usr/bin/env python3
"""Manage code-practice scaffolds, command authorization, and external evidence.

This tool never executes learner commands. Real execution belongs to a
user-confirmed host terminal, user CI, or user-confirmed container.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
from typing import Any

from learn_topic.safety import validate_persisted_text, validate_persisted_value


DIRECTORY_RE = re.compile(r"^\d{2}-[^/\\\x00-\x1f\x7f]+$")
ATTEMPT_RE = re.compile(r"^attempt-(\d{2,})\.json$")
ORIGINS = {"host-tool", "user-ci", "user-supplied"}
STATUSES = {"passed", "failed", "blocked"}
COMMAND_KINDS = {"test", "lint", "format", "typecheck", "variant"}
FILE_ROLES = {"starter", "core_test", "config", "fixture", "support", "variant_test"}
SECRET_KEYS = ("TOKEN", "SECRET", "PASSWORD", "PASSWD", "API_KEY", "AUTHORIZATION", "COOKIE")
SECRET_VALUES = ("authorization:", "cookie:", "bearer ", "sk-", "ghp_", "github_pat_")


class ContractError(RuntimeError):
    pass


def emit(value: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True), file=stream)


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ContractError(f"{label} must be a normalized non-empty string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ContractError(f"{label} contains a control character")
    return value


def relative_path(value: Any, label: str, *, allow_dot: bool = False) -> str:
    value = text(value, label)
    if value == "." and allow_dot:
        return value
    path = PurePosixPath(value)
    if value.startswith("/") or "\\" in value or any(part in {"", ".", ".."} for part in path.parts):
        raise ContractError(f"{label} must be a safe package-relative path")
    if path.parts[0] == ".learn-topic":
        raise ContractError(f"{label} cannot target .learn-topic")
    return path.as_posix()


def load_object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise ContractError(f"{label} must not be a symbolic link")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot read {label}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return value


def stable_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(stable_bytes(value)).hexdigest()


def write_new(path: Path, value: dict[str, Any] | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = stable_bytes(value) if isinstance(value, dict) else value
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def replace(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(stable_bytes(value))
    temporary.replace(path)


def validate_rubric(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("rubric must be an object")
    mode = value.get("mode")
    criteria = value.get("criteria")
    if mode == "pass-fail":
        if not isinstance(criteria, list) or not criteria:
            raise ContractError("pass-fail rubric requires criteria")
        return {"mode": mode, "criteria": [text(item, "rubric criterion") for item in criteria]}
    if mode == "weighted":
        if not isinstance(criteria, list) or not criteria:
            raise ContractError("weighted rubric requires criteria")
        normalized = []
        for index, item in enumerate(criteria):
            if not isinstance(item, dict):
                raise ContractError(f"rubric.criteria[{index}] must be an object")
            weight = item.get("weight")
            if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight <= 0:
                raise ContractError(f"rubric.criteria[{index}].weight must be positive")
            normalized.append({"name": text(item.get("name"), f"rubric.criteria[{index}].name"), "weight": weight})
        return {"mode": mode, "criteria": normalized}
    raise ContractError("rubric.mode must be pass-fail or weighted")


def validate_env(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a string map")
    normalized = {}
    for key, item in value.items():
        key = text(key, f"{label} key")
        item = text(item, f"{label}.{key}")
        if any(marker in key.upper() for marker in SECRET_KEYS):
            raise ContractError(f"{label} contains a secret-like key")
        if any(marker.casefold() in item.casefold() for marker in SECRET_VALUES):
            raise ContractError(f"{label} contains a secret-like value")
        normalized[key] = item
    return normalized


def safe_persisted_text(value: Any, label: str) -> str:
    value = text(value, label)
    try:
        return validate_persisted_text(value, label)
    except Exception as error:
        raise ContractError(str(error)) from error


def validate_test_summary(value: Any) -> dict[str, int | None]:
    if not isinstance(value, dict) or set(value) - {"passed", "failed", "errors", "skipped"}:
        raise ContractError("tests must use only passed/failed/errors/skipped")
    result = {}
    for key in ("passed", "failed", "errors", "skipped"):
        item = value.get(key)
        if item is not None and (not isinstance(item, int) or isinstance(item, bool) or item < 0):
            raise ContractError(f"tests.{key} must be a non-negative integer or null")
        result[key] = item
    return result


def validate_rubric_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("mode") not in {"pass-fail", "weighted"}:
        raise ContractError("rubric_result mode is invalid")
    allowed = {"mode", "passed", "score", "max_score", "criteria"}
    if set(value) - allowed:
        raise ContractError("rubric_result contains unsupported fields")
    for key, item in value.items():
        if isinstance(item, str):
            safe_persisted_text(item, f"rubric_result.{key}")
        elif isinstance(item, list):
            for index, entry in enumerate(item):
                if not isinstance(entry, str):
                    raise ContractError("rubric_result.criteria must be a string array")
                safe_persisted_text(entry, f"rubric_result.criteria[{index}]")
        elif item is not None and not isinstance(item, (bool, int, float)):
            raise ContractError(f"rubric_result.{key} has an invalid type")
    return value


def normalize_command(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    command_id = text(value.get("id"), f"{label}.id")
    kind = text(value.get("kind"), f"{label}.kind")
    if kind not in COMMAND_KINDS:
        raise ContractError(f"{label}.kind is unsupported")
    argv = value.get("argv")
    if not isinstance(argv, list) or not argv:
        raise ContractError(f"{label}.argv must be a non-empty array")
    argv = [text(item, f"{label}.argv") for item in argv]
    if Path(argv[0]).name.casefold() in {"bash", "sh", "zsh", "fish", "cmd", "powershell", "pwsh"}:
        raise ContractError("shell command strings are forbidden")
    folded_argv = " ".join(argv).casefold()
    if any(marker.casefold() in folded_argv for marker in SECRET_VALUES) or any(
        any(marker in token.upper() for marker in SECRET_KEYS) for token in argv
    ):
        raise ContractError(f"{label}.argv contains a secret-like value")
    env = validate_env(value.get("env", {}), f"{label}.env")
    return {
        "id": command_id,
        "kind": kind,
        "argv": argv,
        "cwd": relative_path(value.get("cwd", "."), f"{label}.cwd", allow_dot=True),
        "env": env,
        "timeout_seconds": int(value.get("timeout_seconds", 300)),
        "required": bool(value.get("required", False)),
        "visible": True,
        "effects": [text(item, f"{label}.effects") for item in value.get("effects", [])],
    }


def validate_exercise(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("exercise must be an object")
    hints = value.get("hints", [])
    if not isinstance(hints, list):
        raise ContractError("exercise.hints must be an array")
    normalized_hints = []
    for index, hint in enumerate(hints):
        if not isinstance(hint, dict):
            raise ContractError(f"exercise.hints[{index}] must be an object")
        normalized_hints.append({
            "when": text(hint.get("when"), f"exercise.hints[{index}].when"),
            "content": text(hint.get("content"), f"exercise.hints[{index}].content"),
        })
    layout = text(value.get("layout"), "exercise.layout")
    if layout not in {"standalone", "project"}:
        raise ContractError("exercise.layout must be standalone or project")
    requirements = value.get("core_requirements")
    prompts = value.get("explanation_prompts")
    if not isinstance(requirements, list) or not requirements or not isinstance(prompts, list) or not prompts:
        raise ContractError("exercise requires core_requirements and explanation_prompts")
    return {
        "id": text(value.get("id"), "exercise.id"),
        "version": int(value.get("version", 1)),
        "topic": text(value.get("topic"), "exercise.topic"),
        "lesson_id": text(value.get("lesson_id"), "exercise.lesson_id"),
        "title": text(value.get("title"), "exercise.title"),
        "language": text(value.get("language"), "exercise.language"),
        "version_scope": text(value.get("version_scope"), "exercise.version_scope"),
        "goal": text(value.get("goal"), "exercise.goal"),
        "layout": layout,
        "core_requirements": [text(item, "core requirement") for item in requirements],
        "explanation_prompts": [text(item, "explanation prompt") for item in prompts],
        "rubric": validate_rubric(value.get("rubric")),
        "hints": normalized_hints,
        "answer_policy": {"first_attempt_before_solution": True, "model_written_result_proves_mastery": False},
    }


def validate_plan(path: Path) -> dict[str, Any]:
    raw = load_object(path, "exercise plan")
    if raw.get("schema_version") != 2:
        raise ContractError("exercise plan schema_version must be 2")
    vault_root = Path(text(raw.get("vault_root"), "vault_root")).resolve(strict=True)
    workspace_root = Path(text(raw.get("workspace_root"), "workspace_root")).resolve(strict=True)
    if not vault_root.is_dir() or not workspace_root.is_dir() or workspace_root == vault_root or vault_root in workspace_root.parents:
        raise ContractError("workspace_root must be an existing directory outside the Vault")
    directory = text(raw.get("exercise_directory"), "exercise_directory")
    if not DIRECTORY_RE.fullmatch(directory) or directory.startswith("99-"):
        raise ContractError("exercise_directory must use NN-name")
    files = raw.get("files")
    if not isinstance(files, list) or not files:
        raise ContractError("files must be non-empty")
    normalized_files = []
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise ContractError(f"files[{index}] must be an object")
        role = text(item.get("role"), f"files[{index}].role")
        if role not in FILE_ROLES:
            raise ContractError(f"files[{index}].role is unsupported")
        target = relative_path(item.get("path"), f"files[{index}].path")
        if "solution" in target.casefold() or "answer" in target.casefold():
            raise ContractError("scaffold must not contain answer files")
        source = Path(text(item.get("content_file"), f"files[{index}].content_file"))
        if not source.is_absolute():
            source = path.parent / source
        source = source.resolve(strict=True)
        source.relative_to(path.parent.resolve())
        normalized_files.append({"path": target, "role": role, "content_file": str(source), "user_editable": bool(item.get("user_editable"))})
    if not any(item["role"] == "starter" and item["user_editable"] for item in normalized_files):
        raise ContractError("plan requires a user-editable starter")
    if not any(item["role"] == "core_test" and not item["user_editable"] for item in normalized_files):
        raise ContractError("plan requires a public non-editable core test")
    exercise = validate_exercise(raw.get("exercise"))
    commands = [normalize_command(item, f"commands[{index}]") for index, item in enumerate(raw.get("commands", []))]
    if not any(command["kind"] == "test" and command["required"] for command in commands):
        raise ContractError("plan requires one public required test command")
    return {"schema_version": 2, "vault_root": str(vault_root), "workspace_root": str(workspace_root), "exercise_directory": directory, "exercise": exercise, "files": normalized_files, "commands": commands}


def scaffold(plan_path: Path, *, apply: bool) -> dict[str, Any]:
    plan = validate_plan(plan_path)
    package = Path(plan["workspace_root"]) / plan["exercise_directory"]
    if package.exists():
        raise ContractError("exercise package already exists")
    manifest = {
        "schema_version": 2,
        "exercise": plan["exercise"],
        "exercise_directory": plan["exercise_directory"],
        "commands": plan["commands"],
        "files": [{"path": item["path"], "role": item["role"], "user_editable": item["user_editable"], "sha256": hashlib.sha256(Path(item["content_file"]).read_bytes()).hexdigest()} for item in plan["files"]],
    }
    result = {"ok": True, "op": "scaffold", "mode": "apply" if apply else "dry-run", "exercise_directory": plan["exercise_directory"], "files": [item["path"] for item in plan["files"]], "commands": plan["commands"]}
    if not apply:
        return result
    package.mkdir()
    try:
        for item in plan["files"]:
            target = package / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            write_new(target, Path(item["content_file"]).read_bytes())
        (package / ".learn-topic" / "evidence").mkdir(parents=True)
        write_new(package / ".learn-topic" / "manifest.json", manifest)
    except Exception:
        shutil.rmtree(package)
        raise
    result["manifest_sha256"] = digest(manifest)
    return result


def manifest_package(path: Path) -> tuple[Path, dict[str, Any]]:
    path = path.resolve(strict=True)
    if path.name != "manifest.json" or path.parent.name != ".learn-topic":
        raise ContractError("manifest must be <exercise>/.learn-topic/manifest.json")
    manifest = load_object(path, "manifest")
    if manifest.get("schema_version") != 2:
        raise ContractError("manifest schema_version must be 2")
    if not isinstance(manifest.get("exercise"), dict) or not isinstance(manifest["exercise"].get("id"), str):
        raise ContractError("manifest exercise identity is invalid")
    commands = manifest.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ContractError("manifest commands are required")
    normalized_commands = [normalize_command(item, f"manifest.commands[{index}]") for index, item in enumerate(commands)]
    identifiers = [item["id"] for item in normalized_commands]
    if len(identifiers) != len(set(identifiers)):
        raise ContractError("manifest command ids must be unique")
    manifest["commands"] = normalized_commands
    files = manifest.get("files", [])
    if not isinstance(files, list):
        raise ContractError("manifest files must be an array")
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise ContractError(f"manifest.files[{index}] must be an object")
        relative = relative_path(item.get("path"), f"manifest.files[{index}].path")
        target = path.parent.parent / relative
        if not target.is_file() or target.is_symlink():
            raise ContractError(f"manifest file is missing or unsafe: {relative}")
        expected = text(item.get("sha256"), f"manifest.files[{index}].sha256")
        if item.get("user_editable") is not True and hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ContractError(f"public non-user file changed: {relative}")
    return path.parent.parent, manifest


def authorize(manifest_path: Path, command_id: str, confirmed_at: str, *, apply: bool) -> dict[str, Any]:
    package, manifest = manifest_package(manifest_path)
    command = next((item for item in manifest.get("commands", []) if item.get("id") == command_id), None)
    if command is None:
        raise ContractError(f"manifest has no command {command_id}")
    try:
        datetime.fromisoformat(text(confirmed_at, "confirmed_at").replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError("confirmed_at must be an ISO datetime") from error
    destination = package / ".learn-topic" / "authorization.json"
    authorization = {"schema_version": 2, "manifest_sha256": digest(manifest), "confirmed_at": confirmed_at, "commands": {command_id: command}}
    if destination.exists():
        current = load_object(destination, "authorization")
        if current.get("manifest_sha256") == authorization["manifest_sha256"]:
            authorization["commands"] = {**current.get("commands", {}), command_id: command}
    if apply:
        replace(destination, authorization)
    return {"ok": True, "op": "authorize", "mode": "apply" if apply else "dry-run", "command": command, "execution_owner": "host-tool-or-user-ci-or-user-container"}


def next_attempt_id(directory: Path) -> str:
    numbers = [int(match.group(1)) for path in directory.glob("attempt-*.json") if (match := ATTEMPT_RE.fullmatch(path.name))]
    return f"attempt-{max(numbers, default=0) + 1:02d}"


def validate_attestation(
    attestation: Any,
    *,
    manifest: dict[str, Any],
    command: dict[str, Any],
    origin: str,
    status: str,
    trust_key: bytes | None,
) -> dict[str, Any]:
    if not isinstance(attestation, dict):
        raise ContractError("trusted evidence requires a host or CI attestation")
    required = (
        "origin", "adapter_id", "external_run_id", "manifest_sha256", "command_id",
        "argv", "exit_code", "status", "observed_at", "signature",
    )
    if any(key not in attestation for key in required):
        raise ContractError("trusted attestation is missing required fields")
    if attestation["origin"] != origin or origin not in {"host-tool", "user-ci"}:
        raise ContractError("attestation origin does not match a trusted adapter")
    if attestation["manifest_sha256"] != digest(manifest) or attestation["command_id"] != command["id"] or attestation["argv"] != command["argv"]:
        raise ContractError("attestation does not match the manifest command")
    if attestation["status"] != status or not isinstance(attestation["exit_code"], int) or isinstance(attestation["exit_code"], bool):
        raise ContractError("attestation result is inconsistent")
    if (status == "passed") != (attestation["exit_code"] == 0):
        raise ContractError("attestation status and exit_code disagree")
    safe_persisted_text(attestation["adapter_id"], "attestation.adapter_id")
    safe_persisted_text(attestation["external_run_id"], "attestation.external_run_id")
    try:
        datetime.fromisoformat(text(attestation["observed_at"], "attestation.observed_at").replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError("attestation.observed_at must be an ISO datetime") from error
    if not isinstance(trust_key, bytes) or len(trust_key) < 32:
        raise ContractError("trusted evidence requires an external trust key of at least 32 bytes")
    signed = {key: attestation[key] for key in required if key != "signature"}
    expected_signature = hmac.new(trust_key, stable_bytes(signed), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(attestation["signature"]), expected_signature):
        raise ContractError("attestation signature is invalid")
    return {key: attestation[key] for key in required}


def validate_attempt_artifact(manifest_path: Path, evidence_path: Path, trust_key: bytes) -> dict[str, Any]:
    _, manifest = manifest_package(manifest_path)
    evidence = load_object(evidence_path, "attempt evidence")
    command_id = evidence.get("command_id")
    command = next((item for item in manifest["commands"] if item["id"] == command_id), None)
    if command is None:
        raise ContractError("attempt command does not exist in manifest")
    if evidence.get("schema_version") != 2 or evidence.get("manifest_sha256") != digest(manifest):
        raise ContractError("attempt evidence does not match manifest")
    if evidence.get("exercise_id") != manifest["exercise"]["id"] or evidence.get("verified") is not True:
        raise ContractError("attempt evidence identity or verification state is invalid")
    if evidence.get("status") != "passed":
        raise ContractError("mastery requires a passed code attempt")
    try:
        validate_persisted_value(evidence, "attempt evidence")
    except Exception as error:
        raise ContractError(str(error)) from error
    attestation = validate_attestation(
        evidence.get("attestation"), manifest=manifest, command=command,
        origin=evidence.get("origin"), status=evidence.get("status"), trust_key=trust_key,
    )
    if evidence.get("external_run_id") not in {None, attestation["external_run_id"]}:
        raise ContractError("attempt external_run_id conflicts with attestation")
    return {"manifest": manifest, "evidence": evidence, "sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest()}


def record_attempt(
    manifest_path: Path,
    payload: dict[str, Any],
    *,
    apply: bool,
    attempt_id: str | None = None,
    attestation: dict[str, Any] | None = None,
    trust_key: bytes | None = None,
) -> dict[str, Any]:
    package, manifest = manifest_package(manifest_path)
    command_id = text(payload.get("command_id"), "command_id")
    command = next((item for item in manifest.get("commands", []) if item.get("id") == command_id), None)
    if command is None:
        raise ContractError(f"manifest has no command {command_id}")
    authorization_path = package / ".learn-topic" / "authorization.json"
    if not authorization_path.is_file():
        raise ContractError("command has not been authorized")
    authorization = load_object(authorization_path, "authorization")
    if authorization.get("manifest_sha256") != digest(manifest) or command_id not in authorization.get("commands", {}):
        raise ContractError("authorization does not match the current manifest and command")
    origin = payload.get("origin")
    status = payload.get("status")
    if origin not in ORIGINS or status not in STATUSES:
        raise ContractError("attempt origin or status is invalid")
    allowed_payload = {"command_id", "origin", "status", "summary", "exit_code", "duration_ms", "tests", "rubric_result", "external_run_id"}
    if set(payload) - allowed_payload:
        raise ContractError("evidence payload contains unsupported fields")
    evidence_dir = package / ".learn-topic" / "evidence"
    attempt_id = attempt_id or next_attempt_id(evidence_dir)
    if not re.fullmatch(r"attempt-\d{2,}", attempt_id):
        raise ContractError("attempt_id must use attempt-NN")
    destination = evidence_dir / f"{attempt_id}.json"
    if destination.exists():
        raise ContractError("attempt evidence is append-only")
    verified = False
    trusted_attestation = None
    if origin in {"host-tool", "user-ci"}:
        trusted_attestation = validate_attestation(
            attestation,
            manifest=manifest,
            command=command,
            origin=origin,
            status=status,
            trust_key=trust_key,
        )
        verified = True
    elif attestation is not None:
        raise ContractError("user-supplied evidence cannot carry a trusted attestation")
    evidence = {
        "schema_version": 2, "attempt_id": attempt_id,
        "exercise_id": manifest.get("exercise", {}).get("id"),
        "manifest_sha256": digest(manifest), "command_id": command_id,
        "origin": origin, "status": status, "verified": verified,
        "summary": safe_persisted_text(payload.get("summary"), "summary"),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    if trusted_attestation:
        evidence["attestation"] = trusted_attestation
    if "exit_code" in payload:
        if not isinstance(payload["exit_code"], int) or isinstance(payload["exit_code"], bool):
            raise ContractError("exit_code must be an integer")
        evidence["exit_code"] = payload["exit_code"]
    if "duration_ms" in payload:
        if not isinstance(payload["duration_ms"], int) or isinstance(payload["duration_ms"], bool) or payload["duration_ms"] < 0:
            raise ContractError("duration_ms must be a non-negative integer")
        evidence["duration_ms"] = payload["duration_ms"]
    if "tests" in payload:
        evidence["tests"] = validate_test_summary(payload["tests"])
    if "rubric_result" in payload:
        evidence["rubric_result"] = validate_rubric_result(payload["rubric_result"])
    if "external_run_id" in payload:
        evidence["external_run_id"] = safe_persisted_text(payload["external_run_id"], "external_run_id")
    if apply:
        write_new(destination, evidence)
    return {"ok": True, "op": "record-attempt", "mode": "apply" if apply else "dry-run", "attempt_id": attempt_id, "evidence": evidence, "graduates_alone": verified and status == "passed"}


def add_variant(manifest_path: Path, variant: dict[str, Any], *, apply: bool) -> dict[str, Any]:
    package, manifest = manifest_package(manifest_path)
    if not any((package / ".learn-topic" / "evidence").glob("attempt-*.json")):
        raise ContractError("a public variant requires at least one existing attempt")
    command = normalize_command(variant.get("command"), "variant.command")
    if command["kind"] != "variant" or command["required"]:
        raise ContractError("variant command must be optional and kind=variant")
    if any(item.get("id") == command["id"] for item in manifest.get("commands", [])):
        raise ContractError("variant command id already exists")
    updated = {**manifest, "commands": [*manifest.get("commands", []), command]}
    if apply:
        replace(manifest_path.resolve(), updated)
        (package / ".learn-topic" / "authorization.json").unlink(missing_ok=True)
    return {"ok": True, "op": "add-variant", "mode": "apply" if apply else "dry-run", "command": command, "authorization_invalidated": True}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    scaffold_parser = actions.add_parser("scaffold")
    scaffold_parser.add_argument("--plan", required=True)
    scaffold_parser.add_argument("--apply", action="store_true")
    authorize_parser = actions.add_parser("authorize")
    authorize_parser.add_argument("--manifest", required=True)
    authorize_parser.add_argument("--command", required=True)
    authorize_parser.add_argument("--confirmed-at", required=True)
    authorize_parser.add_argument("--apply", action="store_true")
    record_parser = actions.add_parser("record-attempt")
    record_parser.add_argument("--manifest", required=True)
    record_parser.add_argument("--evidence", required=True)
    record_parser.add_argument("--attempt-id")
    record_parser.add_argument("--attestation", help="host/CI attestation JSON for trusted origins")
    record_parser.add_argument("--trust-key-file", help="external HMAC key file; never copied into the exercise package")
    record_parser.add_argument("--apply", action="store_true")
    variant_parser = actions.add_parser("add-variant")
    variant_parser.add_argument("--manifest", required=True)
    variant_parser.add_argument("--variant", required=True)
    variant_parser.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.action == "scaffold":
            result = scaffold(Path(args.plan), apply=args.apply)
        elif args.action == "authorize":
            result = authorize(Path(args.manifest), args.command, args.confirmed_at, apply=args.apply)
        elif args.action == "record-attempt":
            attestation = load_object(Path(args.attestation), "trusted attestation") if args.attestation else None
            trust_key = None
            if args.trust_key_file:
                key_path = Path(args.trust_key_file)
                if key_path.is_symlink() or not key_path.is_file():
                    raise ContractError("trust key must be a regular non-symbolic file")
                package_root = Path(args.manifest).resolve(strict=True).parent.parent
                if key_path.resolve(strict=True) == package_root or package_root in key_path.resolve(strict=True).parents:
                    raise ContractError("trust key must stay outside the exercise package")
                if os.stat(key_path.resolve(strict=True)).st_mode & 0o077:
                    raise ContractError("trust key permissions must not grant group or other access")
                trust_key = key_path.read_bytes()
            result = record_attempt(
                Path(args.manifest),
                load_object(Path(args.evidence), "evidence payload"),
                apply=args.apply,
                attempt_id=args.attempt_id,
                attestation=attestation,
                trust_key=trust_key,
            )
        else:
            result = add_variant(Path(args.manifest), load_object(Path(args.variant), "variant payload"), apply=args.apply)
    except (ContractError, OSError, ValueError) as error:
        emit({"ok": False, "op": args.action, "error": str(error)}, stream=sys.stderr)
        return 1
    emit(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

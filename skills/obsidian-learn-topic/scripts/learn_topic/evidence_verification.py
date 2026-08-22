from __future__ import annotations

from datetime import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
from typing import Any

from .curriculum import ContractError, EVIDENCE_PROFILES
from .safety import validate_persisted_text


RECEIPT_FIELDS = (
    "schema_version", "verifier_id", "evidence_id", "unit_id", "evidence_profile",
    "capability_level", "evidence_origin", "verified_by", "summary_sha256",
    "verification_ref", "observed_at", "artifact_type", "artifact_sha256",
)


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def load_regular(path: Path, label: str) -> bytes:
    resolved = path.resolve(strict=True)
    if path.is_symlink() or not resolved.is_file():
        raise ContractError(f"{label} must be a regular non-symbolic file")
    return resolved.read_bytes()


def load_trust_key(path: Path, *, forbidden: tuple[Path, ...], package_root: Path | None) -> bytes:
    resolved = path.resolve(strict=True)
    if path.is_symlink() or not resolved.is_file():
        raise ContractError("trust key must be a regular non-symbolic file")
    if any(resolved == item.resolve(strict=True) for item in forbidden):
        raise ContractError("trust key must be physically separate from evidence files")
    if package_root is not None:
        package_root = package_root.resolve(strict=True)
        if resolved == package_root or package_root in resolved.parents:
            raise ContractError("trust key must stay outside the exercise package")
    if stat.S_IMODE(os.stat(resolved).st_mode) & 0o077:
        raise ContractError("trust key permissions must not grant group or other access")
    key = resolved.read_bytes()
    if len(key) < 32:
        raise ContractError("verification receipt trust key must contain at least 32 bytes")
    return key


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(load_regular(path, label))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(f"{label} must contain valid JSON") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} must contain an object")
    return value


def validate_receipt(
    receipt_path: Path,
    artifact_path: Path,
    trust_key_path: Path,
    *,
    unit: dict[str, Any],
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    receipt = load_json(receipt_path, "verification receipt")
    if set(receipt) != {*RECEIPT_FIELDS, "signature"} or receipt.get("schema_version") != 1:
        raise ContractError("verification receipt has an invalid field contract")
    package_root = manifest_path.resolve(strict=True).parent.parent if manifest_path is not None else None
    forbidden = (receipt_path, artifact_path, *(() if manifest_path is None else (manifest_path,)))
    key = load_trust_key(trust_key_path, forbidden=forbidden, package_root=package_root)
    signed = {field: receipt[field] for field in RECEIPT_FIELDS}
    expected = hmac.new(key, canonical_bytes(signed), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(receipt["signature"]), expected):
        raise ContractError("verification receipt signature is invalid")
    if receipt["unit_id"] != unit["unit_id"] or receipt["evidence_profile"] != unit["evidence_profile"]:
        raise ContractError("verification receipt does not match unit or evidence profile")
    if receipt["evidence_profile"] not in EVIDENCE_PROFILES or receipt["capability_level"] not in {"independent", "transfer", "retention"}:
        raise ContractError("verification receipt profile or capability level is invalid")
    if receipt["evidence_origin"] not in {"host-tool", "user-ci", "user-supplied"} or receipt["verified_by"] not in {"host-tool", "user-ci"}:
        raise ContractError("verification receipt origin is invalid")
    for field in ("verifier_id", "evidence_id", "summary_sha256", "verification_ref", "observed_at", "artifact_type", "artifact_sha256"):
        if not isinstance(receipt[field], str) or not receipt[field].strip():
            raise ContractError(f"verification receipt {field} is invalid")
        validate_persisted_text(receipt[field], f"verification receipt {field}")
    try:
        datetime.fromisoformat(receipt["observed_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError("verification receipt observed_at is invalid") from error
    artifact_bytes = load_regular(artifact_path, "verification artifact")
    if hashlib.sha256(artifact_bytes).hexdigest() != receipt["artifact_sha256"]:
        raise ContractError("verification artifact hash does not match receipt")
    if unit["evidence_profile"] == "code-practice":
        if receipt["artifact_type"] != "code-attempt" or manifest_path is None:
            raise ContractError("code-practice requires a signed code-attempt and manifest")
        from exercise_cli import validate_attempt_artifact
        try:
            attempt = validate_attempt_artifact(manifest_path, artifact_path, key)
        except Exception as error:
            raise ContractError(str(error)) from error
        manifest = attempt["manifest"]
        evidence = attempt["evidence"]
        attestation = evidence["attestation"]
        if manifest.get("exercise", {}).get("lesson_id") != unit["unit_id"]:
            raise ContractError("code attempt lesson_id does not match unit_id")
        expected_ref = f"code-attempt:{evidence['attempt_id']}:{attestation['external_run_id']}"
        expected_facts = {
            "evidence_id": evidence["attempt_id"],
            "verifier_id": attestation["adapter_id"],
            "evidence_origin": evidence["origin"],
            "verified_by": evidence["origin"],
            "verification_ref": expected_ref,
            "observed_at": attestation["observed_at"],
            "summary_sha256": hashlib.sha256(evidence["summary"].encode("utf-8")).hexdigest(),
        }
        for field, value in expected_facts.items():
            if receipt[field] != value:
                raise ContractError(f"verification receipt {field} does not match the passed attempt")
    return receipt


def match_record_evidence(item: dict[str, Any], receipt: dict[str, Any]) -> None:
    expected = {
        "evidence_id": receipt["evidence_id"],
        "evidence_profile": receipt["evidence_profile"],
        "capability_level": receipt["capability_level"],
        "origin": receipt["evidence_origin"],
        "verified_by": receipt["verified_by"],
        "verification_ref": receipt["verification_ref"],
        "observed_at": receipt["observed_at"],
        "verified": True,
    }
    for field, value in expected.items():
        if item.get(field) != value:
            raise ContractError(f"learning record evidence {field} does not match signed receipt")
    summary = item.get("summary")
    if not isinstance(summary, str) or hashlib.sha256(summary.encode("utf-8")).hexdigest() != receipt["summary_sha256"]:
        raise ContractError("learning record evidence summary does not match signed receipt")

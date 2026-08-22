from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from learn_topic.curriculum import ContractError  # noqa: E402
from learn_topic.evidence_verification import canonical_bytes, validate_receipt  # noqa: E402
from learn_topic.note_contract import validate_learning_record  # noqa: E402

SPEC = importlib.util.spec_from_file_location("exercise_cli", SCRIPTS / "exercise_cli.py")
assert SPEC and SPEC.loader
exercise_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exercise_cli)


def record_note(item: dict) -> str:
    evidence = "\n".join(f"    {key}: {json.dumps(value, ensure_ascii=False) if isinstance(value, (bool, list, dict)) else value}" for key, value in item.items())
    return f'''---
title: 核心练习学习记录
tags:
  - 学习路线/主题
date: 2026-08-21
updated: 2026-08-21
status: 已核验
category: 技术
record_type: learning-evidence
schema_version: 3
roadmap_topic: 主题
roadmap_root: Roadmap
learning_goal: 独立完成练习
unit_id: CODE-01
content_note: "[[Roadmap/02-核心/§01-练习]]"
stage_title: 04-学习记录
stage_order: 4
lesson_order: 1
progress_status: 已完成
mastery_status: 已独立应用
evidence_profile: code-practice
mastery_evidence:
  - {evidence.lstrip()}
version_scope: v1
---
# 核心练习学习记录
'''


class EvidenceVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root / "exercise"
        self.metadata = self.package / ".learn-topic"
        (self.metadata / "evidence").mkdir(parents=True)
        self.key = b"0123456789abcdef0123456789abcdef"
        self.key_path = self.root / "trust.key"; self.key_path.write_bytes(self.key); self.key_path.chmod(0o600)
        self.command = {"id": "core-test", "kind": "test", "argv": ["python3", "-m", "unittest"], "cwd": ".", "env": {}, "timeout_seconds": 30, "required": True, "visible": True, "effects": []}
        self.manifest = {"schema_version": 2, "exercise": {"id": "EX-1", "lesson_id": "CODE-01"}, "commands": [self.command], "files": []}
        self.manifest_path = self.metadata / "manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        attestation = {
            "origin": "user-ci", "adapter_id": "ci-fixture", "external_run_id": "run-1",
            "manifest_sha256": exercise_cli.digest(self.manifest), "command_id": "core-test",
            "argv": self.command["argv"], "exit_code": 0, "status": "passed",
            "observed_at": "2026-08-21T10:00:00+08:00",
        }
        attestation["signature"] = hmac.new(self.key, exercise_cli.stable_bytes(attestation), hashlib.sha256).hexdigest()
        self.attempt = {
            "schema_version": 2, "attempt_id": "attempt-01", "exercise_id": "EX-1",
            "manifest_sha256": exercise_cli.digest(self.manifest), "command_id": "core-test",
            "origin": "user-ci", "status": "passed", "verified": True,
            "summary": "public tests passed", "recorded_at": "2026-08-21T10:01:00+08:00",
            "attestation": attestation,
        }
        self.attempt_path = self.metadata / "evidence" / "attempt-01.json"
        self.attempt_path.write_text(json.dumps(self.attempt, sort_keys=True), encoding="utf-8")
        self.summary = "public tests passed"
        self.receipt = {
            "schema_version": 1, "verifier_id": "ci-fixture", "evidence_id": "attempt-01",
            "unit_id": "CODE-01", "evidence_profile": "code-practice", "capability_level": "independent",
            "evidence_origin": "user-ci", "verified_by": "user-ci",
            "summary_sha256": hashlib.sha256(self.summary.encode()).hexdigest(),
            "verification_ref": "code-attempt:attempt-01:run-1", "observed_at": "2026-08-21T10:00:00+08:00",
            "artifact_type": "code-attempt", "artifact_sha256": hashlib.sha256(self.attempt_path.read_bytes()).hexdigest(),
        }
        self.receipt["signature"] = hmac.new(self.key, canonical_bytes(self.receipt), hashlib.sha256).hexdigest()
        self.receipt_path = self.root / "receipt.json"; self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        self.unit = {"unit_id": "CODE-01", "evidence_profile": "code-practice"}

    def test_signed_code_attempt_supports_matching_mastery_record(self) -> None:
        receipt = validate_receipt(self.receipt_path, self.attempt_path, self.key_path, unit=self.unit, manifest_path=self.manifest_path)
        item = {
            "evidence_id": "attempt-01", "evidence_profile": "code-practice",
            "capability_level": "independent", "origin": "user-ci", "verified_by": "user-ci",
            "verified": True, "summary": self.summary, "verification_ref": "code-attempt:attempt-01:run-1",
            "observed_at": "2026-08-21T10:00:00+08:00",
        }
        values = validate_learning_record(record_note(item), trusted_receipts={"attempt-01": receipt})
        self.assertEqual(values["mastery_status"], "已独立应用")

    def test_forged_host_claim_and_any_binding_drift_fail(self) -> None:
        item = {
            "evidence_id": "attempt-99", "evidence_profile": "code-practice",
            "capability_level": "independent", "origin": "host-tool", "verified_by": "host-tool",
            "verified": True, "summary": "made up", "verification_ref": "made-up:attempt-99",
            "observed_at": "2026-08-21T10:00:00+08:00",
        }
        with self.assertRaises(ContractError):
            validate_learning_record(record_note(item))
        for field, value in (("unit_id", "OTHER"), ("evidence_profile", "concept-explanation"), ("artifact_sha256", "0" * 64)):
            changed = {**self.receipt, field: value}
            changed["signature"] = hmac.new(self.key, canonical_bytes({key: val for key, val in changed.items() if key != "signature"}), hashlib.sha256).hexdigest()
            self.receipt_path.write_text(json.dumps(changed), encoding="utf-8")
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_receipt(self.receipt_path, self.attempt_path, self.key_path, unit=self.unit, manifest_path=self.manifest_path)

    def test_public_key_failed_attempt_and_attempt_fact_drift_are_rejected(self) -> None:
        with self.assertRaises(ContractError):
            validate_receipt(self.receipt_path, self.attempt_path, self.manifest_path, unit=self.unit, manifest_path=self.manifest_path)
        for field, value in (
            ("evidence_id", "attempt-99"),
            ("verifier_id", "other-adapter"),
            ("verification_ref", "code-attempt:attempt-01:other-run"),
            ("observed_at", "2026-08-21T11:00:00+08:00"),
            ("evidence_origin", "host-tool"),
        ):
            changed = {**self.receipt, field: value}
            changed["signature"] = hmac.new(self.key, canonical_bytes({key: val for key, val in changed.items() if key != "signature"}), hashlib.sha256).hexdigest()
            self.receipt_path.write_text(json.dumps(changed), encoding="utf-8")
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_receipt(self.receipt_path, self.attempt_path, self.key_path, unit=self.unit, manifest_path=self.manifest_path)
        self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        failed = json.loads(json.dumps(self.attempt))
        failed.update({"status": "failed", "summary": "public tests failed"})
        failed["attestation"].update({"status": "failed", "exit_code": 1})
        signed_attestation = {key: value for key, value in failed["attestation"].items() if key != "signature"}
        failed["attestation"]["signature"] = hmac.new(self.key, exercise_cli.stable_bytes(signed_attestation), hashlib.sha256).hexdigest()
        self.attempt_path.write_text(json.dumps(failed, sort_keys=True), encoding="utf-8")
        failed_receipt = {**self.receipt, "summary_sha256": hashlib.sha256(b"public tests failed").hexdigest(), "artifact_sha256": hashlib.sha256(self.attempt_path.read_bytes()).hexdigest()}
        failed_receipt["signature"] = hmac.new(self.key, canonical_bytes({key: value for key, value in failed_receipt.items() if key != "signature"}), hashlib.sha256).hexdigest()
        self.receipt_path.write_text(json.dumps(failed_receipt), encoding="utf-8")
        with self.assertRaises(ContractError):
            validate_receipt(self.receipt_path, self.attempt_path, self.key_path, unit=self.unit, manifest_path=self.manifest_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)

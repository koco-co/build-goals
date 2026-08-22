from __future__ import annotations

import importlib.util
import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "exercise_cli.py"
SPEC = importlib.util.spec_from_file_location("exercise_cli", SCRIPT)
assert SPEC and SPEC.loader
exercise_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exercise_cli)


class ExerciseCliTests(unittest.TestCase):
    @staticmethod
    def sign_attestation(manifest: dict, command: dict, key: bytes, *, origin: str = "user-ci", status: str = "passed") -> dict:
        attestation = {
            "origin": origin,
            "adapter_id": "ci-fixture",
            "external_run_id": "run-123",
            "manifest_sha256": exercise_cli.digest(manifest),
            "command_id": command["id"],
            "argv": command["argv"],
            "exit_code": 0 if status == "passed" else 1,
            "status": status,
            "observed_at": "2026-08-21T10:05:00+08:00",
        }
        attestation["signature"] = hmac.new(key, exercise_cli.stable_bytes(attestation), hashlib.sha256).hexdigest()
        return attestation

    def test_parser_has_no_process_runner(self) -> None:
        choices = exercise_cli.build_parser()._subparsers._group_actions[0].choices
        self.assertEqual(set(choices), {"scaffold", "authorize", "record-attempt", "add-variant"})

    def test_rubric_accepts_pass_fail_or_positive_weights(self) -> None:
        exercise_cli.validate_rubric({"mode": "pass-fail", "criteria": ["all public tests pass"]})
        exercise_cli.validate_rubric({"mode": "weighted", "criteria": [{"name": "correctness", "weight": 3}, {"name": "clarity", "weight": 1}]})
        with self.assertRaises(exercise_cli.ContractError):
            exercise_cli.validate_rubric({"mode": "weighted", "criteria": [{"name": "bad", "weight": 0}]})

    def test_record_attempt_is_append_only_and_user_supplied_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            metadata = package / ".learn-topic"
            (metadata / "evidence").mkdir(parents=True)
            command = {"id": "test", "kind": "test", "argv": ["python", "-m", "unittest"], "cwd": ".", "env": {}, "timeout_seconds": 30, "required": True, "visible": True, "effects": []}
            manifest = {"schema_version": 2, "exercise": {"id": "EX-1"}, "commands": [command], "files": []}
            (metadata / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (metadata / "authorization.json").write_text(json.dumps({"schema_version": 2, "manifest_sha256": exercise_cli.digest(manifest), "commands": {"test": command}}), encoding="utf-8")
            payload = {"command_id": "test", "origin": "user-supplied", "status": "passed", "summary": "2 tests passed"}
            result = exercise_cli.record_attempt(metadata / "manifest.json", payload, apply=True)
            self.assertEqual(result["evidence"]["verified"], False)
            with self.assertRaises(exercise_cli.ContractError):
                exercise_cli.record_attempt(metadata / "manifest.json", payload, apply=True, attempt_id=result["attempt_id"])

    def test_trusted_origin_cannot_be_self_asserted_or_tampered(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            metadata = package / ".learn-topic"
            (metadata / "evidence").mkdir(parents=True)
            command = {"id": "test", "kind": "test", "argv": ["python3", "-m", "unittest"], "cwd": ".", "env": {}, "timeout_seconds": 30, "required": True, "visible": True, "effects": []}
            manifest = {"schema_version": 2, "exercise": {"id": "EX-1"}, "commands": [command], "files": []}
            (metadata / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (metadata / "authorization.json").write_text(json.dumps({"schema_version": 2, "manifest_sha256": exercise_cli.digest(manifest), "commands": {"test": command}}), encoding="utf-8")
            payload = {"command_id": "test", "origin": "user-ci", "status": "passed", "summary": "tests passed"}
            with self.assertRaises(exercise_cli.ContractError):
                exercise_cli.record_attempt(metadata / "manifest.json", payload, apply=False)
            key = b"0123456789abcdef0123456789abcdef"
            attestation = self.sign_attestation(manifest, command, key)
            attestation["argv"] = ["python3", "-c", "pass"]
            with self.assertRaises(exercise_cli.ContractError):
                exercise_cli.record_attempt(metadata / "manifest.json", payload, apply=False, attestation=attestation, trust_key=key)

    def test_secret_like_command_data_is_rejected(self) -> None:
        base = {"id": "test", "kind": "test", "argv": ["python3", "-m", "unittest"], "cwd": ".", "env": {}, "required": True}
        for command in (
            {**base, "env": {"API_TOKEN": "placeholder"}},
            {**base, "env": {"SAFE": "Bearer secret-value"}},
            {**base, "argv": ["python3", "--password", "value"]},
        ):
            with self.subTest(command=command), self.assertRaises(exercise_cli.ContractError):
                exercise_cli.normalize_command(command, "command")

    def test_secret_like_attempt_fields_never_persist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            metadata = package / ".learn-topic"
            (metadata / "evidence").mkdir(parents=True)
            command = {"id": "test", "kind": "test", "argv": ["python3", "-m", "unittest"], "cwd": ".", "env": {}, "timeout_seconds": 30, "required": True, "visible": True, "effects": []}
            manifest = {"schema_version": 2, "exercise": {"id": "EX-1"}, "commands": [command], "files": []}
            (metadata / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (metadata / "authorization.json").write_text(json.dumps({"schema_version": 2, "manifest_sha256": exercise_cli.digest(manifest), "commands": {"test": command}}), encoding="utf-8")
            base = {"command_id": "test", "origin": "user-supplied", "status": "failed", "summary": "safe failure summary"}
            payloads = [
                {**base, "summary": "Bearer secret-token"},
                {**base, "external_run_id": "github_pat_secret"},
                {**base, "rubric_result": {"mode": "pass-fail", "passed": False, "criteria": ["Cookie: secret"]}},
                {**base, "tests": {"passed": 0, "failed": 1, "errors": 0, "skipped": 0, "Authorization": "secret"}},
                {**base, "summary": "path=/opt/private/key.txt"},
                {**base, "external_run_id": "file:///srv/private/run.json"},
                {**base, "rubric_result": {"mode": "pass-fail", "passed": False, "criteria": ["artifact=/private/tmp/run.log"]}},
            ]
            for index, payload in enumerate(payloads):
                with self.subTest(index=index), self.assertRaises(exercise_cli.ContractError):
                    exercise_cli.record_attempt(metadata / "manifest.json", payload, apply=True)
            self.assertEqual(list((metadata / "evidence").iterdir()), [])

    def test_scaffold_authorize_and_record_end_to_end_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            vault = root / "vault"; workspace = root / "workspace"; plans = root / "plans"
            vault.mkdir(); workspace.mkdir(); plans.mkdir()
            (plans / "starter.py").write_text("def add(a, b):\n    raise NotImplementedError\n", encoding="utf-8")
            (plans / "test_exercise.py").write_text("import unittest\n", encoding="utf-8")
            plan = {
                "schema_version": 2,
                "vault_root": str(vault), "workspace_root": str(workspace),
                "exercise_directory": "01-add-two-values",
                "exercise": {
                    "id": "PY-ADD-01", "version": 1, "topic": "Python functions", "lesson_id": "FUN-01",
                    "title": "Add two values", "language": "Python", "version_scope": "supported Python",
                    "goal": "Implement one addition function", "layout": "standalone",
                    "core_requirements": ["Return the sum"], "explanation_prompts": ["Explain type boundaries"],
                    "rubric": {"mode": "weighted", "criteria": [{"name": "correctness", "weight": 3}, {"name": "explanation", "weight": 1}]},
                    "hints": [{"when": "after first failure", "content": "Inspect the return value"}],
                },
                "files": [
                    {"path": "01-add-two-values.py", "role": "starter", "content_file": "starter.py", "user_editable": True},
                    {"path": "test_exercise.py", "role": "core_test", "content_file": "test_exercise.py", "user_editable": False},
                ],
                "commands": [{"id": "core-test", "kind": "test", "argv": ["python3", "-m", "unittest", "-v", "test_exercise.py"], "cwd": ".", "env": {}, "timeout_seconds": 30, "required": True, "visible": True, "effects": []}],
            }
            plan_path = plans / "plan.json"; plan_path.write_text(json.dumps(plan), encoding="utf-8")
            preview = exercise_cli.scaffold(plan_path, apply=False)
            self.assertEqual(preview["mode"], "dry-run")
            exercise_cli.scaffold(plan_path, apply=True)
            manifest = workspace / "01-add-two-values" / ".learn-topic" / "manifest.json"
            exercise_cli.authorize(manifest, "core-test", "2026-08-21T10:00:00+08:00", apply=True)
            normalized_manifest = exercise_cli.load_object(manifest, "manifest")
            command = normalized_manifest["commands"][0]
            key = b"0123456789abcdef0123456789abcdef"
            attestation = self.sign_attestation(normalized_manifest, command, key)
            result = exercise_cli.record_attempt(
                manifest,
                {"command_id": "core-test", "origin": "user-ci", "status": "passed", "summary": "public tests passed"},
                apply=True,
                attestation=attestation,
                trust_key=key,
            )
            self.assertTrue(result["graduates_alone"])
            self.assertFalse((workspace / "01-add-two-values" / ".learn-topic" / "run.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

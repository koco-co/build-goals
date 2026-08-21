#!/usr/bin/env python3
"""Focused contract and real-process tests for exercise_cli.py."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("exercise_cli.py")
SPEC = importlib.util.spec_from_file_location("exercise_cli", SCRIPT)
assert SPEC and SPEC.loader
exercise_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exercise_cli)


class ExerciseDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.sandbox = Path(self.temporary.name)
        self.vault = self.sandbox / "vault"
        self.workspace = self.sandbox / "workspace"
        self.plan_dir = self.sandbox / "plan"
        self.vault.mkdir()
        self.workspace.mkdir()
        self.plan_dir.mkdir()
        (self.plan_dir / "starter.py").write_text(
            "def add(a, b):\n    return a + b\n", encoding="utf-8"
        )
        (self.plan_dir / "test_exercise.py").write_text(
            "import unittest\n"
            "from importlib.machinery import SourceFileLoader\n"
            "module = SourceFileLoader('exercise', '01-add.py').load_module()\n"
            "class TestAdd(unittest.TestCase):\n"
            "    def test_add(self): self.assertEqual(module.add(2, 3), 5)\n"
            "if __name__ == '__main__': unittest.main()\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def exercise(self, **updates: object) -> dict[str, object]:
        value: dict[str, object] = {
            "id": "python-add-01",
            "version": 1,
            "topic": "Python",
            "lesson_id": "functions-01",
            "title": "实现 add",
            "language": "Python",
            "version_scope": "3.14",
            "goal": "实现并解释一个纯函数",
            "layout": "standalone",
            "core_requirements": ["add(2, 3) 返回 5"],
            "explanation_prompts": ["解释输入边界"],
            "rubric": [{"criterion": "核心测试", "points": 100}],
            "hints": [
                {"level": 1, "content": "检查返回值"},
                {"level": 2, "content": "定位 add 函数"},
                {"level": 3, "content": "return a + b"},
            ],
            "optional_challenges": [],
        }
        value.update(updates)
        return value

    def plan(self, **updates: object) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_version": 1,
            "vault_root": str(self.vault),
            "workspace_root": str(self.workspace),
            "exercise_directory": "01-add",
            "exercise": self.exercise(),
            "files": [
                {
                    "path": "01-add.py",
                    "role": "starter",
                    "content_file": "starter.py",
                    "user_editable": True,
                },
                {
                    "path": "test_exercise.py",
                    "role": "core_test",
                    "content_file": "test_exercise.py",
                    "user_editable": False,
                },
            ],
            "commands": [
                {
                    "id": "core-test",
                    "kind": "test",
                    "argv": ["python3", "-m", "unittest", "-v", "test_exercise.py"],
                    "cwd": ".",
                    "env": {},
                    "timeout_seconds": 10,
                    "required": True,
                    "visible": True,
                    "effects": [],
                }
            ],
            "runtime_write_paths": ["__pycache__"],
            "cleanup_paths": ["__pycache__"],
        }
        value.update(updates)
        return value

    def write_plan(self, value: dict[str, object] | None = None, name: str = "exercise-plan.json") -> str:
        path = self.plan_dir / name
        path.write_text(json.dumps(value or self.plan(), ensure_ascii=False), encoding="utf-8")
        return str(path)

    def scaffold(self) -> tuple[Path, Path, dict[str, object]]:
        plan = exercise_cli.load_scaffold_plan(self.write_plan())
        exercise_cli.scaffold(plan, apply=True)
        manifest_path = self.workspace / "01-add" / ".learn-topic" / "manifest.json"
        resolved, package, manifest = exercise_cli.load_manifest(str(manifest_path))
        return resolved, package, manifest

    def authorize(self, manifest_path: Path, package: Path, manifest: dict[str, object]) -> None:
        exercise_cli.authorize(
            manifest_path,
            package,
            manifest,
            command_id="core-test",
            confirmed_at="2026-08-18T10:00:00+08:00",
            apply=True,
        )

    def test_workspace_root_must_exist_be_external_and_is_never_created(self) -> None:
        missing = self.sandbox / "missing"
        with self.assertRaisesRegex(exercise_cli.ContractError, "already exist"):
            exercise_cli.load_scaffold_plan(self.write_plan(self.plan(workspace_root=str(missing))))
        self.assertFalse(missing.exists())
        with self.assertRaisesRegex(exercise_cli.ContractError, "outside the Vault"):
            exercise_cli.load_scaffold_plan(
                self.write_plan(self.plan(workspace_root=str(self.vault)), "inside.json")
            )

    def test_plan_content_files_must_stay_in_plan_directory(self) -> None:
        outside = self.sandbox / "outside.py"
        outside.write_text("pass\n", encoding="utf-8")
        value = self.plan()
        value["files"][0]["content_file"] = str(outside)  # type: ignore[index]
        with self.assertRaisesRegex(exercise_cli.ContractError, "plan directory"):
            exercise_cli.load_scaffold_plan(self.write_plan(value))

    def test_exercise_directory_and_standalone_script_are_numbered(self) -> None:
        for directory in ("exercise", "1-add", "99-assets", "01/foo"):
            with self.subTest(directory=directory):
                with self.assertRaises(exercise_cli.ContractError):
                    exercise_cli.load_scaffold_plan(
                        self.write_plan(self.plan(exercise_directory=directory), f"{len(directory)}.json")
                    )
        value = self.plan()
        value["files"][0]["path"] = "exercise.py"  # type: ignore[index]
        with self.assertRaisesRegex(exercise_cli.ContractError, "numbered"):
            exercise_cli.load_scaffold_plan(self.write_plan(value, "unnumbered.json"))

    def test_project_layout_keeps_ecosystem_filenames(self) -> None:
        value = self.plan(exercise=self.exercise(layout="project"))
        value["files"][0]["path"] = "exercise.py"  # type: ignore[index]
        loaded = exercise_cli.load_scaffold_plan(self.write_plan(value))
        self.assertEqual(loaded["files"][0]["path"], "exercise.py")

    def test_scaffold_rejects_solution_hidden_tests_and_missing_core_test(self) -> None:
        solution = self.plan()
        solution["files"][0]["path"] = "01-solution.py"  # type: ignore[index]
        with self.assertRaisesRegex(exercise_cli.ContractError, "solution"):
            exercise_cli.load_scaffold_plan(self.write_plan(solution, "solution.json"))
        hidden = self.plan()
        hidden["commands"][0]["visible"] = False  # type: ignore[index]
        with self.assertRaisesRegex(exercise_cli.ContractError, "hidden"):
            exercise_cli.load_scaffold_plan(self.write_plan(hidden, "hidden.json"))
        missing = self.plan()
        missing["files"][1]["role"] = "support"  # type: ignore[index]
        with self.assertRaisesRegex(exercise_cli.ContractError, "core_test"):
            exercise_cli.load_scaffold_plan(self.write_plan(missing, "missing.json"))

    def test_one_core_exercise_contract_has_three_hints_and_max_two_challenges(self) -> None:
        for exercise in (
            self.exercise(hints=[{"level": 1, "content": "x"}]),
            self.exercise(optional_challenges=["a", "b", "c"]),
        ):
            with self.subTest(exercise=exercise):
                with self.assertRaises(exercise_cli.ContractError):
                    exercise_cli.load_scaffold_plan(self.write_plan(self.plan(exercise=exercise)))

    def test_rubric_is_public_and_totals_one_hundred(self) -> None:
        exercise = self.exercise(rubric=[{"criterion": "test", "points": 90}])
        with self.assertRaisesRegex(exercise_cli.ContractError, "total 100"):
            exercise_cli.load_scaffold_plan(self.write_plan(self.plan(exercise=exercise)))

    def test_commands_reject_shell_strings_secret_env_and_invalid_timeout(self) -> None:
        variants = [
            (["sh", "-c", "python test.py"], {}, 10),
            (["python3", "test.py"], {"API_TOKEN": "value"}, 10),
            (["python3", "test.py", "sk-secret"], {}, 10),
            (["python3", "test.py"], {}, 0),
        ]
        for index, (argv, env, timeout) in enumerate(variants):
            value = self.plan()
            command = value["commands"][0]  # type: ignore[index]
            command.update(argv=argv, env=env, timeout_seconds=timeout)
            with self.subTest(argv=argv, env=env, timeout=timeout):
                with self.assertRaises(exercise_cli.ContractError):
                    exercise_cli.load_scaffold_plan(self.write_plan(value, f"command-{index}.json"))

    def test_cleanup_must_be_declared_runtime_output(self) -> None:
        with self.assertRaisesRegex(exercise_cli.ContractError, "subset"):
            exercise_cli.load_scaffold_plan(
                self.write_plan(self.plan(runtime_write_paths=[], cleanup_paths=["build"]))
            )
        for index, cleanup in enumerate(("01-add.py", "src")):
            value = self.plan()
            if cleanup == "src":
                value["files"][0]["path"] = "src/01-add.py"  # type: ignore[index]
            value["runtime_write_paths"] = [cleanup]
            value["cleanup_paths"] = [cleanup]
            with self.subTest(cleanup=cleanup):
                with self.assertRaisesRegex(exercise_cli.ContractError, "overlaps protected"):
                    exercise_cli.load_scaffold_plan(self.write_plan(value, f"cleanup-{index}.json"))
        protected_runtime = self.plan(
            runtime_write_paths=["test_exercise.py"], cleanup_paths=[]
        )
        with self.assertRaisesRegex(exercise_cli.ContractError, "non-user file"):
            exercise_cli.load_scaffold_plan(
                self.write_plan(protected_runtime, "runtime-core-test.json")
            )

    def test_scaffold_dry_run_has_no_side_effect_and_apply_never_overwrites(self) -> None:
        plan = exercise_cli.load_scaffold_plan(self.write_plan())
        result = exercise_cli.scaffold(plan, apply=False)
        self.assertEqual(result["mode"], "dry-run")
        self.assertFalse((self.workspace / "01-add").exists())
        exercise_cli.scaffold(plan, apply=True)
        with self.assertRaisesRegex(exercise_cli.ContractError, "never overwrites"):
            exercise_cli.scaffold(plan, apply=True)

    def test_scaffold_manifest_omits_plan_paths_and_contains_answer_policy(self) -> None:
        manifest_path, _, manifest = self.scaffold()
        text = manifest_path.read_text(encoding="utf-8")
        self.assertNotIn(str(self.plan_dir), text)
        self.assertEqual(manifest["workspace_root"], str(self.workspace.resolve()))
        self.assertEqual(manifest["vault_root"], str(self.vault.resolve()))
        self.assertTrue(all("sha256" in item for item in manifest["files"]))
        self.assertFalse(manifest["exercise"]["answer_policy"]["model_written_result_counts_as_mastery"])

    def test_non_user_file_hash_is_bound_to_manifest_and_authorization(self) -> None:
        manifest_path, package, manifest = self.scaffold()
        self.authorize(manifest_path, package, manifest)
        before = exercise_cli.manifest_sha256(manifest)
        (package / "test_exercise.py").write_text("print('fake green')\n", encoding="utf-8")
        self.assertEqual(before, exercise_cli.manifest_sha256(manifest))
        with self.assertRaisesRegex(exercise_cli.ContractError, "non-user file changed"):
            exercise_cli.run_exercise(
                manifest_path, package, manifest, command_id="core-test", apply=True
            )
        with self.assertRaisesRegex(exercise_cli.ContractError, "non-user file changed"):
            exercise_cli.load_manifest(str(manifest_path))

    def test_authorize_dry_run_and_apply_bind_exact_manifest_and_command(self) -> None:
        manifest_path, package, manifest = self.scaffold()
        result = exercise_cli.authorize(
            manifest_path,
            package,
            manifest,
            command_id="core-test",
            confirmed_at="2026-08-18T10:00:00+08:00",
            apply=False,
        )
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["runtime_write_paths"], ["__pycache__"])
        self.assertEqual(result["cleanup_paths"], ["__pycache__"])
        self.assertFalse((package / ".learn-topic" / "authorization.json").exists())
        self.authorize(manifest_path, package, manifest)
        authorization = json.loads((package / ".learn-topic" / "authorization.json").read_text())
        self.assertEqual(authorization["manifest_sha256"], exercise_cli.manifest_sha256(manifest))
        self.assertEqual(authorization["commands"]["core-test"]["argv"], manifest["commands"][0]["argv"])

    def test_run_requires_authorization_and_rejects_stale_manifest(self) -> None:
        manifest_path, package, manifest = self.scaffold()
        with self.assertRaisesRegex(exercise_cli.ContractError, "authorization"):
            exercise_cli.run_exercise(
                manifest_path, package, manifest, command_id="core-test", apply=True
            )
        self.authorize(manifest_path, package, manifest)
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw["exercise"]["version"] = 2
        manifest_path.write_text(json.dumps(raw), encoding="utf-8")
        _, _, changed = exercise_cli.load_manifest(str(manifest_path))
        with self.assertRaisesRegex(exercise_cli.ContractError, "stale"):
            exercise_cli.run_exercise(
                manifest_path, package, changed, command_id="core-test", apply=True
            )

    def test_real_run_uses_argv_clean_env_and_writes_append_only_evidence(self) -> None:
        manifest_path, package, manifest = self.scaffold()
        self.authorize(manifest_path, package, manifest)
        with mock.patch.dict(os.environ, {"LEARN_TOPIC_SECRET": "must-not-leak"}, clear=False):
            first = exercise_cli.run_exercise(
                manifest_path, package, manifest, command_id="core-test", apply=True
            )
            second = exercise_cli.run_exercise(
                manifest_path, package, manifest, command_id="core-test", apply=True
            )
        self.assertTrue(first["ok"])
        self.assertEqual(first["attempt_id"], "attempt-01")
        self.assertEqual(second["attempt_id"], "attempt-02")
        evidence_files = sorted((package / ".learn-topic" / "evidence").glob("attempt-*.json"))
        self.assertEqual([path.name for path in evidence_files], ["attempt-01.json", "attempt-02.json"])
        evidence = json.loads(evidence_files[0].read_text())
        self.assertNotIn(str(package), evidence_files[0].read_text())
        self.assertNotIn("must-not-leak", evidence_files[0].read_text())
        self.assertEqual(evidence["status"], "passed")
        self.assertEqual(evidence["returncode"], 0)
        self.assertEqual(evidence["test_counts"]["passed"], 1)

    def test_failed_command_still_writes_failed_attempt(self) -> None:
        manifest_path, package, manifest = self.scaffold()
        (package / "01-add.py").write_text("def add(a, b): return 0\n", encoding="utf-8")
        self.authorize(manifest_path, package, manifest)
        result = exercise_cli.run_exercise(
            manifest_path, package, manifest, command_id="core-test", apply=True
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "failed")
        evidence = json.loads((package / ".learn-topic" / "evidence" / "attempt-01.json").read_text())
        self.assertEqual(evidence["status"], "failed")

    def test_timeout_is_evidence_and_not_reported_as_pass(self) -> None:
        value = self.plan()
        value["commands"][0].update(  # type: ignore[index]
            argv=["python3", "-c", "import time; time.sleep(2)"], timeout_seconds=1
        )
        # Python -c is argv-safe and not a shell command string.
        manifest_path_value = self.write_plan(value)
        plan = exercise_cli.load_scaffold_plan(manifest_path_value)
        exercise_cli.scaffold(plan, apply=True)
        manifest_path = self.workspace / "01-add" / ".learn-topic" / "manifest.json"
        resolved, package, manifest = exercise_cli.load_manifest(str(manifest_path))
        self.authorize(resolved, package, manifest)
        result = exercise_cli.run_exercise(
            resolved, package, manifest, command_id="core-test", apply=True
        )
        self.assertEqual(result["status"], "timeout")

    def test_unapproved_package_change_is_blocked_and_recorded(self) -> None:
        value = self.plan()
        value["commands"][0]["argv"] = [  # type: ignore[index]
            "python3", "-c", "from pathlib import Path; Path('surprise.txt').write_text('x')"
        ]
        plan = exercise_cli.load_scaffold_plan(self.write_plan(value))
        exercise_cli.scaffold(plan, apply=True)
        manifest_path = self.workspace / "01-add" / ".learn-topic" / "manifest.json"
        resolved, package, manifest = exercise_cli.load_manifest(str(manifest_path))
        self.authorize(resolved, package, manifest)
        result = exercise_cli.run_exercise(
            resolved, package, manifest, command_id="core-test", apply=True
        )
        self.assertEqual(result["status"], "blocked")
        evidence = json.loads((package / ".learn-topic" / "evidence" / "attempt-01.json").read_text())
        self.assertEqual(evidence["status"], "blocked")

    def test_runtime_symlink_is_blocked_recorded_and_safely_cleaned(self) -> None:
        value = self.plan(runtime_write_paths=["generated"], cleanup_paths=["generated"])
        value["commands"][0]["argv"] = [  # type: ignore[index]
            "python3", "-c",
            "from pathlib import Path; Path('generated').mkdir(); Path('generated/link').symlink_to('/tmp')",
        ]
        plan = exercise_cli.load_scaffold_plan(self.write_plan(value))
        exercise_cli.scaffold(plan, apply=True)
        manifest_path = self.workspace / "01-add" / ".learn-topic" / "manifest.json"
        resolved, package, manifest = exercise_cli.load_manifest(str(manifest_path))
        self.authorize(resolved, package, manifest)
        result = exercise_cli.run_exercise(
            resolved, package, manifest, command_id="core-test", apply=True
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["attempt_id"], "attempt-01")
        self.assertFalse((package / "generated").exists())
        evidence = json.loads((package / ".learn-topic" / "evidence" / "attempt-01.json").read_text())
        self.assertEqual(evidence["status"], "blocked")

    def test_declared_dangling_runtime_symlink_is_safely_unlinked(self) -> None:
        value = self.plan(
            runtime_write_paths=["generated", "generated/link"],
            cleanup_paths=["generated/link"],
        )
        value["commands"][0]["argv"] = [  # type: ignore[index]
            "python3", "-c",
            "from pathlib import Path; Path('generated').mkdir(); Path('generated/link').symlink_to('/definitely/missing/target')",
        ]
        plan = exercise_cli.load_scaffold_plan(self.write_plan(value))
        exercise_cli.scaffold(plan, apply=True)
        manifest_path = self.workspace / "01-add" / ".learn-topic" / "manifest.json"
        resolved, package, manifest = exercise_cli.load_manifest(str(manifest_path))
        self.authorize(resolved, package, manifest)
        result = exercise_cli.run_exercise(
            resolved, package, manifest, command_id="core-test", apply=True
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["cleaned"], ["generated/link"])
        self.assertFalse((package / "generated" / "link").is_symlink())

    def test_write_to_workspace_sibling_is_blocked(self) -> None:
        value = self.plan()
        value["commands"][0]["argv"] = [  # type: ignore[index]
            "python3", "-c", "from pathlib import Path; Path('../escaped.txt').write_text('x')"
        ]
        plan = exercise_cli.load_scaffold_plan(self.write_plan(value))
        exercise_cli.scaffold(plan, apply=True)
        manifest_path = self.workspace / "01-add" / ".learn-topic" / "manifest.json"
        resolved, package, manifest = exercise_cli.load_manifest(str(manifest_path))
        self.authorize(resolved, package, manifest)
        result = exercise_cli.run_exercise(
            resolved, package, manifest, command_id="core-test", apply=True
        )
        self.assertEqual(result["status"], "blocked")
        self.assertFalse((self.workspace / "escaped.txt").exists())

    def test_metadata_tampering_is_restored_and_attempt_ids_remain_append_only(self) -> None:
        value = self.plan()
        value["commands"][0]["argv"] = [  # type: ignore[index]
            "python3", "-c",
            "from pathlib import Path; p=Path('.learn-topic/evidence/attempt-01.json'); p.unlink() if p.exists() else None",
        ]
        plan = exercise_cli.load_scaffold_plan(self.write_plan(value))
        exercise_cli.scaffold(plan, apply=True)
        manifest_path = self.workspace / "01-add" / ".learn-topic" / "manifest.json"
        resolved, package, manifest = exercise_cli.load_manifest(str(manifest_path))
        self.authorize(resolved, package, manifest)
        first = exercise_cli.run_exercise(
            resolved, package, manifest, command_id="core-test", apply=True
        )
        first_bytes = (package / ".learn-topic" / "evidence" / "attempt-01.json").read_bytes()
        second = exercise_cli.run_exercise(
            resolved, package, manifest, command_id="core-test", apply=True
        )
        self.assertEqual(first["attempt_id"], "attempt-01")
        self.assertEqual(second["attempt_id"], "attempt-02")
        self.assertEqual(second["status"], "blocked")
        self.assertEqual(
            (package / ".learn-topic" / "evidence" / "attempt-01.json").read_bytes(),
            first_bytes,
        )

    def test_missing_executable_creates_a_blocked_attempt(self) -> None:
        value = self.plan()
        value["commands"][0]["argv"] = ["definitely-not-a-real-learn-topic-command"]  # type: ignore[index]
        plan = exercise_cli.load_scaffold_plan(self.write_plan(value))
        exercise_cli.scaffold(plan, apply=True)
        manifest_path = self.workspace / "01-add" / ".learn-topic" / "manifest.json"
        resolved, package, manifest = exercise_cli.load_manifest(str(manifest_path))
        self.authorize(resolved, package, manifest)
        result = exercise_cli.run_exercise(
            resolved, package, manifest, command_id="core-test", apply=True
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["attempt_id"], "attempt-01")
        evidence_text = (package / ".learn-topic" / "evidence" / "attempt-01.json").read_text()
        self.assertNotIn(str(package), evidence_text)

    def test_declared_runtime_output_can_be_cleaned_but_source_cannot(self) -> None:
        value = self.plan(runtime_write_paths=["generated"], cleanup_paths=["generated"])
        value["commands"][0]["argv"] = [  # type: ignore[index]
            "python3", "-c", "from pathlib import Path; Path('generated').mkdir(); Path('generated/x').write_text('x')"
        ]
        plan = exercise_cli.load_scaffold_plan(self.write_plan(value))
        exercise_cli.scaffold(plan, apply=True)
        manifest_path = self.workspace / "01-add" / ".learn-topic" / "manifest.json"
        resolved, package, manifest = exercise_cli.load_manifest(str(manifest_path))
        self.authorize(resolved, package, manifest)
        result = exercise_cli.run_exercise(
            resolved, package, manifest, command_id="core-test", apply=True
        )
        self.assertEqual(result["cleaned"], ["generated"])
        self.assertFalse((package / "generated").exists())
        manifest["cleanup_paths"] = ["01-add.py"]
        manifest["runtime_write_paths"] = ["01-add.py"]
        with self.assertRaisesRegex(exercise_cli.ContractError, "protected"):
            exercise_cli.cleanup_declared(package, manifest)

    def test_variant_requires_prior_attempt_is_public_optional_and_invalidates_auth(self) -> None:
        manifest_path, package, manifest = self.scaffold()
        (self.plan_dir / "test_variant.py").write_text("print('variant')\n", encoding="utf-8")
        variant = {
            "manifest": str(manifest_path),
            "challenge": "空输入边界",
            "files": [{"path": "test_variant.py", "content_file": "test_variant.py"}],
            "command": {
                "id": "variant-empty",
                "kind": "variant",
                "argv": ["python3", "test_variant.py"],
                "cwd": ".",
                "env": {},
                "timeout_seconds": 10,
                "required": False,
                "visible": True,
                "effects": [],
            },
        }
        variant_path = self.write_plan(variant, "variant.json")
        with self.assertRaisesRegex(exercise_cli.ContractError, "after a recorded"):
            exercise_cli.load_variant_plan(variant_path)
        self.authorize(manifest_path, package, manifest)
        exercise_cli.run_exercise(
            manifest_path, package, manifest, command_id="core-test", apply=True
        )
        loaded = exercise_cli.load_variant_plan(variant_path)
        result = exercise_cli.add_variant(loaded, apply=True)
        self.assertTrue(result["authorization_invalidated"])
        self.assertFalse((package / ".learn-topic" / "authorization.json").exists())
        _, _, changed = exercise_cli.load_manifest(str(manifest_path))
        self.assertEqual(changed["exercise"]["optional_challenges"], ["空输入边界"])
        self.assertEqual(changed["exercise"]["version"], 2)
        self.assertEqual(changed["commands"][-1]["required"], False)

    def test_manifest_cannot_drop_starter_core_test_or_required_test_command(self) -> None:
        manifest_path, _, _ = self.scaffold()
        original = json.loads(manifest_path.read_text(encoding="utf-8"))
        variants = []
        without_starter = json.loads(json.dumps(original))
        without_starter["files"] = [item for item in without_starter["files"] if item["role"] != "starter"]
        variants.append(without_starter)
        without_core_file = json.loads(json.dumps(original))
        without_core_file["files"] = [item for item in without_core_file["files"] if item["role"] != "core_test"]
        variants.append(without_core_file)
        without_required = json.loads(json.dumps(original))
        without_required["commands"][0]["required"] = False
        variants.append(without_required)
        for index, value in enumerate(variants):
            manifest_path.write_text(json.dumps(value), encoding="utf-8")
            with self.subTest(index=index):
                with self.assertRaisesRegex(exercise_cli.ContractError, "retain"):
                    exercise_cli.load_manifest(str(manifest_path))

    def test_manifest_and_evidence_writes_never_initialize_git(self) -> None:
        _, package, _ = self.scaffold()
        self.assertFalse((package / ".git").exists())

    def test_cli_exposes_only_scaffold_authorize_run_and_add_variant(self) -> None:
        parser = exercise_cli.build_parser()
        actions = next(action for action in parser._actions if action.dest == "command_name")
        self.assertEqual(set(actions.choices), {"scaffold", "authorize", "run", "add-variant"})

    def test_real_cli_end_to_end_scaffold_authorize_and_run(self) -> None:
        plan_path = self.write_plan()
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        dry = subprocess.run(
            ["python3", str(SCRIPT), "scaffold", "--plan", plan_path],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)["mode"], "dry-run")
        self.assertFalse((self.workspace / "01-add").exists())
        applied = subprocess.run(
            ["python3", str(SCRIPT), "scaffold", "--plan", plan_path, "--apply"],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        manifest = self.workspace / "01-add" / ".learn-topic" / "manifest.json"
        authorized = subprocess.run(
            [
                "python3", str(SCRIPT), "authorize", "--manifest", str(manifest),
                "--command", "core-test", "--confirmed-at", "2026-08-18T10:00:00+08:00", "--apply",
            ],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )
        self.assertEqual(authorized.returncode, 0, authorized.stderr)
        executed = subprocess.run(
            [
                "python3", str(SCRIPT), "run", "--manifest", str(manifest),
                "--command", "core-test", "--apply",
            ],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )
        self.assertEqual(executed.returncode, 0, executed.stderr)
        result = json.loads(executed.stdout)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["attempt_id"], "attempt-01")


if __name__ == "__main__":
    unittest.main(verbosity=2)

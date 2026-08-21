#!/usr/bin/env python3
"""Focused contracts for the open-source repository learning driver."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import repository_cli


class RepositoryDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.sandbox = Path(self.temporary_directory.name)
        self.vault = self.sandbox / "vault"
        self.plan_dir = self.sandbox / "plans"
        self.checkout = self.sandbox / "source" / "playwright"
        self.vault.mkdir()
        self.plan_dir.mkdir()
        self.commit = "a" * 40

    def plan(self, *, source_mode: str = "isolated") -> dict[str, object]:
        return {
            "provider": "github",
            "repository": "microsoft/playwright",
            "repository_url": "https://github.com/microsoft/playwright",
            "default_branch": "main",
            "target_ref": "refs/tags/v1.54.0",
            "baseline_commit": self.commit,
            "license_spdx": "Apache-2.0",
            "upstream_status": "unchanged",
            "verified_at": "2026-08-18",
            "vault_path": str(self.vault),
            "source_mode": source_mode,
            "checkout_path": str(self.checkout),
            "approved_files": ["packages/playwright-core/src/server/page.ts"],
            "test_argv": ["npm", "test", "--", "page.spec.ts"],
            "patch_file": str(self.plan_dir / "playwright.patch"),
            "evidence_file": str(self.plan_dir / "evidence.json"),
        }

    def write_plan(self, value: dict[str, object] | None = None) -> str:
        path = self.plan_dir / "repository-plan.json"
        path.write_text(
            json.dumps(value or self.plan(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(path)

    def initialize_repository(self, remote: str = "https://github.com/microsoft/playwright") -> str:
        self.checkout.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", str(self.checkout)], check=True)
        subprocess.run(
            ["git", "-C", str(self.checkout), "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.checkout), "config", "user.name", "Test"], check=True
        )
        (self.checkout / "approved.txt").write_text("before\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.checkout), "add", "approved.txt"], check=True)
        subprocess.run(["git", "-C", str(self.checkout), "commit", "-qm", "baseline"], check=True)
        subprocess.run(["git", "-C", str(self.checkout), "remote", "add", "origin", remote], check=True)
        return subprocess.run(
            ["git", "-C", str(self.checkout), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

    def test_valid_plan_normalizes_repository_identity_and_external_paths(self) -> None:
        plan = repository_cli.load_plan(self.write_plan())

        self.assertEqual(plan["repository"], "microsoft/playwright")
        self.assertEqual(plan["baseline_commit"], self.commit)
        self.assertEqual(plan["checkout_path"], str(self.checkout.resolve()))
        self.assertEqual(plan["test_argv"], ["npm", "test", "--", "page.spec.ts"])

    def test_checkout_and_evidence_must_stay_outside_vault(self) -> None:
        for field, value in (
            ("checkout_path", self.vault / "source"),
            ("patch_file", self.vault / "patch.diff"),
            ("evidence_file", self.vault / "evidence.json"),
        ):
            plan = self.plan()
            plan[field] = str(value)
            with self.subTest(field=field):
                with self.assertRaisesRegex(repository_cli.ContractError, "outside the Vault"):
                    repository_cli.load_plan(self.write_plan(plan))

    def test_evidence_outputs_must_stay_beside_the_plan(self) -> None:
        plan = self.plan()
        plan["patch_file"] = str(self.sandbox / "elsewhere.patch")
        with self.assertRaisesRegex(repository_cli.ContractError, "plan directory"):
            repository_cli.load_plan(self.write_plan(plan))

    def test_plan_patch_evidence_and_test_home_must_stay_outside_checkout(self) -> None:
        checkout = self.plan_dir / "source"
        plan = self.plan()
        plan.update(
            {
                "checkout_path": str(checkout),
                "patch_file": str(checkout / ".git" / "learning" / "candidate.patch"),
                "evidence_file": str(checkout / ".git" / "learning" / "evidence.json"),
            }
        )
        with self.assertRaisesRegex(repository_cli.ContractError, "outside checkout_path"):
            repository_cli.load_plan(self.write_plan(plan))

        nested = self.checkout / ".git" / "learning"
        nested.mkdir(parents=True)
        nested_plan = self.plan()
        nested_plan.update(
            {
                "patch_file": str(nested / "candidate.patch"),
                "evidence_file": str(nested / "evidence.json"),
            }
        )
        nested_plan_path = nested / "repository-plan.json"
        nested_plan_path.write_text(json.dumps(nested_plan), encoding="utf-8")
        with self.assertRaisesRegex(repository_cli.ContractError, "outside checkout_path"):
            repository_cli.load_plan(str(nested_plan_path))

    def test_repository_url_and_full_commit_are_canonical(self) -> None:
        for field, value in (
            ("repository_url", "git@github.com:microsoft/playwright.git"),
            ("repository", "playwright"),
            ("baseline_commit", "abc123"),
            ("target_ref", "v1.54.0"),
        ):
            plan = self.plan()
            plan[field] = value
            with self.subTest(field=field):
                with self.assertRaises(repository_cli.ContractError):
                    repository_cli.load_plan(self.write_plan(plan))

    def test_approved_files_reject_escape_git_and_duplicates(self) -> None:
        for files in (
            ["../secret"],
            [".git/config"],
            ["a.ts", "a.ts"],
            [],
        ):
            plan = self.plan()
            plan["approved_files"] = files
            with self.subTest(files=files):
                with self.assertRaises(repository_cli.ContractError):
                    repository_cli.load_plan(self.write_plan(plan))

    def test_test_command_is_an_argv_array_not_shell_text(self) -> None:
        for argv in ("npm test", [], ["npm", 1], ["sh", "-c", "npm test"]):
            plan = self.plan()
            plan["test_argv"] = argv
            with self.subTest(argv=argv):
                with self.assertRaises(repository_cli.ContractError):
                    repository_cli.load_plan(self.write_plan(plan))

    def test_prepare_dry_run_does_not_call_git_or_create_checkout(self) -> None:
        plan = repository_cli.load_plan(self.write_plan())
        with mock.patch.object(repository_cli, "run") as run:
            result = repository_cli.prepare(plan, apply=False)

        run.assert_not_called()
        self.assertFalse(self.checkout.exists())
        self.assertEqual(result["mode"], "dry-run")

    def test_prepare_uses_no_checkout_and_detached_commit_without_submodules(self) -> None:
        plan = repository_cli.load_plan(self.write_plan())
        completed = subprocess.CompletedProcess([], 0, self.commit + "\n", "")
        with mock.patch.object(repository_cli, "run", return_value=completed) as run:
            result = repository_cli.prepare(plan, apply=True)

        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn("--no-checkout", commands[0])
        self.assertIn("--filter=blob:none", commands[0])
        self.assertNotIn("--recurse-submodules", commands[0])
        self.assertIn("--detach", commands[1])
        self.assertIn(self.commit, commands[1])
        self.assertNotIn("commit", " ".join(" ".join(command) for command in commands))
        self.assertEqual(result["head"], self.commit)

    def test_existing_source_is_audited_but_never_prepared_over(self) -> None:
        self.checkout.mkdir(parents=True)
        plan = repository_cli.load_plan(self.write_plan(self.plan(source_mode="existing")))
        with self.assertRaisesRegex(repository_cli.ContractError, "existing source"):
            repository_cli.prepare(plan, apply=True)

    def test_patch_verification_requires_baseline_head_approved_files_and_passing_test(self) -> None:
        self.checkout.mkdir(parents=True)
        plan = repository_cli.load_plan(self.write_plan())
        changed = "packages/playwright-core/src/server/page.ts\0"
        patch = b"diff --git a/page.ts b/page.ts\n+fixed\n"
        responses = [
            subprocess.CompletedProcess([], 0, self.commit + "\n", ""),
            subprocess.CompletedProcess([], 0, changed, ""),
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess([], 0, patch, b""),
            subprocess.CompletedProcess([], 0, "ok\n", ""),
            subprocess.CompletedProcess([], 0, self.commit + "\n", ""),
            subprocess.CompletedProcess([], 0, changed, ""),
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess([], 0, patch, b""),
        ]
        with mock.patch.object(repository_cli, "run", side_effect=responses) as run:
            result = repository_cli.verify_patch(plan, apply=True)

        test_call = next(
            call for call in run.call_args_list if call.args[0] == plan["test_argv"]
        )
        self.assertEqual(test_call.args[0], plan["test_argv"])
        self.assertFalse(test_call.kwargs["shell"])
        self.assertEqual(result["graduation_status"], "passed")
        self.assertEqual(result["patch_sha256"], hashlib.sha256(patch).hexdigest())
        self.assertEqual(Path(plan["patch_file"]).read_bytes(), patch)
        evidence = json.loads(Path(plan["evidence_file"]).read_text(encoding="utf-8"))
        self.assertEqual(evidence["test"]["returncode"], 0)
        self.assertNotIn("stdout", evidence["test"])
        self.assertNotIn("LEARN_TOPIC_TEST_SECRET", test_call.kwargs["env"])

    def test_test_command_cannot_mutate_patch_or_create_unapproved_files(self) -> None:
        commit = self.initialize_repository()
        plan_value = self.plan()
        plan_value.update(
            {
                "baseline_commit": commit,
                "approved_files": ["approved.txt"],
                "test_argv": [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; Path('unapproved.txt').write_text('x')",
                ],
            }
        )
        (self.checkout / "approved.txt").write_text("after\n", encoding="utf-8")
        plan = repository_cli.load_plan(self.write_plan(plan_value))
        with self.assertRaisesRegex(repository_cli.ContractError, "unapproved|changed"):
            repository_cli.verify_patch(plan, apply=True)

    def test_test_command_receives_a_clean_environment_without_host_secrets(self) -> None:
        commit = self.initialize_repository()
        plan_value = self.plan()
        plan_value.update(
            {
                "baseline_commit": commit,
                "approved_files": ["approved.txt"],
                "test_argv": [
                    sys.executable,
                    "-c",
                    "import os,sys; sys.exit(1 if 'LEARN_TOPIC_TEST_SECRET' in os.environ else 0)",
                ],
            }
        )
        (self.checkout / "approved.txt").write_text("after\n", encoding="utf-8")
        plan = repository_cli.load_plan(self.write_plan(plan_value))
        with mock.patch.dict(os.environ, {"LEARN_TOPIC_TEST_SECRET": "do-not-inherit"}):
            result = repository_cli.verify_patch(plan, apply=True)
        self.assertEqual(result["graduation_status"], "passed")

    def test_audit_redacts_credentials_and_fails_closed_on_wrong_origin(self) -> None:
        commit = self.initialize_repository("https://token@github.com/microsoft/playwright.git")
        plan_value = self.plan(source_mode="existing")
        plan_value["baseline_commit"] = commit
        plan = repository_cli.load_plan(self.write_plan(plan_value))
        result = repository_cli.audit(plan)
        self.assertTrue(result["remote_match"])
        self.assertNotIn("remote", result)
        self.assertNotIn("token", json.dumps(result))

        subprocess.run(
            [
                "git", "-C", str(self.checkout), "remote", "set-url", "origin",
                "git@github.com:microsoft/playwright.git",
            ],
            check=True,
        )
        self.assertTrue(repository_cli.audit(plan)["remote_match"])

        subprocess.run(
            [
                "git", "-C", str(self.checkout), "remote", "set-url", "origin",
                "git@github.com:other/project.git",
            ],
            check=True,
        )
        with self.assertRaisesRegex(repository_cli.ContractError, "does not match"):
            repository_cli.audit(plan)

    def test_patch_graduation_requires_known_license_and_unchanged_upstream(self) -> None:
        for field, value in (
            ("license_spdx", "NOASSERTION"),
            ("upstream_status", "changed"),
        ):
            plan_value = self.plan()
            plan_value[field] = value
            plan = repository_cli.load_plan(self.write_plan(plan_value))
            with self.subTest(field=field):
                with self.assertRaisesRegex(repository_cli.ContractError, "license|upstream"):
                    repository_cli.verify_patch(plan, apply=False)

    def test_patch_verification_rejects_changed_head_unapproved_files_empty_patch_and_failed_test(self) -> None:
        self.checkout.mkdir(parents=True)
        plan = repository_cli.load_plan(self.write_plan())
        cases = (
            [subprocess.CompletedProcess([], 0, "b" * 40 + "\n", "")],
            [
                subprocess.CompletedProcess([], 0, self.commit + "\n", ""),
                subprocess.CompletedProcess([], 0, "README.md\0", ""),
            ],
            [
                subprocess.CompletedProcess([], 0, self.commit + "\n", ""),
                subprocess.CompletedProcess([], 0, "packages/playwright-core/src/server/page.ts\0", ""),
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, b"", b""),
            ],
            [
                subprocess.CompletedProcess([], 0, self.commit + "\n", ""),
                subprocess.CompletedProcess([], 0, "packages/playwright-core/src/server/page.ts\0", ""),
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, b"diff\n", b""),
                subprocess.CompletedProcess([], 1, "", "failed"),
            ],
        )
        for responses in cases:
            with self.subTest(length=len(responses)):
                with mock.patch.object(repository_cli, "run", side_effect=responses):
                    with self.assertRaises(repository_cli.ContractError):
                        repository_cli.verify_patch(plan, apply=True)

    def test_upstream_check_reads_remote_without_fetch_pull_merge_or_rebase(self) -> None:
        plan = repository_cli.load_plan(self.write_plan())
        metadata = json.dumps(
            {"archived": False, "disabled": False, "default_branch": "main", "pushed_at": "2026-08-18T00:00:00Z"}
        )
        responses = [
            subprocess.CompletedProcess([], 0, metadata, ""),
            subprocess.CompletedProcess([], 0, f"{'b' * 40}\trefs/heads/main\n", ""),
            subprocess.CompletedProcess(
                [],
                0,
                f"{'b' * 40}\trefs/tags/v1.54.0\n"
                f"{self.commit}\trefs/tags/v1.54.0^{{}}\n",
                "",
            ),
        ]
        with mock.patch.object(repository_cli, "run", side_effect=responses) as run:
            result = repository_cli.upstream_check(plan)

        commands = [" ".join(call.args[0]) for call in run.call_args_list]
        for forbidden in (" fetch ", " pull ", " merge ", " rebase ", " push "):
            self.assertFalse(any(forbidden in f" {command} " for command in commands))
        self.assertTrue(result["changed"])
        self.assertTrue(result["requires_decision"])
        self.assertFalse(result["target_changed"])
        self.assertEqual(result["target_commit"], self.commit)
        self.assertEqual(result["default_branch_commit"], "b" * 40)

    def test_fixed_baseline_suppresses_repeat_decision_for_stable_annotated_tag(self) -> None:
        plan_value = self.plan()
        plan_value["upstream_status"] = "fixed-baseline"
        plan = repository_cli.load_plan(self.write_plan(plan_value))
        metadata = json.dumps(
            {"archived": False, "disabled": False, "default_branch": "main", "pushed_at": None}
        )
        responses = [
            subprocess.CompletedProcess([], 0, metadata, ""),
            subprocess.CompletedProcess([], 0, f"{'b' * 40}\trefs/heads/main\n", ""),
            subprocess.CompletedProcess(
                [],
                0,
                f"{'c' * 40}\trefs/tags/v1.54.0\n"
                f"{self.commit}\trefs/tags/v1.54.0^{{}}\n",
                "",
            ),
        ]
        with mock.patch.object(repository_cli, "run", side_effect=responses):
            result = repository_cli.upstream_check(plan)
        self.assertEqual(result["target_commit"], self.commit)
        self.assertFalse(result["target_changed"])
        self.assertTrue(result["changed"])
        self.assertFalse(result["requires_decision"])

    def test_upstream_check_reports_deleted_target_and_default_branch_rename(self) -> None:
        plan = repository_cli.load_plan(self.write_plan())
        metadata = json.dumps(
            {"archived": False, "disabled": False, "default_branch": "trunk", "pushed_at": None}
        )
        responses = [
            subprocess.CompletedProcess([], 0, metadata, ""),
            subprocess.CompletedProcess([], 0, f"{'b' * 40}\trefs/heads/trunk\n", ""),
            subprocess.CompletedProcess([], 0, "", ""),
        ]
        with mock.patch.object(repository_cli, "run", side_effect=responses):
            result = repository_cli.upstream_check(plan)
        self.assertTrue(result["changed"])
        self.assertTrue(result["default_branch_changed"])
        self.assertFalse(result["target_exists"])

    def test_cli_exposes_audit_prepare_verify_patch_and_upstream_check(self) -> None:
        parser = repository_cli.build_parser()
        for command in ("audit", "prepare", "verify-patch", "upstream-check"):
            with self.subTest(command=command):
                args = parser.parse_args([command, "--plan", self.write_plan()])
                self.assertEqual(args.command, command)


if __name__ == "__main__":
    unittest.main(verbosity=2)

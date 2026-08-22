from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import repository_cli  # noqa: E402


class RepositoryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.vault = self.root / "vault"
        self.plans = self.root / "plans"
        self.checkout = self.root / "source" / "river-cache"
        self.vault.mkdir(); self.plans.mkdir()
        self.commit = "a" * 40

    def plan(self) -> dict:
        return {
            "provider": "github",
            "repository": "northstar-labs/river-cache",
            "repository_url": "https://github.com/northstar-labs/river-cache",
            "default_branch": "main",
            "target_ref": "refs/tags/v1.0.0",
            "baseline_commit": self.commit,
            "license_spdx": "MIT",
            "upstream_status": "unchanged",
            "verified_at": "2026-08-21",
            "vault_path": str(self.vault),
            "source_mode": "isolated",
            "checkout_path": str(self.checkout),
            "approved_files": ["src/cache.py"],
            "test_argv": ["python3", "-m", "unittest", "tests.test_cache"],
            "patch_file": str(self.plans / "candidate.patch"),
            "evidence_file": str(self.plans / "evidence.json"),
        }

    def write_plan(self, value: dict | None = None) -> str:
        path = self.plans / "plan.json"
        path.write_text(json.dumps(value or self.plan()), encoding="utf-8")
        return str(path)

    def test_fixed_outer_route_and_real_patch_gate(self) -> None:
        policy = (SCRIPTS.parent / "rules/repository-learning-policy.md").read_text(encoding="utf-8")
        for stage in (
            "01-项目概述", "02-运行与测试基线", "03-架构与模块地图", "04-核心调用链",
            "05-测试与质量体系", "06-Issue与PR考古", "07-最小修复实践", "08-深入与拓展",
            "09-复习与贡献准备", "10-学习记录", "99-assets",
        ):
            self.assertIn(stage, policy)
        for marker in ("完整 Commit", "一条核心切片", "真实最小 Patch", "相关测试"):
            self.assertIn(marker, policy)

    def test_plan_requires_external_paths_full_commit_and_argv(self) -> None:
        normalized = repository_cli.load_plan(self.write_plan())
        self.assertEqual(normalized["baseline_commit"], self.commit)
        for field, value in (
            ("checkout_path", str(self.vault / "source")),
            ("baseline_commit", "abc123"),
            ("test_argv", ["sh", "-c", "python -m unittest"]),
        ):
            invalid = self.plan(); invalid[field] = value
            with self.subTest(field=field), self.assertRaises(repository_cli.ContractError):
                repository_cli.load_plan(self.write_plan(invalid))

    def test_prepare_dry_run_never_creates_or_calls_git(self) -> None:
        plan = repository_cli.load_plan(self.write_plan())
        with mock.patch.object(repository_cli, "run") as runner:
            result = repository_cli.prepare(plan, apply=False)
        runner.assert_not_called()
        self.assertFalse(self.checkout.exists())
        self.assertEqual(result["mode"], "dry-run")

    def test_patch_gate_rejects_changed_head_and_unapproved_file(self) -> None:
        self.checkout.mkdir(parents=True)
        plan = repository_cli.load_plan(self.write_plan())
        with mock.patch.object(repository_cli, "run", return_value=subprocess.CompletedProcess([], 0, "b" * 40 + "\n", "")):
            with self.assertRaises(repository_cli.ContractError):
                repository_cli.verify_patch(plan, apply=True)

    def test_patch_dry_run_uses_route_graduation_status(self) -> None:
        self.checkout.mkdir(parents=True)
        plan = repository_cli.load_plan(self.write_plan())
        snapshot = {"head": self.commit, "changed": ["src/cache.py"], "patch": b"patch", "patch_sha256": "abc"}
        with mock.patch.object(repository_cli, "patch_snapshot", return_value=snapshot):
            result = repository_cli.verify_patch(plan, apply=False)
        self.assertEqual(result["graduation_status"], "pending-evidence")
        responses = [
            subprocess.CompletedProcess([], 0, self.commit + "\n", ""),
            subprocess.CompletedProcess([], 0, "README.md\0", ""),
        ]
        with mock.patch.object(repository_cli, "run", side_effect=responses):
            with self.assertRaises(repository_cli.ContractError):
                repository_cli.verify_patch(plan, apply=True)

    def test_upstream_check_is_read_only(self) -> None:
        plan = repository_cli.load_plan(self.write_plan())
        metadata = json.dumps({"archived": False, "disabled": False, "default_branch": "main", "pushed_at": None})
        responses = [
            subprocess.CompletedProcess([], 0, metadata, ""),
            subprocess.CompletedProcess([], 0, f"{'b' * 40}\trefs/heads/main\n", ""),
            subprocess.CompletedProcess([], 0, f"{self.commit}\trefs/tags/v1.0.0\n", ""),
        ]
        with mock.patch.object(repository_cli, "run", side_effect=responses) as runner:
            result = repository_cli.upstream_check(plan)
        commands = [" ".join(call.args[0]) for call in runner.call_args_list]
        for forbidden in ("fetch", "pull", "merge", "rebase", "push"):
            self.assertFalse(any(forbidden in command.split() for command in commands))
        self.assertTrue(result["changed"])

    def test_cli_exposes_repository_commands(self) -> None:
        parser = repository_cli.build_parser()
        for command in ("audit", "prepare", "verify-patch", "upstream-check"):
            args = parser.parse_args([command, "--plan", self.write_plan()])
            self.assertEqual(args.command, command)

    def test_real_temp_git_patch_and_test_graduation(self) -> None:
        self.checkout.mkdir(parents=True)
        (self.checkout / "src").mkdir(); (self.checkout / "tests").mkdir()
        (self.checkout / "src" / "cache.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        (self.checkout / "tests" / "test_cache.py").write_text(
            "import unittest\nfrom src.cache import add\n\nclass T(unittest.TestCase):\n    def test_add(self): self.assertEqual(add(1, 2), 3)\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=self.checkout, check=True)
        subprocess.run(["git", "config", "user.name", "fixture"], cwd=self.checkout, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=self.checkout, check=True)
        subprocess.run(["git", "add", "src/cache.py", "tests/test_cache.py"], cwd=self.checkout, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.checkout, check=True)
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.checkout, text=True, capture_output=True, check=True).stdout.strip()
        (self.checkout / "src" / "cache.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        plan = self.plan()
        plan.update({
            "source_mode": "existing", "baseline_commit": commit, "target_ref": commit,
            "test_argv": [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        })
        normalized = repository_cli.load_plan(self.write_plan(plan))
        result = repository_cli.verify_patch(normalized, apply=True)
        self.assertEqual(result["graduation_status"], "passed")
        self.assertTrue(Path(normalized["patch_file"]).read_bytes())
        self.assertEqual(json.loads(Path(normalized["evidence_file"]).read_text())["baseline_commit"], commit)


if __name__ == "__main__":
    unittest.main(verbosity=2)

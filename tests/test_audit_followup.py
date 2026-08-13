from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.requirements_fixture import DEFAULT_SAMPLES, write_json_yaml, write_requirement_package
from tests.test_validate_prd_checkpoint import write_checkpoint

REPO_ROOT = Path(__file__).resolve().parents[1]
PRD_VALIDATOR = REPO_ROOT / "skills" / "build-prd" / "scripts" / "validate_prd.py"
CHECKPOINT_VALIDATOR = REPO_ROOT / "skills" / "build-prd" / "scripts" / "validate_checkpoint.py"
TRACEABILITY = REPO_ROOT / "skills" / "vibe-coding" / "scripts" / "vibe_validation" / "traceability.py"
VIBE_SCRIPTS = REPO_ROOT / "skills" / "vibe-coding" / "scripts"


class AuditFollowupTests(unittest.TestCase):
    def run_prd(self, target: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PRD_VALIDATOR), str(target), "--strict"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def run_checkpoint(self, target: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECKPOINT_VALIDATOR), str(target), "--strict"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_semver_accepts_zero_major_and_metadata_but_rejects_bare_zero(self) -> None:
        for version in ("0.1.0", "1.2.3-rc.1+build.5"):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as temp:
                package = write_requirement_package(Path(temp))
                manifest_path = package / "需求包清单.yaml"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["package_version"] = version
                write_json_yaml(manifest_path, manifest)
                prd = package / "PRD需求文档.md"
                prd.write_text(prd.read_text(encoding="utf-8").replace("- 需求包版本：1.0.0", f"- 需求包版本：{version}"), encoding="utf-8")
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                for item in manifest["files"]:
                    if item["path"] == "PRD需求文档.md":
                        import hashlib
                        item["sha256"] = hashlib.sha256(prd.read_bytes()).hexdigest()
                write_json_yaml(manifest_path, manifest)
                result = self.run_prd(package)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        with tempfile.TemporaryDirectory() as temp:
            package = write_requirement_package(Path(temp))
            manifest_path = package / "需求包清单.yaml"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["package_version"] = "0"
            write_json_yaml(manifest_path, manifest)
            result = self.run_prd(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("PACKAGE_VERSION", result.stdout)

    def test_portable_source_rejects_host_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            package = write_requirement_package(Path(temp))
            manifest_path = package / "需求包清单.yaml"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source"]["project"] = "/Users/alice/private-project"
            write_json_yaml(manifest_path, manifest)
            result = self.run_prd(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("SOURCE_PORTABILITY", result.stdout)

    def test_behavior_fixture_contains_real_empty_and_eighty_character_inputs(self) -> None:
        invalid = next(item for item in DEFAULT_SAMPLES if item["id"] == "SAMPLE-TASK-003")
        boundary = next(item for item in DEFAULT_SAMPLES if item["id"] == "SAMPLE-TASK-004")
        self.assertEqual(invalid["user_input"], "")
        self.assertEqual(len(boundary["user_input"]), 80)

    def test_stage_manifest_template_contains_required_contract(self) -> None:
        template = json.loads(
            (REPO_ROOT / "skills" / "build-prd" / "templates" / "requirement-manifest.template.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(set(template["stage"]), {"included_scope", "deferred_scope", "acceptance"})

    def test_checkpoint_strict_rejects_dependency_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            checkpoint = write_checkpoint(Path(temp))
            session_path = checkpoint / "会话.yaml"
            session = json.loads(session_path.read_text(encoding="utf-8"))
            session["domains"][0]["dependencies"] = ["reporting"]
            session["domains"][1]["dependencies"] = ["task-management"]
            write_json_yaml(session_path, session)
            result = self.run_checkpoint(checkpoint)
            self.assertEqual(result.returncode, 1)
            self.assertIn("DOMAIN_DEPENDENCY_CYCLE", result.stdout)

    def test_checkpoint_strict_rejects_ready_state_with_pending_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            checkpoint = write_checkpoint(Path(temp))
            session_path = checkpoint / "会话.yaml"
            session = json.loads(session_path.read_text(encoding="utf-8"))
            session["status"] = "ready_for_authoring"
            write_json_yaml(session_path, session)
            result = self.run_checkpoint(checkpoint)
            self.assertEqual(result.returncode, 1)
            self.assertIn("READY_FOR_AUTHORING", result.stdout)

    def test_task_sequence_is_independent_of_domain_file_order(self) -> None:
        sys.path.insert(0, str(VIBE_SCRIPTS))
        try:
            from vibe_validation.model import Issue
            from vibe_validation.traceability import validate_tasks

            def task(number: int) -> str:
                return f"""### TASK-{number:03d} 示例\n\n- 需求/验收/Finding：F-001\n- 首个验证证据：pytest -q\n- 正常测试数据：fixture\n- 验证命令：pytest -q\n- 提交边界：本任务\n- 回滚：revert\n- 完成条件：测试通过\n"""

            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                issues: list[Issue] = []
                validate_tasks(task(2) + "\n" + task(1), root / "docs" / "实施任务" / "功能域", root, issues, False)
                self.assertFalse(any(item.code == "TASK_SEQUENCE" for item in issues), issues)
        finally:
            sys.path.remove(str(VIBE_SCRIPTS))

    def test_behavior_sample_id_is_part_of_vibe_traceability(self) -> None:
        sys.path.insert(0, str(VIBE_SCRIPTS))
        try:
            from vibe_validation.model import Issue
            from vibe_validation.traceability import validate_traceability

            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                issues: list[Issue] = []
                validate_traceability(
                    "greenfield",
                    "F-001 F-001-AC-01 SAMPLE-TASK-001",
                    "F-001 F-001-AC-01",
                    None,
                    root / "plan.md",
                    root / "report.md",
                    root,
                    issues,
                )
                self.assertTrue(any("SAMPLE-TASK-001" in item.message for item in issues))
        finally:
            sys.path.remove(str(VIBE_SCRIPTS))


if __name__ == "__main__":
    unittest.main()

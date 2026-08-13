from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.requirements_fixture import (
    DEFAULT_SAMPLES,
    refresh_manifest_hashes,
    write_json_yaml,
    write_requirement_package,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "skills" / "build-prd" / "scripts" / "validate_prd.py"


class ValidatePrdTests(unittest.TestCase):
    def run_validator(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(path), "--strict"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_valid_requirement_package_passes_from_project_or_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = write_requirement_package(root)
            for target in (root, package, package / "PRD需求文档.md"):
                with self.subTest(target=target):
                    result = self.run_validator(target)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("PASS", result.stdout)

    def test_shipped_example_package_passes(self) -> None:
        example = REPO_ROOT / "skills" / "build-prd" / "examples" / "产品需求"
        result = self.run_validator(example)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_root_prd_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = root / "docs" / "PRD需求文档.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("# PRD需求文档\n", encoding="utf-8")
            result = self.run_validator(legacy)
            self.assertEqual(result.returncode, 1)
            self.assertIn("LEGACY_OUTPUT_PATH", result.stdout)

    def test_unconfirmed_package_and_checkpoint_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = write_requirement_package(root, status="in_progress")
            result = self.run_validator(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("PACKAGE_STATUS", result.stdout)

            checkpoint = root / ".build-goals" / "build-prd"
            checkpoint.mkdir(parents=True)
            write_json_yaml(checkpoint / "session.yaml", {"status": "in_progress"})
            result = self.run_validator(checkpoint)
            self.assertEqual(result.returncode, 1)
            self.assertIn("OUTPUT_PATH", result.stdout)

    def test_hash_drift_and_undeclared_files_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = write_requirement_package(root)
            domain = package / "功能域" / "任务管理.md"
            domain.write_text(domain.read_text(encoding="utf-8") + "\n漂移。\n", encoding="utf-8")
            result = self.run_validator(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("FILE_HASH", result.stdout)

            refresh_manifest_hashes(package)
            (package / "未声明.md").write_text("未声明", encoding="utf-8")
            result = self.run_validator(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("UNDECLARED_FILE", result.stdout)

    def test_symlinked_package_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = write_requirement_package(root)
            behavior = package / "行为样例" / "任务管理.yaml"
            content = behavior.read_text(encoding="utf-8")
            behavior.unlink()
            real = package / "行为样例" / "real.yaml"
            real.write_text(content, encoding="utf-8")
            behavior.symlink_to("real.yaml")
            result = self.run_validator(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("NON_REGULAR_FILE", result.stdout)

    def test_symlinked_package_root_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = write_requirement_package(root / "source")
            target = root / "target"
            (target / "docs").mkdir(parents=True)
            (target / "docs" / "产品需求").symlink_to(source, target_is_directory=True)

            result = self.run_validator(target)

            self.assertEqual(result.returncode, 1)
            self.assertIn("NON_REGULAR_FILE", result.stdout)

    def test_missing_behavior_sample_kind_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            for kind in ("normal", "clarification", "invalid", "boundary"):
                with self.subTest(kind=kind):
                    root = Path(temp) / kind
                    samples = [item for item in DEFAULT_SAMPLES if item["kind"] != kind]
                    package = write_requirement_package(root, samples=samples)
                    result = self.run_validator(package)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("SAMPLE_KIND_COVERAGE", result.stdout)

    def test_sample_requires_output_contract_assertions_and_forbidden_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            samples = json.loads(json.dumps(DEFAULT_SAMPLES, ensure_ascii=False))
            samples[0]["output_contract"].pop("semantic")
            samples[0]["assertions"] = []
            samples[0]["forbidden"] = []
            package = write_requirement_package(root, samples=samples)
            result = self.run_validator(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("OUTPUT_CONTRACT", result.stdout)
            self.assertIn("SAMPLE_ASSERTIONS", result.stdout)
            self.assertIn("SAMPLE_FORBIDDEN", result.stdout)

    def test_unresolved_and_internal_implementation_content_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = write_requirement_package(root)
            domain = package / "功能域" / "任务管理.md"
            domain.write_text(
                domain.read_text(encoding="utf-8")
                + "\n## 内部技术架构\n\nTBD：沿用旧框架。\n",
                encoding="utf-8",
            )
            refresh_manifest_hashes(package)
            result = self.run_validator(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("UNRESOLVED_CONTENT", result.stdout)
            self.assertIn("INTERNAL_IMPLEMENTATION_SECTION", result.stdout)

    def test_missing_acceptance_and_duplicate_feature_ids_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = write_requirement_package(root)
            domain = package / "功能域" / "任务管理.md"
            text = domain.read_text(encoding="utf-8")
            text = text.replace(
                "- `F-001-AC-01` Given 用户位于任务页，When 输入“预约牙医”并点击“创建”，Then 列表顶部显示状态为“未完成”的“预约牙医”，并提示“任务已创建”。\n"
                "- `F-001-AC-02` Given 任务名称为空，When 用户点击“创建”，Then 显示“请输入任务名称”并聚焦输入框。\n",
                "没有验收项。\n",
            )
            text += "\n### F-001 重复功能\n\n重复编号。\n"
            domain.write_text(text, encoding="utf-8")
            refresh_manifest_hashes(package)
            result = self.run_validator(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("AC_REQUIRED", result.stdout)
            self.assertIn("FEATURE_ID_DUPLICATE", result.stdout)

    def test_insufficient_research_coverage_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = write_requirement_package(root)
            prd = package / "PRD需求文档.md"
            prd.write_text(
                prd.read_text(encoding="utf-8").replace(
                    "| 竞品 | Competitor Two | https://competitor-two.example/product | 2026-08-13 | 列表反馈方式 |\n",
                    "",
                ),
                encoding="utf-8",
            )
            refresh_manifest_hashes(package)
            result = self.run_validator(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("RESEARCH_COVERAGE", result.stdout)

    def test_full_package_rejects_missing_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            package = write_requirement_package(Path(temp), dependency="shared-auth")
            result = self.run_validator(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("DOMAIN_DEPENDENCY", result.stdout)

    def test_domain_name_must_match_requirement_and_example_file_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            package = write_requirement_package(Path(temp))
            manifest_path = package / "需求包清单.yaml"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["domains"][0]["name"] = "待办事项"
            write_json_yaml(manifest_path, manifest)

            result = self.run_validator(package)

            self.assertEqual(result.returncode, 1)
            self.assertIn("DOMAIN_FILE_NAME", result.stdout)

    def test_closed_stage_package_accepts_declared_external_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            package = write_requirement_package(
                Path(temp),
                package_type="stage",
                dependency="shared-auth",
                external_dependencies=[
                    {
                        "id": "shared-auth",
                        "contract": "用户身份已经由外部系统建立并提供稳定主体 ID。",
                    }
                ],
                stage={
                    "included_scope": "任务创建闭环",
                    "deferred_scope": "团队协作和收费能力",
                    "acceptance": "F-001 的全部验收标准能够独立执行。",
                },
            )
            result = self.run_validator(package)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_package_requires_closed_scope_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            package = write_requirement_package(
                Path(temp), package_type="stage", dependency="shared-auth"
            )
            result = self.run_validator(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("STAGE_CONTRACT", result.stdout)
            self.assertIn("DOMAIN_DEPENDENCY", result.stdout)


if __name__ == "__main__":
    unittest.main()

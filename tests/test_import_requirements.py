from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.requirements_fixture import refresh_manifest_hashes, write_requirement_package

REPO_ROOT = Path(__file__).resolve().parents[1]
IMPORTER = (
    REPO_ROOT / "skills" / "vibe-coding" / "scripts" / "import_requirements.py"
)
VALIDATOR = REPO_ROOT / "skills" / "build-prd" / "scripts" / "validate_prd.py"


class ImportRequirementsTests(unittest.TestCase):
    def run_importer(
        self, source: Path, target: Path, *extra: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(IMPORTER),
                str(source),
                str(target),
                *extra,
            ],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_dry_run_reports_snapshot_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = write_requirement_package(root / "source")
            target = root / "target"
            result = self.run_importer(source, target, "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["written"])
            self.assertIn("task-management", payload["changed_domains"])
            self.assertFalse((target / "docs" / "产品需求").exists())

    def test_write_imports_valid_snapshot_and_records_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = write_requirement_package(root / "source")
            target = root / "target"
            result = self.run_importer(source, target, "--write")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            imported = target / "docs" / "产品需求"
            manifest = json.loads(
                (imported / "需求包清单.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["import"]["source"], str(source.resolve()))
            self.assertRegex(manifest["import"]["imported_at"], r"^\d{4}-\d{2}-\d{2}T")
            validation = subprocess.run(
                [sys.executable, str(VALIDATOR), str(target), "--strict"],
                cwd=REPO_ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(
                validation.returncode, 0, validation.stdout + validation.stderr
            )

    def test_same_snapshot_ignores_local_import_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = write_requirement_package(root / "source")
            target = root / "target"
            self.assertEqual(
                self.run_importer(source, target, "--write").returncode, 0
            )

            compared = self.run_importer(source, target, "--json")

            self.assertEqual(compared.returncode, 0, compared.stdout + compared.stderr)
            payload = json.loads(compared.stdout)
            self.assertFalse(payload["manifest_changed"])
            self.assertFalse(payload["has_changes"])
            self.assertFalse(payload["requires_replace"])
            self.assertEqual(payload["changed_files"], [])

    def test_existing_snapshot_requires_explicit_replace_and_reports_impact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_v1 = write_requirement_package(root / "source-v1")
            target = root / "target"
            self.assertEqual(
                self.run_importer(source_v1, target, "--write").returncode, 0
            )

            source_v2 = write_requirement_package(root / "source-v2")
            domain = source_v2 / "功能域" / "任务管理.md"
            domain.write_text(
                domain.read_text(encoding="utf-8").replace(
                    "让用户记录一项需要完成的事项。",
                    "让用户记录并确认一项需要完成的事项。",
                ),
                encoding="utf-8",
            )
            refresh_manifest_hashes(source_v2)

            compared = self.run_importer(source_v2, target, "--json")
            self.assertEqual(compared.returncode, 0, compared.stdout + compared.stderr)
            payload = json.loads(compared.stdout)
            self.assertIn("task-management", payload["changed_domains"])
            self.assertIn("F-001", payload["changed_features"])
            self.assertTrue(payload["requires_replace"])

            refused = self.run_importer(source_v2, target, "--write")
            self.assertEqual(refused.returncode, 1)
            self.assertIn("TARGET_EXISTS", refused.stdout)

            replaced = self.run_importer(
                source_v2, target, "--write", "--replace"
            )
            self.assertEqual(replaced.returncode, 0, replaced.stdout + replaced.stderr)
            self.assertIn(
                "记录并确认",
                (target / "docs" / "产品需求" / "功能域" / "任务管理.md").read_text(
                    encoding="utf-8"
                ),
            )

    def test_manifest_only_change_requires_explicit_replace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_v1 = write_requirement_package(root / "source-v1")
            target = root / "target"
            self.assertEqual(
                self.run_importer(source_v1, target, "--write").returncode, 0
            )

            source_v2 = write_requirement_package(root / "source-v2")
            manifest_path = source_v2 / "需求包清单.yaml"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source"]["revision"] = "fixture-v2"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            compared = self.run_importer(source_v2, target, "--json")

            self.assertEqual(compared.returncode, 0, compared.stdout + compared.stderr)
            payload = json.loads(compared.stdout)
            self.assertTrue(payload["manifest_changed"])
            self.assertIn("需求包清单.yaml", payload["changed_files"])
            self.assertTrue(payload["requires_replace"])

            refused = self.run_importer(source_v2, target, "--write")
            self.assertEqual(refused.returncode, 1)
            self.assertIn("TARGET_EXISTS", refused.stdout)

            replaced = self.run_importer(
                source_v2, target, "--write", "--replace"
            )
            self.assertEqual(replaced.returncode, 0, replaced.stdout + replaced.stderr)
            imported = json.loads(
                (target / "docs" / "产品需求" / "需求包清单.yaml").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(imported["source"]["revision"], "fixture-v2")

    def test_invalid_or_symlinked_source_is_never_imported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = write_requirement_package(root / "source")
            domain = source / "功能域" / "任务管理.md"
            content = domain.read_text(encoding="utf-8")
            domain.unlink()
            real = source / "功能域" / "real.md"
            real.write_text(content, encoding="utf-8")
            domain.symlink_to("real.md")
            target = root / "target"
            result = self.run_importer(source, target, "--write")
            self.assertEqual(result.returncode, 1)
            self.assertIn("NON_REGULAR_FILE", result.stdout)
            self.assertFalse((target / "docs" / "产品需求").exists())

    def test_existing_live_link_snapshot_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = write_requirement_package(root / "source")
            target = root / "target"
            (target / "docs").mkdir(parents=True)
            (target / "docs" / "产品需求").symlink_to(
                source, target_is_directory=True
            )

            result = self.run_importer(source, target, "--write", "--replace")

            self.assertEqual(result.returncode, 1)
            self.assertIn("TARGET_INVALID", result.stdout)
            self.assertTrue((target / "docs" / "产品需求").is_symlink())


if __name__ == "__main__":
    unittest.main()

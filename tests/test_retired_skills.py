from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RETIRED_SKILLS = ("build-prd", "vibe-coding")


class RetiredSkillsTests(unittest.TestCase):
    def test_retired_skills_and_dedicated_test_assets_are_removed(self) -> None:
        paths = [f"skills/{name}" for name in RETIRED_SKILLS] + [
            "tests/requirements_fixture.py",
            "tests/vibe_coding_validator_cases.py",
            "tests/test_validate_prd.py",
            "tests/test_validate_prd_checkpoint.py",
            "tests/test_validate_vibe_coding.py",
            "tests/test_import_requirements.py",
            "tests/test_run_evidence.py",
            "tests/test_audit_followup.py",
        ]
        for relative in paths:
            with self.subTest(path=relative):
                self.assertFalse(REPO_ROOT.joinpath(relative).exists())

    def test_shipped_files_do_not_reference_retired_capabilities(self) -> None:
        paths = [
            REPO_ROOT / "README.md",
            REPO_ROOT / ".plugin-shared-files.json",
            REPO_ROOT / "scripts/install_skill.py",
            REPO_ROOT / ".claude-plugin/plugin.json",
            REPO_ROOT / ".claude-plugin/marketplace.json",
            REPO_ROOT / ".codex-plugin/plugin.json",
            REPO_ROOT / ".zcode-plugin/plugin.json",
            REPO_ROOT / ".agents/plugins/marketplace.json",
        ]
        paths.extend(
            path
            for path in REPO_ROOT.joinpath("skills").rglob("*")
            if path.is_file() and path.suffix in {".md", ".yaml", ".json", ".py"}
        )
        for path in paths:
            content = path.read_text(encoding="utf-8")
            for name in RETIRED_SKILLS:
                with self.subTest(path=path.relative_to(REPO_ROOT), skill=name):
                    self.assertFalse(name in content, f"{path}: {name}")

    def test_retired_skills_cannot_be_installed_on_any_platform(self) -> None:
        for name in RETIRED_SKILLS:
            for platform in ("claude", "codex", "zcode", "pi"):
                with (
                    self.subTest(skill=name, platform=platform),
                    tempfile.TemporaryDirectory() as temp,
                ):
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(REPO_ROOT / "scripts/install_skill.py"),
                            name,
                            "--platform", platform,
                            "--scope", "project",
                            "--project-dir", temp,
                        ],
                        cwd=REPO_ROOT,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn("找不到 Skill 源目录", result.stderr)
                    self.assertEqual(list(Path(temp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()

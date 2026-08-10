from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "install_skill.py"


class InstallSkillTests(unittest.TestCase):
    def run_installer(
        self,
        home: Path,
        platform: str,
        skill: str = "build-skill",
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(home)
        return subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                skill,
                "--platform",
                platform,
                "--scope",
                "user",
                *extra,
            ],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_codex_install_strips_claude_field_and_keeps_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            result = self.run_installer(home, "codex")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            destination = home / ".agents" / "skills" / "build-skill"
            skill_md = destination.joinpath("SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("disable-model-invocation:", skill_md)
            self.assertTrue(destination.joinpath("agents", "openai.yaml").is_file())
            self.assertIn(
                "allow_implicit_invocation: false",
                destination.joinpath("agents", "openai.yaml").read_text(
                    encoding="utf-8"
                ),
            )

    def test_claude_install_keeps_manual_only_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            result = self.run_installer(home, "claude")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            destination = home / ".claude" / "skills" / "build-skill"
            skill_md = destination.joinpath("SKILL.md").read_text(encoding="utf-8")
            self.assertIn("disable-model-invocation: true", skill_md)
            self.assertFalse(destination.joinpath("agents").exists())

            second = self.run_installer(home, "claude")
            self.assertEqual(second.returncode, 1)
            self.assertIn("--force", second.stderr)

            forced = self.run_installer(home, "claude", "build-skill", "--force")
            self.assertEqual(forced.returncode, 0, forced.stdout + forced.stderr)

    def test_build_plugin_install_materializes_shared_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            result = self.run_installer(
                home,
                "codex",
                "build-plugin",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            destination = home / ".agents" / "skills" / "build-plugin"
            shared = destination / "prompts" / "reviewer.agent.md"
            self.assertTrue(shared.is_file())
            self.assertFalse(shared.is_symlink())
            self.assertTrue(
                destination.joinpath("scripts", "validate_skill.py").is_file()
            )

    def test_handoff_codex_install_strips_claude_only_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            result = self.run_installer(home, "codex", "handoff")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            destination = home / ".agents" / "skills" / "handoff"
            skill_md = destination.joinpath("SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("argument-hint:", skill_md)
            self.assertNotIn("disable-model-invocation:", skill_md)

    def test_build_prd_installs_for_both_platforms(self) -> None:
        for platform, root_name in (("claude", ".claude"), ("codex", ".agents")):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as temp:
                home = Path(temp)
                result = self.run_installer(home, platform, "build-prd")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

                destination = home / root_name / "skills" / "build-prd"
                self.assertTrue(destination.joinpath("SKILL.md").is_file())
                self.assertTrue(
                    destination.joinpath("scripts", "validate_prd.py").is_file()
                )
                if platform == "claude":
                    self.assertFalse(destination.joinpath("agents").exists())
                else:
                    self.assertTrue(
                        destination.joinpath("agents", "openai.yaml").is_file()
                    )

    def test_dry_run_does_not_create_target_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "new-home"
            result = self.run_installer(
                home,
                "codex",
                "build-skill",
                "--dry-run",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((home / ".agents").exists())


if __name__ == "__main__":
    unittest.main()

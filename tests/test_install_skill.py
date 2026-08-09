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
    def run_installer(self, home: Path, platform: str, *extra: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(home)
        return subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                "building-skills",
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

    def test_codex_install_preserves_portable_frontmatter_and_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            result = self.run_installer(home, "codex")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            destination = home / ".agents" / "skills" / "building-skills"
            skill_md = destination.joinpath("SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("disable-model-invocation:", skill_md)
            self.assertTrue(destination.joinpath("agents", "openai.yaml").is_file())
            self.assertIn(
                "allow_implicit_invocation: false",
                destination.joinpath("agents", "openai.yaml").read_text(encoding="utf-8"),
            )

    def test_claude_install_injects_manual_only_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            result = self.run_installer(home, "claude")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            destination = home / ".claude" / "skills" / "building-skills"
            skill_md = destination.joinpath("SKILL.md").read_text(encoding="utf-8")
            self.assertIn("disable-model-invocation: true", skill_md)
            self.assertFalse(destination.joinpath("agents").exists())

            second = self.run_installer(home, "claude")
            self.assertEqual(second.returncode, 1)
            self.assertIn("--force", second.stderr)

            forced = self.run_installer(home, "claude", "--force")
            self.assertEqual(forced.returncode, 0, forced.stdout + forced.stderr)

    def test_dry_run_does_not_create_target_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "new-home"
            result = self.run_installer(home, "codex", "--dry-run")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(home.exists())


if __name__ == "__main__":
    unittest.main()

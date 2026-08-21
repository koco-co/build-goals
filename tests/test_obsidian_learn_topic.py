from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "obsidian-learn-topic"


class ObsidianLearnTopicIntegrationTests(unittest.TestCase):
    def run_skill_test(self, script: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / script)],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_global_skill_identity_and_invocation_are_namespaced(self) -> None:
        skill = SKILL_ROOT.joinpath("SKILL.md").read_text(encoding="utf-8")
        adapter = SKILL_ROOT.joinpath("agents", "openai.yaml").read_text(
            encoding="utf-8"
        )

        self.assertRegex(skill, r"(?m)^name:\s*obsidian-learn-topic\s*$")
        self.assertIn('version: "2.0.0"', skill)
        self.assertNotIn("disable-model-invocation:", skill)
        self.assertIn("allow_implicit_invocation: true", adapter)
        self.assertIn("$obsidian-learn-topic", adapter)

        invocation_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL_ROOT.rglob("*.md")
        )
        self.assertNotRegex(invocation_text, r"(?<!obsidian-)\$learn-topic\b")
        self.assertNotIn("Claude: /learn-topic", invocation_text)
        self.assertNotIn("`/learn-topic", invocation_text)

        readme = REPO_ROOT.joinpath("README.md").read_text(encoding="utf-8")
        self.assertIn("$build-goals:obsidian-learn-topic", readme)
        self.assertIn("/build-goals:obsidian-learn-topic", readme)

    def test_plugin_release_and_dsh_bundle_include_the_new_skill(self) -> None:
        versions = {
            json.loads(path.read_text(encoding="utf-8"))["version"]
            for path in (
                REPO_ROOT / ".claude-plugin" / "plugin.json",
                REPO_ROOT / ".codex-plugin" / "plugin.json",
                REPO_ROOT / "packages" / "dsh-build-goals" / "package.json",
            )
        }
        marketplace = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        versions.add(marketplace["plugins"][0]["version"])
        self.assertEqual(versions, {"2.2.0"})

        generated = (
            REPO_ROOT / "packages" / "dsh-build-goals" / "lib" / "skills.generated.js"
        ).read_text(encoding="utf-8")
        self.assertIn('"name": "obsidian-learn-topic"', generated)
        self.assertTrue(
            REPO_ROOT.joinpath(
                "packages",
                "dsh-build-goals",
                "assets",
                "skills",
                "obsidian-learn-topic",
                "SKILL.md",
            ).is_file()
        )

    def test_public_skill_has_no_generated_or_machine_private_artifacts(self) -> None:
        artifacts = [
            path.relative_to(SKILL_ROOT).as_posix()
            for path in SKILL_ROOT.rglob("*")
            if path.name in {".DS_Store", "__pycache__"} or path.suffix == ".pyc"
        ]
        private_paths = []
        for path in SKILL_ROOT.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".json", ".yaml", ".py", ".base"}:
                if re.search(r"/Users/[^/]+/", path.read_text(encoding="utf-8")):
                    private_paths.append(path.relative_to(SKILL_ROOT).as_posix())
        self.assertEqual(artifacts, [])
        self.assertEqual(private_paths, [])

    @unittest.skipUnless(
        sys.version_info >= (3, 10), "obsidian-learn-topic requires Python 3.10+"
    )
    def test_portable_skill_contract_and_drivers_pass(self) -> None:
        for script in (
            "test_skill_contract.py",
            "test_content_architecture.py",
            "test_roadmap_cli.py",
            "test_repository_cli.py",
        ):
            with self.subTest(script=script):
                result = self.run_skill_test(script)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(
        sys.version_info >= (3, 10) and platform.system() == "Darwin",
        "code exercise execution requires Python 3.10+ and macOS sandbox-exec",
    )
    def test_macos_code_exercise_driver_passes(self) -> None:
        result = self.run_skill_test("test_exercise_cli.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

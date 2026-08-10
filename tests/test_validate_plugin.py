from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "skills" / "build-plugin" / "scripts" / "validate_plugin.py"

VALID_BODY = """
# Outcome

完成目标。

## Routing

- 显式调用。

## Steps

1. 执行并验证。

## Delivery

- 输出结果。

## Guardrails

- 保护数据。

## References

- 无附加文件。
"""


class ValidatePluginTests(unittest.TestCase):
    def run_validator(
        self,
        plugin_dir: Path,
        platform: str = "dual",
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                str(plugin_dir),
                "--platform",
                platform,
            ],
            check=False,
            text=True,
            capture_output=True,
        )

    def write_fixture(self, root: Path) -> Path:
        plugin = root / "fixture-plugin"
        skill = plugin / "skills" / "fixture-skill"
        skill.mkdir(parents=True)
        skill.joinpath("SKILL.md").write_text(
            (
                "---\n"
                "name: fixture-skill\n"
                "description: 显式调用的测试 Skill。\n"
                "disable-model-invocation: true\n"
                "---\n\n"
                f"{textwrap.dedent(VALID_BODY).strip()}\n"
            ),
            encoding="utf-8",
        )
        adapter = skill / "agents" / "openai.yaml"
        adapter.parent.mkdir()
        adapter.write_text(
            "policy:\n  allow_implicit_invocation: false\n",
            encoding="utf-8",
        )

        common = {
            "name": "fixture-plugin",
            "version": "1.0.0",
            "description": "Fixture plugin",
            "skills": "./skills/",
        }
        for directory in (".codex-plugin", ".claude-plugin"):
            manifest = plugin / directory / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps(common, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return plugin

    def test_repository_plugin_passes(self) -> None:
        result = self.run_validator(REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("skills/build-skill", result.stdout)
        self.assertIn("skills/build-plugin", result.stdout)
        self.assertIn("skills/build-prd", result.stdout)
        self.assertIn("skills/shape-idea", result.stdout)
        self.assertIn("skills/handoff", result.stdout)

    def test_dual_version_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = self.write_fixture(Path(temp))
            claude = plugin / ".claude-plugin" / "plugin.json"
            data = json.loads(claude.read_text(encoding="utf-8"))
            data["version"] = "2.0.0"
            claude.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            result = self.run_validator(plugin)
            self.assertEqual(result.returncode, 1)
            self.assertIn("DUAL_VERSION_MISMATCH", result.stdout)

    def test_manifest_path_escape_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = self.write_fixture(Path(temp))
            codex = plugin / ".codex-plugin" / "plugin.json"
            data = json.loads(codex.read_text(encoding="utf-8"))
            data["skills"] = "./../skills/"
            codex.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            result = self.run_validator(plugin)
            self.assertEqual(result.returncode, 1)
            self.assertIn("COMPONENT_PATH_TRAVERSAL", result.stdout)

    def test_plugin_symlink_outside_root_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            plugin = self.write_fixture(base)
            outside = base / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            link = plugin / "skills" / "fixture-skill" / "rules" / "outside.md"
            link.parent.mkdir()
            link.symlink_to(os.path.relpath(outside, link.parent))
            result = self.run_validator(plugin)
            self.assertEqual(result.returncode, 1)
            self.assertIn("SYMLINK_OUTSIDE_PLUGIN", result.stdout)


if __name__ == "__main__":
    unittest.main()

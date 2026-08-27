from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_VALIDATOR = REPO_ROOT / "skills" / "build-skill" / "scripts" / "validate_skill.py"
PLUGIN_VALIDATOR = REPO_ROOT / "skills" / "build-plugin" / "scripts" / "validate_plugin.py"

VALID_BODY = """# Outcome

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


class StrictStatusTests(unittest.TestCase):
    def test_skill_strict_warning_reports_json_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill = Path(temp) / "warning-skill"
            skill.mkdir()
            skill.joinpath("SKILL.md").write_text(
                "---\n"
                "name: warning-skill\n"
                "description: strict status fixture\n"
                "compatibility: 当前适配 Claude Code 与 Codex。\n"
                "---\n\n"
                + textwrap.dedent(VALID_BODY).strip()
                + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SKILL_VALIDATOR), str(skill), "--strict", "--json"],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "fail")
            self.assertTrue(payload["strict"])
            self.assertGreater(payload["warning_count"], 0)

    def test_plugin_strict_warning_reports_json_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = Path(temp) / "fixture-plugin"
            (plugin / "skills").mkdir(parents=True)
            common = {
                "name": "fixture-plugin",
                "version": "1.0.0",
                "description": "fixture",
                "skills": "./skills/",
            }
            for directory in (".claude-plugin", ".codex-plugin"):
                path = plugin / directory / "plugin.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(common) + "\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PLUGIN_VALIDATOR),
                    str(plugin),
                    "--platform",
                    "dual",
                    "--strict",
                    "--json",
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "fail")
            self.assertTrue(payload["strict"])
            self.assertGreater(payload["warning_count"], 0)

    def test_claude_marketplace_version_must_match_plugin_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = Path(temp) / "fixture-plugin"
            (plugin / "skills").mkdir(parents=True)
            common = {
                "name": "fixture-plugin",
                "version": "1.0.0",
                "description": "fixture",
                "skills": "./skills/",
            }
            for directory in (".claude-plugin", ".codex-plugin"):
                path = plugin / directory / "plugin.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(common) + "\n", encoding="utf-8")
            marketplace = plugin / ".claude-plugin" / "marketplace.json"
            marketplace.write_text(
                json.dumps(
                    {
                        "name": "fixture-plugin",
                        "owner": {"name": "fixture"},
                        "plugins": [
                            {
                                "name": "fixture-plugin",
                                "source": "./",
                                "description": "fixture",
                                "version": "9.9.9",
                                "author": {"name": "fixture"},
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(PLUGIN_VALIDATOR), str(plugin), "--platform", "dual"],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("CLAUDE_MARKETPLACE_VERSION_MISMATCH", result.stdout)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "skills" / "build-skill" / "scripts" / "validate_skill.py"

VALID_BODY = """
# Outcome

完成目标。

## Routing

- 路由输入。

## Steps

1. 执行并验证。

## Delivery

- 输出结果。

## Guardrails

- 保护用户数据。

## References

- 无附加文件。
"""


class ValidateSkillTests(unittest.TestCase):
    def run_validator(
        self,
        skill_dir: Path,
        profile: str = "portable",
        plugin_root: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(VALIDATOR),
            str(skill_dir),
            "--profile",
            profile,
        ]
        if plugin_root is not None:
            command.extend(["--plugin-root", str(plugin_root)])
        return subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
        )

    def write_skill(
        self,
        root: Path,
        name: str,
        frontmatter_extra: str = "",
    ) -> Path:
        skill_dir = root / name
        skill_dir.mkdir(parents=True)
        skill_dir.joinpath("SKILL.md").write_text(
            (
                "---\n"
                f"name: {name}\n"
                "description: 用于验证测试夹具，仅在测试中显式调用。\n"
                f"{frontmatter_extra}"
                "---\n\n"
                f"{textwrap.dedent(VALID_BODY).strip()}\n"
            ),
            encoding="utf-8",
        )
        return skill_dir

    def add_codex_adapter(self, skill_dir: Path, implicit: str = "false") -> None:
        adapter = skill_dir / "agents" / "openai.yaml"
        adapter.parent.mkdir(parents=True)
        adapter.write_text(
            (
                "interface:\n"
                '  display_name: "Fixture"\n'
                "policy:\n"
                f"  allow_implicit_invocation: {implicit}\n"
            ),
            encoding="utf-8",
        )

    def write_plugin_manifests(self, root: Path) -> None:
        for directory in (".claude-plugin", ".codex-plugin"):
            manifest = root / directory / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                '{"name":"fixture-plugin","version":"1.0.0",'
                '"description":"fixture","skills":"./skills/"}\n',
                encoding="utf-8",
            )

    def test_valid_portable_skill_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(Path(temp), "valid-skill")
            result = self.run_validator(skill_dir)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS", result.stdout)

    def test_broken_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(Path(temp), "broken-skill")
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(
                skill_md.read_text(encoding="utf-8").replace(
                    "- 无附加文件。",
                    "- 完整读取 `workflows/missing.md`。",
                ),
                encoding="utf-8",
            )
            result = self.run_validator(skill_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("REF_NOT_FOUND", result.stdout)

    def test_claude_extension_is_profile_specific(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(
                Path(temp),
                "manual-skill",
                "disable-model-invocation: true\n",
            )
            self.add_codex_adapter(skill_dir)
            portable = self.run_validator(skill_dir, "portable")
            codex = self.run_validator(skill_dir, "codex")
            claude = self.run_validator(skill_dir, "claude")
            dual = self.run_validator(skill_dir, "dual")
            self.assertEqual(portable.returncode, 1)
            self.assertIn("FRONTMATTER_KEY", portable.stdout)
            self.assertEqual(codex.returncode, 1)
            self.assertIn("FRONTMATTER_KEY", codex.stdout)
            self.assertEqual(claude.returncode, 0, claude.stdout + claude.stderr)
            self.assertEqual(dual.returncode, 0, dual.stdout + dual.stderr)

    def test_dual_manual_policy_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(
                Path(temp),
                "manual-skill",
                "disable-model-invocation: true\n",
            )
            self.add_codex_adapter(skill_dir, "true")
            result = self.run_validator(skill_dir, "dual")
            self.assertEqual(result.returncode, 1)
            self.assertIn("MANUAL_POLICY_MISMATCH", result.stdout)

    def test_nested_frontmatter_is_tolerated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(
                Path(temp),
                "nested-skill",
                (
                    "hooks:\n"
                    "  PreToolUse:\n"
                    "    - matcher: Bash\n"
                    "      hooks:\n"
                    "        - type: command\n"
                    "          command: echo ok\n"
                ),
            )
            result = self.run_validator(skill_dir, "claude")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_prompt_name_must_end_with_agent_md(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(Path(temp), "prompt-skill")
            prompts = skill_dir / "prompts"
            prompts.mkdir()
            prompts.joinpath("reviewer.prompt.md").write_text(
                "review", encoding="utf-8"
            )
            result = self.run_validator(skill_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("AGENT_PROMPT_NAME", result.stdout)

    def test_internal_plugin_symlink_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin_root = Path(temp) / "fixture-plugin"
            self.write_plugin_manifests(plugin_root)
            shared = plugin_root / "skills" / "shared" / "rules" / "quality.md"
            shared.parent.mkdir(parents=True)
            shared.write_text("quality", encoding="utf-8")

            skill_dir = self.write_skill(
                plugin_root / "skills",
                "linked-skill",
            )
            rules = skill_dir / "rules"
            rules.mkdir()
            (rules / "quality.md").symlink_to("../../shared/rules/quality.md")
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(
                skill_md.read_text(encoding="utf-8").replace(
                    "- 无附加文件。",
                    "- 读取 `rules/quality.md`。",
                ),
                encoding="utf-8",
            )

            result = self.run_validator(skill_dir, "portable", plugin_root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_symlink_outside_plugin_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            plugin_root = base / "fixture-plugin"
            self.write_plugin_manifests(plugin_root)
            outside = base / "outside.md"
            outside.write_text("outside", encoding="utf-8")

            skill_dir = self.write_skill(plugin_root / "skills", "linked-skill")
            rules = skill_dir / "rules"
            rules.mkdir()
            (rules / "outside.md").symlink_to(os.path.relpath(outside, rules))

            result = self.run_validator(skill_dir, "portable", plugin_root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("SYMLINK_OUTSIDE_PLUGIN", result.stdout)

    def test_handoff_requires_copyable_next_agent_prompt(self) -> None:
        skill_md = REPO_ROOT.joinpath("skills", "handoff", "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("给下一个 Agent 的提示词", skill_md)
        self.assertIn("真实文件路径", skill_md)
        self.assertIn("可直接复制", skill_md)
        self.assertIn(
            "请读取 `<真实文件路径>` 并继续完成其中记录的任务；"
            "严格遵循文档中的目标、约束、已确认决策和后续步骤。",
            skill_md,
        )
        self.assertIn(
            "请使用 `$skill-name`，读取 `<真实文件路径>` 并继续完成其中记录的任务；"
            "严格遵循文档中的目标、约束、已确认决策和后续步骤。",
            skill_md,
        )


if __name__ == "__main__":
    unittest.main()

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
        strict: bool = False,
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
        if strict:
            command.append("--strict")
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

    def test_empty_compatibility_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(
                Path(temp),
                "empty-compatibility",
                "compatibility:\n",
            )
            result = self.run_validator(skill_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("COMPATIBILITY_EMPTY", result.stdout)

    def test_temporal_compatibility_claim_warns_and_fails_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(
                Path(temp),
                "generic-compatibility",
                "compatibility: 当前适配 Claude Code 与 Codex。\n",
            )
            normal = self.run_validator(skill_dir)
            strict = self.run_validator(skill_dir, strict=True)
            self.assertEqual(normal.returncode, 0, normal.stdout + normal.stderr)
            self.assertIn("COMPATIBILITY_TEMPORAL", normal.stdout)
            self.assertEqual(strict.returncode, 1)
            self.assertIn("COMPATIBILITY_TEMPORAL", strict.stdout)

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

    def test_shipped_user_only_skills_do_not_repeat_invocation_policy(self) -> None:
        redundant_phrases = (
            "用户明确调用",
            "普通请求不得自动触发",
            "普通问答、评审或实现请求不得自动触发",
            "无法确认是否为显式调用",
            "显式调用只授权",
        )

        for skill_md in sorted(REPO_ROOT.glob("skills/*/SKILL.md")):
            text = skill_md.read_text(encoding="utf-8")
            self.assertIn("disable-model-invocation: true", text)
            for phrase in redundant_phrases:
                with self.subTest(skill=skill_md.parent.name, phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_build_skill_defines_conditional_invocation_copy_rules(self) -> None:
        quality = REPO_ROOT.joinpath(
            "skills", "build-skill", "rules", "quality-standard.md"
        ).read_text(encoding="utf-8")

        self.assertIn("仅限用户调用的 Skill", quality)
        self.assertIn("不在正文重复说明调用权限", quality)
        self.assertIn("允许模型调用的 Skill", quality)
        self.assertIn("跨平台 `description`", quality)
        self.assertIn("`when_to_use`", quality)
        self.assertIn("触发条件、排除条件", quality)

    def test_build_skill_defines_frontmatter_decision_matrix(self) -> None:
        skill_root = REPO_ROOT / "skills" / "build-skill"
        frontmatter = skill_root.joinpath("rules", "frontmatter.md").read_text(
            encoding="utf-8"
        )
        template = skill_root.joinpath("templates", "skill.template.md").read_text(
            encoding="utf-8"
        )
        design = skill_root.joinpath(
            "templates", "design-proposal.template.md"
        ).read_text(encoding="utf-8")

        for required in (
            "字段决策矩阵",
            "disable-model-invocation",
            "user-invocable",
            "argument-hint",
            "arguments",
            "allowed-tools",
            "disallowed-tools",
            "paths",
            "context",
            "agent",
            "background",
            "model",
            "effort",
            "hooks",
            "shell",
            "compatibility",
            "agents/openai.yaml",
        ):
            with self.subTest(required=required):
                self.assertIn(required, frontmatter)
        self.assertNotIn("compatibility:", template.split("---", 2)[1])
        self.assertNotIn("metadata:", template.split("---", 2)[1])
        self.assertIn("Frontmatter 字段决策矩阵", design)

    def test_build_skill_separates_content_and_copy_review(self) -> None:
        skill_root = REPO_ROOT / "skills" / "build-skill"
        content_review = skill_root.joinpath(
            "checklists", "content-review.md"
        ).read_text(encoding="utf-8")
        copy_review = skill_root.joinpath(
            "checklists", "copy-review.md"
        ).read_text(encoding="utf-8")
        examples = skill_root.joinpath(
            "examples", "copy-review.example.md"
        ).read_text(encoding="utf-8")
        reviewer = skill_root.joinpath(
            "prompts", "reviewer.agent.md"
        ).read_text(encoding="utf-8")

        self.assertIn("正确性和完整性", content_review)
        self.assertIn("措辞润色不属于本清单", content_review)
        self.assertNotIn("## 表达质量", content_review)
        self.assertIn("自然、清楚、简洁", copy_review)
        self.assertIn("不得改变", copy_review)
        self.assertGreaterEqual(examples.count("## 样本"), 6)
        self.assertIn("内容审查结果", reviewer)
        self.assertIn("文案审查结果", reviewer)
        self.assertIn("只审查，不修改", reviewer)

    def test_shipped_compatibility_describes_only_hard_requirements(self) -> None:
        expected = {
            "build-agents-md": "需要 Python 3.9+ 运行内置校验脚本。",
            "build-plugin": "需要互联网访问和 Python 3.9+ 运行内置静态校验脚本。",
            "build-prd": "需要互联网访问和 Python 3.9+ 运行内置校验脚本。",
            "build-readme": "需要 Python 3.9+ 运行内置校验脚本。",
            "build-skill": "需要互联网访问和 Python 3.9+ 运行内置静态校验脚本。",
            "handoff": None,
            "shape-idea": None,
            "vibe-coding": "需要 Python 3.9+、Git、互联网访问及目标项目的构建与测试工具。",
        }
        prohibited = ("当前适配", "目前适配", "目前仅适配")

        for skill_md in sorted(REPO_ROOT.glob("skills/*/SKILL.md")):
            name = skill_md.parent.name
            frontmatter = skill_md.read_text(encoding="utf-8").split("---", 2)[1]
            for phrase in prohibited:
                with self.subTest(skill=name, phrase=phrase):
                    self.assertNotIn(phrase, frontmatter)
            compatibility = expected[name]
            with self.subTest(skill=name, expected=compatibility):
                if compatibility is None:
                    self.assertNotIn("compatibility:", frontmatter)
                else:
                    self.assertIn(f"compatibility: {compatibility}", frontmatter)

    def test_behavior_changed_skill_versions_are_updated(self) -> None:
        expected = {
            "build-agents-md": 'version: "1.2.0"',
            "build-plugin": 'version: "1.3.0"',
            "build-prd": 'version: "1.0.1"',
            "build-readme": 'version: "1.0.1"',
            "build-skill": 'version: "1.5.0"',
            "handoff": 'version: "1.1.1"',
            "shape-idea": 'version: "1.0.1"',
            "vibe-coding": 'version: "1.2.0"',
        }

        for name, version_line in expected.items():
            with self.subTest(skill=name):
                text = REPO_ROOT.joinpath("skills", name, "SKILL.md").read_text(
                    encoding="utf-8"
                )
                self.assertIn(version_line, text)

    def test_vibe_coding_defines_companion_skill_lifecycle(self) -> None:
        skill_root = REPO_ROOT / "skills" / "vibe-coding"
        contract = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                skill_root / "SKILL.md",
                skill_root / "rules" / "companion-skills.md",
                skill_root / "rules" / "orchestration-contract.md",
            )
        )

        for name in (
            "shape-idea",
            "build-prd",
            "build-agents-md",
            "build-skill",
            "build-plugin",
            "build-readme",
            "handoff",
        ):
            with self.subTest(skill=name):
                self.assertIn(name, contract)
                row = next(
                    line
                    for line in contract.splitlines()
                    if line.startswith(f"| `{name}` |")
                )
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                self.assertEqual(len(cells), 6)
                self.assertTrue(all(cells))
        for required in (
            "触发证据",
            "调用阶段",
            "是否阻断",
            "恢复条件",
            "可直接复制",
            "两个全局决策门禁",
            "按需产物确认",
            "功能开发前",
            "已证实",
            "纯文案",
            "暂停",
        ):
            with self.subTest(required=required):
                self.assertIn(required, contract)

    def test_build_agents_md_defines_nested_orchestration_contract(self) -> None:
        skill_root = REPO_ROOT / "skills" / "build-agents-md"
        contract = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                skill_root / "SKILL.md",
                skill_root / "workflows" / "§05-delivery.md",
            )
        )

        self.assertIn("上层总控", contract)
        self.assertIn("不重复询问", contract)
        self.assertIn("确认依据", contract)
        self.assertIn("恢复条件", contract)

    def test_stateful_build_skills_define_independent_and_controlled_delivery(self) -> None:
        for name, workflow in (
            ("build-agents-md", "§05-delivery.md"),
            ("build-skill", "§06-delivery.md"),
            ("build-plugin", "§07-delivery.md"),
        ):
            with self.subTest(skill=name):
                root = REPO_ROOT / "skills" / name
                contract = "\n".join(
                    path.read_text(encoding="utf-8")
                    for path in (root / "SKILL.md", root / "workflows" / workflow)
                )
                self.assertIn("独立调用", contract)
                self.assertIn("受控调用", contract)
                self.assertIn("不重复询问", contract)
                self.assertIn("上层总控", contract)
                self.assertIn("确认依据", contract)
                self.assertIn("验证", contract)
                self.assertIn("未验证", contract)
                self.assertIn("恢复条件", contract)


if __name__ == "__main__":
    unittest.main()

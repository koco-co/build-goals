from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class UiInteractionContractTests(unittest.TestCase):
    def test_obsidian_learning_skill_is_completely_removed(self) -> None:
        self.assertFalse(REPO_ROOT.joinpath("skills", "obsidian-learn-topic").exists())
        self.assertFalse(
            REPO_ROOT.joinpath("tests", "test_obsidian_learn_topic.py").exists()
        )

        public_files = (
            REPO_ROOT / "README.md",
            REPO_ROOT / ".claude-plugin" / "plugin.json",
            REPO_ROOT / ".claude-plugin" / "marketplace.json",
            REPO_ROOT / ".codex-plugin" / "plugin.json",
        )
        for path in public_files:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("obsidian-learn-topic", text)
                self.assertNotIn("technical-learning", text)
                self.assertNotIn("technical learning", text.lower())

    def test_clarify_idea_keeps_its_own_ui_preview_resources(self) -> None:
        clarify = REPO_ROOT.joinpath("skills", "clarify-idea", "SKILL.md").read_text(
            encoding="utf-8"
        )
        manifest = json.loads(
            REPO_ROOT.joinpath(".plugin-shared-files.json").read_text(encoding="utf-8")
        )
        self.assertIn("rules/ui-interaction-preview.md", clarify)
        self.assertIn("只保留在对话", clarify)
        sources = {item["source"] for item in manifest["mirrors"]}
        for relative in (
            "rules/ui-interaction-preview.md",
            "templates/ui-interaction-preview.template.md",
        ):
            self.assertTrue(
                REPO_ROOT.joinpath("skills", "clarify-idea", relative).is_file()
            )
            self.assertNotIn(f"skills/clarify-idea/{relative}", sources)

    def test_rule_covers_visible_and_invisible_state_changes(self) -> None:
        rule = REPO_ROOT.joinpath(
            "skills", "clarify-idea", "rules", "ui-interaction-preview.md"
        ).read_text(encoding="utf-8")
        template = REPO_ROOT.joinpath(
            "skills",
            "clarify-idea",
            "templates",
            "ui-interaction-preview.template.md",
        ).read_text(encoding="utf-8")

        for required in (
            "本次变更所影响的完整用户流程",
            "所有可达界面状态",
            "进入条件",
            "用户操作",
            "下一状态",
            "加载",
            "空数据",
            "失败",
            "权限受限",
            "判断分支",
            "数据更新",
            "失败恢复",
            "循环",
            "结束条件",
            "交互契约",
            "像素级",
        ):
            with self.subTest(required=required):
                self.assertIn(required, rule)
        self.assertIn("## 状态 1：", template)
        self.assertIn("```text", template)
        self.assertIn("## 状态流", template)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class UiInteractionContractTests(unittest.TestCase):
    def test_obsidian_learning_skill_is_completely_removed(self) -> None:
        self.assertFalse(REPO_ROOT.joinpath("skills", "obsidian-learn-topic").exists())
        self.assertFalse(REPO_ROOT.joinpath("tests", "test_obsidian_learn_topic.py").exists())

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

    def test_ui_preview_rule_and_template_are_shared_without_drift(self) -> None:
        manifest = json.loads(
            REPO_ROOT.joinpath(".plugin-shared-files.json").read_text(
                encoding="utf-8"
            )
        )
        mappings = {
            item["source"]: item["targets"] for item in manifest["mirrors"]
        }
        expected = {
            "skills/shape-idea/rules/ui-interaction-preview.md": [
                "skills/build-prd/rules/ui-interaction-preview.md",
                "skills/vibe-coding/rules/ui-interaction-preview.md",
            ],
            "skills/shape-idea/templates/ui-interaction-preview.template.md": [
                "skills/build-prd/templates/ui-interaction-preview.template.md",
                "skills/vibe-coding/templates/ui-interaction-preview.template.md",
            ],
        }
        for source, targets in expected.items():
            with self.subTest(source=source):
                self.assertEqual(mappings[source], targets)
                source_path = REPO_ROOT / source
                self.assertTrue(source_path.is_file())
                for target in targets:
                    target_path = REPO_ROOT / target
                    self.assertTrue(target_path.is_file())
                    self.assertFalse(target_path.is_symlink())
                    self.assertEqual(source_path.read_bytes(), target_path.read_bytes())

    def test_shared_rule_covers_visible_and_invisible_state_changes(self) -> None:
        rule = REPO_ROOT.joinpath(
            "skills", "shape-idea", "rules", "ui-interaction-preview.md"
        ).read_text(encoding="utf-8")
        template = REPO_ROOT.joinpath(
            "skills",
            "shape-idea",
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
        self.assertIn("## 不可见状态流", template)

    def test_three_skills_apply_the_contract_at_their_own_layer(self) -> None:
        shape = REPO_ROOT.joinpath("skills", "shape-idea", "SKILL.md").read_text(
            encoding="utf-8"
        )
        prd = REPO_ROOT.joinpath(
            "skills", "build-prd", "workflows", "§02-domain-confirmation.md"
        ).read_text(encoding="utf-8")
        prd_quality = REPO_ROOT.joinpath(
            "skills", "build-prd", "rules", "prd-quality-standard.md"
        ).read_text(encoding="utf-8")
        prd_template = REPO_ROOT.joinpath(
            "skills", "build-prd", "templates", "domain-requirements.template.md"
        ).read_text(encoding="utf-8")
        vibe_skill = REPO_ROOT.joinpath(
            "skills", "vibe-coding", "SKILL.md"
        ).read_text(encoding="utf-8")
        vibe_architecture = "\n".join(
            REPO_ROOT.joinpath("skills", "vibe-coding", "workflows", name).read_text(
                encoding="utf-8"
            )
            for name in (
                "§02-requirements-architecture.md",
                "§03-migration-audit.md",
            )
        )
        domain_architecture = REPO_ROOT.joinpath(
            "skills", "vibe-coding", "templates", "domain-architecture.template.md"
        ).read_text(encoding="utf-8")

        self.assertIn("rules/ui-interaction-preview.md", shape)
        self.assertIn("只保留在对话", shape)
        self.assertIn("rules/ui-interaction-preview.md", prd)
        self.assertIn("产品行为状态机", prd)
        self.assertIn("不记录内部类名、表结构或技术实现", prd_quality)
        self.assertIn("#### 可见界面状态与交互", prd_template)
        self.assertIn("#### 产品状态流", prd_template)
        self.assertIn("rules/ui-interaction-preview.md", vibe_skill)
        self.assertIn("rules/ui-interaction-preview.md", vibe_architecture)
        self.assertIn("## 产品交互契约引用", domain_architecture)
        self.assertIn("不得复制完整界面草图或产品状态机", domain_architecture)
        self.assertNotIn("## 可见界面状态与交互", domain_architecture)
        self.assertIn("## 技术状态流", domain_architecture)


if __name__ == "__main__":
    unittest.main()

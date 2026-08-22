from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class ContentQualityTests(unittest.TestCase):
    def test_knowledge_templates_start_from_problem_and_have_specific_shape(self) -> None:
        expectations = {
            "tutorial": ("真实问题", "贯穿案例", "完整结果", "如何验证结果", "失败表现"),
            "explanation": ("核心问题", "心智模型", "工作机制", "错误心智模型", "新场景分析"),
            "how-to": ("真实使用场景", "操作前检查", "操作步骤", "成功验证", "不适用场景"),
            "reference": ("要快速回答的问题", "速查索引", "参数与行为", "失败表现", "兼容性"),
        }
        for name, markers in expectations.items():
            template = read(f"templates/{name}.template.md")
            for marker in markers:
                self.assertIn(marker, template, f"{name}: {marker}")
            self.assertIn("evidence_profile:", template)

    def test_reader_notes_exclude_learning_ledger(self) -> None:
        forbidden = ("progress_status:", "mastery_status:", "作答与反馈", "内部评分", "覆盖矩阵")
        for name in ("tutorial", "explanation", "how-to", "reference"):
            template = read(f"templates/{name}.template.md")
            for marker in forbidden:
                self.assertNotIn(marker, template)

    def test_curriculum_example_has_one_outcome_profile_and_unique_ownership(self) -> None:
        plan = json.loads(read("examples/curriculum-plan.example.json"))
        owners = set()
        for unit in plan["units"]:
            self.assertTrue(unit["learning_outcome"].strip())
            self.assertTrue(unit["evidence_profile"].strip())
            for point in unit["knowledge_ownership"]:
                self.assertNotIn(point, owners)
                owners.add(point)

    def test_examples_are_substantive_not_user_route_migrations(self) -> None:
        for path in (ROOT / "examples").iterdir():
            if path.suffix != ".md":
                continue
            content = path.read_text(encoding="utf-8")
            self.assertGreaterEqual(len(content), 240, path.name)
            self.assertNotIn("迁移示例文件", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)

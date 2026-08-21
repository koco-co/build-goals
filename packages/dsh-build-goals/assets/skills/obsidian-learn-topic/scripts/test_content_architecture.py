#!/usr/bin/env python3
"""Contract tests for the three-layer learning-content architecture."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (SKILL_ROOT / relative).read_text(encoding="utf-8")


class ThreeLayerArchitectureTests(unittest.TestCase):
    def test_curriculum_content_and_evidence_have_distinct_templates(self) -> None:
        expected = {
            "templates/curriculum-map.template.md",
            "templates/curriculum-plan.template.json",
            "templates/tutorial.template.md",
            "templates/explanation.template.md",
            "templates/how-to.template.md",
            "templates/reference.template.md",
            "templates/learning-record.template.md",
        }
        self.assertEqual(
            sorted(path for path in expected if not (SKILL_ROOT / path).is_file()),
            [],
        )

        self.assertIn("record_type: curriculum-map", read("templates/curriculum-map.template.md"))
        for route_template in (
            "templates/curriculum-map.template.md",
            "templates/repository-curriculum-map.template.md",
        ):
            content = read(route_template)
            self.assertIn("<!-- learn-topic-curriculum:start -->", content)
            self.assertIn("{{CURRICULUM_PLAN_JSON}}", content)
        self.assertIn("record_type: learning-evidence", read("templates/learning-record.template.md"))
        for name, document_type in (
            ("tutorial", "教程"),
            ("explanation", "原理解释"),
            ("how-to", "操作指南"),
            ("reference", "参考资料"),
        ):
            template = read(f"templates/{name}.template.md")
            self.assertIn("record_type: knowledge-note", template)
            self.assertIn(f'document_type: "{document_type}"', template)

    def test_reader_facing_templates_do_not_contain_learning_ledger_sections(self) -> None:
        forbidden = (
            "## 本单元知识点清单",
            "覆盖矩阵",
            "## 提问与验收",
            "## 作答记录",
            "内部评定",
            "学习记录状态",
        )
        for name in ("tutorial", "explanation", "how-to", "reference"):
            template = read(f"templates/{name}.template.md")
            for marker in forbidden:
                self.assertNotIn(marker, template, f"{name}: {marker}")

    def test_each_document_type_has_a_distinct_semantic_shape(self) -> None:
        expected = {
            "tutorial": ("## 学习成果", "## 贯穿案例", "## 阶段检查", "## 独立练习"),
            "explanation": ("## 核心问题", "## 心智模型", "## 工作机制", "## 错误心智模型"),
            "how-to": ("## 适用条件", "## 操作步骤", "## 成功验证", "## 故障处理"),
            "reference": ("## 适用范围", "## 速查索引", "## 参数与行为", "## 兼容性"),
        }
        for name, headings in expected.items():
            template = read(f"templates/{name}.template.md")
            for heading in headings:
                self.assertIn(heading, template, f"{name}: {heading}")

    def test_curriculum_plan_fixture_has_unique_ownership_and_dependencies(self) -> None:
        plan = json.loads(read("examples/curriculum-plan.example.json"))
        units = plan["units"]
        unit_ids = [unit["unit_id"] for unit in units]
        self.assertEqual(len(unit_ids), len(set(unit_ids)))
        known = set(unit_ids)
        owners: dict[str, str] = {}
        for unit in units:
            self.assertIn(unit["document_type"], {"教程", "原理解释", "操作指南", "参考资料"})
            self.assertTrue(unit["learning_outcome"].strip())
            self.assertTrue(unit["assessment"].strip())
            self.assertTrue(set(unit["prerequisites"]).issubset(known))
            for point in unit["knowledge_ownership"]:
                self.assertNotIn(point, owners, f"duplicate ownership: {point}")
                owners[point] = unit["unit_id"]

    def test_anti_patterns_cover_all_confirmed_failure_modes(self) -> None:
        anti_patterns = read("examples/content-anti-patterns.example.md")
        for marker in (
            "正文混入问答流水账",
            "知识点重复归属",
            "前置依赖倒置",
            "只有目录没有验收成果",
        ):
            self.assertIn(marker, anti_patterns)

    def test_scaffold_persists_route_map_and_separate_learning_records(self) -> None:
        spec = json.loads(read("templates/scaffold-spec.template.json"))
        directory_roles = [item["role"] for item in spec["directories"]]
        self.assertEqual(directory_roles[-2:], ["records", "assets"])
        paths = [item["path"] for item in spec["notes"]]
        self.assertTrue(any(path.endswith("/§01-学习路线图.md") for path in paths))
        self.assertTrue(any("学习记录/§01-" in path for path in paths))
        self.assertIn("curriculum_plan_file", spec)
        note_plan = json.loads(read("templates/note-plan.template.json"))
        self.assertEqual(note_plan["content_contract"], "three-layer")
        self.assertIn("curriculum_plan_file", note_plan)
        self.assertIn("records_directory", note_plan)

    def test_skill_routes_to_type_specific_templates_and_separate_records(self) -> None:
        skill = read("SKILL.md")
        workflow = read("workflows/§04-learn-unit.md")
        for marker in (
            "课程路线层",
            "知识正文层",
            "学习证据层",
            "单项可验收成果",
        ):
            self.assertIn(marker, skill)
        for template in (
            "templates/tutorial.template.md",
            "templates/explanation.template.md",
            "templates/how-to.template.md",
            "templates/reference.template.md",
            "templates/learning-record.template.md",
        ):
            self.assertIn(template, workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)

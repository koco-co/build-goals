"""Document workflow contracts; these checks do not execute an LLM client."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "build-docs"
DOCUMENT_TEMPLATES = {
    "PRD.md": "prd",
    "ARCHITECTURE.md": "architecture",
    "ROADMAP.md": "roadmap",
    "DATA_MODEL.md": "data-model",
    "CODING_STANDARDS.md": "coding-standards",
    "TESTING_STRATEGY.md": "testing-strategy",
    "adr/": "adr",
    "GLOSSARY.md": "glossary",
    "AGENT_BRIEF.md": "agent-brief",
    "CHANGELOG.md": "changelog",
    "ENVIRONMENT_SETUP.md": "environment-setup",
    "RISKS_AND_KNOWN_ISSUES.md": "risks-and-known-issues",
}
DEFAULT_DOCUMENT_PATHS = {
    "AGENT_BRIEF.md": "docs/spec/AGENT_BRIEF.md",
    "PRD.md": "docs/spec/product/PRD.md",
    "ROADMAP.md": "docs/spec/product/ROADMAP.md",
    "GLOSSARY.md": "docs/spec/product/GLOSSARY.md",
    "ARCHITECTURE.md": "docs/spec/architecture/ARCHITECTURE.md",
    "DATA_MODEL.md": "docs/spec/architecture/DATA_MODEL.md",
    "adr/": "docs/spec/architecture/adr/",
    "CODING_STANDARDS.md": "docs/spec/engineering/CODING_STANDARDS.md",
    "TESTING_STRATEGY.md": "docs/spec/engineering/TESTING_STRATEGY.md",
    "ENVIRONMENT_SETUP.md": "docs/spec/engineering/ENVIRONMENT_SETUP.md",
    "CHANGELOG.md": "docs/spec/status/CHANGELOG.md",
    "RISKS_AND_KNOWN_ISSUES.md": "docs/spec/status/RISKS_AND_KNOWN_ISSUES.md",
}


class BuildDocsContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return SKILL_ROOT.joinpath(relative).read_text(encoding="utf-8")

    def test_routes_include_creation_extraction_and_update_but_exclude_small_tasks(self) -> None:
        entry = self.read("SKILL.md")
        for scenario in ("从零建立", "已有项目提取", "持续更新", "小问题", "小需求"):
            with self.subTest(scenario=scenario):
                self.assertIn(scenario, entry)
        self.assertIn("不修改产品代码", entry)

    def test_each_document_has_a_reachable_template(self) -> None:
        catalog = self.read("rules/documents.md")
        for document, template in DOCUMENT_TEMPLATES.items():
            with self.subTest(document=document):
                self.assertIn(f"`{document}`", catalog)
                relative = f"templates/{template}.template.md"
                self.assertIn(f"`{relative}`", catalog)
                self.assertTrue(self.read(relative).startswith("# "))

    def test_default_paths_match_the_confirmed_directory_structure(self) -> None:
        catalog = self.read("rules/documents.md")
        paths = dict(re.findall(r"^\| `([^`]+)` \| `(docs/[^`]+)` \|", catalog, re.M))
        self.assertEqual(paths, DEFAULT_DOCUMENT_PATHS)

    def test_brief_index_groups_match_document_roles(self) -> None:
        template = self.read("templates/agent-brief.template.md")
        rows = re.findall(
            r"^\| (product|architecture|engineering|status) \| [^|]*? ([A-Z_]+) \|",
            template,
            re.M,
        )
        expected = {
            (path.split("/")[2], "ADR" if document == "adr/" else document[:-3])
            for document, path in DEFAULT_DOCUMENT_PATHS.items()
            if document != "AGENT_BRIEF.md"
        }
        self.assertEqual(len(rows), len(expected))
        self.assertEqual(set(rows), expected)
        self.assertIn("实际位置", template)

    def test_existing_project_extraction_distinguishes_evidence_from_decisions(self) -> None:
        research = self.read("workflows/§01-research.md")
        for source in ("代码", "配置", "测试", "Git", "已有文档"):
            with self.subTest(source=source):
                self.assertIn(source, research)
        for distinction in ("已实现", "已验证", "待确认", "历史理由", "不编造"):
            with self.subTest(distinction=distinction):
                self.assertIn(distinction, research)
        self.assertIn("现状与目标", research)

    def test_planning_and_each_batch_require_confirmation(self) -> None:
        plan = self.read("workflows/§02-plan.md")
        authoring = self.read("workflows/§03-authoring.md")
        self.assertIn("整体规划", plan)
        self.assertIn("确认前不写", plan)
        self.assertIn("每批", authoring)
        self.assertIn("完整内容或 Diff", authoring)
        self.assertIn("确认后写入", authoring)
        self.assertIn("保留", authoring)
        self.assertIn("未提交修改", authoring)

    def test_existing_paths_and_single_line_agent_entry_are_preserved(self) -> None:
        plan = self.read("workflows/§02-plan.md")
        authoring = self.read("workflows/§03-authoring.md")
        self.assertIn("等价文档", plan)
        self.assertIn("沿用现有路径", plan)
        self.assertIn("迁移另行确认", plan)
        self.assertIn("项目状态与开发文档入口：@docs/spec/AGENT_BRIEF.md", authoring)
        self.assertIn("相对路径", authoring)
        self.assertIn("一行", authoring)
        self.assertIn("不整体重写", authoring)

    def test_templates_cover_contracts_and_actual_completion_evidence(self) -> None:
        required = {
            "prd": ("输入", "输出", "状态", "验收"),
            "architecture": ("目录", "依赖", "禁止", "ADR"),
            "roadmap": ("依赖", "Definition of Done", "证据"),
            "data-model": ("字段", "关系", "Schema", "ID"),
            "coding-standards": ("命名", "错误处理", "反模式"),
            "testing-strategy": ("单元", "集成", "端到端", "覆盖", "重试"),
            "adr": ("日期", "状态", "备选", "理由"),
            "glossary": ("术语", "ID"),
            "agent-brief": ("当前状态", "已完成", "下一步", "文档索引"),
            "changelog": ("日期", "已实施", "证据"),
            "environment-setup": ("前置条件", "安装", "Lint", "测试", "运行"),
            "risks-and-known-issues": ("限制", "技术债", "待确认"),
        }
        for template, terms in required.items():
            text = self.read(f"templates/{template}.template.md")
            for term in terms:
                with self.subTest(template=template, term=term):
                    self.assertIn(term, text)

    def test_update_checks_dependencies_and_brief_without_inventing_history(self) -> None:
        authoring = self.read("workflows/§03-authoring.md")
        validation = self.read("workflows/§04-validation.md")
        self.assertIn("受影响", authoring)
        self.assertIn("AGENT_BRIEF", authoring)
        self.assertIn("CHANGELOG", authoring)
        self.assertIn("检查结果", validation)
        self.assertIn("未验证", validation)

    def test_all_local_workflow_resources_are_self_contained(self) -> None:
        self.assertTrue(SKILL_ROOT.is_dir())
        pattern = re.compile(
            r"`((?:workflows|templates|rules|checklists)/[^`]+\.(?:md))`"
        )
        referenced = set()
        for source in SKILL_ROOT.rglob("*.md"):
            if source.parent.name == "templates":
                continue
            for relative in pattern.findall(source.read_text(encoding="utf-8")):
                with self.subTest(source=source.name, reference=relative):
                    self.assertTrue(SKILL_ROOT.joinpath(relative).is_file())
                    referenced.add(relative)
        for resource in SKILL_ROOT.rglob("*.md"):
            if resource.name != "SKILL.md":
                self.assertIn(resource.relative_to(SKILL_ROOT).as_posix(), referenced)


if __name__ == "__main__":
    unittest.main()

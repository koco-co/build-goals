#!/usr/bin/env python3
"""Focused structural and routing contract tests for obsidian-learn-topic."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_FILE = SKILL_ROOT / "SKILL.md"
REFERENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"((?:agents|checklists|examples|rules|scripts|templates|workflows)/"
    r"[A-Za-z0-9_.\-/§]+)"
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if line.startswith((" ", "\t")):
            continue
        if not separator:
            raise AssertionError(f"unsupported frontmatter line: {line}")
        values[key] = value.strip()
    return values


class LearnTopicSkillContractTests(unittest.TestCase):
    def test_frontmatter_has_only_supported_fields_and_precise_routing(self) -> None:
        values = frontmatter(read_text(SKILL_FILE))
        self.assertEqual(
            set(values), {"name", "description", "compatibility", "metadata"}
        )
        self.assertEqual(values["name"], "obsidian-learn-topic")
        self.assertIn('version: "1.0.0"', read_text(SKILL_FILE))
        description = values["description"]
        for marker in ("开始或继续系统学习", "复习", "维护学习路线", "模型直接调用"):
            self.assertIn(marker, description)
        for negative in ("一次性概念问答", "普通故障排查"):
            self.assertIn(negative, description)

    def test_core_sections_exist_in_required_order(self) -> None:
        text = read_text(SKILL_FILE)
        headings = [
            "# Outcome",
            "## Routing",
            "## Steps",
            "## Delivery",
            "## Guardrails",
            "## References",
        ]
        positions = [text.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))

    def test_one_shot_question_contract_and_example_are_present(self) -> None:
        skill = read_text(SKILL_FILE)
        example_path = SKILL_ROOT / "examples/one-shot-question.example.md"
        example = read_text(example_path)

        for marker in (
            "#### Question contract",
            "one-shot",
            "进度状态行",
            "场景",
            "问题",
            "提示",
            "三句以内反馈",
            "验证目标",
            "通过标准",
        ):
            self.assertIn(marker, skill)

        self.assertIn("examples/one-shot-question.example.md", skill)
        for marker in (
            "# One-shot 提问示例",
            "本单元知识点已验收",
            "### 场景",
            "### 问题",
            "### 提示",
            "## 内部评定",
            "ScopeMismatch",
            "admin_login",
        ):
            self.assertIn(marker, example)

    def test_question_contract_is_referenced_by_learning_and_review_flows(self) -> None:
        skill = read_text(SKILL_FILE)
        unit_workflow = read_text(SKILL_ROOT / "workflows/§04-learn-unit.md")
        review_workflow = read_text(SKILL_ROOT / "workflows/§05-review.md")
        lesson_template = read_text(SKILL_ROOT / "templates/lesson.template.md")
        review_template = read_text(SKILL_ROOT / "templates/review.template.md")

        for document in (unit_workflow, review_workflow, lesson_template, review_template):
            for marker in ("进度状态行", "场景", "问题", "提示"):
                self.assertIn(marker, document)

        for document in (lesson_template, review_template):
            self.assertIn("本单元知识点已验收", document)
            self.assertIn("{{QUESTION_STATUS}}", document)
            self.assertNotIn("回答格式", document)

        self.assertIn("Question contract", unit_workflow)
        self.assertIn("Question contract", review_workflow)
        self.assertIn("{{QUESTION_OBJECTIVE}}", lesson_template)
        self.assertIn("{{QUESTION_RESPONSE_FORMAT}}", lesson_template)
        self.assertIn("内部评定", lesson_template)
        self.assertIn("{{QUESTION_PASS_CRITERIA}}", review_template)
        self.assertIn("架构、职责、边界和用户流程", unit_workflow)
        self.assertIn("内部状态名、API", skill)

    def test_learning_record_transaction_is_explicit(self) -> None:
        skill = read_text(SKILL_FILE)
        record_contract = read_text(SKILL_ROOT / "rules/learning-record-contract.md")
        resume_workflow = read_text(SKILL_ROOT / "workflows/§03-resume.md")
        unit_workflow = read_text(SKILL_ROOT / "workflows/§04-learn-unit.md")
        review_workflow = read_text(SKILL_ROOT / "workflows/§05-review.md")
        lesson_template = read_text(SKILL_ROOT / "templates/lesson.template.md")
        for document in (skill, record_contract, resume_workflow, unit_workflow, review_workflow, lesson_template):
            for marker in ("knowledge_points_total", "knowledge_points_covered", "knowledge_points_pending"):
                self.assertIn(marker, document)
        for document in (skill, record_contract, resume_workflow, unit_workflow, review_workflow, lesson_template):
            self.assertIn("立即停止本轮", document)
        for document in (skill, record_contract, resume_workflow, unit_workflow, review_workflow):
            self.assertIn("compare-and-swap", document)
        self.assertIn("先把知识点、覆盖矩阵和一道待回答题写入并读回课程笔记", skill)
        self.assertIn("不得进行只存在于聊天里的教学", skill)
        self.assertIn("没有完成第 3 步时不得开始第 4 步", record_contract)
        self.assertIn("不得选择新的单元", resume_workflow)
        self.assertIn("本单元知识点清单", lesson_template)

    def test_routing_names_every_supported_branch_and_negative_boundary(self) -> None:
        text = read_text(SKILL_FILE)
        for path in (
            "workflows/§01-start.md",
            "workflows/§02-scaffold.md",
            "workflows/§03-resume.md",
            "workflows/§04-learn-unit.md",
            "workflows/§05-review.md",
            "workflows/§06-maintain.md",
            "workflows/§07-open-source.md",
            "workflows/§08-code-exercise.md",
        ):
            self.assertIn(f"`{path}`", text)
        self.assertIn("一次性概念解释或普通故障排查不建立路线", text)

    def test_all_markdown_resource_references_are_closed(self) -> None:
        missing: list[str] = []
        for document in sorted(SKILL_ROOT.rglob("*.md")):
            for relative in sorted(set(REFERENCE_RE.findall(read_text(document)))):
                if not (SKILL_ROOT / relative).exists():
                    missing.append(f"{document.relative_to(SKILL_ROOT)} -> {relative}")
        self.assertEqual(missing, [])

    def test_legacy_reference_bucket_is_absent(self) -> None:
        self.assertFalse((SKILL_ROOT / "references").exists())
        for document in SKILL_ROOT.rglob("*.md"):
            self.assertNotIn("references/", read_text(document), str(document))

    def test_skill_tree_contains_only_purposeful_resource_groups(self) -> None:
        expected = {
            "agents",
            "checklists",
            "examples",
            "rules",
            "scripts",
            "templates",
            "workflows",
        }
        actual = {path.name for path in SKILL_ROOT.iterdir() if path.is_dir()}
        self.assertEqual(actual, expected)
        for path in SKILL_ROOT.rglob("*"):
            if path.is_file():
                self.assertGreater(path.stat().st_size, 0, str(path))

    def test_workflow_and_template_names_follow_skill_architecture(self) -> None:
        workflows = sorted(path.name for path in (SKILL_ROOT / "workflows").glob("*.md"))
        numbers = []
        for name in workflows:
            match = re.fullmatch(r"§(\d{2})-[a-z0-9-]+\.md", name)
            self.assertIsNotNone(match, name)
            numbers.append(int(match.group(1)))
        self.assertEqual(numbers, list(range(1, len(workflows) + 1)))
        for template in (SKILL_ROOT / "templates").iterdir():
            self.assertIn(".template.", template.name, template.name)

    def test_generated_artifacts_are_absent(self) -> None:
        artifacts = [
            path.relative_to(SKILL_ROOT).as_posix()
            for path in SKILL_ROOT.rglob("*")
            if path.name == ".DS_Store" or path.name == "__pycache__" or path.suffix == ".pyc"
        ]
        self.assertEqual(artifacts, [])

    def test_codex_and_claude_allow_model_invocation(self) -> None:
        openai_yaml = read_text(SKILL_ROOT / "agents/openai.yaml")
        self.assertRegex(openai_yaml, r"(?m)^\s*allow_implicit_invocation:\s*true\s*$")
        self.assertIn("$obsidian-learn-topic", openai_yaml)
        self.assertNotIn("disable-model-invocation:", read_text(SKILL_FILE))

    def test_semantic_acceptance_covers_positive_negative_and_failure_cases(self) -> None:
        checklist = read_text(SKILL_ROOT / "checklists/semantic-acceptance.md")
        for case_id in ("LT-01", "LT-06", "LT-07", "LT-09", "LT-10", "LT-15"):
            self.assertIn(case_id, checklist)
        for case_id in ("LT-16", "LT-17", "LT-18", "LT-19", "LT-20", "LT-21"):
            self.assertIn(case_id, checklist)
        for case_id in ("LT-22", "LT-23", "LT-24", "LT-25", "LT-26", "LT-27", "LT-28", "LT-29", "LT-30"):
            self.assertIn(case_id, checklist)
        for marker in ("正向路由", "负向路由", "门禁与失败路径", "全新任务"):
            self.assertIn(marker, checklist)

    def test_examples_are_runtime_agnostic_and_cover_route_boundaries(self) -> None:
        examples = read_text(SKILL_ROOT / "examples/routing.example.md")
        for marker in ("宽泛语言主题", "多语言绑定框架", "硬前置缺失", "开源仓库", "普通代码型单元", "只说继续", "相似内容"):
            self.assertIn(marker, examples)
        self.assertIn("运行时必须重新调研", examples)

    def test_roadmap_base_naming_and_driver_commands_remain_compatible(self) -> None:
        skill = read_text(SKILL_FILE)
        driver = read_text(SKILL_ROOT / "scripts/roadmap_cli.py")
        self.assertIn("<主题路径段>-Roadmap.base", skill)
        for command in ("probe", "scaffold", "validate", "write-note", "renumber", "trash-validation"):
            self.assertRegex(
                driver,
                rf'subparsers\.add_parser\(\s*"{re.escape(command)}"',
                command,
            )
        repository_driver = read_text(SKILL_ROOT / "scripts/repository_cli.py")
        for command in ("audit", "prepare", "verify-patch", "upstream-check"):
            self.assertIn(f'"{command}"', repository_driver, command)
        exercise_driver = read_text(SKILL_ROOT / "scripts/exercise_cli.py")
        for command in ("scaffold", "authorize", "run", "add-variant"):
            self.assertIn(f'"{command}"', exercise_driver, command)

    def test_repository_branch_has_fixed_route_policy_and_assets(self) -> None:
        policy = read_text(SKILL_ROOT / "rules/repository-learning-policy.md")
        for stage in (
            "01-项目概述", "02-运行与测试基线", "03-架构与模块地图",
            "04-核心调用链", "05-测试与质量体系", "06-Issue与PR考古",
            "07-最小修复实践", "08-深入与拓展", "09-复习与贡献准备",
            "99-assets",
        ):
            self.assertIn(stage, policy)
        for marker in ("完整 Commit", "核心切片", "真实最小 Patch", "不 commit", "上游"):
            self.assertIn(marker, policy)
        for path in (
            "templates/repository-scaffold-spec.template.json",
            "templates/repository-prerequisites.template.md",
            "templates/repository-workspace-plan.template.json",
            "templates/repository-patch-evidence.template.md",
        ):
            self.assertTrue((SKILL_ROOT / path).is_file(), path)

    def test_skill_sources_do_not_embed_machine_private_absolute_paths(self) -> None:
        offenders: list[str] = []
        private_home_marker = "/" + "Users/"
        for path in SKILL_ROOT.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".json", ".yaml", ".py", ".base"}:
                if private_home_marker in read_text(path):
                    offenders.append(path.relative_to(SKILL_ROOT).as_posix())
        self.assertEqual(offenders, [])

    def test_code_exercise_branch_has_policy_workflow_templates_and_driver(self) -> None:
        for relative in (
            "rules/code-exercise-policy.md",
            "workflows/§08-code-exercise.md",
            "templates/code-exercise-manifest.template.json",
            "templates/code-exercise-evidence.template.json",
            "scripts/exercise_cli.py",
            "scripts/test_exercise_cli.py",
        ):
            self.assertTrue((SKILL_ROOT / relative).is_file(), relative)
        policy = read_text(SKILL_ROOT / "rules/code-exercise-policy.md")
        for marker in (
            "用户必须提供并最终确认",
            "一个必做核心练习包",
            "三级提示",
            "不使用隐藏测试",
            "attempt-NN.json",
            "不自动 `git init`",
            "模型代写后的通过结果不能单独作为用户掌握证据",
        ):
            self.assertIn(marker, policy)
        skill = read_text(SKILL_FILE)
        unit_workflow = read_text(SKILL_ROOT / "workflows/§04-learn-unit.md")
        code_workflow = read_text(SKILL_ROOT / "workflows/§08-code-exercise.md")
        for text in (skill, unit_workflow, code_workflow):
            self.assertIn("roadmap_kind", text)
            self.assertIn("repository", text)

    def test_code_exercise_template_keeps_external_root_unresolved_and_public(self) -> None:
        template = json.loads(read_text(SKILL_ROOT / "templates/code-exercise-manifest.template.json"))
        self.assertEqual(template["workspace_root"], "{{USER_PROVIDED_CONFIRMED_EXISTING_EXTERNAL_ROOT}}")
        self.assertRegex(template["exercise_directory"], r"^01-")
        self.assertTrue(all(command["visible"] for command in template["commands"]))
        self.assertTrue(any(command["required"] for command in template["commands"]))
        self.assertEqual([hint["level"] for hint in template["exercise"]["hints"]], [1, 2, 3])
        self.assertNotIn("solution", json.dumps(template).casefold())


if __name__ == "__main__":
    unittest.main(verbosity=2)

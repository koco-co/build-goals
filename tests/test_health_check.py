from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "health-check"


class HealthCheckContractTests(unittest.TestCase):
    def test_skill_has_the_confirmed_plugin_only_structure(self) -> None:
        expected = {
            "SKILL.md",
            "agents/openai.yaml",
            "checklists/semantic-acceptance.md",
            "rules/domain-contract.md",
            "templates/health-check-report.template.md",
            "workflows/§01-inspection.md",
            "workflows/§02-remediation.md",
        }
        actual = {
            str(path.relative_to(SKILL_ROOT))
            for path in SKILL_ROOT.rglob("*")
            if path.is_file()
        }

        self.assertEqual(actual, expected)
        self.assertFalse(SKILL_ROOT.joinpath("scripts").exists())
        self.assertFalse(SKILL_ROOT.joinpath("prompts").exists())

    def test_skill_reports_once_then_repairs_after_confirmation(self) -> None:
        contract = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                SKILL_ROOT / "SKILL.md",
                SKILL_ROOT / "rules" / "domain-contract.md",
                SKILL_ROOT / "workflows" / "§01-inspection.md",
                SKILL_ROOT / "workflows" / "§02-remediation.md",
                SKILL_ROOT / "templates" / "health-check-report.template.md",
            )
        )

        for required in (
            "只读",
            "一次性报告",
            "证据",
            "修复方案",
            "影响文件",
            "验证方式",
            "用户确认",
            "重新运行健康检查",
            "未发现问题",
            "发现的问题",
        ):
            with self.subTest(required=required):
                self.assertIn(required, contract)

        for prohibited in ("统一评级", "健康等级", "严重级别", "severity", "P0"):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, contract)

    def test_domain_contract_covers_only_the_confirmed_four_domains(self) -> None:
        contract = SKILL_ROOT.joinpath("rules", "domain-contract.md").read_text(
            encoding="utf-8"
        )
        for domain in (
            "Agent Skill",
            "Plugin",
            "README",
            "AGENTS.md",
            "CLAUDE.md",
        ):
            with self.subTest(domain=domain):
                self.assertIn(domain, contract)
        self.assertIn("四个项目规范领域", contract)
        self.assertNotIn("PRD", contract)
        for excluded in (
            "代码质量",
            "安全",
            "依赖",
            "测试覆盖率",
            "CI",
            "性能",
        ):
            with self.subTest(excluded=excluded):
                self.assertIn(excluded, contract)

    def test_child_skills_define_the_health_check_controlled_branch(self) -> None:
        for name in (
            "build-agents-md",
            "build-plugin",
            "build-readme",
            "build-skill",
        ):
            with self.subTest(skill=name):
                text = REPO_ROOT.joinpath("skills", name, "SKILL.md").read_text(
                    encoding="utf-8"
                )
                self.assertIn("由 `health-check` 调用", text)
                self.assertIn("审查阶段保持只读", text)
                self.assertIn("上层取得修复确认后", text)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "build-agents-md"
VALIDATOR = SKILL_DIR / "scripts" / "validate_agents_md.py"


class ValidateAgentsMdTests(unittest.TestCase):
    def run_validator(
        self,
        project_root: Path,
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(project_root), *extra],
            check=False,
            text=True,
            capture_output=True,
        )

    def write_instruction_pair(
        self,
        directory: Path,
        body: str | None = None,
    ) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        directory.joinpath("AGENTS.md").write_text(
            body
            or (
                "# Agent Guide\n\n"
                "## Project\n\n"
                "This repository contains a tested fixture.\n\n"
                "## Commands\n\n"
                "- Run `python3 -m unittest`.\n"
            ),
            encoding="utf-8",
        )
        directory.joinpath("CLAUDE.md").write_bytes(b"@AGENTS.md")

    def test_valid_root_and_nested_instructions_pass_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            project.joinpath("docs").mkdir()
            project.joinpath("docs", "development.md").write_text(
                "# Development\n", encoding="utf-8"
            )
            self.write_instruction_pair(
                project,
                (
                    "# Agent Guide\n\n"
                    "## Project\n\n"
                    "Use [development guidance](docs/development.md).\n\n"
                    "## Commands\n\n"
                    "- Run `python3 -m unittest`.\n"
                ),
            )
            self.write_instruction_pair(project / "packages" / "api")

            result = self.run_validator(project, "--strict")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS", result.stdout)
            self.assertIn("AGENTS.md files: 2", result.stdout)

    def test_missing_root_agents_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_validator(Path(temp), "--strict")

            self.assertEqual(result.returncode, 1)
            self.assertIn("AGENTS_NOT_FOUND", result.stdout)

    def test_copied_claude_body_fails_import_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            project.joinpath("AGENTS.md").write_text(
                "# Agent Guide\n", encoding="utf-8"
            )
            project.joinpath("CLAUDE.md").write_text(
                "# Agent Guide\n", encoding="utf-8"
            )

            result = self.run_validator(project, "--strict")

            self.assertEqual(result.returncode, 1)
            self.assertIn("CLAUDE_IMPORT_CONTENT", result.stdout)

    def test_claude_symlink_fails_regular_file_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            project.joinpath("AGENTS.md").write_text(
                "# Agent Guide\n", encoding="utf-8"
            )
            project.joinpath("CLAUDE.md").symlink_to(project / "AGENTS.md")

            result = self.run_validator(project, "--strict")

            self.assertEqual(result.returncode, 1)
            self.assertIn("CLAUDE_REGULAR_FILE_REQUIRED", result.stdout)

    def test_exact_claude_import_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            self.write_instruction_pair(project)

            result = self.run_validator(project, "--strict")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_claude_import_accepts_standard_trailing_newline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            self.write_instruction_pair(project)
            project.joinpath("CLAUDE.md").write_bytes(b"@AGENTS.md\n")

            result = self.run_validator(project, "--strict")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_claude_import_rejects_extra_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            self.write_instruction_pair(project)
            project.joinpath("CLAUDE.md").write_bytes(b"@AGENTS.md\nextra")

            result = self.run_validator(project, "--strict")

            self.assertEqual(result.returncode, 1)
            self.assertIn("CLAUDE_IMPORT_CONTENT", result.stdout)

    def test_broken_local_link_fails_strict_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            self.write_instruction_pair(
                project,
                "# Agent Guide\n\nSee [missing](docs/missing.md).\n",
            )

            result = self.run_validator(project, "--strict")

            self.assertEqual(result.returncode, 1)
            self.assertIn("LOCAL_LINK_NOT_FOUND", result.stdout)

    def test_unresolved_template_placeholder_fails_strict_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            self.write_instruction_pair(
                project,
                "# {{ project_name }} Agent Guide\n",
            )

            result = self.run_validator(project, "--strict")

            self.assertEqual(result.returncode, 1)
            self.assertIn("PLACEHOLDER", result.stdout)

    def test_standalone_todo_placeholder_fails_strict_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            self.write_instruction_pair(
                project,
                "# Agent Guide\n\n- TODO: add project commands\n",
            )

            result = self.run_validator(project, "--strict")

            self.assertEqual(result.returncode, 1)
            self.assertIn("PLACEHOLDER", result.stdout)

    def test_todo_word_inside_a_real_rule_is_not_a_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            self.write_instruction_pair(
                project,
                "# Agent Guide\n\nDo not leave TODO markers in release rules.\n",
            )

            result = self.run_validator(project, "--strict")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nested_agents_without_claude_fails_only_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            self.write_instruction_pair(project)
            nested = project / "packages" / "web"
            nested.mkdir(parents=True)
            nested.joinpath("AGENTS.md").write_text(
                "# Web Agent Guide\n", encoding="utf-8"
            )

            normal = self.run_validator(project)
            strict = self.run_validator(project, "--strict")

            self.assertEqual(normal.returncode, 0, normal.stdout + normal.stderr)
            self.assertIn("CLAUDE_NOT_FOUND", normal.stdout)
            self.assertEqual(strict.returncode, 1)
            self.assertIn("CLAUDE_NOT_FOUND", strict.stdout)

    def test_length_budget_is_advisory_not_a_hard_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            lines = ["# Agent Guide", ""] + [
                f"- Project-specific rule {index}." for index in range(205)
            ]
            self.write_instruction_pair(project, "\n".join(lines) + "\n")

            result = self.run_validator(project, "--strict")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("AGENTS_LENGTH_SOFT", result.stdout)

    def test_repository_instructions_pass_strict_import_validation(self) -> None:
        result = self.run_validator(REPO_ROOT, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class BuildAgentsMdContractTests(unittest.TestCase):
    def test_skill_contract_covers_confirmed_behavior(self) -> None:
        skill_md = SKILL_DIR.joinpath("SKILL.md").read_text(encoding="utf-8")
        contract = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted(SKILL_DIR.rglob("*.md"))
        )

        self.assertNotIn("disable-model-invocation:", skill_md)
        self.assertIn("整体重构", contract)
        self.assertIn("完整内容预览", contract)
        self.assertIn("内容取舍原则", contract)
        self.assertIn("何时添加子目录指令", contract)
        self.assertIn("命令验证状态", contract)
        self.assertIn("嵌套 `AGENTS.md`", contract)
        self.assertIn("CLAUDE.md", contract)
        self.assertIn("@AGENTS.md", contract)
        self.assertIn("来源已确认、运行未验证", contract)
        self.assertIn("明确的初始化、重构或修复请求不重复确认本地编辑", contract)
        self.assertIn("仅审查或预览时保持只读", contract)
        self.assertIn("不得创建项目级 `docs/`", contract)
        self.assertIn("标准文件尾换行可有可无", contract)

        for awkward in (
            "完整替换预览",
            "项目特有信息准入",
            "嵌套准入",
            "项目事实集",
            "完成门槛",
        ):
            with self.subTest(awkward=awkward):
                self.assertNotIn(awkward, contract)

    def test_templates_and_examples_use_natural_section_names(self) -> None:
        authored_content = "\n".join(
            path.read_text(encoding="utf-8")
            for directory in ("templates", "examples")
            for path in sorted(SKILL_DIR.joinpath(directory).glob("*.md"))
        )

        for heading in (
            "## 项目概览",
            "## 仓库结构",
            "## 常用命令",
            "## 关键约定",
            "## 验证流程",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, authored_content)
        for old_heading in (
            "## 项目定位",
            "## 工作地图",
            "## 关键命令",
            "## 项目不变量",
            "## 变更与验证",
            "## 交付边界",
        ):
            with self.subTest(old_heading=old_heading):
                self.assertNotIn(old_heading, authored_content)

    def test_skill_has_three_distinct_examples(self) -> None:
        expected = {
            "library-or-cli.example.md",
            "application.example.md",
            "monorepo.example.md",
        }
        actual = {path.name for path in SKILL_DIR.joinpath("examples").glob("*.md")}

        self.assertEqual(actual, expected)

    def test_codex_adapter_allows_implicit_invocation(self) -> None:
        adapter = SKILL_DIR.joinpath("agents", "openai.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("allow_implicit_invocation: true", adapter)


if __name__ == "__main__":
    unittest.main()

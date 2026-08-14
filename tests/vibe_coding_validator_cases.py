from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.requirements_fixture import write_requirement_package

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "skills" / "vibe-coding" / "scripts" / "validate_delivery.py"
INSTALLER = REPO_ROOT / "scripts" / "install_skill.py"

ARCHITECTURE_DESIGN = Path("docs/架构设计/架构设计方案.md")
ARCHITECTURE_MIGRATION = Path("docs/架构迁移/架构迁移方案.md")
DOMAIN_ARCHITECTURE_DESIGN = Path("docs/架构设计/功能域/任务管理.md")
DOMAIN_ARCHITECTURE_MIGRATION = Path("docs/架构迁移/功能域/任务管理.md")
GLOBAL_PLAN = Path("docs/实施任务/实施任务清单.md")
DOMAIN_PLAN = Path("docs/实施任务/功能域/任务管理.md")
GLOBAL_REPORT = Path("docs/交付验收/交付验收报告.md")
DOMAIN_REPORT = Path("docs/交付验收/功能域/任务管理.md")


def doc(
    title: str, headings: tuple[str, ...], body: str, status: str = "已确认"
) -> str:
    sections = "\n".join(f"{heading}\n{body}" for heading in headings[1:])
    return f"{title}\n- 文档状态：{status}\n- 更新时间：2026-08-10\n{sections}\n"


GREEN_HEADINGS = (
    "# 架构设计方案",
    "## 需求与约束",
    "## 调研与方案比较",
    "## 目标架构",
    "## 技术选型",
    "## 目录与模块边界",
    "## 接口与数据契约",
    "## 测试与质量策略",
    "## 安全与配置",
    "## 交付与运行",
    "## 风险与权衡",
    "## 验收标准",
)
MIGRATION_HEADINGS = (
    "# 架构迁移方案",
    "## 当前架构基线",
    "## 审查发现",
    "## 外部参考与方案比较",
    "## 目标架构",
    "## 迁移差距",
    "## 分阶段迁移",
    "## 兼容与回滚",
    "## 仓库治理",
    "## 测试与质量策略",
    "## 安全与配置",
    "## 风险与验收",
)
PLAN_HEADINGS = (
    "# 实施任务清单",
    "## 执行原则",
    "## 配套 Skill 计划",
    "## 需求追踪",
    "## 依赖图",
    "## Agent 与 Worktree 计划",
    "## 任务列表",
    "## 测试数据计划",
    "## 基础工程就绪",
    "## 项目指令就绪",
    "## 集成顺序",
    "## 验收矩阵",
    "## 提交与回滚",
)
REPORT_HEADINGS = (
    "# 交付验收报告",
    "## 完成范围",
    "## 需求追踪结果",
    "## 最终架构与目录",
    "## Agent、Worktree 与提交",
    "## 实际验证",
    "## 正常测试数据",
    "## UI、视觉与交互",
    "## 安全与配置",
    "## 配套 Skill 生命周期",
    "## 仓库治理",
    "## 已验证",
    "## 未验证",
    "## 阻塞",
    "## 外部动作状态",
    "## 可复现命令",
)
DOMAIN_ARCHITECTURE_HEADINGS = (
    "# 功能域架构：任务管理",
    "## 功能域边界",
    "## 需求映射",
    "## 组件与依赖",
    "## 接口与数据契约",
    "## 验证策略",
    "## 风险与回退",
)
DOMAIN_PLAN_HEADINGS = (
    "# 功能域实施任务：任务管理",
    "## 功能域目标",
    "## 输入与依赖",
    "## 任务列表",
    "## 功能域验证",
    "## 集成与回滚",
)
DOMAIN_REPORT_HEADINGS = (
    "# 功能域交付验收：任务管理",
    "## 完成范围",
    "## 需求与任务追踪",
    "## 实际验证",
    "## 未验证与阻塞",
    "## 集成结果",
)
AGENTS_MD = """# Fixture project instructions

## Commands

- `python -m unittest`: run the verified test suite.
"""


class VibeCodingValidatorTests(unittest.TestCase):
    @staticmethod
    def expanded_marker(marker: str) -> str:
        if "F-001-AC-01" in marker and "F-001-AC-02" not in marker:
            return marker + " F-001-AC-02"
        return marker

    def run_validator(
        self, root: Path, mode: str, phase: str, *extra: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                str(root),
                "--mode",
                mode,
                "--phase",
                phase,
                "--strict",
                *extra,
            ],
            check=False,
            text=True,
            capture_output=True,
        )

    def write_architecture(self, root: Path, mode: str) -> None:
        requirements_mode = mode in {"greenfield", "continuation"}
        if requirements_mode:
            write_requirement_package(root)
        marker = "F-001 F-001-AC-01" if requirements_mode else "AUD-001"
        headings = GREEN_HEADINGS if requirements_mode else MIGRATION_HEADINGS
        architecture = (
            root / ARCHITECTURE_DESIGN
            if requirements_mode
            else root / ARCHITECTURE_MIGRATION
        )
        route = {
            "greenfield": (
                "- 项目路线：新项目\n"
                "- 旧项目参考：不参考\n"
                "- 允许参考范围：N/A（不参考旧项目）\n"
                "- 需求快照：`docs/产品需求/需求包清单.yaml`\n"
            ),
            "continuation": (
                "- 项目路线：现有项目续建\n"
                "- 旧项目参考：当前项目\n"
                "- 允许参考范围：当前项目中与已确认需求直接相关的内容\n"
                "- 需求快照：`docs/产品需求/需求包清单.yaml`\n"
            ),
            "migration": (
                "- 项目路线：现有项目架构或技术栈迁移\n"
                "- 旧项目参考：当前项目\n"
                "- 允许参考范围：用户确认的迁移基线\n"
            ),
        }[mode]
        architecture.parent.mkdir(parents=True, exist_ok=True)
        architecture.write_text(
            doc(
                headings[0],
                headings,
                f"{marker}：该章节包含足够具体的架构、测试、安全和回滚证据。",
            ).replace(
                "- 更新时间：2026-08-10\n",
                "- 更新时间：2026-08-10\n" + route,
            ),
            encoding="utf-8",
        )
        domain_architecture = (
            root / DOMAIN_ARCHITECTURE_DESIGN
            if requirements_mode
            else root / DOMAIN_ARCHITECTURE_MIGRATION
        )
        domain_architecture.parent.mkdir(parents=True, exist_ok=True)
        domain_architecture.write_text(
            doc(
                DOMAIN_ARCHITECTURE_HEADINGS[0],
                DOMAIN_ARCHITECTURE_HEADINGS,
                f"{marker}：任务管理域包含可执行的边界、契约、验证与回退说明。",
            ),
            encoding="utf-8",
        )

    def task_block(
        self, marker: str, status: str = "待开始", commit: str = "待生成"
    ) -> str:
        integration_status = (
            "已集成到指定集成分支并验证通过。" if status == "已完成" else "尚未集成。"
        )
        return textwrap.dedent(f"""
            ### TASK-001 账号创建
            - 状态：{status}
            - 需求/验收/Finding：{marker}
            - 目标：完成可独立验收的账号创建功能。
            - 首个验证证据：test_account_creation
            - 正常测试数据：factory 创建隔离普通用户并自动清理。
            - 验证命令：python -m unittest
            - Worktree：N/A（串行执行）
            - 集成状态：{integration_status}
            - 提交边界：账号创建实现及其必要测试。
            - Commit：{commit}
            - 回滚：revert 本任务 commit。
            - 完成条件：主流程和错误路径均通过自动化测试。
            """).strip()

    def write_plan(
        self, root: Path, marker: str, status: str = "待开始", commit: str = "待生成"
    ) -> None:
        marker = self.expanded_marker(marker)
        body = "该章节包含完整、可执行且可复核的任务、数据、测试、集成与回滚说明。"
        text = doc(PLAN_HEADINGS[0], PLAN_HEADINGS, body)
        text = text.replace(
            "## 需求追踪\n" + body, f"## 需求追踪\n{marker} -> TASK-001"
        )
        text = text.replace(
            "## 任务列表\n" + body,
            "## 任务列表\n任务管理域任务见 `功能域/任务管理.md`。",
        )
        global_plan = root / GLOBAL_PLAN
        global_plan.parent.mkdir(parents=True, exist_ok=True)
        global_plan.write_text(text, encoding="utf-8")

        domain_body = "该功能域包含完整、可执行且可复核的输入、任务、验证和集成说明。"
        domain_text = doc(
            DOMAIN_PLAN_HEADINGS[0], DOMAIN_PLAN_HEADINGS, domain_body
        ).replace(
            "## 任务列表\n" + domain_body,
            "## 任务列表\n" + self.task_block(marker, status, commit),
        )
        domain_plan = root / DOMAIN_PLAN
        domain_plan.parent.mkdir(parents=True, exist_ok=True)
        domain_plan.write_text(domain_text, encoding="utf-8")

    def write_report(self, root: Path, marker: str, commit: str) -> None:
        marker = self.expanded_marker(marker)
        body = f"{marker}、TASK-001 与 commit {commit} 已由真实命令和测试证据完成验证。"
        global_report = root / GLOBAL_REPORT
        global_report.parent.mkdir(parents=True, exist_ok=True)
        global_report.write_text(
            doc(REPORT_HEADINGS[0], REPORT_HEADINGS, body, status="已完成"),
            encoding="utf-8",
        )
        domain_report = root / DOMAIN_REPORT
        domain_report.parent.mkdir(parents=True, exist_ok=True)
        domain_report.write_text(
            doc(
                DOMAIN_REPORT_HEADINGS[0],
                DOMAIN_REPORT_HEADINGS,
                body,
                status="已完成",
            ),
            encoding="utf-8",
        )

    def write_agent_instructions(self, root: Path) -> None:
        root.joinpath("AGENTS.md").write_text(AGENTS_MD, encoding="utf-8")
        root.joinpath("CLAUDE.md").symlink_to("AGENTS.md")

    def init_git(self, root: Path) -> None:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(
            ["git", "-C", str(root), "config", "user.name", "Test"], check=True
        )
        subprocess.run(
            ["git", "-C", str(root), "config", "user.email", "test@example.com"],
            check=True,
        )

    def commit_paths(self, root: Path, message: str, *paths: str) -> str:
        subprocess.run(["git", "-C", str(root), "add", "--", *paths], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", message], check=True)
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()

    def write_readiness_plan(
        self,
        root: Path,
        marker: str,
        *,
        status: str = "已更新并验证",
        commit: str = "abcdef1",
        baseline: str = "abcdef1",
        foundation_commit: str = "N/A（无需变更）",
        existing_worktrees: str = "N/A（无既有 worktree）",
    ) -> None:
        self.write_plan(root, marker)
        plan = root / GLOBAL_PLAN
        text = plan.read_text(encoding="utf-8")
        foundation = textwrap.dedent(f"""
            ## 基础工程就绪

            - 状态：已验证
            - 安装命令：python -m pip install -e .
            - 安装结果：exit 0，依赖安装成功。
            - 启动或 Smoke 命令：python -m fixture --help
            - 启动或 Smoke 结果：exit 0，smoke 通过。
            - 基础测试命令：python -m unittest
            - 基础测试结果：exit 0，基础测试通过。
            - 基础工程提交：{foundation_commit}
            - 既有 Worktrees：{existing_worktrees}
            """).strip()
        readiness = textwrap.dedent(f"""
            ## 项目指令就绪

            - 状态：{status}
            - 触发证据：根项目指令需要初始化或更新。
            - 内容确认：已确认完整内容和文件操作。
            - 验证命令：python3 <build-agents-md>/scripts/validate_agents_md.py . --strict
            - 验证结果：通过。
            - 治理提交：{commit}
            - 功能开发基线：{baseline}
            - 恢复条件：N/A（已就绪）
            """).strip()
        text = text.replace(
            "## 基础工程就绪\n该章节包含完整、可执行且可复核的任务、数据、测试、集成与回滚说明。",
            foundation,
        )
        text = text.replace(
            "## 项目指令就绪\n该章节包含完整、可执行且可复核的任务、数据、测试、集成与回滚说明。",
            readiness,
        )
        plan.write_text(text, encoding="utf-8")

    def test_greenfield_plan_passes_and_missing_traceability_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            self.write_plan(root, "F-001 F-001-AC-01")
            passed = self.run_validator(root, "greenfield", "plan")
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            plan = root / DOMAIN_PLAN
            plan.write_text(
                plan.read_text().replace("F-001-AC-01", "F-001-AC-99"),
                encoding="utf-8",
            )
            failed = self.run_validator(root, "greenfield", "plan")
            self.assertEqual(failed.returncode, 1)
            self.assertIn("PRD_TRACEABILITY", failed.stdout)

    def test_existing_project_continuation_uses_confirmed_requirement_package(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "continuation")
            self.write_plan(root, "F-001 F-001-AC-01")

            result = self.run_validator(root, "continuation", "plan")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unconfirmed_requirement_package_is_not_implementable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            manifest_path = root / "docs" / "产品需求" / "需求包清单.yaml"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "in_progress"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_validator(root, "greenfield", "architecture")

            self.assertEqual(result.returncode, 1)
            self.assertIn("REQUIREMENTS_PACKAGE", result.stdout)
            self.assertIn("PACKAGE_STATUS", result.stdout)

    def test_new_project_reference_requires_an_explicit_allowed_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            path = root / ARCHITECTURE_DESIGN
            text = path.read_text(encoding="utf-8").replace(
                "- 旧项目参考：不参考\n- 允许参考范围：N/A（不参考旧项目）",
                "- 旧项目参考：按用户指定范围\n- 允许参考范围：旧项目的公开 CLI 输入输出",
            )
            path.write_text(text, encoding="utf-8")
            passed = self.run_validator(root, "greenfield", "architecture")
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)

            path.write_text(
                text.replace(
                    "- 允许参考范围：旧项目的公开 CLI 输入输出",
                    "- 允许参考范围：",
                ),
                encoding="utf-8",
            )
            failed = self.run_validator(root, "greenfield", "architecture")
            self.assertEqual(failed.returncode, 1)
            self.assertIn("REFERENCE_SCOPE", failed.stdout)

    def test_legacy_root_documents_and_missing_domain_documents_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            legacy = root / "docs" / "架构设计方案.md"
            legacy.write_text("# legacy\n", encoding="utf-8")
            (root / DOMAIN_ARCHITECTURE_DESIGN).unlink()

            result = self.run_validator(root, "greenfield", "architecture")

            self.assertEqual(result.returncode, 1)
            self.assertIn("LEGACY_DOCUMENT_PATH", result.stdout)
            self.assertIn("DOMAIN_DOCUMENT_REQUIRED", result.stdout)

    def test_migration_plan_requires_audit_traceability(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "migration")
            self.write_plan(root, "AUD-001")
            passed = self.run_validator(root, "migration", "plan")
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            plan = root / DOMAIN_PLAN
            plan.write_text(
                plan.read_text().replace("AUD-001", "AUD-999"),
                encoding="utf-8",
            )
            failed = self.run_validator(root, "migration", "plan")
            self.assertIn("AUDIT_TRACEABILITY", failed.stdout)

    def test_placeholder_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            path = root / ARCHITECTURE_DESIGN
            path.write_text(path.read_text() + "\nTODO\n", encoding="utf-8")
            result = self.run_validator(root, "greenfield", "architecture")
            self.assertEqual(result.returncode, 1)
            self.assertIn("PLACEHOLDER", result.stdout)

    def test_readiness_requires_agent_instructions_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            self.write_plan(root, "F-001 F-001-AC-01")
            plan = root / GLOBAL_PLAN
            plan.write_text(
                plan.read_text(encoding="utf-8").replace(
                    "## 项目指令就绪", "## 项目指令状态"
                ),
                encoding="utf-8",
            )

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("AGENT_READINESS_SECTION", result.stdout)

    def test_readiness_requires_foundation_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            self.write_plan(root, "F-001 F-001-AC-01")

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("FOUNDATION_NOT_READY", result.stdout)

    def test_readiness_rejects_unexecuted_foundation_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="有效沿用",
                commit="N/A（无需更新）",
                baseline="当前已确认基线",
            )
            self.write_agent_instructions(root)
            plan = root / GLOBAL_PLAN
            plan.write_text(
                plan.read_text(encoding="utf-8")
                .replace("- 安装命令：python -m pip install -e .", "- 安装命令：未执行")
                .replace(
                    "- 安装结果：exit 0，依赖安装成功。", "- 安装结果：尚无结果。"
                ),
                encoding="utf-8",
            )

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("FOUNDATION_COMMAND_REQUIRED", result.stdout)
            self.assertIn("FOUNDATION_RESULT_NOT_PASSING", result.stdout)

    def test_readiness_rejects_negated_or_unexecuted_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            self.write_agent_instructions(root)
            governance = self.commit_paths(
                root,
                "docs(agent): establish project instructions",
                "AGENTS.md",
                "CLAUDE.md",
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                commit=governance,
                baseline="readiness 执行时的当前 HEAD",
            )
            plan = root / GLOBAL_PLAN
            plan.write_text(
                plan.read_text(encoding="utf-8")
                .replace(
                    "- 安装命令：python -m pip install -e .",
                    "- 安装命令：未执行，因为环境缺失。",
                )
                .replace(
                    "- 安装结果：exit 0，依赖安装成功。",
                    "- 安装结果：依赖安装未成功。",
                )
                .replace(
                    "- 验证命令：python3 <build-agents-md>/scripts/validate_agents_md.py . --strict",
                    "- 验证命令：未执行，因为环境缺失：python3 <build-agents-md>/scripts/validate_agents_md.py . --strict",
                )
                .replace("- 内容确认：已确认", "- 内容确认：未经已确认")
                .replace("- 验证结果：通过。", "- 验证结果：未通过。"),
                encoding="utf-8",
            )

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("FOUNDATION_COMMAND_REQUIRED", result.stdout)
            self.assertIn("FOUNDATION_RESULT_NOT_PASSING", result.stdout)
            self.assertIn("AGENT_VALIDATION_COMMAND", result.stdout)
            self.assertIn("AGENT_VALIDATION_RESULT", result.stdout)
            self.assertIn("AGENT_CONTENT_APPROVAL", result.stdout)

    def test_readiness_rejects_unknown_foundation_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            subprocess.run(
                ["git", "-C", str(root), "commit", "--allow-empty", "-qm", "base"],
                check=True,
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="有效沿用",
                commit="N/A（无需更新）",
                baseline="readiness 执行时的当前 HEAD",
            )
            self.write_agent_instructions(root)
            plan = root / GLOBAL_PLAN
            plan.write_text(
                plan.read_text(encoding="utf-8").replace(
                    "- 基础工程提交：N/A（无需变更）",
                    "- 基础工程提交：deadbee",
                ),
                encoding="utf-8",
            )

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("FOUNDATION_COMMIT_UNKNOWN", result.stdout)

    def test_readiness_requires_foundation_commit_in_current_head(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            subprocess.run(
                ["git", "-C", str(root), "commit", "--allow-empty", "-qm", "base"],
                check=True,
            )
            primary = subprocess.check_output(
                ["git", "-C", str(root), "branch", "--show-current"], text=True
            ).strip()
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", "-c", "side"],
                check=True,
            )
            root.joinpath("foundation.txt").write_text("side\n", encoding="utf-8")
            foundation = self.commit_paths(
                root, "chore: unrelated foundation", "foundation.txt"
            )
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", primary], check=True
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="有效沿用",
                commit="N/A（无需更新）",
                baseline="readiness 执行时的当前 HEAD",
                foundation_commit=foundation,
            )
            self.write_agent_instructions(root)

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("FOUNDATION_COMMIT_NOT_IN_HEAD", result.stdout)

    def test_readiness_accepts_verified_existing_agent_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="有效沿用",
                commit="N/A（无需更新）",
                baseline="当前已确认基线",
            )
            self.write_agent_instructions(root)

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_readiness_requires_confirmed_agent_instruction_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="等待 build-agents-md",
                commit="未生成",
                baseline="未建立",
            )

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("AGENT_INSTRUCTIONS_PENDING", result.stdout)

    def test_readiness_requires_governance_commit_in_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Test"], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "test@example.com"],
                check=True,
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(root, "F-001 F-001-AC-01")
            self.write_agent_instructions(root)

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("AGENT_GOVERNANCE_COMMIT_UNKNOWN", result.stdout)

    def test_readiness_accepts_frozen_governance_commit_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            self.write_agent_instructions(root)
            governance = self.commit_paths(
                root,
                "docs(agent): establish project instructions",
                "AGENTS.md",
                "CLAUDE.md",
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                commit=governance,
                baseline="readiness 执行时的当前 HEAD",
            )
            self.commit_paths(
                root,
                "docs(plan): record implementation readiness",
                "docs",
            )

            result = self.run_validator(
                root, "greenfield", "readiness", "--require-clean"
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_readiness_requires_governance_commit_in_feature_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            root.joinpath("base.txt").write_text("base\n", encoding="utf-8")
            baseline = self.commit_paths(root, "base", "base.txt")
            self.write_agent_instructions(root)
            governance = self.commit_paths(
                root,
                "docs(agent): establish project instructions",
                "AGENTS.md",
                "CLAUDE.md",
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                commit=governance,
                baseline=baseline,
            )

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("AGENT_GOVERNANCE_NOT_IN_BASELINE", result.stdout)

    def test_readiness_rejects_governance_commit_without_instruction_change(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            self.write_agent_instructions(root)
            self.commit_paths(
                root,
                "docs(agent): establish project instructions",
                "AGENTS.md",
                "CLAUDE.md",
            )
            root.joinpath("app.txt").write_text("not instructions\n", encoding="utf-8")
            fake_governance = self.commit_paths(
                root, "docs(agent): misleading commit", "app.txt"
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                commit=fake_governance,
                baseline="readiness 执行时的当前 HEAD",
            )

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("AGENT_GOVERNANCE_COMMIT_CONTENT", result.stdout)

    def test_readiness_requires_feature_baseline_in_current_head(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            self.write_agent_instructions(root)
            governance = self.commit_paths(
                root,
                "docs(agent): establish project instructions",
                "AGENTS.md",
                "CLAUDE.md",
            )
            primary = subprocess.check_output(
                ["git", "-C", str(root), "branch", "--show-current"], text=True
            ).strip()
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", "-c", "side"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "commit", "--allow-empty", "-qm", "side"],
                check=True,
            )
            side_baseline = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
            ).strip()
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", primary], check=True
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                commit=governance,
                baseline=side_baseline,
            )

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("AGENT_BASELINE_NOT_IN_CURRENT_HEAD", result.stdout)

    def test_delivery_keeps_governance_sha_frozen_after_feature_commits(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            self.write_agent_instructions(root)
            governance = self.commit_paths(
                root,
                "docs(agent): establish project instructions",
                "AGENTS.md",
                "CLAUDE.md",
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                commit=governance,
                baseline="readiness 执行时的当前 HEAD",
            )
            readiness_baseline = self.commit_paths(
                root,
                "docs(plan): record implementation readiness",
                "docs",
            )

            marker_rejected = self.run_validator(root, "greenfield", "delivery")
            self.assertIn("AGENT_FEATURE_BASELINE_UNKNOWN", marker_rejected.stdout)

            plan = root / GLOBAL_PLAN
            plan.write_text(
                plan.read_text(encoding="utf-8").replace(
                    "- 功能开发基线：readiness 执行时的当前 HEAD",
                    f"- 功能开发基线：{readiness_baseline}",
                ),
                encoding="utf-8",
            )
            root.joinpath("app.txt").write_text("feature\n", encoding="utf-8")
            feature_sha = self.commit_paths(root, "feat: add feature", "app.txt")
            domain_plan = root / DOMAIN_PLAN
            domain_plan.write_text(
                domain_plan.read_text(encoding="utf-8")
                .replace("- 状态：待开始", "- 状态：已完成")
                .replace("- Commit：待生成", f"- Commit：{feature_sha}")
                .replace("- 集成状态：尚未集成。", "- 集成状态：已集成。"),
                encoding="utf-8",
            )
            self.write_report(root, "F-001 F-001-AC-01", feature_sha)

            result = self.run_validator(root, "greenfield", "delivery")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            root.joinpath("AGENTS.md").write_text(
                AGENTS_MD
                + "\n- `python -m unittest tests.integration`: run integration tests.\n",
                encoding="utf-8",
            )
            self.commit_paths(
                root,
                "docs(agent): unconfirmed instruction drift",
                "AGENTS.md",
            )

            drifted = self.run_validator(root, "greenfield", "delivery")

            self.assertEqual(drifted.returncode, 1)
            self.assertIn("AGENT_INSTRUCTIONS_DRIFT", drifted.stdout)

    def test_readiness_does_not_block_on_agents_length_soft_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="有效沿用",
                commit="N/A（无需更新）",
                baseline="当前已确认基线",
            )
            root.joinpath("AGENTS.md").write_text(
                "# Long but valid instructions\n"
                + "\n".join(f"- Rule {index}" for index in range(121)),
                encoding="utf-8",
            )
            root.joinpath("CLAUDE.md").symlink_to("AGENTS.md")

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("AGENTS_LENGTH_SOFT", result.stdout)

    def test_readiness_accepts_valid_nested_agent_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="有效沿用",
                commit="N/A（无需更新）",
                baseline="当前已确认基线",
            )
            self.write_agent_instructions(root)
            nested = root / "services" / "api"
            nested.mkdir(parents=True)
            nested.joinpath("AGENTS.md").write_text(
                "# API instructions\n\n- `python -m unittest tests.api`\n",
                encoding="utf-8",
            )
            nested.joinpath("CLAUDE.md").symlink_to("AGENTS.md")

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_readiness_accepts_nested_only_governance_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            self.write_agent_instructions(root)
            self.commit_paths(
                root,
                "docs(agent): establish root instructions",
                "AGENTS.md",
                "CLAUDE.md",
            )
            nested = root / "services" / "api"
            nested.mkdir(parents=True)
            nested.joinpath("AGENTS.md").write_text(
                "# API instructions\n\n- `python -m unittest tests.api`\n",
                encoding="utf-8",
            )
            nested.joinpath("CLAUDE.md").symlink_to("AGENTS.md")
            governance = self.commit_paths(
                root,
                "docs(agent): establish API instructions",
                "services/api/AGENTS.md",
                "services/api/CLAUDE.md",
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                commit=governance,
                baseline="readiness 执行时的当前 HEAD",
            )

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_readiness_accepts_root_and_nested_governance_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            self.write_agent_instructions(root)
            nested = root / "services" / "api"
            nested.mkdir(parents=True)
            nested.joinpath("AGENTS.md").write_text(
                "# API instructions\n\n- `python -m unittest tests.api`\n",
                encoding="utf-8",
            )
            nested.joinpath("CLAUDE.md").symlink_to("AGENTS.md")
            governance = self.commit_paths(
                root,
                "docs(agent): establish all project instructions",
                "AGENTS.md",
                "CLAUDE.md",
                "services/api/AGENTS.md",
                "services/api/CLAUDE.md",
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                commit=governance,
                baseline="readiness 执行时的当前 HEAD",
            )

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_readiness_requires_claude_md_relative_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="有效沿用",
                commit="N/A（无需更新）",
                baseline="当前已确认基线",
            )
            root.joinpath("AGENTS.md").write_text(AGENTS_MD, encoding="utf-8")
            root.joinpath("CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("CLAUDE_SYMLINK_REQUIRED", result.stdout)

    def test_readiness_rejects_feature_worktree_created_too_early(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Test"], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "test@example.com"],
                check=True,
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="有效沿用",
                commit="N/A（无需更新）",
                baseline="当前 HEAD",
            )
            self.write_agent_instructions(root)
            root.joinpath(".gitignore").write_text(".worktrees/\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "prepare plan"],
                check=True,
            )
            worktree = root / ".worktrees" / "TASK-001"
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "worktree",
                    "add",
                    "-q",
                    "-b",
                    "feat/task-001",
                    str(worktree),
                    "HEAD",
                ],
                check=True,
            )

            result = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(result.returncode, 1)
            self.assertIn("FEATURE_WORKTREE_BEFORE_READINESS", result.stdout)

    def test_readiness_allows_only_exact_preexisting_worktree_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="有效沿用",
                commit="N/A（无需更新）",
                baseline="readiness 执行时的当前 HEAD",
            )
            self.write_agent_instructions(root)
            root.joinpath(".gitignore").write_text(".worktrees/\n", encoding="utf-8")
            self.commit_paths(root, "prepare plan", ".")
            worktree = root / ".worktrees" / "preexisting"
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "worktree",
                    "add",
                    "-q",
                    "-b",
                    "chore/preexisting",
                    str(worktree),
                    "HEAD",
                ],
                check=True,
            )
            plan = root / GLOBAL_PLAN
            plan.write_text(
                plan.read_text(encoding="utf-8").replace(
                    "- 既有 Worktrees：N/A（无既有 worktree）",
                    "- 既有 Worktrees：`.worktrees/preexisting` | "
                    "`refs/heads/chore/preexisting` | 并行既有任务",
                ),
                encoding="utf-8",
            )

            allowed = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)

            registered_plan = plan.read_text(encoding="utf-8")
            plan.write_text(
                registered_plan.replace(
                    "`refs/heads/chore/preexisting`", "`refs/heads/TASK-001`"
                ),
                encoding="utf-8",
            )
            mismatched = self.run_validator(root, "greenfield", "readiness")

            self.assertEqual(mismatched.returncode, 1)
            self.assertIn("WORKTREE_BASELINE_MISMATCH", mismatched.stdout)

            plan.write_text(
                registered_plan.replace(
                    "`.worktrees/preexisting`", "`.worktrees/wrong-path`"
                ),
                encoding="utf-8",
            )
            wrong_path = self.run_validator(root, "greenfield", "readiness")
            self.assertEqual(wrong_path.returncode, 1)
            self.assertIn("FEATURE_WORKTREE_BEFORE_READINESS", wrong_path.stdout)
            self.assertIn("WORKTREE_BASELINE_MISMATCH", wrong_path.stdout)

            plan.write_text(
                registered_plan.replace(
                    "`.worktrees/preexisting` | `refs/heads/chore/preexisting` | 并行既有任务",
                    "`refs/heads/chore/preexisting`",
                ),
                encoding="utf-8",
            )
            branch_only = self.run_validator(root, "greenfield", "readiness")
            self.assertEqual(branch_only.returncode, 1)
            self.assertIn("WORKTREE_BASELINE_FORMAT", branch_only.stdout)
            self.assertIn("FEATURE_WORKTREE_BEFORE_READINESS", branch_only.stdout)

    def test_delivery_rechecks_agent_instruction_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            self.write_agent_instructions(root)
            sha = self.commit_paths(
                root,
                "docs(agent): establish instructions",
                "AGENTS.md",
                "CLAUDE.md",
            )
            self.write_architecture(root, "greenfield")
            self.write_readiness_plan(
                root, "F-001 F-001-AC-01", commit=sha, baseline=sha
            )
            plan = root / DOMAIN_PLAN
            plan.write_text(
                plan.read_text(encoding="utf-8")
                .replace("- 状态：待开始", "- 状态：已完成")
                .replace("- Commit：待生成", f"- Commit：{sha}")
                .replace("- 集成状态：尚未集成。", "- 集成状态：已集成。"),
                encoding="utf-8",
            )
            self.write_report(root, "F-001 F-001-AC-01", sha)
            root.joinpath("CLAUDE.md").unlink()
            root.joinpath("CLAUDE.md").symlink_to("WRONG.md")

            result = self.run_validator(root, "greenfield", "delivery")

            self.assertEqual(result.returncode, 1)
            self.assertIn("CLAUDE_LINK_TARGET", result.stdout)

    def test_delivery_checks_real_commit_and_clean_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Test"], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "test@example.com"],
                check=True,
            )
            self.write_architecture(root, "greenfield")
            self.write_agent_instructions(root)
            (root / "app.txt").write_text("implemented\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "initial implementation"],
                check=True,
            )
            sha = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "--short", "HEAD"], text=True
            ).strip()
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="有效沿用",
                commit="N/A（无需更新）",
                baseline=sha,
            )
            plan = root / DOMAIN_PLAN
            plan.write_text(
                plan.read_text(encoding="utf-8")
                .replace("- 状态：待开始", "- 状态：已完成")
                .replace("- Commit：待生成", f"- Commit：{sha}")
                .replace("- 集成状态：尚未集成。", "- 集成状态：已集成。"),
                encoding="utf-8",
            )
            self.write_report(root, "F-001 F-001-AC-01", sha)
            subprocess.run(["git", "-C", str(root), "add", "docs"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "docs: record delivery"],
                check=True,
            )
            result = self.run_validator(
                root, "greenfield", "delivery", "--require-clean"
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            plan = root / DOMAIN_PLAN
            plan.write_text(plan.read_text().replace(sha, "deadbee"), encoding="utf-8")
            failed = self.run_validator(root, "greenfield", "delivery")
            self.assertIn("TASK_COMMIT_UNKNOWN", failed.stdout)

    def test_delivery_rejects_completed_task_with_registered_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Test"], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "test@example.com"],
                check=True,
            )
            self.write_architecture(root, "greenfield")
            self.write_agent_instructions(root)
            (root / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
            (root / "app.txt").write_text("implemented\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "initial implementation"],
                check=True,
            )
            sha = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "--short", "HEAD"], text=True
            ).strip()
            worktree = root / ".worktrees" / "TASK-001"
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "worktree",
                    "add",
                    "-q",
                    "-b",
                    "feat/task-001",
                    str(worktree),
                    sha,
                ],
                check=True,
            )
            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                status="有效沿用",
                commit="N/A（无需更新）",
                baseline=sha,
            )
            plan = root / DOMAIN_PLAN
            plan.write_text(
                plan.read_text(encoding="utf-8")
                .replace("- 状态：待开始", "- 状态：已完成")
                .replace("- Commit：待生成", f"- Commit：{sha}")
                .replace("- 集成状态：尚未集成。", "- 集成状态：已集成。")
                .replace(
                    "- Worktree：N/A（串行执行）",
                    "- Worktree：`.worktrees/TASK-001`",
                ),
                encoding="utf-8",
            )
            self.write_report(root, "F-001 F-001-AC-01", sha)
            subprocess.run(["git", "-C", str(root), "add", "docs"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "docs: record delivery"],
                check=True,
            )

            failed = self.run_validator(
                root, "greenfield", "delivery", "--require-clean"
            )
            self.assertEqual(failed.returncode, 1, failed.stdout + failed.stderr)
            self.assertIn("COMPLETED_WORKTREE_REMAINS", failed.stdout)

            plan.write_text(
                plan.read_text()
                .replace("- 状态：已完成", "- 状态：阻塞")
                .replace(
                    "- 集成状态：已集成到指定集成分支并验证通过。",
                    "- 集成状态：尚未集成，保留 worktree 供问题恢复。",
                ),
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(root), "add", "docs"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "docs: record blocker"],
                check=True,
            )
            blocked = self.run_validator(
                root, "greenfield", "delivery", "--require-clean"
            )
            self.assertEqual(blocked.returncode, 0, blocked.stdout + blocked.stderr)

            plan.write_text(
                plan.read_text()
                .replace("- 状态：阻塞", "- 状态：已完成")
                .replace(
                    "- 集成状态：尚未集成，保留 worktree 供问题恢复。",
                    "- 集成状态：已集成到指定集成分支并验证通过。",
                ),
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(root), "add", "docs"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "docs: clear blocker"],
                check=True,
            )

            subprocess.run(
                ["git", "-C", str(root), "worktree", "remove", str(worktree)],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "branch", "-d", "feat/task-001"],
                check=True,
                capture_output=True,
                text=True,
            )
            passed = self.run_validator(
                root, "greenfield", "delivery", "--require-clean"
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)

    def test_end_to_end_readiness_feature_cleanup_and_instruction_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_git(root)
            self.write_architecture(root, "greenfield")
            root.joinpath("app.txt").write_text("scaffold\n", encoding="utf-8")
            root.joinpath(".gitignore").write_text(".worktrees/\n", encoding="utf-8")
            scaffold = self.commit_paths(
                root,
                "chore(scaffold): establish verified project foundation",
                "app.txt",
                ".gitignore",
                "docs/架构设计",
                "docs/产品需求",
            )

            self.write_agent_instructions(root)
            nested = root / "services" / "api"
            nested.mkdir(parents=True)
            nested.joinpath("AGENTS.md").write_text(
                "# API instructions\n\n- `python -m unittest tests.api`\n",
                encoding="utf-8",
            )
            nested.joinpath("CLAUDE.md").symlink_to("AGENTS.md")
            governance = self.commit_paths(
                root,
                "docs(agent): establish project instructions",
                "AGENTS.md",
                "CLAUDE.md",
                "services/api/AGENTS.md",
                "services/api/CLAUDE.md",
            )

            self.write_readiness_plan(
                root,
                "F-001 F-001-AC-01",
                commit=governance,
                baseline="readiness 执行时的当前 HEAD",
                foundation_commit=scaffold,
            )
            readiness_record = self.commit_paths(
                root,
                "docs(plan): record implementation readiness",
                "docs/实施任务",
            )

            readiness = self.run_validator(
                root, "greenfield", "readiness", "--require-clean"
            )
            self.assertEqual(
                readiness.returncode, 0, readiness.stdout + readiness.stderr
            )

            plan = root / GLOBAL_PLAN
            plan.write_text(
                plan.read_text(encoding="utf-8").replace(
                    "- 功能开发基线：readiness 执行时的当前 HEAD",
                    f"- 功能开发基线：{readiness_record}",
                ),
                encoding="utf-8",
            )
            self.commit_paths(
                root,
                "docs(plan): freeze readiness baseline",
                GLOBAL_PLAN.as_posix(),
            )

            worktree = root / ".worktrees" / "TASK-001"
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "worktree",
                    "add",
                    "-q",
                    "-b",
                    "feat/TASK-001",
                    str(worktree),
                    "HEAD",
                ],
                check=True,
            )
            worktree.joinpath("feature.txt").write_text(
                "implemented\n", encoding="utf-8"
            )
            feature = self.commit_paths(
                worktree,
                "feat: implement TASK-001",
                "feature.txt",
            )
            subprocess.run(
                ["git", "-C", str(root), "merge", "--ff-only", "feat/TASK-001"],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "worktree", "remove", str(worktree)],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "branch", "-d", "feat/TASK-001"],
                check=True,
                capture_output=True,
                text=True,
            )

            domain_plan = root / DOMAIN_PLAN
            domain_plan.write_text(
                domain_plan.read_text(encoding="utf-8")
                .replace("- 状态：待开始", "- 状态：已完成")
                .replace("- Commit：待生成", f"- Commit：{feature}")
                .replace("- 集成状态：尚未集成。", "- 集成状态：已集成。")
                .replace(
                    "- Worktree：N/A（串行执行）",
                    "- Worktree：`.worktrees/TASK-001`",
                ),
                encoding="utf-8",
            )
            self.write_report(root, "F-001 F-001-AC-01", feature)
            self.commit_paths(root, "docs: record delivery", "docs")

            delivery = self.run_validator(
                root, "greenfield", "delivery", "--require-clean"
            )
            self.assertEqual(delivery.returncode, 0, delivery.stdout + delivery.stderr)

            nested.joinpath("AGENTS.md").write_text(
                "# API instructions\n\n- `python -m unittest tests.api.v2`\n",
                encoding="utf-8",
            )
            self.commit_paths(
                root,
                "docs(agent): unconfirmed nested drift",
                "services/api/AGENTS.md",
            )
            drifted = self.run_validator(
                root, "greenfield", "delivery", "--require-clean"
            )
            self.assertEqual(drifted.returncode, 1)
            self.assertIn("AGENT_INSTRUCTIONS_DRIFT", drifted.stdout)

    def test_vibe_coding_installs_for_both_platforms(self) -> None:
        for platform, platform_root in (("claude", ".claude"), ("codex", ".agents")):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as temp:
                env = os.environ.copy()
                env["HOME"] = temp
                result = subprocess.run(
                    [
                        sys.executable,
                        str(INSTALLER),
                        "vibe-coding",
                        "--platform",
                        platform,
                        "--scope",
                        "user",
                    ],
                    cwd=REPO_ROOT,
                    env=env,
                    check=False,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                target = Path(temp) / platform_root / "skills" / "vibe-coding"
                self.assertTrue(
                    target.joinpath("scripts", "validate_delivery.py").is_file()
                )
                self.assertTrue(target.joinpath("scripts", "validate_prd.py").is_file())
                self.assertTrue(
                    target.joinpath("scripts", "import_requirements.py").is_file()
                )
                self.assertTrue(
                    target.joinpath("scripts", "validate_agents_md.py").is_file()
                )
                self.assertFalse(
                    target.joinpath("scripts", "validate_prd.py").is_symlink()
                )
                self.assertFalse(
                    target.joinpath("scripts", "validate_agents_md.py").is_symlink()
                )
                self.assertFalse(
                    target.joinpath("prompts", "reviewer.agent.md").is_symlink()
                )
                self.assertEqual(
                    target.joinpath("agents").exists(), platform == "codex"
                )

                project = Path(temp) / "fixture-project"
                self.write_architecture(project, "greenfield")
                self.write_readiness_plan(
                    project,
                    "F-001 F-001-AC-01",
                    status="有效沿用",
                    commit="N/A（无需更新）",
                    baseline="N/A（非 Git 项目）",
                )
                self.write_agent_instructions(project)
                installed_readiness = subprocess.run(
                    [
                        sys.executable,
                        str(target / "scripts" / "validate_delivery.py"),
                        str(project),
                        "--mode",
                        "greenfield",
                        "--phase",
                        "readiness",
                        "--strict",
                    ],
                    check=False,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(
                    installed_readiness.returncode,
                    0,
                    installed_readiness.stdout + installed_readiness.stderr,
                )
                installed_agents_help = subprocess.run(
                    [
                        sys.executable,
                        str(target / "scripts" / "validate_agents_md.py"),
                        "--help",
                    ],
                    check=False,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(
                    installed_agents_help.returncode,
                    0,
                    installed_agents_help.stdout + installed_agents_help.stderr,
                )


if __name__ == "__main__":
    unittest.main()

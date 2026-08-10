from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "skills" / "vibe-coding" / "scripts" / "validate_delivery.py"
INSTALLER = REPO_ROOT / "scripts" / "install_skill.py"


def doc(title: str, headings: tuple[str, ...], body: str, status: str = "已确认") -> str:
    sections = "\n".join(f"{heading}\n{body}" for heading in headings[1:])
    return f"{title}\n- 文档状态：{status}\n- 更新时间：2026-08-10\n{sections}\n"


GREEN_HEADINGS = (
    "# 架构设计方案", "## 需求与约束", "## 调研与方案比较", "## 目标架构",
    "## 技术选型", "## 目录与模块边界", "## 接口与数据契约", "## 测试与质量策略",
    "## 安全与配置", "## 交付与运行", "## 风险与权衡", "## 验收标准",
)
MIGRATION_HEADINGS = (
    "# 架构迁移方案", "## 当前架构基线", "## 审查发现", "## 外部参考与方案比较",
    "## 目标架构", "## 迁移差距", "## 分阶段迁移", "## 兼容与回滚",
    "## 仓库治理", "## 测试与质量策略", "## 安全与配置", "## 风险与验收",
)
PLAN_HEADINGS = (
    "# 实施任务清单", "## 执行原则", "## 需求追踪", "## 依赖图",
    "## Agent 与 Worktree 计划", "## 任务列表", "## 测试数据计划",
    "## 集成顺序", "## 验收矩阵", "## 提交与回滚",
)
REPORT_HEADINGS = (
    "# 交付验收报告", "## 完成范围", "## 需求追踪结果", "## 最终架构与目录",
    "## Agent、Worktree 与提交", "## 实际验证", "## 正常测试数据",
    "## UI、视觉与交互", "## 安全与配置", "## 仓库治理", "## 已验证",
    "## 未验证", "## 阻塞", "## 外部动作状态", "## 可复现命令",
)


class VibeCodingValidatorTests(unittest.TestCase):
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
        docs = root / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        marker = "F-001 F-001-AC-01" if mode == "greenfield" else "AUD-001"
        headings = GREEN_HEADINGS if mode == "greenfield" else MIGRATION_HEADINGS
        filename = "架构设计方案.md" if mode == "greenfield" else "架构迁移方案.md"
        docs.joinpath(filename).write_text(
            doc(
                headings[0],
                headings,
                f"{marker}：该章节包含足够具体的架构、测试、安全和回滚证据。",
            ),
            encoding="utf-8",
        )
        if mode == "greenfield":
            docs.joinpath("PRD需求文档.md").write_text(
                "# PRD需求文档\n- 文档状态：已确认\n## 功能详细设计\n"
                "### F-001 账号创建\n#### 验收标准\n- `F-001-AC-01` 创建账号成功。\n",
                encoding="utf-8",
            )

    def task_block(
        self, marker: str, status: str = "待开始", commit: str = "待生成"
    ) -> str:
        return textwrap.dedent(
            f"""
            ### TASK-001 账号创建
            - 状态：{status}
            - 需求/验收/Finding：{marker}
            - 目标：完成可独立验收的账号创建功能。
            - 第一条失败测试：test_account_creation
            - 正常测试数据：factory 创建隔离普通用户并自动清理。
            - 验证命令：python -m unittest
            - 提交边界：账号创建实现及其必要测试。
            - Commit：{commit}
            - 回滚：revert 本任务 commit。
            - 完成条件：主流程和错误路径均通过自动化测试。
            """
        ).strip()

    def write_plan(
        self, root: Path, marker: str, status: str = "待开始", commit: str = "待生成"
    ) -> None:
        body = "该章节包含完整、可执行且可复核的任务、数据、测试、集成与回滚说明。"
        text = doc(PLAN_HEADINGS[0], PLAN_HEADINGS, body)
        text = text.replace("## 需求追踪\n" + body, f"## 需求追踪\n{marker} -> TASK-001")
        text = text.replace(
            "## 任务列表\n" + body,
            "## 任务列表\n" + self.task_block(marker, status, commit),
        )
        (root / "docs" / "实施任务清单.md").write_text(text, encoding="utf-8")

    def write_report(self, root: Path, marker: str, commit: str) -> None:
        body = f"{marker}、TASK-001 与 commit {commit} 已由真实命令和测试证据完成验证。"
        (root / "docs" / "交付验收报告.md").write_text(
            doc(REPORT_HEADINGS[0], REPORT_HEADINGS, body, status="已完成"),
            encoding="utf-8",
        )

    def test_greenfield_plan_passes_and_missing_traceability_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "greenfield")
            self.write_plan(root, "F-001 F-001-AC-01")
            passed = self.run_validator(root, "greenfield", "plan")
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            plan = root / "docs" / "实施任务清单.md"
            plan.write_text(
                plan.read_text().replace("F-001-AC-01", "F-001-AC-99"),
                encoding="utf-8",
            )
            failed = self.run_validator(root, "greenfield", "plan")
            self.assertEqual(failed.returncode, 1)
            self.assertIn("PRD_TRACEABILITY", failed.stdout)

    def test_migration_plan_requires_audit_traceability(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_architecture(root, "migration")
            self.write_plan(root, "AUD-001")
            passed = self.run_validator(root, "migration", "plan")
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            plan = root / "docs" / "实施任务清单.md"
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
            path = root / "docs" / "架构设计方案.md"
            path.write_text(path.read_text() + "\nTODO\n", encoding="utf-8")
            result = self.run_validator(root, "greenfield", "architecture")
            self.assertEqual(result.returncode, 1)
            self.assertIn("PLACEHOLDER", result.stdout)

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
            (root / "app.txt").write_text("implemented\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "initial implementation"],
                check=True,
            )
            sha = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "--short", "HEAD"], text=True
            ).strip()
            self.write_plan(root, "F-001 F-001-AC-01", "已完成", sha)
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
            plan = root / "docs" / "实施任务清单.md"
            plan.write_text(
                plan.read_text().replace(sha, "deadbee"), encoding="utf-8"
            )
            failed = self.run_validator(root, "greenfield", "delivery")
            self.assertIn("TASK_COMMIT_UNKNOWN", failed.stdout)

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
                self.assertTrue(target.joinpath("scripts", "validate_delivery.py").is_file())
                self.assertTrue(target.joinpath("scripts", "validate_prd.py").is_file())
                self.assertFalse(target.joinpath("scripts", "validate_prd.py").is_symlink())
                self.assertFalse(target.joinpath("prompts", "reviewer.agent.md").is_symlink())
                self.assertEqual(target.joinpath("agents").exists(), platform == "codex")


if __name__ == "__main__":
    unittest.main()

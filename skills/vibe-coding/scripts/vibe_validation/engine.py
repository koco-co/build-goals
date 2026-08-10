"""Validation orchestration for architecture, plan, and delivery phases."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .documents import (
    ARCHITECTURE_HEADINGS,
    ARCHITECTURE_PATHS,
    PLAN_HEADINGS,
    PLAN_PATH,
    PRD_PATH,
    REPORT_HEADINGS,
    REPORT_PATH,
    read_required,
    validate_headings,
    validate_placeholders,
    validate_status,
    validate_substantive_sections,
)
from .model import Issue, Report
from .repository import validate_clean_git, validate_tracked_secrets
from .traceability import validate_report_tasks, validate_tasks, validate_traceability


def _validate_document(
    text: str,
    path: Path,
    headings: tuple[str, ...],
    status: str,
    root: Path,
    issues: list[Issue],
) -> None:
    validate_headings(text, headings, path, root, issues)
    validate_status(text, status, path, root, issues)
    validate_placeholders(text, path, root, issues)


def validate_project(
    project_root: Path,
    mode: str,
    phase: str,
    require_clean: bool = False,
) -> Report:
    root = project_root.expanduser().resolve()
    issues: list[Issue] = []
    if not root.is_dir():
        issues.append(Issue("error", "PROJECT_ROOT", str(root), "项目根目录不存在。"))
        return Report(str(root), mode, phase, issues)

    architecture_path = root / ARCHITECTURE_PATHS[mode]
    architecture_text = read_required(architecture_path, root, issues)
    if architecture_text is not None:
        _validate_document(
            architecture_text,
            architecture_path,
            ARCHITECTURE_HEADINGS[mode],
            "已确认",
            root,
            issues,
        )
        validate_substantive_sections(
            architecture_text,
            ("## 目标架构", "## 测试与质量策略", "## 安全与配置"),
            architecture_path,
            root,
            issues,
        )

    if mode == "greenfield":
        source_path = root / PRD_PATH
        source_text = read_required(source_path, root, issues)
    else:
        source_path = architecture_path
        source_text = architecture_text

    plan_text: Optional[str] = None
    tasks = []
    if phase in {"plan", "delivery"}:
        plan_path = root / PLAN_PATH
        plan_text = read_required(plan_path, root, issues)
        if plan_text is not None:
            _validate_document(plan_text, plan_path, PLAN_HEADINGS, "已确认", root, issues)
            validate_substantive_sections(
                plan_text,
                ("## 测试数据计划", "## 验收矩阵"),
                plan_path,
                root,
                issues,
            )
            tasks = validate_tasks(plan_text, plan_path, root, issues, phase == "delivery")
            if source_text is not None:
                validate_traceability(
                    mode,
                    source_text,
                    plan_text,
                    None,
                    plan_path,
                    root / REPORT_PATH,
                    root,
                    issues,
                )

    if phase == "delivery":
        report_path = root / REPORT_PATH
        report_text = read_required(report_path, root, issues)
        if report_text is not None:
            _validate_document(report_text, report_path, REPORT_HEADINGS, "已完成", root, issues)
            validate_substantive_sections(
                report_text,
                (
                    "## 需求追踪结果",
                    "## 实际验证",
                    "## 正常测试数据",
                    "## 安全与配置",
                    "## 已验证",
                    "## 未验证",
                    "## 阻塞",
                    "## 外部动作状态",
                ),
                report_path,
                root,
                issues,
                minimum=8,
            )
            validate_report_tasks(tasks, report_text, report_path, root, issues)
            if source_text is not None and plan_text is not None:
                validate_traceability(
                    mode,
                    source_text,
                    plan_text,
                    report_text,
                    root / PLAN_PATH,
                    report_path,
                    root,
                    issues,
                )
        validate_tracked_secrets(root, issues)
        if require_clean:
            validate_clean_git(root, issues)

    return Report(str(root), mode, phase, issues)

"""Validation orchestration for architecture, plan, readiness, and delivery."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from validate_prd import PackageSnapshot, load_validated_snapshot

from .agent_instructions import validate_agent_documents, validate_agent_readiness
from .documents import (
    ARCHITECTURE_DOMAIN_DIRS,
    ARCHITECTURE_HEADINGS,
    ARCHITECTURE_PATHS,
    DOMAIN_ARCHITECTURE_HEADINGS,
    DOMAIN_PLAN_HEADINGS,
    DOMAIN_REPORT_HEADINGS,
    PLAN_DOMAIN_DIR,
    PLAN_HEADINGS,
    PLAN_PATH,
    REPORT_DOMAIN_DIR,
    REPORT_HEADINGS,
    REPORT_PATH,
    REQUIREMENTS_MODES,
    REQUIREMENTS_PATH,
    discover_domain_names,
    domain_document_paths,
    read_required,
    validate_headings,
    validate_legacy_document_paths,
    validate_placeholders,
    validate_route_metadata,
    validate_status,
    validate_substantive_sections,
)
from .foundation import validate_foundation_readiness
from .model import Issue, Report, add_issue
from .repository import (
    validate_clean_git,
    validate_completed_worktrees,
    validate_no_feature_worktrees_before_readiness,
    validate_tracked_secrets,
)
from .traceability import validate_report_tasks, validate_tasks, validate_traceability

MIGRATION_FINDINGS_PATH = Path("docs/架构迁移/审查发现.yaml")


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


def _load_requirements(
    root: Path, issues: list[Issue]
) -> tuple[Optional[PackageSnapshot], Optional[str]]:
    snapshot, report = load_validated_snapshot(root)
    for item in report.issues:
        suffix = f"（第 {item.line} 行）" if item.line is not None else ""
        add_issue(
            issues,
            "error",
            "REQUIREMENTS_PACKAGE",
            root / REQUIREMENTS_PATH,
            f"{item.code}: {item.message}{suffix}",
            root,
        )
    if snapshot is None:
        return None, None

    source_parts = [(snapshot.root / "PRD需求文档.md").read_text(encoding="utf-8")]
    source_parts.extend(
        (snapshot.root / domain.requirements).read_text(encoding="utf-8")
        for domain in snapshot.domains
    )
    source_parts.extend(
        (snapshot.root / domain.examples).read_text(encoding="utf-8")
        for domain in snapshot.domains
    )
    behavior_index = snapshot.root / "行为样例" / "产品行为样例集.yaml"
    if behavior_index.is_file():
        source_parts.append(behavior_index.read_text(encoding="utf-8"))
    return snapshot, "\n\n".join(source_parts)


def _read_domain_documents(
    directory: Path,
    names: list[str],
    title_prefix: str,
    headings: tuple[str, ...],
    status: str,
    root: Path,
    issues: list[Issue],
) -> list[tuple[Path, str]]:
    documents: list[tuple[Path, str]] = []
    for path in domain_document_paths(directory, names, root, issues):
        text = read_required(path, root, issues)
        if text is None:
            continue
        _validate_document(text, path, (f"# {title_prefix}{path.stem}", *headings), status, root, issues)
        documents.append((path, text))
    return documents


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
    if mode not in ARCHITECTURE_PATHS:
        issues.append(Issue("error", "PROJECT_MODE", str(root), "项目路线无效。"))
        return Report(str(root), mode, phase, issues)

    validate_legacy_document_paths(root, issues)

    snapshot: Optional[PackageSnapshot] = None
    requirement_source: Optional[str] = None
    if mode in REQUIREMENTS_MODES:
        snapshot, requirement_source = _load_requirements(root, issues)

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
        validate_route_metadata(architecture_text, mode, architecture_path, root, issues)
        validate_substantive_sections(
            architecture_text,
            ("## 目标架构", "## 测试与质量策略", "## 安全与配置"),
            architecture_path,
            root,
            issues,
        )

    architecture_domain_dir = root / ARCHITECTURE_DOMAIN_DIRS[mode]
    if snapshot is not None:
        domain_names = [domain.name for domain in snapshot.domains]
    else:
        domain_names = discover_domain_names(architecture_domain_dir, root, issues)
    _read_domain_documents(
        architecture_domain_dir,
        domain_names,
        "功能域架构：",
        DOMAIN_ARCHITECTURE_HEADINGS,
        "已确认",
        root,
        issues,
    )

    if mode == "migration":
        findings_path = root / MIGRATION_FINDINGS_PATH
        source_text = read_required(findings_path, root, issues)
    else:
        source_text = requirement_source

    plan_text: Optional[str] = None
    trace_plan_text: Optional[str] = None
    tasks = []
    if phase in {"plan", "readiness", "delivery"}:
        plan_path = root / PLAN_PATH
        plan_text = read_required(plan_path, root, issues)
        if plan_text is not None:
            _validate_document(plan_text, plan_path, PLAN_HEADINGS, "已确认", root, issues)
            validate_substantive_sections(
                plan_text,
                ("## 配套 Skill 计划", "## 测试数据计划", "## 验收矩阵"),
                plan_path,
                root,
                issues,
            )

        plan_domains = _read_domain_documents(
            root / PLAN_DOMAIN_DIR,
            domain_names,
            "功能域实施任务：",
            DOMAIN_PLAN_HEADINGS,
            "已确认",
            root,
            issues,
        )
        domain_plan_text = "\n\n".join(text for _path, text in plan_domains)
        if domain_plan_text:
            task_path = plan_domains[0][0] if len(plan_domains) == 1 else root / PLAN_DOMAIN_DIR
            tasks = validate_tasks(domain_plan_text, task_path, root, issues, phase == "delivery")
        trace_plan_text = domain_plan_text or None
        if source_text is not None and trace_plan_text:
            validate_traceability(
                mode,
                source_text,
                trace_plan_text,
                None,
                root / PLAN_PATH,
                root / REPORT_PATH,
                root,
                issues,
            )

    if phase in {"readiness", "delivery"} and plan_text is not None:
        validate_foundation_readiness(root, plan_text, issues)
        validate_agent_readiness(root, plan_text, issues, phase=phase)
        validate_agent_documents(root, issues)

    if phase == "readiness":
        validate_no_feature_worktrees_before_readiness(root, plan_text or "", issues)
        if require_clean:
            validate_clean_git(root, issues)

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
                    "## 配套 Skill 生命周期",
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

        report_domains = _read_domain_documents(
            root / REPORT_DOMAIN_DIR,
            domain_names,
            "功能域交付验收：",
            DOMAIN_REPORT_HEADINGS,
            "已完成",
            root,
            issues,
        )
        domain_report_text = "\n\n".join(text for _path, text in report_domains)
        trace_report_text = domain_report_text or report_text or ""
        if trace_report_text:
            validate_report_tasks(
                tasks,
                trace_report_text,
                report_domains[0][0] if len(report_domains) == 1 else report_path,
                root,
                issues,
            )
        if source_text is not None and trace_plan_text and trace_report_text:
            validate_traceability(
                mode,
                source_text,
                trace_plan_text,
                trace_report_text,
                root / PLAN_PATH,
                report_path,
                root,
                issues,
            )
        validate_tracked_secrets(root, issues)
        validate_completed_worktrees(root, tasks, issues)
        if require_clean:
            validate_clean_git(root, issues)

    return Report(str(root), mode, phase, issues)

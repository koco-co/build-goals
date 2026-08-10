"""Markdown contract validation."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Optional

from .model import Issue, add_issue

ARCHITECTURE_PATHS = {
    "greenfield": Path("docs/架构设计方案.md"),
    "migration": Path("docs/架构迁移方案.md"),
}
PLAN_PATH = Path("docs/实施任务清单.md")
REPORT_PATH = Path("docs/交付验收报告.md")
PRD_PATH = Path("docs/PRD需求文档.md")

ARCHITECTURE_HEADINGS = {
    "greenfield": (
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
    ),
    "migration": (
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
    ),
}
PLAN_HEADINGS = (
    "# 实施任务清单",
    "## 执行原则",
    "## 需求追踪",
    "## 依赖图",
    "## Agent 与 Worktree 计划",
    "## 任务列表",
    "## 测试数据计划",
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
    "## 仓库治理",
    "## 已验证",
    "## 未验证",
    "## 阻塞",
    "## 外部动作状态",
    "## 可复现命令",
)
PLACEHOLDERS = (
    (re.compile(r"\{\{[^{}\n]+\}\}"), "模板占位符"),
    (re.compile(r"(?i)\bTODO\b"), "TODO"),
    (re.compile(r"(?i)\bTBD\b"), "TBD"),
    (re.compile(r"待确认|待补充"), "未完成标记"),
    (re.compile(r"(?i)(?<![A-Za-z])xxx(?![A-Za-z])"), "xxx 占位"),
)


def read_required(path: Path, root: Path, issues: list[Issue]) -> Optional[str]:
    if not path.is_file():
        add_issue(issues, "error", "FILE_REQUIRED", path, "缺少必需文件。", root)
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        add_issue(issues, "error", "FILE_READ", path, f"无法以 UTF-8 读取：{exc}", root)
        return None


def validate_headings(
    text: str,
    required: Iterable[str],
    path: Path,
    root: Path,
    issues: list[Issue],
) -> None:
    required_tuple = tuple(required)
    positions: list[int] = []
    for heading in required_tuple:
        matches = list(re.finditer(rf"(?m)^{re.escape(heading)}\s*$", text))
        if not matches:
            add_issue(
                issues,
                "error",
                "HEADING_REQUIRED",
                path,
                f"缺少章节 {heading!r}。",
                root,
            )
            continue
        if len(matches) > 1:
            add_issue(
                issues,
                "error",
                "HEADING_DUPLICATE",
                path,
                f"章节 {heading!r} 出现多次。",
                root,
            )
        positions.append(matches[0].start())
    if len(positions) == len(required_tuple) and positions != sorted(positions):
        add_issue(
            issues, "error", "HEADING_ORDER", path, "核心章节顺序不符合模板契约。", root
        )


def validate_status(
    text: str,
    expected: str,
    path: Path,
    root: Path,
    issues: list[Issue],
) -> None:
    if not re.search(rf"(?m)^-\s*文档状态：{re.escape(expected)}\s*$", text):
        add_issue(
            issues,
            "error",
            "DOCUMENT_STATUS",
            path,
            f"文档必须包含“文档状态：{expected}”。",
            root,
        )


def validate_placeholders(
    text: str, path: Path, root: Path, issues: list[Issue]
) -> None:
    for pattern, label in PLACEHOLDERS:
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            add_issue(
                issues,
                "error",
                "PLACEHOLDER",
                path,
                f"第 {line} 行包含 {label}。",
                root,
            )


def section_body(text: str, heading: str) -> Optional[str]:
    match = re.search(rf"(?m)^{re.escape(heading)}\s*$", text)
    if not match:
        return None
    start = match.end()
    next_heading = re.search(r"(?m)^#{1,2}\s+.+$", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()


def validate_substantive_sections(
    text: str,
    headings: Iterable[str],
    path: Path,
    root: Path,
    issues: list[Issue],
    minimum: int = 20,
) -> None:
    for heading in headings:
        body = section_body(text, heading)
        if body is not None and len(re.sub(r"\s+", "", body)) < minimum:
            add_issue(
                issues,
                "error",
                "SECTION_EMPTY",
                path,
                f"章节 {heading!r} 内容不足。",
                root,
            )

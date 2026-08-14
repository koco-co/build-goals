"""Markdown contract validation."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Optional

from .model import Issue, add_issue

ARCHITECTURE_PATHS = {
    "greenfield": Path("docs/架构设计/架构设计方案.md"),
    "continuation": Path("docs/架构设计/架构设计方案.md"),
    "migration": Path("docs/架构迁移/架构迁移方案.md"),
}
ARCHITECTURE_DOMAIN_DIRS = {
    "greenfield": Path("docs/架构设计/功能域"),
    "continuation": Path("docs/架构设计/功能域"),
    "migration": Path("docs/架构迁移/功能域"),
}
PLAN_PATH = Path("docs/实施任务/实施任务清单.md")
PLAN_DOMAIN_DIR = Path("docs/实施任务/功能域")
REPORT_PATH = Path("docs/交付验收/交付验收报告.md")
REPORT_DOMAIN_DIR = Path("docs/交付验收/功能域")
REQUIREMENTS_PATH = Path("docs/产品需求")
REQUIREMENTS_MODES = {"greenfield", "continuation"}
LEGACY_DOCUMENT_PATHS = (
    Path("docs/PRD需求文档.md"),
    Path("docs/架构设计方案.md"),
    Path("docs/架构迁移方案.md"),
    Path("docs/实施任务清单.md"),
    Path("docs/交付验收报告.md"),
)

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
        "## 交付与运行",
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
ARCHITECTURE_HEADINGS["continuation"] = ARCHITECTURE_HEADINGS["greenfield"]
DOMAIN_ARCHITECTURE_HEADINGS = (
    "## 功能域边界",
    "## 需求映射",
    "## 组件与依赖",
    "## 接口与数据契约",
    "## 验证策略",
)
PLAN_HEADINGS = (
    "# 实施任务清单",
    "## 执行原则",
    "## 需求追踪",
    "## 依赖图",
    "## Agent 与 Worktree 计划",
    "## 任务列表",
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
    "## 实际验证",
    "## 仓库治理",
    "## 已验证",
    "## 未验证",
    "## 阻塞",
    "## 外部动作状态",
    "## 可复现命令",
)
DOMAIN_PLAN_HEADINGS = (
    "## 功能域目标",
    "## 输入与依赖",
    "## 任务列表",
    "## 功能域验证",
    "## 集成与回滚",
)
DOMAIN_REPORT_HEADINGS = (
    "## 完成范围",
    "## 需求与任务追踪",
    "## 实际验证",
    "## 未验证与阻塞",
    "## 集成结果",
)
PLACEHOLDERS = (
    (re.compile(r"\{\{[^{}\n]+\}\}"), "模板占位符"),
    (re.compile(r"(?i)\bTODO\b"), "TODO"),
    (re.compile(r"(?i)\bTBD\b"), "TBD"),
    (re.compile(r"待确认|待补充"), "未完成标记"),
    (re.compile(r"(?i)(?<![A-Za-z])xxx(?![A-Za-z])"), "xxx 占位"),
)


def read_required(path: Path, root: Path, issues: list[Issue]) -> Optional[str]:
    if path.is_symlink():
        add_issue(
            issues,
            "error",
            "DOCUMENT_SYMLINK",
            path,
            "交付文档必须是项目内普通文件，不能是符号链接。",
            root,
        )
        return None
    if not path.is_file():
        add_issue(issues, "error", "FILE_REQUIRED", path, "缺少必需文件。", root)
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        add_issue(issues, "error", "FILE_READ", path, f"无法以 UTF-8 读取：{exc}", root)
        return None


def validate_legacy_document_paths(root: Path, issues: list[Issue]) -> None:
    for relative in LEGACY_DOCUMENT_PATHS:
        path = root / relative
        if path.exists() or path.is_symlink():
            add_issue(
                issues,
                "error",
                "LEGACY_DOCUMENT_PATH",
                path,
                "旧的 docs 根目录产物路径已停用；请迁移到对应的文档族目录。",
                root,
            )


def domain_document_paths(
    directory: Path,
    names: Iterable[str],
    root: Path,
    issues: list[Issue],
) -> list[Path]:
    """Resolve an exact domain document set and reject undeclared Markdown files."""

    expected = {f"{name}.md" for name in names}
    paths: list[Path] = []
    for filename in sorted(expected):
        path = directory / filename
        if path.is_symlink() or not path.is_file():
            add_issue(
                issues,
                "error",
                "DOMAIN_DOCUMENT_REQUIRED",
                path,
                "缺少功能域普通文档，或该路径是符号链接。",
                root,
            )
        else:
            paths.append(path)
    if directory.is_dir():
        for path in sorted(directory.glob("*.md")):
            if path.name not in expected:
                add_issue(
                    issues,
                    "error",
                    "DOMAIN_DOCUMENT_UNDECLARED",
                    path,
                    "功能域文档未出现在当前已确认的功能域集合中。",
                    root,
                )
    return paths


def discover_domain_names(
    directory: Path, root: Path, issues: list[Issue]
) -> list[str]:
    if not directory.is_dir():
        add_issue(
            issues,
            "error",
            "DOMAIN_DOCUMENT_REQUIRED",
            directory,
            "至少需要一个功能域文档。",
            root,
        )
        return []
    names: list[str] = []
    for path in sorted(directory.glob("*.md")):
        if path.is_symlink() or not path.is_file():
            add_issue(
                issues,
                "error",
                "DOMAIN_DOCUMENT_REQUIRED",
                path,
                "功能域文档必须是普通文件。",
                root,
            )
            continue
        names.append(path.stem)
    if not names:
        add_issue(
            issues,
            "error",
            "DOMAIN_DOCUMENT_REQUIRED",
            directory,
            "至少需要一个功能域 Markdown 文档。",
            root,
        )
    return names


def validate_route_metadata(
    text: str, mode: str, path: Path, root: Path, issues: list[Issue]
) -> None:
    def field(label: str) -> Optional[str]:
        match = re.search(
            rf"(?m)^-[ \t]*{re.escape(label)}：[ \t]*(.*?)[ \t]*$", text
        )
        return match.group(1).strip() if match else None

    route = field("项目路线")
    reference = field("旧项目参考")
    scope = field("允许参考范围")
    if mode == "greenfield":
        if route != "新项目":
            add_issue(
                issues,
                "error",
                "PROJECT_ROUTE",
                path,
                "项目路线必须是“新项目”。",
                root,
            )
        if reference not in {"不参考", "按用户指定范围"}:
            add_issue(
                issues,
                "error",
                "REFERENCE_POLICY",
                path,
                "新项目必须明确不参考旧项目，或仅按用户指定范围参考。",
                root,
            )
        if reference == "按用户指定范围" and (not scope or scope.startswith("N/A")):
            add_issue(
                issues,
                "error",
                "REFERENCE_SCOPE",
                path,
                "参考旧项目时必须写明用户授权的具体范围。",
                root,
            )
    elif mode == "continuation":
        if route != "现有项目续建":
            add_issue(
                issues,
                "error",
                "PROJECT_ROUTE",
                path,
                "项目路线必须是“现有项目续建”。",
                root,
            )
        if reference != "当前项目" or not scope:
            add_issue(
                issues,
                "error",
                "REFERENCE_SCOPE",
                path,
                "续建路线必须明确当前项目及允许读取的范围。",
                root,
            )
    else:
        if route != "现有项目架构或技术栈迁移":
            add_issue(
                issues,
                "error",
                "PROJECT_ROUTE",
                path,
                "迁移路线必须明确为现有项目架构或技术栈迁移。",
                root,
            )
        if reference != "当前项目" or not scope:
            add_issue(
                issues,
                "error",
                "REFERENCE_SCOPE",
                path,
                "迁移路线必须记录已确认的旧项目基线范围。",
                root,
            )
    if mode in REQUIREMENTS_MODES and field("需求快照") != "`docs/产品需求/需求包清单.yaml`":
        add_issue(
            issues,
            "error",
            "REQUIREMENTS_SNAPSHOT",
            path,
            "架构文档必须固定引用项目内的需求包清单快照。",
            root,
        )


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

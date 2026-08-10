#!/usr/bin/env python3
"""Validate the fixed product-only PRD contract for building-prds."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

REQUIRED_HEADINGS = (
    "## 产品定位与范围",
    "## 产品现状与目标",
    "## 功能地图与用户旅程",
    "## 全局交互与文案原则",
    "## 功能详细设计",
    "## 跨功能产品要求",
    "## 设计依据与来源",
)

REQUIRED_FEATURE_HEADINGS = (
    "#### 作用与目标",
    "#### 适用角色、入口与前置条件",
    "#### 用户预输入",
    "#### 交互流程",
    "#### 状态与提示文案",
    "#### 期望输出",
    "#### 异常、边界与恢复",
    "#### 产品质量要求",
    "#### 设计依据",
    "#### 验收标准",
)

INPUT_COLUMNS = (
    "字段或内容",
    "提供者",
    "必填",
    "格式与范围",
    "默认值",
    "校验规则",
    "正确示例",
    "错误示例",
)

OUTPUT_COLUMNS = (
    "输出内容",
    "呈现形式",
    "触发条件",
    "排序或状态",
    "用户后续动作",
    "完整示例",
)

COPY_COLUMNS = ("状态", "触发条件", "最终文案", "后续动作")

FEATURE_RE = re.compile(r"(?m)^###\s+(F-\d{3})\s+(.+?)\s*$")
AC_RE = re.compile(r"`(F-\d{3}-AC-\d{2})`")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
URL_RE = re.compile(r"https://[^\s|]+")

UNRESOLVED_RE = re.compile(
    r"\b(?:TODO|TBD|TBC|FIXME)\b"
    r"|待确认|待定|开放问题|未决项|阻塞项|未知项|假设[：:\s]"
)
PLACEHOLDER_RE = re.compile(r"\{\{[^}\n]+\}\}|\[\s*(?:待填写|填写)\s*\]")
TECHNICAL_HEADING_RE = re.compile(
    r"(?m)^#{1,6}\s*(?:技术架构|系统架构|技术栈|技术选型|数据库设计|"
    r"API\s*设计|接口设计|部署方案|运维方案|工程实现|实现方案|任务拆解)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    line: Optional[int] = None


@dataclass
class Report:
    path: str
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return self.issues

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "status": "pass" if not self.errors else "fail",
            "error_count": len(self.errors),
            "issues": [asdict(issue) for issue in self.issues],
        }


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def add_issue(
    issues: list[Issue],
    code: str,
    message: str,
    *,
    text: Optional[str] = None,
    offset: Optional[int] = None,
) -> None:
    line = None
    if text is not None and offset is not None:
        line = line_number(text, offset)
    issues.append(Issue(code=code, message=message, line=line))


def subsection(section: str, heading: str) -> str:
    match = re.search(rf"(?m)^{re.escape(heading)}\s*$", section)
    if match is None:
        return ""
    tail = section[match.end() :]
    next_heading = re.search(r"(?m)^####\s+", tail)
    return tail[: next_heading.start()] if next_heading else tail


def has_markdown_columns(section: str, columns: Iterable[str]) -> bool:
    return any(
        line.lstrip().startswith("|") and all(column in line for column in columns)
        for line in section.splitlines()
    )


def validate_path(path: Path, issues: list[Issue]) -> None:
    if path.name != "PRD需求文档.md" or path.parent.name != "docs":
        add_issue(
            issues,
            "OUTPUT_PATH",
            "PRD 必须位于当前项目的 docs/PRD需求文档.md。",
        )


def validate_document_structure(text: str, issues: list[Issue]) -> None:
    title_matches = list(re.finditer(r"(?m)^# PRD需求文档\s*$", text))
    if len(title_matches) != 1:
        add_issue(
            issues,
            "TITLE",
            f"主标题必须且只能出现一次；实际出现 {len(title_matches)} 次。",
        )

    if not re.search(r"(?m)^- 文档状态：已确认\s*$", text):
        add_issue(issues, "DOCUMENT_STATUS", "文档状态必须明确为“已确认”。")

    positions: list[int] = []
    for heading in REQUIRED_HEADINGS:
        matches = list(re.finditer(rf"(?m)^{re.escape(heading)}\s*$", text))
        if not matches:
            add_issue(issues, "HEADING_REQUIRED", f"缺少必需章节：{heading}")
            continue
        if len(matches) > 1:
            add_issue(
                issues,
                "HEADING_DUPLICATE",
                f"必需章节重复：{heading}",
                text=text,
                offset=matches[1].start(),
            )
        positions.append(matches[0].start())

    if len(positions) == len(REQUIRED_HEADINGS) and positions != sorted(positions):
        add_issue(issues, "HEADING_ORDER", "必需章节顺序不符合 PRD 模板。")


def validate_prohibited_content(text: str, issues: list[Issue]) -> None:
    for match in UNRESOLVED_RE.finditer(text):
        add_issue(
            issues,
            "UNRESOLVED_CONTENT",
            f"发现未确定内容标记：{match.group(0)!r}。",
            text=text,
            offset=match.start(),
        )

    for match in PLACEHOLDER_RE.finditer(text):
        add_issue(
            issues,
            "PLACEHOLDER_CONTENT",
            "发现尚未替换的模板占位内容。",
            text=text,
            offset=match.start(),
        )

    for match in TECHNICAL_HEADING_RE.finditer(text):
        add_issue(
            issues,
            "TECHNICAL_SECTION",
            f"PRD 不允许技术实现章节：{match.group(0).strip()}。",
            text=text,
            offset=match.start(),
        )


def feature_sections(text: str) -> list[tuple[re.Match[str], str]]:
    matches = list(FEATURE_RE.finditer(text))
    cross_feature = re.search(r"(?m)^## 跨功能产品要求\s*$", text)
    boundary = cross_feature.start() if cross_feature else len(text)
    sections: list[tuple[re.Match[str], str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else boundary
        sections.append((match, text[match.start() : end]))
    return sections


def validate_features(text: str, issues: list[Issue]) -> None:
    sections = feature_sections(text)
    if not sections:
        add_issue(issues, "FEATURE_REQUIRED", "功能详细设计至少需要一项 F-NNN 功能。")
        return

    seen_features: set[str] = set()
    seen_acceptance: set[str] = set()

    for match, section in sections:
        feature_id = match.group(1)
        if feature_id in seen_features:
            add_issue(
                issues,
                "FEATURE_ID_DUPLICATE",
                f"功能编号重复：{feature_id}。",
                text=text,
                offset=match.start(),
            )
        seen_features.add(feature_id)

        for heading in REQUIRED_FEATURE_HEADINGS:
            if not re.search(rf"(?m)^{re.escape(heading)}\s*$", section):
                add_issue(
                    issues,
                    "FEATURE_SECTION_REQUIRED",
                    f"{feature_id} 缺少子章节：{heading}。",
                    text=text,
                    offset=match.start(),
                )

        input_section = subsection(section, "#### 用户预输入")
        if input_section and not has_markdown_columns(input_section, INPUT_COLUMNS):
            add_issue(
                issues,
                "INPUT_TABLE",
                f"{feature_id} 的用户预输入表格缺少规定列。",
                text=text,
                offset=match.start(),
            )

        copy_section = subsection(section, "#### 状态与提示文案")
        if copy_section and not has_markdown_columns(copy_section, COPY_COLUMNS):
            add_issue(
                issues,
                "COPY_TABLE",
                f"{feature_id} 的状态与提示文案表格缺少规定列。",
                text=text,
                offset=match.start(),
            )

        output_section = subsection(section, "#### 期望输出")
        if output_section and not has_markdown_columns(output_section, OUTPUT_COLUMNS):
            add_issue(
                issues,
                "OUTPUT_TABLE",
                f"{feature_id} 的期望输出表格缺少规定列。",
                text=text,
                offset=match.start(),
            )

        acceptance_section = subsection(section, "#### 验收标准")
        acceptance = list(AC_RE.finditer(acceptance_section))
        if not acceptance:
            add_issue(
                issues,
                "AC_REQUIRED",
                f"{feature_id} 至少需要一条关联验收标准。",
                text=text,
                offset=match.start(),
            )
            continue

        for ac_match in acceptance:
            acceptance_id = ac_match.group(1)
            if not acceptance_id.startswith(f"{feature_id}-AC-"):
                add_issue(
                    issues,
                    "AC_FEATURE_MISMATCH",
                    f"{acceptance_id} 不属于 {feature_id}。",
                    text=text,
                    offset=match.start() + ac_match.start(),
                )
            if acceptance_id in seen_acceptance:
                add_issue(
                    issues,
                    "AC_ID_DUPLICATE",
                    f"验收编号重复：{acceptance_id}。",
                    text=text,
                    offset=match.start() + ac_match.start(),
                )
            seen_acceptance.add(acceptance_id)

            line_start = acceptance_section.rfind("\n", 0, ac_match.start()) + 1
            line_end = acceptance_section.find("\n", ac_match.end())
            if line_end == -1:
                line_end = len(acceptance_section)
            acceptance_line = acceptance_section[line_start:line_end]
            if not all(token in acceptance_line for token in ("Given", "When", "Then")):
                add_issue(
                    issues,
                    "AC_FORMAT",
                    f"{acceptance_id} 必须包含 Given、When 和 Then。",
                    text=text,
                    offset=match.start() + ac_match.start(),
                )


def parse_source_rows(text: str) -> list[list[str]]:
    heading = re.search(r"(?m)^## 设计依据与来源\s*$", text)
    if heading is None:
        return []

    rows: list[list[str]] = []
    for line in text[heading.end() :].splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] == "类型":
            continue
        if all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
            continue
        rows.append(cells)
    return rows


def validate_research(text: str, issues: list[Issue]) -> None:
    counts = {"竞品": 0, "开源项目": 0, "官方规范": 0}
    rows = parse_source_rows(text)

    for cells in rows:
        if len(cells) < 5:
            add_issue(issues, "SOURCE_ROW", "调研来源表格的每行必须包含五列。")
            continue

        source_type, name, url, accessed, adopted = cells[:5]
        valid = True
        if source_type not in counts:
            continue
        if not name or not adopted:
            add_issue(
                issues,
                "SOURCE_DETAIL",
                f"{source_type} 来源必须填写名称和具体借鉴点。",
            )
            valid = False
        if URL_RE.fullmatch(url) is None:
            add_issue(
                issues,
                "SOURCE_URL",
                f"{source_type} 来源必须使用可直接访问的 https URL：{url!r}。",
            )
            valid = False
        if DATE_RE.fullmatch(accessed) is None:
            add_issue(
                issues,
                "SOURCE_DATE",
                f"{source_type} 来源必须记录 YYYY-MM-DD 访问日期：{accessed!r}。",
            )
            valid = False
        if valid:
            counts[source_type] += 1

    requirements = {"竞品": 2, "开源项目": 2, "官方规范": 1}
    missing = [
        f"{source_type} {counts[source_type]}/{minimum}"
        for source_type, minimum in requirements.items()
        if counts[source_type] < minimum
    ]
    if missing:
        add_issue(
            issues,
            "RESEARCH_COVERAGE",
            "调研来源未达到最低覆盖：" + "，".join(missing) + "。",
        )


def validate_prd(path: Path) -> Report:
    resolved = path.expanduser().resolve()
    issues: list[Issue] = []
    validate_path(resolved, issues)

    if not resolved.is_file():
        add_issue(issues, "FILE_REQUIRED", f"找不到 PRD 文件：{resolved}")
        return Report(str(resolved), issues)

    try:
        text = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        add_issue(issues, "FILE_READ", f"无法以 UTF-8 读取 PRD：{exc}")
        return Report(str(resolved), issues)

    if not text.strip():
        add_issue(issues, "FILE_EMPTY", "PRD 文件为空。")
        return Report(str(resolved), issues)

    validate_document_structure(text, issues)
    validate_prohibited_content(text, issues)
    validate_features(text, issues)
    validate_research(text, issues)
    return Report(str(resolved), issues)


def print_human(report: Report) -> None:
    for issue in report.issues:
        location = f":{issue.line}" if issue.line is not None else ""
        print(f"ERROR   {issue.code:28} {report.path}{location}: {issue.message}")

    if report.errors:
        print(f"FAIL: {len(report.errors)} error(s) — {report.path}")
    else:
        print(f"PASS: 0 error(s) — {report.path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="校验 building-prds 生成的产品 PRD 路径、结构和确定性要求。"
    )
    parser.add_argument("prd", type=Path, help="目标 docs/PRD需求文档.md")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="保留与其他仓库校验器一致的严格模式接口",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_prd(args.prd)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

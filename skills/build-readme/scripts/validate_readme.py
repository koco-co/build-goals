#!/usr/bin/env python3
"""Validate the deterministic parts of an opinionated GitHub README."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Optional, Sequence

HERO_RE = re.compile(r"\A\s*<div\s+align=[\"']center[\"']\s*>", re.IGNORECASE)
TITLE_RE = re.compile(r"(?m)^#\s+(.+?)\s*$")
TAGLINE_RE = re.compile(
    r"<p\s+align=[\"']center[\"']\s*>\s*<(?P<tag>i|em)>"
    r"(?P<content>.+?)</(?P=tag)>\s*</p>",
    re.IGNORECASE | re.DOTALL,
)
HTML_HEADING_RE = re.compile(r"<h([2-6])\b([^>]*)>(.*?)</h\1>", re.I | re.S)
MARKDOWN_HEADING_RE = re.compile(r"(?m)^#{2,6}\s+\S")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[^)]*)?\)")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+[^)]*)?\)")
BADGE_LINK_RE = re.compile(
    r"\[!\[[^\]]*\]\([^)]+\)\]\(([^)\s]+)(?:\s+[^)]*)?\)"
)
HTML_REF_RE = re.compile(r"<(?:img|a)\b[^>]*?\b(?:src|href)=[\"']([^\"']+)[\"']", re.I)
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*>", re.I)
ANCHOR_RE = re.compile(r"<a\s+id=[\"']([^\"']+)[\"']\s*>\s*</a>", re.I)
MERMAID_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.I | re.S)
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|TBD|FIXME|XXX)\b|\{\{[^}\n]+\}\}|\[\s*(?:待填写|填写)\s*\]",
    re.IGNORECASE,
)
BODY_BOLD_RE = re.compile(
    r"(?<!\*)\*\*[^*\n]+\*\*(?!\*)|(?<!_)__[^_\n]+__(?!_)"
)
HTML_BOLD_RE = re.compile(r"<(?:strong|b)\b", re.I)
MARKUP_ARTIFACT_RE = re.compile(r"(?mi)^\s*(?:[-*+]\s+)?`span`\s*$")
REMOTE_IMAGE_HOSTS = {"img.shields.io"}
TRACKED_HTML_TAGS = {
    "a",
    "b",
    "blockquote",
    "center",
    "code",
    "del",
    "details",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "i",
    "kbd",
    "li",
    "mark",
    "ol",
    "p",
    "pre",
    "s",
    "span",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
SUPPORTED_MERMAID_STARTS = (
    "flowchart ",
    "graph ",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "journey",
    "gantt",
    "pie",
    "mindmap",
    "timeline",
    "quadrantChart",
    "xychart",
    "block-beta",
    "architecture-beta",
)


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    path: str
    line: int
    message: str


@dataclass
class Report:
    readme: str
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    def to_dict(self, *, strict: bool = False) -> dict[str, object]:
        return {
            "readme": self.readme,
            "status": (
                "fail" if self.errors or (strict and self.warnings) else "pass"
            ),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [asdict(issue) for issue in self.issues],
        }


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, max(offset, 0)) + 1


def add_issue(
    issues: list[Issue],
    severity: str,
    code: str,
    path: Path,
    line: int,
    message: str,
) -> None:
    issues.append(Issue(severity, code, str(path), line, message))


class BalancedHTMLParser(HTMLParser):
    """Track GitHub-supported paired HTML tags outside Markdown code."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.problems: list[tuple[int, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, Optional[str]]]
    ) -> None:
        del attrs
        normalized = tag.lower()
        if normalized in TRACKED_HTML_TAGS:
            self.stack.append((normalized, self.getpos()[0]))

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, Optional[str]]]
    ) -> None:
        del tag, attrs

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized not in TRACKED_HTML_TAGS:
            return
        line = self.getpos()[0]
        if not self.stack:
            self.problems.append((line, f"发现多余的 </{normalized}>。"))
            return
        expected, expected_line = self.stack[-1]
        if expected != normalized:
            self.problems.append(
                (
                    line,
                    f"HTML 标签错配：第 {expected_line} 行的 <{expected}> "
                    f"尚未闭合，却遇到 </{normalized}>。",
                )
            )
            return
        self.stack.pop()

    def finish(self) -> None:
        for tag, line in reversed(self.stack):
            self.problems.append((line, f"HTML 标签 <{tag}> 缺少 </{tag}>。"))


def validate_html_balance(text: str, path: Path, issues: list[Issue]) -> None:
    parser = BalancedHTMLParser()
    try:
        parser.feed(mask_code(text))
        parser.close()
    except (ValueError, TypeError) as exc:
        add_issue(
            issues,
            "error",
            "HTML_TAG_MISMATCH",
            path,
            1,
            f"HTML 无法解析：{exc}",
        )
        return
    parser.finish()
    for line, message in parser.problems:
        add_issue(issues, "error", "HTML_TAG_MISMATCH", path, line, message)


def mask_code(text: str) -> str:
    """Replace fenced and inline code with spaces while preserving newlines."""
    output: list[str] = []
    fence: Optional[str] = None
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        marker_match = re.match(r"(```+|~~~+)", stripped)
        if marker_match:
            marker = marker_match.group(1)
            if fence is None:
                fence = marker[0]
            elif marker[0] == fence:
                fence = None
            output.append("\n" if line.endswith("\n") else "")
            continue
        if fence is not None:
            output.append("\n" if line.endswith("\n") else "")
            continue
        masked = re.sub(r"`[^`\n]+`", lambda match: " " * len(match.group(0)), line)
        output.append(masked)
    return "".join(output)


def uses_mathematical_style(value: str, required_style: str) -> bool:
    """Accept non-Latin text, but require one exact style for Latin letters."""
    for character in value:
        if character.isascii() and character.isalpha():
            return False
        name = unicodedata.name(character, "")
        if "MATHEMATICAL" not in name:
            continue
        if "CAPITAL" not in name and "SMALL" not in name:
            continue
        if required_style not in name:
            return False
    return True


def plain_text(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value)


def validate_hero(text: str, path: Path, issues: list[Issue]) -> None:
    if not HERO_RE.search(text):
        add_issue(
            issues,
            "error",
            "HERO_CENTER",
            path,
            1,
            'README 必须以 <div align="center"> 居中首屏开始。',
        )
        return

    closing = text.lower().find("</div>")
    if closing < 0:
        add_issue(issues, "error", "HERO_CLOSE", path, 1, "居中首屏缺少 </div>。")
        hero = text
    else:
        hero = text[: closing + len("</div>")]

    title = TITLE_RE.search(hero)
    if title is None:
        add_issue(issues, "error", "TITLE_REQUIRED", path, 1, "首屏缺少一级项目标题。")
    elif not uses_mathematical_style(title.group(1), "BOLD SCRIPT"):
        add_issue(
            issues,
            "error",
            "TITLE_SCRIPT",
            path,
            line_number(text, title.start()),
            "一级项目标题必须包含 Mathematical Script 花体字形。",
        )

    tagline = TAGLINE_RE.search(hero)
    if "***" in hero or tagline is None:
        add_issue(
            issues,
            "error",
            "TAGLINE_STYLE",
            path,
            1,
            "一句话描述必须使用居中的 <p><i> HTML 结构，不能使用 ***。",
        )
    elif not uses_mathematical_style(
        plain_text(tagline.group("content")), "BOLD ITALIC"
    ):
        add_issue(
            issues,
            "error",
            "TAGLINE_DECORATION",
            path,
            line_number(text, tagline.start()),
            "一句话描述中的拉丁字母必须使用 Mathematical Bold Italic 字形。",
        )

    shield_count = len(re.findall(r"https://img\.shields\.io/", hero, re.I))
    if shield_count < 2:
        add_issue(
            issues,
            "error",
            "SHIELDS_REQUIRED",
            path,
            1,
            f"首屏至少需要 2 枚 Shields；当前发现 {shield_count} 枚。",
        )


def validate_section_anchors(
    body: str,
    body_offset: int,
    full_text: str,
    path: Path,
    issues: list[Issue],
) -> None:
    anchors = list(ANCHOR_RE.finditer(body))
    seen: dict[str, int] = {}
    for anchor in anchors:
        identifier = anchor.group(1)
        normalized = identifier.casefold()
        line = line_number(full_text, body_offset + anchor.start())
        if normalized in seen:
            add_issue(
                issues,
                "error",
                "ANCHOR_DUPLICATE",
                path,
                line,
                f"锚点重复：{identifier}（首次出现在第 {seen[normalized]} 行）。",
            )
        else:
            seen[normalized] = line

    for heading in HTML_HEADING_RE.finditer(body):
        prefix = body[: heading.start()].rstrip()
        anchor = re.search(
            r"<a\s+id=[\"'][^\"']+[\"']\s*>\s*</a>\s*\Z",
            prefix,
            re.I,
        )
        if anchor is None:
            add_issue(
                issues,
                "error",
                "SECTION_ANCHOR_REQUIRED",
                path,
                line_number(full_text, body_offset + heading.start()),
                "每个居中章节标题前必须有稳定且唯一的显式锚点。",
            )


def has_visible_prose(value: str) -> bool:
    without_links = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", value)
    without_tags = re.sub(r"<[^>]+>", "", without_links)
    return bool(re.search(r"[A-Za-z0-9\u3400-\u9fff]", without_tags))


def validate_body_italics(
    body: str,
    body_offset: int,
    full_text: str,
    path: Path,
    issues: list[Issue],
) -> None:
    position = 0
    for line in body.splitlines(keepends=True):
        stripped = line.strip()
        line_offset = body_offset + position
        position += len(line)
        if not stripped:
            continue
        if stripped.startswith(("|", "<!--", "<a ", "<h", "</h", "---")):
            continue
        if re.fullmatch(
            r"</?(?:details|summary|table|thead|tbody|tr|th|td|ul|ol|li|blockquote)>.*",
            stripped,
            re.I,
        ):
            continue

        remaining = re.sub(
            r"<(?:i|em)>.*?</(?:i|em)>", "", stripped, flags=re.I
        )
        if has_visible_prose(remaining):
            add_issue(
                issues,
                "error",
                "BODY_ITALIC",
                path,
                line_number(full_text, line_offset),
                "普通正文和列表说明必须完整使用 <i> 或 <em> 斜体。",
            )
            return


def validate_fences(text: str, path: Path, issues: list[Issue]) -> None:
    active: Optional[tuple[str, int, int]] = None
    for number, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if match is None:
            continue
        marker = match.group(1)
        rest = match.group(2).strip()
        if active is None:
            if not rest:
                add_issue(
                    issues,
                    "error",
                    "FENCE_LANGUAGE_REQUIRED",
                    path,
                    number,
                    "围栏代码块必须声明语言；纯文本使用 text。",
                )
            active = (marker[0], len(marker), number)
            continue
        character, length, _ = active
        if marker[0] == character and len(marker) >= length and not rest:
            active = None
    if active is not None:
        _, _, start = active
        add_issue(
            issues,
            "error",
            "FENCE_UNCLOSED",
            path,
            start,
            "围栏代码块缺少闭合标记。",
        )


def validate_section_style(text: str, path: Path, issues: list[Issue]) -> None:
    masked = mask_code(text)
    hero_end = masked.lower().find("</div>")
    body = masked[hero_end + len("</div>") :] if hero_end >= 0 else masked
    body_offset = hero_end + len("</div>") if hero_end >= 0 else 0

    markdown_heading = MARKDOWN_HEADING_RE.search(body)
    if markdown_heading:
        add_issue(
            issues,
            "error",
            "SECTION_HEADING_STYLE",
            path,
            line_number(masked, body_offset + markdown_heading.start()),
            "二级及以下章节标题必须使用居中的 HTML heading。",
        )

    headings = list(HTML_HEADING_RE.finditer(body))
    if not headings:
        add_issue(
            issues,
            "error",
            "SECTION_REQUIRED",
            path,
            1,
            "README 至少需要一个居中的二级章节标题。",
        )
    for heading in headings:
        attributes = heading.group(2)
        if re.search(r"\balign=[\"']center[\"']", attributes, re.I) is None:
            add_issue(
                issues,
                "error",
                "SECTION_HEADING_STYLE",
                path,
                line_number(masked, body_offset + heading.start()),
                '章节标题必须设置 align="center"。',
            )
        content = plain_text(heading.group(3))
        if not uses_mathematical_style(content, "BOLD ITALIC"):
            add_issue(
                issues,
                "warning",
                "SECTION_DECORATION",
                path,
                line_number(masked, body_offset + heading.start()),
                "英文章节标题应使用 Mathematical Bold Italic 字形。",
            )

    body_without_inline_code = re.sub(r"`[^`\n]+`", "", body)
    bold = BODY_BOLD_RE.search(body_without_inline_code)
    html_bold = HTML_BOLD_RE.search(body_without_inline_code)
    if bold or html_bold:
        match = bold or html_bold
        assert match is not None
        add_issue(
            issues,
            "error",
            "BODY_BOLD",
            path,
            line_number(masked, body_offset + match.start()),
            "正文不能使用 Markdown 或 HTML 粗体。",
        )

    if "<i>" not in body.lower() and "<em>" not in body.lower():
        add_issue(
            issues,
            "warning",
            "BODY_ITALIC",
            path,
            1,
            "正文未发现 HTML 斜体内容。",
        )
    else:
        validate_body_italics(body, body_offset, masked, path, issues)

    original_hero_end = text.lower().find("</div>")
    original_body_offset = (
        original_hero_end + len("</div>") if original_hero_end >= 0 else 0
    )
    original_body = text[original_body_offset:]
    artifact = MARKUP_ARTIFACT_RE.search(original_body)
    if artifact:
        add_issue(
            issues,
            "error",
            "MARKUP_ARTIFACT",
            path,
            line_number(text, original_body_offset + artifact.start()),
            "发现疑似格式转换残留的字面量 `span`。",
        )

    validate_section_anchors(body, body_offset, masked, path, issues)


def discover_project_root(readme: Path, explicit: Optional[Path]) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    current = readme.parent.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def iter_references(text: str) -> Iterable[tuple[str, bool, int]]:
    for match in MARKDOWN_IMAGE_RE.finditer(text):
        yield match.group(2), True, match.start()
    for match in BADGE_LINK_RE.finditer(text):
        yield match.group(1), False, match.start()
    for match in MARKDOWN_LINK_RE.finditer(text):
        yield match.group(2), False, match.start()
    for match in HTML_REF_RE.finditer(text):
        yield match.group(1), match.group(0).lower().startswith("<img"), match.start()


def local_target(reference: str, readme: Path, project_root: Path) -> Optional[Path]:
    if reference.startswith(("#", "http://", "https://", "mailto:", "data:")):
        return None
    parsed = urllib.parse.urlsplit(reference)
    if parsed.scheme or parsed.netloc:
        return None
    raw_path = urllib.parse.unquote(parsed.path)
    if not raw_path:
        return None
    if raw_path.startswith("/"):
        return (project_root / raw_path.lstrip("/")).resolve(strict=False)
    return (readme.parent / raw_path).resolve(strict=False)


def validate_references(
    text: str,
    readme: Path,
    project_root: Path,
    issues: list[Issue],
) -> list[str]:
    remote_urls: list[str] = []
    seen_local: set[Path] = set()
    seen_references: set[tuple[str, bool]] = set()

    for match in MARKDOWN_IMAGE_RE.finditer(text):
        if not match.group(1).strip():
            add_issue(
                issues,
                "error",
                "IMAGE_ALT_REQUIRED",
                readme,
                line_number(text, match.start()),
                "Markdown 图片必须提供非空替代文本。",
            )
    for match in HTML_IMAGE_RE.finditer(text):
        alt = re.search(r"\balt=[\"']([^\"']*)[\"']", match.group(0), re.I)
        if alt is None or not alt.group(1).strip():
            add_issue(
                issues,
                "error",
                "IMAGE_ALT_REQUIRED",
                readme,
                line_number(text, match.start()),
                "HTML 图片必须提供非空 alt 属性。",
            )

    for reference, is_image, offset in iter_references(text):
        key = (reference, is_image)
        if key in seen_references:
            continue
        seen_references.add(key)

        if reference.startswith(("http://", "https://")):
            remote_urls.append(reference)
            if is_image and not is_allowed_remote_image(reference):
                add_issue(
                    issues,
                    "error",
                    "REMOTE_IMAGE_HOTLINK",
                    readme,
                    line_number(text, offset),
                    f"远程图片必须改为仓库内资源；仅 Shields 和 GitHub Actions 徽章例外：{reference}",
                )

        target = local_target(reference, readme, project_root)
        if target is None or target in seen_local:
            continue
        seen_local.add(target)

        try:
            target.relative_to(project_root)
        except ValueError:
            add_issue(
                issues,
                "error",
                "LOCAL_REF_OUTSIDE",
                readme,
                line_number(text, offset),
                f"本地引用越过项目根目录：{reference}",
            )
            continue

        if not target.exists():
            add_issue(
                issues,
                "error",
                "LOCAL_REF_MISSING",
                readme,
                line_number(text, offset),
                f"本地引用不存在：{reference}",
            )
            continue

        if target.suffix.lower() == ".svg" and target.is_file():
            validate_svg(target, issues)
    return remote_urls


def is_allowed_remote_image(reference: str) -> bool:
    parsed = urllib.parse.urlsplit(reference)
    host = parsed.netloc.casefold()
    if host in REMOTE_IMAGE_HOSTS:
        return True
    return (
        host == "github.com"
        and "/actions/workflows/" in parsed.path
        and parsed.path.endswith("/badge.svg")
    )


def validate_svg(target: Path, issues: list[Issue]) -> None:
    try:
        root = ET.parse(target).getroot()
        if not root.tag.lower().endswith("svg"):
            raise ET.ParseError("根元素不是 svg")
    except (ET.ParseError, OSError) as exc:
        add_issue(
            issues,
            "error",
            "SVG_INVALID",
            target,
            1,
            f"SVG 无法解析：{exc}",
        )
        return

    unsafe: list[str] = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1].casefold()
        if tag in {"script", "foreignobject"}:
            unsafe.append(f"禁止元素 <{tag}>")
        for raw_name, raw_value in element.attrib.items():
            name = raw_name.rsplit("}", 1)[-1].casefold()
            value = raw_value.strip().casefold()
            if name.startswith("on"):
                unsafe.append(f"禁止事件属性 {name}")
            if name in {"href", "src"} and value.startswith(
                ("http://", "https://", "//", "javascript:")
            ):
                unsafe.append(f"禁止外部或脚本引用 {raw_value}")
            if name == "style" and re.search(r"url\s*\(\s*(?:https?:|//|javascript:)", value):
                unsafe.append("禁止 style 中的外部或脚本 URL")
    if unsafe:
        add_issue(
            issues,
            "error",
            "SVG_UNSAFE",
            target,
            1,
            "SVG 包含不安全内容：" + "；".join(dict.fromkeys(unsafe)),
        )


def validate_mermaid(text: str, readme: Path, issues: list[Issue]) -> None:
    for match in MERMAID_RE.finditer(text):
        lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
        if not lines or not lines[0].startswith(SUPPORTED_MERMAID_STARTS):
            add_issue(
                issues,
                "error",
                "MERMAID_SYNTAX",
                readme,
                line_number(text, match.start()),
                "Mermaid 代码块缺少受支持的图表类型声明。",
            )


def verify_remote_urls(
    urls: Iterable[str], readme: Path, timeout: float, issues: list[Issue]
) -> None:
    for url in sorted(set(urls)):
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "build-readme-validator/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status >= 400:
                    raise urllib.error.HTTPError(
                        url, response.status, "HTTP error", response.headers, None
                    )
                response.read(1)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            add_issue(
                issues,
                "warning",
                "REMOTE_URL_UNREACHABLE",
                readme,
                1,
                f"远程 URL 无法访问：{url}（{exc}）",
            )


def validate_readme(
    readme: Path,
    *,
    project_root: Optional[Path] = None,
    verify_remote: bool = False,
    timeout: float = 10.0,
) -> Report:
    path = readme.expanduser().resolve()
    issues: list[Issue] = []

    if not path.is_file():
        add_issue(issues, "error", "README_REQUIRED", path, 1, "README 文件不存在。")
        return Report(str(path), issues)

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        add_issue(
            issues, "error", "README_READ", path, 1, f"无法读取 UTF-8 README：{exc}"
        )
        return Report(str(path), issues)

    if not text.strip():
        add_issue(issues, "error", "README_EMPTY", path, 1, "README 为空。")
        return Report(str(path), issues)

    root = discover_project_root(path, project_root)
    validate_hero(text, path, issues)
    validate_section_style(text, path, issues)

    masked = mask_code(text)
    placeholder = PLACEHOLDER_RE.search(masked)
    if placeholder:
        add_issue(
            issues,
            "error",
            "UNRESOLVED_CONTENT",
            path,
            line_number(masked, placeholder.start()),
            f"README 包含未解决占位内容：{placeholder.group(0)}",
        )

    validate_html_balance(text, path, issues)
    validate_fences(text, path, issues)
    remote_urls = validate_references(text, path, root, issues)
    validate_mermaid(text, path, issues)
    if verify_remote:
        verify_remote_urls(remote_urls, path, timeout, issues)
    return Report(str(path), issues)


def print_human(report: Report, *, strict: bool = False) -> None:
    for issue in report.issues:
        print(
            f"{issue.severity.upper():7} {issue.code:28} "
            f"{issue.path}:{issue.line}: {issue.message}"
        )
    if report.errors or (strict and report.warnings):
        print(
            f"FAIL: {len(report.errors)} error(s), "
            f"{len(report.warnings)} warning(s) — {report.readme}"
        )
    else:
        print(f"PASS: 0 error(s), {len(report.warnings)} warning(s) — {report.readme}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="校验 build-readme 生成的 GitHub 风格 README。"
    )
    parser.add_argument("readme", type=Path, help="要校验的 README Markdown 文件")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="项目根目录；省略时从 README 向上寻找 .git",
    )
    parser.add_argument(
        "--verify-remote",
        action="store_true",
        help="联网验证远程链接、图片和 Shields",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="远程请求超时秒数")
    parser.add_argument("--strict", action="store_true", help="将 warning 视为失败")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_readme(
        args.readme,
        project_root=args.project_root,
        verify_remote=args.verify_remote,
        timeout=args.timeout,
    )
    if args.json:
        print(json.dumps(report.to_dict(strict=args.strict), ensure_ascii=False, indent=2))
    else:
        print_human(report, strict=args.strict)
    if report.errors or (args.strict and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate AGENTS.md / CLAUDE.md single-source instruction pairs.

The validator is intentionally dependency-free. It checks deterministic file
structure and local references; it does not try to judge whether project rules
are complete or whether an agent client actually loaded them.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional, Sequence

IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".repos",
    ".ruff_cache",
    ".svn",
    ".turbo",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "venv",
}
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
FENCED_CODE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
PLACEHOLDER_PATTERNS = (
    re.compile(r"\{\{[^}\n]+\}\}"),
    re.compile(
        r"^\s*(?:[-*+]\s*)?(?:TODO|TBD|FIXME|XXX)(?:\s*[:：].*)?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r"\[\s*(?:project[ _-]?name|待填写|填写)\s*\]", re.IGNORECASE),
    re.compile(r"<\s*(?:project[ _-]?name|待填写)\s*>", re.IGNORECASE),
)
REMOTE_SCHEMES = {
    "data",
    "ftp",
    "http",
    "https",
    "mailto",
    "ssh",
    "tel",
}


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    path: str
    message: str


@dataclass
class Report:
    project_root: str
    agents_count: int
    issues: List[Issue]

    @property
    def errors(self) -> List[Issue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    def to_dict(self) -> dict:
        return {
            "project_root": self.project_root,
            "status": "pass" if not self.errors else "fail",
            "agents_count": self.agents_count,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [asdict(issue) for issue in self.issues],
        }


def display_path(path: Path, root: Path) -> str:
    try:
        relative = path.relative_to(root)
        return str(relative) if str(relative) else "."
    except ValueError:
        return str(path)


def add_issue(
    issues: List[Issue],
    severity: str,
    code: str,
    path: Path,
    message: str,
    root: Path,
) -> None:
    issues.append(
        Issue(
            severity=severity,
            code=code,
            path=display_path(path, root),
            message=message,
        )
    )


def discover_agents_files(root: Path) -> List[Path]:
    discovered: List[Path] = []
    for current, directories, files in os.walk(root, followlinks=False):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in IGNORED_DIRECTORIES
            and not Path(current, directory).is_symlink()
        )
        if "AGENTS.md" in files:
            discovered.append(Path(current, "AGENTS.md"))
    return sorted(discovered, key=lambda path: (len(path.parts), str(path)))


def read_text(path: Path, root: Path, issues: List[Issue]) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        add_issue(
            issues,
            "error",
            "FILE_READ",
            path,
            f"无法以 UTF-8 读取文件：{exc}",
            root,
        )
        return None


def mask_code(text: str) -> str:
    without_fences = FENCED_CODE_RE.sub("", text)
    return INLINE_CODE_RE.sub("", without_fences)


def link_destination(raw_destination: str) -> str:
    destination = raw_destination.strip()
    if destination.startswith("<") and ">" in destination:
        return destination[1 : destination.index(">")]
    return destination.split(maxsplit=1)[0]


def validate_local_links(
    agents: Path,
    text: str,
    root: Path,
    issues: List[Issue],
) -> None:
    for match in MARKDOWN_LINK_RE.finditer(mask_code(text)):
        raw_destination = link_destination(match.group(1))
        if not raw_destination or raw_destination.startswith("#"):
            continue

        parsed = urllib.parse.urlsplit(raw_destination)
        if parsed.scheme.lower() in REMOTE_SCHEMES or parsed.netloc:
            continue

        decoded_path = urllib.parse.unquote(parsed.path)
        if not decoded_path:
            continue
        if decoded_path.startswith("/"):
            candidate = root / decoded_path.lstrip("/")
        else:
            candidate = agents.parent / decoded_path

        if not candidate.exists():
            add_issue(
                issues,
                "error",
                "LOCAL_LINK_NOT_FOUND",
                agents,
                f"本地 Markdown 链接不存在：{raw_destination}",
                root,
            )


def validate_placeholders(
    agents: Path,
    text: str,
    root: Path,
    issues: List[Issue],
) -> None:
    for pattern in PLACEHOLDER_PATTERNS:
        match = pattern.search(text)
        if match:
            add_issue(
                issues,
                "error",
                "PLACEHOLDER",
                agents,
                f"发现未解析占位符：{match.group(0)!r}",
                root,
            )
            return


def validate_claude_pair(
    agents: Path,
    *,
    root: Path,
    strict: bool,
    issues: List[Issue],
) -> None:
    claude = agents.with_name("CLAUDE.md")
    if not claude.exists() and not claude.is_symlink():
        add_issue(
            issues,
            "error" if strict else "warning",
            "CLAUDE_NOT_FOUND",
            claude,
            "同目录缺少 CLAUDE.md 单一来源入口。",
            root,
        )
        return

    if claude.is_symlink():
        try:
            target = os.readlink(claude)
        except OSError as exc:
            add_issue(
                issues,
                "error",
                "CLAUDE_LINK_TARGET",
                claude,
                f"无法读取符号链接：{exc}",
                root,
            )
            return

        if target != "AGENTS.md":
            add_issue(
                issues,
                "error",
                "CLAUDE_LINK_TARGET",
                claude,
                "CLAUDE.md 必须使用精确相对目标 AGENTS.md。",
                root,
            )
            return

        try:
            resolved = claude.resolve(strict=True)
        except (OSError, RuntimeError):
            add_issue(
                issues,
                "error",
                "CLAUDE_LINK_TARGET",
                claude,
                "CLAUDE.md 符号链接已断开。",
                root,
            )
            return

        if resolved != agents.resolve():
            add_issue(
                issues,
                "error",
                "CLAUDE_LINK_TARGET",
                claude,
                "CLAUDE.md 必须解析到同目录 AGENTS.md。",
                root,
            )
        return

    add_issue(
        issues,
        "error",
        "CLAUDE_SYMLINK_REQUIRED",
        claude,
        "CLAUDE.md 必须是指向同目录 AGENTS.md 的相对符号链接。",
        root,
    )


def validate_project(
    project_root: Path,
    *,
    strict: bool = False,
) -> Report:
    root = project_root.resolve()
    issues: List[Issue] = []

    if not root.is_dir():
        add_issue(
            issues,
            "error",
            "PROJECT_ROOT_NOT_FOUND",
            project_root,
            "目标项目目录不存在或不是目录。",
            root,
        )
        return Report(str(root), 0, issues)

    root_agents = root / "AGENTS.md"
    if not root_agents.is_file():
        add_issue(
            issues,
            "error",
            "AGENTS_NOT_FOUND",
            root_agents,
            "项目根目录必须包含 AGENTS.md。",
            root,
        )

    agents_files = discover_agents_files(root)
    for agents in agents_files:
        text = read_text(agents, root, issues)
        if text is None:
            continue
        if not text.strip():
            add_issue(
                issues,
                "error",
                "AGENTS_EMPTY",
                agents,
                "AGENTS.md 不能为空。",
                root,
            )

        line_count = len(text.splitlines())
        if line_count > 120:
            add_issue(
                issues,
                "warning",
                "AGENTS_LENGTH_SOFT",
                agents,
                f"共 {line_count} 行，超过 120 行软复查预算；必要内容可保留。",
                root,
            )

        validate_claude_pair(
            agents,
            root=root,
            strict=strict,
            issues=issues,
        )
        if strict:
            validate_local_links(agents, text, root, issues)
            validate_placeholders(agents, text, root, issues)

    return Report(str(root), len(agents_files), issues)


def print_report(report: Report) -> None:
    for issue in report.issues:
        label = "ERROR" if issue.severity == "error" else "WARN"
        print(f"{label} {issue.code} {issue.path}: {issue.message}")
    print(f"AGENTS.md files: {report.agents_count}")
    status = "PASS" if not report.errors else "FAIL"
    print(
        f"{status}: {len(report.errors)} error(s), "
        f"{len(report.warnings)} warning(s) — {report.project_root}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate AGENTS.md and CLAUDE.md instruction pairs."
    )
    parser.add_argument("project_root", type=Path, help="Target project root.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require every AGENTS.md companion and validate local content.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable report.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_project(
        args.project_root,
        strict=args.strict,
    )
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())

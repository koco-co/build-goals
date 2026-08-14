"""Git cleanliness and tracked-secret checks."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from .documents import PLAN_PATH, section_body
from .model import Issue, add_issue
from .traceability import Task, task_field

PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")
SUSPICIOUS_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "service-account.json",
}
SECRET_SUFFIXES = {".pem", ".p12", ".pfx", ".key"}


def git_run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        capture_output=True,
    )


def is_git_repo(root: Path) -> bool:
    result = git_run(root, "rev-parse", "--is-inside-work-tree")
    return result.returncode == 0 and result.stdout.strip() == "true"


def validate_clean_git(root: Path, issues: list[Issue]) -> None:
    if not is_git_repo(root):
        add_issue(
            issues,
            "warning",
            "GIT_UNAVAILABLE",
            root,
            "项目不是 Git 工作树，无法验证干净状态。",
            root,
        )
        return
    result = git_run(root, "status", "--porcelain")
    if result.returncode != 0:
        add_issue(
            issues,
            "error",
            "GIT_STATUS",
            root,
            result.stderr.strip() or "无法读取 Git 状态。",
            root,
        )
    elif result.stdout.strip():
        add_issue(issues, "error", "GIT_DIRTY", root, "Git 工作区不干净。", root)


def validate_completed_worktrees(
    root: Path, tasks: list[Task], issues: list[Issue]
) -> None:
    """Reject task-owned worktrees that should have been removed after integration."""
    if not is_git_repo(root):
        return
    result = git_run(root, "worktree", "list", "--porcelain")
    if result.returncode != 0:
        add_issue(
            issues,
            "error",
            "GIT_WORKTREE_LIST",
            root,
            result.stderr.strip() or "无法枚举 Git worktrees。",
            root,
        )
        return

    project_root = root.resolve()
    registered: list[Path] = []
    for line in result.stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        worktree = Path(line[len("worktree ") :]).resolve()
        if worktree != project_root:
            registered.append(worktree)

    for task in tasks:
        status = task_field(task, "状态")
        integration_status = task_field(task, "集成状态") or ""
        declared_worktree = task_field(task, "Worktree") or ""
        if status not in {"已完成", "完成"} or "已集成" not in integration_status:
            continue
        declared_paths = {
            piece.strip().strip("`")
            for piece in re.split(r"\s+/\s+|[,;，；]", declared_worktree)
            if piece.strip()
        }
        for worktree in registered:
            relative = Path(os.path.relpath(worktree, project_root)).as_posix()
            candidates = {str(worktree), worktree.as_posix(), relative}
            if candidates.isdisjoint(declared_paths):
                continue
            add_issue(
                issues,
                "error",
                "COMPLETED_WORKTREE_REMAINS",
                worktree,
                f"{task.task_id} 已完成并集成，但对应 worktree 仍已注册。",
                root,
            )
            break


def _registered_worktrees(root: Path, output: str) -> dict[Path, str]:
    registered: dict[Path, str] = {}
    for record in output.strip().split("\n\n"):
        path: Optional[Path] = None
        branch = "detached"
        for line in record.splitlines():
            if line.startswith("worktree "):
                path = Path(line[len("worktree ") :]).resolve()
            elif line.startswith("branch "):
                branch = line[len("branch ") :].strip()
        if path is not None and path != root.resolve():
            registered[path] = branch
    return registered


def _baseline_worktrees(
    root: Path, plan_text: str, issues: list[Issue]
) -> dict[Path, str]:
    plan_path = root / PLAN_PATH
    body = section_body(plan_text, "## 基础工程就绪")
    if body is None:
        return {}
    match = re.search(r"(?m)^-\s*既有 Worktrees：\s*(.*?)\s*$", body)
    if match is None:
        return {}
    value = match.group(1).strip()
    if value in {"N/A（无既有 worktree）", "N/A (无既有 worktree)"}:
        return {}

    baseline: dict[Path, str] = {}
    for raw_entry in re.split(r"[;；]", value):
        parts = [piece.strip().strip("`") for piece in raw_entry.split("|")]
        if len(parts) != 3 or not all(parts):
            add_issue(
                issues,
                "error",
                "WORKTREE_BASELINE_FORMAT",
                plan_path,
                "既有 Worktrees 必须使用“路径 | refs/heads/分支 | 用途”，多项用分号分隔。",
                root,
            )
            continue
        raw_path, branch, _purpose = parts
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        baseline[path.resolve()] = branch
    return baseline


def validate_no_feature_worktrees_before_readiness(
    root: Path, plan_text: str, issues: list[Issue]
) -> None:
    """Reject every non-baseline worktree before the readiness gate passes."""
    if not is_git_repo(root):
        return
    result = git_run(root, "worktree", "list", "--porcelain")
    if result.returncode != 0:
        add_issue(
            issues,
            "error",
            "GIT_WORKTREE_LIST",
            root,
            result.stderr.strip() or "无法枚举 Git worktrees。",
            root,
        )
        return

    registered = _registered_worktrees(root, result.stdout)
    baseline = _baseline_worktrees(root, plan_text, issues)

    for worktree, branch in registered.items():
        expected_branch = baseline.get(worktree)
        if expected_branch is None:
            add_issue(
                issues,
                "error",
                "FEATURE_WORKTREE_BEFORE_READINESS",
                worktree,
                "该 worktree 未登记在 readiness 前的既有 Worktrees 基线中；不得通过任务写 N/A、漏填或只写分支名绕过门禁。",
                root,
            )
        elif expected_branch != branch:
            add_issue(
                issues,
                "error",
                "WORKTREE_BASELINE_MISMATCH",
                worktree,
                f"既有 Worktree 的登记分支为 {expected_branch!r}，实际为 {branch!r}。",
                root,
            )

    for worktree, expected_branch in baseline.items():
        if worktree not in registered:
            add_issue(
                issues,
                "error",
                "WORKTREE_BASELINE_MISMATCH",
                root / PLAN_PATH,
                f"既有 Worktree 清单登记了未注册路径 {worktree}（{expected_branch}）。",
                root,
            )


def validate_tracked_secrets(root: Path, issues: list[Issue]) -> None:
    if not is_git_repo(root):
        return
    result = git_run(root, "ls-files", "-z")
    if result.returncode != 0:
        add_issue(issues, "warning", "GIT_LS_FILES", root, "无法枚举已跟踪文件。", root)
        return
    for raw in result.stdout.split("\0"):
        if not raw:
            continue
        path = root / raw
        lower_name = path.name.lower()
        if lower_name in SUSPICIOUS_NAMES or path.suffix.lower() in SECRET_SUFFIXES:
            add_issue(
                issues,
                "error",
                "TRACKED_SECRET_FILE",
                path,
                "疑似秘密文件已被 Git 跟踪。",
                root,
            )
            continue
        try:
            if not path.is_file() or path.stat().st_size > 1_000_000:
                continue
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            add_issue(
                issues,
                "warning",
                "TRACKED_FILE_UNREADABLE",
                path,
                f"无法检查已跟踪文件内容：{exc}",
                root,
            )
            continue
        if PRIVATE_KEY_RE.search(content):
            add_issue(
                issues,
                "error",
                "TRACKED_PRIVATE_KEY",
                path,
                "已跟踪文件包含私钥头。",
                root,
            )

"""Git cleanliness and tracked-secret checks."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .model import Issue, add_issue

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
        add_issue(issues, "warning", "GIT_UNAVAILABLE", root, "项目不是 Git 工作树，无法验证干净状态。", root)
        return
    result = git_run(root, "status", "--porcelain")
    if result.returncode != 0:
        add_issue(issues, "error", "GIT_STATUS", root, result.stderr.strip() or "无法读取 Git 状态。", root)
    elif result.stdout.strip():
        add_issue(issues, "error", "GIT_DIRTY", root, "Git 工作区不干净。", root)


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
            add_issue(issues, "error", "TRACKED_SECRET_FILE", path, "疑似秘密文件已被 Git 跟踪。", root)
            continue
        try:
            if not path.is_file() or path.stat().st_size > 1_000_000:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if PRIVATE_KEY_RE.search(content):
            add_issue(issues, "error", "TRACKED_PRIVATE_KEY", path, "已跟踪文件包含私钥头。", root)

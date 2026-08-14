"""Foundation readiness evidence validation."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

from .documents import PLAN_PATH, section_body
from .model import Issue, add_issue

FOUNDATION_HEADING = "## 基础工程就绪"
FOUNDATION_FIELDS = (
    "状态",
    "安装命令",
    "安装结果",
    "启动或 Smoke 命令",
    "启动或 Smoke 结果",
    "基础测试命令",
    "基础测试结果",
    "基础工程提交",
    "既有 Worktrees",
)
READY_STATES = {"已验证", "有效沿用并验证"}
PASS_MARKERS = ("通过", "成功", "exit 0")
NEGATIVE_MARKERS = (
    "未执行",
    "尚未执行",
    "待执行",
    "无法执行",
    "未运行",
    "未通过",
    "不通过",
    "未成功",
    "失败",
    "尚无",
    "无法",
    "非零",
    "exit 1",
    "不适用",
    "N/A",
)
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
NO_CHANGE_STATES = {"N/A（无需变更）", "无需变更"}


def _field(body: str, label: str) -> Optional[str]:
    match = re.search(rf"(?m)^-\s*{re.escape(label)}：\s*(.*?)\s*$", body)
    return match.group(1).strip() if match else None


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        capture_output=True,
    )


def _commit_exists(root: Path, revision: str) -> bool:
    return _git(root, "cat-file", "-e", f"{revision}^{{commit}}").returncode == 0


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    return (
        _git(root, "merge-base", "--is-ancestor", ancestor, descendant).returncode == 0
    )


def _contains_negative_evidence(value: str) -> bool:
    return any(marker in value for marker in NEGATIVE_MARKERS)


def validate_foundation_readiness(
    root: Path,
    plan_text: str,
    issues: list[Issue],
) -> None:
    """Require installation, startup or smoke, and basic-test evidence."""
    plan_path = root / PLAN_PATH
    body = section_body(plan_text, FOUNDATION_HEADING)
    if body is None:
        add_issue(
            issues,
            "error",
            "FOUNDATION_READINESS_SECTION",
            plan_path,
            f"任务清单缺少 {FOUNDATION_HEADING!r}。",
            root,
        )
        return

    values: dict[str, str] = {}
    for label in FOUNDATION_FIELDS:
        value = _field(body, label)
        if not value:
            add_issue(
                issues,
                "error",
                "FOUNDATION_READINESS_FIELD",
                plan_path,
                f"基础工程就绪记录缺少字段“{label}”。",
                root,
            )
        else:
            values[label] = value

    if values.get("状态") not in READY_STATES:
        add_issue(
            issues,
            "error",
            "FOUNDATION_NOT_READY",
            plan_path,
            "基础工程尚未达到“已验证”或“有效沿用并验证”状态。",
            root,
        )

    for label in ("安装命令", "启动或 Smoke 命令", "基础测试命令"):
        value = values.get(label, "")
        if value == "-" or _contains_negative_evidence(value):
            add_issue(
                issues,
                "error",
                "FOUNDATION_COMMAND_REQUIRED",
                plan_path,
                f"“{label}”必须记录实际执行的可复现命令；库项目可使用导入或 CLI smoke 命令。",
                root,
            )

    for label in ("安装结果", "启动或 Smoke 结果", "基础测试结果"):
        value = values.get(label, "")
        if value and (
            _contains_negative_evidence(value)
            or not any(marker in value for marker in PASS_MARKERS)
        ):
            add_issue(
                issues,
                "error",
                "FOUNDATION_RESULT_NOT_PASSING",
                plan_path,
                f"“{label}”没有记录通过、成功或 exit 0 的执行结果。",
                root,
            )

    foundation_commit = values.get("基础工程提交", "").strip().strip("`")
    if foundation_commit in NO_CHANGE_STATES:
        return
    if not COMMIT_RE.fullmatch(foundation_commit):
        add_issue(
            issues,
            "error",
            "FOUNDATION_COMMIT_UNKNOWN",
            plan_path,
            "基础工程提交必须是实际存在的明确 SHA，或精确记录 N/A（无需变更）。",
            root,
        )
    elif not _commit_exists(root, foundation_commit):
        add_issue(
            issues,
            "error",
            "FOUNDATION_COMMIT_UNKNOWN",
            plan_path,
            "基础工程提交不是当前 Git 仓库中可验证的 commit。",
            root,
        )
    elif not _is_ancestor(root, foundation_commit, "HEAD"):
        add_issue(
            issues,
            "error",
            "FOUNDATION_COMMIT_NOT_IN_HEAD",
            plan_path,
            "当前 HEAD 不包含记录的基础工程提交。",
            root,
        )

"""Project-instruction readiness and drift validation."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

from validate_agents_md import (
    IGNORED_DIRECTORIES,
    validate_project as validate_agents_project,
)

from .documents import PLAN_PATH, section_body
from .model import Issue, add_issue

READINESS_HEADING = "## 项目指令就绪"
READY_STATES = {"有效沿用", "已更新并验证"}
READINESS_FIELDS = (
    "状态",
    "触发证据",
    "内容确认",
    "验证命令",
    "验证结果",
    "治理提交",
    "功能开发基线",
    "恢复条件",
)
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
BASELINE_HEAD_MARKER = "readiness 执行时的当前 HEAD"
NEGATIVE_RESULT_MARKERS = (
    "未通过",
    "不通过",
    "未成功",
    "失败",
    "未执行",
    "尚未执行",
    "无法执行",
    "待执行",
    "尚无",
    "无法",
    "非零",
    "exit 1",
)
NEGATIVE_APPROVAL_MARKERS = (
    "未确认",
    "未经",
    "未获确认",
    "尚未确认",
    "拒绝确认",
    "否决",
)
NO_GOVERNANCE_STATES = {"N/A（无需更新）", "无需更新"}


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


def _is_git_repo(root: Path) -> bool:
    result = _git(root, "rev-parse", "--is-inside-work-tree")
    return result.returncode == 0 and result.stdout.strip() == "true"


def _commit_exists(root: Path, revision: str) -> bool:
    return _git(root, "cat-file", "-e", f"{revision}^{{commit}}").returncode == 0


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = _git(root, "merge-base", "--is-ancestor", ancestor, descendant)
    return result.returncode == 0


def _resolve_revision(
    root: Path, value: str, *, allow_head_marker: bool
) -> Optional[str]:
    normalized = value.strip().strip("`")
    if allow_head_marker and normalized == BASELINE_HEAD_MARKER:
        return "HEAD"
    if COMMIT_RE.fullmatch(normalized) and _commit_exists(root, normalized):
        return normalized
    return None


def _is_instruction_path(raw: str) -> bool:
    path = Path(raw)
    return path.name in {"AGENTS.md", "CLAUDE.md"} and not any(
        part in IGNORED_DIRECTORIES for part in path.parts[:-1]
    )


def _commit_paths(root: Path, revision: str) -> tuple[str, ...]:
    result = _git(
        root,
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-only",
        "-r",
        revision,
    )
    if result.returncode != 0:
        return ()
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def _instruction_drift_paths(root: Path, governance: str) -> tuple[str, ...]:
    changed = _git(root, "diff", "--name-only", governance, "--", ".")
    paths = {
        line.strip()
        for line in changed.stdout.splitlines()
        if line.strip() and _is_instruction_path(line.strip())
    }
    untracked = _git(root, "ls-files", "--others", "--exclude-standard")
    paths.update(
        line.strip()
        for line in untracked.stdout.splitlines()
        if line.strip() and _is_instruction_path(line.strip())
    )
    return tuple(sorted(paths))


def _is_passing_result(value: str) -> bool:
    return not any(marker in value for marker in NEGATIVE_RESULT_MARKERS) and any(
        marker in value for marker in ("通过", "成功", "exit 0")
    )


def _is_executed_validation_command(value: str) -> bool:
    return not any(marker in value for marker in NEGATIVE_RESULT_MARKERS) and all(
        marker in value
        for marker in ("validate_agents_md.py", "--strict")
    )


def _is_confirmed(value: str) -> bool:
    return not any(marker in value for marker in NEGATIVE_APPROVAL_MARKERS) and any(
        marker in value for marker in ("已确认", "用户确认", "确认通过")
    )


def validate_agent_documents(root: Path, issues: list[Issue]) -> None:
    """Reuse build-agents-md's single source and local-reference checks."""
    report = validate_agents_project(root, strict=True)
    for issue in report.issues:
        path = root / issue.path if issue.path != "." else root
        severity = issue.severity
        if issue.code == "AGENTS_LENGTH_SOFT":
            severity = "info"
        add_issue(
            issues,
            severity,
            issue.code,
            path,
            issue.message,
            root,
        )


def validate_agent_readiness(
    root: Path,
    plan_text: str,
    issues: list[Issue],
    *,
    phase: str,
) -> None:
    """Require an evidence-backed instruction state before feature work begins."""
    plan_path = root / PLAN_PATH
    body = section_body(plan_text, READINESS_HEADING)
    if body is None:
        add_issue(
            issues,
            "error",
            "AGENT_READINESS_SECTION",
            plan_path,
            f"任务清单缺少 {READINESS_HEADING!r}。",
            root,
        )
        return

    values: dict[str, str] = {}
    for label in READINESS_FIELDS:
        value = _field(body, label)
        if not value:
            add_issue(
                issues,
                "error",
                "AGENT_READINESS_FIELD",
                plan_path,
                f"项目指令就绪记录缺少字段“{label}”。",
                root,
            )
        else:
            values[label] = value

    status = values.get("状态")
    if status not in READY_STATES:
        add_issue(
            issues,
            "error",
            "AGENT_INSTRUCTIONS_PENDING",
            plan_path,
            "项目指令尚未达到“有效沿用”或“已更新并验证”状态，功能开发必须暂停。",
            root,
        )
        return

    command = values.get("验证命令", "")
    if not _is_executed_validation_command(command):
        add_issue(
            issues,
            "error",
            "AGENT_VALIDATION_COMMAND",
            plan_path,
            "验证命令必须调用项目指令严格校验器 validate_agents_md.py，并启用 --strict。",
            root,
        )
    if not _is_passing_result(values.get("验证结果", "")):
        add_issue(
            issues,
            "error",
            "AGENT_VALIDATION_RESULT",
            plan_path,
            "项目指令没有记录通过的验证结果。",
            root,
        )

    if status == "有效沿用":
        if values.get("治理提交", "").strip().strip("`") not in NO_GOVERNANCE_STATES:
            add_issue(
                issues,
                "error",
                "AGENT_GOVERNANCE_COMMIT",
                plan_path,
                "有效沿用时，治理提交必须明确记录无需更新。",
                root,
            )
        return

    if not _is_confirmed(values.get("内容确认", "")):
        add_issue(
            issues,
            "error",
            "AGENT_CONTENT_APPROVAL",
            plan_path,
            "项目指令更新缺少完整内容和文件操作的确认依据。",
            root,
        )

    if not _is_git_repo(root):
        add_issue(
            issues,
            "error",
            "AGENT_GOVERNANCE_GIT_REQUIRED",
            plan_path,
            "项目指令已经更新，但当前目录不是可验证治理提交的 Git 工作树。",
            root,
        )
        return

    governance = _resolve_revision(
        root, values.get("治理提交", ""), allow_head_marker=False
    )
    if governance is None:
        add_issue(
            issues,
            "error",
            "AGENT_GOVERNANCE_COMMIT_UNKNOWN",
            plan_path,
            "项目指令治理提交必须回填为当前仓库中实际存在的明确 SHA。",
            root,
        )
        return

    governance_paths = _commit_paths(root, governance)
    instruction_paths = tuple(
        path for path in governance_paths if _is_instruction_path(path)
    )
    if not instruction_paths:
        add_issue(
            issues,
            "error",
            "AGENT_GOVERNANCE_COMMIT_CONTENT",
            plan_path,
            "项目指令治理提交没有修改根目录或嵌套目录中的 AGENTS.md/CLAUDE.md。",
            root,
        )
    unrelated_paths = tuple(
        path for path in governance_paths if not _is_instruction_path(path)
    )
    if unrelated_paths:
        add_issue(
            issues,
            "error",
            "AGENT_GOVERNANCE_COMMIT_SCOPE",
            plan_path,
            "项目指令治理提交混入了非 AGENTS.md/CLAUDE.md 文件："
            + "、".join(unrelated_paths),
            root,
        )

    raw_baseline = values.get("功能开发基线", "").strip().strip("`")
    baseline = _resolve_revision(
        root,
        raw_baseline,
        allow_head_marker=phase == "readiness",
    )
    if baseline is None:
        add_issue(
            issues,
            "error",
            "AGENT_FEATURE_BASELINE_UNKNOWN",
            plan_path,
            "功能开发基线不是可验证的 commit；自引用标记只允许在 readiness 阶段临时使用，交付前必须回填明确 SHA。",
            root,
        )
    elif not _is_ancestor(root, governance, baseline):
        add_issue(
            issues,
            "error",
            "AGENT_GOVERNANCE_NOT_IN_BASELINE",
            plan_path,
            "功能开发基线不包含项目指令治理提交。",
            root,
        )
    elif not _is_ancestor(root, baseline, "HEAD"):
        add_issue(
            issues,
            "error",
            "AGENT_BASELINE_NOT_IN_CURRENT_HEAD",
            plan_path,
            "当前 HEAD 不包含已冻结的功能开发基线。",
            root,
        )

    drift_paths = _instruction_drift_paths(root, governance)
    if drift_paths:
        add_issue(
            issues,
            "error",
            "AGENT_INSTRUCTIONS_DRIFT",
            plan_path,
            "项目指令已偏离用户确认并冻结的治理提交："
            + "、".join(drift_paths)
            + "。必须重新确认、形成新的治理提交并回填 SHA。",
            root,
        )

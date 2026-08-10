"""Requirement, finding, task, and commit traceability validation."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .model import Issue, add_issue

FUNCTION_RE = re.compile(r"\bF-\d{3}\b")
AC_RE = re.compile(r"\bF-\d{3}-AC-\d{2}\b")
AUDIT_RE = re.compile(r"\bAUD-\d{3}\b")
TASK_RE = re.compile(r"(?m)^###\s+(TASK-(\d{3}))\b[^\n]*$")
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
TASK_LABELS = (
    "需求/验收/Finding",
    "第一条失败测试",
    "正常测试数据",
    "验证命令",
    "提交边界",
    "回滚",
    "完成条件",
)
FINAL_STATES = {"已完成", "阻塞", "已取消"}


@dataclass(frozen=True)
class Task:
    task_id: str
    number: int
    body: str


def split_tasks(text: str) -> list[Task]:
    matches = list(TASK_RE.finditer(text))
    tasks: list[Task] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        tasks.append(Task(match.group(1), int(match.group(2)), text[match.end():end].strip()))
    return tasks


def _field(body: str, label: str) -> Optional[str]:
    match = re.search(rf"(?m)^-\s*{re.escape(label)}：\s*(.*?)\s*$", body)
    return match.group(1).strip() if match else None


def validate_tasks(
    text: str,
    path: Path,
    root: Path,
    issues: list[Issue],
    delivery: bool,
) -> list[Task]:
    tasks = split_tasks(text)
    if not tasks:
        add_issue(issues, "error", "TASKS_REQUIRED", path, "至少需要一个 TASK-NNN。", root)
        return []
    numbers = [task.number for task in tasks]
    if numbers != list(range(1, len(numbers) + 1)):
        add_issue(issues, "error", "TASK_SEQUENCE", path, f"任务编号必须从 001 连续递增；实际为 {numbers}。", root)
    for task in tasks:
        for label in TASK_LABELS:
            value = _field(task.body, label)
            if not value or value in {"-", "N/A", "待生成", "待开始"}:
                add_issue(
                    issues,
                    "error",
                    "TASK_FIELD",
                    path,
                    f"{task.task_id} 缺少有效字段“{label}”。",
                    root,
                )
        if not delivery:
            continue
        status = _field(task.body, "状态")
        if status not in FINAL_STATES:
            add_issue(issues, "error", "TASK_STATUS", path, f"{task.task_id} 缺少最终状态。", root)
            continue
        commit = _field(task.body, "Commit")
        if status == "已完成":
            if not commit or not COMMIT_RE.fullmatch(commit.strip("`")):
                add_issue(issues, "error", "TASK_COMMIT", path, f"{task.task_id} 缺少有效 commit SHA。", root)
            elif _is_git_repo(root) and not _commit_exists(root, commit.strip("`")):
                add_issue(issues, "error", "TASK_COMMIT_UNKNOWN", path, f"{task.task_id} 的 commit 不存在。", root)
    return tasks


def _is_git_repo(root: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        check=False,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _commit_exists(root: Path, sha: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{sha}^{{commit}}"],
        check=False,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def validate_traceability(
    mode: str,
    source_text: str,
    plan_text: str,
    report_text: Optional[str],
    plan_path: Path,
    report_path: Path,
    root: Path,
    issues: list[Issue],
) -> None:
    if mode == "greenfield":
        identifiers = sorted(set(FUNCTION_RE.findall(source_text)) | set(AC_RE.findall(source_text)))
        code = "PRD_TRACEABILITY"
        label = "PRD 需求/验收"
    else:
        identifiers = sorted(set(AUDIT_RE.findall(source_text)))
        code = "AUDIT_TRACEABILITY"
        label = "迁移 Finding"
    if not identifiers:
        add_issue(issues, "error", f"{code}_SOURCE", plan_path, f"权威输入中没有发现可追踪的{label} ID。", root)
        return
    for identifier in identifiers:
        if identifier not in plan_text:
            add_issue(issues, "error", code, plan_path, f"任务清单未追踪 {identifier}。", root)
        if report_text is not None and identifier not in report_text:
            add_issue(issues, "error", f"{code}_REPORT", report_path, f"交付报告未追踪 {identifier}。", root)


def validate_report_tasks(
    tasks: list[Task],
    report_text: str,
    report_path: Path,
    root: Path,
    issues: list[Issue],
) -> None:
    for task in tasks:
        if task.task_id not in report_text:
            add_issue(issues, "error", "REPORT_TASK_MISSING", report_path, f"交付报告未追踪 {task.task_id}。", root)

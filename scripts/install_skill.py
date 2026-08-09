#!/usr/bin/env python3
"""Install a canonical skill into Claude Code or Codex.

The repository keeps one portable source. Claude-only frontmatter is injected into
its installed copy; Codex keeps the portable SKILL.md and its agents/openai.yaml.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class InstallError(RuntimeError):
    """Raised when an installation cannot be completed safely."""


def inject_claude_manual_invocation(skill_md: str) -> str:
    """Return SKILL.md with Claude's manual-only field set to true."""
    lines = skill_md.splitlines()
    if not lines or lines[0].strip() != "---":
        raise InstallError("SKILL.md 缺少起始 Frontmatter 分隔符。")

    try:
        closing = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise InstallError("SKILL.md 缺少结束 Frontmatter 分隔符。") from exc

    field_pattern = re.compile(r"^disable-model-invocation\s*:")
    found = False
    for index in range(1, closing):
        if field_pattern.match(lines[index].strip()):
            lines[index] = "disable-model-invocation: true"
            found = True
            break

    if not found:
        lines.insert(closing, "disable-model-invocation: true")

    suffix = "\n" if skill_md.endswith("\n") else ""
    return "\n".join(lines) + suffix


def resolve_destination(
    *,
    skill_name: str,
    platform: str,
    scope: str,
    project_dir: Optional[Path] = None,
    home_dir: Optional[Path] = None,
) -> Path:
    """Resolve the installation directory without mutating the filesystem."""
    if platform not in {"claude", "codex"}:
        raise InstallError(f"不支持的平台：{platform}")
    if scope not in {"user", "project"}:
        raise InstallError(f"不支持的安装范围：{scope}")

    platform_root = ".claude" if platform == "claude" else ".agents"
    if scope == "user":
        base = (home_dir or Path.home()).expanduser().resolve()
    else:
        base = (project_dir or Path.cwd()).expanduser().resolve()

    return base / platform_root / "skills" / skill_name


def run_validator(validator: Path, skill_dir: Path, profile: str) -> None:
    """Run the bundled deterministic validator and raise on failure."""
    if not validator.is_file():
        raise InstallError(f"找不到校验脚本：{validator}")

    completed = subprocess.run(
        [sys.executable, str(validator), str(skill_dir), "--profile", profile, "--strict"],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        details = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
        raise InstallError(f"Skill 校验失败：\n{details}")


def install_skill(
    *,
    repo_root: Path,
    skill_name: str,
    platform: str,
    scope: str,
    project_dir: Optional[Path] = None,
    home_dir: Optional[Path] = None,
    force: bool = False,
    dry_run: bool = False,
) -> Path:
    """Validate, adapt, and atomically install one skill."""
    if not NAME_PATTERN.fullmatch(skill_name):
        raise InstallError("Skill 名称只能包含小写字母、数字和单个连字符。")

    repo_root = repo_root.expanduser().resolve()
    source = repo_root / "skills" / skill_name
    validator = repo_root / "skills" / "building-skills" / "scripts" / "validate_skill.py"
    if scope == "project":
        project_root = (project_dir or Path.cwd()).expanduser().resolve()
        if not project_root.is_dir():
            raise InstallError(f"项目目录不存在或不是目录：{project_root}")

    destination = resolve_destination(
        skill_name=skill_name,
        platform=platform,
        scope=scope,
        project_dir=project_dir,
        home_dir=home_dir,
    )

    if not source.is_dir():
        raise InstallError(f"找不到 Skill 源目录：{source}")
    if not (source / "SKILL.md").is_file():
        raise InstallError(f"源目录缺少 SKILL.md：{source}")
    if destination.is_symlink():
        raise InstallError(f"目标目录是符号链接，拒绝覆盖：{destination}")
    if destination.exists() and not force:
        raise InstallError(f"目标目录已存在：{destination}\n确认覆盖后重新执行并添加 --force。")

    run_validator(validator, source, "portable")
    temp_parent: Optional[Path] = None
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_parent = destination.parent

    with tempfile.TemporaryDirectory(prefix=f".{skill_name}-install-", dir=temp_parent) as temp_root:
        stage = Path(temp_root) / skill_name
        shutil.copytree(
            source,
            stage,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )

        if platform == "claude":
            skill_md = stage / "SKILL.md"
            skill_md.write_text(
                inject_claude_manual_invocation(skill_md.read_text(encoding="utf-8")),
                encoding="utf-8",
            )
            # This directory is a Codex presentation/policy adapter, not Claude runtime content.
            shutil.rmtree(stage / "agents", ignore_errors=True)
            profile = "claude"
        else:
            profile = "codex"

        run_validator(validator, stage, profile)

        if dry_run:
            return destination

        backup: Optional[Path] = None
        if destination.exists():
            backup = destination.with_name(f".{destination.name}.backup-{os.getpid()}")
            if backup.exists():
                shutil.rmtree(backup)
            destination.replace(backup)

        try:
            stage.replace(destination)
        except Exception:
            if backup is not None and backup.exists() and not destination.exists():
                backup.replace(destination)
            raise
        else:
            if backup is not None and backup.exists():
                shutil.rmtree(backup)

    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="将仓库中的可移植 Skill 安装到 Claude Code 或 Codex。",
    )
    parser.add_argument("skill", help="skills/ 下的 Skill 目录名")
    parser.add_argument("--platform", choices=("claude", "codex"), required=True)
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument(
        "--project-dir",
        type=Path,
        help="项目级安装的目标仓库；省略时使用当前目录",
    )
    parser.add_argument("--force", action="store_true", help="覆盖已有安装")
    parser.add_argument("--dry-run", action="store_true", help="完成校验与适配，但不写入目标目录")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    try:
        destination = install_skill(
            repo_root=repo_root,
            skill_name=args.skill,
            platform=args.platform,
            scope=args.scope,
            project_dir=args.project_dir,
            force=args.force,
            dry_run=args.dry_run,
        )
    except (InstallError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    action = "校验通过，计划安装到" if args.dry_run else "安装完成"
    print(f"{action}：{destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

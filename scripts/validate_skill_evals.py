#!/usr/bin/env python3
"""Validate deterministic behavior-evaluation assets for shipped Skills."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

KINDS = {"should_trigger", "should_not_trigger", "behavior"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def shipped_skills(root: Path) -> set[str]:
    skills_root = root / "skills"
    return {path.parent.name for path in skills_root.glob("*/SKILL.md")}


def validate_eval_file(path: Path, expected_skill: str) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"{path}: 无法读取 JSON：{exc}"]
    if not isinstance(data, dict):
        return [f"{path}: 根节点必须是对象"]
    if data.get("skill") != expected_skill:
        errors.append(f"{path}: skill 必须为 {expected_skill!r}")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        return [*errors, f"{path}: cases 必须是非空数组"]

    ids: set[str] = set()
    found_kinds: set[str] = set()
    for index, case in enumerate(cases, start=1):
        prefix = f"{path}: cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        unknown = set(case) - {"id", "kind", "prompt", "expected"}
        missing = {"id", "kind", "prompt", "expected"} - set(case)
        if unknown:
            errors.append(f"{prefix} 包含未知字段：{', '.join(sorted(unknown))}")
        if missing:
            errors.append(f"{prefix} 缺少字段：{', '.join(sorted(missing))}")
            continue
        case_id = case["id"]
        if not isinstance(case_id, str) or not ID_RE.fullmatch(case_id):
            errors.append(f"{prefix}.id 必须是小写 kebab-case")
        elif case_id in ids:
            errors.append(f"{prefix}.id 重复：{case_id}")
        else:
            ids.add(case_id)
        kind = case["kind"]
        if kind not in KINDS:
            errors.append(f"{prefix}.kind 必须是 {', '.join(sorted(KINDS))} 之一")
        else:
            found_kinds.add(kind)
        if not isinstance(case["prompt"], str) or not case["prompt"].strip():
            errors.append(f"{prefix}.prompt 必须是非空字符串")
        expected = case["expected"]
        if (
            not isinstance(expected, list)
            or not expected
            or not all(isinstance(item, str) and item.strip() for item in expected)
        ):
            errors.append(f"{prefix}.expected 必须是非空字符串数组")
    missing_kinds = KINDS - found_kinds
    if missing_kinds:
        errors.append(f"{path}: 缺少用例类型：{', '.join(sorted(missing_kinds))}")
    return errors


def validate_repository(root: Path) -> list[str]:
    root = root.resolve()
    expected = shipped_skills(root)
    eval_root = root / "evals" / "skills"
    if not eval_root.is_dir():
        return [f"{eval_root}: 目录不存在"]
    actual = {path.stem for path in eval_root.glob("*.json")}
    errors: list[str] = []
    for missing in sorted(expected - actual):
        errors.append(f"{eval_root}: 缺少 {missing}.json")
    for extra in sorted(actual - expected):
        errors.append(f"{eval_root}: 未分发的 Skill 不应有评测文件：{extra}.json")
    for skill in sorted(expected & actual):
        errors.extend(validate_eval_file(eval_root / f"{skill}.json", skill))
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="静态校验所有 Skill 的行为评测资产。")
    parser.add_argument(
        "root", nargs="?", type=Path, default=Path.cwd(), help="项目根目录"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_repository(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAIL: {len(errors)} error(s)")
        return 1
    count = len(shipped_skills(args.root.resolve()))
    print(f"PASS: {count} Skill eval file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

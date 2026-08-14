#!/usr/bin/env python3
"""Check or explicitly refresh cross-Skill runtime mirror files."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

MANIFEST_NAME = ".plugin-shared-files.json"


class SyncError(RuntimeError):
    """Raised when the mirror contract is invalid or unsafe."""


def safe_path(root: Path, raw_path: object, field: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise SyncError(f"{field} 必须是非空相对路径。")
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise SyncError(f"{field} 必须位于 Plugin 根目录内：{raw_path}")

    candidate = root / relative
    try:
        candidate.resolve(strict=False).relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise SyncError(f"{field} 越过 Plugin 根目录：{raw_path}") from exc
    return candidate


def load_contracts(root: Path) -> List[Tuple[Path, List[Path]]]:
    manifest = root / MANIFEST_NAME
    if not manifest.is_file():
        raise SyncError(f"找不到共享文件清单：{manifest}")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SyncError(f"无法读取共享文件清单：{exc}") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise SyncError("共享文件清单必须是 version=1 的 JSON 对象。")

    mirrors = data.get("mirrors")
    if not isinstance(mirrors, list) or not mirrors:
        raise SyncError("共享文件清单 mirrors 必须是非空数组。")

    contracts: List[Tuple[Path, List[Path]]] = []
    seen_sources = set()
    seen_targets = set()
    for index, item in enumerate(mirrors):
        if not isinstance(item, dict):
            raise SyncError(f"mirrors[{index}] 必须是对象。")
        source = safe_path(root, item.get("source"), f"mirrors[{index}].source")
        seen_sources.add(source)
        raw_targets = item.get("targets")
        if not isinstance(raw_targets, list) or not raw_targets:
            raise SyncError(f"mirrors[{index}].targets 必须是非空数组。")
        targets = [
            safe_path(root, raw, f"mirrors[{index}].targets[{target_index}]")
            for target_index, raw in enumerate(raw_targets)
        ]
        for target in targets:
            if target in seen_targets:
                raise SyncError(f"同一镜像目标不能重复声明：{target.relative_to(root)}")
            seen_targets.add(target)
        contracts.append((source, targets))

    overlap = seen_sources & seen_targets
    if overlap:
        paths = ", ".join(str(path.relative_to(root)) for path in sorted(overlap))
        raise SyncError(f"同一路径不能同时作为规范源和镜像：{paths}")
    return contracts


def synchronize(root: Path, *, write: bool) -> int:
    try:
        contracts = load_contracts(root)
    except SyncError as exc:
        print(f"ERROR: {exc}")
        return 1

    errors: List[str] = []
    changed = 0
    checked = 0
    for source, targets in contracts:
        if source.is_symlink() or not source.is_file():
            errors.append(f"SOURCE: {source.relative_to(root)} 必须是存在的普通文件。")
            continue
        try:
            source_bytes = source.read_bytes()
        except OSError as exc:
            errors.append(f"SOURCE: 无法读取 {source.relative_to(root)}：{exc}")
            continue

        for target in targets:
            checked += 1
            if target.is_symlink():
                errors.append(
                    f"SYMLINK: {target.relative_to(root)} 必须先转换为普通文件。"
                )
                continue
            if target.exists() and not target.is_file():
                errors.append(
                    f"TARGET: {target.relative_to(root)} 已存在且不是普通文件。"
                )
                continue
            try:
                target_bytes = target.read_bytes() if target.is_file() else None
            except OSError as exc:
                errors.append(f"TARGET: 无法读取 {target.relative_to(root)}：{exc}")
                continue
            if target_bytes == source_bytes:
                continue
            if not write:
                errors.append(
                    f"DRIFT: {target.relative_to(root)} != {source.relative_to(root)}"
                )
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            except OSError as exc:
                errors.append(f"WRITE: 无法更新 {target.relative_to(root)}：{exc}")
                continue
            if target.is_symlink() or not target.is_file():
                errors.append(f"WRITE: {target.relative_to(root)} 写入后不是普通文件。")
                continue
            changed += 1

    for error in errors:
        print(error)
    if errors:
        return 1
    action = "同步完成" if write else "检查通过"
    print(f"PASS: 共享文件{action}，检查 {checked} 个镜像，更新 {changed} 个。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="检查共享运行文件，或显式写入与规范源一致的普通镜像文件。"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Plugin 根目录；默认使用当前工作目录。",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="显式更新缺失或漂移的普通镜像文件；默认只检查。",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: Plugin 根目录不存在或不是目录：{root}")
        return 1
    return synchronize(root, write=args.write)


if __name__ == "__main__":
    sys.exit(main())

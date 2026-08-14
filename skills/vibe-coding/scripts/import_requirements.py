#!/usr/bin/env python3
"""Validate, compare, and snapshot-import a portable requirement package."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from validate_prd import (
    MANIFEST_NAME,
    PACKAGE_DIR,
    PackageSnapshot,
    load_validated_snapshot,
    sha256_file,
)

FEATURE_RE = re.compile(r"\bF-\d{3}\b")


def _features(path: Path) -> set[str]:
    if not path.is_file() or path.suffix != ".md":
        return set()
    try:
        return set(FEATURE_RE.findall(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError):
        return set()


def _manifest_contract(snapshot: PackageSnapshot) -> dict[str, Any]:
    """Return source-owned manifest data without local import provenance."""
    return {key: value for key, value in snapshot.manifest.items() if key != "import"}


def compare_snapshots(source: PackageSnapshot, existing: PackageSnapshot | None) -> dict[str, Any]:
    if existing is None:
        changed_files: list[str] = []
        removed_files: list[str] = []
        added_files = sorted([MANIFEST_NAME, *source.files])
        manifest_changed = True
    else:
        source_names = set(source.files)
        existing_names = set(existing.files)
        added_files = sorted(source_names - existing_names)
        removed_files = sorted(existing_names - source_names)
        changed_files = sorted(
            name for name in source_names & existing_names if source.files[name] != existing.files[name]
        )
        manifest_changed = _manifest_contract(source) != _manifest_contract(existing)
        if manifest_changed:
            changed_files.append(MANIFEST_NAME)
            changed_files.sort()

    source_domains = {item.domain_id: item for item in source.domains}
    existing_domains = {item.domain_id: item for item in existing.domains} if existing else {}
    changed_domains: set[str] = set(source_domains) ^ set(existing_domains)
    for domain_id in set(source_domains) & set(existing_domains):
        if source_domains[domain_id] != existing_domains[domain_id]:
            changed_domains.add(domain_id)
        paths = {
            source_domains[domain_id].requirements.as_posix(),
            source_domains[domain_id].examples.as_posix(),
            existing_domains[domain_id].requirements.as_posix(),
            existing_domains[domain_id].examples.as_posix(),
        }
        if paths & set(changed_files + added_files + removed_files):
            changed_domains.add(domain_id)

    changed_features: set[str] = set()
    impacted = set(changed_files + added_files + removed_files)
    for name in impacted:
        if not name.startswith("功能域/"):
            continue
        changed_features.update(_features(source.root / name))
        if existing is not None:
            changed_features.update(_features(existing.root / name))

    has_changes = bool(added_files or removed_files or changed_files)
    return {
        "added_files": added_files,
        "removed_files": removed_files,
        "changed_files": changed_files,
        "changed_domains": sorted(changed_domains),
        "changed_features": sorted(changed_features),
        "manifest_changed": manifest_changed,
        "has_changes": has_changes,
        "requires_replace": existing is not None and has_changes,
    }


def _record_import(package: Path, source: PackageSnapshot) -> None:
    manifest_path = package / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_contract = source.manifest.get("source")
    source_project = "unknown"
    source_revision = "unknown"
    if isinstance(source_contract, dict):
        if isinstance(source_contract.get("project"), str) and source_contract["project"].strip():
            source_project = source_contract["project"]
        if isinstance(source_contract.get("revision"), str) and source_contract["revision"].strip():
            source_revision = source_contract["revision"]
    manifest["import"] = {
        "source_project": source_project,
        "source_revision": source_revision,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest_sha256": sha256_file(source.root / MANIFEST_NAME),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_snapshot(source: PackageSnapshot, docs: Path) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
    holder = tempfile.TemporaryDirectory(prefix=".requirements-import-", dir=docs)
    staged = Path(holder.name) / "产品需求"
    shutil.copytree(source.root, staged, symlinks=True)
    _record_import(staged, source)
    snapshot, report = load_validated_snapshot(staged)
    if snapshot is None:
        holder.cleanup()
        details = "; ".join(f"{item.code}: {item.message}" for item in report.issues)
        raise RuntimeError(f"STAGED_SNAPSHOT_INVALID: {details}")
    return staged, holder


def _write_snapshot(source: PackageSnapshot, target_project: Path, *, replace: bool) -> None:
    docs = target_project / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    target = target_project / PACKAGE_DIR
    staged, holder = _prepare_snapshot(source, docs)
    displaced: Path | None = None
    try:
        if target.exists():
            if not replace:
                raise FileExistsError("TARGET_EXISTS")
            displaced = Path(holder.name) / "previous"
            target.rename(displaced)
        staged.rename(target)
        if displaced is not None:
            shutil.rmtree(displaced)
    except OSError:
        if displaced is not None and displaced.exists() and not target.exists():
            displaced.rename(target)
        raise
    finally:
        holder.cleanup()


def _print_human(payload: dict[str, Any]) -> None:
    if payload.get("errors"):
        for error in payload["errors"]:
            print(f"ERROR   {error['code']}: {error['message']}")
        print("FAIL: 需求快照未导入。")
        return
    action = "已写入" if payload["written"] else "只读比较"
    print(f"PASS: 需求快照{action}。")
    print(f"- 来源：{payload['source']}")
    print(f"- 目标：{payload['target']}")
    print(f"- 变化功能域：{', '.join(payload['changed_domains']) or '无'}")
    print(f"- 变化功能：{', '.join(payload['changed_features']) or '无'}")
    if payload["requires_replace"] and not payload["written"]:
        print("- TARGET_EXISTS：目标已有不同快照；确认影响后使用 --write --replace。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验并将外部 docs/产品需求/ 复制为目标项目的本地快照。")
    parser.add_argument("source", type=Path, help="来源项目或产品需求包路径")
    parser.add_argument("target_project", type=Path, help="目标项目根目录")
    parser.add_argument("--write", action="store_true", help="实际写入；默认只比较")
    parser.add_argument("--replace", action="store_true", help="替换已有快照；仅在用户确认差异后与 --write 同时使用")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    source, source_report = load_validated_snapshot(args.source)
    target_project = args.target_project.expanduser().resolve(strict=False)
    target_package = target_project / PACKAGE_DIR
    errors: list[dict[str, str]] = []
    if source is None:
        errors.extend({"code": issue.code, "message": issue.message} for issue in source_report.issues)
        payload: dict[str, Any] = {
            "source": str(args.source.expanduser().resolve(strict=False)),
            "target": str(target_package),
            "written": False,
            "changed_domains": [],
            "changed_features": [],
            "requires_replace": False,
            "errors": errors,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            _print_human(payload)
        return 1

    existing: PackageSnapshot | None = None
    if target_package.exists():
        existing, existing_report = load_validated_snapshot(target_package)
        if existing is None:
            errors.append(
                {
                    "code": "TARGET_INVALID",
                    "message": "; ".join(f"{item.code}: {item.message}" for item in existing_report.issues),
                }
            )
    changes = compare_snapshots(source, existing)
    written = False
    if args.replace and not args.write:
        errors.append({"code": "REPLACE_REQUIRES_WRITE", "message": "--replace 必须与 --write 同时使用。"})
    elif args.write and target_package.exists() and not args.replace and changes["has_changes"]:
        errors.append({"code": "TARGET_EXISTS", "message": "目标已有不同需求快照；必须先确认差异再显式替换。"})
    elif args.write and not errors and not (existing is not None and not changes["has_changes"]):
        try:
            _write_snapshot(source, target_project, replace=args.replace)
            written = True
        except (OSError, RuntimeError) as exc:
            errors.append({"code": "IMPORT_WRITE", "message": str(exc)})

    payload = {
        "source": str(source.root),
        "target": str(target_package),
        "written": written,
        **changes,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_human(payload)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

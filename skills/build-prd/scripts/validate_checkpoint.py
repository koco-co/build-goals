#!/usr/bin/env python3
"""Validate resumable build-prd domain checkpoints."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

DOMAIN_ID_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?")
FEATURE_ID_RE = re.compile(r"F-\d{3}")


@dataclass(frozen=True)
class Issue:
    code: str
    path: str
    message: str


def _checkpoint_root(target: Path) -> Path:
    expanded = target.expanduser()
    if expanded.name == "build-prd" and expanded.parent.name == ".build-goals":
        return expanded.resolve(strict=False)
    return (expanded / ".build-goals" / "build-prd").resolve(strict=False)


def _read_object(path: Path, root: Path, issues: list[Issue]) -> Optional[dict[str, Any]]:
    try:
        display = path.relative_to(root).as_posix()
    except ValueError:
        display = str(path)
    if path.is_symlink() or not path.is_file():
        issues.append(Issue("NON_REGULAR_FILE", display, "检查点必须是普通文件，不能缺失或使用符号链接。"))
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.append(Issue("CHECKPOINT_FORMAT", display, f"无法读取 JSON 对象：{exc}"))
        return None
    if not isinstance(value, dict):
        issues.append(Issue("CHECKPOINT_FORMAT", display, "检查点顶层必须是对象。"))
        return None
    return value


def _strings(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _safe_relative(value: Any) -> Optional[Path]:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path == Path("."):
        return None
    return path


def _validate_domain(
    root: Path,
    path: Path,
    expected: dict[str, Any],
    issues: list[Issue],
) -> set[str]:
    data = _read_object(path, root, issues)
    if data is None:
        return set()
    display = path.relative_to(root).as_posix()
    if data.get("schema_version") != "1.0":
        issues.append(Issue("SCHEMA_VERSION", display, "schema_version 必须为 1.0。"))
    if data.get("domain_id") != expected["id"] or data.get("name") != expected["name"]:
        issues.append(Issue("DOMAIN_METADATA", display, "功能域 ID 或名称与会话不一致。"))
    if data.get("status") != "confirmed":
        issues.append(Issue("DOMAIN_STATUS", display, "已完成功能域必须标记为 confirmed。"))
    if data.get("dependencies") != expected["dependencies"]:
        issues.append(Issue("DOMAIN_DEPENDENCY", display, "功能域依赖与会话地图不一致。"))
    if not isinstance(data.get("summary"), str) or not data["summary"].strip():
        issues.append(Issue("DOMAIN_SUMMARY", display, "功能域缺少已确认总结。"))
    if not _strings(data.get("evidence")):
        issues.append(Issue("DOMAIN_EVIDENCE", display, "功能域至少需要一条证据引用。"))

    features = data.get("features")
    if not isinstance(features, list) or not features:
        issues.append(Issue("FEATURES_REQUIRED", display, "功能域至少需要一项功能。"))
        return set()
    ids: set[str] = set()
    for index, feature in enumerate(features):
        label = f"{display}.features[{index}]"
        if not isinstance(feature, dict):
            issues.append(Issue("FEATURE_ENTRY", label, "功能必须是对象。"))
            continue
        feature_id = feature.get("id")
        if not isinstance(feature_id, str) or FEATURE_ID_RE.fullmatch(feature_id) is None:
            issues.append(Issue("FEATURE_ID", label, "功能 ID 必须使用 F-NNN。"))
        elif feature_id in ids:
            issues.append(Issue("FEATURE_ID", label, "功能 ID 重复。"))
        else:
            ids.add(feature_id)
        if not isinstance(feature.get("name"), str) or not feature["name"].strip():
            issues.append(Issue("FEATURE_NAME", label, "功能缺少名称。"))
        for key in ("user_inputs", "interactions", "external_contracts", "forbidden", "acceptance"):
            if not _strings(feature.get(key)):
                issues.append(Issue("FEATURE_FIELD", label, f"{key} 必须是非空字符串数组。"))
        outputs = feature.get("outputs")
        if not isinstance(outputs, dict) or not all(
            _strings(outputs.get(key)) for key in ("exact", "semantic", "runtime")
        ):
            issues.append(Issue("OUTPUT_CONTRACT", label, "outputs 必须分别包含 exact、semantic 和 runtime 非空数组。"))
    return ids


def _dependency_cycle(domains: dict[str, dict[str, Any]]) -> bool:
    graph = {
        domain_id: [item for item in domain["dependencies"] if item in domains]
        for domain_id, domain in domains.items()
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in graph.get(node, [])):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph if node not in visited)


def validate_checkpoint(target: Path, *, strict: bool = False) -> tuple[Path, list[Issue]]:
    root = _checkpoint_root(target)
    issues: list[Issue] = []
    session = _read_object(root / "会话.yaml", root, issues)
    if session is None:
        return root, issues
    if session.get("schema_version") != "1.0":
        issues.append(Issue("SCHEMA_VERSION", "会话.yaml", "schema_version 必须为 1.0。"))
    status = session.get("status")
    if status not in {"in_progress", "ready_for_authoring"}:
        issues.append(Issue("SESSION_STATUS", "会话.yaml", "status 必须是 in_progress 或 ready_for_authoring。"))
    source = session.get("source")
    if not isinstance(source, dict) or not all(
        isinstance(source.get(key), str) and source[key].strip()
        for key in ("project", "revision")
    ):
        issues.append(Issue("SOURCE", "会话.yaml", "source 必须记录 project 和 revision。"))

    domains_raw = session.get("domains")
    domains: dict[str, dict[str, Any]] = {}
    if not isinstance(domains_raw, list) or not domains_raw:
        issues.append(Issue("DOMAINS_REQUIRED", "会话.yaml", "会话至少需要一个功能域。"))
        domains_raw = []
    for index, domain in enumerate(domains_raw):
        label = f"会话.yaml.domains[{index}]"
        if not isinstance(domain, dict):
            issues.append(Issue("DOMAIN_ENTRY", label, "功能域必须是对象。"))
            continue
        domain_id = domain.get("id")
        name = domain.get("name")
        dependencies = domain.get("dependencies")
        checkpoint = _safe_relative(domain.get("checkpoint"))
        if not isinstance(domain_id, str) or DOMAIN_ID_RE.fullmatch(domain_id) is None:
            issues.append(Issue("DOMAIN_ID", label, "功能域 ID 格式无效。"))
            continue
        if domain_id in domains:
            issues.append(Issue("DOMAIN_ID", label, "功能域 ID 重复。"))
            continue
        if not isinstance(name, str) or not name.strip():
            issues.append(Issue("DOMAIN_NAME", label, "功能域缺少名称。"))
            continue
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            issues.append(Issue("DOMAIN_DEPENDENCY", label, "dependencies 必须是字符串数组。"))
            dependencies = []
        if checkpoint is None or checkpoint.parts[:1] != ("功能域",) or checkpoint.suffix != ".yaml":
            issues.append(Issue("CHECKPOINT_PATH", label, "checkpoint 必须位于 功能域/*.yaml。"))
            continue
        domains[domain_id] = {
            "id": domain_id,
            "name": name,
            "dependencies": dependencies,
            "checkpoint": checkpoint,
        }

    domain_ids = set(domains)
    for domain in domains.values():
        unknown = set(domain["dependencies"]) - domain_ids
        if unknown:
            issues.append(Issue("DOMAIN_DEPENDENCY", "会话.yaml", f"{domain['id']} 包含未知依赖：{sorted(unknown)}。"))
        if strict and domain["id"] in domain["dependencies"]:
            issues.append(Issue("DOMAIN_SELF_DEPENDENCY", "会话.yaml", f"{domain['id']} 不能依赖自身。"))
    if strict and _dependency_cycle(domains):
        issues.append(Issue("DOMAIN_DEPENDENCY_CYCLE", "会话.yaml", "功能域依赖不能形成环。"))

    completed = session.get("completed_domains")
    pending = session.get("pending_domains")
    completed_valid = isinstance(completed, list) and all(
        isinstance(item, str) and bool(item.strip()) for item in completed
    )
    pending_valid = isinstance(pending, list) and all(
        isinstance(item, str) and bool(item.strip()) for item in pending
    )
    completed_set = set(completed) if completed_valid else set()
    pending_set = set(pending) if pending_valid else set()
    if (
        not completed_valid
        or not pending_valid
        or completed_set & pending_set
        or completed_set | pending_set != domain_ids
        or (completed_valid and len(completed_set) != len(completed))
        or (pending_valid and len(pending_set) != len(pending))
    ):
        issues.append(Issue("DOMAIN_PARTITION", "会话.yaml", "completed_domains 与 pending_domains 必须无重复、无交集且完整覆盖功能域地图。"))
    current = session.get("current_domain")
    if pending_set:
        if current not in pending_set:
            issues.append(Issue("CURRENT_DOMAIN", "会话.yaml", "current_domain 必须位于待处理功能域。"))
    elif current is not None:
        issues.append(Issue("CURRENT_DOMAIN", "会话.yaml", "全部完成后 current_domain 必须为 null。"))

    if strict and status == "ready_for_authoring":
        if pending_set or current is not None or completed_set != domain_ids:
            issues.append(Issue("READY_FOR_AUTHORING", "会话.yaml", "ready_for_authoring 要求全部功能域已完成、pending_domains 为空且 current_domain 为 null。"))

    global_features: dict[str, str] = {}
    for domain_id in sorted(completed_set & domain_ids):
        domain = domains[domain_id]
        feature_ids = _validate_domain(root, root / domain["checkpoint"], domain, issues)
        if strict:
            for feature_id in feature_ids:
                previous = global_features.get(feature_id)
                if previous is not None:
                    issues.append(Issue("FEATURE_ID_GLOBAL_DUPLICATE", domain["checkpoint"].as_posix(), f"{feature_id} 已在功能域 {previous} 使用；功能 ID 必须跨功能域唯一。"))
                else:
                    global_features[feature_id] = domain_id
    return root, issues


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验 build-prd 的逐功能域过程检查点。")
    parser.add_argument("target", type=Path, help="项目根目录或 .build-goals/build-prd 目录")
    parser.add_argument("--strict", action="store_true", help="增加依赖环、全局功能 ID 与 authoring 就绪状态检查")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root, issues = validate_checkpoint(args.target, strict=args.strict)
    for issue in issues:
        print(f"ERROR   {issue.code:24} {issue.path}: {issue.message}")
    if issues:
        print(f"FAIL: {len(issues)} error(s) — {root}")
        return 1
    print(f"PASS: 0 error(s) — {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

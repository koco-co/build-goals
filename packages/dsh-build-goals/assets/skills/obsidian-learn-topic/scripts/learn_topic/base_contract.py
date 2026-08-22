from __future__ import annotations

from typing import Any
import re

from .curriculum import ContractError


REQUIRED = {"route", "current", "review-due", "blocked", "evidence"}


def _tokens(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_tokens(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {_tokens(item)}" for key, item in value.items())
    return str(value)


def _expressions(view: dict[str, Any]) -> set[str]:
    filters = view.get("filters", [])
    if isinstance(filters, list):
        return {" ".join(item.split()) for item in filters if isinstance(item, str)}
    if isinstance(filters, dict):
        return {" ".join(item.split()) for item in _tokens(filters).splitlines() if item.strip()}
    if not isinstance(filters, str) or not filters.strip():
        return set()
    expressions = set()
    for line in filters.splitlines():
        match = re.match(r"^\s*-\s*(.*?)\s*$", line)
        if not match:
            continue
        raw = match.group(1)
        if raw.startswith("'") and raw.endswith("'"):
            value = raw[1:-1]
        elif raw.startswith('"') and raw.endswith('"'):
            try:
                import json
                value = json.loads(raw)
            except ValueError:
                value = raw[1:-1]
        else:
            value = raw
        expressions.add(" ".join(value.split()))
    return expressions


def detect_capabilities(views: Any, *, require_all: bool = False) -> set[str]:
    if not isinstance(views, list):
        raise ContractError("Base views must be an array")
    found: set[str] = set()
    for view in views:
        if not isinstance(view, dict):
            continue
        body = _tokens(view)
        expressions = _expressions(view)
        evidence_filter = 'record_type == "learning-evidence"'
        if "formula.route_order" in body and expressions == set():
            found.add("route")
        if expressions == {evidence_filter, 'progress_status == "学习中"'}:
            found.add("current")
        if expressions == {evidence_filter, 'formula.review_due == true'}:
            found.add("review-due")
        if expressions == {evidence_filter, 'progress_status == "阻塞"'}:
            found.add("blocked")
        if expressions in (
            {evidence_filter, 'mastery_status != ""'},
            {evidence_filter, "mastery_status != null"},
        ):
            found.add("evidence")
    if require_all and found != REQUIRED:
        raise ContractError(f"Base is missing semantic capabilities: {', '.join(sorted(REQUIRED - found))}")
    return found


def parse_base_views(content: str) -> list[dict[str, Any]]:
    """Parse the small view subset needed for semantic validation.

    Obsidian performs the authoritative YAML parse when a Base is opened. This
    parser intentionally extracts only view names, filters, formulas, and order
    so static validation does not require a third-party YAML package.
    """
    if not isinstance(content, str) or "views:" not in content:
        raise ContractError("Base content must contain views")
    body = content.split("views:", 1)[1]
    starts = list(re.finditer(r"(?m)^  - type:\s*([^\n]+)$", body))
    if not starts:
        raise ContractError("Base content has no views")
    views = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(body)
        block = body[match.start():end]
        name_match = re.search(r"(?m)^    name:\s*(.+)$", block)
        name = name_match.group(1).strip().strip('"') if name_match else f"view-{index + 1}"
        filter_match = re.search(r"(?ms)^    filters:\s*\n(.*?)(?=^    [A-Za-z][A-Za-z0-9_.-]*:|\Z)", block)
        filters = filter_match.group(1) if filter_match else ""
        views.append({"name": name, "filters": filters, "body": block})
    return views


def validate_base_root(content: str, root: str) -> None:
    prefix = content.split("views:", 1)[0]
    accepted = {
        f'file.inFolder("{root}")',
        f'file.path.startsWith("{root}/")',
    }
    expressions = _expressions({"filters": prefix})
    root_expressions = {
        expression for expression in expressions
        if "file.inFolder" in expression or "file.path.startsWith" in expression
    }
    if len(root_expressions) != 1 or root_expressions.isdisjoint(accepted) or expressions != {*root_expressions, 'file.ext == "md"'}:
        raise ContractError("Base root filter must lock the exact roadmap_root")

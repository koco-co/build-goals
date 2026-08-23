#!/usr/bin/env python3
"""Validate distributed eval fixtures and optional real-client observations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOMAINS = {"language", "framework", "concept", "repository"}
ROUTING_FIELDS = {"id", "domain", "input", "expected_branch", "required_behaviors"}
CONTENT_FIELDS = {"id", "domain", "topic", "expected"}


class EvalError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvalError(f"{path} must contain an object")
    return value


def validate_fixtures() -> dict[str, Any]:
    results = {}
    for name in ("routing-cases.json", "content-cases.json"):
        value = load(ROOT / "evals" / name)
        cases = value.get("cases")
        if value.get("schema_version") != 1 or not isinstance(cases, list):
            raise EvalError(f"{name} has an invalid contract")
        required = ROUTING_FIELDS if name == "routing-cases.json" else CONTENT_FIELDS
        for index, case in enumerate(cases):
            if not isinstance(case, dict) or not required.issubset(case):
                raise EvalError(f"{name} cases[{index}] is missing required fields")
            if not all(isinstance(case[field], str) and case[field].strip() for field in required - {"required_behaviors", "expected"}):
                raise EvalError(f"{name} cases[{index}] has an empty scalar field")
            list_field = "required_behaviors" if name == "routing-cases.json" else "expected"
            values = case[list_field]
            if not isinstance(values, list) or len(values) < 3 or not all(isinstance(item, str) and item.strip() for item in values):
                raise EvalError(f"{name} cases[{index}].{list_field} must contain substantive checks")
        ids = [case["id"] for case in cases]
        domains = {case["domain"] for case in cases}
        if len(ids) != len(set(ids)) or domains != DOMAINS:
            raise EvalError(f"{name} must have unique ids and all four domains")
        results[name] = len(cases)
    return results


def fixture_ids() -> set[str]:
    identifiers: set[str] = set()
    for name in ("routing-cases.json", "content-cases.json"):
        identifiers.update(case["id"] for case in load(ROOT / "evals" / name)["cases"])
    return identifiers


def validate_observation(path: Path) -> dict[str, Any]:
    value = load(path)
    required = {"client", "fresh_session", "case_id", "result", "evidence"}
    if not required.issubset(value):
        raise EvalError("observation is missing required fields")
    if value["client"] not in {"codex", "claude"} or value["fresh_session"] is not True:
        raise EvalError("observation must come from a supported fresh client")
    if value["result"] not in {"passed", "failed", "not-verified", "blocked"}:
        raise EvalError("observation result is invalid")
    if value["case_id"] not in fixture_ids():
        raise EvalError("observation case_id is not a distributed eval case")
    if not isinstance(value["evidence"], list) or not value["evidence"] or not all(
        isinstance(item, str) and item.strip() for item in value["evidence"]
    ):
        raise EvalError("observation evidence must be a non-empty string array")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate"])
    parser.add_argument("--observation", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        fixtures = validate_fixtures()
        observations = [validate_observation(Path(path)) for path in args.observation]
    except (EvalError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "fixtures": fixtures, "observations": len(observations)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

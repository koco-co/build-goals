#!/usr/bin/env python3
"""Validate and transact v3 Obsidian learning roadmaps through Obsidian CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

from learn_topic.base_contract import detect_capabilities, parse_base_views, validate_base_root
from learn_topic.curriculum import ContractError, extract_curriculum, validate_curriculum, validate_directories, validate_visible_projection
from learn_topic.migration import build_migration_preview
from learn_topic.evidence_verification import validate_receipt
from learn_topic.note_contract import (
    parse_frontmatter, validate_curriculum_map_properties, validate_knowledge_note,
    validate_learning_record, validate_planned_note, validate_repository_visible_projection,
)
from learn_topic.obsidian_adapter import ObsidianCLI
from learn_topic.transactions import sha256_text
from learn_topic.vault_paths import roadmap_base_path, validate_vault_path


def emit(value: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True), file=stream)


def load_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise ContractError(f"{label} must not be a symbolic link")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot read {label}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return value


def read_file(path: Any, *, relative_to: Path, label: str) -> str:
    if not isinstance(path, str) or not path:
        raise ContractError(f"{label} must be a path")
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = relative_to / candidate
    candidate = candidate.resolve(strict=True)
    if not candidate.is_file() or candidate.is_symlink():
        raise ContractError(f"{label} must be a regular file")
    return candidate.read_text(encoding="utf-8")


def selected_vault(cli: ObsidianCLI, expected_name: str | None, expected_path: str | None) -> dict[str, str]:
    cli.run(["help"], target_vault=False)
    name = cli.run(["vault", "info=name"])
    path = str(Path(cli.run(["vault", "info=path"])).resolve())
    version = cli.run(["version"], target_vault=False)
    if expected_name and name != expected_name:
        raise ContractError(f"selected Vault {name!r} does not match plan {expected_name!r}")
    if expected_path and path != str(Path(expected_path).resolve()):
        raise ContractError("selected Vault path does not match plan")
    return {"name": name, "path": path, "version": version}


def roadmap_markdown_files(cli: ObsidianCLI, root: str) -> set[str]:
    return {
        line.strip() for line in cli.run(["files", f"folder={root}", "ext=md"]).splitlines()
        if line.strip()
    }


def require_eval_ok(result: Any, operation: str) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise ContractError(f"obsidian eval {operation} did not confirm success")
    return result


def apply_scaffold_transaction(cli: ObsidianCLI, directories: list[str], files: list[dict[str, str]]) -> None:
    try:
        require_eval_ok(cli.eval("batch-create", {"directories": directories, "files": files}), "batch-create")
    except Exception as error:
        raise ContractError(
            "scaffold transaction failed or its transport result is unknown; "
            "only the adapter may clean paths recorded as created by this transaction, "
            f"so no caller-side deletion was attempted: {error}"
        ) from error


def load_scaffold(path: Path) -> dict[str, Any]:
    raw = load_json(path, "scaffold spec")
    if raw.get("schema_version") != 3:
        raise ContractError("scaffold schema_version must be 3")
    root = validate_vault_path(raw.get("root", ""))
    base = raw.get("base")
    if not isinstance(base, dict) or validate_vault_path(base.get("path", "")) != roadmap_base_path(root):
        raise ContractError("base path must be <root>/<root-name>-Roadmap.base")
    plan_text = read_file(raw.get("curriculum_plan_file"), relative_to=path.parent, label="curriculum plan")
    plan = validate_curriculum(json.loads(plan_text))
    if plan["roadmap_root"] != root:
        raise ContractError("scaffold root must match curriculum roadmap_root")
    if raw.get("roadmap_kind", "topic") != plan["roadmap_kind"]:
        raise ContractError("scaffold roadmap_kind must match curriculum")
    base_content = read_file(base.get("content_file"), relative_to=path.parent, label="Base content")
    validate_base_root(base_content, root)
    capabilities = detect_capabilities(parse_base_views(base_content), require_all=True)
    directories = raw.get("directories")
    notes = raw.get("notes")
    if not isinstance(directories, list) or not isinstance(notes, list) or not notes:
        raise ContractError("scaffold directories and notes are required")
    normalized_directories = []
    for item in directories:
        if not isinstance(item, dict):
            raise ContractError("directory entries must be objects")
        directory = validate_vault_path(item.get("path", ""))
        if not directory.startswith(root + "/"):
            raise ContractError("directories must stay inside roadmap root")
        relative = PurePosixPath(directory).relative_to(PurePosixPath(root))
        if not relative.parts or any(not re.match(r"^\d{2}-", part) for part in relative.parts):
            raise ContractError("directories must be numbered declared children of root")
        normalized_directories.append({"path": directory, "role": item.get("role"), "keep": bool(item.get("keep"))})
    expected_directories = [
        {"path": f"{root}/{item['name']}", "role": item["role"]}
        for item in plan["directories"]
    ] + [
        {"path": f"{root}/{item['path']}", "role": item["role"]}
        for item in plan["subdirectories"]
    ]
    if [{"path": item["path"], "role": item["role"]} for item in normalized_directories] != expected_directories:
        raise ContractError("scaffold directories must exactly match the curriculum directory contract")
    if plan["roadmap_kind"] == "repository":
        repository = raw.get("repository")
        if not isinstance(repository, dict):
            raise ContractError("repository scaffold requires repository identity")
        projected = {
            "provider": repository.get("provider"), "name": repository.get("name"), "url": repository.get("url"),
            "default_branch": repository.get("default_branch"), "target_ref": repository.get("target_ref"),
            "commit": repository.get("commit"), "license_spdx": repository.get("license_spdx"),
            "verified_at": repository.get("verified_at"), "scope": repository.get("scope"),
            "core_slice": repository.get("core_slice"), "upstream_checked_at": repository.get("upstream_checked_at"),
            "upstream_status": repository.get("upstream_status"), "graduation_status": repository.get("graduation_status"),
        }
        if projected != plan["repository"]:
            raise ContractError("repository scaffold identity must match the curriculum authority")
    normalized_notes = []
    route_notes = []
    knowledge_by_unit: dict[str, int] = {}
    evidence_by_unit: dict[str, int] = {}
    records = [item["path"] for item in normalized_directories if item.get("role") == "records"]
    if len(records) != 1:
        raise ContractError("scaffold requires exactly one records directory")
    staged_notes = []
    for item in notes:
        note_path = validate_vault_path(item.get("path", ""), markdown=True)
        if not note_path.startswith(root + "/"):
            raise ContractError("note must be below roadmap root")
        content = read_file(item.get("content_file"), relative_to=path.parent, label=f"content for {note_path}")
        properties = parse_frontmatter(content)
        staged_notes.append((note_path, content, properties))
    evidence_paths = {
        str(properties.get("unit_id")): note_path
        for note_path, _, properties in staged_notes
        if properties.get("record_type") == "learning-evidence"
    }
    for note_path, content, properties in staged_notes:
        if properties.get("record_type") == "curriculum-map":
            if extract_curriculum(content) != plan:
                raise ContractError("route note curriculum does not match transaction plan")
            validate_visible_projection(content, plan)
            validate_curriculum_map_properties(properties, plan)
            validate_repository_visible_projection(content, plan)
            expected_route_path = f"{root}/{plan['directories'][0]['name']}/§01-学习路线图.md"
            if note_path != expected_route_path:
                raise ContractError("curriculum-map note must be the first note in the overview directory")
            route_notes.append(note_path)
        elif properties.get("record_type") == "learning-evidence":
            validate_learning_record(content)
            unit_id = str(properties.get("unit_id"))
            evidence_by_unit[unit_id] = evidence_by_unit.get(unit_id, 0) + 1
        elif properties.get("record_type") == "knowledge-note":
            validate_knowledge_note(content)
            unit_id = str(properties.get("unit_id"))
            knowledge_by_unit[unit_id] = knowledge_by_unit.get(unit_id, 0) + 1
        else:
            raise ContractError(f"unsupported record_type in {note_path}")
        if properties.get("record_type") != "curriculum-map":
            unit = next((entry for entry in plan["units"] if entry["unit_id"] == properties.get("unit_id")), None)
            if unit is None:
                raise ContractError(f"note unit_id is not planned: {note_path}")
            validate_planned_note(
                properties, target_path=note_path, unit=unit, roadmap_root=root,
                records_directory=records[0], roadmap_topic=plan["topic"],
                learning_goal=plan["learning_goal"],
                version_scope=plan["version_baseline"],
                paired_evidence_path=evidence_paths.get(unit["unit_id"], ""),
            )
        normalized_notes.append({"path": note_path, "content": content})
    if len(route_notes) != 1:
        raise ContractError("scaffold requires exactly one curriculum-map note")
    if not knowledge_by_unit or knowledge_by_unit != evidence_by_unit or any(count != 1 for count in knowledge_by_unit.values()):
        raise ContractError("scaffold requires exactly one knowledge note and one learning record for every created unit")
    return {
        "schema_version": 3, "vault_name": raw.get("vault_name"),
        "vault_path": raw.get("vault_path"), "root": root,
        "plan": plan, "base": {"path": base["path"], "content": base_content},
        "directories": normalized_directories, "notes": normalized_notes,
        "capabilities": sorted(capabilities),
    }


def cmd_probe(args: argparse.Namespace) -> dict[str, Any]:
    cli = ObsidianCLI(args.vault)
    return {"ok": True, "op": "probe", "vault": selected_vault(cli, None, None)}


def cmd_validate_curriculum(args: argparse.Namespace) -> dict[str, Any]:
    plan = validate_curriculum(load_json(Path(args.plan), "curriculum plan"))
    return {"ok": True, "op": "validate-curriculum", "schema_version": 3, "units": len(plan["units"])}


def cmd_validate_base(args: argparse.Namespace) -> dict[str, Any]:
    content = Path(args.base).read_text(encoding="utf-8")
    validate_base_root(content, validate_vault_path(args.root))
    capabilities = detect_capabilities(parse_base_views(content), require_all=True)
    return {"ok": True, "op": "validate-base", "capabilities": sorted(capabilities)}


def cmd_scaffold(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_scaffold(Path(args.spec))
    result = {"ok": True, "op": "scaffold", "mode": "apply" if args.apply else "dry-run", "root": spec["root"], "directories": [item["path"] for item in spec["directories"]], "files": [spec["base"]["path"], *[item["path"] for item in spec["notes"]]], "base_capabilities": spec["capabilities"]}
    if not args.apply:
        return result
    cli = ObsidianCLI(args.vault or spec["vault_name"])
    result["vault"] = selected_vault(cli, spec["vault_name"], spec["vault_path"])
    files = [{"path": spec["base"]["path"], "content": spec["base"]["content"]}, *spec["notes"]]
    files = [{"path": item["path"], "content": item["content"]} for item in files]
    files.extend({"path": f"{directory['path']}/.gitkeep", "content": ""} for directory in spec["directories"] if directory["keep"])
    apply_scaffold_transaction(cli, [spec["root"], *[item["path"] for item in spec["directories"]]], files)
    return result


def cmd_validate(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_scaffold(Path(args.spec))
    cli = ObsidianCLI(args.vault or spec["vault_name"])
    vault = selected_vault(cli, spec["vault_name"], spec["vault_path"])
    for path, expected in [(spec["base"]["path"], spec["base"]["content"]), *[(item["path"], item["content"]) for item in spec["notes"]]]:
        if cli.read(path) != expected:
            raise ContractError(f"read-back mismatch: {path}")
    cli.run(["base:query", f"path={spec['base']['path']}", "format=paths"])
    return {"ok": True, "op": "validate", "vault": vault, "root": spec["root"], "base_capabilities": spec["capabilities"], "read_back": True}


def cmd_write_note(args: argparse.Namespace) -> dict[str, Any]:
    plan_path = Path(args.plan)
    raw = load_json(plan_path, "note plan")
    if raw.get("schema_version") != 3:
        raise ContractError("note plan schema_version must be 3")
    route_path = validate_vault_path(raw.get("route_note", ""), markdown=True)
    cli = ObsidianCLI(args.vault or raw.get("vault_name"))
    vault = selected_vault(cli, raw.get("vault_name"), raw.get("vault_path"))
    route = cli.read(route_path)
    if sha256_text(route) != raw.get("expected_route_sha256"):
        raise ContractError("route note compare-and-swap failed")
    curriculum = extract_curriculum(route)
    root = curriculum["roadmap_root"]
    expected_route = f"{root}/{curriculum['directories'][0]['name']}/§01-学习路线图.md"
    if route_path != expected_route or raw.get("root") != root:
        raise ContractError("note plan root and route_note must match the curriculum authority")
    records_directory = f"{root}/{curriculum['records_directory']}"
    if raw.get("records_directory") != records_directory:
        raise ContractError("note plan records_directory must match the curriculum authority")
    writes_raw = raw.get("writes")
    if not isinstance(writes_raw, list) or len(writes_raw) != 2:
        raise ContractError("write-note requires one knowledge note and one learning record in a single transaction")
    normalized_writes = []
    units = []
    for index, item in enumerate(writes_raw):
        if not isinstance(item, dict):
            raise ContractError(f"writes[{index}] must be an object")
        target = validate_vault_path(item.get("path", ""), markdown=True)
        if not target.startswith(root + "/"):
            raise ContractError("note target must stay inside the curriculum roadmap_root")
        content = read_file(item.get("content_file"), relative_to=plan_path.parent, label=f"writes[{index}] content")
        properties = parse_frontmatter(content)
        unit = next((entry for entry in curriculum["units"] if entry["unit_id"] == properties.get("unit_id")), None)
        if unit is None:
            raise ContractError("note unit_id is not planned")
        expected_file = item.get("expected_current_file")
        expected = None if expected_file is None else read_file(expected_file, relative_to=plan_path.parent, label=f"writes[{index}] expected current")
        normalized_writes.append({"path": target, "content": content, "properties": properties, "unit": unit, "expected": expected})
        units.append(unit["unit_id"])
    if len(set(units)) != 1 or {item["properties"].get("record_type") for item in normalized_writes} != {"knowledge-note", "learning-evidence"}:
        raise ContractError("write-note pair must contain matching knowledge and evidence notes for one unit")
    unit = normalized_writes[0]["unit"]
    knowledge_write = next(item for item in normalized_writes if item["properties"].get("record_type") == "knowledge-note")
    evidence_write = next(item for item in normalized_writes if item["properties"].get("record_type") == "learning-evidence")

    existing_files = roadmap_markdown_files(cli, root)
    for item in normalized_writes:
        actual = cli.read(item["path"]) if item["path"] in existing_files else None
        if actual != item["expected"]:
            raise ContractError(f"note compare-and-swap failed before transaction: {item['path']}")
    existing_unit_paths: dict[str, set[str]] = {"knowledge-note": set(), "learning-evidence": set()}
    for existing_path in existing_files:
        if existing_path in {route_path, knowledge_write["path"], evidence_write["path"]}:
            continue
        try:
            existing_properties = parse_frontmatter(cli.read(existing_path))
        except ContractError:
            continue
        record_type = existing_properties.get("record_type")
        if existing_properties.get("unit_id") == unit["unit_id"] and record_type in existing_unit_paths:
            existing_unit_paths[record_type].add(existing_path)
    if existing_unit_paths["knowledge-note"] or existing_unit_paths["learning-evidence"]:
        raise ContractError("write-note would create duplicate knowledge or learning-evidence records for the unit")
    receipts: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw.get("trusted_evidence", [])):
        if not isinstance(item, dict):
            raise ContractError(f"trusted_evidence[{index}] must be an object")
        def external_file(field: str) -> Path:
            value = item.get(field)
            if not isinstance(value, str) or not value:
                raise ContractError(f"trusted_evidence[{index}].{field} is required")
            candidate = Path(value)
            return candidate if candidate.is_absolute() else plan_path.parent / candidate
        receipt_path = external_file("receipt_file")
        artifact_path = external_file("artifact_file")
        trust_key_path = external_file("trust_key_file")
        manifest_value = item.get("manifest_file")
        manifest_path = external_file("manifest_file") if manifest_value else None
        vault_path = Path(vault["path"]).resolve()
        external_paths = [receipt_path, artifact_path, trust_key_path, *([manifest_path] if manifest_path else [])]
        if any(candidate.resolve(strict=True) == vault_path or vault_path in candidate.resolve(strict=True).parents for candidate in external_paths):
            raise ContractError("verification receipts, artifacts, manifests, and trust keys must stay outside the Vault")
        receipt = validate_receipt(receipt_path, artifact_path, trust_key_path, unit=unit, manifest_path=manifest_path)
        if receipt["evidence_id"] in receipts:
            raise ContractError("trusted evidence ids must be unique")
        receipts[receipt["evidence_id"]] = receipt
    for item in normalized_writes:
        if item["properties"].get("record_type") == "knowledge-note":
            validate_knowledge_note(item["content"])
        else:
            validate_learning_record(item["content"], trusted_receipts=receipts)
        validate_planned_note(
            item["properties"], target_path=item["path"], unit=unit,
            roadmap_root=root, records_directory=records_directory,
            roadmap_topic=curriculum["topic"], learning_goal=curriculum["learning_goal"],
            version_scope=curriculum["version_baseline"],
            paired_evidence_path=evidence_write["path"],
        )
    result = {"ok": True, "op": "write-note", "mode": "apply" if args.apply else "dry-run", "paths": [item["path"] for item in normalized_writes], "unit_id": unit["unit_id"]}
    if args.apply:
        require_eval_ok(cli.eval("batch-write", {"files": [{"path": item["path"], "expected": item["expected"], "content": item["content"]} for item in normalized_writes]}), "batch-write")
        for item in normalized_writes:
            if cli.read(item["path"]) != item["content"]:
                raise ContractError("note pair read-back mismatch")
    return result


def normalize_renumber_plan(path: Path) -> dict[str, Any]:
    raw = load_json(path, "renumber plan")
    if raw.get("schema_version") != 3 or raw.get("roadmap_kind") != "topic":
        raise ContractError("renumber only accepts v3 topic routes; repository outer routes are fixed")
    root = validate_vault_path(raw.get("root", ""))
    expected = validate_directories(raw.get("expected_directories"), roadmap_kind="topic")
    final = validate_directories(raw.get("final_directories"), roadmap_kind="topic")
    expected_paths = {f"{root}/{item['name']}" for item in expected}
    final_paths = {f"{root}/{item['name']}" for item in final}
    protected = {
        f"{root}/{expected[0]['name']}",
        f"{root}/99-assets",
    }
    moves_raw = raw.get("moves")
    if not isinstance(moves_raw, list) or not moves_raw:
        raise ContractError("renumber plan requires moves")
    moves = []
    sources: set[str] = set(); targets: set[str] = set()
    for index, item in enumerate(moves_raw):
        if not isinstance(item, dict):
            raise ContractError(f"moves[{index}] must be an object")
        source = validate_vault_path(item.get("from", "")); target = validate_vault_path(item.get("to", ""))
        if PurePosixPath(source).parent.as_posix() != root or PurePosixPath(target).parent.as_posix() != root:
            raise ContractError("renumber moves must stay among direct children of roadmap root")
        if source not in expected_paths or target not in final_paths or source in protected:
            raise ContractError("renumber move is outside the declared route or targets a protected directory")
        if source in sources or target in targets:
            raise ContractError("renumber paths must be unique")
        sources.add(source); targets.add(target); moves.append({"from": source, "to": target})
    additions = []
    addition_paths: set[str] = set()
    for index, item in enumerate(raw.get("add_directories", [])):
        if not isinstance(item, dict):
            raise ContractError(f"add_directories[{index}] must be an object")
        addition = validate_vault_path(item.get("path", ""))
        if PurePosixPath(addition).parent.as_posix() != root or addition not in final_paths or addition in expected_paths:
            raise ContractError("added directory must be a new declared direct child of roadmap root")
        if addition in addition_paths:
            raise ContractError("added directories must be unique")
        addition_paths.add(addition)
        additions.append(addition)
    projected = (expected_paths - sources) | targets | set(additions)
    if projected != final_paths:
        raise ContractError("moves and additions do not produce final_directories exactly")
    updates = raw.get("property_updates")
    if not isinstance(updates, list):
        raise ContractError("property_updates must be an array")
    normalized_updates = []
    for index, item in enumerate(updates):
        if not isinstance(item, dict) or not isinstance(item.get("expected"), dict) or not isinstance(item.get("set"), dict):
            raise ContractError(f"property_updates[{index}] must have expected and set objects")
        update_path = validate_vault_path(item.get("path", ""), markdown=True)
        if not update_path.startswith(root + "/"):
            raise ContractError("property update must stay inside roadmap root")
        for field in ("stage_title", "stage_order"):
            if field not in item["expected"] or field not in item["set"]:
                raise ContractError(f"property_updates[{index}] must update {field}")
        stage_name = PurePosixPath(update_path).relative_to(PurePosixPath(root)).parts[0]
        stage_order = int(stage_name.split("-", 1)[0])
        if item["set"]["stage_title"] != stage_name or item["set"]["stage_order"] != stage_order:
            raise ContractError(f"property_updates[{index}] target properties must match the final parent stage")
        normalized_updates.append({"path": update_path, "expected": item["expected"], "set": item["set"]})
    links = []
    links_raw = raw.get("expected_links")
    if not isinstance(links_raw, list) or not links_raw:
        raise ContractError("renumber requires non-empty expected_links")
    for index, item in enumerate(links_raw):
        if not isinstance(item, dict):
            raise ContractError(f"expected_links[{index}] must be an object")
        source = validate_vault_path(item.get("source", ""), markdown=True)
        target = validate_vault_path(item.get("target", ""), markdown=True)
        if not source.startswith(root + "/") or not target.startswith(root + "/"):
            raise ContractError("expected links must stay inside roadmap root")
        links.append({"source": source, "target": target})
    route_update = raw.get("route_update")
    if not isinstance(route_update, dict):
        raise ContractError("renumber requires a route_update compare-and-swap")
    route_path = f"{root}/{final[0]['name']}/§01-学习路线图.md"
    if route_update.get("path") != route_path:
        raise ContractError("route_update must target the authoritative route note")
    expected_before = read_file(route_update.get("expected_before_file"), relative_to=path.parent, label="route expected-before")
    expected_after_moves = read_file(route_update.get("expected_after_moves_file"), relative_to=path.parent, label="route expected-after-moves")
    replacement = read_file(route_update.get("content_file"), relative_to=path.parent, label="route replacement")
    before_curriculum = extract_curriculum(expected_before)
    after_moves_curriculum = extract_curriculum(expected_after_moves)
    for label, current in (("expected-before", before_curriculum), ("expected-after-moves", after_moves_curriculum)):
        if current["roadmap_root"] != root or current["roadmap_kind"] != "topic" or current["directories"] != expected:
            raise ContractError(f"route_update {label} curriculum must match expected_directories")
        validate_visible_projection(expected_before if label == "expected-before" else expected_after_moves, current)
    curriculum = extract_curriculum(replacement)
    if curriculum["roadmap_root"] != root or curriculum["roadmap_kind"] != "topic" or curriculum["directories"] != final:
        raise ContractError("route_update curriculum must match final_directories")
    validate_visible_projection(replacement, curriculum)
    base = raw.get("base")
    if not isinstance(base, dict) or base.get("path") != roadmap_base_path(root) or not isinstance(base.get("view"), str):
        raise ContractError("renumber requires the route Base query contract")
    base_expected = base.get("expected_paths")
    if not isinstance(base_expected, list) or not base_expected or any(not isinstance(item, str) or not item.startswith(root + "/") for item in base_expected):
        raise ContractError("base.expected_paths must be non-empty and stay inside roadmap root")
    if route_path not in base_expected:
        raise ContractError("base.expected_paths must include the authoritative route note")
    return {
        "schema_version": 3, "vault_name": raw.get("vault_name"), "vault_path": raw.get("vault_path"),
        "root": root, "expected_directories": expected, "final_directories": final,
        "moves": moves, "add_directories": additions, "property_updates": normalized_updates,
        "expected_links": links, "route_update": {"path": route_path, "expected_before": expected_before, "expected_after_moves": expected_after_moves, "content": replacement},
        "base": base,
    }


def cmd_renumber(args: argparse.Namespace) -> dict[str, Any]:
    plan = normalize_renumber_plan(Path(args.plan))
    cli = ObsidianCLI(args.vault or plan["vault_name"])
    vault = selected_vault(cli, plan["vault_name"], plan["vault_path"])
    current_folders = cli.eval("list-directories", {"path": plan["root"]})["folders"]
    expected_folders = [f"{plan['root']}/{item['name']}" for item in plan["expected_directories"]]
    if current_folders != expected_folders:
        raise ContractError("current roadmap directories do not match expected_directories")
    if cli.read(plan["route_update"]["path"]) != plan["route_update"]["expected_before"]:
        raise ContractError("route_update expected-before compare-and-swap failed")
    files = {line.strip() for line in cli.run(["files", f"folder={plan['root']}", "ext=md"]).splitlines() if line.strip()}
    affected_after = set()
    affected_before = set()
    for path_value in files:
        for move in plan["moves"]:
            if path_value.startswith(move["from"] + "/"):
                affected_before.add(path_value)
                affected_after.add(move["to"] + path_value[len(move["from"]):])
    if affected_after != {item["path"] for item in plan["property_updates"]}:
        raise ContractError("property_updates must cover every Markdown file in moved directories exactly")
    if affected_after != {item["source"] for item in plan["expected_links"]}:
        raise ContractError("expected_links must cover every Markdown file in moved directories")
    final_markdown = (files - affected_before) | affected_after
    if set(plan["base"]["expected_paths"]) != final_markdown:
        raise ContractError("base.expected_paths must cover the final roadmap Markdown set exactly")
    result = {"ok": True, "op": "renumber", "mode": "apply" if args.apply else "dry-run", "vault": vault, "root": plan["root"], "moves": plan["moves"], "add_directories": plan["add_directories"]}
    if not args.apply:
        return result
    temporary = [(f"{PurePosixPath(item['from']).parent}/.learn-topic-move-{index:02d}", item) for index, item in enumerate(plan["moves"])]
    staged: list[tuple[str, dict[str, str]]] = []; completed: list[tuple[str, dict[str, str]]] = []
    added: list[str] = []; updated_fields: list[tuple[dict[str, Any], str]] = []; route_write_attempted = False
    try:
        for temp, item in temporary:
            cli.move(item["from"], temp); staged.append((temp, item))
        for temp, item in staged:
            cli.move(temp, item["to"]); completed.append((temp, item))
        for addition in plan["add_directories"]:
            added.append(addition)
            require_eval_ok(cli.eval("mkdir", {"path": addition}), "mkdir")
        for update in plan["property_updates"]:
            for field in ("stage_title", "stage_order"):
                actual = cli.run(["property:read", f"path={update['path']}", f"name={field}"])
                if actual != str(update["expected"][field]):
                    raise ContractError(f"property compare-and-swap failed: {update['path']} {field}")
        for update in plan["property_updates"]:
            for field in ("stage_title", "stage_order"):
                property_type = "number" if field == "stage_order" else "text"
                updated_fields.append((update, field))
                cli.run(["property:set", f"path={update['path']}", f"name={field}", f"value={update['set'][field]}", f"type={property_type}"])
        if cli.read(plan["route_update"]["path"]) != plan["route_update"]["expected_after_moves"]:
            raise ContractError("route changed unexpectedly during renumber")
        route_write_attempted = True
        require_eval_ok(cli.eval("write", {"path": plan["route_update"]["path"], "expected": plan["route_update"]["expected_after_moves"], "content": plan["route_update"]["content"]}), "write")
        for link in plan["expected_links"]:
            output = cli.run(["links", f"path={link['source']}"])
            if link["target"] not in output and PurePosixPath(link["target"]).stem not in output:
                raise ContractError(f"expected link is missing: {link['source']} -> {link['target']}")
        output_paths = {line.strip() for line in cli.run(["base:query", f"path={plan['base']['path']}", f"view={plan['base']['view']}", "format=paths"]).splitlines() if line.strip()}
        if output_paths != set(plan["base"]["expected_paths"]):
            raise ContractError("Base query paths do not exactly match the final roadmap Markdown set")
    except Exception as error:
        rollback_errors = []
        if route_write_attempted:
            try:
                route_path = plan["route_update"]["path"]
                current_route = cli.read(route_path)
                if current_route == plan["route_update"]["content"]:
                    require_eval_ok(cli.eval("write", {"path": route_path, "expected": plan["route_update"]["content"], "content": plan["route_update"]["expected_after_moves"]}), "write rollback")
                elif current_route != plan["route_update"]["expected_after_moves"]:
                    raise ContractError("route rollback found an unexpected current value")
                if cli.read(route_path) != plan["route_update"]["expected_after_moves"]:
                    raise ContractError("route rollback read-back mismatch")
            except Exception as rollback_error: rollback_errors.append(str(rollback_error))
        for update, field in reversed(updated_fields):
            try:
                property_type = "number" if field == "stage_order" else "text"
                cli.run(["property:set", f"path={update['path']}", f"name={field}", f"value={update['expected'][field]}", f"type={property_type}"])
            except Exception as rollback_error: rollback_errors.append(str(rollback_error))
        for addition in reversed(added):
            try: require_eval_ok(cli.eval("remove-if-exists", {"path": addition}), "remove-if-exists")
            except Exception as rollback_error: rollback_errors.append(str(rollback_error))
        for _, item in reversed(completed):
            try: cli.move(item["to"], item["from"])
            except Exception as rollback_error: rollback_errors.append(str(rollback_error))
        for temp, item in reversed(staged[len(completed):]):
            try: cli.move(temp, item["from"])
            except Exception as rollback_error: rollback_errors.append(str(rollback_error))
        if rollback_errors:
            raise ContractError(f"renumber failed and rollback was incomplete: {error}; {'; '.join(rollback_errors)}") from error
        raise
    return result


def cmd_migrate(args: argparse.Namespace) -> dict[str, Any]:
    raw = load_json(Path(args.plan), "migration plan")
    if raw.get("source_schema") not in {1, 2} or raw.get("target_schema") != 3:
        raise ContractError("migration must be legacy/v2 to v3")
    preview = build_migration_preview(
        raw.get("records", []),
        target_curriculum=raw.get("target_curriculum"),
        unit_mappings=raw.get("unit_mappings"),
    )
    result = {"ok": True, "op": "migrate", "mode": "apply" if args.apply else "dry-run", "preview": preview, "preserves": ["answers", "practice", "reviews", "attempts"], "dual_write": False}
    if args.apply:
        if not args.output:
            raise ContractError("migrate --apply requires --output")
        output = Path(args.output)
        if output.exists():
            raise ContractError("migration output already exists")
        output.write_text(json.dumps(preview, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        result["output"] = str(output)
    return result


def cmd_trash(args: argparse.Namespace) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.run_id):
        raise ContractError("run-id is invalid")
    root = validate_vault_path(args.root)
    result = {"ok": True, "op": "trash-validation", "mode": "apply" if args.apply else "dry-run", "root": root}
    if args.apply:
        cli = ObsidianCLI(args.vault)
        expected_root = f"99-LearnTopic-Acceptance-{args.run_id}"
        if PurePosixPath(root).name != expected_root:
            raise ContractError(f"trash-validation root must end with {expected_root}")
        if not args.marker.startswith(root + "/"):
            raise ContractError("acceptance marker must be below the exact test root")
        marker = cli.read(args.marker)
        if f"learn_topic_test_run: {args.run_id}" not in marker:
            raise ContractError("acceptance marker does not match run-id")
        cli.run(["delete", f"path={root}"])
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault")
    actions = parser.add_subparsers(dest="command", required=True)
    probe = actions.add_parser("probe"); probe.set_defaults(handler=cmd_probe)
    curriculum = actions.add_parser("validate-curriculum"); curriculum.add_argument("--plan", required=True); curriculum.set_defaults(handler=cmd_validate_curriculum)
    base = actions.add_parser("validate-base"); base.add_argument("--base", required=True); base.add_argument("--root", required=True); base.set_defaults(handler=cmd_validate_base)
    scaffold = actions.add_parser("scaffold"); scaffold.add_argument("--spec", required=True); scaffold.add_argument("--apply", action="store_true"); scaffold.set_defaults(handler=cmd_scaffold)
    validate = actions.add_parser("validate"); validate.add_argument("--spec", required=True); validate.set_defaults(handler=cmd_validate)
    write = actions.add_parser("write-note"); write.add_argument("--plan", required=True); write.add_argument("--apply", action="store_true"); write.set_defaults(handler=cmd_write_note)
    renumber = actions.add_parser("renumber"); renumber.add_argument("--plan", required=True); renumber.add_argument("--apply", action="store_true"); renumber.set_defaults(handler=cmd_renumber)
    migrate = actions.add_parser("migrate"); migrate.add_argument("--plan", required=True); migrate.add_argument("--output"); migrate.add_argument("--apply", action="store_true"); migrate.set_defaults(handler=cmd_migrate)
    trash = actions.add_parser("trash-validation"); trash.add_argument("--root", required=True); trash.add_argument("--marker", required=True); trash.add_argument("--run-id", required=True); trash.add_argument("--apply", action="store_true"); trash.set_defaults(handler=cmd_trash)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = args.handler(args)
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as error:
        emit({"ok": False, "op": args.command, "error": str(error)}, stream=sys.stderr)
        return 1
    emit(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

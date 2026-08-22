from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "roadmap_cli.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("roadmap_cli", SCRIPT)
assert SPEC and SPEC.loader
roadmap_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(roadmap_cli)
ROOT = SCRIPT.parents[1]


def curriculum() -> dict:
    return {
        "schema_version": 3, "roadmap_kind": "topic", "roadmap_root": "Roadmap",
        "directories": [
            {"name": "01-主题概述", "role": "overview"}, {"name": "02-核心", "role": "formal"},
            {"name": "03-复习与综合应用", "role": "review"}, {"name": "04-学习记录", "role": "records"},
            {"name": "99-assets", "role": "assets"},
        ],
        "subdirectories": [],
        "records_directory": "04-学习记录", "topic": "主题", "learning_goal": "独立解释主题",
        "version_baseline": "v1", "source_checked_at": "2026-08-21",
        "units": [{
            "unit_id": "CORE-01", "stage": "02-核心", "note_path": "02-核心/§01-核心.md",
            "title": "核心机制", "document_type": "原理解释", "learning_outcome": "解释核心机制",
            "prerequisites": [], "knowledge_ownership": ["CORE-MECHANISM"],
            "evidence_profile": "concept-explanation", "assessment": "分析一个新场景",
        }],
    }


def route_note(plan: dict) -> str:
    contract = json.dumps(plan, ensure_ascii=False, indent=2)
    return f'''---
title: 主题学习路线图
tags:
  - 学习路线/主题
date: 2026-08-21
updated: 2026-08-21
status: 待核验
category: 技术
record_type: curriculum-map
schema_version: 3
roadmap_root: Roadmap
roadmap_kind: topic
roadmap_topic: 主题
roadmap_status: 进行中
learning_goal: 独立解释主题
stage_title: 01-主题概述
stage_order: 1
lesson_order: 1
version_baseline: v1
version_scope: v1
source_checked_at: 2026-08-21
upstream_status: unchanged
verified_at: 2026-08-21
sources:
  - https://example.com/topic-docs
---
# 主题学习路线图

## 知识依赖图

```mermaid
flowchart LR
  %% unit: CORE-01
  CORE-01["核心机制"]
```

## 单元目录

| 单元 ID | 阶段与计划文件 | 正文类型 | 单项可验收成果 | 前置单元 | Evidence profile | 验收方式 |
| --- | --- | --- | --- | --- | --- | --- |
| `CORE-01` | `02-核心/§01-核心.md` | 原理解释 | 解释核心机制 | 无 | `concept-explanation` | 分析一个新场景 |

## 知识点唯一归属

| 知识点 ID | 唯一所属单元 |
| --- | --- |
| `CORE-MECHANISM` | `CORE-01` |

## 机器可读课程合同

<!-- learn-topic-curriculum:start -->
```json
{contract}
```
<!-- learn-topic-curriculum:end -->
'''


def knowledge_note() -> str:
    detail = "这个段落用一个具体的新场景解释机制、边界与可观察结果，确保内容不是标题或目录占位。"
    return f'''---
title: 核心机制
tags:
  - 学习路线/主题
date: 2026-08-21
updated: 2026-08-21
status: 待核验
category: 技术
record_type: knowledge-note
document_type: 原理解释
roadmap_topic: 主题
roadmap_root: Roadmap
learning_goal: 独立解释主题
unit_id: CORE-01
learning_outcome: 解释核心机制
knowledge_ownership:
  - CORE-MECHANISM
hard_prerequisites: []
assessment_method: 分析一个新场景
evidence_profile: concept-explanation
evidence_note: "[[Roadmap/04-学习记录/§01-核心-学习记录]]"
stage_title: 02-核心
stage_order: 2
lesson_order: 1
verified_at: 2026-08-21
version_scope: v1
sources:
  - https://example.com/topic-docs
coverage_status: 完整覆盖
---
# 核心机制
## 核心问题
{detail}
## 心智模型
{detail}
## 工作机制
{detail}
## 错误心智模型
{detail}
## 新场景分析
{detail}
'''


def learning_record() -> str:
    return '''---
title: 核心机制学习记录
tags:
  - 学习路线/主题
date: 2026-08-21
updated: 2026-08-21
status: 草稿
category: 技术
record_type: learning-evidence
schema_version: 3
roadmap_topic: 主题
roadmap_root: Roadmap
learning_goal: 独立解释主题
unit_id: CORE-01
content_note: "[[Roadmap/02-核心/§01-核心]]"
stage_title: 04-学习记录
stage_order: 4
lesson_order: 1
progress_status: 学习中
mastery_status: 未证明
evidence_profile: concept-explanation
mastery_evidence: []
version_scope: v1
---
# 核心机制学习记录
'''


def renumber_runtime_plan() -> dict:
    return {
        "vault_name": "Vault", "vault_path": None, "root": "Roadmap",
        "expected_directories": [
            {"name": "01-主题概述", "role": "overview"}, {"name": "02-旧", "role": "formal"},
            {"name": "03-复习与综合应用", "role": "review"}, {"name": "04-学习记录", "role": "records"},
            {"name": "99-assets", "role": "assets"},
        ],
        "final_directories": [],
        "moves": [{"from": "Roadmap/02-旧", "to": "Roadmap/02-新"}], "add_directories": [],
        "property_updates": [{"path": "Roadmap/02-新/§01-X.md", "expected": {"stage_title": "02-旧", "stage_order": 2}, "set": {"stage_title": "02-新", "stage_order": 2}}],
        "expected_links": [{"source": "Roadmap/02-新/§01-X.md", "target": "Roadmap/04-学习记录/§01-X-学习记录.md"}],
        "route_update": {"path": "Roadmap/01-主题概述/§01-学习路线图.md", "expected_before": "route", "expected_after_moves": "route", "content": "new route"},
        "base": {"path": "Roadmap/Roadmap-Roadmap.base", "view": "route", "expected_paths": ["Roadmap/01-主题概述/§01-学习路线图.md", "Roadmap/02-新/§01-X.md"]},
    }


class RoadmapCliTests(unittest.TestCase):
    def test_parser_exposes_v3_commands(self) -> None:
        choices = roadmap_cli.build_parser()._subparsers._group_actions[0].choices
        self.assertEqual(set(choices), {"probe", "validate-curriculum", "validate-base", "scaffold", "validate", "write-note", "renumber", "migrate", "trash-validation"})

    def test_base_template_has_five_semantic_capabilities(self) -> None:
        path = ROOT / "templates" / "topic-roadmap.template.base"
        with tempfile.TemporaryDirectory() as temporary:
            rendered = Path(temporary) / "Roadmap.base"
            rendered.write_text(path.read_text(encoding="utf-8").replace("{{ROADMAP_FILTER_JSON}}", '"file.inFolder(\\"Roadmap\\")"'), encoding="utf-8")
            result = roadmap_cli.cmd_validate_base(type("Args", (), {"base": str(rendered), "root": "Roadmap"})())
        self.assertEqual(set(result["capabilities"]), {"route", "current", "review-due", "blocked", "evidence"})

    def test_migration_preview_is_deterministic_and_never_dual_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            plan = Path(temporary) / "migration.json"
            plan.write_text(json.dumps({
                "source_schema": 2, "target_schema": 3,
                "records": [{"unit_id": "ID-1", "learning_status": "已掌握", "answers": ["kept"], "attempts": [{"id": "a"}], "reviews": []}],
                "target_curriculum": curriculum(),
                "unit_mappings": [{"legacy_unit_id": "ID-1", "target_unit_id": "CORE-01", "legacy_content": "Old/§01.md", "target_note_path": "02-核心/§01-核心.md", "legacy_knowledge_ownership": ["CORE-MECHANISM"]}],
            }), encoding="utf-8")
            args = type("Args", (), {"plan": str(plan), "apply": False, "output": None})()
            first = roadmap_cli.cmd_migrate(args)
            second = roadmap_cli.cmd_migrate(args)
            self.assertEqual(first, second)
            self.assertFalse(first["dual_write"])
            self.assertEqual(first["preview"]["records"][0]["answers"], ["kept"])

    def test_scaffold_enforces_exact_topology_and_visible_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            plan = curriculum()
            (folder / "curriculum.json").write_text(json.dumps(plan), encoding="utf-8")
            (folder / "route.md").write_text(route_note(plan), encoding="utf-8")
            (folder / "knowledge.md").write_text(knowledge_note(), encoding="utf-8")
            (folder / "record.md").write_text(learning_record(), encoding="utf-8")
            base = (ROOT / "templates" / "topic-roadmap.template.base").read_text(encoding="utf-8")
            (folder / "route.base").write_text(base.replace("{{ROADMAP_FILTER_JSON}}", '"file.inFolder(\\"Roadmap\\")"'), encoding="utf-8")
            directories = [{"path": f"Roadmap/{item['name']}", "role": item["role"], "keep": True} for item in plan["directories"]]
            spec = {
                "schema_version": 3, "roadmap_kind": "topic", "root": "Roadmap",
                "curriculum_plan_file": "curriculum.json",
                "base": {"path": "Roadmap/Roadmap-Roadmap.base", "content_file": "route.base"},
                "directories": directories,
                "notes": [
                    {"path": "Roadmap/01-主题概述/§01-学习路线图.md", "content_file": "route.md"},
                    {"path": "Roadmap/02-核心/§01-核心.md", "content_file": "knowledge.md"},
                    {"path": "Roadmap/04-学习记录/§01-核心-学习记录.md", "content_file": "record.md"},
                ],
            }
            spec_path = folder / "spec.json"; spec_path.write_text(json.dumps(spec), encoding="utf-8")
            self.assertEqual(roadmap_cli.load_scaffold(spec_path)["root"], "Roadmap")
            (folder / "knowledge.md").write_text("---\nrecord_type: knowledge-note\n---\n# 空文\n", encoding="utf-8")
            with self.assertRaises(roadmap_cli.ContractError):
                roadmap_cli.load_scaffold(spec_path)
            (folder / "knowledge.md").write_text(knowledge_note(), encoding="utf-8")
            spec["notes"].append({"path": "Roadmap/04-学习记录/§02-重复-学习记录.md", "content_file": "record.md"})
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(roadmap_cli.ContractError):
                roadmap_cli.load_scaffold(spec_path)
            spec["notes"].pop()
            spec["directories"][1]["path"] = "Roadmap/02-漂移"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(roadmap_cli.ContractError):
                roadmap_cli.load_scaffold(spec_path)

    def test_write_note_requires_a_matching_two_file_unit_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            plan = curriculum(); route = route_note(plan)
            (folder / "knowledge.md").write_text(knowledge_note(), encoding="utf-8")
            (folder / "record.md").write_text(learning_record(), encoding="utf-8")
            raw = {
                "schema_version": 3, "vault_name": "Vault", "root": "Roadmap",
                "route_note": "Roadmap/01-主题概述/§01-学习路线图.md",
                "expected_route_sha256": roadmap_cli.sha256_text(route),
                "records_directory": "Roadmap/04-学习记录",
                "writes": [
                    {"path": "Roadmap/02-核心/§01-核心.md", "content_file": "knowledge.md", "expected_current_file": None},
                    {"path": "Roadmap/04-学习记录/§01-核心-学习记录.md", "content_file": "record.md", "expected_current_file": None},
                ],
                "trusted_evidence": [],
            }
            plan_path = folder / "note-plan.json"; plan_path.write_text(json.dumps(raw), encoding="utf-8")
            class FakeCLI:
                def read(self, path):
                    if path.endswith("学习路线图.md"): return route
                    raise roadmap_cli.ContractError("missing")
                def run(self, arguments, **kwargs):
                    if arguments[0] == "files": return ""
                    return ""
            args = type("Args", (), {"plan": str(plan_path), "vault": "Vault", "apply": False})()
            with mock.patch.object(roadmap_cli, "ObsidianCLI", return_value=FakeCLI()), mock.patch.object(roadmap_cli, "selected_vault", return_value={"name": "Vault", "path": "/tmp/vault", "version": "1"}):
                result = roadmap_cli.cmd_write_note(args)
                self.assertEqual(len(result["paths"]), 2)
                raw["writes"].pop(); plan_path.write_text(json.dumps(raw), encoding="utf-8")
                with self.assertRaises(roadmap_cli.ContractError):
                    roadmap_cli.cmd_write_note(args)

    def test_write_note_rejects_existing_duplicate_unit_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); plan = curriculum(); route = route_note(plan)
            new_knowledge = knowledge_note().replace("§01-核心-学习记录", "§99-第二份-学习记录")
            (folder / "knowledge.md").write_text(new_knowledge, encoding="utf-8")
            (folder / "old-knowledge.md").write_text(knowledge_note(), encoding="utf-8")
            new_record = learning_record().replace("§01-核心-学习记录", "§99-第二份-学习记录").replace("lesson_order: 1", "lesson_order: 99")
            (folder / "record.md").write_text(new_record, encoding="utf-8")
            raw = {
                "schema_version": 3, "vault_name": "Vault", "root": "Roadmap",
                "route_note": "Roadmap/01-主题概述/§01-学习路线图.md",
                "expected_route_sha256": roadmap_cli.sha256_text(route), "records_directory": "Roadmap/04-学习记录",
                "writes": [
                    {"path": "Roadmap/02-核心/§01-核心.md", "content_file": "knowledge.md", "expected_current_file": "old-knowledge.md"},
                    {"path": "Roadmap/04-学习记录/§99-第二份-学习记录.md", "content_file": "record.md", "expected_current_file": None},
                ], "trusted_evidence": [],
            }
            plan_path = folder / "note-plan.json"; plan_path.write_text(json.dumps(raw), encoding="utf-8")
            existing_record_path = "Roadmap/04-学习记录/§01-核心-学习记录.md"
            class FakeCLI:
                def run(self, arguments, **kwargs):
                    if arguments[0] == "files":
                        return "\n".join([raw["route_note"], raw["writes"][0]["path"], existing_record_path])
                    return ""
                def read(self, path):
                    return {raw["route_note"]: route, raw["writes"][0]["path"]: knowledge_note(), existing_record_path: learning_record()}[path]
            args = type("Args", (), {"plan": str(plan_path), "vault": "Vault", "apply": False})()
            with mock.patch.object(roadmap_cli, "ObsidianCLI", return_value=FakeCLI()), mock.patch.object(roadmap_cli, "selected_vault", return_value={"name": "Vault", "path": "/tmp/vault", "version": "1"}):
                with self.assertRaises(roadmap_cli.ContractError):
                    roadmap_cli.cmd_write_note(args)

    def test_knowledge_gate_rejects_fenced_fake_sections_and_weak_sources(self) -> None:
        valid = knowledge_note()
        with self.assertRaises(roadmap_cli.ContractError):
            roadmap_cli.validate_knowledge_note(valid.replace("https://example.com/topic-docs", "x"))
        frontmatter, _ = valid.split("\n---\n", 1)
        detail = "这个围栏里的段落看似很长，但它只是示例代码，不能冒充读者真正可见的知识正文和章节。"
        fenced = frontmatter + "\n---\n# 核心机制\n```markdown\n" + "\n".join(f"## {heading}\n{detail}" for heading in ("核心问题", "心智模型", "工作机制", "错误心智模型", "新场景分析")) + "\n```\n"
        with self.assertRaises(roadmap_cli.ContractError):
            roadmap_cli.validate_knowledge_note(fenced)
        nested_fence = frontmatter + "\n---\n# 核心机制\n````markdown\n```markdown\n" + "\n".join(f"## {heading}\n{detail}" for heading in ("核心问题", "心智模型", "工作机制", "错误心智模型", "新场景分析")) + "\n```\n````\n"
        with self.assertRaises(roadmap_cli.ContractError):
            roadmap_cli.validate_knowledge_note(nested_fence)
        tilde_fence = frontmatter + "\n---\n# 核心机制\n~~~markdown\n" + "\n".join(f"## {heading}\n{detail}" for heading in ("核心问题", "心智模型", "工作机制", "错误心智模型", "新场景分析")) + "\n~~~\n"
        with self.assertRaises(roadmap_cli.ContractError):
            roadmap_cli.validate_knowledge_note(tilde_fence)
        with self.assertRaises(roadmap_cli.ContractError):
            roadmap_cli.validate_knowledge_note(frontmatter + "\n---\n# 核心机制\n````markdown\n## 核心问题\n未闭合围栏")

    def test_batch_write_contract_surfaces_incomplete_rollback(self) -> None:
        source = (SCRIPT.parent / "learn_topic" / "obsidian_adapter.py").read_text(encoding="utf-8")
        self.assertIn("batch-write failed and rollback was incomplete", source)
        batch_write = source.split('if ("{operation}" === "batch-write")', 1)[1].split('if ("{operation}" === "list-directories")', 1)[0]
        self.assertNotIn("catch {{}}", batch_write)

    def test_batch_create_contract_tracks_intents_and_surfaces_incomplete_rollback(self) -> None:
        source = (SCRIPT.parent / "learn_topic" / "obsidian_adapter.py").read_text(encoding="utf-8")
        batch_create = source.split('if ("{operation}" === "batch-create")', 1)[1].split('if ("{operation}" === "batch-write")', 1)[0]
        self.assertIn("batch-create failed and rollback was incomplete", batch_create)
        self.assertLess(batch_create.index("createdDirectories.push(path)"), batch_create.index("await adapter.mkdir(path)"))
        self.assertLess(batch_create.index("createdFiles.push(item.path)"), batch_create.index("await adapter.write(item.path, item.content)"))
        self.assertNotIn("catch {{}}", batch_create)

    def test_scaffold_cas_conflict_never_deletes_preexisting_targets(self) -> None:
        directories = ["Roadmap", "Roadmap/01-概述"]
        files = [
            {"path": "Roadmap/Roadmap-Roadmap.base", "content": "new base"},
            {"path": "Roadmap/01-概述/§01-路线.md", "content": "new route"},
        ]
        original = {
            "Roadmap": None,
            "Roadmap/01-概述": None,
            "Roadmap/Roadmap-Roadmap.base": b"existing base bytes",
            "Roadmap/01-概述/§01-路线.md": b"existing route bytes",
        }
        for conflict in original:
            class FakeCLI:
                def __init__(self) -> None:
                    self.state = dict(original); self.calls = []
                def eval(self, operation, payload):
                    self.calls.append((operation, payload))
                    raise roadmap_cli.ContractError(f"target already exists: {conflict}")
            fake = FakeCLI()
            with self.subTest(conflict=conflict), self.assertRaisesRegex(roadmap_cli.ContractError, "no caller-side deletion was attempted"):
                roadmap_cli.apply_scaffold_transaction(fake, directories, files)
            self.assertEqual(fake.state, original)
            self.assertEqual([operation for operation, _ in fake.calls], ["batch-create"])

    def test_scaffold_unknown_transport_never_guesses_cleanup_ownership(self) -> None:
        class FakeCLI:
            def __init__(self) -> None: self.calls = []
            def eval(self, operation, payload):
                self.calls.append(operation)
                raise roadmap_cli.ContractError("transport result unknown")
        fake = FakeCLI()
        with self.assertRaisesRegex(roadmap_cli.ContractError, "transport result is unknown"):
            roadmap_cli.apply_scaffold_transaction(fake, ["Roadmap"], [{"path": "Roadmap/route.md", "content": "route"}])
        self.assertEqual(fake.calls, ["batch-create"])

    def test_renumber_rejects_external_moves_and_repository_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "renumber.json"
            minimal = {
                "schema_version": 3, "roadmap_kind": "topic", "root": "Roadmap",
                "expected_directories": curriculum()["directories"],
                "final_directories": curriculum()["directories"],
                "moves": [{"from": "Outside/02-核心", "to": "Roadmap/02-核心"}],
            }
            path.write_text(json.dumps(minimal), encoding="utf-8")
            with self.assertRaises(roadmap_cli.ContractError):
                roadmap_cli.normalize_renumber_plan(path)
            minimal["roadmap_kind"] = "repository"
            path.write_text(json.dumps(minimal), encoding="utf-8")
            with self.assertRaises(roadmap_cli.ContractError):
                roadmap_cli.normalize_renumber_plan(path)

    def test_renumber_rolls_back_each_property_field_after_partial_failure(self) -> None:
        plan = renumber_runtime_plan()
        class FakeCLI:
            def __init__(self) -> None:
                self.fields = {"stage_title": "02-旧", "stage_order": "2"}
                self.failed = False
            def eval(self, operation, payload):
                if operation == "list-directories":
                    return {"folders": ["Roadmap/01-主题概述", "Roadmap/02-旧", "Roadmap/03-复习与综合应用", "Roadmap/04-学习记录", "Roadmap/99-assets"]}
                return {"ok": True}
            def read(self, path): return "route"
            def move(self, source, target): pass
            def run(self, arguments, **kwargs):
                if arguments[0] == "help": return "help"
                if arguments[:2] == ["vault", "info=name"]: return "Vault"
                if arguments[:2] == ["vault", "info=path"]: return "/tmp/vault"
                if arguments[0] == "version": return "1"
                if arguments[0] == "files": return "Roadmap/01-主题概述/§01-学习路线图.md\nRoadmap/02-旧/§01-X.md"
                if arguments[0] == "property:read":
                    field = next(item.split("=", 1)[1] for item in arguments if item.startswith("name="))
                    return self.fields[field]
                if arguments[0] == "property:set":
                    field = next(item.split("=", 1)[1] for item in arguments if item.startswith("name="))
                    value = next(item.split("=", 1)[1] for item in arguments if item.startswith("value="))
                    if field == "stage_order" and not self.failed:
                        self.fields[field] = value
                        self.failed = True
                        raise roadmap_cli.ContractError("injected write-after-effect failure")
                    self.fields[field] = value
                    return ""
                return ""
        fake = FakeCLI()
        args = type("Args", (), {"plan": "unused", "vault": "Vault", "apply": True})()
        with mock.patch.object(roadmap_cli, "normalize_renumber_plan", return_value=plan), mock.patch.object(roadmap_cli, "ObsidianCLI", return_value=fake), mock.patch.object(roadmap_cli, "selected_vault", return_value={"name": "Vault", "path": "/tmp/vault", "version": "1"}):
            with self.assertRaises(roadmap_cli.ContractError):
                roadmap_cli.cmd_renumber(args)
        self.assertEqual(fake.fields, {"stage_title": "02-旧", "stage_order": "2"})

    def test_renumber_rolls_back_route_on_false_result_and_write_after_effect(self) -> None:
        plan = renumber_runtime_plan()
        for failure_mode in ("ok-false", "write-after-effect"):
            class FakeCLI:
                def __init__(self) -> None:
                    self.fields = {"stage_title": "02-旧", "stage_order": "2"}
                    self.route = "route"
                    self.directories = {"Roadmap/02-旧"}
                    self.failed = False
                def eval(self, operation, payload):
                    if operation == "list-directories":
                        return {"ok": True, "folders": ["Roadmap/01-主题概述", "Roadmap/02-旧", "Roadmap/03-复习与综合应用", "Roadmap/04-学习记录", "Roadmap/99-assets"]}
                    if operation == "write":
                        if not self.failed:
                            self.failed = True
                            if failure_mode == "write-after-effect":
                                self.route = payload["content"]
                                raise roadmap_cli.ContractError("injected write-after-effect")
                            return {"ok": False}
                        self.route = payload["content"]
                        return {"ok": True}
                    return {"ok": True}
                def read(self, path): return self.route
                def move(self, source, target):
                    self.directories.remove(source); self.directories.add(target)
                def run(self, arguments, **kwargs):
                    if arguments[0] == "files": return "Roadmap/01-主题概述/§01-学习路线图.md\nRoadmap/02-旧/§01-X.md"
                    if arguments[0] == "property:read":
                        field = next(item.split("=", 1)[1] for item in arguments if item.startswith("name="))
                        return self.fields[field]
                    if arguments[0] == "property:set":
                        field = next(item.split("=", 1)[1] for item in arguments if item.startswith("name="))
                        self.fields[field] = next(item.split("=", 1)[1] for item in arguments if item.startswith("value="))
                    return ""
            fake = FakeCLI()
            args = type("Args", (), {"plan": "unused", "vault": "Vault", "apply": True})()
            with self.subTest(failure_mode=failure_mode), mock.patch.object(roadmap_cli, "normalize_renumber_plan", return_value=plan), mock.patch.object(roadmap_cli, "ObsidianCLI", return_value=fake), mock.patch.object(roadmap_cli, "selected_vault", return_value={"name": "Vault", "path": "/tmp/vault", "version": "1"}):
                with self.assertRaises(roadmap_cli.ContractError):
                    roadmap_cli.cmd_renumber(args)
            self.assertEqual(fake.route, "route")
            self.assertEqual(fake.fields, {"stage_title": "02-旧", "stage_order": "2"})
            self.assertEqual(fake.directories, {"Roadmap/02-旧"})


if __name__ == "__main__":
    unittest.main(verbosity=2)

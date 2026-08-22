from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from learn_topic.curriculum import (  # noqa: E402
    ContractError, REPOSITORY_DIRECTORIES, extract_curriculum,
    validate_curriculum, validate_visible_projection,
)


class CurriculumTests(unittest.TestCase):
    def fixture(self) -> dict:
        return {
            "schema_version": 3,
            "roadmap_kind": "topic",
            "roadmap_root": "Learning/Rust-Ownership",
            "directories": [
                {"name": "01-Rust所有权概述", "role": "overview"},
                {"name": "02-正式学习", "role": "formal"},
                {"name": "03-深入与拓展", "role": "extension"},
                {"name": "04-复习与综合应用", "role": "review"},
                {"name": "05-学习记录", "role": "records"},
                {"name": "99-assets", "role": "assets"},
            ],
            "subdirectories": [],
            "records_directory": "05-学习记录",
            "topic": "Rust Ownership",
            "learning_goal": "Explain and apply ownership to prevent invalid aliasing",
            "version_baseline": "stable channel checked at route creation",
            "source_checked_at": "2026-08-21",
            "units": [
                {
                    "unit_id": "OWN-01",
                    "stage": "01-Rust所有权概述",
                    "note_path": "01-Rust所有权概述/§02-所有权心智模型.md",
                    "title": "所有权心智模型",
                    "document_type": "原理解释",
                    "learning_outcome": "Explain why a moved value cannot be reused",
                    "prerequisites": [],
                    "knowledge_ownership": ["ownership.move"],
                    "evidence_profile": "concept-explanation",
                    "assessment": "Explain a new move scenario and predict the compiler result",
                }
            ],
        }

    def test_validates_v3_and_extracts_authority(self) -> None:
        plan = validate_curriculum(self.fixture())
        note = "before\n<!-- learn-topic-curriculum:start -->\n```json\n" + json.dumps(plan) + "\n```\n<!-- learn-topic-curriculum:end -->\nafter"
        self.assertEqual(extract_curriculum(note), plan)

    def test_rejects_v2_duplicate_ownership_and_cycles(self) -> None:
        plan = self.fixture()
        plan["schema_version"] = 2
        with self.assertRaises(ContractError):
            validate_curriculum(plan)

    def test_topic_directory_roles_and_continuity_are_enforced(self) -> None:
        plan = self.fixture()
        plan["directories"][1]["name"] = "03-正式学习"
        with self.assertRaises(ContractError):
            validate_curriculum(plan)
        plan = self.fixture()
        plan["directories"][-2]["role"] = "formal"
        with self.assertRaises(ContractError):
            validate_curriculum(plan)

    def test_repository_uses_fixed_outer_route_and_identity(self) -> None:
        plan = self.fixture()
        plan["roadmap_kind"] = "repository"
        plan["directories"] = [{"name": name, "role": role} for name, role in REPOSITORY_DIRECTORIES]
        plan["records_directory"] = "10-学习记录"
        plan["units"][0].update({"stage": "01-项目概述", "note_path": "01-项目概述/§02-核心概览.md"})
        plan["repository"] = {
            "provider": "github", "name": "northstar-labs/river-cache", "url": "https://github.com/northstar-labs/river-cache",
            "default_branch": "main", "target_ref": "refs/tags/v1.0.0", "commit": "a" * 40,
            "license_spdx": "MIT", "verified_at": "2026-08-21", "scope": "core request path",
            "core_slice": "request to cache lookup", "upstream_checked_at": "2026-08-21",
            "upstream_status": "unchanged", "graduation_status": "pending-evidence",
        }
        self.assertEqual(validate_curriculum(plan)["repository"]["commit"], "a" * 40)
        for upstream in ("unchanged", "fixed-baseline", "changed", "blocked", "archived"):
            plan["repository"]["upstream_status"] = upstream
            validate_curriculum(plan)
        for graduation in ("pending-evidence", "blocked", "passed"):
            plan["repository"]["graduation_status"] = graduation
            validate_curriculum(plan)
        for license_id in ("3D-Slicer-1.0", "MIT", "NOASSERTION"):
            plan["repository"]["license_spdx"] = license_id
            validate_curriculum(plan)
        plan["repository"]["license_spdx"] = "MIT"
        for field, invalid in (
            ("default_branch", "../bad"), ("target_ref", "refs/heads/../bad"),
            ("license_spdx", "not-a-license"), ("verified_at", "not-a-date"),
            ("graduation_status", "graduated"),
        ):
            candidate = json.loads(json.dumps(plan))
            candidate["repository"][field] = invalid
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_curriculum(candidate)
        plan["repository"].update({"upstream_status": "unchanged", "graduation_status": "pending-evidence"})
        plan["directories"][1]["name"] = "02-随意改名"
        with self.assertRaises(ContractError):
            validate_curriculum(plan)

    def test_nested_directories_must_be_declared_and_continuous(self) -> None:
        plan = self.fixture()
        plan["units"][0].update({
            "stage": "02-正式学习",
            "note_path": "02-正式学习/01-基础/§01-所有权.md",
        })
        with self.assertRaises(ContractError):
            validate_curriculum(plan)
        plan["subdirectories"] = [{"path": "02-正式学习/01-基础", "role": "section"}]
        self.assertEqual(validate_curriculum(plan)["subdirectories"][0]["path"], "02-正式学习/01-基础")
        plan["subdirectories"] = [{"path": "02-正式学习/02-跳号", "role": "section"}]
        with self.assertRaises(ContractError):
            validate_curriculum(plan)

    def test_visible_tables_and_graph_must_project_contract(self) -> None:
        plan = self.fixture()
        contract = json.dumps(plan, ensure_ascii=False)
        note = f'''## 知识依赖图
```mermaid
flowchart LR
  %% unit: OWN-01
```
## 单元目录
| 单元 ID | 阶段与计划文件 | 正文类型 | 单项可验收成果 | 前置单元 | Evidence profile | 验收方式 |
| --- | --- | --- | --- | --- | --- | --- |
| `OWN-01` | `01-Rust所有权概述/§02-所有权心智模型.md` | 原理解释 | Explain why a moved value cannot be reused | 无 | `concept-explanation` | Explain a new move scenario and predict the compiler result |
## 知识点唯一归属
| 知识点 ID | 唯一所属单元 |
| --- | --- |
| `ownership.move` | `OWN-01` |
## 机器可读课程合同
<!-- learn-topic-curriculum:start -->
```json
{contract}
```
<!-- learn-topic-curriculum:end -->
'''
        validate_visible_projection(note, plan)
        with self.assertRaises(ContractError):
            validate_visible_projection(note.replace("ownership.move", "ownership.copy", 1), plan)
        plan = self.fixture()
        duplicate = dict(plan["units"][0])
        duplicate.update({"unit_id": "OWN-02", "note_path": "02-实践/§01-借用.md", "prerequisites": ["OWN-02"]})
        plan["units"].append(duplicate)
        with self.assertRaises(ContractError):
            validate_curriculum(plan)


if __name__ == "__main__":
    unittest.main(verbosity=2)

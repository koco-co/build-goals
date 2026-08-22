from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from learn_topic.curriculum import ContractError  # noqa: E402
from learn_topic.note_contract import (  # noqa: E402
    validate_curriculum_map_properties, validate_learning_record,
    validate_planned_note, validate_repository_visible_projection,
)


class NoteContractTests(unittest.TestCase):
    def unit(self) -> dict:
        return {
            "unit_id": "OWN-01", "title": "移动", "stage": "02-所有权", "note_path": "02-所有权/§01-移动.md",
            "document_type": "原理解释", "learning_outcome": "解释移动",
            "evidence_profile": "concept-explanation", "assessment": "分析新场景",
            "knowledge_ownership": ["OWN-MOVE"], "prerequisites": ["PRE-01"],
        }

    def test_knowledge_note_must_match_all_curriculum_fields(self) -> None:
        properties = {
            "record_type": "knowledge-note", "unit_id": "OWN-01",
            "roadmap_root": "Roadmap", "roadmap_topic": "所有权", "learning_goal": "解释移动",
            "document_type": "原理解释", "learning_outcome": "解释移动",
            "evidence_profile": "concept-explanation", "assessment_method": "分析新场景",
            "knowledge_ownership": ["OWN-MOVE"], "hard_prerequisites": ["PRE-01"],
            "stage_title": "02-所有权", "stage_order": 2, "lesson_order": 1,
            "evidence_note": "[[Roadmap/05-学习记录/§01-移动-学习记录]]",
        }
        properties["title"] = "移动"; properties["version_scope"] = "v1"
        common = {"roadmap_topic": "所有权", "learning_goal": "解释移动", "version_scope": "v1", "paired_evidence_path": "Roadmap/05-学习记录/§01-移动-学习记录.md"}
        validate_planned_note(properties, target_path="Roadmap/02-所有权/§01-移动.md", unit=self.unit(), roadmap_root="Roadmap", records_directory="Roadmap/05-学习记录", **common)
        properties["learning_outcome"] = "另一个成果"
        with self.assertRaises(ContractError):
            validate_planned_note(properties, target_path="Roadmap/02-所有权/§01-移动.md", unit=self.unit(), roadmap_root="Roadmap", records_directory="Roadmap/05-学习记录", **common)
        properties["learning_outcome"] = "解释移动"
        for field, invalid in (
            ("roadmap_root", "Other"),
            ("roadmap_topic", "Other"),
            ("learning_goal", "Other"),
            ("knowledge_ownership", ["OTHER"]),
            ("hard_prerequisites", []),
            ("stage_title", "99-错误"),
            ("stage_order", 999),
            ("lesson_order", 99),
            ("evidence_note", "[[Roadmap/05-学习记录/§99-错误]]"),
        ):
            candidate = {**properties, field: invalid}
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_planned_note(candidate, target_path="Roadmap/02-所有权/§01-移动.md", unit=self.unit(), roadmap_root="Roadmap", records_directory="Roadmap/05-学习记录", **common)

    def test_evidence_must_live_in_records_and_link_planned_content(self) -> None:
        properties = {
            "record_type": "learning-evidence", "unit_id": "OWN-01", "title": "移动学习记录", "version_scope": "v1",
            "roadmap_root": "Roadmap", "roadmap_topic": "所有权", "learning_goal": "解释移动",
            "evidence_profile": "concept-explanation",
            "content_note": "[[Roadmap/02-所有权/§01-移动]]",
            "stage_title": "05-学习记录", "stage_order": 5, "lesson_order": 1,
        }
        common = {"roadmap_topic": "所有权", "learning_goal": "解释移动", "version_scope": "v1", "paired_evidence_path": "Roadmap/05-学习记录/§01-移动-学习记录.md"}
        validate_planned_note(properties, target_path="Roadmap/05-学习记录/§01-移动-学习记录.md", unit=self.unit(), roadmap_root="Roadmap", records_directory="Roadmap/05-学习记录", **common)
        with self.assertRaises(ContractError):
            validate_planned_note(properties, target_path="Roadmap/02-所有权/§02-错误位置.md", unit=self.unit(), roadmap_root="Roadmap", records_directory="Roadmap/05-学习记录", **common)

    def test_learning_record_rejects_unsupported_mastery(self) -> None:
        note = """---
record_type: learning-evidence
progress_status: 已完成
mastery_status: 已迁移
evidence_profile: concept-explanation
mastery_evidence:
  - origin: host-tool
    verified: true
    evidence_profile: concept-explanation
    capability_level: independent
    summary: 只复述原场景
    evidence_id: check-01
    verification_ref: session:123
    observed_at: 2026-08-21T10:00:00+08:00
---
"""
        with self.assertRaises(ContractError):
            validate_learning_record(note)

    def test_repository_frontmatter_and_visible_baseline_match_authority(self) -> None:
        repository = {
            "provider": "github", "name": "northstar-labs/river-cache",
            "url": "https://github.com/northstar-labs/river-cache", "default_branch": "main",
            "target_ref": "refs/tags/v1.0.0", "commit": "a" * 40, "license_spdx": "MIT",
            "verified_at": "2026-08-21", "scope": "core request path", "core_slice": "request to cache lookup",
            "upstream_checked_at": "2026-08-21", "upstream_status": "unchanged",
            "graduation_status": "pending-evidence",
        }
        plan = {
            "roadmap_kind": "repository", "roadmap_root": "Roadmap", "topic": "River Cache",
            "learning_goal": "trace one request", "version_baseline": "a" * 40,
            "source_checked_at": "2026-08-21", "repository": repository,
        }
        properties = {
            "title": "River Cache 学习路线图", "tags": ["学习路线/river-cache"], "date": "2026-08-21",
            "updated": "2026-08-21", "status": "待核验", "category": "技术", "record_type": "curriculum-map",
            "schema_version": 3, "roadmap_topic": "River Cache", "roadmap_kind": "repository",
            "roadmap_root": "Roadmap", "roadmap_status": "进行中", "learning_goal": "trace one request",
            "stage_title": "01-项目概述", "stage_order": 1, "lesson_order": 1,
            "version_baseline": "a" * 40, "version_scope": "fixed commit", "source_checked_at": "2026-08-21",
            "upstream_status": "unchanged", "verified_at": "2026-08-21", "sources": ["https://example.com/docs"],
            "repository_provider": "github", "repository_name": repository["name"], "repository_url": repository["url"],
            "repository_default_branch": "main", "repository_target_ref": "refs/tags/v1.0.0",
            "repository_commit": "a" * 40, "repository_license_spdx": "MIT", "repository_verified_at": "2026-08-21",
            "repository_scope": "core request path", "core_slice": "request to cache lookup",
            "upstream_checked_at": "2026-08-21", "graduation_status": "pending-evidence",
        }
        validate_curriculum_map_properties(properties, plan)
        visible = f"- Provider：`github`\n- 仓库：`{repository['name']}`\n- Canonical URL：`{repository['url']}`\n- 默认分支：`main`\n- 目标 ref：`refs/tags/v1.0.0`\n- Commit：`{'a' * 40}`\n- 许可证：`MIT`\n- 学习范围：core request path\n- 核心切片：request to cache lookup\n- 上游检查：`2026-08-21`\n- 上游状态：`unchanged`\n- 仓库核验：`2026-08-21`\n- 毕业状态：`pending-evidence`\n"
        validate_repository_visible_projection(visible, plan)
        for field, value in (("repository_name", "attacker/other"), ("repository_commit", "b" * 40), ("repository_scope", "other")):
            drifted = {**properties, field: value}
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_curriculum_map_properties(drifted, plan)


if __name__ == "__main__":
    unittest.main(verbosity=2)

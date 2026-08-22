from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from learn_topic.migration import ContractError, build_migration_preview, migrate_record  # noqa: E402


def curriculum() -> dict:
    return {
        "schema_version": 3, "roadmap_kind": "topic", "roadmap_root": "Roadmap",
        "directories": [
            {"name": "01-主题概述", "role": "overview"},
            {"name": "02-核心", "role": "formal"},
            {"name": "03-复习与综合应用", "role": "review"},
            {"name": "04-学习记录", "role": "records"},
            {"name": "99-assets", "role": "assets"},
        ],
        "subdirectories": [],
        "records_directory": "04-学习记录", "topic": "主题", "learning_goal": "独立应用主题",
        "version_baseline": "v1", "source_checked_at": "2026-08-21",
        "units": [{
            "unit_id": "NEW-01", "stage": "02-核心", "note_path": "02-核心/§01-核心.md",
            "title": "核心", "document_type": "原理解释", "learning_outcome": "解释机制",
            "prerequisites": [], "knowledge_ownership": ["POINT-01"],
            "evidence_profile": "concept-explanation", "assessment": "分析新场景",
        }],
    }


class MigrationTests(unittest.TestCase):
    def test_preserves_history_and_infers_conservatively(self) -> None:
        old = {
            "unit_id": "HTTP-01",
            "learning_status": "已掌握",
            "mastery_score": 90,
            "answers": ["original answer"],
            "attempts": [{"id": "attempt-01"}],
            "reviews": [{"date": "2026-08-01"}],
            "unrelated_legacy_field": "do not carry forward",
        }
        migrated = migrate_record(old, evidence_profile="concept-explanation")
        self.assertEqual(migrated["progress_status"], "已完成")
        self.assertEqual(migrated["mastery_status"], "未证明")
        self.assertEqual(migrated["answers"], old["answers"])
        self.assertNotIn("mastery_score", migrated)
        self.assertNotIn("unrelated_legacy_field", migrated)

    def test_ambiguous_profile_stops(self) -> None:
        with self.assertRaises(ContractError):
            migrate_record({"unit_id": "X", "learning_status": "学习中"}, evidence_profile=None)

    def test_content_mapping_must_be_one_to_one_and_match_curriculum(self) -> None:
        records = [{"unit_id": "OLD-01", "learning_status": "学习中", "answers": ["kept"]}]
        mapping = [{
            "legacy_unit_id": "OLD-01", "target_unit_id": "NEW-01",
            "legacy_content": "Old/§01.md", "target_note_path": "02-核心/§01-核心.md",
            "legacy_knowledge_ownership": ["POINT-01"],
        }]
        preview = build_migration_preview(records, target_curriculum=curriculum(), unit_mappings=mapping)
        self.assertEqual(preview["records"][0]["legacy_unit_id"], "OLD-01")
        ambiguous = [*mapping, {**mapping[0], "target_unit_id": "NEW-01"}]
        with self.assertRaises(ContractError):
            build_migration_preview(records, target_curriculum=curriculum(), unit_mappings=ambiguous)
        wrong_path = [{**mapping[0], "target_note_path": "02-核心/§99-错误.md"}]
        with self.assertRaises(ContractError):
            build_migration_preview(records, target_curriculum=curriculum(), unit_mappings=wrong_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)

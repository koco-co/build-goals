from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from learn_topic.learning_state import ContractError, can_graduate, normalize_learning_state  # noqa: E402


class LearningStateTests(unittest.TestCase):
    def test_states_are_independent(self) -> None:
        state = normalize_learning_state({"progress_status": "已完成", "mastery_status": "未证明"})
        self.assertEqual(state["mastery_status"], "未证明")

    def test_unverified_user_supplied_evidence_does_not_graduate(self) -> None:
        record = {
            "progress_status": "已完成",
            "mastery_status": "已独立应用",
            "evidence_profile": "code-practice",
            "mastery_evidence": [{"origin": "user-supplied", "verified": False}],
        }
        self.assertFalse(can_graduate(record))
        record["mastery_evidence"][0] = {
            "origin": "host-tool", "verified": True,
            "evidence_profile": "code-practice", "capability_level": "independent",
            "summary": "public command passed and learner explained the boundary",
            "evidence_id": "attempt-01", "verification_ref": "sha256:abc",
            "observed_at": "2026-08-21T10:00:00+08:00",
        }
        self.assertTrue(can_graduate(record))
        record["mastery_evidence"][0] = {
            "origin": "user-supplied", "verified": True, "verified_by": "host-tool",
            "evidence_profile": "code-practice", "capability_level": "independent",
            "summary": "host independently reproduced the result",
            "evidence_id": "attempt-02", "verification_ref": "host-run:2",
            "observed_at": "2026-08-21T10:05:00+08:00",
        }
        self.assertTrue(can_graduate(record))

    def test_mastery_level_must_match_status(self) -> None:
        record = {
            "progress_status": "已完成", "mastery_status": "已迁移",
            "evidence_profile": "concept-explanation",
            "mastery_evidence": [{
                "origin": "host-tool", "verified": True,
                "evidence_profile": "concept-explanation", "capability_level": "independent",
                "summary": "only repeated the original scenario",
                "evidence_id": "check-01", "verification_ref": "session:123",
                "observed_at": "2026-08-21T10:10:00+08:00",
            }],
        }
        self.assertFalse(can_graduate(record))
        record["mastery_evidence"][0]["capability_level"] = "transfer"
        self.assertTrue(can_graduate(record))

    def test_unknown_status_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            normalize_learning_state({"progress_status": "已掌握", "mastery_status": "未证明"})


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from learn_topic.base_contract import ContractError, detect_capabilities, validate_base_root  # noqa: E402


class BaseContractTests(unittest.TestCase):
    def test_names_and_order_are_not_contract(self) -> None:
        views = [
            {"name": "路线总览", "filters": [], "body": "formula.route_order"},
            {"name": "正在推进", "filters": ['record_type == "learning-evidence"', 'progress_status == "学习中"']},
            {"name": "需要复查", "filters": ['record_type == "learning-evidence"', 'formula.review_due == true']},
            {"name": "卡住了", "filters": ['record_type == "learning-evidence"', 'progress_status == "阻塞"']},
            {"name": "证据账本", "filters": ['record_type == "learning-evidence"', 'mastery_status != ""']},
        ]
        self.assertEqual(detect_capabilities(views), {"route", "current", "review-due", "blocked", "evidence"})

    def test_missing_capability_is_rejected(self) -> None:
        with self.assertRaises(ContractError):
            detect_capabilities([{"name": "route", "filters": []}], require_all=True)

    def test_opposite_semantics_do_not_count(self) -> None:
        views = [
            {"body": "formula.route_order", "filters": ['progress_status != "学习中"']},
            {"filters": ['record_type != "learning-evidence"', 'progress_status == "学习中"']},
            {"filters": ['record_type == "learning-evidence"', 'formula.review_due == false']},
            {"filters": ['record_type == "learning-evidence"', 'progress_status != "阻塞"']},
            {"filters": ['record_type == "learning-evidence"', 'mastery_status == ""']},
        ]
        self.assertEqual(detect_capabilities(views), set())

    def test_extra_constant_filter_invalidates_capability(self) -> None:
        views = [{"filters": ['record_type == "learning-evidence"', 'progress_status == "学习中"', "false"]}]
        self.assertNotIn("current", detect_capabilities(views))

    def test_root_filter_is_exact(self) -> None:
        validate_base_root('filters:\n  - \'file.ext == "md"\'\n  - \'file.inFolder("Roadmap")\'\nviews:\n', "Roadmap")
        with self.assertRaises(ContractError):
            validate_base_root('filters:\n  - file.inFolder("Other")\nviews:\n', "Roadmap")
        with self.assertRaises(ContractError):
            validate_base_root('filters:\n  - \'file.inFolder("Roadmap") || true\'\nviews:\n', "Roadmap")
        with self.assertRaises(ContractError):
            validate_base_root('filters:\n  - \'file.ext == "md"\'\n  - \'file.inFolder("Roadmap")\'\n  - false\nviews:\n', "Roadmap")


if __name__ == "__main__":
    unittest.main(verbosity=2)

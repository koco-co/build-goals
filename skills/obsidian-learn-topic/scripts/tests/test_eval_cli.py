from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "eval_cli.py"
SPEC = importlib.util.spec_from_file_location("eval_cli", SCRIPT)
assert SPEC and SPEC.loader
eval_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eval_cli)


class EvalCliTests(unittest.TestCase):
    def test_distributed_fixtures_have_substantive_contract(self) -> None:
        self.assertEqual(eval_cli.validate_fixtures(), {"routing-cases.json": 4, "content-cases.json": 4})

    def test_fixture_missing_required_behavior_fails(self) -> None:
        malformed = {
            "schema_version": 1,
            "cases": [{"id": f"id-{domain}", "domain": domain, "input": "x", "expected_branch": "start"} for domain in eval_cli.DOMAINS],
        }
        original = eval_cli.load
        with mock.patch.object(eval_cli, "load", side_effect=lambda path: malformed if path.name == "routing-cases.json" else original(path)):
            with self.assertRaises(eval_cli.EvalError):
                eval_cli.validate_fixtures()

    def test_observation_binds_known_case_and_nonempty_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "observation.json"
            value = {"client": "codex", "fresh_session": True, "case_id": "route-language", "result": "passed", "evidence": ["fresh session transcript id 123"]}
            path.write_text(json.dumps(value), encoding="utf-8")
            self.assertEqual(eval_cli.validate_observation(path)["case_id"], "route-language")
            value["case_id"] = "unknown-case"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(eval_cli.EvalError):
                eval_cli.validate_observation(path)
            value["case_id"] = "route-language"; value["evidence"] = []
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(eval_cli.EvalError):
                eval_cli.validate_observation(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)

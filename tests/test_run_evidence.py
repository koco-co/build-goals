from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "skills" / "vibe-coding" / "scripts" / "run_evidence.py"


class RunEvidenceTests(unittest.TestCase):
    def test_records_command_exit_code_and_stream_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "evidence.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--output",
                    str(output),
                    "--summary",
                    "fixture validation",
                    "--",
                    sys.executable,
                    "-c",
                    "import sys; print('ok'); print('warn', file=sys.stderr)",
                ],
                cwd=REPO_ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "1.0")
            self.assertEqual(payload["exit_code"], 0)
            self.assertEqual(payload["summary"], "fixture validation")
            self.assertGreater(payload["stdout"]["bytes"], 0)
            self.assertGreater(payload["stderr"]["bytes"], 0)
            self.assertRegex(payload["stdout"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(payload["stderr"]["sha256"], r"^[0-9a-f]{64}$")
            if sys.platform != "win32":
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_propagates_failure_exit_code_and_still_writes_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "failure.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--output",
                    str(output),
                    "--",
                    sys.executable,
                    "-c",
                    "raise SystemExit(7)",
                ],
                cwd=REPO_ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 7)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["exit_code"], 7)
            self.assertIn("不是不可篡改", payload["note"])


if __name__ == "__main__":
    unittest.main()

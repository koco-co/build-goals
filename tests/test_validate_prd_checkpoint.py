from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = (
    REPO_ROOT / "skills" / "build-prd" / "scripts" / "validate_checkpoint.py"
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_checkpoint(root: Path) -> Path:
    checkpoint = root / ".build-goals" / "build-prd"
    write_json(
        checkpoint / "会话.yaml",
        {
            "schema_version": "1.0",
            "status": "in_progress",
            "source": {"project": str(root), "revision": "fixture"},
            "domain_map_confirmed_at": "2026-08-13T03:00:00+08:00",
            "domains": [
                {
                    "id": "task-management",
                    "name": "任务管理",
                    "dependencies": [],
                    "checkpoint": "功能域/task-management.yaml",
                },
                {
                    "id": "reporting",
                    "name": "报表",
                    "dependencies": ["task-management"],
                    "checkpoint": "功能域/reporting.yaml",
                },
            ],
            "completed_domains": ["task-management"],
            "current_domain": "reporting",
            "pending_domains": ["reporting"],
        },
    )
    write_json(
        checkpoint / "功能域" / "task-management.yaml",
        {
            "schema_version": "1.0",
            "domain_id": "task-management",
            "name": "任务管理",
            "status": "confirmed",
            "confirmed_at": "2026-08-13T03:10:00+08:00",
            "dependencies": [],
            "summary": "用户可以创建并完成任务。",
            "features": [
                {
                    "id": "F-001",
                    "name": "创建任务",
                    "user_inputs": ["创建任务：预约牙医"],
                    "interactions": ["缺少名称时追问任务名称"],
                    "outputs": {
                        "exact": ["状态字段"],
                        "semantic": ["说明创建结果"],
                        "runtime": ["任务 ID 可变化"],
                    },
                    "external_contracts": ["任务名称和状态保持可见"],
                    "forbidden": ["不得静默丢弃输入"],
                    "acceptance": [
                        "Given 用户在任务页，When 创建任务，Then 显示新任务。"
                    ],
                }
            ],
            "evidence": ["用户确认的功能域总结"],
        },
    )
    return checkpoint


class ValidatePrdCheckpointTests(unittest.TestCase):
    def run_validator(self, target: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(target), "--strict"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_valid_confirmed_domain_checkpoint_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkpoint = write_checkpoint(root)
            for target in (root, checkpoint):
                with self.subTest(target=target):
                    result = self.run_validator(target)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_completed_domain_requires_confirmed_complete_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            checkpoint = write_checkpoint(Path(temp))
            path = checkpoint / "功能域" / "task-management.yaml"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["status"] = "draft"
            data["features"][0]["outputs"]["semantic"] = []
            write_json(path, data)

            result = self.run_validator(checkpoint)

            self.assertEqual(result.returncode, 1)
            self.assertIn("DOMAIN_STATUS", result.stdout)
            self.assertIn("OUTPUT_CONTRACT", result.stdout)

    def test_domain_partition_and_current_domain_must_be_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            checkpoint = write_checkpoint(Path(temp))
            path = checkpoint / "会话.yaml"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["completed_domains"] = []
            data["current_domain"] = "unknown"
            write_json(path, data)

            result = self.run_validator(checkpoint)

            self.assertEqual(result.returncode, 1)
            self.assertIn("DOMAIN_PARTITION", result.stdout)
            self.assertIn("CURRENT_DOMAIN", result.stdout)

    def test_domain_partition_rejects_non_string_entries_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            checkpoint = write_checkpoint(Path(temp))
            path = checkpoint / "会话.yaml"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["completed_domains"] = [{"id": "task-management"}]
            write_json(path, data)

            result = self.run_validator(checkpoint)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("DOMAIN_PARTITION", result.stdout)
            self.assertNotIn("Traceback", result.stderr)

    def test_checkpoint_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            checkpoint = write_checkpoint(Path(temp))
            path = checkpoint / "功能域" / "task-management.yaml"
            real = checkpoint / "功能域" / "real.yaml"
            path.rename(real)
            path.symlink_to("real.yaml")

            result = self.run_validator(checkpoint)

            self.assertEqual(result.returncode, 1)
            self.assertIn("NON_REGULAR_FILE", result.stdout)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class ValidatorCoreMirrorTests(unittest.TestCase):
    def test_build_skill_and_build_plugin_validator_cores_are_identical(self) -> None:
        source = REPO_ROOT / "skills" / "build-skill" / "scripts" / "validate_skill_core.py"
        mirror = REPO_ROOT / "skills" / "build-plugin" / "scripts" / "validate_skill_core.py"
        self.assertTrue(source.is_file())
        self.assertTrue(mirror.is_file())
        self.assertFalse(source.is_symlink())
        self.assertFalse(mirror.is_symlink())
        self.assertEqual(source.read_bytes(), mirror.read_bytes())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "skills" / "building-skills" / "scripts" / "validate_skill.py"


VALID_BODY = """
# Outcome

完成目标。

## Routing

- 路由输入。

## Steps

1. 执行并验证。

## Delivery

- 输出结果。

## Guardrails

- 保护用户数据。

## References

- 无附加文件。
"""


class ValidateSkillTests(unittest.TestCase):
    def run_validator(self, skill_dir: Path, profile: str = "portable") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(skill_dir), "--profile", profile],
            check=False,
            text=True,
            capture_output=True,
        )

    def write_skill(self, root: Path, name: str, frontmatter_extra: str = "") -> Path:
        skill_dir = root / name
        skill_dir.mkdir()
        skill_dir.joinpath("SKILL.md").write_text(
            (
                "---\n"
                f"name: {name}\n"
                "description: 用于验证测试夹具，仅在测试中显式调用。\n"
                f"{frontmatter_extra}"
                "---\n\n"
                f"{textwrap.dedent(VALID_BODY).strip()}\n"
            ),
            encoding="utf-8",
        )
        return skill_dir

    def test_valid_portable_skill_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(Path(temp), "valid-skill")
            result = self.run_validator(skill_dir)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS", result.stdout)

    def test_broken_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(Path(temp), "broken-skill")
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(
                skill_md.read_text(encoding="utf-8").replace(
                    "- 无附加文件。",
                    "- 完整读取 `workflows/missing.md`。",
                ),
                encoding="utf-8",
            )
            result = self.run_validator(skill_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("REF_NOT_FOUND", result.stdout)

    def test_claude_extension_is_profile_specific(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(
                Path(temp),
                "manual-skill",
                "disable-model-invocation: true\n",
            )
            portable = self.run_validator(skill_dir, "portable")
            claude = self.run_validator(skill_dir, "claude")
            self.assertEqual(portable.returncode, 1)
            self.assertIn("FRONTMATTER_KEY", portable.stdout)
            self.assertEqual(claude.returncode, 0, claude.stdout + claude.stderr)

    def test_nested_frontmatter_is_tolerated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = self.write_skill(
                Path(temp),
                "nested-skill",
                "hooks:\n  PreToolUse:\n    - matcher: Bash\n      hooks:\n        - type: command\n          command: echo ok\n",
            )
            result = self.run_validator(skill_dir, "claude")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

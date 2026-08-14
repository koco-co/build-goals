from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "skills" / "build-plugin" / "scripts" / "validate_plugin.py"
SYNC_SHARED_FILES = (
    REPO_ROOT / "skills" / "build-plugin" / "scripts" / "sync_shared_files.py"
)

VALID_BODY = """
# Outcome

完成目标。

## Routing

- 显式调用。

## Steps

1. 执行并验证。

## Delivery

- 输出结果。

## Guardrails

- 保护数据。

## References

- 无附加文件。
"""


class ValidatePluginTests(unittest.TestCase):
    def run_validator(
        self,
        plugin_dir: Path,
        platform: str = "dual",
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                str(plugin_dir),
                "--platform",
                platform,
            ],
            check=False,
            text=True,
            capture_output=True,
        )

    def write_fixture(self, root: Path) -> Path:
        plugin = root / "fixture-plugin"
        skill = plugin / "skills" / "fixture-skill"
        skill.mkdir(parents=True)
        skill.joinpath("SKILL.md").write_text(
            (
                "---\n"
                "name: fixture-skill\n"
                "description: 显式调用的测试 Skill。\n"
                "disable-model-invocation: true\n"
                "---\n\n"
                f"{textwrap.dedent(VALID_BODY).strip()}\n"
            ),
            encoding="utf-8",
        )
        adapter = skill / "agents" / "openai.yaml"
        adapter.parent.mkdir()
        adapter.write_text(
            "policy:\n  allow_implicit_invocation: false\n",
            encoding="utf-8",
        )

        common = {
            "name": "fixture-plugin",
            "version": "1.0.0",
            "description": "Fixture plugin",
            "skills": "./skills/",
        }
        for directory in (".codex-plugin", ".claude-plugin"):
            manifest = plugin / directory / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps(common, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return plugin

    def test_repository_plugin_passes(self) -> None:
        result = self.run_validator(REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("skills/build-skill", result.stdout)
        self.assertIn("skills/build-plugin", result.stdout)
        self.assertIn("skills/build-prd", result.stdout)
        self.assertIn("skills/build-readme", result.stdout)
        self.assertIn("skills/build-agents-md", result.stdout)
        self.assertIn("skills/shape-idea", result.stdout)
        self.assertIn("skills/handoff", result.stdout)

    def test_build_plugin_templates_and_rules_are_standalone_safe(self) -> None:
        skill = REPO_ROOT / "skills" / "build-plugin"
        for name in ("claude-plugin.template.json", "codex-plugin.template.json"):
            with self.subTest(template=name):
                manifest = json.loads(
                    (skill / "templates" / name).read_text(encoding="utf-8")
                )
                self.assertNotIn("_comment", manifest)

        claude_manifest = json.loads(
            (skill / "templates" / "claude-plugin.template.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(claude_manifest["author"]["name"], "<author-name>")
        self.assertEqual(claude_manifest["author"]["url"], "<author-url>")

        compatibility = (skill / "rules" / "platform-compatibility.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("skills/build-skill/", compatibility)

        implementation = (skill / "workflows" / "§05-implementation.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("<build-plugin-skill-dir>/scripts/sync_shared_files.py", implementation)
        self.assertIn("--root <plugin-root> --write", implementation)
        self.assertEqual(implementation.count("sync_shared_files.py --root <plugin-root>"), 2)
        self.assertNotIn("python3 skills/build-plugin/", implementation)

        design = (skill / "workflows" / "§03-design.md").read_text(encoding="utf-8")
        self.assertNotIn("examples/dual-platform-plugin.example.md", design)

    def test_repository_shared_runtime_files_are_regular_mirrors(self) -> None:
        contracts = {
            "skills/build-plugin/checklists/skill-content-review.md": "skills/build-skill/checklists/content-review.md",
            "skills/build-plugin/checklists/skill-copy-review.md": "skills/build-skill/checklists/copy-review.md",
            "skills/build-plugin/checklists/skill-design-review.md": "skills/build-skill/checklists/design-review.md",
            "skills/build-plugin/examples/skill-copy-review.example.md": "skills/build-skill/examples/copy-review.example.md",
            "skills/build-plugin/prompts/reviewer.agent.md": "skills/build-skill/prompts/reviewer.agent.md",
            "skills/build-plugin/rules/skill-architecture.md": "skills/build-skill/rules/architecture.md",
            "skills/build-plugin/rules/skill-frontmatter.md": "skills/build-skill/rules/frontmatter.md",
            "skills/build-plugin/rules/skill-quality-standard.md": "skills/build-skill/rules/quality-standard.md",
            "skills/build-plugin/scripts/validate_skill.py": "skills/build-skill/scripts/validate_skill.py",
            "skills/build-plugin/scripts/validate_skill_core.py": "skills/build-skill/scripts/validate_skill_core.py",
            "skills/build-plugin/templates/skill.template.md": "skills/build-skill/templates/skill.template.md",
            "skills/vibe-coding/scripts/validate_agents_md.py": "skills/build-agents-md/scripts/validate_agents_md.py",
            "skills/vibe-coding/scripts/validate_prd.py": "skills/build-prd/scripts/validate_prd.py",
        }
        manifest = json.loads(
            REPO_ROOT.joinpath(".plugin-shared-files.json").read_text(encoding="utf-8")
        )
        declared = {
            target: item["source"]
            for item in manifest["mirrors"]
            for target in item["targets"]
        }
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(declared, contracts)

        for mirror_name, source_name in contracts.items():
            with self.subTest(mirror=mirror_name):
                mirror = REPO_ROOT / mirror_name
                source = REPO_ROOT / source_name
                self.assertTrue(mirror.is_file())
                self.assertFalse(mirror.is_symlink())
                self.assertEqual(mirror.read_bytes(), source.read_bytes())

    def test_shared_runtime_mirror_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = self.write_fixture(Path(temp))
            source = plugin / "shared" / "source.md"
            mirror = plugin / "shared" / "mirror.md"
            source.parent.mkdir()
            source.write_text("canonical\n", encoding="utf-8")
            mirror.write_text("drifted\n", encoding="utf-8")
            plugin.joinpath(".plugin-shared-files.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "mirrors": [
                            {
                                "source": "shared/source.md",
                                "targets": ["shared/mirror.md"],
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_validator(plugin)

            self.assertEqual(result.returncode, 1)
            self.assertIn("SHARED_MIRROR_DRIFT", result.stdout)

    def test_shared_runtime_symlink_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = self.write_fixture(Path(temp))
            source = plugin / "shared" / "source.md"
            mirror = plugin / "shared" / "mirror.md"
            source.parent.mkdir()
            source.write_text("canonical\n", encoding="utf-8")
            mirror.symlink_to("source.md")
            plugin.joinpath(".plugin-shared-files.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "mirrors": [
                            {
                                "source": "shared/source.md",
                                "targets": ["shared/mirror.md"],
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_validator(plugin)

            self.assertEqual(result.returncode, 1)
            self.assertIn("SHARED_MIRROR_SYMLINK", result.stdout)

    def test_shared_runtime_source_target_overlap_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = self.write_fixture(Path(temp))
            first = plugin / "shared" / "first.md"
            second = plugin / "shared" / "second.md"
            first.parent.mkdir()
            first.write_text("first\n", encoding="utf-8")
            second.write_text("second\n", encoding="utf-8")
            plugin.joinpath(".plugin-shared-files.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "mirrors": [
                            {
                                "source": "shared/second.md",
                                "targets": ["shared/first.md"],
                            },
                            {
                                "source": "shared/first.md",
                                "targets": ["shared/second.md"],
                            },
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_validator(plugin)

            self.assertEqual(result.returncode, 1)
            self.assertIn("SHARED_MIRROR_SOURCE_TARGET_OVERLAP", result.stdout)

    def test_shared_runtime_mirrors_can_be_synchronized_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = Path(temp) / "fixture-plugin"
            source = plugin / "shared" / "source.md"
            mirror = plugin / "shared" / "mirror.md"
            source.parent.mkdir(parents=True)
            source.write_text("canonical\n", encoding="utf-8")
            mirror.write_text("drifted\n", encoding="utf-8")
            plugin.joinpath(".plugin-shared-files.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "mirrors": [
                            {
                                "source": "shared/source.md",
                                "targets": ["shared/mirror.md"],
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            check_before = subprocess.run(
                [sys.executable, str(SYNC_SHARED_FILES), "--root", str(plugin)],
                check=False,
                text=True,
                capture_output=True,
            )
            synchronized = subprocess.run(
                [
                    sys.executable,
                    str(SYNC_SHARED_FILES),
                    "--root",
                    str(plugin),
                    "--write",
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            check_after = subprocess.run(
                [sys.executable, str(SYNC_SHARED_FILES), "--root", str(plugin)],
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(check_before.returncode, 1)
            self.assertIn("DRIFT", check_before.stdout)
            self.assertEqual(
                synchronized.returncode,
                0,
                synchronized.stdout + synchronized.stderr,
            )
            self.assertEqual(
                check_after.returncode,
                0,
                check_after.stdout + check_after.stderr,
            )
            self.assertEqual(mirror.read_bytes(), source.read_bytes())

    def test_shared_runtime_sync_rejects_directory_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = Path(temp) / "fixture-plugin"
            source = plugin / "shared" / "source.md"
            mirror = plugin / "shared" / "mirror.md"
            source.parent.mkdir(parents=True)
            source.write_text("canonical\n", encoding="utf-8")
            mirror.mkdir()
            plugin.joinpath(".plugin-shared-files.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "mirrors": [
                            {
                                "source": "shared/source.md",
                                "targets": ["shared/mirror.md"],
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SYNC_SHARED_FILES),
                    "--root",
                    str(plugin),
                    "--write",
                ],
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("TARGET", result.stdout)
            self.assertFalse(mirror.joinpath("source.md").exists())

    def test_shared_runtime_sync_rejects_fifo_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = Path(temp) / "fixture-plugin"
            source = plugin / "shared" / "source.md"
            mirror = plugin / "shared" / "mirror.md"
            source.parent.mkdir(parents=True)
            source.write_text("canonical\n", encoding="utf-8")
            os.mkfifo(mirror)
            plugin.joinpath(".plugin-shared-files.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "mirrors": [
                            {
                                "source": "shared/source.md",
                                "targets": ["shared/mirror.md"],
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SYNC_SHARED_FILES),
                    "--root",
                    str(plugin),
                    "--write",
                ],
                check=False,
                text=True,
                capture_output=True,
                timeout=5,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("TARGET", result.stdout)
            self.assertTrue(mirror.exists())
            self.assertFalse(mirror.is_file())

    def test_shared_runtime_sync_rejects_chains_and_cycles_before_writing(
        self,
    ) -> None:
        variants = {
            "self": [
                {
                    "source": "shared/first.md",
                    "targets": ["shared/first.md"],
                },
            ],
            "cycle": [
                {
                    "source": "shared/second.md",
                    "targets": ["shared/first.md"],
                },
                {
                    "source": "shared/first.md",
                    "targets": ["shared/second.md"],
                },
            ],
            "chain": [
                {
                    "source": "shared/second.md",
                    "targets": ["shared/third.md"],
                },
                {
                    "source": "shared/first.md",
                    "targets": ["shared/second.md"],
                },
            ],
        }

        for name, mirrors in variants.items():
            with self.subTest(variant=name), tempfile.TemporaryDirectory() as temp:
                plugin = Path(temp) / "fixture-plugin"
                shared = plugin / "shared"
                shared.mkdir(parents=True)
                original = {
                    "first.md": b"first\n",
                    "second.md": b"second\n",
                    "third.md": b"third\n",
                }
                for filename, content in original.items():
                    shared.joinpath(filename).write_bytes(content)
                plugin.joinpath(".plugin-shared-files.json").write_text(
                    json.dumps(
                        {"version": 1, "mirrors": mirrors},
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                result = subprocess.run(
                    [
                        sys.executable,
                        str(SYNC_SHARED_FILES),
                        "--root",
                        str(plugin),
                        "--write",
                    ],
                    check=False,
                    text=True,
                    capture_output=True,
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("同时作为规范源和镜像", result.stdout)
                for filename, content in original.items():
                    self.assertEqual(shared.joinpath(filename).read_bytes(), content)

    def test_repository_agent_instructions_are_concise_and_project_specific(
        self,
    ) -> None:
        agents = REPO_ROOT / "AGENTS.md"
        claude = REPO_ROOT / "CLAUDE.md"

        self.assertTrue(agents.is_file())
        self.assertTrue(claude.is_symlink())
        self.assertEqual(os.readlink(claude), "AGENTS.md")

        instructions = agents.read_text(encoding="utf-8")
        for required in (
            "项目概览",
            "仓库结构",
            "常用命令",
            "关键约定",
            "验证流程",
            "提交与发布",
            "skills/",
            "validate_plugin.py",
            "不得自动 commit、push 或更新本地 Plugin",
        ):
            with self.subTest(required=required):
                self.assertIn(required, instructions)
        for excluded in (
            "## 开始修改前",
            "## 完成后的发布确认",
            "claude plugin marketplace update build-goals",
            "codex plugin marketplace upgrade build-goals --json",
            "所有 Skill 仅允许显式调用",
        ):
            with self.subTest(excluded=excluded):
                self.assertNotIn(excluded, instructions)
        self.assertLessEqual(len(instructions.splitlines()), 120)

    def test_build_skills_route_release_actions_by_invocation_mode(self) -> None:
        contracts = {
            "build-skill": (
                REPO_ROOT / "skills" / "build-skill" / "SKILL.md",
                REPO_ROOT / "skills" / "build-skill" / "workflows" / "§06-delivery.md",
                REPO_ROOT
                / "skills"
                / "build-skill"
                / "templates"
                / "delivery-report.template.md",
            ),
            "build-plugin": (
                REPO_ROOT / "skills" / "build-plugin" / "SKILL.md",
                REPO_ROOT / "skills" / "build-plugin" / "workflows" / "§07-delivery.md",
                REPO_ROOT
                / "skills"
                / "build-plugin"
                / "templates"
                / "plugin-delivery-report.template.md",
            ),
        }

        for name, paths in contracts.items():
            with self.subTest(skill=name):
                contract = "\n".join(path.read_text(encoding="utf-8") for path in paths)
                self.assertIn("主动询问", contract)
                self.assertIn("只授权其中部分动作", contract)
                self.assertIn("不得在用户回答前执行", contract)
                self.assertIn("实现和验证已经完成。是否执行以下交付动作？", contract)
                self.assertIn("只列出真实适用的动作", contract)
                self.assertIn("独立调用", contract)
                self.assertIn("受控调用", contract)
                self.assertIn("不重复询问", contract)
                self.assertIn("上层总控", contract)
                self.assertIn("恢复条件", contract)

    def test_repository_release_versions_are_synchronized(self) -> None:
        claude_manifest = json.loads(
            REPO_ROOT.joinpath(".claude-plugin", "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        codex_manifest = json.loads(
            REPO_ROOT.joinpath(".codex-plugin", "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        marketplace = json.loads(
            REPO_ROOT.joinpath(".claude-plugin", "marketplace.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(claude_manifest["version"], codex_manifest["version"])
        self.assertEqual(
            claude_manifest["version"], marketplace["plugins"][0]["version"]
        )
        self.assertEqual(claude_manifest["version"], "2.0.1")

    def test_claude_marketplace_manifest_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = self.write_fixture(Path(temp))
            marketplace = plugin / ".claude-plugin" / "marketplace.json"
            marketplace.write_text(
                json.dumps(
                    {
                        "name": "fixture-marketplace",
                        "owner": {"name": "fixture"},
                        "plugins": [{"name": "fixture-plugin", "source": "./"}],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            result = self.run_validator(plugin)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dual_version_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = self.write_fixture(Path(temp))
            claude = plugin / ".claude-plugin" / "plugin.json"
            data = json.loads(claude.read_text(encoding="utf-8"))
            data["version"] = "2.0.0"
            claude.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            result = self.run_validator(plugin)
            self.assertEqual(result.returncode, 1)
            self.assertIn("DUAL_VERSION_MISMATCH", result.stdout)

    def test_manifest_path_escape_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plugin = self.write_fixture(Path(temp))
            codex = plugin / ".codex-plugin" / "plugin.json"
            data = json.loads(codex.read_text(encoding="utf-8"))
            data["skills"] = "./../skills/"
            codex.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            result = self.run_validator(plugin)
            self.assertEqual(result.returncode, 1)
            self.assertIn("COMPONENT_PATH_TRAVERSAL", result.stdout)

    def test_plugin_symlink_outside_root_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            plugin = self.write_fixture(base)
            outside = base / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            link = plugin / "skills" / "fixture-skill" / "rules" / "outside.md"
            link.parent.mkdir()
            link.symlink_to(os.path.relpath(outside, link.parent))
            result = self.run_validator(plugin)
            self.assertEqual(result.returncode, 1)
            self.assertIn("SYMLINK_OUTSIDE_PLUGIN", result.stdout)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = REPO_ROOT / "packages" / "dsh-build-goals" / "scripts" / "sync_skills.py"
INSTALLER = REPO_ROOT / "scripts" / "install_skill.py"
PACKAGE_DIR = REPO_ROOT / "packages" / "dsh-build-goals"

SKILL_TEMPLATE = """---
name: {name}
description: {description}
{invocation}metadata:
  author: fixture
  version: "1.0.0"
---

# Outcome

{description}
"""


def run_sync(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SYNC_SCRIPT), "--root", str(root), *extra],
        check=False,
        text=True,
        capture_output=True,
    )


def run_installer(
    home: Path,
    platform: str,
    skill: str = "build-skill",
    *extra: str,
    scope: str = "user",
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    child_env = os.environ.copy()
    child_env.pop("DSH_HOME", None)
    child_env["HOME"] = str(home)
    child_env.update(env or {})
    return subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            skill,
            "--platform",
            platform,
            "--scope",
            scope,
            *extra,
        ],
        cwd=REPO_ROOT,
        env=child_env,
        check=False,
        text=True,
        capture_output=True,
    )


def make_fixture_skill(
    root: Path,
    name: str,
    *,
    description: str = "fixture skill",
    invocation: str = "disable-model-invocation: true\n",
    extra_files: dict[str, str] | None = None,
) -> Path:
    skill = root / "skills" / name
    skill.mkdir(parents=True)
    skill.joinpath("SKILL.md").write_text(
        SKILL_TEMPLATE.format(
            name=name, description=description, invocation=invocation
        ),
        encoding="utf-8",
    )
    for relative, content in (extra_files or {}).items():
        target = skill / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return skill


class SyncSkillsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "packages" / "dsh-build-goals").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_sync_mirrors_skills_and_generates_manifest(self) -> None:
        make_fixture_skill(
            self.root,
            "demo-one",
            extra_files={
                "workflows/§01-research.md": "# Research\n",
                "agents/openai.yaml": "name: codex-only\n",
                ".DS_Store": "metadata",
            },
        )
        make_fixture_skill(
            self.root,
            "demo-two",
            description="second fixture",
            invocation="disable-model-invocation: false\nuser-invocable: false\n",
        )

        result = run_sync(self.root, "--write")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        assets = self.root / "packages" / "dsh-build-goals" / "assets" / "skills"
        self.assertEqual(
            sorted(path.name for path in assets.iterdir()),
            ["demo-one", "demo-two"],
        )
        self.assertTrue(
            (assets / "demo-one" / "workflows" / "§01-research.md").is_file()
        )
        self.assertFalse((assets / "demo-one" / "agents").exists())
        self.assertFalse(any(path.name == ".DS_Store" for path in assets.rglob("*")))

        manifest = json.loads(
            self.root.joinpath(
                "packages", "dsh-build-goals", "lib", "skills.generated.js"
            )
            .read_text(encoding="utf-8")
            .split("export const SKILLS = ", 1)[1]
            .rsplit(",", 1)[0]
            + "]"
        )
        by_name = {entry["name"]: entry for entry in manifest}
        self.assertEqual(
            (
                by_name["demo-one"]["modelInvocable"],
                by_name["demo-one"]["userInvocable"],
            ),
            (False, True),
        )
        self.assertEqual(by_name["demo-two"]["modelInvocable"], True)
        self.assertEqual(by_name["demo-two"]["userInvocable"], False)

    def test_sync_check_detects_asset_and_manifest_drift(self) -> None:
        make_fixture_skill(self.root, "demo-one", extra_files={"rules/r.md": "a"})
        self.assertEqual(run_sync(self.root, "--write").returncode, 0)

        mirrored = (
            self.root
            / "packages"
            / "dsh-build-goals"
            / "assets"
            / "skills"
            / "demo-one"
            / "rules"
            / "r.md"
        )
        mirrored.write_text("tampered", encoding="utf-8")
        drift = run_sync(self.root)
        self.assertEqual(drift.returncode, 1)
        self.assertIn("r.md", drift.stderr)

        mirrored.write_text("a", encoding="utf-8")
        manifest_path = (
            self.root / "packages" / "dsh-build-goals" / "lib" / "skills.generated.js"
        )
        manifest_path.write_text("export const SKILLS = [];\n", encoding="utf-8")
        drift = run_sync(self.root)
        self.assertEqual(drift.returncode, 1)
        self.assertIn("清单漂移", drift.stderr)

        self.assertEqual(run_sync(self.root, "--write").returncode, 0)
        self.assertEqual(run_sync(self.root).returncode, 0)

    def test_sync_rejects_invalid_names_and_invocation_values(self) -> None:
        bad_name = make_fixture_skill(self.root, "demoBadName")
        result = run_sync(self.root, "--write")
        self.assertEqual(result.returncode, 1)
        self.assertIn("kebab-case", result.stderr)

        import shutil

        shutil.rmtree(bad_name)
        make_fixture_skill(
            self.root, "demo-one", invocation="disable-model-invocation: maybe\n"
        )
        result = run_sync(self.root, "--write")
        self.assertEqual(result.returncode, 1)
        self.assertIn("disable-model-invocation", result.stderr)


class InstallSkillDshTests(unittest.TestCase):
    def test_dsh_install_keeps_frontmatter_and_drops_agents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            result = run_installer(home, "dsh")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            destination = home / ".dsh" / "skills" / "build-skill"
            skill_md = destination.joinpath("SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("disable-model-invocation:", skill_md)
            self.assertIn("compatibility:", skill_md)
            self.assertFalse(destination.joinpath("agents").exists())

            second = run_installer(home, "dsh")
            self.assertEqual(second.returncode, 1)
            self.assertIn("--force", second.stderr)

    def test_dsh_install_honors_dsh_home_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            dsh_home = home / "custom-dsh"
            result = run_installer(home, "dsh", env={"DSH_HOME": str(dsh_home)})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(
                (dsh_home / "skills" / "build-skill" / "SKILL.md").is_file()
            )
            self.assertFalse((home / ".dsh").exists())

    def test_dsh_project_scope_installs_under_project_dot_dsh(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            project = home / "project"
            project.mkdir()
            result = run_installer(
                home,
                "dsh",
                "build-skill",
                "--project-dir",
                str(project),
                scope="project",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(
                (project / ".dsh" / "skills" / "build-skill" / "SKILL.md").is_file()
            )


class DshPluginPackageTests(unittest.TestCase):
    def test_package_manifest_declares_bundle_patch(self) -> None:
        package = json.loads((PACKAGE_DIR / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["name"], "@koco-co/dsh-build-goals")
        patch = package["dsh"]["bundle"]["patch"]
        self.assertTrue((PACKAGE_DIR / patch).is_file())

    def test_patch_mounts_the_provider_row(self) -> None:
        patch = (PACKAGE_DIR / "cordis.patch.yml").read_text(encoding="utf-8")
        self.assertIn("id: build-goals-skill-provider", patch)
        self.assertIn("name: '@koco-co/dsh-build-goals'", patch)

    def test_js_sources_parse_and_manifest_covers_all_skills(self) -> None:
        for relative in ("lib/index.js", "lib/skills.generated.js"):
            with self.subTest(file=relative):
                checked = subprocess.run(
                    ["node", "--check", str(PACKAGE_DIR / relative)],
                    check=False,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

        shipped = sorted(path.name for path in (REPO_ROOT / "skills").iterdir())
        manifest = (PACKAGE_DIR / "lib" / "skills.generated.js").read_text(
            encoding="utf-8"
        )
        for skill_name in shipped:
            self.assertIn(f'"name": "{skill_name}"', manifest)

        lines = {
            skill_name: next(
                line
                for line in manifest.splitlines()
                if f'"name": "{skill_name}"' in line
            )
            for skill_name in shipped
        }
        for skill_name in (
            "build-agents-md",
            "build-plugin",
            "build-prd",
            "build-readme",
            "build-skill",
            "handoff",
            "health-check",
            "shape-idea",
        ):
            with self.subTest(skill=skill_name):
                self.assertIn('"modelInvocable": true', lines[skill_name])
        self.assertIn('"modelInvocable": false', lines["vibe-coding"])

        readme = (PACKAGE_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("9 个配套 Skill 既可由模型按描述调用", readme)
        self.assertIn("`vibe-coding` 仅通过 `/vibe-coding` 启动", readme)

    def test_committed_assets_match_the_authoritative_source(self) -> None:
        result = run_sync(REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generated_paths_are_marked_in_gitattributes(self) -> None:
        attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        for generated in (
            "packages/dsh-build-goals/assets/**",
            "packages/dsh-build-goals/lib/skills.generated.js",
        ):
            with self.subTest(path=generated):
                self.assertIn(f"{generated} linguist-generated", attributes)


if __name__ == "__main__":
    unittest.main()

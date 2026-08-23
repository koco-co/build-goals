from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class SkillContractTests(unittest.TestCase):
    def test_identity_and_model_invocation(self) -> None:
        skill = read("SKILL.md")
        self.assertRegex(skill, r"(?m)^name: obsidian-learn-topic$")
        self.assertIn('version: "4.0.0"', skill)
        self.assertNotIn("disable-model-invocation", skill)
        self.assertIn("allow_implicit_invocation: true", read("agents/openai.yaml"))

    def test_v3_state_and_evidence_contract(self) -> None:
        record = read("rules/learning-record-contract.md")
        profiles = read("rules/evidence-profiles.md")
        for value in ("未开始", "学习中", "阻塞", "已完成"):
            self.assertIn(value, record)
        for value in ("未证明", "已独立应用", "已迁移", "已保持"):
            self.assertIn(value, record)
        for profile in (
            "concept-explanation", "tutorial-reproduction", "task-operation",
            "reference-application", "code-practice", "repository-reading",
            "repository-patch", "custom",
        ):
            self.assertIn(profile, profiles)

    def test_review_checkpoint_uses_heading_contract(self) -> None:
        contract = read("rules/learning-record-contract.md")
        template = read("templates/learning-record.template.md")
        example = read("examples/recoverable-checkpoint.example.md")

        for heading in ("## 场景", "## 问题", "## 提示"):
            self.assertIn(heading, contract)
        self.assertIn("### 场景", template)
        self.assertIn("### 问题", template)
        self.assertIn("{{OPTIONAL_HINT_SECTION}}", template)
        self.assertNotIn("### 任务", template)
        self.assertNotIn("{{PROGRESSIVE_HINT_OR_NONE}}", template)
        self.assertIn("## 场景", example)
        self.assertIn("## 问题", example)
        self.assertNotIn("## 任务", example)
        self.assertNotRegex(
            "\n".join((contract, template, example)),
            r"(?m)^(?:场景|问题)[：:]",
        )

    def test_deprecated_contracts_are_absent(self) -> None:
        active_paths = [
            ROOT / "SKILL.md",
            ROOT / "templates/learning-record.template.md",
            ROOT / "templates/topic-roadmap.template.base",
            ROOT / "templates/code-exercise-manifest.template.json",
            ROOT / "scripts/exercise_cli.py",
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in active_paths)
        for marker in ("mastery_score", "sandbox-exec", "04-复习与面试"):
            self.assertNotIn(marker, text)
        examples = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "examples").iterdir() if path.is_file())
        for private_example in ("Playwright", "Kata"):
            self.assertNotIn(private_example, examples)

    def test_cross_domain_evals_are_machine_readable(self) -> None:
        routing = json.loads(read("evals/routing-cases.json"))
        content = json.loads(read("evals/content-cases.json"))
        self.assertEqual({case["domain"] for case in routing["cases"]}, {"language", "framework", "concept", "repository"})
        self.assertEqual({case["domain"] for case in content["cases"]}, {"language", "framework", "concept", "repository"})

    def test_resource_references_are_closed(self) -> None:
        pattern = re.compile(r"(?<![A-Za-z0-9_])((?:agents|checklists|evals|examples|rules|scripts|templates|workflows)/[A-Za-z0-9_.\-/§]+)")
        missing = []
        for document in ROOT.rglob("*.md"):
            for relative in set(pattern.findall(document.read_text(encoding="utf-8"))):
                if not (ROOT / relative).exists():
                    missing.append(f"{document.relative_to(ROOT)} -> {relative}")
        self.assertEqual(missing, [])

    def test_repository_prerequisite_uses_explicit_evidence_profile(self) -> None:
        prerequisite = read("templates/repository-prerequisites.template.md")
        self.assertIn("evidence_profile: task-operation", prerequisite)

    def test_attestation_contract_is_routed_and_secret_stays_external(self) -> None:
        workflow = read("workflows/§08-code-exercise.md")
        policy = read("rules/code-exercise-policy.md")
        self.assertIn("templates/code-exercise-attestation.template.json", workflow)
        self.assertIn("--trust-key-file", workflow)
        self.assertIn("练习包之外", policy)


if __name__ == "__main__":
    unittest.main(verbosity=2)

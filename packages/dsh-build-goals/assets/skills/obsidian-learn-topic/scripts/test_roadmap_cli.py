#!/usr/bin/env python3
"""Focused contract tests for roadmap_cli.py.

The suite is intentionally independent of a running Obsidian instance.  Live
Vault acceptance is covered separately; these tests protect the driver's input
normalization and its defensive interpretation of CLI output.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import roadmap_cli


class RoadmapContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.sandbox = Path(self.temporary_directory.name)
        self.vault = self.sandbox / "vault"
        self.inputs = self.sandbox / "inputs"
        self.vault.mkdir()
        self.inputs.mkdir()
        self.root = "📚 Learning & Research/Coding-Roadmap/Python"
        self.learning_goal = "能够用 Python 独立完成小型自动化项目"
        self.version_scope = "Python 3.13"

    def write_text(self, name: str, content: str) -> str:
        path = self.inputs / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    def write_json(self, name: str, value: dict[str, object]) -> str:
        path = self.inputs / name
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(path)

    def base_content(self, root: str | None = None) -> str:
        selected_root = root or self.root
        file_filter = 'file.ext == "md"'
        folder_filter = f"file.inFolder({json.dumps(selected_root, ensure_ascii=False)})"
        return (
            "filters:\n"
            "  and:\n"
            f"    - {json.dumps(file_filter, ensure_ascii=False)}\n"
            f"    - {json.dumps(folder_filter, ensure_ascii=False)}\n"
            "formulas:\n"
            "  route_order: 'if(stage_order && lesson_order, stage_order * 100 + lesson_order, 0)'\n"
            "properties:\n"
            "  note.learning_status:\n"
            "    displayName: 学习状态\n"
            "  note.roadmap_status:\n"
            "    displayName: 路线状态\n"
            "  note.mastery_evidence:\n"
            "    displayName: 掌握证据\n"
            "views:\n"
            "  - type: table\n"
            "    name: 学习路线\n"
            "    sort:\n"
            "      - property: formula.route_order\n"
            "        direction: ASC\n"
            "  - type: table\n"
            "    name: 学习中\n"
            "  - type: table\n"
            "    name: 阻塞\n"
            "  - type: table\n"
            "    name: 待复习\n"
            "  - type: table\n"
            "    name: 已掌握\n"
            "  - type: table\n"
            "    name: 待核验\n"
        )

    def note_content(self, lesson_order: int) -> str:
        learning_status = "学习中" if lesson_order == 1 else "未开始"
        roadmap_status = "roadmap_status: 进行中\n" if lesson_order == 1 else ""
        return (
            "---\n"
            f'title: "Lesson {lesson_order}"\n'
            "aliases: []\n"
            "tags:\n"
            '  - "学习路线/Python"\n'
            "date: 2026-08-08\n"
            "updated: 2026-08-08\n"
            "status: 待核验\n"
            'category: "Learning"\n'
            "note_type: 教程\n"
            "difficulty: 入门\n"
            'roadmap_topic: "Python"\n'
            f"roadmap_root: {json.dumps(self.root, ensure_ascii=False)}\n"
            f"learning_goal: {json.dumps(self.learning_goal, ensure_ascii=False)}\n"
            "knowledge_points_total: 0\n"
            "knowledge_points_covered: 0\n"
            "knowledge_points_pending: 0\n"
            'stage_title: "01-Python概述"\n'
            "stage_order: 1\n"
            f"lesson_order: {lesson_order}\n"
            f"learning_status: {learning_status}\n"
            f"{roadmap_status}"
            "mastery_score: 0\n"
            "hard_prerequisites: []\n"
            "soft_prerequisites: []\n"
            "blocked_by: []\n"
            "mastery_evidence: []\n"
            "assessment_type:\n"
            "assessment_at:\n"
            "last_reviewed:\n"
            "next_review:\n"
            "review_count: 0\n"
            "verified_at: 2026-08-08\n"
            f"version_scope: {json.dumps(self.version_scope, ensure_ascii=False)}\n"
            "sources: []\n"
            "---\n\n"
            f"# Lesson {lesson_order}\n"
        )

    def scaffold_spec(self) -> dict[str, object]:
        base_file = self.write_text("Python-Roadmap.base", self.base_content())
        first_note = self.write_text("§01-前置准备.md", self.note_content(1))
        second_note = self.write_text("§02-Python概述.md", self.note_content(2))
        overview = f"{self.root}/01-Python概述"
        return {
            "vault_name": "Test Vault",
            "vault_path": str(self.vault),
            "topic": {
                "display": "Python",
                "path_segment": "Python",
                "tag": "Python",
            },
            "learning_goal": self.learning_goal,
            "version_scope": self.version_scope,
            "root": self.root,
            "base": {
                "path": f"{self.root}/Python-Roadmap.base",
                "content_file": base_file,
            },
            "directories": [
                {"path": overview, "role": "overview", "keep": False},
                {"path": f"{self.root}/02-语法基础", "role": "formal", "keep": True},
                {"path": f"{self.root}/03-深入与拓展", "role": "extension", "keep": True},
                {"path": f"{self.root}/04-复习与面试", "role": "review", "keep": True},
                {"path": f"{self.root}/99-assets", "role": "assets", "keep": True},
            ],
            "notes": [
                {
                    "path": f"{overview}/§01-前置准备.md",
                    "content_file": first_note,
                },
                {
                    "path": f"{overview}/§02-Python概述.md",
                    "content_file": second_note,
                },
            ],
        }

    def repository_scaffold_spec(self) -> dict[str, object]:
        spec = self.scaffold_spec()
        commit = "a" * 40
        spec["roadmap_kind"] = "repository"
        spec["repository"] = {
            "provider": "github",
            "name": "python/cpython",
            "url": "https://github.com/python/cpython",
            "default_branch": "main",
            "target_ref": "refs/tags/v3.13.7",
            "commit": commit,
            "license_spdx": "PSF-2.0",
            "verified_at": "2026-08-18",
            "scope": "CPython 解释器主流程",
            "core_slice": "源文件到字节码执行",
            "upstream_checked_at": "2026-08-18",
            "upstream_status": "unchanged",
        }
        overview = f"{self.root}/01-项目概述"
        spec["directories"] = [
            {"path": overview, "role": "overview", "keep": False},
            {"path": f"{self.root}/02-运行与测试基线", "role": "formal", "keep": True},
            {"path": f"{self.root}/03-架构与模块地图", "role": "formal", "keep": True},
            {"path": f"{self.root}/04-核心调用链", "role": "formal", "keep": True},
            {"path": f"{self.root}/05-测试与质量体系", "role": "formal", "keep": True},
            {"path": f"{self.root}/06-Issue与PR考古", "role": "formal", "keep": True},
            {"path": f"{self.root}/07-最小修复实践", "role": "formal", "keep": True},
            {"path": f"{self.root}/08-深入与拓展", "role": "extension", "keep": True},
            {"path": f"{self.root}/09-复习与贡献准备", "role": "review", "keep": True},
            {"path": f"{self.root}/99-assets", "role": "assets", "keep": True},
        ]
        for note in spec["notes"]:
            filename = PurePosixPath(note["path"]).name
            note["path"] = f"{overview}/{filename}"
            content_path = Path(note["content_file"])
            content = content_path.read_text(encoding="utf-8").replace(
                'stage_title: "01-Python概述"', 'stage_title: "01-项目概述"'
            )
            content = content.replace(
                'roadmap_topic: "Python"\n',
                'roadmap_topic: "Python"\nroadmap_kind: repository\n',
            )
            if filename == "§01-前置准备.md":
                content = content.replace(
                    "roadmap_status: 进行中\n",
                    "roadmap_status: 进行中\n"
                    "repository_provider: github\n"
                    'repository_name: "python/cpython"\n'
                    'repository_url: "https://github.com/python/cpython"\n'
                    'repository_default_branch: "main"\n'
                    'repository_target_ref: "refs/tags/v3.13.7"\n'
                    f'repository_commit: "{commit}"\n'
                    'repository_license_spdx: "PSF-2.0"\n'
                    "repository_verified_at: 2026-08-18\n"
                    'repository_scope: "CPython 解释器主流程"\n'
                    'core_slice: "源文件到字节码执行"\n'
                    "upstream_checked_at: 2026-08-18\n"
                    "upstream_status: unchanged\n"
                    "graduation_status: pending\n",
                )
            content_path.write_text(content, encoding="utf-8")
        return spec

    def load_scaffold(self, spec: dict[str, object]) -> dict[str, object]:
        return roadmap_cli.load_scaffold_spec(self.write_json("scaffold.json", spec))

    def renumber_plan(self) -> dict[str, object]:
        return {
            "vault_name": "Test Vault",
            "vault_path": str(self.vault),
            "root": self.root,
            "moves": [
                {
                    "from": f"{self.root}/02-语法基础",
                    "to": f"{self.root}/03-语法基础",
                },
                {
                    "from": f"{self.root}/03-深入与拓展",
                    "to": f"{self.root}/02-深入与拓展",
                },
            ],
            "expected_links": [
                {
                    "source": f"{self.root}/01-Python概述/§02-Python概述.md",
                    "target": f"{self.root}/03-语法基础/§01-基础.md",
                    "minimum_count": 1,
                    "require_no_unresolved": True,
                    "old_targets": [f"{self.root}/02-语法基础/§01-基础.md"],
                }
            ],
            "base": {
                "path": f"{self.root}/Python-Roadmap.base",
                "view": "学习路线",
                "expected_paths": [f"{self.root}/01-Python概述/§02-Python概述.md"],
            },
        }

    def load_renumber(self, plan: dict[str, object]) -> dict[str, object]:
        return roadmap_cli.load_renumber_plan(self.write_json("renumber.json", plan))

    def write_note_content(
        self,
        *,
        stage_title: str = "02-语法基础",
        stage_order: int = 2,
        lesson_order: int = 1,
        status: str = "待核验",
        learning_status: str = "学习中",
        mastery_score: object = 0,
        mastery_evidence: tuple[str, ...] = (),
        assessment_type: str | None = None,
        assessment_at: str | None = None,
        last_reviewed: str | None = None,
        next_review: str | None = None,
        review_count: object = 0,
        verified_at: str | None = "2026-08-08",
        sources: tuple[str, ...] = (),
        roadmap_status: str | None = None,
        body: str = "# 变量与基本类型\n\n`$value` 与 \"quoted text\" 必须原样保留。\n",
    ) -> str:
        def list_property(key: str, values: tuple[str, ...]) -> str:
            if not values:
                return f"{key}: []\n"
            items = "".join(
                f"  - {json.dumps(value, ensure_ascii=False)}\n" for value in values
            )
            return f"{key}:\n{items}"

        def nullable_property(key: str, value: str | None) -> str:
            return f"{key}:\n" if value is None else f"{key}: {value}\n"

        return "".join(
            [
                "---\n",
                'title: "变量与基本类型"\n',
                "aliases: []\n",
                "tags:\n",
                '  - "学习路线/Python"\n',
                "date: 2026-08-08\n",
                "updated: 2026-08-08\n",
                f"status: {status}\n",
                'category: "Learning"\n',
                "note_type: 教程\n",
                "difficulty: 入门\n",
                'roadmap_topic: "Python"\n',
                f"roadmap_root: {json.dumps(self.root, ensure_ascii=False)}\n",
                f"learning_goal: {json.dumps(self.learning_goal, ensure_ascii=False)}\n",
                "knowledge_points_total: 0\n",
                "knowledge_points_covered: 0\n",
                "knowledge_points_pending: 0\n",
                f"stage_title: {json.dumps(stage_title, ensure_ascii=False)}\n",
                f"stage_order: {stage_order}\n",
                f"lesson_order: {lesson_order}\n",
                f"learning_status: {learning_status}\n",
                f"roadmap_status: {roadmap_status}\n" if roadmap_status is not None else "",
                f"mastery_score: {mastery_score}\n",
                "hard_prerequisites: []\n",
                "soft_prerequisites: []\n",
                "blocked_by: []\n",
                list_property("mastery_evidence", mastery_evidence),
                nullable_property("assessment_type", assessment_type),
                nullable_property("assessment_at", assessment_at),
                nullable_property("last_reviewed", last_reviewed),
                nullable_property("next_review", next_review),
                f"review_count: {review_count}\n",
                nullable_property("verified_at", verified_at),
                f"version_scope: {json.dumps(self.version_scope, ensure_ascii=False)}\n",
                list_property("sources", sources),
                "---\n\n",
                body,
            ]
        )

    def write_note_plan(self, *, mode: str = "create") -> dict[str, object]:
        content_file = self.write_text("planned-note.md", self.write_note_content())
        plan: dict[str, object] = {
            "vault_name": "Test Vault",
            "vault_path": str(self.vault),
            "root": self.root,
            "topic": {
                "display": "Python",
                "path_segment": "Python",
                "tag": "Python",
            },
            "learning_goal": self.learning_goal,
            "version_scope": self.version_scope,
            "path": f"{self.root}/02-语法基础/§01-变量与基本类型.md",
            "content_file": content_file,
            "mode": mode,
            "remove_gitkeep": mode == "create",
        }
        if mode == "replace":
            plan["expected_current_file"] = self.write_text(
                "expected-current.md",
                self.write_note_content(body="# 原有内容\n"),
            )
        return plan

    def load_write_note(self, plan: dict[str, object]) -> dict[str, object]:
        return roadmap_cli.load_write_note_plan(self.write_json("note.json", plan))


class VaultPathTests(RoadmapContractTestCase):
    def test_safe_vault_paths_are_preserved(self) -> None:
        safe_paths = (
            "Learning/Python-Roadmap",
            "📚 Learning & Research/Python-Roadmap/01-Python概述",
            "Inbox/§01-前置准备.md",
        )
        for value in safe_paths:
            with self.subTest(value=value):
                self.assertEqual(roadmap_cli.validate_vault_path(value), value)

    def test_unsafe_vault_paths_are_rejected(self) -> None:
        unsafe_paths = (
            "",
            " Learning/Python",
            "Learning/Python ",
            "/Learning/Python",
            "Learning\\Python",
            "Learning/../Python",
            "Learning//Python",
            "Learning/Python/",
            ".agents/skills",
            ".CLAUDE/settings.json",
            "Clippings/page.md",
            "Learning/Attachments/image.png",
            "Learning/\x00Python",
        )
        for value in unsafe_paths:
            with self.subTest(value=value):
                with self.assertRaises(roadmap_cli.ContractError):
                    roadmap_cli.validate_vault_path(value)

    def test_dot_segments_are_rejected_instead_of_silently_normalized(self) -> None:
        for value in ("./Learning/Python", "Learning/./Python", "Learning/Python/."):
            with self.subTest(value=value):
                with self.assertRaises(roadmap_cli.ContractError):
                    roadmap_cli.validate_vault_path(value)

    def test_shell_safe_apostrophe_path_is_allowed_but_expansion_characters_are_rejected(self) -> None:
        safe = "Learning/Python's-Roadmap"
        self.assertEqual(roadmap_cli.validate_vault_path(safe), safe)

        for value in (
            'Learning/Py"thon-Roadmap',
            "Learning/Py`thon-Roadmap",
            "Learning/Py$(whoami)-Roadmap",
            "Learning/$TOPIC-Roadmap",
        ):
            with self.subTest(value=value):
                with self.assertRaises(roadmap_cli.ContractError):
                    roadmap_cli.validate_vault_path(value)


class ScaffoldSpecTests(RoadmapContractTestCase):
    def test_valid_scaffold_spec_is_normalized_and_loads_external_content(self) -> None:
        normalized = self.load_scaffold(self.scaffold_spec())

        self.assertEqual(normalized["vault_name"], "Test Vault")
        self.assertEqual(normalized["vault_path"], str(self.vault.resolve()))
        self.assertEqual(normalized["root"], self.root)
        self.assertEqual(normalized["base"]["path"], f"{self.root}/Python-Roadmap.base")
        self.assertEqual(normalized["base"]["content"], self.base_content())
        self.assertEqual(
            normalized["gitkeeps"],
            [
                f"{self.root}/02-语法基础/.gitkeep",
                f"{self.root}/03-深入与拓展/.gitkeep",
                f"{self.root}/04-复习与面试/.gitkeep",
                f"{self.root}/99-assets/.gitkeep",
            ],
        )
        self.assertEqual(len(normalized["notes"]), 2)
        self.assertIn("learning_status: 学习中", normalized["notes"][0]["content"])

    def test_repository_scaffold_uses_the_fixed_outer_route_and_persists_commit_baseline(self) -> None:
        normalized = self.load_scaffold(self.repository_scaffold_spec())

        self.assertEqual(normalized["roadmap_kind"], "repository")
        self.assertEqual(normalized["repository"]["name"], "python/cpython")
        self.assertEqual(normalized["repository"]["commit"], "a" * 40)
        self.assertEqual(
            [PurePosixPath(item["path"]).name for item in normalized["directories"]],
            [
                "01-项目概述",
                "02-运行与测试基线",
                "03-架构与模块地图",
                "04-核心调用链",
                "05-测试与质量体系",
                "06-Issue与PR考古",
                "07-最小修复实践",
                "08-深入与拓展",
                "09-复习与贡献准备",
                "99-assets",
            ],
        )

    def test_repository_scaffold_rejects_missing_renamed_or_reordered_outer_stages(self) -> None:
        mutations = (
            lambda directories: directories.pop(4),
            lambda directories: directories[3].update(
                {"path": f"{self.root}/04-源码阅读"}
            ),
            lambda directories: (
                directories[2].update({"path": f"{self.root}/04-架构与模块地图"}),
                directories[3].update({"path": f"{self.root}/03-核心调用链"}),
            ),
        )
        for mutate in mutations:
            spec = self.repository_scaffold_spec()
            mutate(spec["directories"])
            with self.subTest(paths=[item["path"] for item in spec["directories"]]):
                with self.assertRaisesRegex(roadmap_cli.ContractError, "repository outer route"):
                    self.load_scaffold(spec)

    def test_repository_scaffold_requires_canonical_anchor_metadata(self) -> None:
        spec = self.repository_scaffold_spec()
        first_note = Path(spec["notes"][0]["content_file"])
        first_note.write_text(
            first_note.read_text(encoding="utf-8").replace(
                f'repository_commit: "{"a" * 40}"\n', ""
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "repository_commit"):
            self.load_scaffold(spec)

    def test_generic_scaffold_defaults_to_topic_kind(self) -> None:
        normalized = self.load_scaffold(self.scaffold_spec())
        self.assertEqual(normalized["roadmap_kind"], "topic")

    def test_shipped_base_template_meets_the_driver_contract(self) -> None:
        template = Path(__file__).resolve().parents[1] / "templates" / "topic-roadmap.template.base"
        folder_filter = f"file.inFolder({json.dumps(self.root, ensure_ascii=False)})"
        rendered = template.read_text(encoding="utf-8").replace(
            "{{ROADMAP_FILTER_JSON}}",
            json.dumps(folder_filter, ensure_ascii=False),
        )
        spec = self.scaffold_spec()
        spec["base"]["content_file"] = self.write_text("rendered.base", rendered)
        normalized = self.load_scaffold(spec)
        self.assertIn("property: formula.route_order", normalized["base"]["content"])
        self.assertIn("note.learning_status:", normalized["base"]["content"])

    def test_shipped_base_filter_safely_serializes_apostrophe_root_as_exact_expression(self) -> None:
        template = Path(__file__).resolve().parents[1] / "templates" / "topic-roadmap.template.base"
        root = "Learning/O'Reilly-Roadmap"
        expected_filter = f"file.inFolder({json.dumps(root, ensure_ascii=False)})"
        rendered = template.read_text(encoding="utf-8").replace(
            "{{ROADMAP_FILTER_JSON}}",
            json.dumps(expected_filter, ensure_ascii=False),
        )
        filter_lines = [
            line.strip()[2:]
            for line in rendered.splitlines()
            if line.strip().startswith("- ") and "file.inFolder" in line
        ]

        self.assertEqual(len(filter_lines), 1)
        self.assertEqual(json.loads(filter_lines[0]), expected_filter)

    def test_placeholder_is_rejected(self) -> None:
        spec = self.scaffold_spec()
        spec["root"] = "Learning/{{TOPIC}}-Roadmap"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "unfilled placeholder"):
            self.load_scaffold(spec)

        spec = self.scaffold_spec()
        spec["topic"]["display"] = "{{TOPIC_DISPLAY}}"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "unfilled placeholder"):
            self.load_scaffold(spec)

    def test_unfilled_placeholder_in_external_content_is_rejected(self) -> None:
        spec = self.scaffold_spec()
        Path(spec["notes"][0]["content_file"]).write_text(
            self.note_content(1) + "\n{{TODO}}\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "unfilled placeholder"):
            self.load_scaffold(spec)

        spec = self.scaffold_spec()
        Path(spec["notes"][0]["content_file"]).write_text(
            self.note_content(1) + "\n{{一句话定义主题及其价值。}}\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "unfilled placeholder"):
            self.load_scaffold(spec)

    def test_course_body_may_contain_legitimate_template_expression(self) -> None:
        spec = self.scaffold_spec()
        note_file = Path(spec["notes"][0]["content_file"])
        note_file.write_text(
            self.note_content(1)
            + "\n```vue\n<template><p>{{ message }}</p></template>\n```\n",
            encoding="utf-8",
        )

        normalized = self.load_scaffold(spec)

        self.assertIn("{{ message }}", normalized["notes"][0]["content"])

    def test_content_files_must_stay_under_the_scaffold_spec_temp_directory(self) -> None:
        outside = self.sandbox / "other-host-files"
        outside.mkdir()

        spec = self.scaffold_spec()
        outside_base = outside / "Python-Roadmap.base"
        outside_base.write_text(self.base_content(), encoding="utf-8")
        spec["base"]["content_file"] = str(outside_base)
        with self.assertRaises(roadmap_cli.ContractError):
            self.load_scaffold(spec)

        spec = self.scaffold_spec()
        outside_note = outside / "§01-前置准备.md"
        outside_note.write_text(self.note_content(1), encoding="utf-8")
        spec["notes"][0]["content_file"] = str(outside_note)
        with self.assertRaises(roadmap_cli.ContractError):
            self.load_scaffold(spec)

    def test_content_files_may_live_in_a_child_of_the_spec_temp_directory(self) -> None:
        spec = self.scaffold_spec()
        nested = self.inputs / "rendered" / "notes"
        nested.mkdir(parents=True)
        nested_note = nested / "§01-前置准备.md"
        nested_note.write_text(self.note_content(1), encoding="utf-8")
        spec["notes"][0]["content_file"] = str(nested_note)

        normalized = self.load_scaffold(spec)

        self.assertIn("roadmap_status: 进行中", normalized["notes"][0]["content"])

    def test_base_must_use_topic_roadmap_suffix_inside_roadmap_root(self) -> None:
        spec = self.scaffold_spec()
        spec["base"]["path"] = f"{self.root}/Roadmap.base"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "base.path must be"):
            self.load_scaffold(spec)

    def test_base_content_must_scope_the_roadmap_and_expose_learning_view(self) -> None:
        spec = self.scaffold_spec()
        Path(spec["base"]["content_file"]).write_text(
            'filters:\n  - file.ext == "md"\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "base content missing"):
            self.load_scaffold(spec)

    def test_overview_directory_name_must_end_with_topic_overview(self) -> None:
        spec = self.scaffold_spec()
        old_overview = spec["directories"][0]["path"]
        new_overview = f"{self.root}/01-前置与扫盲"
        spec["directories"][0]["path"] = new_overview
        for note in spec["notes"]:
            note["path"] = note["path"].replace(old_overview, new_overview)
        with self.assertRaisesRegex(roadmap_cli.ContractError, "01 directory must be named"):
            self.load_scaffold(spec)

    def test_directory_segments_must_be_numbered(self) -> None:
        spec = self.scaffold_spec()
        spec["directories"][1]["path"] = f"{self.root}/语法基础"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "01-99 prefix"):
            self.load_scaffold(spec)

    def test_directory_must_be_below_roadmap_root(self) -> None:
        spec = self.scaffold_spec()
        spec["directories"][1]["path"] = "Other-Roadmap/02-语法基础"
        with self.assertRaises(roadmap_cli.ContractError):
            self.load_scaffold(spec)

    def test_top_level_directory_numbers_must_be_unique(self) -> None:
        spec = self.scaffold_spec()
        spec["directories"][1]["path"] = f"{self.root}/01-第二概述"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "duplicate top-level"):
            self.load_scaffold(spec)

    def test_directory_numbers_are_contiguous_and_99_is_reserved_for_assets(self) -> None:
        spec = self.scaffold_spec()
        spec["directories"][2]["path"] = f"{self.root}/04-深入与拓展"
        spec["directories"][3]["path"] = f"{self.root}/05-复习与面试"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "contiguous from 01"):
            self.load_scaffold(spec)

        spec = self.scaffold_spec()
        spec["directories"][-1]["path"] = f"{self.root}/99-附件"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "99-assets"):
            self.load_scaffold(spec)

    def test_scaffold_requires_all_stage_roles_in_order_and_assets(self) -> None:
        spec = self.scaffold_spec()
        spec["directories"][1]["role"] = "extension"
        with self.assertRaises(roadmap_cli.ContractError):
            self.load_scaffold(spec)

        spec = self.scaffold_spec()
        spec["directories"][2]["role"] = "formal"
        with self.assertRaises(roadmap_cli.ContractError):
            self.load_scaffold(spec)

        spec = self.scaffold_spec()
        spec["directories"][3]["role"] = "formal"
        with self.assertRaises(roadmap_cli.ContractError):
            self.load_scaffold(spec)

        spec = self.scaffold_spec()
        spec["directories"] = spec["directories"][:-1]
        with self.assertRaises(roadmap_cli.ContractError):
            self.load_scaffold(spec)

    def test_every_initially_empty_directory_requires_gitkeep(self) -> None:
        for index in (1, 2, 3, 4):
            spec = self.scaffold_spec()
            spec["directories"][index]["keep"] = False
            with self.subTest(path=spec["directories"][index]["path"]):
                with self.assertRaisesRegex(roadmap_cli.ContractError, "keep|gitkeep"):
                    self.load_scaffold(spec)

    def test_shipped_scaffold_template_declares_stage_roles(self) -> None:
        template_path = Path(__file__).resolve().parents[1] / "templates" / "scaffold-spec.template.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        roles = [directory.get("role") for directory in template["directories"]]
        self.assertEqual(roles[0], "overview")
        self.assertGreaterEqual(roles.count("formal"), 1)
        self.assertEqual(roles[-3:], ["extension", "review", "assets"])
        self.assertEqual(template["directories"][-1]["path"], "{{ROADMAP_ROOT}}/99-assets")

    def test_note_must_use_section_number_prefix(self) -> None:
        spec = self.scaffold_spec()
        spec["notes"][0]["path"] = f"{self.root}/01-Python概述/前置准备.md"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "Markdown note must use"):
            self.load_scaffold(spec)

    def test_note_must_stay_inside_overview_directory(self) -> None:
        spec = self.scaffold_spec()
        spec["notes"][0]["path"] = f"{self.root}/02-语法基础/§01-前置准备.md"
        with self.assertRaises(roadmap_cli.ContractError):
            self.load_scaffold(spec)

    def test_overview_note_numbers_must_start_at_one(self) -> None:
        spec = self.scaffold_spec()
        spec["notes"] = [spec["notes"][1]]
        with self.assertRaisesRegex(roadmap_cli.ContractError, "must start at §01"):
            self.load_scaffold(spec)

    def test_overview_note_numbers_must_reject_a_section_one_to_three_gap(self) -> None:
        spec = self.scaffold_spec()
        spec["notes"][1]["path"] = f"{self.root}/01-Python概述/§03-Python概述.md"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "contiguous from §01"):
            self.load_scaffold(spec)

    def test_overview_note_numbers_must_remain_contiguous_after_required_notes(self) -> None:
        spec = self.scaffold_spec()
        fourth_note = self.write_text("§04-扩展阅读.md", self.note_content(4))
        spec["notes"].append(
            {
                "path": f"{self.root}/01-Python概述/§04-扩展阅读.md",
                "content_file": fourth_note,
            }
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "contiguous from §01"):
            self.load_scaffold(spec)

    def test_note_content_requires_learning_properties(self) -> None:
        spec = self.scaffold_spec()
        Path(spec["notes"][0]["content_file"]).write_text(
            self.note_content(1).replace("learning_status: 学习中\n", ""),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "missing property learning_status"):
            self.load_scaffold(spec)

    def test_every_scaffold_note_requires_clean_initial_mastery_and_review_state(self) -> None:
        mutations = (
            ("published", "status: 待核验", "status: 已发布"),
            ("nonzero score", "mastery_score: 0", "mastery_score: 1"),
            (
                "premature evidence",
                "mastery_evidence: []",
                'mastery_evidence:\n  - "未经验收"',
            ),
            ("assessment type", "assessment_type:\n", "assessment_type: quiz\n"),
            ("assessment date", "assessment_at:\n", "assessment_at: 2026-08-08\n"),
            ("last reviewed", "last_reviewed:\n", "last_reviewed: 2026-08-08\n"),
            ("next review", "next_review:\n", "next_review: 2026-08-09\n"),
            ("review count", "review_count: 0", "review_count: 1"),
        )
        for note_index in (0, 1):
            for label, old, new in mutations:
                spec = self.scaffold_spec()
                note_file = Path(spec["notes"][note_index]["content_file"])
                content = note_file.read_text(encoding="utf-8")
                self.assertIn(old, content)
                note_file.write_text(content.replace(old, new), encoding="utf-8")
                with self.subTest(note_index=note_index, field=label):
                    with self.assertRaisesRegex(
                        roadmap_cli.ContractError,
                        "initial scaffold|unmastered|publication state",
                    ):
                        self.load_scaffold(spec)

    def test_topic_path_segment_and_tag_are_distinct_safe_values(self) -> None:
        spec = self.scaffold_spec()
        spec["topic"]["path_segment"] = "owner/repo"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "safe directory segment"):
            self.load_scaffold(spec)

        spec = self.scaffold_spec()
        spec["topic"]["tag"] = "C++"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "Obsidian-safe"):
            self.load_scaffold(spec)

    def test_topic_tag_cannot_start_with_a_number(self) -> None:
        for tag in ("1python", "-python"):
            raw = {
                "topic": {
                    "display": "Python",
                    "path_segment": "Python",
                    "tag": tag,
                }
            }
            with self.subTest(tag=tag):
                with self.assertRaisesRegex(roadmap_cli.ContractError, "tag|number|digit|start"):
                    roadmap_cli.normalize_topic_metadata(raw)

        for tag in ("Python", "中文", "_python"):
            raw = {
                "topic": {
                    "display": "Python",
                    "path_segment": "Python",
                    "tag": tag,
                }
            }
            with self.subTest(valid_tag=tag):
                self.assertEqual(roadmap_cli.normalize_topic_metadata(raw)["tag"], tag)

    def test_topic_path_segment_rejects_shell_expansion_characters(self) -> None:
        for path_segment in ('Py"thon', "Py`thon", "Py$(whoami)", "$PYTHON"):
            raw = {
                "topic": {
                    "display": "Python",
                    "path_segment": path_segment,
                    "tag": "Python",
                }
            }
            with self.subTest(path_segment=path_segment):
                with self.assertRaisesRegex(roadmap_cli.ContractError, "path_segment|safe|shell"):
                    roadmap_cli.normalize_topic_metadata(raw)

    def test_stage_title_uses_the_actual_path_segment_when_display_name_differs(self) -> None:
        spec = self.scaffold_spec()
        spec["topic"] = {
            "display": "owner/repo",
            "path_segment": "owner-repo",
            "tag": "owner-repo",
        }
        old_overview = f"{self.root}/01-Python概述"
        new_overview = f"{self.root}/01-owner-repo概述"
        spec["directories"][0]["path"] = new_overview
        for index, note in enumerate(spec["notes"], start=1):
            note["path"] = note["path"].replace(old_overview, new_overview)
            if index == 2:
                note["path"] = note["path"].replace("§02-Python概述.md", "§02-owner-repo概述.md")
            note_file = Path(note["content_file"])
            note_file.write_text(
                note_file.read_text(encoding="utf-8")
                .replace('roadmap_topic: "Python"', 'roadmap_topic: "owner/repo"')
                .replace('stage_title: "01-Python概述"', 'stage_title: "01-owner-repo概述"')
                .replace('  - "学习路线/Python"', '  - "学习路线/owner-repo"'),
                encoding="utf-8",
            )

        normalized = self.load_scaffold(spec)

        self.assertIn(
            'stage_title: "01-owner-repo概述"',
            normalized["notes"][0]["content"].splitlines(),
        )

    def test_note_canonical_metadata_must_match_the_spec(self) -> None:
        spec = self.scaffold_spec()
        note_path = Path(spec["notes"][0]["content_file"])
        note_path.write_text(
            self.note_content(1).replace(
                f"learning_goal: {json.dumps(self.learning_goal, ensure_ascii=False)}",
                'learning_goal: "different goal"',
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "canonical metadata"):
            self.load_scaffold(spec)

    def test_first_overview_unit_is_active_and_second_is_not_started(self) -> None:
        spec = self.scaffold_spec()
        first = Path(spec["notes"][0]["content_file"])
        first.write_text(
            self.note_content(1).replace("learning_status: 学习中", "learning_status: 未开始"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "must start with learning_status"):
            self.load_scaffold(spec)

    def test_prerequisite_anchor_requires_active_roadmap_status(self) -> None:
        spec = self.scaffold_spec()
        first = Path(spec["notes"][0]["content_file"])
        first.write_text(
            self.note_content(1).replace("roadmap_status: 进行中\n", ""),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "roadmap_status"):
            self.load_scaffold(spec)

        spec = self.scaffold_spec()
        first = Path(spec["notes"][0]["content_file"])
        first.write_text(
            self.note_content(1).replace("roadmap_status: 进行中", "roadmap_status: 已完成"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "roadmap_status.*进行中"):
            self.load_scaffold(spec)

    def test_required_overview_notes_cannot_be_replaced_by_generic_titles(self) -> None:
        spec = self.scaffold_spec()
        spec["notes"][1]["path"] = f"{self.root}/01-Python概述/§02-简介.md"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "required overview notes are missing"):
            self.load_scaffold(spec)


class WriteNotePlanTests(RoadmapContractTestCase):
    def replace_plan_with_content(self, content: str) -> dict[str, object]:
        plan = self.write_note_plan(mode="replace")
        Path(plan["content_file"]).write_text(content, encoding="utf-8")
        return plan

    def repository_anchor_plan(self) -> dict[str, object]:
        plan = self.write_note_plan()
        commit = "a" * 40
        plan.update(
            {
                "roadmap_kind": "repository",
                "repository": {
                    "provider": "github",
                    "name": "python/cpython",
                    "url": "https://github.com/python/cpython",
                    "default_branch": "main",
                    "target_ref": "refs/tags/v3.13.7",
                    "commit": commit,
                    "license_spdx": "PSF-2.0",
                    "verified_at": "2026-08-18",
                    "scope": "CPython 解释器主流程",
                    "core_slice": "源文件到字节码执行",
                    "upstream_checked_at": "2026-08-18",
                    "upstream_status": "unchanged",
                },
                "path": f"{self.root}/01-项目概述/§01-前置准备.md",
            }
        )
        content = self.write_note_content(
            stage_title="01-项目概述",
            stage_order=1,
            roadmap_status="进行中",
        ).replace(
            'roadmap_topic: "Python"\n',
            'roadmap_topic: "Python"\n'
            'roadmap_kind: repository\n'
            'repository_provider: github\n'
            'repository_name: "python/cpython"\n'
            'repository_url: "https://github.com/python/cpython"\n'
            'repository_default_branch: "main"\n'
            'repository_target_ref: "refs/tags/v3.13.7"\n'
            f'repository_commit: "{commit}"\n'
            'repository_license_spdx: "PSF-2.0"\n'
            'repository_verified_at: 2026-08-18\n'
            'repository_scope: "CPython 解释器主流程"\n'
            'core_slice: "源文件到字节码执行"\n'
            'upstream_checked_at: 2026-08-18\n'
            'upstream_status: unchanged\n'
            'graduation_status: pending\n',
        )
        Path(plan["content_file"]).write_text(content, encoding="utf-8")
        return plan

    def test_repository_anchor_write_preserves_commit_slice_and_graduation_state(self) -> None:
        normalized = self.load_write_note(self.repository_anchor_plan())
        self.assertEqual(normalized["roadmap_kind"], "repository")
        self.assertEqual(normalized["repository"]["commit"], "a" * 40)

        plan = self.repository_anchor_plan()
        content_path = Path(plan["content_file"])
        content_path.write_text(
            content_path.read_text(encoding="utf-8").replace(
                "graduation_status: pending\n", ""
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "graduation_status"):
            self.load_write_note(plan)

    def test_repository_completion_requires_real_patch_and_test_evidence(self) -> None:
        plan = self.repository_anchor_plan()
        plan["mode"] = "replace"
        plan["remove_gitkeep"] = False
        plan["expected_current_file"] = self.write_text(
            "repository-current.md", Path(plan["content_file"]).read_text(encoding="utf-8")
        )
        content_path = Path(plan["content_file"])
        content = content_path.read_text(encoding="utf-8").replace(
            "graduation_status: pending", "graduation_status: passed"
        )
        content_path.write_text(content, encoding="utf-8")
        with self.assertRaisesRegex(roadmap_cli.ContractError, "repository_patch_file"):
            self.load_write_note(plan)

        patch = b"diff --git a/a b/a\n+verified\n"
        patch_path = self.inputs / "candidate.patch"
        patch_path.write_bytes(patch)
        evidence = {
            "repository": "python/cpython",
            "repository_url": "https://github.com/python/cpython",
            "baseline_commit": "a" * 40,
            "target_ref": "refs/tags/v3.13.7",
            "license_spdx": "PSF-2.0",
            "upstream_status": "unchanged",
            "graduation_status": "passed",
            "patch_sha256": hashlib.sha256(patch).hexdigest(),
            "changed_files": ["Python/ceval.c"],
            "approved_files": ["Python/ceval.c"],
            "test": {"argv": ["python3", "-m", "test"], "returncode": 0},
        }
        evidence_path = self.inputs / "patch-evidence.json"
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        plan["repository_patch_file"] = str(patch_path)
        plan["repository_evidence_file"] = str(evidence_path)
        normalized = self.load_write_note(plan)
        self.assertEqual(normalized["roadmap_kind"], "repository")

    def test_repository_roadmap_cannot_complete_while_graduation_is_pending(self) -> None:
        plan = self.repository_anchor_plan()
        content_path = Path(plan["content_file"])
        content_path.write_text(
            content_path.read_text(encoding="utf-8").replace(
                "roadmap_status: 进行中", "roadmap_status: 已完成"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "requires graduation_status"):
            self.load_write_note(plan)

    def test_valid_create_plan_is_normalized_and_loads_exact_external_content(self) -> None:
        plan = self.write_note_plan()

        normalized = self.load_write_note(plan)

        self.assertEqual(normalized["vault_name"], "Test Vault")
        self.assertEqual(normalized["vault_path"], str(self.vault.resolve()))
        self.assertEqual(normalized["root"], self.root)
        self.assertEqual(normalized["topic"]["display"], "Python")
        self.assertEqual(normalized["learning_goal"], self.learning_goal)
        self.assertEqual(normalized["version_scope"], self.version_scope)
        self.assertEqual(normalized["path"], plan["path"])
        self.assertEqual(normalized["mode"], "create")
        self.assertTrue(normalized["remove_gitkeep"])
        self.assertEqual(
            normalized["content"],
            Path(plan["content_file"]).read_text(encoding="utf-8"),
        )
        self.assertIn('`$value` 与 "quoted text"', normalized["content"])

    def test_valid_replace_plan_requires_and_loads_exact_expected_content(self) -> None:
        plan = self.write_note_plan(mode="replace")

        normalized = self.load_write_note(plan)

        self.assertEqual(normalized["mode"], "replace")
        self.assertFalse(normalized["remove_gitkeep"])
        self.assertEqual(
            normalized["expected_current"],
            Path(plan["expected_current_file"]).read_text(encoding="utf-8"),
        )
        self.assertNotEqual(normalized["expected_current"], normalized["content"])

    def test_write_note_plan_must_match_selected_vault_identity(self) -> None:
        plan = self.write_note_plan()
        plan_path = self.write_json("note.json", plan)

        with self.assertRaisesRegex(roadmap_cli.ContractError, "vault_path|selected Vault"):
            roadmap_cli.load_write_note_plan(
                plan_path,
                actual_vault_path=str(self.sandbox / "different-vault"),
            )

    def test_content_and_expected_files_must_stay_under_plan_directory(self) -> None:
        outside = self.sandbox / "outside-plan-root"
        outside.mkdir()

        create_plan = self.write_note_plan()
        outside_content = outside / "planned-note.md"
        outside_content.write_text(self.write_note_content(), encoding="utf-8")
        create_plan["content_file"] = str(outside_content)
        with self.assertRaisesRegex(roadmap_cli.ContractError, "(?:plan|plan/spec) directory"):
            self.load_write_note(create_plan)

        replace_plan = self.write_note_plan(mode="replace")
        outside_expected = outside / "expected-current.md"
        outside_expected.write_text(self.write_note_content(body="# 旧内容\n"), encoding="utf-8")
        replace_plan["expected_current_file"] = str(outside_expected)
        with self.assertRaisesRegex(
            roadmap_cli.ContractError,
            "(?:plan|plan/spec) directory",
        ):
            self.load_write_note(replace_plan)

    def test_content_and_expected_files_may_live_in_nested_plan_directory(self) -> None:
        plan = self.write_note_plan(mode="replace")
        nested = self.inputs / "rendered" / "notes"
        nested.mkdir(parents=True)
        content = nested / "next.md"
        expected = nested / "current.md"
        content.write_text(self.write_note_content(), encoding="utf-8")
        expected.write_text(self.write_note_content(body="# 旧内容\n"), encoding="utf-8")
        plan["content_file"] = str(content)
        plan["expected_current_file"] = str(expected)

        normalized = self.load_write_note(plan)

        self.assertEqual(normalized["content"], content.read_text(encoding="utf-8"))
        self.assertEqual(
            normalized["expected_current"], expected.read_text(encoding="utf-8")
        )

    def test_target_must_be_section_numbered_markdown_below_a_numbered_stage(self) -> None:
        invalid_paths = (
            f"{self.root}/语法基础/§01-变量.md",
            f"{self.root}/02-语法基础/变量.md",
            f"{self.root}/02-语法基础/§01-变量.txt",
            f"{self.root}/§01-变量.md",
            "Other-Roadmap/02-语法基础/§01-变量.md",
        )
        for target in invalid_paths:
            plan = self.write_note_plan()
            plan["path"] = target
            with self.subTest(target=target):
                with self.assertRaisesRegex(
                    roadmap_cli.ContractError,
                    "numbered stage|01-99|§01|Markdown|roadmap root|below",
                ):
                    self.load_write_note(plan)

    def test_course_markdown_cannot_be_written_into_reserved_assets_stage(self) -> None:
        plan = self.write_note_plan()
        plan["path"] = f"{self.root}/99-assets/§01-说明.md"
        Path(plan["content_file"]).write_text(
            self.write_note_content(stage_title="99-assets", stage_order=99),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(roadmap_cli.ContractError, "99-assets|reserved|assets"):
            self.load_write_note(plan)

    def test_target_stage_and_lesson_numbers_must_match_canonical_frontmatter(self) -> None:
        replacements = (
            ('stage_title: "02-语法基础"', 'stage_title: "03-深入拓展"'),
            ("stage_order: 2", "stage_order: 3"),
            ("lesson_order: 1", "lesson_order: 2"),
            ('  - "学习路线/Python"', '  - "学习路线/Wrong"'),
            ('roadmap_topic: "Python"', 'roadmap_topic: "Wrong"'),
            (
                f"roadmap_root: {json.dumps(self.root, ensure_ascii=False)}",
                'roadmap_root: "Learning/Wrong-Roadmap"',
            ),
            (
                f"learning_goal: {json.dumps(self.learning_goal, ensure_ascii=False)}",
                'learning_goal: "different goal"',
            ),
            (
                f"version_scope: {json.dumps(self.version_scope, ensure_ascii=False)}",
                'version_scope: "Python 2.7"',
            ),
        )
        for old, new in replacements:
            plan = self.write_note_plan()
            content_path = Path(plan["content_file"])
            content_path.write_text(
                content_path.read_text(encoding="utf-8").replace(old, new),
                encoding="utf-8",
            )
            with self.subTest(replacement=new):
                with self.assertRaisesRegex(roadmap_cli.ContractError, "canonical|metadata"):
                    self.load_write_note(plan)

    def test_write_note_content_requires_complete_learning_frontmatter(self) -> None:
        plan = self.write_note_plan()
        content_path = Path(plan["content_file"])
        content_path.write_text(
            content_path.read_text(encoding="utf-8").replace("mastery_evidence: []\n", ""),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            roadmap_cli.ContractError,
            "missing propert(?:y|ies).*mastery_evidence",
        ):
            self.load_write_note(plan)

    def test_create_plan_requires_unmastered_initial_learning_state(self) -> None:
        replacements = (
            ("status: 待核验", "status: 已发布"),
            ("learning_status: 学习中", "learning_status: 已掌握"),
            ("mastery_score: 0", "mastery_score: 100"),
            ("review_count: 0", "review_count: 1"),
            (
                "mastery_evidence: []",
                'mastery_evidence:\n  - "未经验证的证据"',
            ),
        )
        for old, new in replacements:
            plan = self.write_note_plan()
            content_path = Path(plan["content_file"])
            content_path.write_text(
                content_path.read_text(encoding="utf-8").replace(old, new),
                encoding="utf-8",
            )
            with self.subTest(new=new):
                with self.assertRaisesRegex(
                    roadmap_cli.ContractError,
                    "create|initial|status|mastery|review|evidence",
                ):
                    self.load_write_note(plan)

    def test_replace_cannot_claim_mastery_without_published_evidence(self) -> None:
        invalid_replacements = (
            (
                "mastered but unpublished",
                (
                    ("learning_status: 学习中", "learning_status: 已掌握"),
                    (
                        "mastery_evidence: []",
                        'mastery_evidence:\n  - "通过实践验收"',
                    ),
                ),
            ),
            (
                "mastered without evidence",
                (
                    ("learning_status: 学习中", "learning_status: 已掌握"),
                    ("status: 待核验", "status: 已发布"),
                ),
            ),
        )
        for label, replacements in invalid_replacements:
            plan = self.write_note_plan(mode="replace")
            content_path = Path(plan["content_file"])
            content = content_path.read_text(encoding="utf-8")
            for old, new in replacements:
                content = content.replace(old, new)
            content_path.write_text(content, encoding="utf-8")
            with self.subTest(case=label):
                with self.assertRaisesRegex(
                    roadmap_cli.ContractError,
                    "mastery|published|evidence|已掌握|已发布|证据",
                ):
                    self.load_write_note(plan)

    def test_replace_rejects_invalid_mastery_score_values_and_bounds(self) -> None:
        for score in ("not-a-number", -1, 101):
            plan = self.replace_plan_with_content(
                self.write_note_content(mastery_score=score)
            )
            with self.subTest(score=score):
                with self.assertRaisesRegex(
                    roadmap_cli.ContractError,
                    "mastery_score|score|0.*100|numeric",
                ):
                    self.load_write_note(plan)

    def test_replace_rejects_invalid_review_count_values_and_bounds(self) -> None:
        for review_count in ("not-a-number", -1, 1.5):
            plan = self.replace_plan_with_content(
                self.write_note_content(review_count=review_count)
            )
            with self.subTest(review_count=review_count):
                with self.assertRaisesRegex(
                    roadmap_cli.ContractError,
                    "review_count|review|non-negative|integer",
                ):
                    self.load_write_note(plan)

    def test_published_replace_requires_nonempty_sources_and_iso_verified_date(self) -> None:
        invalid_cases = (
            (
                "missing sources",
                self.write_note_content(status="已发布", sources=()),
            ),
            (
                "empty source item",
                self.write_note_content(status="已发布", sources=("",)),
            ),
            (
                "blank source item",
                self.write_note_content(status="已发布", sources=("   ",)),
            ),
            (
                "missing verified date",
                self.write_note_content(
                    status="已发布",
                    sources=("https://docs.python.org/3/",),
                    verified_at=None,
                ),
            ),
            (
                "non-ISO verified date",
                self.write_note_content(
                    status="已发布",
                    sources=("https://docs.python.org/3/",),
                    verified_at="08/08/2026",
                ),
            ),
        )
        for label, content in invalid_cases:
            with self.subTest(case=label):
                with self.assertRaisesRegex(
                    roadmap_cli.ContractError,
                    "published|sources|source|verified_at|ISO",
                ):
                    self.load_write_note(self.replace_plan_with_content(content))

    def test_complete_published_nonmastered_replace_is_accepted(self) -> None:
        plan = self.replace_plan_with_content(
            self.write_note_content(
                status="已发布",
                sources=("https://docs.python.org/3/",),
                verified_at="2026-08-08",
            )
        )

        normalized = self.load_write_note(plan)

        self.assertEqual(normalized["mode"], "replace")
        self.assertIn("status: 已发布", normalized["content"])

    def test_mastered_replace_requires_nonempty_evidence_assessment_and_iso_reviews(self) -> None:
        common = {
            "status": "已发布",
            "learning_status": "已掌握",
            "mastery_score": 90,
            "mastery_evidence": ("[[实践验收记录]]",),
            "assessment_type": "practice",
            "assessment_at": "2026-08-08",
            "last_reviewed": "2026-08-08",
            "next_review": "2026-08-15",
            "review_count": 1,
            "sources": ("https://docs.python.org/3/",),
            "verified_at": "2026-08-08",
        }
        invalid_overrides = (
            ("empty evidence item", {"mastery_evidence": ("",)}),
            ("blank evidence item", {"mastery_evidence": ("   ",)}),
            ("missing assessment type", {"assessment_type": None}),
            ("missing assessment date", {"assessment_at": None}),
            ("non-ISO assessment date", {"assessment_at": "yesterday"}),
            ("missing last review", {"last_reviewed": None}),
            ("non-ISO last review", {"last_reviewed": "08/08/2026"}),
            ("missing next review", {"next_review": None}),
            ("non-ISO next review", {"next_review": "next week"}),
        )
        for label, overrides in invalid_overrides:
            properties = {**common, **overrides}
            content = self.write_note_content(**properties)
            with self.subTest(case=label):
                with self.assertRaisesRegex(
                    roadmap_cli.ContractError,
                    "mastered|已掌握|evidence|assessment|review|ISO",
                ):
                    self.load_write_note(self.replace_plan_with_content(content))

    def test_complete_mastered_replace_accepts_unit_defined_score_below_base_label(self) -> None:
        content = self.write_note_content(
            status="已发布",
            learning_status="已掌握",
            mastery_score=80,
            mastery_evidence=("[[实践验收记录]]",),
            assessment_type="practice",
            assessment_at="2026-08-08",
            last_reviewed="2026-08-08",
            next_review="2026-08-15",
            review_count=1,
            sources=("https://docs.python.org/3/",),
            verified_at="2026-08-08",
        )

        normalized = self.load_write_note(self.replace_plan_with_content(content))

        self.assertIn("mastery_score: 80", normalized["content"])
        self.assertIn("learning_status: 已掌握", normalized["content"])

    def test_replace_topic_anchor_requires_valid_roadmap_status(self) -> None:
        invalid_statuses: tuple[str | None, ...] = (None, "invalid")
        for roadmap_status in invalid_statuses:
            plan = self.write_note_plan(mode="replace")
            plan["path"] = f"{self.root}/01-Python概述/§01-前置准备.md"
            Path(plan["content_file"]).write_text(
                self.write_note_content(
                    stage_title="01-Python概述",
                    stage_order=1,
                    roadmap_status=roadmap_status,
                ),
                encoding="utf-8",
            )
            with self.subTest(roadmap_status=roadmap_status):
                with self.assertRaisesRegex(
                    roadmap_cli.ContractError,
                    "roadmap_status|topic anchor|anchor",
                ):
                    self.load_write_note(plan)

    def test_replace_topic_anchor_accepts_active_roadmap_status(self) -> None:
        plan = self.write_note_plan(mode="replace")
        plan["path"] = f"{self.root}/01-Python概述/§01-前置准备.md"
        Path(plan["content_file"]).write_text(
            self.write_note_content(
                stage_title="01-Python概述",
                stage_order=1,
                roadmap_status="进行中",
            ),
            encoding="utf-8",
        )

        normalized = self.load_write_note(plan)

        self.assertIn("roadmap_status: 进行中", normalized["content"])

    def test_create_forbids_expected_current_and_replace_requires_it(self) -> None:
        create_plan = self.write_note_plan()
        create_plan["expected_current_file"] = self.write_text(
            "unexpected-current.md",
            self.write_note_content(body="# 旧内容\n"),
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "create|expected_current"):
            self.load_write_note(create_plan)

        replace_plan = self.write_note_plan(mode="replace")
        del replace_plan["expected_current_file"]
        with self.assertRaisesRegex(roadmap_cli.ContractError, "replace|expected_current"):
            self.load_write_note(replace_plan)

    def test_mode_and_remove_gitkeep_have_safe_combinations(self) -> None:
        plan = self.write_note_plan()
        plan["mode"] = "append"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "mode|create|replace"):
            self.load_write_note(plan)

        plan = self.write_note_plan()
        plan["remove_gitkeep"] = "yes"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "remove_gitkeep|boolean"):
            self.load_write_note(plan)

        plan = self.write_note_plan(mode="replace")
        plan["remove_gitkeep"] = True
        with self.assertRaisesRegex(roadmap_cli.ContractError, "replace|gitkeep"):
            self.load_write_note(plan)

    def test_unfilled_placeholder_in_planned_content_is_rejected(self) -> None:
        plan = self.write_note_plan()
        Path(plan["content_file"]).write_text(
            self.write_note_content() + "\n{{TODO}}\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(roadmap_cli.ContractError, "unfilled placeholder"):
            self.load_write_note(plan)

    def test_cli_exposes_dry_run_by_default_and_explicit_apply(self) -> None:
        parser = roadmap_cli.build_parser()
        dry_run = parser.parse_args(["write-note", "--plan", "/tmp/note.json"])
        apply = parser.parse_args(
            ["write-note", "--plan", "/tmp/note.json", "--apply"]
        )

        self.assertEqual(dry_run.command, "write-note")
        self.assertEqual(dry_run.plan, "/tmp/note.json")
        self.assertFalse(dry_run.apply)
        self.assertTrue(apply.apply)
        self.assertIs(dry_run.handler, roadmap_cli.command_write_note)


class PersistentRoadmapStateContractTests(unittest.TestCase):
    skill_root = Path(__file__).resolve().parents[1]

    def test_prerequisite_template_persists_active_topic_status(self) -> None:
        template = (self.skill_root / "templates" / "overview-prerequisites.template.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("roadmap_status: 进行中", template)

    def test_base_exposes_topic_status_independently_from_unit_status(self) -> None:
        base = (self.skill_root / "templates" / "topic-roadmap.template.base").read_text(
            encoding="utf-8"
        )
        self.assertIn("note.roadmap_status:", base)
        self.assertIn("note.learning_status:", base)

    def test_resume_contract_uses_the_prerequisite_anchor_for_active_topic_discovery(self) -> None:
        resume = (self.skill_root / "workflows" / "§03-resume.md").read_text(encoding="utf-8")
        self.assertIn("§01-前置准备.md", resume)
        self.assertIn("roadmap_status", resume)
        self.assertRegex(resume, "roadmap_status[^\n]*进行中")


class RenumberPlanTests(RoadmapContractTestCase):
    def test_valid_renumber_plan_is_normalized(self) -> None:
        normalized = self.load_renumber(self.renumber_plan())

        self.assertEqual(normalized["root"], self.root)
        self.assertEqual(len(normalized["moves"]), 2)
        self.assertEqual(normalized["expected_links"][0]["minimum_count"], 1)
        self.assertTrue(normalized["expected_links"][0]["require_no_unresolved"])
        self.assertRegex(normalized["run_id"], r"^[0-9a-f]{32}$")

    def test_insertion_plan_can_add_a_directory_after_vacating_its_number(self) -> None:
        plan = self.renumber_plan()
        plan["moves"] = [
            {
                "from": f"{self.root}/02-语法基础",
                "to": f"{self.root}/03-语法基础",
            },
            {
                "from": f"{self.root}/03-深入与拓展",
                "to": f"{self.root}/04-深入与拓展",
            },
            {
                "from": f"{self.root}/04-复习与面试",
                "to": f"{self.root}/05-复习与面试",
            },
        ]
        plan["add_directories"] = [
            {"path": f"{self.root}/02-新增阶段", "keep": True}
        ]

        normalized = self.load_renumber(plan)

        self.assertEqual(normalized["add_directories"][0]["path"], f"{self.root}/02-新增阶段")

    def test_renumber_added_empty_directory_requires_gitkeep(self) -> None:
        plan = self.renumber_plan()
        plan["add_directories"] = [
            {"path": f"{self.root}/05-新增阶段", "keep": False}
        ]
        with self.assertRaisesRegex(roadmap_cli.ContractError, "keep|gitkeep"):
            self.load_renumber(plan)

    def test_property_updates_must_match_the_final_stage_directory(self) -> None:
        plan = self.renumber_plan()
        plan["property_updates"] = [
            {
                "path": f"{self.root}/03-语法基础/§01-基础.md",
                "stage_title": "03-语法基础",
                "stage_order": 3,
                "updated": "2026-08-08",
            }
        ]
        normalized = self.load_renumber(plan)
        self.assertEqual(normalized["property_updates"][0]["stage_order"], 3)

        plan["property_updates"][0]["stage_order"] = 2
        with self.assertRaisesRegex(roadmap_cli.ContractError, "match directory number"):
            self.load_renumber(plan)

    def test_property_update_path_must_be_unique_markdown(self) -> None:
        plan = self.renumber_plan()
        update = {
            "path": f"{self.root}/03-语法基础/config.json",
            "stage_title": "03-语法基础",
            "stage_order": 3,
        }
        plan["property_updates"] = [update]
        with self.assertRaisesRegex(roadmap_cli.ContractError, "must be Markdown"):
            self.load_renumber(plan)

    def test_duplicate_move_source_is_rejected(self) -> None:
        plan = self.renumber_plan()
        plan["moves"].append(copy.deepcopy(plan["moves"][0]))
        plan["moves"][-1]["to"] = f"{self.root}/04-语法基础"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "duplicate move source"):
            self.load_renumber(plan)

    def test_duplicate_move_target_is_rejected(self) -> None:
        plan = self.renumber_plan()
        plan["moves"][1]["to"] = plan["moves"][0]["to"]
        with self.assertRaisesRegex(roadmap_cli.ContractError, "duplicate move target"):
            self.load_renumber(plan)

    def test_move_must_change_path(self) -> None:
        plan = self.renumber_plan()
        plan["moves"][0]["to"] = plan["moves"][0]["from"]
        with self.assertRaisesRegex(roadmap_cli.ContractError, "does not change"):
            self.load_renumber(plan)

    def test_move_must_be_an_immediate_numbered_child(self) -> None:
        plan = self.renumber_plan()
        plan["moves"][0]["from"] = f"{self.root}/01-Python概述/02-子目录"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "immediate child"):
            self.load_renumber(plan)

        plan = self.renumber_plan()
        plan["moves"][0]["to"] = f"{self.root}/语法基础"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "01-99 prefix"):
            self.load_renumber(plan)

    def test_expected_links_must_stay_inside_roadmap_root(self) -> None:
        plan = self.renumber_plan()
        plan["expected_links"][0]["target"] = "Other-Roadmap/03-语法基础/§01-基础.md"
        with self.assertRaises(roadmap_cli.ContractError):
            self.load_renumber(plan)

    def test_base_path_must_use_topic_roadmap_suffix_inside_roadmap_root(self) -> None:
        plan = self.renumber_plan()
        plan["base"]["path"] = "📚 Learning & Research/Other-Roadmap.base"
        with self.assertRaises(roadmap_cli.ContractError):
            self.load_renumber(plan)


class RenumberEvalDriverTests(unittest.TestCase):
    """Execute the shipped JavaScript preflight against a minimal mocked Vault."""

    root = "Learning/Python"

    def run_preflight(
        self,
        *,
        current_directory_names: list[str],
        moves: list[dict[str, str]],
        files_by_directory: dict[str, list[str]] | None = None,
        property_updates: list[dict[str, object]] | None = None,
        add_directories: list[dict[str, object]] | None = None,
        roadmap_kind: str = "topic",
    ) -> dict[str, object]:
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required to execute the embedded Obsidian eval driver")
        payload = {
            "op": "renumber_preflight",
            "root": self.root,
            "moves": moves,
            "add_directories": add_directories or [],
            "expected_links": [],
            "property_updates": property_updates or [],
            "run_id": "unit-test",
        }
        encoded = base64.b64encode(
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        driver = roadmap_cli.EVAL_DRIVER.replace("__LEARN_TOPIC_PAYLOAD__", encoded)
        current_paths = [f"{self.root}/{name}" for name in current_directory_names]
        files_by_directory = files_by_directory or {}
        harness = f"""
const rootPath = {json.dumps(self.root)};
const childPaths = {json.dumps(current_paths)};
const filesByDirectory = {json.dumps(files_by_directory)};
const childFolders = childPaths.map((path) => {{
  const name = path.split("/").pop();
  const children = (filesByDirectory[name] || []).map((filename) => ({{
    path: `${{path}}/${{filename}}`,
    extension: filename.endsWith(".md") ? "md" : filename.split(".").pop(),
  }}));
  return {{path, children}};
}});
const folderMap = new Map(childFolders.map((folder) => [folder.path, folder]));
const fileMap = new Map(childFolders.flatMap((folder) => folder.children.map((file) => [file.path, file])));
const overviewPath = childPaths.find((path) => path.split("/").pop().startsWith("01-"));
const anchorPath = `${{overviewPath}}/§01-前置准备.md`;
const anchorFile = {{path: anchorPath, extension: "md"}};
const anchorContent = `---\nroadmap_kind: {roadmap_kind}\n---\n\n# Anchor\n`;
fileMap.set(anchorPath, anchorFile);
folderMap.set(rootPath, {{path: rootPath, children: childFolders}});
const adapter = {{
  exists: async () => false,
  write: async () => undefined,
  read: async () => "",
  list: async () => ({{files: [], folders: []}}),
}};
global.parseYaml = (text) => {{
  const result = {{}};
  for (const line of text.split(/\\r?\\n/)) {{
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*):\\s*(.*)$/);
    if (match) result[match[1]] = match[2] || null;
  }}
  return result;
}};
global.app = {{
  vault: {{
    adapter,
    createFolder: async () => undefined,
    create: async () => undefined,
    read: async (file) => file.path === anchorPath ? anchorContent : "",
    getMarkdownFiles: () => [anchorFile],
    getFolderByPath: (path) => folderMap.get(path) || null,
    getFileByPath: (path) => fileMap.get(path) || null,
    getAbstractFileByPath: (path) => folderMap.get(path) || fileMap.get(path) || null,
    getConfig: (key) => key === "trashOption" ? "system" : true,
  }},
  fileManager: {{
    renameFile: async () => undefined,
    trashFile: async () => undefined,
    processFrontMatter: async () => undefined,
  }},
}};
(async () => {{
  const output = await eval({json.dumps(driver)});
  process.stdout.write(String(output));
}})().catch((error) => {{
  process.stderr.write(error?.stack || String(error));
  process.exit(1);
}});
"""
        completed = subprocess.run(
            [node, "-e", harness],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        marker_index = completed.stdout.rfind(roadmap_cli.SENTINEL)
        self.assertGreaterEqual(marker_index, 0, completed.stdout)
        return json.loads(completed.stdout[marker_index + len(roadmap_cli.SENTINEL) :])

    def test_renumber_preflight_rejects_a_gap_in_final_top_level_numbers(self) -> None:
        result = self.run_preflight(
            current_directory_names=["01-Python概述", "02-语法基础", "03-深入拓展", "04-复习面试", "99-assets"],
            moves=[
                {
                    "from": f"{self.root}/04-复习面试",
                    "to": f"{self.root}/05-复习面试",
                }
            ],
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "contiguous from 01")

    def test_renumber_preflight_allows_contiguous_numbers_plus_99_assets(self) -> None:
        result = self.run_preflight(
            current_directory_names=["01-Python概述", "02-语法基础", "03-深拓展", "99-assets"],
            moves=[
                {
                    "from": f"{self.root}/03-深拓展",
                    "to": f"{self.root}/03-深与拓展",
                }
            ],
        )

        self.assertTrue(result["ok"], result)

    def test_renumber_preflight_rejects_missing_property_updates_for_moved_markdown(self) -> None:
        result = self.run_preflight(
            current_directory_names=["01-Python概述", "02-语法基础", "03-深入拓展", "04-复习面试", "99-assets"],
            files_by_directory={"02-语法基础": ["§01-变量.md"]},
            moves=[
                {
                    "from": f"{self.root}/02-语法基础",
                    "to": f"{self.root}/03-语法基础",
                },
                {
                    "from": f"{self.root}/03-深入拓展",
                    "to": f"{self.root}/02-深入拓展",
                },
            ],
            property_updates=[],
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "property_updates.*§01-变量\\.md")

    def test_renumber_preflight_accepts_complete_property_updates_for_moved_markdown(self) -> None:
        result = self.run_preflight(
            current_directory_names=["01-Python概述", "02-语法基础", "03-深入拓展", "04-复习面试", "99-assets"],
            files_by_directory={"02-语法基础": ["§01-变量.md"]},
            moves=[
                {
                    "from": f"{self.root}/02-语法基础",
                    "to": f"{self.root}/03-语法基础",
                },
                {
                    "from": f"{self.root}/03-深入拓展",
                    "to": f"{self.root}/02-深入拓展",
                },
            ],
            property_updates=[
                {
                    "path": f"{self.root}/03-语法基础/§01-变量.md",
                    "stage_title": "03-语法基础",
                    "stage_order": 3,
                }
            ],
        )

        self.assertTrue(result["ok"], result)

    def test_renumber_preflight_requires_final_99_assets(self) -> None:
        result = self.run_preflight(
            current_directory_names=["01-Python概述", "02-语法基础", "03-深入拓展", "04-复习面试"],
            moves=[
                {
                    "from": f"{self.root}/04-复习面试",
                    "to": f"{self.root}/04-复习与面试",
                }
            ],
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "99-assets")

    def test_repository_outer_route_cannot_be_renumbered_or_downgraded(self) -> None:
        result = self.run_preflight(
            current_directory_names=[
                "01-项目概述", "02-运行与测试基线", "03-架构与模块地图",
                "04-核心调用链", "05-测试与质量体系", "06-Issue与PR考古",
                "07-最小修复实践", "08-深入与拓展", "09-复习与贡献准备",
                "99-assets",
            ],
            moves=[
                {"from": f"{self.root}/04-核心调用链", "to": f"{self.root}/04-源码漫游"}
            ],
            roadmap_kind="repository",
        )
        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "repository outer route|fixed")

    def test_renumber_preflight_cannot_convert_99_assets_into_numbered_stage(self) -> None:
        result = self.run_preflight(
            current_directory_names=["01-Python概述", "02-语法基础", "03-深入拓展", "04-复习面试", "99-assets"],
            moves=[
                {
                    "from": f"{self.root}/99-assets",
                    "to": f"{self.root}/05-assets",
                }
            ],
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "99-assets")

    def test_renumber_preflight_cannot_swap_overview_out_of_directory_one(self) -> None:
        result = self.run_preflight(
            current_directory_names=["01-Python概述", "02-语法基础", "03-深入拓展", "04-复习面试", "99-assets"],
            moves=[
                {
                    "from": f"{self.root}/01-Python概述",
                    "to": f"{self.root}/02-Python概述",
                },
                {
                    "from": f"{self.root}/02-语法基础",
                    "to": f"{self.root}/01-语法基础",
                },
            ],
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "overview|anchor|01")

    def test_renumber_preflight_allows_overview_rename_within_directory_one(self) -> None:
        result = self.run_preflight(
            current_directory_names=["01-Python概述", "02-语法基础", "03-深入拓展", "04-复习面试", "99-assets"],
            moves=[
                {
                    "from": f"{self.root}/01-Python概述",
                    "to": f"{self.root}/01-Python入门概述",
                }
            ],
        )

        self.assertTrue(result["ok"], result)


class WriteNoteEvalDriverTests(RoadmapContractTestCase):
    """Execute the write-note CAS and gitkeep behavior against a mocked Vault."""

    def run_write_note(
        self,
        *,
        operation: str,
        mode: str,
        target_exists: bool,
        existing_content: str | None = None,
        gitkeep_exists: bool = False,
        remove_gitkeep: bool | None = None,
        lesson_order: int = 1,
        sibling_note_names: list[str] | None = None,
        sibling_note_states: dict[str, str] | None = None,
        extra_markdown_files: dict[str, str] | None = None,
        payload_content: str | None = None,
        anchor: bool = False,
        base_exists: bool = True,
        base_filter_root: str | None = None,
        vault_anchor_kind: str = "topic",
    ) -> dict[str, object]:
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required to execute the embedded Obsidian eval driver")
        plan = self.write_note_plan(mode=mode)
        if anchor:
            plan["path"] = f"{self.root}/01-Python概述/§01-前置准备.md"
            Path(plan["content_file"]).write_text(
                self.write_note_content(
                    stage_title="01-Python概述",
                    stage_order=1,
                    roadmap_status="进行中",
                ),
                encoding="utf-8",
            )
        elif lesson_order != 1:
            plan["path"] = str(plan["path"]).replace(
                "§01-", f"§{lesson_order:02d}-", 1
            )
            Path(plan["content_file"]).write_text(
                self.write_note_content(lesson_order=lesson_order),
                encoding="utf-8",
            )
        if remove_gitkeep is not None:
            plan["remove_gitkeep"] = remove_gitkeep
        normalized = self.load_write_note(plan)
        if payload_content is not None:
            normalized["content"] = payload_content
        normalized["op"] = operation
        encoded = base64.b64encode(
            json.dumps(normalized, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        driver = roadmap_cli.EVAL_DRIVER.replace("__LEARN_TOPIC_PAYLOAD__", encoded)
        target = normalized["path"]
        parent = PurePosixPath(target).parent.as_posix()
        gitkeep = normalized["gitkeep_path"]
        route_base_path = f"{self.root}/{PurePosixPath(self.root).name}-Roadmap.base"
        selected_filter_root = base_filter_root or self.root
        route_base_content = self.base_content(selected_filter_root)
        anchor_path = f"{self.root}/01-Python概述/§01-前置准备.md"
        anchor_content = self.write_note_content(
            stage_title="01-Python概述",
            stage_order=1,
            learning_status="已掌握",
            roadmap_status="进行中",
        )
        if vault_anchor_kind == "repository":
            anchor_content = anchor_content.replace(
                'roadmap_topic: "Python"\n',
                'roadmap_topic: "Python"\nroadmap_kind: repository\n',
            )
        route_base_document = {
            "filters": {
                "and": [
                    'file.ext == "md"',
                    f"file.inFolder({json.dumps(selected_filter_root, ensure_ascii=False)})",
                ]
            },
            "views": [
                {"name": name}
                for name in ("学习路线", "学习中", "阻塞", "待复习", "已掌握", "待核验")
            ],
        }
        sibling_contents: dict[str, str] = {}
        for name in sibling_note_names or []:
            match = re.match(r"^§(\d{2})-", name)
            order = int(match.group(1)) if match else 1
            sibling_contents[name] = self.write_note_content(
                lesson_order=order,
                learning_status="未开始",
            )
        for name, learning_state in (sibling_note_states or {}).items():
            match = re.match(r"^§(\d{2})-", name)
            order = int(match.group(1)) if match else 1
            sibling_contents[name] = self.write_note_content(
                lesson_order=order,
                learning_status=learning_state,
            )
        starting_content = existing_content
        if target_exists and starting_content is None:
            starting_content = normalized.get("expected_current") or "existing content"
        harness = f"""
const marker = {json.dumps(roadmap_cli.SENTINEL)};
const rootPath = {json.dumps(normalized["root"], ensure_ascii=False)};
const parentPath = {json.dumps(parent, ensure_ascii=False)};
const targetPath = {json.dumps(target, ensure_ascii=False)};
const gitkeepPath = {json.dumps(gitkeep, ensure_ascii=False)};
const routeBasePath = {json.dumps(route_base_path, ensure_ascii=False)};
const routeBaseContent = {json.dumps(route_base_content, ensure_ascii=False)};
const routeBaseDocument = {json.dumps(route_base_document, ensure_ascii=False)};
const anchorPath = {json.dumps(anchor_path, ensure_ascii=False)};
const anchorContent = {json.dumps(anchor_content, ensure_ascii=False)};
const folders = new Map([
  [rootPath, {{path: rootPath, children: []}}],
  [parentPath, {{path: parentPath, children: []}}],
]);
const files = new Map();
const contents = new Map();
if (targetPath !== anchorPath) {{
  const anchorFile = {{path: anchorPath, extension: "md"}};
  files.set(anchorPath, anchorFile);
  contents.set(anchorPath, anchorContent);
}}
const siblingContents = {json.dumps(sibling_contents, ensure_ascii=False)};
for (const [name, content] of Object.entries(siblingContents)) {{
  const path = `${{parentPath}}/${{name}}`;
  const file = {{path, extension: "md"}};
  files.set(path, file);
  contents.set(path, content);
  folders.get(parentPath).children.push(file);
}}
if ({json.dumps(base_exists)}) {{
  const file = {{path: routeBasePath, extension: "base"}};
  files.set(routeBasePath, file);
  contents.set(routeBasePath, routeBaseContent);
  folders.get(rootPath).children.push(file);
}}
const extraMarkdownFiles = {json.dumps(extra_markdown_files or {}, ensure_ascii=False)};
for (const [path, content] of Object.entries(extraMarkdownFiles)) {{
  const file = {{path, extension: "md"}};
  files.set(path, file);
  contents.set(path, content);
}}
if ({json.dumps(target_exists)}) {{
  const file = {{path: targetPath, extension: "md"}};
  files.set(targetPath, file);
  contents.set(targetPath, {json.dumps(starting_content, ensure_ascii=False)});
  folders.get(parentPath).children.push(file);
}}
const adapterFiles = new Map();
if ({json.dumps(gitkeep_exists)}) adapterFiles.set(gitkeepPath, "");
const calls = {{create: [], modify: [], adapterRemove: []}};
const adapter = {{
  exists: async (path) => folders.has(path) || files.has(path) || adapterFiles.has(path),
  write: async (path, content) => adapterFiles.set(path, content),
  read: async (path) => adapterFiles.has(path) ? adapterFiles.get(path) : contents.get(path),
  remove: async (path) => {{
    calls.adapterRemove.push(path);
    adapterFiles.delete(path);
  }},
  list: async () => ({{files: [], folders: []}}),
}};
const parseScalar = (raw) => {{
  if (raw === "") return null;
  if (raw === "[]") return [];
  if (raw === "true") return true;
  if (raw === "false") return false;
  if (/^-?\\d+$/.test(raw)) return Number(raw);
  if (raw.startsWith('"') && raw.endsWith('"')) return JSON.parse(raw);
  return raw;
}};
global.parseYaml = (text) => {{
  if (text === routeBaseContent) return routeBaseDocument;
  const result = {{}};
  let listKey = null;
  for (const rawLine of text.split(/\\r?\\n/)) {{
    if (rawLine === "---" || rawLine.trim() === "") continue;
    const listMatch = rawLine.match(/^\\s+-\\s+(.+)$/);
    if (listMatch && listKey) {{
      if (!Array.isArray(result[listKey])) result[listKey] = [];
      result[listKey].push(parseScalar(listMatch[1]));
      continue;
    }}
    const propertyMatch = rawLine.match(/^([A-Za-z_][A-Za-z0-9_]*):(?:\\s*(.*))?$/);
    if (!propertyMatch) continue;
    listKey = propertyMatch[1];
    result[listKey] = parseScalar(propertyMatch[2] || "");
  }}
  return result;
}};
const readFile = async (file) => contents.get(file.path);
global.app = {{
  vault: {{
    adapter,
    createFolder: async () => undefined,
    create: async (path, content) => {{
      calls.create.push({{path, content}});
      if (files.has(path)) throw new Error(`collision: ${{path}}`);
      const file = {{path, extension: "md"}};
      files.set(path, file);
      contents.set(path, content);
      folders.get(parentPath).children.push(file);
      return file;
    }},
    modify: async (file, content) => {{
      calls.modify.push({{path: file.path, content}});
      contents.set(file.path, content);
    }},
    read: readFile,
    cachedRead: readFile,
    getMarkdownFiles: () => [...files.values()].filter((file) => file.extension === "md"),
    getFolderByPath: (path) => folders.get(path) || null,
    getFileByPath: (path) => files.get(path) || null,
    getAbstractFileByPath: (path) => folders.get(path) || files.get(path) || null,
    getConfig: (key) => key === "trashOption" ? "system" : true,
  }},
  fileManager: {{
    renameFile: async () => undefined,
    trashFile: async () => undefined,
    processFrontMatter: async () => undefined,
  }},
  metadataCache: {{
    isCacheClean: () => true,
    resolvedLinks: {{}},
    unresolvedLinks: {{}},
    getFileCache: () => null,
  }},
  workspace: {{getLeavesOfType: () => []}},
}};
(async () => {{
  const raw = await eval({json.dumps(driver)});
  const markerIndex = raw.lastIndexOf(marker);
  const report = JSON.parse(raw.slice(markerIndex + marker.length));
  report.harness = {{
    targetExists: files.has(targetPath),
    targetContent: contents.get(targetPath) ?? null,
    gitkeepExists: adapterFiles.has(gitkeepPath),
    calls,
  }};
  process.stdout.write(marker + JSON.stringify(report));
}})().catch((error) => {{
  process.stderr.write(error?.stack || String(error));
  process.exit(1);
}});
"""
        completed = subprocess.run(
            [node, "-e", harness],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        marker_index = completed.stdout.rfind(roadmap_cli.SENTINEL)
        self.assertGreaterEqual(marker_index, 0, completed.stdout)
        return json.loads(completed.stdout[marker_index + len(roadmap_cli.SENTINEL) :])

    def test_create_preflight_rejects_existing_target(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="create",
            target_exists=True,
            gitkeep_exists=True,
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "already exists|create")

    def test_replace_preflight_rejects_missing_target(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="replace",
            target_exists=False,
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "does not exist|missing|replace")

    def test_replace_preflight_rejects_content_changed_since_plan(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="replace",
            target_exists=True,
            existing_content="# concurrently changed\n",
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "changed|snapshot|expected")

    def test_write_note_preflight_rejects_missing_topic_roadmap_base(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="replace",
            target_exists=True,
            base_exists=False,
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "roadmap Base.*missing|Base is missing")

    def test_write_note_preflight_rejects_base_scoped_to_another_root(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="replace",
            target_exists=True,
            base_filter_root="Learning/Other-Roadmap",
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "Base.*root filter|filter.*match")

    def test_write_note_cannot_downgrade_repository_anchor_to_topic_plan(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="create",
            target_exists=False,
            gitkeep_exists=True,
            vault_anchor_kind="repository",
        )
        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "roadmap_kind.*Vault anchor|repository")

    def test_write_note_preflight_rejects_another_active_unit_in_same_roadmap(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="replace",
            target_exists=True,
            sibling_note_states={"§02-另一个学习单元.md": "学习中"},
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "another learning unit|already active|学习中")

    def test_create_preflight_requires_remove_gitkeep_when_gitkeep_exists(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="create",
            target_exists=False,
            gitkeep_exists=True,
            remove_gitkeep=False,
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "gitkeep|remove_gitkeep")

    def test_create_preflight_rejects_remove_gitkeep_when_gitkeep_is_missing(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="create",
            target_exists=False,
            gitkeep_exists=False,
            remove_gitkeep=True,
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "gitkeep|missing")

    def test_create_preflight_rejects_a_gap_after_existing_lesson(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="create",
            target_exists=False,
            remove_gitkeep=False,
            lesson_order=3,
            sibling_note_names=["§01-已有课程.md"],
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "contiguous|next|§02|lesson")

    def test_create_preflight_requires_first_lesson_in_empty_stage(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="create",
            target_exists=False,
            gitkeep_exists=True,
            remove_gitkeep=True,
            lesson_order=9,
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "first|next|§01|lesson")

    def test_create_preflight_accepts_the_next_contiguous_lesson(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="create",
            target_exists=False,
            remove_gitkeep=False,
            lesson_order=2,
            sibling_note_names=["§01-已有课程.md"],
        )

        self.assertTrue(result["ok"], result)

    def test_create_preflight_ignores_parent_readme_when_counting_lessons(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="create",
            target_exists=False,
            gitkeep_exists=True,
            remove_gitkeep=True,
            lesson_order=1,
            sibling_note_names=["README.md"],
        )

        self.assertTrue(result["ok"], result)

    def test_active_unit_scan_ignores_experiment_readme_under_assets(self) -> None:
        result = self.run_write_note(
            operation="write_note_preflight",
            mode="replace",
            target_exists=True,
            extra_markdown_files={
                f"{self.root}/99-assets/实验/README.md": "# 实验说明\n\nlearning_status: 学习中\n"
            },
        )

        self.assertTrue(result["ok"], result)

    def test_create_apply_writes_exact_content_then_removes_only_stage_gitkeep(self) -> None:
        result = self.run_write_note(
            operation="write_note_apply",
            mode="create",
            target_exists=False,
            gitkeep_exists=True,
        )

        self.assertTrue(result["ok"], result)
        harness = result["harness"]
        self.assertTrue(harness["targetExists"])
        self.assertEqual(harness["targetContent"], self.write_note_content())
        self.assertFalse(harness["gitkeepExists"])
        self.assertEqual(len(harness["calls"]["create"]), 1)
        self.assertEqual(harness["calls"]["modify"], [])
        self.assertEqual(
            harness["calls"]["adapterRemove"],
            [f"{self.root}/02-语法基础/.gitkeep"],
        )

    def test_replace_apply_writes_exact_content_without_touching_gitkeep(self) -> None:
        plan = self.write_note_plan(mode="replace")
        expected = Path(plan["expected_current_file"]).read_text(encoding="utf-8")
        result = self.run_write_note(
            operation="write_note_apply",
            mode="replace",
            target_exists=True,
            existing_content=expected,
        )

        self.assertTrue(result["ok"], result)
        harness = result["harness"]
        self.assertEqual(harness["targetContent"], self.write_note_content())
        self.assertEqual(harness["calls"]["create"], [])
        self.assertEqual(len(harness["calls"]["modify"]), 1)
        self.assertEqual(harness["calls"]["adapterRemove"], [])


class ScaffoldEvalDriverTests(unittest.TestCase):
    root = "Learning/Python"
    learning_goal = "掌握 Python 自动化"
    version_scope = "Python 3.13"

    def valid_base_content(self) -> str:
        return "filters: []\nproperties:\n  note.roadmap_status: {}\nviews: []\n"

    def parsed_base_document(self) -> dict[str, object]:
        return {
            "filters": {
                "and": [
                    'file.ext == "md"',
                    f"file.inFolder({json.dumps(self.root, ensure_ascii=False)})",
                ]
            },
            "formulas": {
                "route_order": "if(stage_order && lesson_order, stage_order * 100 + lesson_order, 0)",
                "review_due": "if(next_review, date(next_review) <= today(), false)",
                "mastery_label": 'if(mastery_score >= 85, "稳固", if(mastery_score >= 60, "需巩固", "未掌握"))',
            },
            "properties": {
                "note.learning_status": {},
                "note.roadmap_status": {},
                "note.mastery_evidence": {},
            },
            "views": [
                {
                    "name": "学习路线",
                    "groupBy": {"property": "note.stage_title", "direction": "ASC"},
                    "sort": [{"property": "formula.route_order", "direction": "ASC"}],
                },
                {"name": "学习中", "filters": {"and": ['learning_status == "学习中"']}},
                {"name": "阻塞", "filters": {"and": ['learning_status == "阻塞"']}},
                {
                    "name": "待复习",
                    "filters": {
                        "and": [
                            "formula.review_due == true",
                            {
                                "or": [
                                    'learning_status == "已掌握"',
                                    'learning_status == "待复习"',
                                ]
                            },
                        ]
                    },
                },
                {
                    "name": "已掌握",
                    "filters": {
                        "and": [
                            'learning_status == "已掌握"',
                            'status == "已发布"',
                            "list(mastery_evidence).length > 0",
                        ]
                    },
                },
                {"name": "待核验", "filters": {"and": ['status == "待核验"']}},
            ],
        }

    def valid_note_content(self) -> str:
        return (
            "---\n"
            'title: "前置准备"\n'
            "aliases: []\n"
            "tags:\n"
            '  - "学习路线/Python"\n'
            "date: 2026-08-08\n"
            "updated: 2026-08-08\n"
            "status: 待核验\n"
            "category: Learning\n"
            "note_type: 教程\n"
            "difficulty: 入门\n"
            f"roadmap_root: {json.dumps(self.root, ensure_ascii=False)}\n"
            'roadmap_topic: "Python"\n'
            f"learning_goal: {json.dumps(self.learning_goal, ensure_ascii=False)}\n"
            "knowledge_points_total: 0\n"
            "knowledge_points_covered: 0\n"
            "knowledge_points_pending: 0\n"
            'stage_title: "01-Python概述"\n'
            "stage_order: 1\n"
            "lesson_order: 1\n"
            "learning_status: 学习中\n"
            "roadmap_status: 进行中\n"
            "mastery_score: 0\n"
            "hard_prerequisites: []\n"
            "soft_prerequisites: []\n"
            "blocked_by: []\n"
            "mastery_evidence: []\n"
            "assessment_type:\n"
            "assessment_at:\n"
            "last_reviewed:\n"
            "next_review:\n"
            "review_count: 0\n"
            "verified_at: 2026-08-08\n"
            f"version_scope: {json.dumps(self.version_scope, ensure_ascii=False)}\n"
            "sources: []\n"
            "---\n\n"
            "# 前置准备\n"
        )

    def run_preflight(
        self,
        *,
        base_content: str,
        note_content: str,
        parsed_base: dict[str, object] | None = None,
    ) -> dict[str, object]:
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required to execute the embedded Obsidian eval driver")
        payload = {
            "op": "scaffold_preflight",
            "root": self.root,
            "topic": {"display": "Python", "path_segment": "Python", "tag": "Python"},
            "learning_goal": self.learning_goal,
            "version_scope": self.version_scope,
            "base": {
                "path": f"{self.root}/Python-Roadmap.base",
                "content": base_content,
            },
            "directories": [
                {"path": f"{self.root}/01-Python概述", "role": "overview", "keep": False},
                {"path": f"{self.root}/02-语法基础", "role": "formal", "keep": True},
                {"path": f"{self.root}/03-深入与拓展", "role": "extension", "keep": True},
                {"path": f"{self.root}/04-复习与面试", "role": "review", "keep": True},
                {"path": f"{self.root}/99-assets", "role": "assets", "keep": True},
            ],
            "notes": [
                {
                    "path": f"{self.root}/01-Python概述/§01-前置准备.md",
                    "content": note_content,
                }
            ],
            "gitkeeps": [
                f"{self.root}/02-语法基础/.gitkeep",
                f"{self.root}/03-深入与拓展/.gitkeep",
                f"{self.root}/04-复习与面试/.gitkeep",
                f"{self.root}/99-assets/.gitkeep",
            ],
        }
        encoded = base64.b64encode(
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        driver = roadmap_cli.EVAL_DRIVER.replace("__LEARN_TOPIC_PAYLOAD__", encoded)
        parsed_base = parsed_base or self.parsed_base_document()
        harness = f"""
const parsedBase = {json.dumps(parsed_base, ensure_ascii=False)};
const adapter = {{
  exists: async () => false,
  write: async () => undefined,
  read: async () => "",
  list: async () => ({{files: [], folders: []}}),
}};
global.parseYaml = (text) => {{
  if (text.includes("filters: [\\n") || text.includes("title: [broken")) {{
    throw new Error("invalid YAML in acceptance fixture");
  }}
  if (text.includes("filters:") && text.includes("views:")) {{
    return parsedBase;
  }}
  const result = {{}};
  let listKey = null;
  const scalar = (raw) => {{
    if (raw === "") return null;
    if (raw === "[]") return [];
    if (raw === "true") return true;
    if (raw === "false") return false;
    if (/^-?\\d+$/.test(raw)) return Number(raw);
    if (raw.startsWith('"') && raw.endsWith('"')) return JSON.parse(raw);
    return raw;
  }};
  for (const rawLine of text.split(/\\r?\\n/)) {{
    if (rawLine === "---" || rawLine.trim() === "") continue;
    const listMatch = rawLine.match(/^\\s+-\\s+(.+)$/);
    if (listMatch && listKey) {{
      if (!Array.isArray(result[listKey])) result[listKey] = [];
      result[listKey].push(scalar(listMatch[1]));
      continue;
    }}
    const propertyMatch = rawLine.match(/^([A-Za-z_][A-Za-z0-9_]*):(?:\\s*(.*))?$/);
    if (!propertyMatch) continue;
    listKey = propertyMatch[1];
    result[listKey] = scalar(propertyMatch[2] || "");
  }}
  return result;
}};
global.app = {{
  vault: {{
    adapter,
    createFolder: async () => undefined,
    create: async () => undefined,
    getFolderByPath: () => null,
    getFileByPath: () => null,
    getAbstractFileByPath: () => null,
    getConfig: (key) => key === "trashOption" ? "system" : true,
  }},
  fileManager: {{
    renameFile: async () => undefined,
    trashFile: async () => undefined,
    processFrontMatter: async () => undefined,
  }},
}};
(async () => {{
  const output = await eval({json.dumps(driver)});
  process.stdout.write(String(output));
}})().catch((error) => {{
  process.stderr.write(error?.stack || String(error));
  process.exit(1);
}});
"""
        completed = subprocess.run(
            [node, "-e", harness],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        marker_index = completed.stdout.rfind(roadmap_cli.SENTINEL)
        self.assertGreaterEqual(marker_index, 0, completed.stdout)
        return json.loads(completed.stdout[marker_index + len(roadmap_cli.SENTINEL) :])

    def test_scaffold_preflight_rejects_malformed_base_yaml(self) -> None:
        result = self.run_preflight(
            base_content="filters: [\nviews: []\n",
            note_content=self.valid_note_content(),
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "(?i)ya?ml")

    def test_scaffold_preflight_rejects_malformed_markdown_frontmatter(self) -> None:
        result = self.run_preflight(
            base_content=self.valid_base_content(),
            note_content=self.valid_note_content().replace('title: "前置准备"', "title: [broken"),
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "(?i)frontmatter|ya?ml")

    def test_scaffold_preflight_accepts_complete_parsed_frontmatter(self) -> None:
        result = self.run_preflight(
            base_content=self.valid_base_content(),
            note_content=self.valid_note_content(),
        )

        self.assertTrue(result["ok"], result)

    def test_scaffold_preflight_rejects_noninitial_mastery_and_review_state(self) -> None:
        mutations = (
            ("published", "status: 待核验", "status: 已发布"),
            ("nonzero score", "mastery_score: 0", "mastery_score: 1"),
            (
                "premature evidence",
                "mastery_evidence: []",
                'mastery_evidence:\n  - "未经验收"',
            ),
            ("assessment type", "assessment_type:\n", "assessment_type: quiz\n"),
            ("assessment date", "assessment_at:\n", "assessment_at: 2026-08-08\n"),
            ("last reviewed", "last_reviewed:\n", "last_reviewed: 2026-08-08\n"),
            ("next review", "next_review:\n", "next_review: 2026-08-09\n"),
            ("review count", "review_count: 0", "review_count: 1"),
        )
        for label, old, new in mutations:
            note = self.valid_note_content()
            self.assertIn(old, note)
            result = self.run_preflight(
                base_content=self.valid_base_content(),
                note_content=note.replace(old, new),
            )
            with self.subTest(field=label):
                self.assertFalse(result["ok"], result)
                self.assertRegex(
                    str(result.get("error")),
                    "initial scaffold|mastery|publication state",
                )

    def test_scaffold_preflight_matches_json_serialized_filter_for_apostrophe_root(self) -> None:
        original_root = self.root
        self.root = "Learning/O'Reilly-Roadmap"
        self.addCleanup(setattr, self, "root", original_root)
        parsed_base = self.parsed_base_document()

        result = self.run_preflight(
            base_content=self.valid_base_content(),
            note_content=self.valid_note_content(),
            parsed_base=parsed_base,
        )

        expected = f"file.inFolder({json.dumps(self.root, ensure_ascii=False)})"
        self.assertIn(expected, parsed_base["filters"]["and"])
        self.assertTrue(result["ok"], result)

    def test_scaffold_preflight_rejects_required_property_moved_into_body(self) -> None:
        note = self.valid_note_content().replace("learning_status: 学习中\n", "")
        note += "\nlearning_status: 学习中\n"
        result = self.run_preflight(
            base_content=self.valid_base_content(),
            note_content=note,
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "learning_status")

    def test_scaffold_preflight_validates_canonical_value_from_parsed_object(self) -> None:
        canonical = f"roadmap_root: {json.dumps(self.root, ensure_ascii=False)}\n"
        note = self.valid_note_content().replace(
            canonical,
            canonical + 'roadmap_root: "Learning/Wrong-Roadmap"\n',
        )
        result = self.run_preflight(
            base_content=self.valid_base_content(),
            note_content=note,
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "roadmap_root|canonical")

    def test_scaffold_preflight_rejects_wide_or_wrong_base_filters_and_formula(self) -> None:
        parsed_base = self.parsed_base_document()
        parsed_base["filters"] = {"and": ["true"]}
        parsed_base["formulas"] = {"route_order": "0"}
        result = self.run_preflight(
            base_content=self.valid_base_content(),
            note_content=self.valid_note_content(),
            parsed_base=parsed_base,
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "filter|route_order|formula")

    def test_scaffold_preflight_rejects_named_views_without_required_behavior(self) -> None:
        parsed_base = self.parsed_base_document()
        for view in parsed_base["views"]:
            if view["name"] != "学习路线":
                view["filters"] = {"and": ["true"]}
        result = self.run_preflight(
            base_content=self.valid_base_content(),
            note_content=self.valid_note_content(),
            parsed_base=parsed_base,
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "view|filter|学习中|阻塞|待复习|已掌握|待核验")

    def test_scaffold_preflight_rejects_wrong_review_due_formula(self) -> None:
        parsed_base = self.parsed_base_document()
        parsed_base["formulas"]["review_due"] = "false"
        result = self.run_preflight(
            base_content=self.valid_base_content(),
            note_content=self.valid_note_content(),
            parsed_base=parsed_base,
        )

        self.assertFalse(result["ok"], result)
        self.assertRegex(str(result.get("error")), "review_due|formula")

    def test_scaffold_preflight_allows_additional_confirmed_base_views(self) -> None:
        parsed_base = self.parsed_base_document()
        parsed_base["views"].append({"name": "学习时间线", "filters": {"and": ["true"]}})
        result = self.run_preflight(
            base_content=self.valid_base_content(),
            note_content=self.valid_note_content(),
            parsed_base=parsed_base,
        )

        self.assertTrue(result["ok"], result)


class ObsidianOutputTests(unittest.TestCase):
    def cli(self) -> roadmap_cli.ObsidianCLI:
        instance = object.__new__(roadmap_cli.ObsidianCLI)
        instance.vault_name = "Test Vault"
        instance.executable = "/usr/local/bin/obsidian"
        return instance

    def test_exit_zero_with_error_text_is_rejected(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["obsidian"],
            returncode=0,
            stdout="Error: File not found",
            stderr="",
        )
        cli = self.cli()
        with mock.patch.object(roadmap_cli.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(roadmap_cli.ContractError, "reported an error"):
                cli.command("read", "path=missing.md")

    def test_eval_requires_a_structured_sentinel(self) -> None:
        cli = self.cli()
        with mock.patch.object(cli, "text", return_value="undefined"):
            with self.assertRaisesRegex(roadmap_cli.ContractError, "0 structured sentinels"):
                cli.eval("probe", {})

    def test_eval_rejects_malformed_sentinel_json(self) -> None:
        cli = self.cli()
        with mock.patch.object(cli, "text", return_value="LEARN_TOPIC_JSON:{broken}"):
            with self.assertRaisesRegex(roadmap_cli.ContractError, "not valid JSON"):
                cli.eval("probe", {})

    def test_eval_rejects_ok_false(self) -> None:
        cli = self.cli()
        payload = {
            "learnTopic": True,
            "ok": False,
            "op": "probe",
            "error": "capability missing",
        }
        with mock.patch.object(
            cli,
            "text",
            return_value=f"LEARN_TOPIC_JSON:{json.dumps(payload)}",
        ):
            with self.assertRaisesRegex(roadmap_cli.ContractError, "capability missing"):
                cli.eval("probe", {})

    def test_eval_accepts_one_ok_sentinel(self) -> None:
        cli = self.cli()
        payload = {"learnTopic": True, "ok": True, "op": "probe", "capabilities": {}}
        with mock.patch.object(
            cli,
            "text",
            return_value=f"=> LEARN_TOPIC_JSON:{json.dumps(payload)}",
        ):
            self.assertEqual(cli.eval("probe", {}), payload)


class BaseQueryTests(unittest.TestCase):
    def test_base_query_returns_output_when_all_expected_rows_are_present(self) -> None:
        cli = mock.Mock()
        cli.text.return_value = "Roadmap/01-Overview/§01-Start.md\nRoadmap/01-Overview/§02-What.md"
        base = {
            "path": "Roadmap/Roadmap.base",
            "view": "学习路线",
            "expected_paths": [
                "Roadmap/01-Overview/§01-Start.md",
                "Roadmap/01-Overview/§02-What.md",
            ],
        }

        result = roadmap_cli.base_query(cli, base)

        self.assertEqual(result["output"], cli.text.return_value)
        cli.text.assert_called_once_with(
            "base:query",
            "path=Roadmap/Roadmap.base",
            "view=学习路线",
            "format=paths",
        )

    def test_base_query_rejects_a_missing_expected_row(self) -> None:
        cli = mock.Mock()
        cli.text.return_value = "Roadmap/01-Overview/§01-Start.md"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "missing expected paths"):
            roadmap_cli.base_query(
                cli,
                {
                    "path": "Roadmap/Roadmap.base",
                    "view": "学习路线",
                    "expected_paths": ["Roadmap/01-Overview/§02-What.md"],
                },
            )

    def test_base_query_requires_exact_rows_not_substring_matches(self) -> None:
        cli = mock.Mock()
        cli.text.return_value = "Roadmap/01-Overview/§01-Start.md.backup"
        with self.assertRaisesRegex(roadmap_cli.ContractError, "missing expected paths"):
            roadmap_cli.base_query(
                cli,
                {
                    "path": "Roadmap/Roadmap.base",
                    "view": "学习路线",
                    "expected_paths": ["Roadmap/01-Overview/§01-Start.md"],
                },
            )

    def test_exact_base_query_rejects_unplanned_extra_rows(self) -> None:
        cli = mock.Mock()
        cli.text.return_value = (
            "Roadmap/01-Overview/§01-Start.md\n"
            "Roadmap/01-Overview/§02-What.md\n"
            "Roadmap/99-Unplanned.md"
        )
        with self.assertRaisesRegex(roadmap_cli.ContractError, "unexpected paths"):
            roadmap_cli.base_query(
                cli,
                {
                    "path": "Roadmap/Roadmap.base",
                    "view": "学习路线",
                    "expected_paths": [
                        "Roadmap/01-Overview/§01-Start.md",
                        "Roadmap/01-Overview/§02-What.md",
                    ],
                },
                exact=True,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = (
    REPO_ROOT / "skills" / "build-readme" / "scripts" / "validate_readme.py"
)

VALID_README = """
<div align="center">

# 𝓑𝓾𝓲𝓵𝓭 𝓕𝓵𝓸𝔀

<p align="center">从想法到可验证交付 · 𝑭𝒓𝒐𝒎 𝑰𝒅𝒆𝒂 𝒕𝒐 𝑽𝒆𝒓𝒊𝒇𝒊𝒂𝒃𝒍𝒆 𝑫𝒆𝒍𝒊𝒗𝒆𝒓𝒚</p>

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](https://opensource.org/license/mit)

</div>

<a id="overview"></a>
<h2 align="center">𝑶𝒗𝒆𝒓𝒗𝒊𝒆𝒘 · 简介</h2>

<p>_Build Flow_ 用于把项目事实整理成可执行文档。</p>

- 先读取仓库事实。
- 再生成可验证的 _README_。

<a id="workflow"></a>
<h2 align="center">𝑾𝒐𝒓𝒌𝒇𝒍𝒐𝒘 · 流程</h2>

```mermaid
flowchart LR
    A[Research] --> B[Preview]
    B --> C[Confirm]
    C --> D[Write]
    D --> E[Validate]
```
"""


class ValidateReadmeTests(unittest.TestCase):
    def write_readme(self, root: Path, text: str = VALID_README) -> Path:
        path = root / "README.md"
        path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
        return path

    def run_validator(
        self, path: Path, *extra: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(path), "--strict", *extra],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_valid_readme_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_validator(self.write_readme(Path(temp)))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS", result.stdout)

    def test_shipped_example_passes(self) -> None:
        example = (
            REPO_ROOT
            / "skills"
            / "build-readme"
            / "examples"
            / "readme.example.md"
        )
        example_text = example.read_text(encoding="utf-8")
        self.assertIn("# 𝓑𝓾𝓲𝓵𝓭 𝓕𝓵𝓸𝔀", example_text)
        self.assertIn(
            "𝑭𝒓𝒐𝒎 𝑹𝒆𝒑𝒐𝒔𝒊𝒕𝒐𝒓𝒚 𝑭𝒂𝒄𝒕𝒔 𝒕𝒐 "
            "𝑽𝒆𝒓𝒊𝒇𝒊𝒂𝒃𝒍𝒆 𝑫𝒐𝒄𝒖𝒎𝒆𝒏𝒕𝒂𝒕𝒊𝒐𝒏",
            example_text,
        )
        for heading in (
            "𝑶𝒗𝒆𝒓𝒗𝒊𝒆𝒘",
            "𝑾𝒐𝒓𝒌𝒇𝒍𝒐𝒘",
            "𝑸𝒖𝒊𝒄𝒌 𝑺𝒕𝒂𝒓𝒕",
            "𝑬𝒗𝒊𝒅𝒆𝒏𝒄𝒆",
        ):
            self.assertIn(heading, example_text)
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_validator(
                self.write_readme(Path(temp), example_text)
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_plain_title_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp), VALID_README.replace("𝓑𝓾𝓲𝓵𝓭 𝓕𝓵𝓸𝔀", "Build Flow")
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("TITLE_SCRIPT", result.stdout)

    def test_wrong_script_title_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp),
                VALID_README.replace("𝓑𝓾𝓲𝓵𝓭 𝓕𝓵𝓸𝔀", "𝒷𝓊𝒾𝒻𝒹 𝒡𝓁𝑜𝓊"),
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("TITLE_SCRIPT", result.stdout)

    def test_markdown_bold_italic_tagline_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp),
                VALID_README.replace(
                    '<p align="center">从想法到可验证交付 · 𝑭𝒓𝒐𝒎 𝑰𝒅𝒆𝒂 𝒕𝒐 𝑽𝒆𝒓𝒊𝒇𝒊𝒂𝒃𝒍𝒆 𝑫𝒆𝒍𝒊𝒗𝒆𝒓𝒚</p>',
                    '***从想法到可验证交付***',
                ),
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("TAGLINE_STYLE", result.stdout)

    def test_wrong_tagline_math_style_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp),
                VALID_README.replace(
                    "𝑭𝒓𝒐𝒎 𝑰𝒅𝒆𝒂 𝒕𝒐 𝑽𝒆𝒓𝒊𝒇𝒊𝒂𝒃𝒍𝒆 𝑫𝒆𝒍𝒊𝒗𝒆𝒓𝒚",
                    "𝐹𝓇𝑜𝓂 𝐼𝒹𝑒𝒶 𝓉𝑜 𝒱𝑒𝓇𝒾𝒻𝒾𝒶𝒷𝓁𝑒 𝒟𝑒𝓁𝒾𝓋𝑒𝓇𝓍",
                ),
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("TAGLINE_DECORATION", result.stdout)

    def test_markdown_section_heading_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp),
                VALID_README.replace(
                    '<h2 align="center">𝑶𝒗𝒆𝒓𝒗𝒊𝒆𝒘 · 简介</h2>',
                    "## 简介",
                ),
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("SECTION_HEADING_STYLE", result.stdout)

    def test_wrong_heading_math_style_fails_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp),
                VALID_README.replace("𝑶𝒗𝒆𝒓𝒗𝒊𝒆𝒘", "𝒪𝓋𝑒𝓇𝓋𝒾𝑒𝓌"),
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("SECTION_DECORATION", result.stdout)

    def test_plain_english_body_paragraph_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp), VALID_README + "\n<p>This paragraph is not italic.</p>\n"
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("ENGLISH_ITALIC", result.stdout)

    def test_html_italic_fails(self) -> None:
        for tag in ("i", "em"):
            with self.subTest(tag=tag), tempfile.TemporaryDirectory() as temp:
                path = self.write_readme(
                    Path(temp), VALID_README + f"\n<p><{tag}>中文</{tag}></p>\n"
                )
                result = self.run_validator(path)
                self.assertEqual(result.returncode, 1)
                self.assertIn("HTML_ITALIC_FORBIDDEN", result.stdout)

    def test_chinese_markdown_italic_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(Path(temp), VALID_README + "\n<p>_中文说明_</p>\n")
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("CHINESE_ITALIC_FORBIDDEN", result.stdout)

    def test_all_bold_syntaxes_fail(self) -> None:
        variants = ("__Bold text__", "<strong>Bold text</strong>", "<b>Bold text</b>")
        for variant in variants:
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temp:
                path = self.write_readme(Path(temp), VALID_README + f"\n{variant}\n")
                result = self.run_validator(path)
                self.assertEqual(result.returncode, 1)
                self.assertIn("BODY_BOLD", result.stdout)

    def test_malformed_html_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp), VALID_README + "\n<p><i>Broken paragraph</p>\n"
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("HTML_TAG_MISMATCH", result.stdout)

    def test_literal_span_artifact_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(Path(temp), VALID_README + "\n`span`\n")
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("MARKUP_ARTIFACT", result.stdout)

    def test_duplicate_anchor_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp), VALID_README + '\n<a id="overview"></a>\n'
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("ANCHOR_DUPLICATE", result.stdout)

    def test_heading_without_anchor_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp), VALID_README.replace('<a id="overview"></a>\n', "", 1)
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("SECTION_ANCHOR_REQUIRED", result.stdout)

    def test_unlabeled_code_fence_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp), VALID_README.replace("```mermaid", "```", 1)
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("FENCE_LANGUAGE_REQUIRED", result.stdout)

    def test_missing_local_image_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp), VALID_README + "\n![Architecture](assets/missing.svg)\n"
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("LOCAL_REF_MISSING", result.stdout)

    def test_invalid_svg_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asset = root / "assets" / "broken.svg"
            asset.parent.mkdir()
            asset.write_text("<svg><broken>", encoding="utf-8")
            path = self.write_readme(
                root, VALID_README + "\n![Architecture](assets/broken.svg)\n"
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("SVG_INVALID", result.stdout)

    def test_unsafe_svg_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asset = root / "assets" / "unsafe.svg"
            asset.parent.mkdir()
            asset.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<script>alert(1)</script>'
                '<image href="https://tracker.example/pixel"/>'
                "</svg>",
                encoding="utf-8",
            )
            path = self.write_readme(
                root, VALID_README + "\n![Architecture](assets/unsafe.svg)\n"
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("SVG_UNSAFE", result.stdout)

    def test_unresolved_placeholder_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(Path(temp), VALID_README + "\n<p><i>TBD</i></p>\n")
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("UNRESOLVED_CONTENT", result.stdout)

    def test_image_without_alt_text_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp),
                VALID_README + "\n![](https://example.com/architecture.svg)\n",
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("IMAGE_ALT_REQUIRED", result.stdout)

    def test_remote_image_hotlink_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp),
                VALID_README + "\n![Screenshot](https://example.com/screenshot.png)\n",
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("REMOTE_IMAGE_HOTLINK", result.stdout)

    def test_body_bold_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp), VALID_README + "\n<p>**Do not use bold.**</p>\n"
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("BODY_BOLD", result.stdout)

    def test_strict_json_reports_warning_as_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_readme(
                Path(temp), VALID_README.replace("𝑶𝒗𝒆𝒓𝒗𝒊𝒆𝒘", "Overview")
            )
            result = self.run_validator(path, "--json")
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(report["error_count"], 0)
            self.assertEqual(report["warning_count"], 1)
            self.assertEqual(report["status"], "fail")

    def test_repository_readme_passes(self) -> None:
        result = self.run_validator(REPO_ROOT / "README.md")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "skills" / "build-prd" / "scripts" / "validate_prd.py"

VALID_PRD = """
# PRD需求文档

- 文档状态：已确认
- 更新时间：2026-08-10

## 产品定位与范围

### 产品作用

帮助个人把零散事项整理为清晰、可执行的任务。

### 目标用户与角色

- 普通用户：创建、查看和完成自己的任务。

### 范围边界

- 包含任务创建、任务列表和完成反馈。
- 不包含团队协作和收费能力。

### 产品成功标准

- 用户能在一分钟内完成首次任务创建。

## 产品现状与目标

### 已实现现状

当前产品已提供任务列表。

### 目标需求

补全任务创建和完成反馈体验。

## 功能地图与用户旅程

用户进入任务页，创建任务，在列表中查看并将其标记为完成。

## 全局交互与文案原则

操作反馈使用简短、明确且可执行的中文文案。

## 功能详细设计

### F-001 创建任务

#### 作用与目标

让用户记录一项需要完成的事项。

#### 适用角色、入口与前置条件

- 角色：普通用户。
- 入口：任务页“新建任务”按钮。
- 前置条件：用户已进入任务页。

#### 用户预输入

| 字段或内容 | 提供者 | 必填 | 格式与范围 | 默认值 | 校验规则 | 正确示例 | 错误示例 |
| ---------- | ------ | ---- | ---------- | ------ | -------- | -------- | -------- |
| 任务名称 | 普通用户 | 是 | 1–80 个字符 | 无 | 去除首尾空格后不能为空 | 预约牙医 | 空字符串 |

#### 交互流程

1. 用户点击“新建任务”。
2. 产品显示任务名称输入框和“创建”按钮。
3. 用户输入名称并点击“创建”。
4. 产品把新任务显示在列表顶部。

#### 状态与提示文案

| 状态 | 触发条件 | 最终文案 | 后续动作 |
| ---- | -------- | -------- | -------- |
| 输入为空 | 用户提交空内容 | “请输入任务名称” | 聚焦任务名称输入框 |
| 创建成功 | 有效任务创建完成 | “任务已创建” | 返回任务列表 |

#### 期望输出

| 输出内容 | 呈现形式 | 触发条件 | 排序或状态 | 用户后续动作 | 完整示例 |
| -------- | -------- | -------- | ---------- | ------------ | -------- |
| 新任务 | 列表项 | 创建成功 | 位于列表顶部、状态为未完成 | 标记完成或继续创建 | 预约牙医 · 未完成 |

#### 异常、边界与恢复

- 输入超过 80 个字符时显示“任务名称最多 80 个字符”，并保留已输入内容。

#### 产品质量要求

- 用户提交后 1 秒内看到成功反馈或可执行的失败反馈。

#### 设计依据

- 采用单字段快速创建方式，减少首次记录任务的操作负担。

#### 验收标准

- `F-001-AC-01` Given 用户位于任务页，When 输入“预约牙医”并点击“创建”，Then 列表顶部显示状态为“未完成”的“预约牙医”，并提示“任务已创建”。
- `F-001-AC-02` Given 任务名称为空，When 用户点击“创建”，Then 显示“请输入任务名称”并聚焦输入框。

## 跨功能产品要求

- 所有交互均可通过键盘完成，焦点顺序与视觉顺序一致。
- 错误反馈必须说明原因和下一步动作。

## 设计依据与来源

| 类型 | 名称 | 一手来源 | 访问日期 | 借鉴点 |
| ---- | ---- | -------- | -------- | ------ |
| 竞品 | Competitor One | https://competitor-one.example/product | 2026-08-10 | 快速创建入口 |
| 竞品 | Competitor Two | https://competitor-two.example/product | 2026-08-10 | 列表反馈方式 |
| 开源项目 | Open Source One | https://github.com/example/open-one | 2026-08-10 | 空状态处理 |
| 开源项目 | Open Source Two | https://github.com/example/open-two | 2026-08-10 | 输入校验体验 |
| 官方规范 | Accessibility Guide | https://standards.example/accessibility | 2026-08-10 | 键盘操作要求 |
"""


class ValidatePrdTests(unittest.TestCase):
    def write_prd(self, root: Path, text: str = VALID_PRD) -> Path:
        path = root / "docs" / "PRD需求文档.md"
        path.parent.mkdir(parents=True)
        path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
        return path

    def run_validator(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(path), "--strict"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_valid_prd_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_validator(self.write_prd(Path(temp)))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS", result.stdout)

    def test_shipped_example_passes(self) -> None:
        example = REPO_ROOT / "skills" / "build-prd" / "examples" / "prd.example.md"
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_validator(
                self.write_prd(Path(temp), example.read_text(encoding="utf-8"))
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unresolved_content_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_prd(
                Path(temp), VALID_PRD.replace("补全任务创建", "TBD：补全任务创建")
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("UNRESOLVED_CONTENT", result.stdout)

    def test_technical_section_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_prd(
                Path(temp), VALID_PRD + "\n## 技术架构\n\n使用三层架构。\n"
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("TECHNICAL_SECTION", result.stdout)

    def test_duplicate_feature_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            duplicate = VALID_PRD.replace(
                "## 跨功能产品要求",
                "### F-001 查看任务\n\n重复编号。\n\n## 跨功能产品要求",
            )
            result = self.run_validator(self.write_prd(Path(temp), duplicate))
            self.assertEqual(result.returncode, 1)
            self.assertIn("FEATURE_ID_DUPLICATE", result.stdout)

    def test_feature_without_acceptance_criteria_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            without_acceptance = VALID_PRD.replace(
                "- `F-001-AC-01` Given 用户位于任务页，When 输入“预约牙医”并点击“创建”，Then 列表顶部显示状态为“未完成”的“预约牙医”，并提示“任务已创建”。\n"
                "- `F-001-AC-02` Given 任务名称为空，When 用户点击“创建”，Then 显示“请输入任务名称”并聚焦输入框。\n",
                "尚未编写验收标准。\n",
            )
            result = self.run_validator(self.write_prd(Path(temp), without_acceptance))
            self.assertEqual(result.returncode, 1)
            self.assertIn("AC_REQUIRED", result.stdout)

    def test_insufficient_research_coverage_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            insufficient = VALID_PRD.replace(
                "| 竞品 | Competitor Two | https://competitor-two.example/product | 2026-08-10 | 列表反馈方式 |\n",
                "",
            )
            result = self.run_validator(self.write_prd(Path(temp), insufficient))
            self.assertEqual(result.returncode, 1)
            self.assertIn("RESEARCH_COVERAGE", result.stdout)

    def test_wrong_output_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "PRD.md"
            path.write_text(textwrap.dedent(VALID_PRD).lstrip(), encoding="utf-8")
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("OUTPUT_PATH", result.stdout)


if __name__ == "__main__":
    unittest.main()

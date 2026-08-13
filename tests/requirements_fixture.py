from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT_PRD = """# PRD需求文档

- 文档状态：已确认
- 需求包 ID：task-product
- 需求包版本：1.0.0
- 需求包类型：完整
- 更新时间：2026-08-13

## 产品定位与范围

帮助个人把零散事项整理为清晰、可执行的任务。

## 产品现状与目标

当前产品已有任务列表，目标是补全任务创建和完成反馈。

## 功能域地图

| 功能域 ID | 名称 | 作用 | 依赖 | 需求文件 | 行为样例 |
| --- | --- | --- | --- | --- | --- |
| task-management | 任务管理 | 创建和完成任务 | 无 | `功能域/任务管理.md` | `行为样例/任务管理.yaml` |

## 跨域用户旅程

用户进入任务页，创建任务，在列表中查看并将其标记为完成。

## 全局输入与输出约定

用户输入保留原始语义；固定文件路径和字段必须完全一致，解释性文字只要求语义达标。

## 全局交互与文案原则

操作反馈使用简短、明确且可执行的中文文案。

## 跨功能产品要求

所有交互均可通过键盘完成，错误反馈必须说明原因和下一步动作。

## 设计依据与来源

| 类型 | 名称 | 一手来源 | 访问日期 | 借鉴点 |
| --- | --- | --- | --- | --- |
| 竞品 | Competitor One | https://competitor-one.example/product | 2026-08-13 | 快速创建入口 |
| 竞品 | Competitor Two | https://competitor-two.example/product | 2026-08-13 | 列表反馈方式 |
| 开源项目 | Open Source One | https://github.com/example/open-one | 2026-08-13 | 空状态处理 |
| 开源项目 | Open Source Two | https://github.com/example/open-two | 2026-08-13 | 输入校验体验 |
| 官方规范 | Accessibility Guide | https://standards.example/accessibility | 2026-08-13 | 键盘操作要求 |
"""


DOMAIN_PRD = """# 功能域：任务管理

- 文档状态：已确认
- 功能域 ID：task-management
- 依赖功能域：无

## 功能域范围

包含任务创建、任务列表和完成反馈，不包含团队协作和收费能力。

## 用户能力与旅程

普通用户从任务页进入创建流程，提交后查看任务状态并继续操作。

## 功能详细设计

### F-001 创建任务

#### 作用与目标

让用户记录一项需要完成的事项。

#### 适用角色、入口与前置条件

普通用户从任务页“新建任务”按钮进入，前置条件是已经打开任务页。

#### 用户输入契约

| 输入项 | 提供者 | 必填 | 格式与范围 | 默认值 | 校验规则 | 正确示例 | 错误示例 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 任务名称 | 普通用户 | 是 | 1–80 个字符 | 无 | 去除首尾空格后不能为空 | 预约牙医 | 空字符串 |

#### 用户交互与追问

1. 用户点击“新建任务”。
2. 产品显示输入框；信息不足时只追问缺失的任务名称。
3. 用户提交后，产品显示结果或可恢复的失败反馈。

#### 状态与提示文案

| 状态 | 触发条件 | 最终文案 | 后续动作 |
| --- | --- | --- | --- |
| 输入为空 | 用户提交空内容 | “请输入任务名称” | 聚焦任务名称输入框 |
| 创建成功 | 有效任务创建完成 | “任务已创建” | 返回任务列表 |

#### 输出契约

| 输出内容 | 呈现形式 | 触发条件 | 固定结构 | 语义要求 | 运行时可变内容 | 完整示例 |
| --- | --- | --- | --- | --- | --- | --- |
| 新任务 | 列表项 | 创建成功 | 任务名称和状态字段 | 明确说明创建成功 | 创建时间和内部 ID | 预约牙医 · 未完成 |

#### 对外契约

用户依赖任务名称、状态和错误文案；内部框架、数据库与模块划分不属于需求。

#### 异常、边界与恢复

输入为空或超过 80 个字符时保留输入，给出具体原因并允许修改后重试。

#### 产品质量要求

用户提交后 1 秒内看到成功反馈或可执行的失败反馈。

#### 设计依据

采用单字段快速创建方式，减少首次记录任务的操作负担。

#### 行为样例

- `SAMPLE-TASK-001`：典型正确输入。
- `SAMPLE-TASK-002`：信息不足并追问。
- `SAMPLE-TASK-003`：错误输入。
- `SAMPLE-TASK-004`：边界输入。

#### 验收标准

- `F-001-AC-01` Given 用户位于任务页，When 输入“预约牙医”并点击“创建”，Then 列表顶部显示状态为“未完成”的“预约牙医”，并提示“任务已创建”。
- `F-001-AC-02` Given 任务名称为空，When 用户点击“创建”，Then 显示“请输入任务名称”并聚焦输入框。
"""


def _sample(sample_id: str, kind: str, user_input: str) -> dict[str, Any]:
    return {
        "id": sample_id,
        "feature_id": "F-001",
        "kind": kind,
        "user_input": user_input,
        "starting_state": ["用户已进入任务页"],
        "expected_behavior": ["按照输入契约处理", "返回用户可理解的结果"],
        "expected_output": "显示任务结果或可执行的恢复提示。",
        "output_contract": {
            "exact": ["固定字段名、状态值和最终提示文案"],
            "semantic": ["解释必须覆盖结果、原因和下一步动作"],
            "runtime": ["运行时生成的 ID、日期和耗时允许变化"],
        },
        "assertions": ["结果与 F-001 验收标准一致"],
        "forbidden": ["不得把内部实现或未验证状态描述为用户结果"],
        "sensitive_data": "none",
    }


DEFAULT_SAMPLES = [
    _sample("SAMPLE-TASK-001", "normal", "创建任务：预约牙医"),
    _sample("SAMPLE-TASK-002", "clarification", "帮我创建一个任务"),
    _sample("SAMPLE-TASK-003", "invalid", "创建一个空名称任务"),
    _sample("SAMPLE-TASK-004", "boundary", "创建一个正好 80 个字符的任务"),
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_requirement_package(
    root: Path,
    *,
    package_type: str = "full",
    status: str = "confirmed",
    dependency: str | None = None,
    external_dependencies: list[dict[str, str]] | None = None,
    stage: dict[str, str] | None = None,
    samples: list[dict[str, Any]] | None = None,
) -> Path:
    package = root / "docs" / "产品需求"
    requirement = package / "功能域" / "任务管理.md"
    behavior = package / "行为样例" / "任务管理.yaml"
    index = package / "行为样例" / "产品行为样例集.yaml"
    prd = package / "PRD需求文档.md"

    package.mkdir(parents=True, exist_ok=True)
    prd_text = ROOT_PRD.replace(
        "- 需求包类型：完整",
        f"- 需求包类型：{'完整' if package_type == 'full' else '阶段'}",
    )
    prd.write_text(prd_text, encoding="utf-8")
    requirement.parent.mkdir(parents=True, exist_ok=True)
    requirement.write_text(DOMAIN_PRD, encoding="utf-8")
    write_json_yaml(
        behavior,
        {
            "schema_version": "1.0",
            "domain_id": "task-management",
            "samples": samples if samples is not None else DEFAULT_SAMPLES,
        },
    )
    write_json_yaml(
        index,
        {
            "schema_version": "1.0",
            "package_id": "task-product",
            "domains": [
                {
                    "id": "task-management",
                    "file": "任务管理.yaml",
                    "sample_ids": [item["id"] for item in (samples or DEFAULT_SAMPLES)],
                }
            ],
        },
    )

    dependencies = [dependency] if dependency else []
    tracked = [
        Path("PRD需求文档.md"),
        Path("功能域/任务管理.md"),
        Path("行为样例/产品行为样例集.yaml"),
        Path("行为样例/任务管理.yaml"),
    ]
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "package_id": "task-product",
        "package_version": "1.0.0",
        "status": status,
        "package_type": package_type,
        "generated_at": "2026-08-13",
        "source": {"project": str(root), "revision": "fixture"},
        "domains": [
            {
                "id": "task-management",
                "name": "任务管理",
                "status": "confirmed",
                "requirements": "功能域/任务管理.md",
                "examples": "行为样例/任务管理.yaml",
                "dependencies": dependencies,
            }
        ],
        "external_dependencies": external_dependencies or [],
        "files": [
            {"path": path.as_posix(), "sha256": _sha256(package / path)}
            for path in tracked
        ],
    }
    if stage is not None:
        manifest["stage"] = stage
    write_json_yaml(package / "需求包清单.yaml", manifest)
    return package


def refresh_manifest_hashes(package: Path) -> None:
    manifest_path = package / "需求包清单.yaml"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["files"]:
        item["sha256"] = _sha256(package / item["path"])
    write_json_yaml(manifest_path, manifest)

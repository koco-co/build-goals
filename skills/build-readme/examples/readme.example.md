# Build Flow

Build Flow 从仓库事实生成准确、可验证的项目说明。

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](https://opensource.org/license/mit)

> 本文件只示范内容层级和标准 GitHub Markdown；示例事实不可直接复制到其他项目。

## 功能

- 从代码、配置、测试和现有文档提取已实现能力。
- 区分已验证结论与当前环境未验证的结论。
- 只在有助于理解时使用表格、图表或图片。

## 工作流

```mermaid
flowchart LR
    A[核对事实] --> B[确定内容]
    B --> C[编写 README]
    C --> D[验证]
```

## 快速开始

```bash
python3 path/to/validate_readme.py README.md --strict
```

## 验证状态

| 状态 | 含义 |
| --- | --- |
| 已验证 | 有实际命令结果或可定位证据 |
| 未验证 | 当前环境未执行，不能写成已通过 |

## 许可证

示例项目使用 MIT License。真实 README 必须以目标仓库中的许可证文件为依据。

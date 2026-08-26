---
name: build-readme
description: 基于真实项目事实创建或更新 README；文件缺失或与事实不符时使用，不用于普通文档润色、代码开发或发布。
compatibility: 需要 Python 3.9+ 运行内置校验脚本。
metadata:
  author: koco-co
  version: "2.2.0"
---

# Outcome

把项目真实能力整理为准确、可维护且通过验证的 GitHub 风格 README。

## Routing

- 没有根目录 `README.md` 时创建；已有时保留事实并更新。
- 已有伴随 README 时一并列出并在确认后同步；不存在时不创建。
- 仅审查或预览时保持只读；普通文档、代码、发布和仓库主页配置不属于本 Skill。
- 由 `health-check` 受控调用时，审查阶段保持只读；上层取得修复确认后再修复。

## Steps

1. 读取 `workflows/§01-research.md`，核对入口、安装、使用、验证、限制和资源。
2. 读取 `workflows/§02-preview.md` 与 `templates/readme-preview.template.md`，展示内容、视觉组件、同步文件和外部动作，等待确认。
3. 确认后读取 `workflows/§03-authoring.md`、`rules/github-style.md` 和 `rules/evidence-and-content.md`，编写 README。
4. 读取 `workflows/§04-validation.md` 与 `checklists/semantic-acceptance.md`，运行校验器并记录渲染或远程检查状态。
5. 读取 `workflows/§05-delivery.md`，报告变更、证据和未验证项。

## Rules

- 只写有仓库证据的能力、命令、版本、兼容性、许可证和链接；保留未提交修改。
- 翻译 README、图片、远程渲染、安装依赖、提交、推送和发布都需明确授权。

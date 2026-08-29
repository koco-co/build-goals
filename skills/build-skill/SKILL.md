---
name: build-skill
description: 创建、升级或重构通用或项目级 Agent Skill；涉及 Skill 设计、实现或审查时使用，不用于 Plugin 打包、普通提示词润色或一般编码。
compatibility: 需要访问互联网；内置静态校验脚本需要 Python 3.9+。
metadata:
  author: koco-co
  version: "2.3.0"
---

# Outcome

把明确的 Skill 需求转化为结构最小、行为可靠、可验证并适配目标平台的实现。

## Routing

- 新建通用 Skill、创建项目级 Skill 或升级已有 Skill 时进入对应分支。
- 由 `health-check` 调用时，审查阶段保持只读；上层取得修复确认后再修复。
- 由 `build-plugin` 统筹并调用时，遵循它规定的任务范围、确认要求和恢复条件。
- Plugin 打包、安装、分发、普通文档或提示词润色不属于本 Skill。

## Steps

1. 读取 `workflows/§01-research.md`，查明需求、目标项目、现状、依赖和平台契约。
2. 读取 `workflows/§02-clarification.md`，只确认会改变结构、行为、权限或验收的决策。
3. 读取 `workflows/§03-design.md`、`rules/architecture.md`、`rules/frontmatter.md`、`rules/quality-standard.md` 和 `rules/platform-compatibility.md`，展示最小设计并等待实施确认；确认前不写入目标文件。
4. 确认后读取 `workflows/§04-implementation.md`，只实现确认范围，复用确定性工具并保持单一规范源。
5. 读取 `workflows/§05-validation.md`，按变更选择静态、内容、文案、独立 Reviewer、场景和平台验证。
6. 读取 `workflows/§06-delivery.md`，报告变更、验证状态、未验证项和恢复条件。

## Rules

- `SKILL.md` 只保留目标、路由/退出、执行顺序和必要红线；详细规则、模板、示例和校验由附属文件承载。
- 每条新增内容都必须有用户需求、仓库事实、平台契约、可复现缺陷或明确安全要求依据；重复或无法说明用途就删除。
- 不自动 commit、push、发布、安装或更新 Plugin；保留用户未提交修改。

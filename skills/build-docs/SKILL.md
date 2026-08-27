---
name: build-docs
description: 为大型代码项目建立、提取、更新开发文档或复核外部审查报告；需要梳理跨模块、分阶段文档，或判断针对已有文档的审查意见并在确认后修订时使用，不用于小问题、小需求、单篇润色、README 或 AGENTS.md 整体重构及代码开发。
disable-model-invocation: true
metadata:
  author: koco-co
  version: "1.2.0"
---

# Outcome

建立和维护与项目事实、已确认设计一致的文档体系，依据证据取舍外部审查意见。

## Routing

- 从零建立：项目尚无实现，依据需求和确认的设计编写文档。
- 已有项目提取：已有代码但文档缺失或不完整，从实现及相关资料提取事实并补齐文档。
- 持续更新：已有文档体系，依据开发进展或新决策更新受影响内容。
- 审查报告复核：用户提供针对已有文档的外部审查报告，逐项核查、说明取舍，确认后修订并提交。
- 小问题、小需求、局部修复、单篇润色和产品代码开发直接退出；README 与 AGENTS.md 整体重构不属于本 Skill。

## Steps

1. 审查报告复核直接读取 `workflows/§05-review.md`，完成该分支后结束；其余三个分支按以下步骤执行。
2. 读取 `workflows/§01-research.md`，确定工作流、项目事实和未决事项。
3. 读取 `rules/documents.md` 与 `workflows/§02-plan.md`，确认文档职责、实际路径和编写批次。
4. 读取 `workflows/§03-authoring.md`，按批次读取职责表中对应模板，展示内容并在确认后写入，同时维护接续入口。
5. 读取 `workflows/§04-validation.md` 与 `checklists/acceptance.md`，检查内容、引用和事实依据，报告结果与未验证项。

## Guardrails

- 不修改产品代码、机器 Schema、构建配置或客户端配置；不执行推送、安装、部署。
- 仅审查报告复核分支在用户明确确认修改与 commit 后允许提交；其他分支不提交。
- 保留项目已有结构与未提交工作；仅写入已确认的文档改动。

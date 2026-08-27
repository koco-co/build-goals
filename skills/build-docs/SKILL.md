---
name: build-docs
description: 为大型代码项目从零建立、从已有项目提取或持续更新开发文档；需要梳理跨模块、分阶段开发的需求、架构与接续信息时使用，不用于小问题、小需求、单篇文档润色、README 或 AGENTS.md 整体重构及代码开发。
disable-model-invocation: true
metadata:
  author: koco-co
  version: "1.1.0"
---

# Outcome

建立与项目事实和已确认设计一致、可供多次开发会话使用的文档体系。

## Routing

- 从零建立：项目尚无实现，依据需求和确认的设计编写文档。
- 已有项目提取：已有代码但文档缺失或不完整，从实现及相关资料提取事实并补齐文档。
- 持续更新：已有文档体系，依据开发进展或新决策更新受影响内容。
- 小问题、小需求、局部修复、单篇润色和产品代码开发直接退出；README 与 AGENTS.md 整体重构不属于本 Skill。

## Steps

1. 读取 `workflows/§01-research.md`，确定工作流、项目事实和未决事项。
2. 读取 `rules/documents.md` 与 `workflows/§02-plan.md`，确认文档职责、实际路径和编写批次。
3. 读取 `workflows/§03-authoring.md`，按批次读取职责表中对应模板，展示内容并在确认后写入，同时维护接续入口。
4. 读取 `workflows/§04-validation.md` 与 `checklists/acceptance.md`，检查内容、引用和事实依据，报告结果与未验证项。

## Guardrails

- 不修改产品代码、机器 Schema、构建配置或客户端配置；不执行提交、推送、安装、部署。
- 保留项目已有结构与未提交工作；文档写入以已确认的批次为范围。

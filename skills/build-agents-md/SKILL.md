---
name: build-agents-md
description: 初始化或整体重构项目的 AGENTS.md，并以 CLAUDE.md 相对符号链接保持 Claude Code 与 Codex 单一来源；先研究仓库并给出完整替换预览，确认后写入和验证。
compatibility: 当前适配 Claude Code 与 Codex；运行内置校验器需要 Python 3.9+。
disable-model-invocation: true
metadata:
  author: koco-co
  version: "1.0.0"
---

# Outcome

为目标仓库建立简洁、项目特有、可执行且可验证的 Agent 指令入口：以 `AGENTS.md` 为唯一正文，以同目录 `CLAUDE.md` 相对符号链接兼容 Claude Code；仅在确有独立上下文时增加嵌套指令。

## Routing

- 根目录没有 `AGENTS.md` 时，执行初始化分支。
- 已有 `AGENTS.md` 时，允许整体重构；必须先展示完整替换预览，不能默认保留原有章节结构。
- Monorepo 仅在子目录存在不同技术栈、命令、边界或硬性规则时创建嵌套 `AGENTS.md`。
- 用户只要求审查、建议或预览时，停在只读阶段。
- 普通 README、项目文档、通用 Agent 行为规范、测试框架或 CI 建设不属于本 Skill。

## Steps

1. 研究目标仓库
   - 完整读取 `workflows/§01-research.md` 和 `rules/content-admission.md`。
   - 查清仓库结构、入口、真实命令、现有指令、文档、CI 与版本控制状态。
   - 完成条件：每项拟写内容都有项目证据，且嵌套边界已有理由。

2. 提交完整预览
   - 完整读取 `workflows/§02-preview.md` 和 `templates/replacement-preview.template.md`。
   - 列出全部新增、替换、删除与链接操作，并逐文件展示完整拟写正文。
   - 完成条件：用户明确确认预览；不得在用户确认预览前写入。

3. 写入单一来源指令
   - 确认后完整读取 `workflows/§03-authoring.md`、`rules/platform-and-scope.md` 和 `templates/agents-md.template.md`。
   - 需要判断内容粒度时，只读取最接近目标项目形态的 `examples/` 示例。
   - 完成条件：确认范围内的 `AGENTS.md` 与 `CLAUDE.md` 已落地，未扩张到其他项目文件。

4. 验证
   - 完整读取 `workflows/§04-validation.md` 和 `checklists/semantic-acceptance.md`。
   - 运行 `scripts/validate_agents_md.py`；按风险补充真实、可复现的项目命令验证。
   - 完成条件：结构检查、语义检查、命令证据与未验证项分别记录。

5. 交付
   - 完整读取 `workflows/§05-delivery.md`。
   - 完成条件：用户能定位变更、复现检查，并决定是否执行适用的版本控制或本地 Plugin 更新动作。

## Delivery

- 说明采用的根目录与嵌套边界，以及每个文件为何存在。
- 列出新增、替换、删除、链接和明确未处理的文件。
- 汇报实际运行的命令、结果、失败修复与“来源已确认、运行未验证”的命令。
- 区分机械校验、项目行为验证和真实客户端加载验证，不扩大结论。
- 实现与验证结束后，只询问一次是否执行适用动作：commit、push、更新本地 Claude Code Plugin、更新本地 Codex Plugin；未获确认不得执行，部分授权只执行获准部分。

## Guardrails

- `AGENTS.md` 只接纳项目特有信息，不复制通用 Agent 操作守则或长篇教程。
- 不以固定九章、固定行数或博客模板替代对仓库事实的判断；长度阈值只能是提醒。
- 不静默丢弃现有 `CLAUDE.md` 中的 Claude 专有规则；必须泛化、报告移除理由，或作为阻塞项交给用户决定。
- 不得创建项目级 `docs/`、lint、CI、测试 harness 或其他辅助体系来支撑本 Skill。
- 保留用户已有未提交修改；完整替换也必须限于预览中明确列出的文件和内容。
- 不运行需要凭据、外部写入、发布或高成本环境初始化的命令，除非用户另行授权。
- 不自动 commit、push、安装或更新本地 Plugin。

## References

- 开始时完整读取 `workflows/§01-research.md` 和 `rules/content-admission.md`。
- 预览前完整读取 `workflows/§02-preview.md` 和 `templates/replacement-preview.template.md`。
- 用户确认后完整读取 `workflows/§03-authoring.md`、`rules/platform-and-scope.md` 与 `templates/agents-md.template.md`。
- 示例按项目形态选读：`examples/library-or-cli.example.md`、`examples/application.example.md` 或 `examples/monorepo.example.md`。
- 写入后完整读取 `workflows/§04-validation.md` 和 `checklists/semantic-acceptance.md`，并执行 `scripts/validate_agents_md.py`。
- 交付时完整读取 `workflows/§05-delivery.md`。

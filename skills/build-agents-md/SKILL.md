---
name: build-agents-md
description: 初始化或重构项目的 AGENTS.md，并通过只包含 @AGENTS.md 的普通 CLAUDE.md 文件供 Claude Code 与 Codex 共用；项目指令缺失、失效或与事实不符时使用，不用于普通文档、CI 或测试建设。
license: MIT
compatibility: 需要 Python 3.9+ 运行内置校验脚本。
metadata:
  author: koco-co
  version: "4.0.0"
---

# Outcome

为项目建立简洁、具体、可执行且可验证的 Agent 开发指南。

## Routing

- 根目录缺少 `AGENTS.md` 时初始化；已有时先审查再整体重构。
- Monorepo 只有子目录确有不同约定时才创建嵌套指南。
- 用户明确要求初始化、重构或修复项目指令且范围可由仓库事实确定时直接实施；仅审查或预览时保持只读。
- 普通文档、通用 Agent 规范、测试框架和 CI 建设直接退出；由 `audit-agent-setup` 调用时遵循上层授权范围。

## Steps

1. 读取 `workflows/§01-research.md` 和 `rules/content-admission.md`，只用仓库事实确定内容和文件范围。
2. 读取 `workflows/§02-preview.md`，形成完整正文及文件操作；只有用户要求预览，或存在会改变文件范围、规则语义或删除内容的未决选择时才等待确认。
3. 授权范围明确后读取 `workflows/§03-authoring.md`、`rules/platform-and-scope.md` 和 `templates/agents-md.template.md`，写入 `AGENTS.md` 与只包含一行 `@AGENTS.md` 的普通 `CLAUDE.md` 文件。
4. 读取 `workflows/§04-validation.md` 与 `checklists/semantic-acceptance.md`，运行校验器及适用项目命令。
5. 读取 `workflows/§05-delivery.md`，报告变更、证据、未验证项和恢复条件。

## Rules

- `AGENTS.md` 只保留项目特有约定；保留用户未提交修改，不创建额外文档、CI 或测试体系。
- 提交、推送、安装和 Plugin 更新不属于默认步骤，必须单独授权。

---
name: handoff
description: 由用户显式调用的会话交接工作流。用于将当前对话压缩为供下一位 agent 交接的精简文档。
argument-hint: "下一次会话将用于什么？"
compatibility: 当前适配 Claude Code 与 Codex。
disable-model-invocation: true
metadata:
  author: koco-co
  version: "1.0.0"
---

# Outcome

将当前对话上下文整理为精简的交接文档，帮助新 agent 在下一次会话中继续工作。

## Routing

- 用户明确调用 `handoff` 时进入本工作流。
- 用户传入的参数描述下一次会话的用途，并用于定制 交接文档。
- 普通总结、文档编写或实现请求不得自动触发本 Skill。

## Steps

1. 总结当前会话上下文，使新 agent 能够接续工作。
2. 将交接文档保存到用户操作系统的临时目录，不得保存到当前工作区。
3. 在文档中加入名为 `suggested skills` 的章节，推荐下一位 agent 应调用的 Skills。
4. 如果用户传入参数，将其视为下一次会话的用途，并据此调整文档重点。

## Delivery

- 交付一个位于操作系统临时目录的交接文档。
- 文档必须包含 `suggested skills` 章节。
- 文档内容应足够让新 agent 在下一次会话中恢复上下文并继续工作。

## Guardrails

- 不得将交接文档写入当前工作区。
- 不得忽略用户传入的下一次会话用途参数。

## References

- 无附加文件。

# 总控编排契约

## 1. 两次全局确认

`vibe-coding` 只有两个全局决策门禁：

1. 架构方案确认：此前保持只读；确认后才能写架构文档，仍不能搭建脚手架或开发功能。
2. 整体实施路线确认：先展示功能域顺序、任务、依赖、并行、测试、提交和验收；确认后才能写实施任务文档、搭建脚手架、创建 worktree 和本地 commit。

第二次确认覆盖已展示的所有功能域。后续不逐域重复询问，除非产品范围、公开契约、持久化数据、认证授权、部署拓扑、核心工具链或整体依赖路线发生实质变化。

`health-check` 内部领域尚未决定的具体内容仍按其自身规则预览确认，例如项目指令完整正文或 README 修改预览。这不是第三个全局门禁；同一内容已经被完整等价确认时不机械重复。

## 2. 路线与权威输入

| 路线 | 旧项目读取 | 产品行为权威输入 | 架构文档族 |
| --- | --- | --- | --- |
| 新项目，只按需求实现 | 不读取 | `docs/产品需求/` | `docs/架构设计/` |
| 新项目，参考旧项目指定部分 | 只读用户授权范围 | `docs/产品需求/`；旧项目只提供证据 | `docs/架构设计/` |
| 现有项目按需求续建 | 读取当前项目相关事实 | `docs/产品需求/` 与当前事实差距 | `docs/架构设计/` |
| 现有项目架构或技术栈迁移 | 读取当前项目完整基线 | 已确认外部行为基线与迁移目标 | `docs/架构迁移/` |

路线 1–3 只接受严格校验通过的完整或正式阶段需求包。过程检查点、旧单文件 PRD 和实时来源链接都不是权威输入。

## 3. Agent 角色

各角色职责以对应角色提示文件（`prompts/*.agent.md`）中的 Role 段为权威。

| 角色 | 角色提示文件 | 写权限 |
| --- | --- | --- |
| Architecture Researcher | `prompts/architecture-researcher.agent.md` | 无 |
| Competitor Researcher | `prompts/competitor-researcher.agent.md` | 无 |
| 旧项目参考检查员 | `prompts/legacy-reference-inspector.agent.md` | 无 |
| Repository Auditor | `prompts/repository-auditor.agent.md` | 无 |
| Implementation Planner | `prompts/implementation-planner.agent.md` | 仅任务草案 |
| Feature Developer | `prompts/feature-developer.agent.md` | 仅分配 worktree |
| Test Engineer | `prompts/test-engineer.agent.md` | 分配范围内 |
| UI Reviewer | `prompts/ui-reviewer.agent.md` | 默认只读 |
| Security Reviewer | `prompts/security-reviewer.agent.md` | 默认只读 |
| Integration Manager | `prompts/integration-manager.agent.md` | 集成分支 |
| Independent Reviewer | `prompts/reviewer.agent.md` | 无 |

同一 Agent 不同时担任功能实现者和最终独立 Reviewer。

## 4. 最小上下文

所有 Agent 都只接收完成任务所需的内容。功能 Agent 的输入固定包含：

- 任务 ID、唯一目标和当前功能域；
- 全局需求、架构和实施索引中的相关条目；
- 当前功能域需求、行为样例、架构和任务；
- 当前域直接依赖的输入输出契约；
- 允许修改、只读依赖和禁止修改路径；
- 首个验证证据、正常测试数据、验证命令和完成条件；
- 当前适用的 `AGENTS.md` 路径与功能开发基线；
- 是否允许本地提交和要求的返回格式。

不要发送整个历史对话、全部旧项目、所有需求域、无关秘密或用户数据。需要额外上下文时，Agent 必须指出与当前任务的直接关系，由总控补充最小范围。

旧项目参考检查员还必须收到明确的“允许读取”和“禁止带入”列表，只能返回：

```markdown
## 已观察行为
## 用户输入
## 期望输出
## 对外契约
## 文件或命令证据
## 证据缺口
```

禁止返回旧项目目标架构建议、内部模块全景、大段代码或与授权范围无关的信息。

## 5. 返回契约

研究 Agent 返回事实、来源、发现、候选方案、推荐、风险和证据缺口。实现 Agent 返回任务、修改文件、首个验证证据、实现、命令与结果、commit、偏离和阻塞。集成 Agent 返回已集成提交、冲突、验证、任务文档更新和剩余风险。

所有结论区分实际运行证据、静态证据和推断。没有真实执行的界面、业务或外部流程不得写成已验证。

## 6. 配套 Skills

按 `rules/companion-skills.md` 处理 `shape-idea`、`health-check` 和 `handoff`。项目规范领域统一由 `health-check` 封装，不在总控计划和交付记录中展开内部 Skill。

受控调用只传最小上下文。子 Skill 不重复询问由总控管理的本地 commit，也不得自行 push、发布、部署或更新本地 Plugin。`health-check` 没有发现问题时不增加用户交互；发现问题时暂停当前阶段，报告后经用户确认直接修复并复检。出现新的产品、架构、公开契约或范围决策时返回对应全局门禁。

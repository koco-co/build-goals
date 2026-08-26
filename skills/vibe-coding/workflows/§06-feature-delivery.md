# 多 Agent 功能开发与集成

## Phase 1：构造最小上下文包

功能 Agent 的最小上下文包以 `rules/orchestration-contract.md` §4 为唯一定义；本文件只强调两点：

- 不要无差别发送整个会话、全部需求包、所有已完成功能域或整个旧项目；
- Agent 确实需要查看额外文件时，先说明它与当前任务的直接关系，再只读加载该范围。

## Phase 2：TDD 功能切片

遵循 `rules/tdd-and-quality-gates.md` 和 `prompts/feature-developer.agent.md`，按任务类型先建立首个验证证据。每个功能切片：

1. 核对 HEAD 包含共同基线，并读取当前路径适用的全部 `AGENTS.md`；
2. 以最小行为完成实现，运行该切片适用的检查与 UI 场景；
3. 更新必要文档和任务证据；
4. 创建一次本地 commit。

功能切片必须纵向覆盖可见行为，不把“只建数据库表”或“只画页面壳”当作完整产品功能，除非它本身是经确认的独立迁移单元。

## Phase 3：专项 Agent

按需调用：

- `prompts/test-engineer.agent.md`：测试矩阵、fixture、集成与 E2E；
- `prompts/ui-reviewer.agent.md`：视觉、响应式、无障碍和组件交互；
- `prompts/security-reviewer.agent.md`：权限、秘密、依赖和数据流；
- `prompts/reviewer.agent.md`：独立核对实现与已确认方案。

专项 Agent 不绕过功能所有者直接扩大范围。发现架构或产品范围问题时返回主 Agent 决策。

## Phase 4：原子提交

遵循 `rules/worktree-and-commits.md`：

- 一个可独立验证、可独立回滚的功能单元对应一个 commit；
- commit 不混入无关格式化或其他任务；
- 提交正文包含 TASK、需求/验收 ID 和验证命令；
- 测试失败、需求未满足或工作区包含未知文件时不提交；
- 不 push、不 force push、不自动合并受保护分支。

## Phase 5：集成

唯一的 Integration Manager 使用角色提示文件 `prompts/integration-manager.agent.md`，按其中的流程（核对基线与提交边界、按依赖顺序 merge/cherry-pick、冲突保护最新用户改动、每步运行受影响检查、更新任务状态与 SHA、干净后立即清理 worktree 与任务分支）集成并行提交，仓库不变量见 `rules/worktree-and-commits.md`。

如果并行任务修改了同一契约，停止集成并回到任务计划，不用“最后写入覆盖前者”解决。

任务只有完成集成验证和安全清理后才能标记为“已完成”。脏 worktree、未集成补丁、冲突或测试失败时保留现场，并标记为进行中或阻塞。

一个功能域全部任务完成后，写入该域的交付证据并自动进入依赖已满足的下一功能域。已确认整体实施路线没有实质变化时，不重新向用户确认下一域。

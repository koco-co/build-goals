# 多 Agent 功能开发与集成

## Phase 1: 构造最小上下文包

每个功能 Agent 只获得：

- 一个 `TASK-NNN`；
- 对应 PRD 功能与验收 ID，或迁移发现；
- 相关架构章节和接口契约；
- 允许修改的文件与禁止区域；
- 测试数据与验证命令；
- 依赖提交；
- 单次 commit 完成条件。
- 当前作用域适用的根目录与局部 `AGENTS.md` 路径；
- 已通过 readiness 的共同基线和项目指令治理提交。

不要向所有 Agent 无差别发送整个会话或全部私有资料。

## Phase 2: TDD 功能切片

使用 `prompts/feature-developer.agent.md`：

1. 核对 HEAD 包含共同基线，并读取当前路径适用的全部 `AGENTS.md`；
2. 先写最小失败测试，并记录失败原因符合目标缺口；
3. 实现使测试通过的最小代码；
4. 重构命名、结构、错误处理和重复逻辑；
5. 运行该切片的格式、Lint、类型、单元与必要集成测试；
6. 对 UI 功能补充组件和 E2E 场景；
7. 更新必要文档和任务证据；
8. 创建一次本地 commit。

功能切片必须纵向覆盖可见行为，不把“只建数据库表”或“只画页面壳”当作完整产品功能，除非它本身是经确认的独立迁移单元。

## Phase 3: 专项 Agent

按需调用：

- `prompts/test-engineer.agent.md`：测试矩阵、fixture、集成与 E2E；
- `prompts/ui-reviewer.agent.md`：视觉、响应式、无障碍和组件交互；
- `prompts/security-reviewer.agent.md`：权限、秘密、依赖和数据流；
- `prompts/reviewer.agent.md`：独立核对实现与已确认方案。

专项 Agent 不绕过功能所有者直接扩大范围。发现架构或产品范围问题时返回主 Agent 决策。

## Phase 4: 原子提交

遵循 `rules/worktree-and-commits.md`：

- 一个可独立验证、可独立回滚的功能单元对应一个 commit；
- commit 不混入无关格式化或其他任务；
- 提交正文包含 TASK、需求/验收 ID 和验证命令；
- 测试失败、需求未满足或工作区包含未知文件时不提交；
- 不 push、不 force push、不自动合并受保护分支。

## Phase 5: 集成

唯一的 Integration Manager 使用 `prompts/integration-manager.agent.md`：

1. 检查提交边界和证据；
2. 按依赖顺序合并或 cherry-pick；
3. 处理冲突时保护最新用户改动；
4. 每次集成后运行受影响测试；
5. 更新 `docs/实施任务清单.md` 的状态和 commit SHA；
6. 确认任务 worktree 干净且没有未集成补丁后，立即移除该 worktree 和本地任务分支并记录证据；
7. 所有切片完成后运行全量门禁。

如果并行任务修改了同一契约，停止集成并回到任务计划，不用“最后写入覆盖前者”解决。

任务只有完成集成验证和安全清理后才能标记为“已完成”。脏 worktree、未集成补丁、冲突或测试失败时保留现场，并标记为进行中或阻塞。

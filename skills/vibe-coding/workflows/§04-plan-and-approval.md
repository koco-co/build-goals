# 架构落地、任务规划与第二次确认

## Phase 1: 写入已确认架构

用户确认架构后：

- PRD 驱动路线使用 `templates/architecture-design.template.md` 创建或规范化更新 `docs/架构设计方案.md`；
- 迁移路线使用 `templates/architecture-migration.template.md` 创建或规范化更新 `docs/架构迁移方案.md`。

文档必须标记“文档状态：已确认”，写明基线 HEAD、来源、方案比较、最终决策和验收方式。不得保留 TODO、TBD、待确认或模板占位符。

运行：

```bash
python3 <vibe-coding>/scripts/validate_delivery.py \
  <project-root> \
  --mode <greenfield|migration> \
  --phase architecture \
  --strict
```

失败时修复后重跑。

## Phase 2: 生成需求追踪

PRD 路线将全部 `F-NNN` 与 `F-NNN-AC-NN` 映射到任务。迁移路线将全部高优先级审查发现和迁移阶段映射到任务。

每个任务必须包含：

- `TASK-NNN`；
- 功能切片或迁移单元；
- 对应需求、验收项或审查发现；
- 明确输入和输出；
- 依赖任务；
- 负责角色；
- 允许修改和禁止修改的文件；
- 第一条失败测试；
- 完成后运行的检查；
- 正常测试数据；
- 是否可并行与 worktree 名；
- 单次 commit 边界；
- 回滚方式。

任务方案还必须包含配套 Skill 计划和“项目指令就绪”记录。此时可以把项目指令标记为“待脚手架验证”“预计有效沿用”或“预计调用 build-agents-md”，但不能提前声称已经验证。

## Phase 3: 构建依赖图和 Agent 计划

使用 `prompts/implementation-planner.agent.md` 输出：

1. 关键路径；
2. 可并行任务组；
3. 文件所有权冲突；
4. Agent 角色和上下文包；
5. 集成顺序；
6. 每阶段验收；
7. 预计需要的用户或外部环境动作。

禁止按“前端 Agent、后端 Agent”粗粒度分配整个层。优先按用户可见功能或可独立验证的垂直切片分配。

## Phase 4: 第二次用户确认

先在对话中展示完整任务列表、依赖图、并行计划、提交边界和验收矩阵。

同时展示配套 Skill 的触发证据、调用阶段、阻断性和恢复条件。`build-agents-md` 的完整正文尚未生成时，只确认它作为条件任务及其提交边界；后续仍需按该 Skill 展示完整文件内容并取得按需产物确认。

用户确认前：

- 不创建 `docs/实施任务清单.md`；
- 不初始化或替换工具链；
- 不创建 worktree；
- 不修改业务代码；
- 不创建功能 commit。

用户确认后，使用 `templates/implementation-plan.template.md` 写入 `docs/实施任务清单.md`，标记“文档状态：已确认”，并运行 plan 阶段严格校验。

任务范围变化时更新计划；会改变产品行为、架构或公开接口的变化必须重新取得确认。

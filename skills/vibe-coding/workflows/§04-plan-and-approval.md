# 架构文档、实施任务与第二次全局确认

开始本工作流前读取 `../rules/workflow-state-and-permissions.md`。第一次全局确认后进入 `architecture_approved`；第二次全局确认后进入 `plan_approved`。本文件不得在这两个状态之间提前创建实施任务文件或执行 Git 写操作。

## 1. 固定需求快照并写入已确认架构

第一次全局确认后：

- 路线 1–3 的来源需求包不在目标项目时，先执行只读比较；首次导入使用 `scripts/import_requirements.py ... --write`，已有不同快照则必须先展示影响并取得明确替换确认后使用 `--write --replace`；
- 路线 1–3 使用 `templates/architecture-design.template.md` 写 `docs/架构设计/架构设计方案.md`；
- 路线 4 使用 `templates/architecture-migration.template.md` 写 `docs/架构迁移/架构迁移方案.md`；
- 每个功能域使用 `templates/domain-architecture.template.md` 写入同一文档族的 `功能域/<功能域>.md`。

全局文档必须标记“文档状态：已确认”，记录项目路线、旧项目参考政策、允许参考范围、需求快照或迁移基线、方案比较、共同架构和跨域验证。功能域文档记录本域边界、需求或 Finding 映射、组件与依赖、接口和数据契约、验证策略与回退。

运行：

```text
python3 <vibe-coding>/scripts/validate_delivery.py <project-root> \
  --mode <greenfield|continuation|migration> \
  --phase architecture \
  --strict
```

路线 1–2 使用 `greenfield`，路线 3 使用 `continuation`，路线 4 使用 `migration`。失败时修复后重跑。

## 2. 在对话中生成按功能域拆分的任务方案

第二次全局确认前，Implementation Planner 只在对话中构建完整任务方案，不创建 `docs/实施任务/`。

路线 1–3 将所有 `F-NNN`、`F-NNN-AC-NN` 与行为样例 ID 映射到任务；路线 4 将全部 Blocking/High Findings 和已确认迁移阶段映射到任务。

拟定的全局实施清单应覆盖：

- 执行原则和配套 Skill 计划；
- 全局需求与行为样例追踪索引；
- 功能域依赖图与集成顺序；
- Agent、文件所有权和 worktree 计划；
- 测试数据、基础工程与项目指令 readiness；
- 跨域验收、提交和回滚策略。

每个拟定功能域任务必须有连续唯一的 `TASK-NNN`，并说明需求/验收/样例/Finding、目标、任务类型对应的首个验证证据、正常测试数据、验证命令、Worktree、集成状态、提交边界、Commit、回滚和完成条件。

任务编号在整个项目唯一。按用户可见的垂直功能切片，不按“前端 Agent / 后端 Agent”粗分整层。

## 3. 构建整体实施路线

使用 Implementation Planner 输出：

1. 功能域依赖顺序与关键路径；
2. 各域任务、可并行组和文件所有权冲突；
3. 脚手架、共享契约、项目指令和迁移基础任务；
4. 每域任务类型、验证策略与提交边界；
5. 集成顺序和最终跨域 E2E；
6. 预计需要的用户或外部环境动作。

给规划 Agent 的内容仅包含需求包全局索引、当前规划域及其直接依赖，不发送无关旧项目材料。

## 4. 第二次全局确认并落盘任务文档

在对话中一次展示整体实施路线、功能域顺序、任务摘要、并行边界、提交策略和验收矩阵。用户确认前：

- 不创建 `docs/实施任务/`；
- 不初始化或替换工具链；
- 不创建分支或 worktree；
- 不创建 commit；
- 不修改业务代码。

确认后进入 `plan_approved`，一次性写入：

- `docs/实施任务/实施任务清单.md`：全局依赖、追踪、基础工程、Agent/worktree、验证与集成策略；
- `docs/实施任务/功能域/<功能域>.md`：实际 `TASK-NNN`、任务类型、验证证据、测试数据、命令、提交和回滚边界。

全部任务文档标记“文档状态：已确认”，然后运行 plan 阶段严格校验。第二次确认同时授权统一状态表中 `plan_approved` 明确列出的本地 Git 操作，不扩大到 push、受保护分支合并、发布或部署。

这次确认覆盖已展示的全部功能域任务。后续完成一个域后自动进入下一域，不再询问“是否继续”或逐域确认。只有出现会改变产品行为、公开契约、持久化数据、认证授权、部署拓扑、核心工具链或整体依赖路线的实质变化，才返回对应全局门禁；局部实现细节和已确认范围内的任务细化直接更新本域文档并记录原因。

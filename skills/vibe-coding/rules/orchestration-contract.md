# 总控编排契约

## 1. 两次确认门禁

`vibe-coding` 只有两个强制写入门禁：

1. **架构确认**
   - 之前只读调研；
   - 确认后才能写入架构文档；
   - 仍不能搭建脚手架或开发功能。
2. **任务确认**
   - 先提交完整任务、依赖、并行、测试和提交方案；
   - 确认后才能写入任务清单、搭建脚手架、创建 worktree 和本地 commit。

后续若产品范围、公开接口、数据模型、认证、部署拓扑或关键工具链发生实质变化，回到对应门禁。

## 2. 路线与权威产物

### PRD 驱动

权威输入：

```text
docs/PRD需求文档.md
```

权威输出：

```text
docs/架构设计方案.md
docs/实施任务清单.md
docs/交付验收报告.md
```

### 已有项目迁移

权威输出：

```text
docs/架构迁移方案.md
docs/实施任务清单.md
docs/交付验收报告.md
```

项目已有同等权威文档时，在架构方案中决定合并或沿用；不创建职责重复的第二套文档。

## 3. Agent 团队角色

| 角色                    | 主要职责                     | 写权限          |
| ----------------------- | ---------------------------- | --------------- |
| Architecture Researcher | 官方规范、工具链、架构方案   | 无              |
| Competitor Researcher   | 竞品与开源参考               | 无              |
| Repository Auditor      | 全仓事实与风险               | 无              |
| Implementation Planner  | 功能切片、依赖和追踪         | 仅任务草案      |
| Feature Developer       | 单一功能切片和测试           | 仅分配 worktree |
| Test Engineer           | 测试矩阵、fixture、E2E       | 分配范围内      |
| UI Reviewer             | 视觉、交互、无障碍           | 默认只读        |
| Security Reviewer       | 权限、秘密、依赖与数据流     | 默认只读        |
| Integration Manager     | 唯一集成、冲突处理和全量验证 | 集成分支        |
| Independent Reviewer    | 对照方案审查证据             | 无              |

同一 Agent 不同时担任功能实现者和最终独立 Reviewer。

## 4. 上下文包

每个 Agent 输入必须包含：

- 任务 ID 和唯一目标；
- 权威需求或审查发现；
- 相关架构章节；
- 允许修改和禁止修改的文件；
- 输入、输出和接口；
- 第一条失败测试；
- 测试数据；
- 完成条件；
- 返回格式；
- 是否允许提交。

不发送与任务无关的整个仓库秘密、历史对话或用户数据。

## 5. 输出契约

研究 Agent 返回：

```markdown
## Facts

## Sources

## Findings

## Options

## Recommendation

## Risks

## Evidence Gaps
```

实现 Agent 返回：

```markdown
## Task

## Files Changed

## Tests Added First

## Implementation

## Commands and Results

## Commit

## Deviations

## Blockers
```

集成 Agent 返回：

```markdown
## Integrated Commits

## Conflicts

## Validation

## Task Plan Updates

## Remaining Risks
```

## 6. 配套 Skills

- 产品想法未澄清：`shape-idea`
- PRD 缺失或不完整：`build-prd`
- 项目需要 Skill：`build-skill`
- 项目需要 Plugin：`build-plugin`
- README 与事实不一致：`build-readme`
- 需要跨会话接续：`handoff`

这些 Skill 都是显式调用能力。平台支持受控委派时，在用户已经确认总体方案且子任务清楚的范围内调用；平台不支持时输出交接提示，等待用户显式触发。不得复制其完整流程到本 Skill。

## 7. 降级

无法使用 Subagent 时，主 Agent 按角色顺序执行并保持独立输入、输出和复核记录。

无法使用 Git worktree 时，按依赖串行执行，同一时间只允许一个功能切片修改工作区。

降级必须在交付报告中明确，不得把串行角色模拟描述成真实并发团队。

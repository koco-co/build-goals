---
name: vibe-coding
description: 按已确认需求包新建、续建或迁移项目，也可按指定范围参考旧项目；不用于普通代码修改或单点 Bug。
compatibility: 需要 Python 3.9+、Git，以及目标项目实际使用的构建与验证工具；调研公开资料时需要互联网访问。
disable-model-invocation: true
metadata:
  author: koco-co
  version: "2.2.0"
---

# Outcome

把已确认需求包转化为架构清晰、实现完整、可回滚且证据可复核的软件项目。

产出 `docs/架构设计/`（迁移路线用 `docs/架构迁移/`）、`docs/实施任务/` 和 `docs/交付验收/` 三类文档。

## Routing

1. 新项目，只按需求实现。
2. 新项目，参考旧项目的指定部分。
3. 现有项目，按需求续建。
4. 现有项目，架构或技术栈迁移。

- 路线 1–3 需要严格校验且已确认的完整需求包或正式阶段包；`.build-goals/build-prd/` 检查点不能直接实施。
- 需求包缺失、未确认、哈希漂移或样例不完整时，先执行基线 `health-check`；普通代码修改和单点 Bug 直接退出。

## Steps

0. 读取 `rules/workflow-state-and-permissions.md`，它是所有写入和 Git 操作的唯一权限表。
1. 读取 `workflows/§01-baseline-and-routing.md`，保护现场、选择路线、比较需求快照并完成基线健康检查。
2. 读取路线对应的 `workflows/§02-requirements-architecture.md` 或 `workflows/§03-migration-audit.md`；涉及 UI 时读取 `rules/ui-interaction-preview.md`，展示架构方案并等待第一次全局确认。
3. 读取 `workflows/§04-plan-and-approval.md`；第一次确认后固定需求快照和架构文档，展示整体实施路线，第二次确认后再写入实施任务。
4. 读取 `workflows/§05-scaffold-and-worktrees.md`；建立最小脚手架并通过就绪健康检查，之后才创建功能 worktree 或调起功能 Agent。
5. 读取 `workflows/§06-feature-delivery.md`、`rules/worktree-and-commits.md` 和 `rules/tdd-and-quality-gates.md`，按功能域交付，独立任务可并行，完成后自动进入下一域，不再询问是否继续。
6. 读取 `workflows/§07-validation.md` 和 `rules/acceptance-standard.md`，完成域内、跨域和端到端验证。
7. 读取 `workflows/§08-delivery.md`，写入交付证据并执行最终健康检查；受保护分支合并、push、发布、部署和本地 Plugin 更新另行授权。

## Rules

- 保留未提交修改；未完成对应确认前不写需求快照、架构、实施任务、代码或交付文档。
- 只有用户确认的产品范围、公开契约、数据、权限和部署变化才能进入实现。

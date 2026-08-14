# Worktree 与提交规范

## 1. 并发判定

只有任务同时满足以下条件才并发：

- 依赖已经满足；
- 接口契约已经冻结；
- 文件所有权不重叠；
- 测试可在隔离环境运行；
- 能形成独立 commit；
- 集成顺序明确。

共享数据模型、核心配置、锁文件、路由入口或同一组件的任务通常串行，除非先建立独立契约提交。

## 2. 基线

创建 worktree 前记录：

- 主工作树分支和 HEAD；
- 本轮唯一集成分支及最终受保护主分支；
- 工作区状态；
- 现有 worktrees；
- 任务依赖提交；
- 用户未提交修改。

所有并行分支从明确 SHA 创建，不使用会移动的模糊基线。

## 3. 命名

推荐：

```text
branch: feat/TASK-012-user-login
worktree: ../project-TASK-012-user-login
```

迁移任务可以使用：

```text
refactor/TASK-021-config-boundary
```

名称包含任务 ID 和功能，不包含 Agent 名称。

## 4. 文件所有权

任务清单列出：

- 可修改路径；
- 只读依赖；
- 禁止修改路径；
- 共享契约所有者。

Agent 发现需要修改未分配文件时先返回主控，不自行扩大范围。

## 5. 提交边界

一个 commit 必须：

- 对应一个可独立验证、可独立回滚的功能或迁移单元；
- 同时包含实现和该单元必要测试；
- 不混入无关格式化、依赖升级或文档重写；
- 通过任务规定的质量门禁；
- 工作区中没有未知文件；
- 在正文列出 TASK、需求/验收 ID 和验证命令。

示例：

```text
feat(auth): implement passwordless sign-in

TASK-012
Requirements: F-003, F-003-AC-01, F-003-AC-02
Tests: uv run pytest tests/auth -q
```

脚手架、共享契约和纯迁移也可以独立提交，但必须在任务清单中预先定义。

## 6. 集成

集成与清理的确切步骤以 `prompts/integration-manager.agent.md` 为流程唯一权威。本文件只保留仓库不变量：

- 只有 Integration Manager 可以集成并行提交；
- 集成按依赖顺序 merge 或 cherry-pick；
- 冲突时重新理解两侧语义，不用整文件 ours/theirs 覆盖，不 reset 隐藏冲突；
- 每个提交集成后运行受影响检查；
- 任务提交已集成、检查通过、worktree 干净且无独有改动时，立即移除该 worktree 和本地任务分支并记录命令证据；
- 未集成、脏文件、独有改动或所有权不明的 worktree 保留现场，任务保持进行中或阻塞。

## 7. 禁止操作

未经单独授权不执行：

- push 或 force push；
- merge 到受保护分支；
- rebase 改写共享历史；
- `git reset --hard`；
- `git clean`；
- 删除包含未集成提交的分支或 worktree；
- 清理未在本轮任务清单中声明、会话开始前已存在或所有权不明的 worktree；
- 自动 stash 用户工作；
- 修改 Git 远程或权限。

全部任务和最终质量门禁通过后，合并集成分支到受保护主分支仍需用户单独授权。获准并验证成功后，按相同证据标准清理本地集成 worktree 和分支；没有授权时保留集成分支，不 push。

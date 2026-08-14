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

只有 Integration Manager 可以集成并行提交。

集成时：

1. 核对父提交与任务状态；
2. 检查 diff 不越界；
3. 按依赖顺序 merge 或 cherry-pick；
4. 冲突时重新读取最新两侧内容；
5. 保留用户最新改动；
6. 运行受影响测试；
7. 确认任务 worktree 干净，并确认任务分支相对集成分支不存在未集成补丁；
8. 立即移除该 worktree 和对应本地任务分支；
9. 更新任务清单中的任务 SHA、集成 SHA、验证与清理证据；
10. 再处理下一提交。

禁止通过覆盖文件、选择“theirs/ours”整文件或重置分支隐藏冲突。

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

## 8. 清理

任务清单确认后，本轮任务 worktree 的安全清理属于已授权实施步骤，不再逐个询问。每个任务集成后立即执行：

1. 核对任务分支、worktree 路径和当前集成分支均与任务清单一致；
2. `git status --porcelain` 必须为空；
3. 任务 commit 已成为集成分支祖先，或 `git cherry <integration> <task-branch>` 不存在以 `+` 开头的未集成补丁；
4. 受影响测试在集成分支通过；
5. 使用精确路径执行 `git worktree remove <task-worktree>`；
6. merge 集成时使用 `git branch -d <task-branch>`；cherry-pick 集成时，只有前述补丁等价检查通过后才可对精确分支执行 `git branch -D <task-branch>`；
7. 重新运行 `git worktree list --porcelain` 和分支枚举，记录删除结果。

任一条件失败就保留 worktree 和分支，将任务标记为进行中或阻塞，并报告独有提交、脏文件或验证失败。不得把尚未集成的任务标记为已完成。交付报告分别记录已清理与因证据不足而保留的 worktrees。

全部任务和最终质量门禁通过后，合并集成分支到受保护主分支仍需用户单独授权。获准并验证成功后，按相同证据标准清理本地集成 worktree 和分支；没有授权时保留集成分支，不 push。

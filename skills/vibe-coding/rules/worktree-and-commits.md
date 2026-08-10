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
7. 更新任务清单；
8. 再处理下一提交。

禁止通过覆盖文件、选择“theirs/ours”整文件或重置分支隐藏冲突。

## 7. 禁止操作

未经单独授权不执行：

- push 或 force push；
- merge 到受保护分支；
- rebase 改写共享历史；
- `git reset --hard`；
- `git clean`；
- 删除包含未集成提交的分支或 worktree；
- 自动 stash 用户工作；
- 修改 Git 远程或权限。

## 8. 清理

只有在提交已安全集成、验证通过且不存在独有改动时，才移除 worktree。交付报告记录保留和清理的 worktrees。

# 脚手架与 Worktree 准备

## Phase 1: 选择最小现代化工具链

按照 `rules/modern-engineering.md`：

1. 核对当前官方支持和项目约束；
2. 选择包管理、运行时、格式化、Lint、类型检查、测试、pre-commit 和 CI；
3. 记录版本策略与选择理由；
4. 优先使用单一配置源和锁文件；
5. 不同时引入职责重叠的工具。

Python 项目通常优先评估 `uv + pyproject.toml + Ruff + Pyright + pytest + pre-commit`；CLI 可按需求采用 `Rich` 或 `Typer`。这只是默认候选，不替代项目事实。

## Phase 2: 建立最小可运行骨架

脚手架至少包含：

- 明确的源码与测试目录；
- 可重复安装的依赖和锁文件；
- 一个真实运行入口；
- 格式化、Lint、类型检查和测试命令；
- CI 最小质量门禁；
- `.gitignore` 和其他适用忽略文件；
- `.env.example` 或等价配置契约，不包含秘密；
- 正常测试数据的 fixture/factory/seed 入口；
- 适用的 AGENTS/CLAUDE 指令；
- 失败时可理解的日志或 CLI 输出。

先写最小 smoke test，再实现让它通过的骨架。

## Phase 3: 验证并提交脚手架

在干净或隔离环境运行安装、启动、格式、Lint、类型、构建和 smoke test。

全部通过后创建一个本地提交，例如：

```text
chore(scaffold): establish verified project foundation

TASK-001
```

脚手架提交不得混入第一个产品功能。

## Phase 4: 创建并行 Worktrees

仅对满足以下条件的任务并行：

- 依赖已经完成或不存在；
- 修改文件集合不重叠；
- 接口契约已经冻结；
- 能独立运行测试和提交；
- 集成顺序明确。

推荐命名：

```text
branch: feat/TASK-012-user-login
worktree: ../<repo>-TASK-012-user-login
```

每个 worktree 从同一已记录基线或明确依赖提交创建。创建后立即记录路径、分支、任务和所有权。

不为了展示并行而创建 worktree；共享核心文件或顺序强依赖的任务保持串行。

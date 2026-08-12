# 脚手架、项目指令与 Worktree 准备

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
- 失败时可理解的日志或 CLI 输出。

先写最小 smoke test，再实现让它通过的骨架。

## Phase 3: 验证并提交脚手架

在干净或隔离环境运行安装、启动、格式、Lint、类型、构建和 smoke test。

将实际执行的安装命令、启动或等价 smoke 命令、基础测试命令、退出状态和关键结果写入任务清单的“基础工程就绪”章节。库或无常驻服务的项目也不能只写“不适用”，应使用导入、CLI `--help`、最小示例或等价可执行 smoke 验证入口。先从基线摘要回填 readiness 前已经存在的 worktree 清单；每项使用“路径 | 完整分支引用 | 既有用途”，没有则记录 `N/A（无既有 worktree）`。

全部通过后创建一个本地提交，例如：

```text
chore(scaffold): establish verified project foundation

TASK-001
```

脚手架提交不得混入第一个产品功能。

已有项目不需要脚手架变更时，记录当前基础工程已经满足哪些条件及对应证据，不制造空提交。

## Phase 4: 建立项目指令就绪状态

脚手架或基础工程命令稳定后，重新核对基线阶段的项目指令分类。

### 有效沿用

只有以下条件全部满足时才记录“有效沿用”：

- 根 `AGENTS.md`、必要的局部文件和同目录 `CLAUDE.md` 单一来源入口结构有效；
- 构建、启动、格式、Lint、类型和测试命令来自当前仓库证据；
- 适用的安全、生成文件和禁止修改边界没有与最终架构冲突；
- 安全且低成本的关键命令已实际运行，未执行项准确记录原因。

不为有效文件做纯文案润色，也不创建项目指令治理提交。把验证证据写入任务清单；基础工程没有代码或配置变更时明确记录“无需变更”，不制造空提交。

### 创建或更新

出现以下任一证据时调用 `build-agents-md`：

- 根 `AGENTS.md` 缺失；
- `CLAUDE.md` 缺失、断链、目标错误或不是允许的单一来源入口；
- 关键命令、目录职责、禁止修改区或安全边界已证实失效；
- Monorepo 新增了确有不同技术栈、命令或职责的子项目；
- 现有指令互相冲突、包含秘密或危险操作。

向 `build-agents-md` 传递上层总控、任务 ID、当前基线、已确认架构、真实命令、文件范围和“本地提交由上层统一管理”。子 Skill 必须先展示完整正文和文件操作；用户确认后才能写入。完成静态校验和适用的真实命令验证后，由总控创建独立治理提交：

```text
docs(agent): establish project instructions
```

该治理提交只包含确认过的根目录或嵌套 `AGENTS.md` / `CLAUDE.md`，不得混入任务清单、产品功能或其他治理文件。提交完成后立即取得明确 SHA，回填任务清单的“治理提交”，并向子 Skill 结果回填同一 SHA；不得使用“本提交”或按最新 Git 历史动态定位。

随后完成“基础工程就绪”和“项目指令就绪”证据，令“功能开发基线”保持精确标记 `readiness 执行时的当前 HEAD`，并以独立计划提交保存记录，例如：

```text
docs(plan): record implementation readiness
```

这个标记只指 readiness 实际执行时的 HEAD；冻结的治理提交始终使用明确 SHA。后续任何根目录或嵌套项目指令变更都视为漂移，必须重新展示受影响正文、取得确认、形成新的独立治理提交并更新记录。

### 无法调用

项目指令不合格且平台不能受控调用 `build-agents-md` 时，使用 `rules/companion-skills.md` 的可直接复制提示暂停交接。不得创建功能 worktree、调起功能 Agent，或在本 Skill 内临时拼写一份简化 AGENTS 文件。

## Phase 5: 执行 readiness 门禁

更新 `docs/实施任务清单.md` 的“基础工程就绪”和“项目指令就绪”章节，然后运行：

```bash
python3 <vibe-coding>/scripts/validate_delivery.py \
  <project-root> \
  --mode <greenfield|migration> \
  --phase readiness \
  --require-clean \
  --strict
```

该门禁先拒绝未执行、失败或否定式证据，核验基础工程提交和既有 worktree 基线，再复用 `build-agents-md` 的校验器以 `--require-symlink` 检查单一来源入口、本地链接、占位符、确认与验证记录。项目指令更新时还会核验治理提交只包含根目录或嵌套 `AGENTS.md` / `CLAUDE.md`、明确 SHA 已冻结且属于功能开发基线。失败时修复或恢复到对应阶段，不得降级为 warning 后继续。

readiness 通过后立即取得当次校验的 HEAD SHA，将任务清单中的 `readiness 执行时的当前 HEAD` 回填为该明确 SHA，并在创建功能 worktree 前保存这项元数据变更。自引用标记只允许 readiness 临时使用；delivery 会拒绝仍未回填的标记。

## Phase 6: 创建并行 Worktrees

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

共同基线必须通过 readiness；项目指令发生更新时，该基线必须包含冻结的治理提交。readiness 会枚举所有已注册的非当前 worktree，只豁免基线阶段按路径、分支和用途准确登记的既有 worktree；任务写 N/A、遗漏或仅匹配 TASK/分支名都不能放行新 worktree。任何功能 worktree 早于 readiness 创建，都应移除尚无独有改动的本轮 worktree后重新建立；存在独有改动时保留现场并报告阻塞，不强制删除。

不为了展示并行而创建 worktree；共享核心文件或顺序强依赖的任务保持串行。

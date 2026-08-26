# 脚手架、项目指令与 Worktree 准备

## Phase 1：确定项目实际工具链

按照 `rules/modern-engineering.md`：

1. 核对当前官方支持和项目约束；
2. 选择项目实际需要的运行时、依赖管理、构建和验证工具；
3. 记录版本策略与选择理由；
4. 依赖需要锁定时使用项目生态的锁文件；
5. 不同时引入职责重叠的工具。

格式化、Lint、类型检查、pre-commit、CI 或 CLI 框架只有在项目要求、选定生态或仓库事实支持时才纳入，不使用默认技术栈清单替代设计决策。

## Phase 2：建立最小可运行骨架

脚手架只包含架构方案和需求要求的内容，最低保证：

- 一个真实运行入口；
- 可重复执行的安装或构建方式；
- 能验证该入口的命令。

源码、测试、锁文件、格式化、Lint、类型检查、CI、忽略文件、环境变量示例、测试数据和日志，只在需求或项目技术选择确实需要时创建。

## Phase 3：验证并提交脚手架

运行架构方案中已确认的安装、构建、启动和验证命令。

将实际执行的安装命令、启动或等价 smoke 命令、基础测试命令、退出状态和关键结果写入 `docs/实施任务/实施任务清单.md` 的“基础工程就绪”章节。库或无常驻服务的项目也不能只写“不适用”，应使用导入、CLI `--help`、最小示例或等价可执行 smoke 验证入口。先从基线摘要回填 readiness 前已经存在的 worktree 清单；每项使用“路径 | 完整分支引用 | 既有用途”，没有则记录 `N/A（无既有 worktree）`。

全部通过后创建一个本地提交，例如：

```text
chore(scaffold): establish verified project foundation

TASK-001
```

脚手架提交不得混入第一个产品功能。

已有项目不需要脚手架变更时，记录当前基础工程已经满足哪些条件及对应证据，不制造空提交。

## Phase 4：执行就绪检查点

脚手架或基础工程命令稳定后受控调用 `health-check`，传递当前 HEAD、脚手架和真实命令证据、项目指令初步状态、已生成规范产物、任务范围和上层提交契约。

没有发现问题时不与用户交互，直接记录就绪结论。发现问题时暂停当前阶段，由 `health-check` 一次性报告；用户确认后直接组织修复、验证并复检。项目指令需要新增或整体重构时，仍须展示完整正文和全部文件操作；确认后形成独立治理提交：

```text
docs(agent): establish project instructions
```

治理提交只包含确认过的根目录或嵌套 `AGENTS.md` / `CLAUDE.md`，不得混入任务清单、产品功能或其他治理文件。提交完成后立即取得明确 SHA，回填任务清单的“治理提交”，并把同一 SHA 记入 `health-check` 结果。

项目指令不需修改时，只有以下条件全部满足才记录“有效沿用”：

- 根 `AGENTS.md`、必要的局部文件和同目录 `CLAUDE.md` 单一来源入口结构有效；
- 记录的构建、启动和适用验证命令来自当前仓库证据；
- 适用的安全、生成文件和禁止修改边界没有与最终架构冲突；
- 安全且低成本的关键命令已实际运行，未执行项准确记录原因。

有效沿用时不制造改写提交。无论哪一分支，都完成“基础工程就绪”和“项目指令就绪”证据，令“功能开发基线”保持精确标记 `readiness 执行时的当前 HEAD`，并以独立计划提交保存记录，例如：

```text
docs(plan): record implementation readiness
```

这个标记只指 readiness 实际执行时的 HEAD；冻结的治理提交始终使用明确 SHA。后续任何根目录或嵌套项目指令变更都视为漂移，必须重新展示受影响正文、取得确认、形成新的独立治理提交并更新记录。

平台不能受控调用时按 `rules/companion-skills.md` 输出只指向 `health-check` 的人工交接提示。复检满足恢复条件前，不得创建功能 worktree 或调起功能 Agent。

## Phase 5：执行 readiness 门禁

先按 `checklists/implementation-readiness.md` 检查任务清单、工具链、基础工程、项目指令和既有 worktree 证据；更新 `docs/实施任务/实施任务清单.md` 的对应章节，然后运行：

```bash
python3 <vibe-coding>/scripts/validate_delivery.py \
  <project-root> \
  --mode <greenfield|continuation|migration> \
  --phase readiness \
  --require-clean \
  --strict
```

该门禁先拒绝未执行、失败或否定式证据，核验基础工程提交和既有 worktree 基线，再以 `--strict` 检查项目指令单一来源入口、本地链接、占位符、确认与验证记录。项目指令更新时还会核验治理提交只包含根目录或嵌套 `AGENTS.md` / `CLAUDE.md`、明确 SHA 已冻结且属于功能开发基线。失败时修复或恢复到对应阶段，不得降级为 warning 后继续。

readiness 通过后立即取得当次校验的 HEAD SHA，将任务清单中的 `readiness 执行时的当前 HEAD` 回填为该明确 SHA，并在创建功能 worktree 前保存这项元数据变更。自引用标记只允许 readiness 临时使用；delivery 会拒绝仍未回填的标记。

## Phase 6：创建并行 Worktrees

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

---
name: vibe-coding
description: 依据 docs/PRD需求文档.md 从零设计并实现项目，或审查并迁移已有项目；经过架构与任务两个全局决策门禁，按生命周期调用配套 Skills，在项目指令就绪后以 TDD、多 Agent 和可选 Git worktrees 完成功能开发、原子提交与全链路验收。
compatibility: 需要 Python 3.9+、Git、互联网访问及目标项目的构建与测试工具。
disable-model-invocation: true
metadata:
  author: koco-co
  version: "1.2.0"
---

# Outcome

将已经确认的产品需求或已有低质量项目，转化为架构清晰、实现完整、测试充分、可独立回滚并具有可复核交付证据的软件项目。

## Routing

- 当前项目存在已确认的 `docs/PRD需求文档.md`，且用户要求实现该 PRD 时，执行“PRD 驱动的新建或续建项目”分支。
- 用户要求审查并现代化改造已有项目时，执行“已有项目架构审查与迁移”分支；先建立当前基线，再提出迁移方案。
- PRD 驱动分支缺少有效 `docs/PRD需求文档.md` 时，转交 `build-prd`；PRD 完成前不自行推断产品需求。
- 项目需要新增或升级 Agent Skill、Plugin、README 或项目指令时，按 `rules/companion-skills.md` 分别调用 `build-skill`、`build-plugin`、`build-readme` 或 `build-agents-md`。
- 项目指令缺失、链接异常或与真实工程事实冲突时，必须在功能开发前完成 `build-agents-md`；无法受控调用时暂停并输出可直接复制的交接提示。
- 只要求澄清想法时转交 `shape-idea`；只要求整理会话交接时转交 `handoff`。
- 普通代码修改、单点 Bug 修复、单个文档编写或没有完整项目交付目标的任务，不进入本 Skill。

## Steps

1. 建立只读基线并选择路线
   - 完整读取 `workflows/§01-baseline-and-routing.md`。
   - 读取 Git 当前分支、HEAD、工作区状态、已有 worktrees、项目规则、文档、代码、测试、CI 和配置。
   - 将当前 HEAD、未提交修改和用户新增文件视为必须保护的工作，不执行 reset、clean、强制 checkout、历史改写或无证据覆盖。
   - PRD 驱动分支先执行 `scripts/validate_prd.py`；已有项目分支先完成全仓事实盘点。
   - 完成条件：目标路线、输入产物、当前状态、现有用户修改、可用工具和无法继续的原因均已明确。

2. 调研并提出架构方案
   - PRD 驱动分支完整读取 `workflows/§02-greenfield-architecture.md`。
   - 已有项目分支完整读取 `workflows/§03-migration-audit.md`。
   - 调研前读取 `rules/modern-engineering.md`、`rules/repository-audit.md`、`rules/orchestration-contract.md` 和 `rules/companion-skills.md`。
   - 使用多个只读 Agent 并行调研官方规范、当前稳定工具链、竞品、活跃开源项目、项目现状、安全和测试策略。
   - 输出至少两个可行方案、明确权衡、推荐方案、目标目录树、模块边界、数据与接口契约、质量策略和迁移风险。
   - 只在对话中提交架构方案；用户确认前不写入架构文档，也不修改项目代码。
   - 完成条件：用户明确确认推荐架构、实施边界和关键权衡。

3. 写入架构文档并安排实施任务
   - 完整读取 `workflows/§04-plan-and-approval.md`。
   - 新建或续建项目使用 `templates/architecture-design.template.md` 写入 `docs/架构设计方案.md`。
   - 迁移项目使用 `templates/architecture-migration.template.md` 写入 `docs/架构迁移方案.md`。
   - 使用 `templates/implementation-plan.template.md` 生成按功能切片、需求可追踪、依赖明确、测试先行、可独立提交和回滚的任务方案。
   - 先在对话中提交任务方案；用户第二次确认前不写入 `docs/实施任务清单.md`，也不搭建脚手架。
   - 用户确认后写入任务清单，并运行 `scripts/validate_delivery.py` 的 plan 阶段校验。
   - 完成条件：架构文档和任务清单均标记为已确认，每个需求与验收项都有任务、测试和提交边界。

4. 构建脚手架并通过项目指令就绪门禁
   - 完整读取 `workflows/§05-scaffold-and-worktrees.md`。
   - 按 `rules/modern-engineering.md` 选择当前稳定且与项目约束匹配的工具链，不为追求新颖而引入无必要复杂度。
   - 建立最小可运行骨架、依赖管理、格式化、Lint、类型检查、测试入口、CI、环境变量示例、忽略规则和正常测试数据基础。
   - 脚手架必须通过适用检查，再形成一个可独立回滚的本地提交。
   - 依据已验证的真实命令复查项目指令；需要创建或更新时调用 `build-agents-md`，在完整内容确认后写入、严格验证，并由总控形成只含项目指令的独立治理提交、回填明确 SHA。
   - 在任务清单记录安装、启动或 smoke、基础测试的实际证据和既有 worktree 基线，再运行 `scripts/validate_delivery.py --phase readiness --strict`；通过前不得创建功能 worktree 或调起功能 Agent。
   - 只有 readiness 通过后，才根据依赖图为无依赖且文件所有权不重叠的任务创建独立 worktree；有依赖的任务保持串行。
   - 完成条件：干净环境可以安装、启动并运行第一组测试，项目指令有效且位于功能开发共同基线，任务与 worktree 映射已经冻结。

5. 调起 Agent 开发团队并按功能交付
   - 完整读取 `workflows/§06-feature-delivery.md`。
   - 读取 `rules/worktree-and-commits.md` 与 `rules/tdd-and-quality-gates.md`。
   - 每个 Agent 开始前读取其作用域内的 `AGENTS.md`；只领取一个可独立验证的功能切片，先写失败测试，再实现最小代码，随后重构并运行该切片要求的全部质量检查。
   - 每个功能单元通过验收后创建一次本地 Git commit；提交必须包含任务与需求追踪信息，不混入其他任务。
   - 并行任务通过 worktree 隔离；集成由唯一的 Integration Manager 按依赖顺序进入已确认的集成分支，并在每次集成后重跑受影响检查。
   - 任务提交已集成、检查通过、worktree 干净且不存在未集成独有改动时，立即自动移除该 worktree 和本地任务分支；不把已完成 worktree 留到最终交付再批量清理。
   - 平台没有 Subagent 或 worktree 能力时，以角色隔离的串行方式执行，并在交付中明确降级情况。
   - 完成条件：所有确认任务均已实现、集成并关联到唯一提交，没有遗漏需求、未说明的范围漂移或已完成但仍残留的任务 worktree。

6. 完成全链路验证
   - 完整读取 `workflows/§07-validation.md`。
   - 读取 `rules/acceptance-standard.md`，使用 `checklists/final-acceptance.md` 完成内容与场景审查。
   - 运行格式化、Lint、类型检查、构建、单元测试、集成测试和端到端测试；有前端或可视界面时，再执行视觉、响应式、无障碍和组件交互验证。
   - 使用真实可复现的正常测试数据验证平台流程，并清理调试数据、脏数据、占位文案、PRD 原文和用户口述文案。
   - 检查安全密钥、环境变量、权限、依赖、日志、错误处理、文档与运行入口，并复查项目指令是否发生已证实的失效或冲突。
   - 运行 `scripts/validate_delivery.py` 的 delivery 阶段严格校验；已完成并集成的任务仍残留已注册 worktree 时必须失败，修复后重跑。
   - 完成条件：所有适用质量检查通过，未验证内容和无法完成的原因都有准确证据，不把静态存在描述为真实功能已通过。

7. 交付并停止
   - 完整读取 `workflows/§08-delivery.md`。
   - 使用 `templates/delivery-report.template.md` 写入 `docs/交付验收报告.md`。
   - 更新 `docs/实施任务清单.md` 中的状态、测试证据和 commit SHA，再执行最终校验。
   - 全部任务验收通过后，若集成分支不同于受保护主分支，先报告最终 diff 与验证证据并请求一次明确合并授权；获准后本地合并、重跑最终校验，再清理集成 worktree 和本地集成分支。
   - 按配套 Skill 生命周期完成 README、项目指令和交接处理；不在本 Skill 中复制其他 Skill 的构建流程。
   - 完成条件：用户能够定位全部产物、提交和验证证据，并能明确判断哪些已经验证、哪些尚未验证、哪些无法完成。

## Delivery

- PRD 驱动分支交付 `docs/架构设计方案.md`、`docs/实施任务清单.md`、`docs/交付验收报告.md`、实现代码、测试数据与功能提交。
- 迁移分支交付 `docs/架构迁移方案.md`、`docs/实施任务清单.md`、`docs/交付验收报告.md`、迁移代码、测试数据与阶段提交。
- 最终回复列出需求追踪结果、最终目录、Agent 与 worktree 分工、提交清单、实际运行命令、测试结果、界面验证、安全检查和剩余限制。
- 分别说明已验证内容、未验证内容和无法完成的原因，并区分静态检查、真实用户流程、视觉验证和外部环境限制。
- 不自动 push、发布、部署或开始下一个项目。
- 实现和验证完成后，由总控一次询问当前任务适用的 commit、push、发布、部署或本地 Plugin 更新动作；子 Skill 不重复询问。

## Guardrails

- 当前仓库内容和未提交修改均属于用户资产；不回滚、不覆盖、不删除、不丢弃，不使用 `git reset --hard`、`git clean`、强制 checkout、rebase 改写共享历史或 force push。
- 用户确认架构前保持项目只读；用户确认任务清单前不搭建脚手架或修改业务代码。
- 用户确认实施任务清单后，视为授权在确认范围内创建本地分支、worktree 和本地 commit；不包含 push、合并受保护分支、发布、部署、外部数据写入或权限提升。
- 任务确认不授权写入用户尚未看过的完整产物；配套 Skill 的按需内容确认仍须完成。
- 任务清单确认同时授权清理本次任务创建且已安全集成的干净 worktree 和本地任务分支；脏 worktree、未集成独有提交、未知 worktree 或会话开始前已存在的 worktree 不自动删除。
- 任何会改变产品范围、公开接口、持久化数据、认证授权、兼容性或部署拓扑的偏离，都必须回到设计或任务确认阶段。
- 多 Agent 只接收完成任务所需的最小上下文，不向外部服务发送私有代码、凭据、用户数据或未公开文档。
- 测试不得破坏生产数据；真实测试数据必须位于隔离环境，可重复创建并有明确清理策略。
- 现代化不等于盲目升级；必须依据官方支持、项目约束、维护活跃度、迁移成本和可验证收益选择工具。
- 不以注释、README、假数据、跳过测试、降低断言或隐藏失败代替功能实现。
- 无法安全合并用户现有改动、缺少必要访问条件或关键验收不能执行时，停止在最小阻塞点并给出可复核证据。

## References

- 建立基线和选择路线时，完整读取 `workflows/§01-baseline-and-routing.md`。
- PRD 驱动架构设计时，完整读取 `workflows/§02-greenfield-architecture.md`。
- 已有项目审查与迁移时，完整读取 `workflows/§03-migration-audit.md`。
- 架构确认后编排任务时，完整读取 `workflows/§04-plan-and-approval.md`。
- 搭建脚手架、准备项目指令和创建 worktrees 时，完整读取 `workflows/§05-scaffold-and-worktrees.md` 与 `rules/companion-skills.md`。
- 功能开发与集成时，完整读取 `workflows/§06-feature-delivery.md`。
- 验证时，完整读取 `workflows/§07-validation.md`、`rules/tdd-and-quality-gates.md`、`rules/acceptance-standard.md` 和 `checklists/final-acceptance.md`。
- 交付时，完整读取 `workflows/§08-delivery.md` 和 `templates/delivery-report.template.md`。
- 组织 Agent 团队前，读取 `rules/orchestration-contract.md`；每个角色只读取 prompts 目录中与其职责对应的 Agent 文件。
- 评审架构时使用 `checklists/architecture-acceptance.md`；开始编码前使用 `checklists/implementation-readiness.md`。
- 需要输出粒度参考时，按路线读取 `examples/greenfield-plan.example.md` 或 `examples/migration-plan.example.md`。

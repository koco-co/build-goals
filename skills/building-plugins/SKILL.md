
---
name: building-plugins
description: 由用户显式调用的 Agent Plugin 构建、升级与迁移工作流。用于创建、改造 Claude Code、Codex 等Agent Plugin，组织 Skills、Agents、Hooks、MCP、UI 与发布配置；Plugin 中的新建或升级 Skill 必须遵循 building-skills 的同一规范。
compatibility: 目前仅适配 Claude Code 与 Codex；机械校验需 Python 3.9+。
disable-model-invocation: true
metadata:
  author: koco-co
  version: "1.0.0"
---
# Outcome

将明确的插件需求转化为结构清晰、权限可控、能够安装和验证，并适配 Claude Code、Codex 等 Agent 的完整 Plugin。

## Routing

- 用户明确调用 `building-plugins` 并要求从零构建 Plugin 时，执行“新建 Plugin”分支。
- 用户提供已有 Plugin 并要求完善、修复或升级时，执行“审查与升级”分支。
- 用户要求把现有 Skills、Hooks、Agents 或配置仓库改造成 Plugin 时，执行“仓库迁移”分支。
- 用户要求同时支持 Claude Code 与 Codex 时，执行“双平台 Plugin”分支，核心组件只维护一份，Manifest 与平台适配分别管理。
- Plugin 需要新建或升级 Skill 时，转交 `building-skills`；平台不支持 Skill 间受控委派时，输出明确交接内容并要求用户显式调用。
- 用户只要求编写单个 Skill 且没有插件打包、安装或分发需求时，转交 `building-skills`。
- 无法确认是否为显式调用时，不推断触发；要求用户明确调用 `building-plugins`。

## Steps

1. 查明事实

   - 完整读取 `workflows/§01-research.md`。
   - 识别目标平台、现有仓库、组件、安装方式、权限、发布方式和稳定接口。
   - 对已有 Plugin 或迁移任务，读取全部 Manifest、Skills、Agents、Hooks、MCP、UI、脚本、测试和发布配置。
   - 核对 Claude Code 与 Codex 当前官方契约；当前范围外的平台只记录，不提前实现。
   - 不询问能够从仓库、环境或文档中自行查明的事实。
   - 完成条件：形成当前结构、目标结构、平台差异、风险和未知项摘要。
2. 确认关键决策

   - 完整读取 `workflows/§02-clarification.md`。
   - 只询问无法自行确定，并且会改变插件形态、权限、发布或验收结果的问题。
   - 每轮只询问一个主要问题，同时给出推荐答案、理由和其他选择的影响。
   - 已经明确的内容不得重复询问；没有待确认事项时直接进入设计。
   - 完成条件：目标平台、插件形态、组件范围、安装方式、权限、版本策略和验收标准明确。
3. 提出设计并等待确认

   - 完整读取 `workflows/§03-design.md`。
   - 设计前读取 `rules/plugin-architecture.md`、`rules/platform-compatibility.md`、`rules/security-and-permissions.md`。
   - Plugin 包含 Skill 时，同时读取 `rules/skill-architecture.md` 和 `rules/skill-quality-standard.md`。
   - 使用 `templates/plugin-design-proposal.template.md` 输出 `tree` 风格目录、组件边界、平台适配、软链接、验证和交付方案。
   - 明确哪些能力属于 Skill、Agent、Hook、MCP、UI、CLI、CI 或 Manifest。
   - 用户确认前不得创建、修改、移动或删除目标文件。
   - 完成条件：用户明确确认实施范围、破坏性变化和验收标准。
4. 处理 Skill 子任务

   - 完整读取 `workflows/§04-skill-delegation.md`。
   - 已有 Skill 先运行 `scripts/validate_skill.py` 并使用 `checklists/skill-design-review.md`、`checklists/skill-semantic-acceptance.md` 复核。
   - 新建或升级 Skill 时，使用 `building-skills`；不得在本 Skill 中复制一套 Skill 构建流程。
   - 需要输出 Skill 骨架时，使用 `templates/skill.template.md`。
   - 多 Agent 提示文件必须使用 `<name>.agent.md`。
   - 完成条件：所有纳入 Plugin 的 Skill 均符合 `building-skills` 的同一规范，并记录实际验证结果。
5. 执行

   - 完整读取 `workflows/§05-implementation.md`。
   - 只创建实际需要的组件；不为未来能力创建空目录和占位文件。
   - 双平台共用内容只维护一份；重复使用的仓库内文件使用相对软链接，链接目标必须留在 Plugin 根目录内。
   - Claude Code 配置写入 `.claude-plugin/`，Codex 配置写入 `.codex-plugin/`；其他组件位于 Plugin 根目录。
   - 确定性转换与校验交给脚本，事件驱动行为交给 Hooks，外部工具和数据接入交给 MCP。
   - 完成条件：已确认组件全部落地，路径闭合，权限最小化，没有未经同意的外部副作用。
6. 验证

   - 完整读取 `workflows/§06-validation.md`。
   - 运行 `scripts/validate_plugin.py`，再运行目标平台官方校验和真实安装或本地加载测试。
   - 使用 `checklists/plugin-design-review.md` 和 `checklists/plugin-semantic-acceptance.md` 完成语义与场景验收。
   - 至少覆盖 Manifest、组件发现、显式调用、负向不触发、软链接、安装、更新、失败路径和平台差异。
   - 无法运行的平台必须标为“未完成真实客户端验证”，不得描述为已通过。
   - 完成条件：机械检查通过，关键场景通过，未验证与阻塞项明确。
7. 交付并停止

   - 完整读取 `workflows/§07-delivery.md`。
   - 使用 `templates/plugin-delivery-report.template.md` 输出交付报告。
   - 列出最终目录、平台 Manifest、组件、软链接、命令、结果、版本和发布状态。
   - 当前 Plugin 交付后停止，不自行开始下一个 Plugin 或其他平台适配。
   - 完成条件：用户能够定位全部变更、复现验证并判断是否验收。

## Delivery

最终输出必须包含：

- Plugin 目标、已完成范围和明确排除项；
- 最终目录树与关键组件职责；
- 新增、修改、删除和迁移内容；
- Claude Code 与 Codex 的 Manifest、调用、安装和验证差异；
- Skill 子任务及其 `building-skills` 验收结果；
- 软链接清单及目标；
- 实际运行的命令、结果、失败修复记录；
- 已验证、未验证和阻塞项；
- 版本、Marketplace 或发布状态；
- 完成后停止。

## Guardrails

- 保护代码、凭据、用户数据、仓库权限和外部服务权限。
- 用户确认设计前保持只读；实施确认不自动授权提交、推送、发布、删除、上线或提高权限。
- 引入 MCP、Hooks、可执行脚本、网络访问、认证、遥测或持久化前，明确权限和数据流。
- 软链接只允许相对路径，并且最终目标必须位于当前 Plugin 根目录内。
- 不复制 `building-skills` 已经负责的 Skill 规范；通过委派和软链接复用。
- 不把静态文件存在描述为真实安装或调用已经通过。
- 不为 Claude Code 与 Codex 复制两套相同工作流；只隔离真实的平台差异。
- 当前不声明其他 Coding Agent 的兼容性。

## References

- 开始时完整读取 `workflows/§01-research.md`。
- 澄清关键决策时完整读取 `workflows/§02-clarification.md`。
- 输出设计前完整读取 `workflows/§03-design.md`、`rules/plugin-architecture.md`、`rules/platform-compatibility.md` 和 `rules/security-and-permissions.md`。
- Plugin 包含 Skill 时读取 `rules/skill-architecture.md`、`rules/skill-quality-standard.md` 和 `templates/skill.template.md`。
- 处理 Skill 子任务时完整读取 `workflows/§04-skill-delegation.md`。
- 实施时完整读取 `workflows/§05-implementation.md`。
- 验证时完整读取 `workflows/§06-validation.md`、`checklists/plugin-design-review.md` 和 `checklists/plugin-semantic-acceptance.md`。
- 需要独立 Reviewer 时读取 `prompts/reviewer.agent.md`。
- 交付时完整读取 `workflows/§07-delivery.md` 和 `templates/plugin-delivery-report.template.md`。

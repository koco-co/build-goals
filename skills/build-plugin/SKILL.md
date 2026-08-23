---
name: build-plugin
description: 创建、升级或迁移 Claude Code、Codex 等 Agent Plugin；任务涉及 Plugin 打包、平台适配、安装或分发时使用，单独构建 Skill 或普通代码时不使用。
compatibility: 需要互联网访问和 Python 3.9+ 运行内置静态校验脚本。
metadata:
  author: koco-co
  version: "2.2.0"
---

# Outcome

将明确的插件需求转化为结构清晰、权限可控、能够安装和验证，并适配 Claude Code、Codex 等 Agent 的完整 Plugin。

## Routing

- 从零构建 Plugin 时，执行“新建 Plugin”分支。
- 用户提供已有 Plugin 并要求完善、修复或升级时，执行“审查与升级”分支。
- 用户要求把现有 Skills、Hooks、Agents 或配置仓库改造成 Plugin 时，执行“仓库迁移”分支。
- 用户要求同时支持 Claude Code 与 Codex 时，执行“双平台 Plugin”分支，核心组件只维护一份，Manifest 与平台适配分别管理。
- 由 `vibe-coding` 等上层总控受控调用时，保留尚未完成的内容确认，但按上层任务、提交与恢复契约返回结果。
- 由 `health-check` 受控调用时，审查阶段保持只读，仅返回问题、证据、修复方案、影响文件和验证方式；上层取得修复确认后，按本 Skill 现有流程修复和验证，保留尚未确认的行为与内容门禁。
- Plugin 需要新建或升级 Skill 时，转交 `build-skill`；平台不支持 Skill 间受控委派时，生成完整交接提示，由用户继续调用对应 Skill。
- 用户只要求编写单个 Skill 且没有插件打包、安装或分发需求时，转交 `build-skill`。

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
   - Plugin 包含 Skill 时，同时读取 `rules/skill-architecture.md`、`rules/skill-frontmatter.md` 和 `rules/skill-quality-standard.md`。
   - 使用 `templates/plugin-design-proposal.template.md` 输出 `tree` 风格目录、组件边界、平台适配、共享文件、验证和交付方案。
   - 明确哪些能力属于 Skill、Agent、Hook、MCP、UI、CLI、CI 或 Manifest。
   - 用户确认前不得创建、修改、移动或删除目标文件。
   - 完成条件：用户明确确认实施范围、破坏性变化和验收标准。

4. 处理 Skill 子任务
   - 完整读取 `workflows/§04-skill-delegation.md`。
   - 已有 Skill 先运行 `scripts/validate_skill.py`，再依次使用 `checklists/skill-design-review.md`、`checklists/skill-content-review.md` 和 `checklists/skill-copy-review.md` 复核。
   - 新建或升级 Skill 时，使用 `build-skill`；不得在本 Skill 中复制一套 Skill 构建流程。
   - 需要输出 Skill 骨架时，使用 `templates/skill.template.md`。
   - 多 Agent 提示文件必须使用 `<name>.agent.md`。
   - 新建、整体重构或改变触发、Frontmatter、权限与平台行为时，使用 `prompts/reviewer.agent.md` 调起独立 Reviewer。
   - 完成条件：所有纳入 Plugin 的 Skill 均符合 `build-skill` 的同一规范，并记录内容审查、文案审查、内容回归、适用的独立审查和实际验证结果。

5. 执行
   - 完整读取 `workflows/§05-implementation.md`。
   - 只创建实际需要的组件；不为未来能力创建空目录和占位文件。
   - 双平台共用内容只设一个规范源；跨 Skill 运行依赖使用清单声明的普通镜像，并通过确定性脚本同步和校验。
   - Claude Code 配置写入 `.claude-plugin/`，Codex 配置写入 `.codex-plugin/`；其他组件位于 Plugin 根目录。
   - 确定性转换与校验交给脚本，事件驱动行为交给 Hooks，外部工具和数据接入交给 MCP。
   - 完成条件：已确认组件全部完成，文件引用有效，权限保持最小化，没有未经同意的外部副作用。

6. 验证
   - 完整读取 `workflows/§06-validation.md`。
   - 运行 `scripts/validate_plugin.py`，再运行目标平台官方校验和真实安装或本地加载测试。
   - 使用 `checklists/plugin-design-review.md` 和 `checklists/plugin-semantic-acceptance.md` 完成内容与场景审查。
   - 验证本次变更涉及的 Manifest、组件发现、调用策略、共享镜像、安装、更新、可复现失败和平台差异。
   - 无法运行的平台必须标为“未完成真实客户端验证”，不得描述为已通过。
   - 完成条件：静态检查和关键场景均通过，未验证内容和无法继续的原因均已说明。

7. 按调用模式交付并停止
   - 完整读取 `workflows/§07-delivery.md`。
   - 使用 `templates/plugin-delivery-report.template.md` 输出交付报告。
   - 列出最终目录、平台 Manifest、组件、共享镜像与必要链接、命令、结果、版本和发布状态。
   - 独立调用时，只列出真实适用的 commit、push、Marketplace、Claude Code Plugin 与 Codex Plugin 动作，并主动询问用户是否执行；允许全部授权或只授权其中部分动作。
   - 受控调用时不重复询问，也不执行 commit、push、Marketplace、Release 或本地 Plugin 更新；向上层总控返回修改内容、确认依据、验证证据、提交与发布状态、未验证项和恢复条件。
   - 当前 Plugin 交付后停止，不自行开始下一个 Plugin 或其他平台适配。
   - 完成条件：独立调用时用户能够对适用动作作出选择；受控调用时上层总控获得继续编排所需的完整状态。

## Delivery

最终输出必须包含：

- Plugin 目标、已完成范围和明确排除项；
- 新增、修改、删除和迁移内容；
- Claude Code 与 Codex 的 Manifest、调用、安装和验证差异；
- 共享镜像清单、规范源及必要链接，以及 Skill 子任务的 `build-skill` 验收结果；
- 实际运行的命令与结果；
- 版本、Marketplace 或发布状态；
- 已验证、未验证，以及无法完成的内容和原因。

其余交付细节遵循 `workflows/§07-delivery.md`，并用 `templates/plugin-delivery-report.template.md` 组织报告；独立调用提问后停止，受控调用返回上层总控后停止。

## Guardrails

- 保护代码、凭据、用户数据、仓库权限和外部服务权限。
- 用户确认设计前保持只读；实施确认不自动授权提交、推送、发布、删除、上线或提高权限。
- 独立调用在实现和验证完成后必须主动询问适用的交付动作；受控调用不得重复询问或执行，由上层总控统一管理。任何模式都不得列出目标仓库或平台并不存在的动作。
- 引入 MCP、Hooks、可执行脚本、网络访问、认证、遥测或持久化前，明确权限和数据流。
- 跨 Skill 运行依赖不得依赖客户端保留软链接；使用清单声明的普通镜像，并拒绝内容漂移。
- 必要符号链接只允许相对路径，并且最终目标必须位于当前 Plugin 根目录内。
- 不另行改写 `build-skill` 已经负责的 Skill 规范；通过委派、规范源和确定性镜像复用。
- 不把静态文件存在描述为真实安装或调用已经通过。
- 不为 Claude Code 与 Codex 复制两套相同工作流；只隔离真实的平台差异。
- 当前不声明其他 Coding Agent 的兼容性。

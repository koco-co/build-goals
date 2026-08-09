---
name: building-skills
description: 由用户显式调用的 Agent Skill 构建与升级工作流。用于从零设计、实现和验证通用 Skill 或项目级定制 Skill，也用于审查并重构已有低质量 Skill；当前适配 Claude Code 与 Codex。不要因普通提示词润色、文档编写或一般编码请求自动进入本 Skill。
compatibility: 当前适配 Claude Code 与 Codex；运行内置机械校验需要 Python 3.9 或更高版本。
disable-model-invocation: true
metadata:
  author: koco-co
  version: "1.1.0"
---

# Outcome

将一个明确的 Skill 需求转化为结构精简、行为可靠、能够真实运行和验证，并适配目标 Agent 平台的完整实现。

## Routing

- 用户明确调用 `building-skills` 并要求新建通用 Skill 时，执行“通用 Skill”分支。
- 用户明确调用 `building-skills` 并提供目标项目时，执行“项目级定制 Skill”分支，先探索项目再设计接入方式。
- 用户明确调用 `building-skills` 并提供已有 Skill 时，执行“审查与升级”分支，先建立现状基线再提出变更。
- 用户要求构建、打包、安装、迁移或发布 Plugin 时，转交 `building-plugins`；本 Skill 只处理其中需要新建或升级的 Skill。
- 用户只要求润色提示词、编写普通文档或处理与 Skill 无关的任务时，不进入本 Skill。
- 无法确认是否为显式调用时，不推断触发；要求用户明确调用 `building-skills`。

## Steps

1. 查明事实
   - 完整读取 `workflows/§01-research.md`。
   - 读取用户已提供的需求、目标 Skill、目标仓库、现有规则和可用工具。
   - 对项目级 Skill，探索项目架构、CLI、测试、Hooks、文档和既有约定。
   - 对已有 Skill，记录当前输入、输出、行为、依赖、已知问题和兼容接口。
   - 调研目标平台规范以及同类实现；用户明确免除外部竞品调研时，仍需核对目标环境和平台契约。
   - 不向用户询问能够从环境、代码或文档中自行查明的事实。
   - 完成条件：形成现状与约束摘要，清楚区分已确认事实、合理推断和未知项。

2. 确认关键决策
   - 完整读取 `workflows/§02-clarification.md`。
   - 只询问无法从环境确定，并且不同答案会改变结构、行为或验收结果的决策。
   - 每轮只询问一个主要问题，同时给出推荐答案、推荐理由及其他选择的影响。
   - 已在提示词、代码、文档或此前回答中明确的内容不得重复询问。
   - 不存在真实未决问题时，明确记录“无待确认决策”，直接进入设计。
   - 完成条件：目标、非目标、Skill 类型、触发方式、输入、输出、分支、权限边界和验收标准均已明确。

3. 提出设计并等待确认
   - 完整读取 `workflows/§03-design.md`。
   - 设计前读取 `rules/architecture.md`、`rules/quality-standard.md` 和 `rules/platform-compatibility.md`。
   - 使用 `templates/design-proposal.template.md` 组织方案；需要参考粒度时，按 Skill 类型读取对应示例。
   - 输出 `tree` 风格目录、文件职责、按需读取关系、机械校验、语义验收、平台适配和 Hooks/CLI 归属建议。
   - 设计必须解释为何保留每个目录；不为形式完整创建空目录或占位文件。
   - 设计完成后只请求一次实施确认。用户确认前不得创建、修改、移动或删除目标文件。
   - 完成条件：用户明确确认实施范围和验收标准。

4. 执行
   - 完整读取 `workflows/§04-implementation.md`。
   - 使用 `templates/skill.template.md` 作为 `SKILL.md` 的结构基线，不得删除其中的核心章节。
   - 优先复用仓库已有 CLI、校验器、测试和公共能力；只有确有缺口时才新增 Skill 内脚本。
   - 将确定性处理交给代码，将固定结构交给模板，将输出范式交给 Few-shot，将不可机械判断的要求交给规则和清单。
   - 保持单一规范源；平台差异集中在 Manifest、适配文件或安装过程，不复制两套核心工作流。
   - 多 Agent 提示文件必须使用 `<name>.agent.md`，不得继续创建 `*.prompt.md`。
   - 只修改已确认范围内的文件，不留下空文件、空目录或无真实用途的占位内容。
   - 完成条件：设计中的全部目标项已实现，文件引用闭合，未引入未经同意的破坏性变化。

5. 验证
   - 完整读取 `workflows/§05-validation.md`。
   - 先运行目标仓库已有检查；没有等价能力时，运行 `scripts/validate_skill.py` 或本次实现提供的校验入口。
   - 使用 `checklists/design-review.md` 检查设计落实情况，再使用 `checklists/semantic-acceptance.md` 完成语义与场景验收。
   - 至少验证显式触发、负向不触发、新建通用 Skill、新建项目级 Skill、升级已有 Skill、确认门禁和失败路径。
   - 能够实际运行的平台必须进行真实验证；只能静态检查的平台必须标记为“未完成真实运行验证”。
   - 发现失败时，修复后重新运行受影响检查，不得用文字说明替代验证。
   - 完成条件：机械检查通过，关键场景通过，剩余未验证项和阻塞项均已明确记录。

6. 交付并停止
   - 完整读取 `workflows/§06-delivery.md`。
   - 使用 `templates/delivery-report.template.md` 输出交付报告。
   - 清楚区分“已验证”“未验证”和“阻塞”，不得把文件存在描述为行为已验证。
   - 当前 Skill 完成交付后停止，不得自行开始下一个 Skill 或创建其占位目录。
   - 完成条件：用户能够定位全部变更、复现验证并判断是否验收。

## Delivery

最终输出必须包含：

- 本次目标、已完成范围和明确排除项；
- 最终目录树与每个关键文件的职责；
- 新增、修改、删除及移出 Skill 目录的内容；
- Claude Code、Codex 或其他目标平台的适配差异；
- 实际执行的校验命令、场景、结果和失败修复记录；
- 外部来源与许可证信息；未使用外部来源时明确说明；
- 已验证、未验证和阻塞项；
- 下一步状态，并在当前 Skill 完成后停止。

## Guardrails

- 保护用户代码、凭据、隐私数据和仓库权限，不在示例、日志或报告中泄露秘密。
- 用户确认设计前保持只读；实施确认不等于授权提交、推送、发布、删除或修改仓库权限。
- 遇到删除、覆盖稳定接口、迁移目录、改变触发行为、执行外部副作用或提高权限时，取得对应范围的明确授权。
- 不制造问题、不重复询问、不虚构调研结论，不声称执行了未运行的命令或未完成的平台验证。
- 可机械判断的要求由 CLI、脚本、测试或结构化校验承担；模型判断只处理语义和场景层面的问题。
- 规则冲突时，优先保护数据与权限，其次遵循用户明确约束、目标仓库约定和平台官方契约。
- 发现任务不属于 Skill 构建或升级时及时退出本流程，不把本 Skill 扩张为通用任务代理。

## References

- 开始调研时，完整读取 `workflows/§01-research.md`。
- 识别和询问关键决策时，完整读取 `workflows/§02-clarification.md`。
- 输出目录与实施方案前，完整读取 `workflows/§03-design.md`、`rules/architecture.md`、`rules/quality-standard.md` 和 `rules/platform-compatibility.md`。
- 构建通用 Skill 时，读取 `examples/global-skill.example.md`；构建项目级 Skill 时，读取 `examples/project-skill.example.md`。
- 开始改动文件后，完整读取 `workflows/§04-implementation.md`。
- 验证时，完整读取 `workflows/§05-validation.md`、`checklists/design-review.md` 和 `checklists/semantic-acceptance.md`。
- 需要独立审阅者或 Subagent 时，读取 `prompts/reviewer.agent.md`；不涉及多 Agent 时不要读取。
- 交付时，完整读取 `workflows/§06-delivery.md` 和 `templates/delivery-report.template.md`。

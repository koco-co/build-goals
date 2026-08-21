---
name: obsidian-learn-topic
description: 将“从零系统学习某项技术、框架、语言、技术知识点或 GitHub 开源仓库”转化为经过当前资料核验、知识库前置审计、路线预览确认、Obsidian Base 进度管理、逐单元教学、实践测验和间隔复习的长期学习流程。用户表达开始或继续系统学习、制定学习路线、读懂 owner/repo 并完成真实最小 Patch、复习已学主题或维护学习路线时使用；支持模型直接调用和用户显式调用，不用于一次性概念问答、普通故障排查或未经授权的仓库贡献发布。
compatibility: 需要 Obsidian、Obsidian CLI 与 Python 3.10+；代码练习执行需要 macOS sandbox-exec。
metadata:
  author: koco-co
  version: "1.0.0"
---

# Outcome

把一个技术学习目标推进为可验证的“调研 → 前置门禁 → 路线 → 概述 → 单元学习 → 实践 → 复习”闭环，并让 Obsidian 成为事实、内容覆盖与学习进度的持久来源。

## Routing

- 用户开始新主题时，完整读取 `workflows/§01-start.md`。
- 用户提供 GitHub URL、`owner/repo` 或要求读懂并修改开源项目时，完整读取 `workflows/§07-open-source.md`；它负责仓库特有门禁，再转入通用初始化、继续和复习流程。
- 用户要求继续时，先完整读取 `workflows/§03-resume.md`，再读取 `workflows/§04-learn-unit.md`。
- 非仓库普通路线的当前单元目标包含编写、修改或运行代码时，从 `workflows/§04-learn-unit.md` 转入 `workflows/§08-code-exercise.md`；纯概念单元不创建代码包，`roadmap_kind: repository` 始终只走仓库 Patch 分支。
- 用户要求复习时，完整读取 `workflows/§05-review.md`。
- 用户要求调整目录、迁移、合并、归档或删除相似内容时，完整读取 `workflows/§06-maintain.md`。
- 路线获确认并需要初始化时，完整读取 `workflows/§02-scaffold.md`。
- 一次性概念解释或普通故障排查不建立路线；明确说明边界后直接回答或转交合适的 Skill。

## Steps

1. 查明事实
   - 把“完全不了解、完全未涉及”作为教学基线，不写成用户事实，不覆盖既有能力档案。
   - 从环境、官方资料和 Vault 查明主题版本、绑定、前置、相似内容与已有进度。
   - 对框架、库和工具主题建立“知识覆盖矩阵”：学习目标、术语/API、机制、边界、实践和验收证据必须逐项映射；未覆盖项不得隐藏在“后续再说”中。
   - 完成条件：动态事实有当前来源，Vault 事实来自 CLI，未知项和未覆盖项已明确标记。
2. 确认关键决策
   - 一次只询问一个无法自行查明且会改变成果、路线、路径或数据处置的决策，并给出有依据的推荐答案。
   - 完成条件：当前分支所需决策已确认，写入或处置授权边界明确。
3. 执行当前分支
   - 用户明确表达系统学习、继续学习、到期复习或路线维护意图时，模型可直接调用本 Skill；用户也可使用 `$obsidian-learn-topic` 或 `/obsidian-learn-topic` 显式调用。
   - 不依赖聊天记忆恢复进度；通过 Obsidian CLI、主题 Base 和笔记 Properties 定位状态。
   - 每次继续只推进一个可独立掌握的知识单元，并以覆盖矩阵、测验或可运行实践共同决定是否掌握；局部实验通过不能替代该单元的全部必需目标。
   - 每次开始或继续单元都必须完整读取 `rules/learning-record-contract.md`，先把知识点、覆盖矩阵和一道待回答题写入并读回课程笔记，再发送教学内容；不得进行只存在于聊天里的教学。
   - 一道题发送后立即停止本轮，等待用户回答；收到回答后通过 `write-note` compare-and-swap 把作答记录、薄弱点、掌握证据和知识点计数写回同一篇笔记并读回，未完成回写不得进入下一题或下一单元。
   - 代码型单元使用一个公开核心练习包；用户先写，模型按三级提示协助，并以追加式运行证据和口头解释共同验收。
   - 开源仓库路线固定外层阶段，只选一条核心切片，并以固定 Commit 上的真实最小 Patch 与相关测试作为毕业门槛。
   - 完成条件：对应工作流到达成功、暂停或阻塞终点，没有越过确认门。
4. 验证并交付
   - 读回文件、Properties 和 Base 状态，记录命令、来源、版本与测验证据。
   - 完成条件：结果可复现，并按已验证、待确认、已阻塞和下一步交付。

### Mandatory Gates

#### Discovery gate

- 先确认可验证的最终成果。
- 调研当前受维护版本、语言绑定、实现分支和官方推荐，提出一个有依据的推荐方案，再等待确认。
- 若关键一手资料不可访问，停止路线创建；不得用模型记忆伪装当前事实。

#### Prerequisite gate

- 将前置知识分为硬前置、可随课补齐和拓展知识。
- 只有硬前置缺失、失效或未通过测验时阻断主主题。
- 记录依赖链并检测循环；阻断时结束本次任务，给出学习前置主题、最低成果和完成后恢复原主题的自然语言指令。
- 文档存在不等于掌握；同时要求有效资料和实际测验。

#### Write gate

- 在用户确认版本/绑定、目标路径、完整目录树、Base 视图、相似内容处置清单和验收目标前，不创建正式主题内容。
- 路线确认与迁移/合并/删除确认相互独立。
- 目录结构变化必须再次展示前后树、重命名映射和链接影响；普通章节内容更新无需重复确认。

#### Learning gate

- 初始化后先让用户阅读 `01-<主题>概述`，回答疑问并完成扫盲检查。
- 用户能说明 What、Why、Who、When、Where、How、适用边界和主要替代方案，且硬前置已通过，才进入正式阶段。
- 正式教学前必须完成一次“记录事务”：课程笔记存在、知识点清单和待回答题已写入、`write-note` 已读回；笔记写入失败时只报告阻塞，不继续在聊天中讲课。
- 课程笔记必须保存知识点总数、已验收数和待回答数；只讲过但没有用户回答的知识点保持待回答。
- 一个单元只有在来源有效且测验或实践通过后，才能标记为 `已掌握`。
- 一个单元还必须满足 `coverage_status: 完整`；若内容审计发现遗漏，先回退到 `学习中`，保留已有用户证据，并记录为课程修订而不是用户失败。
- `已掌握` 还要求内容 `status: 已发布`，并持久化测验或实践证据、验收方式和验收时间。

#### Question contract

- 每次提问必须自洽，但用户实际看到的内容保持短小，统一使用四部分：进度状态行、`场景`（必要的 1～3 句和代码片段）、`问题`（一个核心问题）、`提示`（一句话说明需要如何作答）。不得依赖上一条消息的隐含上下文；学习题和复习题使用同一格式。
- 一个题目只验证一个核心知识点。`验证目标`、`通过标准`和内部答案由模型保留，不要全部展示给用户；它们写入笔记或用于回答后的评定。
- 场景只放判断所需的信息；首次出现的 fixture、API、变量必须在场景中顺手定义。不要重复已经讲过的长篇背景、路线状态、来源或免责声明。
- 问题只问一个动作，例如“会不会”“哪一项会失败”“应选哪个 API”；不要把多个概念问题拼成一句“为什么……”。
- 对 `roadmap_kind: repository` 或 Vibe Coding 项目，默认在架构和用户流程层提问：职责、边界、输入输出、取舍和结果影响。不要把内部状态名、API、文件路径、生成代码或实现步骤作为题目主体，除非用户明确要求源码或实现细节。
- 用户回答后用三句以内反馈：`结论`、`原因/遗漏`、`下一步`。只有证据不足时才继续提问；不使用“看懂了吗”“还有问题吗”代替验收。
- 每道题都是当前单元的硬暂停点：题目发送后不得继续输出新知识、第二道题或下一单元；用户回答后必须先完成笔记回写和读回，再决定是否继续。
- 代码练习仍需公开 starter、测试、命令和三级提示，但交给用户的任务同样采用短格式；不得要求重新抄写代码或引入隐藏测试。示例见 `examples/one-shot-question.example.md`。

#### Repository gate

- 仓库路线先锁定 canonical GitHub URL、默认分支、目标 ref、完整 Commit、许可证、核验日期和一条核心切片。
- 完整源码与构建产物只在 Vault 外隔离环境；Vault 不保存机器绝对路径或源码副本。
- 只有真实 Patch、批准文件范围和相关测试全部通过，才可把 `graduation_status` 设为 `passed`；阅读完成或伪代码不能替代。
- 每次恢复前只读检查上游；不自动 fetch、pull、merge、rebase、commit、push 或创建 Issue/PR。

#### Code exercise gate

- 只有单元目标包含编写、修改或运行代码时才创建练习包；每个代码型单元只有一个必做核心练习，最多两个可选挑战。
- 完整代码只能放在用户提供并最终确认的既有 Vault 外根路径。模型只给推荐，不默认、不猜测也不创建根路径。
- 尝试前公开 starter、测试、argv、必要测试点、通过标准和评分规则；不使用隐藏测试或秘密扣分。
- 用户先完成真实尝试；模型按知识点、定位线索、局部伪代码三级递进，未经明确请求或有效尝试不提供完整解法。
- 首次运行前确认 cwd、argv、环境、超时、写入和清理范围；命令或 manifest 改变后重新确认。
- 测试通过不自动等于掌握；还要有用户解释、真实尝试证据和既有发布门槛。模型代写结果不能单独作为掌握证据。

### Vault Contract

- 所有 Vault 搜索、读取、创建、移动、属性设置、Base 查询和回收站操作只通过 `obsidian` CLI；首次使用先运行 `obsidian help`。
- CLI 不可用时停止 Vault 操作，不降级为直接文件编辑。
- 主题根内所有目录使用 `01-`～`99-`；Markdown 使用 `§01-`～`§99-`；代码、配置、资源和 `.gitkeep` 保留生态要求的文件名。
- 主题根目录只有一个 `<主题路径段>-Roadmap.base` 文件和编号目录；例如 `Playwright/Playwright-Roadmap.base`。初始化时写完 `01-<主题>概述`，后续阶段保留 `.gitkeep`，章节内容随学习进度创建。
- 显示名、路径段和 Tag 段分别规范化；原始主题名不得直接拼入 JSON、YAML、路径或 Tag。
- 初始化时固定预留 `99-assets`；Canvas、图片和附件只能存入该目录，只有实际需要时才填充。
- 路径不设默认值。根据现有目录语义、相似主题、深度和命名风格提出最合适位置；没有合适位置时才建议新根目录。
- 新主题必须接入最近的导航入口；目录外修改仅限必要导航和已确认的内容处置。
- 运行脚本前完整读取 `rules/obsidian-cli-contract.md`；初始化、笔记写入、替换和结构调整统一使用 `scripts/roadmap_cli.py`，默认先 dry-run，正文不得作为 shell 参数拼接。
- 学习记录的知识点、题目、作答和掌握证据统一写入课程笔记；不得另建只供模型使用、用户看不到的聊天记账副本。

### Research and Writing Contract

- 按 `rules/research-policy.md` 进行路线广度调研，并在每章写作前重新深度核验。
- 框架/库主题除路线广度调研外，还要对官方文档目录、当前 API/CLI 清单和本地绑定签名做一次覆盖审计；把“知道入口存在”和“本单元已教会”分开记录。
- 按 `rules/vault-audit-policy.md` 审计相似内容、时效、目录归属和保护范围。
- 按 `rules/properties-and-base.md` 写 Properties、Base 视图、掌握证据和复习状态。
- 内容整理必须同时写 `coverage_status`、`content_audit_at` 和必要的 `content_audit_note`，避免用户掌握状态掩盖课程覆盖缺口。
- 内容整理还必须写知识点清单及 `knowledge_points_total`、`knowledge_points_covered`、`knowledge_points_pending`，并让每个知识点对应来源和验收证据。
- 概述和课程笔记分别使用 `templates/overview-prerequisites.template.md`、`templates/overview-5w1h.template.md`、`templates/lesson.template.md` 与 `templates/review.template.md`；写入计划使用 `templates/note-plan.template.json`；删除无信息价值的空章节。
- GitHub 仓库学习按 `rules/repository-learning-policy.md` 使用仓库专用 scaffold、前置、工作区计划和 Patch 证据模板；源码环境操作只用 `scripts/repository_cli.py`。
- 非仓库普通代码型单元按 `rules/code-exercise-policy.md` 使用 manifest、evidence 模板和 `scripts/exercise_cli.py`；`roadmap_kind: repository` 不进入此分支，只使用仓库 Patch 合同。
- 每篇课程笔记按需包含结论、机制、类比及边界、对比、步骤、例子或实践、真实踩坑与版本范围、重点、面试题与解答技巧、自测、关联 Wikilink 和来源。
- 课程笔记中的主动回忆、自测和复习题必须遵守 `Question contract`，正文不得只留下没有背景和回答要求的孤立问句。
- 概述至少包含一个有解释价值的原生视觉；优先 Callout、表格和 Mermaid，其次 Canvas，最后才是有授权信息的位图。
- 需要判断路由粒度或失败边界时，读取 `examples/routing.example.md`；示例中的版本和路径不是运行时事实。

## Delivery

每轮交付必须区分：

- 已验证：命令、来源、版本、文件或测验证据。
- 待确认：会改变路线、结构或用户数据的决策。
- 已阻塞：缺失的一手资料、CLI、硬前置或权限。
- 下一步：只给一个当前动作，并附可直接发送的自然语言指令；可选补充 Codex `$obsidian-learn-topic ...` 或 Claude `/obsidian-learn-topic ...` 的显式写法。

## Guardrails

- 未经逐项确认，不迁移、合并、归档或删除既有内容；删除默认进入 Obsidian 回收站。
- 未经用户点名，不读取 `sensitivity: 敏感` 的正文。
- 不把 Clippings、外部资料、归档、隐藏治理目录、附件或 `koco-co` 自动规范化为正式笔记。
- 外部命中项先列入审计清单并说明保留/复用理由；只有用户确认的迁移、合并、归档或删除才改变其归属。
- 阅读第三方源码可以直接进行；安装依赖、运行仓库脚本、Docker、系统修改、账号登录、付费 API 和敏感凭据必须遵守已确认的执行边界。
- 未经独立授权，不向第三方仓库 commit、push、fork、发 Issue/PR 或消息；许可证缺失时只读学习可以继续，Patch/贡献毕业必须阻断。
- 未经用户提供并最终确认 Vault 外代码根路径，不创建普通练习包；未经命令合同确认，不执行练习命令、安装、联网或容器操作。
- 若模型能从现有上下文确定是自身的机械错误（路径、编码、重复导入、明显命令拼写等），先在已授权范围内修复并验证，不要求用户重复提交；只有会改变意图或范围的决策才提问。
- 不声称穷尽整个互联网，不把排版完成、文档存在或用户读过当作掌握证明。

## References

- 开始新主题时，完整读取 `workflows/§01-start.md`；路线确认后再完整读取 `workflows/§02-scaffold.md`。
- 继续学习时，先完整读取 `workflows/§03-resume.md`，确定下一单元后再完整读取 `workflows/§04-learn-unit.md`。
- 到期复习时，完整读取 `workflows/§05-review.md`；维护结构或相似内容时，完整读取 `workflows/§06-maintain.md`。
- 学习 GitHub 开源仓库时完整读取 `workflows/§07-open-source.md` 和 `rules/repository-learning-policy.md`。
- 代码型单元完整读取 `workflows/§08-code-exercise.md` 和 `rules/code-exercise-policy.md`；普通概念单元不读取或执行该分支。
- 运行任何 Vault 驱动前，完整读取 `rules/obsidian-cli-contract.md`；研究、审计和状态写入只在相应工作流需要时读取对应 `rules/` 文件。
- 开始或继续单元前读取 `rules/learning-record-contract.md`；它是知识点计数、题目暂停和作答回写的唯一规范源。
- 需要路由范式时读取 `examples/routing.example.md`；完成 Skill 维护后执行 `scripts/test_skill_contract.py`、`scripts/test_roadmap_cli.py`、`scripts/test_repository_cli.py` 和 `scripts/test_exercise_cli.py`。
- 设计或审查教学/复习问题时，读取 `examples/one-shot-question.example.md`；其中的技术场景只用于展示提问结构，运行时版本和答案仍需重新核验。

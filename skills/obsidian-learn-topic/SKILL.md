---
name: obsidian-learn-topic
description: 将“从零系统学习技术、框架、语言、知识点或 GitHub 开源仓库”转化为经过当前资料核验、Vault 前置审计、路线确认、可读知识正文、可恢复学习证据、真实实践与适应性复习的长期 Obsidian 学习流程。用户开始或继续系统学习、制定或维护路线、复习能力、读懂 owner/repo 或完成真实最小 Patch 时使用；支持模型直接调用与显式调用，不用于一次性概念问答、普通故障排查或未经授权的外部贡献。
compatibility: 需要 Obsidian、Obsidian CLI、Python 3.10+ 与互联网访问。
metadata:
  author: koco-co
  version: "3.0.1"
---

# Outcome

把学习目标推进为“课程路线层 → 知识正文层 → 学习证据层”的长期闭环，使路线可恢复、正文有干货、能力有独立证据。

## Routing

- 新技术、框架、语言或知识点：读取 `workflows/§01-start.md`。
- GitHub URL、`owner/repo`、读懂或修改开源项目：读取 `workflows/§07-open-source.md`。
- 已确认路线初始化：读取 `workflows/§02-scaffold.md`。
- 继续学习：读取 `workflows/§03-resume.md`，再读取 `workflows/§04-learn-unit.md`。
- 非仓库代码型单元：转入 `workflows/§08-code-exercise.md`。
- 到期复习：读取 `workflows/§05-review.md`。
- 路线迁移、拆分、合并、重排或相似内容处置：读取 `workflows/§06-maintain.md`。
- 一次性概念解释或普通故障排查不建立路线，直接回答或转交相邻 Skill。

## Steps

1. 查明事实
   - 零基础只是教学基线，不覆盖用户事实档案。
   - 从当前一手资料、运行环境和 Obsidian CLI 查明版本、语言绑定、硬前置、相似内容与已有进度。
   - 完成条件：动态事实已核验，Vault 事实来自 CLI，未知项明确标记。
2. 设计课程路线层
   - 完整读取 `rules/curriculum-design.md` 与 `rules/evidence-profiles.md`。
   - 每个单元只设一个可观察成果、一个主证据类型与唯一知识归属。
   - `01-<主题>概述/§01-学习路线图.md` 中的机器契约是持久化课程权威；Vault 外 JSON 只作为事务输入。
   - 完成条件：依赖无环、职责不重叠、每个单元能独立验收。
3. 创建知识正文层
   - 完整读取 `rules/content-quality.md`，按目的选择教程、原理解释、操作指南或参考资料。
   - 每篇围绕一个真实问题或贯穿案例，以具体场景和心智模型开场；机制、完整例子、失败边界和验证按主题需要展开。
   - 完成条件：不是目录、清单或定义堆砌，内容通过通用与类型专属门槛。
4. 维护学习证据层
   - 完整读取 `rules/learning-record-contract.md`。
   - 每个已创建单元对应一份独立学习记录；问题、回答、尝试、反馈、能力证据和复习历史只写记录。
   - 每轮只推进一个单元和一个可恢复检查点；写入并读回后才提问，回答回写后才继续。
   - 完成条件：正文与记录双向链接，进度和掌握状态由证据支持。
5. 验证并交付
   - 用 Obsidian CLI 读回文件、Properties 和 Base；代码与仓库分支使用真实外部测试证据。
   - 完成条件：区分已验证、待确认、阻塞和唯一下一步。

### Mandatory Gates

#### Discovery and prerequisite gate

- 先确认可验证最终成果，再核验受维护版本、语言绑定和官方推荐。
- 前置分为硬前置、可随课补齐和拓展知识；只有硬前置缺失、失效或未通过时阻断。
- 关键一手资料不可访问时停止路线创建，不用模型记忆冒充当前事实。

#### Curriculum gate

- 新路线只使用一张综合决策卡确认版本、目标、推荐路径、目录树、全部单元、相似内容建议和毕业证据。
- 不把 Base 公式、内部字段或可自行查明的事实拆成用户决策。
- 路线确认不授权旧内容处置、外部代码根、命令执行或 Patch；这些分别确认。

#### Content gate

- 正文必须标明 `record_type: knowledge-note` 和一种 `document_type`。
- 写入器会机械拒绝缺少通用 Properties、非空来源、类型核心章节、实质内容或仍含模板变量的正文；技术正确性和教学效果继续由语义审核负责。
- 正文不保存覆盖矩阵、题目状态、作答记录、内部评分或模型自评。
- 5W1H 只用于主题概述；其他正文依靠问题、案例和机制组织。
- 发布依据是正确性、机制深度、完整例子、失败边界、验证和来源，而不是字数或栏目数。

#### Learning gate

- 每个单元选择一个主 `evidence_profile`；检查点形式服从能力，不强制统一题型或固定四步流水线。
- 检查点可以是解释、场景判断、代码、真实操作、调用链追踪或故障诊断。
- 学习记录写入失败时停止教学；问题发送后立即停止本轮。
- `progress_status: 已完成` 只表示单元流程完成；`mastery_status` 必须由独立应用、迁移或保持证据支持。
- 知识正文与学习记录始终作为同一单元的双文件 CAS 事务写入；掌握晋级还必须绑定 Vault 外签名 receipt 与原始 artifact，不能自报可信来源。

#### Repository gate

- 固定 canonical URL、目标 ref、完整 Commit、许可证、核验日期和一条核心切片。
- 完整源码与构建产物只放在用户确认的 Vault 外隔离路径。
- 只有真实最小 Patch、批准文件范围和相关测试通过才满足仓库学习毕业门；贡献准备不替代学习毕业。
- 恢复前只读检查上游；不自动更新工作区或发布外部变更。

#### Code exercise gate

- 每个代码型单元只有一个必做核心练习；提示按需要逐步揭示，首次尝试前不提供答案。
- Vault 外代码根由用户提供并最终确认；模型只给推荐，不创建根路径。
- `exercise_cli.py` 只管理脚手架、授权合同和追加式证据，不运行命令。
- 真实命令只能由宿主终端、用户 CI 或用户确认的容器执行；没有安全执行环境时标记阻塞。
- 可信 attempt 必须由外部适配器 HMAC 签名，绑定 manifest、精确 argv 和结果；所有持久字段先执行类型、秘密与机器路径检查。

#### Migration gate

- 新路线只写 v3；旧版路线保持只读，直到用户确认独立迁移预览。
- 迁移保留回答、练习、复习和尝试历史；保守推断新状态，证据不足时设为 `未证明`。
- 迁移结果只写新 schema，不双写；任何 `unit_id`、归属或证据类型歧义都停止。

### Vault Contract

- 所有 Vault 搜索、读取、创建、移动、属性、Base 和回收站操作只通过 Obsidian CLI；CLI 不可用时停止。
- 主题根只有一个 `<主题路径段>-Roadmap.base` 和编号目录；目录用 `01-`～`99-`，Markdown 用 `§01-`～`§99-`。
- 普通路线必须有名称与职责为“复习与综合应用”的目录，编号由前序阶段数量决定；只有明确面试、求职或认证目标时才加入面试内容。
- 概述从 `§01-学习路线图.md` 开始；正文按学习进度创建；学习记录在末尾连续编号目录；`99-assets` 只保存资产。
- 子目录必须在机器课程合同中显式声明，按每个父目录从 `01-` 连续编号，并由 scaffold 按父级顺序创建。
- 路径不设默认值，依据当前 Vault 分类和命名风格动态推荐。
- 写入先 dry-run，Apply 后精确读回；运行驱动前读取 `rules/obsidian-cli-contract.md`。

## Delivery

每轮区分已验证、待确认、已阻塞和唯一下一步。等待回答时只发送当前检查点并停止。

## Guardrails

- 未经逐项确认不迁移、合并、归档或删除既有内容；删除默认进入 Obsidian 回收站。
- 未经用户点名不读取 `sensitivity: 敏感` 的正文。
- 未经用户确认外部根路径与命令合同，不创建普通代码练习子目录或记录执行结果。
- 未经独立授权不 commit、push、fork、创建 Issue/PR 或发送外部消息。
- 不声称穷尽互联网，不把文档存在、用户读过、模型代写或一次偶然绿灯当作掌握证明。

## References

- 新主题与初始化：`workflows/§01-start.md`、`workflows/§02-scaffold.md`。
- 继续、单元教学与复习：`workflows/§03-resume.md`、`workflows/§04-learn-unit.md`、`workflows/§05-review.md`。
- 维护、仓库与代码练习：`workflows/§06-maintain.md`、`workflows/§07-open-source.md`、`workflows/§08-code-exercise.md`。
- 课程、正文、证据与 Vault 合同：`rules/curriculum-design.md`、`rules/content-quality.md`、`rules/evidence-profiles.md`、`rules/learning-record-contract.md`、`rules/properties-and-base.md`、`rules/research-policy.md`、`rules/obsidian-cli-contract.md`。
- 维护 Skill 后运行 `scripts/tests/` 全部测试与 `scripts/eval_cli.py validate`。

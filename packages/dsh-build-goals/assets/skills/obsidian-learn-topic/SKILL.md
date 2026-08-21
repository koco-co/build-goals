---
name: obsidian-learn-topic
description: 将“从零系统学习某项技术、框架、语言、技术知识点或 GitHub 开源仓库”转化为经过当前资料核验、知识库前置审计、课程路线确认、分类型知识正文、独立学习证据、实践测验和间隔复习的长期 Obsidian 学习流程。用户表达开始或继续系统学习、制定学习路线、读懂 owner/repo 并完成真实最小 Patch、复习已学主题或维护学习路线时使用；支持模型直接调用和用户显式调用，不用于一次性概念问答、普通故障排查或未经授权的仓库贡献发布。
compatibility: 需要 Obsidian、Obsidian CLI 与 Python 3.10+；代码练习执行需要 macOS sandbox-exec。
metadata:
  author: koco-co
  version: "2.0.0"
---

# Outcome

把技术学习目标推进为“课程路线层 → 知识正文层 → 学习证据层”的长期闭环，让内容可读、知识分配稳定、掌握证据可恢复。

## Routing

- 开始新主题：读取 `workflows/§01-start.md`。
- GitHub URL、`owner/repo` 或读懂并修改开源项目：读取 `workflows/§07-open-source.md`。
- 继续学习：读取 `workflows/§03-resume.md`，再读取 `workflows/§04-learn-unit.md`。
- 非仓库代码型单元：从单元流程转入 `workflows/§08-code-exercise.md`。
- 到期复习：读取 `workflows/§05-review.md`。
- 路线迁移、拆分、合并、重排或相似内容处置：读取 `workflows/§06-maintain.md`。
- 已确认路线初始化：读取 `workflows/§02-scaffold.md`。
- 一次性概念解释或普通故障排查不建立路线，直接回答或转交相邻 Skill。

## Steps

1. 查明事实
   - 零基础只作为教学基线，不写成用户事实。
   - 从当前官方资料、环境和 Obsidian CLI 查明版本、语言绑定、前置、相似内容和已有进度。
   - 完成条件：动态事实有当前来源，Vault 事实来自 CLI，未知项明确标记。
2. 设计课程路线层
   - 完整读取 `rules/curriculum-design.md`。
   - 先定义单项可验收成果和证据，再确定依赖、知识点唯一归属、正文类型和目录。
   - 把完整计划持久化到 `01-<主题>概述/§01-学习路线图.md`；未学习单元不创建空白正文。
   - 完成条件：依赖无环、无重复归属、每个单元都有成果和验收方式。
3. 创建知识正文层
   - 完整读取 `rules/content-quality.md`，按目的选择教程、原理解释、操作指南或参考资料模板。
   - 每篇正文只承担一种主要职责，使用一个贯穿案例或连贯问题，不保存问答流水账与模型评定。
   - 完成条件：通用和类型专属语义质量门槛均通过。
4. 维护学习证据层
   - 完整读取 `rules/learning-record-contract.md`。
   - 每个已创建单元对应一份独立学习记录；所有问题、用户回答、实践、掌握与复习证据只写入记录。
   - 每次只推进一个单元、一道问题；写入并读回后才向用户提问，回答回写后才继续。
   - 完成条件：正文与记录双向链接，掌握判定有分类毕业证据。
5. 验证并交付
   - 通过 Obsidian CLI 读回文件、Properties、Base 和必要 UI 状态；代码与仓库分支运行公开测试。
   - 完成条件：结果可复现，并区分已验证、待确认、阻塞和下一步。

### Mandatory Gates

#### Discovery and prerequisite gate

- 先确认可验证最终成果，再核验受维护版本、语言绑定和官方推荐。
- 前置分为硬前置、可随课补齐和拓展知识；只有硬前置缺失、失效或未通过时阻断。
- 关键一手资料不可访问时停止路线创建，不用模型记忆伪装当前事实。

#### Curriculum gate

- 路线预览包含版本基线、完整目录、全部单元、依赖、知识点唯一归属、正文类型和验收证据。
- 单元采用单项可验收成果；可分别验收的成果必须拆分。
- 先验证 Vault 外课程计划，再把它渲染为学习路线图。

#### Write gate

- 用户确认版本、目标路径、完整目录树、路线图、Base 视图、相似内容建议和验收目标前，不创建路线。
- 路线确认不授权迁移、合并、归档或删除；这些动作逐项确认。
- 目录变化先展示前后树、重命名映射和链接影响。

#### Content gate

- 知识正文必须标明 `record_type: knowledge-note` 和一种 `document_type`。
- 正文不得包含知识点计数、覆盖矩阵、题目状态、作答记录、内部评分和模型自评。
- 发布依据是机制深度、完整示例、边界、验证和来源，不是篇幅或栏目数量。

#### Learning gate

- 初始化后先完成前置和概述单元，再进入正式阶段。
- 教学按“示范 → 补全 → 独立应用 → 迁移验证”推进；一道记忆题不能直接代表掌握。
- 学习记录写入失败时停止教学；问题发送后立即停止本轮。
- 正文发布、内容完整和分类毕业证据同时满足后，学习记录才能标记 `已掌握`。

#### Repository gate

- 固定 canonical URL、目标 ref、完整 Commit、许可证、核验日期和一条核心切片。
- 完整源码与构建产物只在 Vault 外隔离环境。
- 只有真实最小 Patch、批准文件范围和相关测试通过才毕业。
- 恢复前只读检查上游；不自动更新工作区或向上游发布。

#### Code exercise gate

- 代码型单元只有一个必做核心练习，最多两个可选挑战。
- Vault 外代码根路径由用户提供并最终确认；模型只给推荐，不创建根路径。
- 公开 starter、测试、argv、通过标准和提示；用户先尝试，模型代写结果不能单独证明掌握。

### Vault Contract

- 所有 Vault 搜索、读取、创建、移动、属性、Base 和回收站操作只通过 Obsidian CLI；CLI 不可用时停止。
- 主题根只有一个 `<主题路径段>-Roadmap.base` 和编号目录；目录用 `01-`～`99-`，Markdown 用 `§01-`～`§99-`。
- 概述目录从 `§01-学习路线图.md` 开始；正文按学习进度创建；学习记录位于路线末尾连续编号目录；`99-assets` 只保存资产。
- 路径不设默认值，依据当前 Vault 分类和命名风格动态推荐。
- 运行驱动前读取 `rules/obsidian-cli-contract.md`；写入先 dry-run，Apply 后精确读回。

## Delivery

每轮区分已验证、待确认、已阻塞和唯一下一步。等待用户回答时只发送当前一道题并停止。

## Guardrails

- 未经逐项确认不迁移、合并、归档或删除既有内容；删除默认进入 Obsidian 回收站。
- 未经用户点名不读取 `sensitivity: 敏感` 的正文。
- 未经用户确认外部根路径与命令合同，不创建或运行普通代码练习。
- 未经独立授权不 commit、push、fork、创建 Issue/PR 或发送外部消息。
- 不声称穷尽互联网，不把文档存在、用户读过或测试偶然绿灯当作掌握证明。

## References

- 新主题与初始化：`workflows/§01-start.md`、`workflows/§02-scaffold.md`。
- 继续、单元教学与复习：`workflows/§03-resume.md`、`workflows/§04-learn-unit.md`、`workflows/§05-review.md`。
- 维护、仓库和普通代码练习：`workflows/§06-maintain.md`、`workflows/§07-open-source.md`、`workflows/§08-code-exercise.md`。
- 课程、正文、记录、研究与 Vault 合同：`rules/curriculum-design.md`、`rules/content-quality.md`、`rules/learning-record-contract.md`、`rules/research-policy.md`、`rules/properties-and-base.md`、`rules/obsidian-cli-contract.md`。
- 设计问题时读取 `examples/one-shot-question.example.md`；维护 Skill 后运行四个既有专项测试和 `scripts/test_content_architecture.py`。

# 路线 Properties 与 Base 合同

## 笔记 Properties

每篇学习笔记至少包含：

```yaml
title: "标题"
aliases: []
tags:
  - "学习路线/主题"
date: YYYY-MM-DD
updated: YYYY-MM-DD
status: 待核验
category: "所属知识库领域"
note_type: 教程
difficulty: 入门
roadmap_topic: "主题"
roadmap_root: "Vault/相对/主题路径"
learning_goal: "可验证成果"
knowledge_points_total: 0
knowledge_points_covered: 0
knowledge_points_pending: 0
stage_title: "01-带编号的阶段标题"
stage_order: 1
lesson_order: 1
learning_status: 学习中
mastery_score: 0
hard_prerequisites: []
soft_prerequisites: []
blocked_by: []
mastery_evidence: []
assessment_type:
assessment_at:
last_reviewed:
next_review:
review_count: 0
verified_at: YYYY-MM-DD
version_scope: "适用版本"
sources: []
coverage_status: 完整
content_audit_at: YYYY-MM-DD
content_audit_note:
```

`status` 表示内容质量：`草稿`、`待核验`、`已发布`、`已归档`。

`learning_status` 表示学习状态：

- `未开始`
- `学习中`
- `已掌握`
- `阻塞`
- `待复习`
- `已归档`

不得用内容发布状态代替用户掌握状态。

`coverage_status` 表示课程内容覆盖状态，与用户掌握状态分离：

- `完整`：本单元的必需目标、边界、实践和验收证据均已列出并有当前来源。
- `部分覆盖`：已发现有必需目标尚未进入正文或验收；不得仅凭局部证据标记整单元掌握。
- `待核验`：来源、版本或实现边界尚未完成当前核验。

知识点计数表示持久化教学记录，不等于正文段落数量：

- `knowledge_points_total`：本单元计划覆盖的知识点总数。
- `knowledge_points_covered`：用户已经通过题目或实践验收的知识点数。
- `knowledge_points_pending`：已讲解但仍等待用户回答或补测的知识点数。

三者应满足 `covered + pending = total`。聊天中讲过但没有写入笔记的内容不计入 `covered`；回填时先计入 `pending`。

`content_audit_at` 记录最近一次内容覆盖审计日期；`content_audit_note` 记录遗漏、修订和与用户掌握证据的关系。课程遗漏导致回退时保留原 `mastery_evidence`，不把内容缺口归因于用户。

主题的 `§01-前置准备.md` 是持久锚点，额外保存：

```yaml
roadmap_status: 进行中
```

允许值为 `进行中`、`阻塞`、`已完成`、`已归档`。它表示整条路线是否仍应被恢复，与单篇笔记的 `learning_status` 分离；单元刚完成、下一篇尚未创建时，主题仍保持 `进行中`。

开源仓库路线的锚点额外保存 `roadmap_kind: repository`、canonical 仓库身份、默认分支、目标 ref、完整 Commit、许可证、核验日期、学习范围、`core_slice`、上游检查状态和 `graduation_status`。`graduation_status` 只允许 `pending`、`blocked`、`passed`，其判定遵守 `rules/repository-learning-policy.md`；普通主题无需这些字段。

## 掌握与复习

- `mastery_score` 使用 0～100，只能依据短测、主动回忆或实践证据更新；`85` 仅是 Base 中“稳固”的显示分界，不替代每个单元正文定义的通过标准。
- `mastery_evidence` 保存到当前笔记测验结果、小型实验或实验笔记的 Wikilink；同时记录 `assessment_type` 与 `assessment_at`。
- 代码型单元的 `mastery_evidence` 同时写明 `exercise_id`、最新有效 `attempt_id`、结果摘要、得分和用户解释验收；不保存 Vault 外绝对路径、完整日志或敏感环境。
- 同一时刻只有当前概述或正式单元为 `学习中`；其他已创建但尚未教学的概述单元为 `未开始`，正式规划项不提前创建笔记。
- 首次掌握后设 `review_count: 0`、`next_review: +1d`；第 1 次通过后设 `review_count: 1`、`next_review: +7d`；第 2 次通过后设 `review_count: 2`、`next_review: +30d`；后续按证据调整。
- 失败时保存薄弱点并缩短间隔，不制造后台提醒承诺。
- 到期且尚未完成复习时，Base 公式将其列入 `待复习` 视图。
- 只有 `status: 已发布`、`coverage_status: 完整`、掌握证据非空且达到该单元通过标准，才可设置 `learning_status: 已掌握`。
- 代码型单元还要求所有必需公开命令有通过证据、用户完成真实尝试并能解释关键实现与边界；模型代写结果不得单独满足掌握门。

## Base 合同

主题根目录只有一个 `<主题路径段>-Roadmap.base`。例如主题目录为 `Playwright/`，Base 文件为 `Playwright-Roadmap.base`。它：

- 只过滤 `roadmap_root` 内的 Markdown。
- 不依赖聊天记忆或文件修改时间猜测掌握状态。
- 至少提供 `学习路线`、`学习中`、`阻塞`、`待复习`、`已掌握`、`待核验` 六个视图。
- 建议提供 `待补齐` 视图筛选 `coverage_status: 部分覆盖`，让课程遗漏不会被用户掌握状态掩盖。
- 显示阶段、单元顺序、掌握分、掌握证据、核验日期、适用版本和复习日期。
- 显示知识点总数、已验收数、待回答数和内容覆盖状态。
- 显示 `coverage_status`、`content_audit_at` 和内容审计说明；至少提供一个筛选 `coverage_status: 部分覆盖` 的 `待补齐` 视图。
- 将 `stage_order * 100 + lesson_order` 作为稳定路线序号。
- `学习路线` 视图按稳定路线序号升序；`stage_title` 使用真实的编号目录名，避免中文标题排序改变阶段顺序。
- Base 暴露锚点的 `roadmap_status`；恢复主题时以它为主，`learning_status` 只定位已创建的当前单元。
- 仓库路线还显示锚点的 Commit、核心切片、上游状态和毕业状态；绝不显示 Vault 外机器路径。

Base 是动态索引，不会显示空目录；空阶段仍由文件树和 `.gitkeep` 保留，直到创建第一篇笔记。

## 发布门槛

技术笔记只有在以下条件全部满足时才可设为 `已发布`：

- 必需 Properties 合法。
- 正文完整，无空标题或模板占位符。
- 至少一个当前一手来源。
- `verified_at` 和 `version_scope` 与正文一致。
- Wikilink 无新增真实断链，且已接入导航。
- 代码或命令按实际运行范围标注验证证据。

全部通过后再用 Obsidian CLI 把 `status` 设为 `已发布` 并读回验证；否则保持 `待核验`，且不得标记为已掌握。

## 资产目录

初始化时在主题根预留 `99-assets`。Canvas、图片或附件只写入该目录；主题根内所有目录仍使用 `01-`～`99-` 前缀，资产文件自身保留格式或工具链要求的名称。

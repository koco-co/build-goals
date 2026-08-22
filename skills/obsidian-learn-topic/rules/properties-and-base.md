# 三层 Properties 与 Base 合同

## 通用 Properties

路线笔记包含 `title`、`tags`、`date`、`updated`、`status`、`category`、`record_type`、`roadmap_topic`、`roadmap_root`、`stage_title`、`stage_order`、`lesson_order`、`verified_at` 和 `version_scope`。

`record_type` 只允许 `curriculum-map`、`knowledge-note`、`learning-evidence`。

## 课程路线图

路线图额外包含 `schema_version: 3`、`roadmap_status`、`learning_goal`、`version_baseline`、`source_checked_at`、`upstream_status` 和 `sources`。正文中的 `learn-topic-curriculum` JSON 块是持久化课程权威；Vault 外计划文件只是生成或迁移事务输入。

开源仓库路线图的机器合同同时保存 provider、canonical 仓库身份、默认分支、目标 ref、完整 Commit、许可证、学习 scope、核心切片、上游检查和 `graduation_status`；Frontmatter 与可见基线必须逐字段投影该合同，不得形成第二套仓库事实。

## 知识正文

知识正文额外包含 `document_type`、`unit_id`、`learning_outcome`、`knowledge_ownership`、前置依赖、`assessment_method`、`evidence_profile`、`evidence_note`、`coverage_status`、内容核验信息和来源。

`status` 表示正文质量，`coverage_status` 表示课程覆盖。正文不保存进度、掌握状态、rubric 分数或用户回答。

## 学习记录

学习记录额外包含 `unit_id`、`content_note`、`progress_status`、`mastery_status`、`evidence_profile`、`mastery_evidence`、验收信息与复习日期。专项 rubric 结果放在证据条目中，不设置通用 `mastery_score`。

## Base 语义能力

主题根只有 `<主题路径段>-Roadmap.base`。Base 名称和视图顺序允许用户调整，但必须提供五类可验证能力：

1. `route`：按课程顺序查看路线、正文与证据。
2. `current`：找到当前学习中的单元。
3. `review-due`：找到到期复习的能力。
4. `blocked`：找到阻塞单元和原因。
5. `evidence`：查看掌握状态及其证据。

默认模板可提供 `待核验`、`待补齐` 等附加视图，但它们不是写入门禁。验证器按精确过滤语义识别能力，不依赖固定中文视图名；根过滤、五项能力都拒绝恒真、恒假、冲突条件和会漏项的额外条件。

## 发布与毕业

正文发布需要类型专属质量、当前一手来源、适用版本、链接和实际验证范围合格。学习毕业需要正文可用、单元流程完成以及主 evidence profile 的独立证据；正文存在、阅读完成或模型评价不能替代。

`99-assets` 只保存 Canvas、图片和附件。学习记录使用路线末尾连续编号目录，不占用 `99`。

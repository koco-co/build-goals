# 三层 Properties 与 Base 合同

## 通用 Properties

所有路线笔记包含 `title`、`tags`、`date`、`updated`、`status`、`category`、`record_type`、`roadmap_topic`、`roadmap_root`、`stage_title`、`stage_order`、`lesson_order`、`verified_at` 和 `version_scope`。

`record_type` 只允许：

- `curriculum-map`
- `knowledge-note`
- `learning-evidence`

## 课程路线图

路线图额外包含 `roadmap_status`、`learning_goal`、`version_baseline`、`source_checked_at`、`upstream_status` 和 `sources`。`roadmap_status` 只允许 `进行中`、`阻塞`、`已完成`、`已归档`。

开源仓库路线图同时保存 canonical 仓库身份、完整 Commit、许可证、核心切片、上游检查和 `graduation_status`。

## 知识正文

知识正文额外包含：

- `document_type`：教程、原理解释、操作指南或参考资料；
- `unit_id`、`learning_outcome`、`knowledge_ownership`；
- `hard_prerequisites`、`soft_prerequisites`、`blocked_by`；
- `assessment_method`、`evidence_note`；
- `coverage_status`、`content_audit_at`、`content_audit_note`、`sources`。

`status` 表示正文质量；`coverage_status` 表示课程覆盖。正文不保存 `learning_status`、掌握分或用户回答。

## 学习记录

学习记录额外包含 `unit_id`、`content_note`、`learning_status`、知识点计数、`mastery_score`、`mastery_evidence`、验收信息和复习日期。学习状态与正文发布状态分离。

## Base

主题根只有 `<主题路径段>-Roadmap.base`。它至少提供：

- `学习路线`：全部三层文件；
- `课程路线`：只显示路线图；
- `知识正文`：只显示 `knowledge-note`；
- `学习记录`：只显示 `learning-evidence`；
- `学习中`、`阻塞`、`待复习`、`已掌握`：只查询学习记录；
- `待核验`、`待补齐`：只查询知识正文。

Base 以 Properties 查询状态，不从文件修改时间或聊天记忆推断。根过滤器必须锁定路线目录，路线序号仍为 `stage_order * 100 + lesson_order`。

## 发布门槛

知识正文只有在类型专属门槛、当前一手来源、版本、Wikilink 和实际代码验证范围均合格时设为 `已发布`。学习记录的掌握门遵守 `rules/learning-record-contract.md`，不能用正文存在或用户读过代替。

## 资产目录

`99-assets` 继续保留给 Canvas、图片和附件。学习记录使用路线末尾连续编号目录，不占用 `99`。

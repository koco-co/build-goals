---
title: "{{TOPIC_DISPLAY}}学习路线图"
aliases: []
tags:
  - "学习路线/{{TOPIC_TAG}}"
date: {{DATE}}
updated: {{DATE}}
status: 待核验
category: "{{CATEGORY}}"
record_type: curriculum-map
schema_version: 3
roadmap_topic: "{{TOPIC_DISPLAY}}"
roadmap_kind: topic
roadmap_root: "{{ROADMAP_ROOT}}"
roadmap_status: 进行中
learning_goal: "{{LEARNING_GOAL}}"
stage_title: "01-{{TOPIC_PATH_SEGMENT}}概述"
stage_order: 1
lesson_order: 1
version_baseline: "{{VERSION_BASELINE}}"
version_scope: "{{VERSION_SCOPE}}"
source_checked_at: {{DATE}}
upstream_status: unchanged
verified_at: {{DATE}}
sources: []
---

# {{TOPIC_DISPLAY}}学习路线图

> [!abstract] 最终成果
> {{LEARNING_GOAL}}

## 版本与资料基线

- 学习基线：`{{VERSION_BASELINE}}`
- 适用范围：`{{VERSION_SCOPE}}`
- 最近核验：`{{DATE}}`
- 上游状态：`unchanged`

## 知识依赖图

```mermaid
flowchart LR
  %% unit: {{UNIT_ID}}
  {{UNIT_ID}}["{{LESSON_TITLE}}"]
  {{DEPENDENCY_COMMENT_LINES}}
```

## 单元目录

| 单元 ID | 阶段与计划文件 | 正文类型 | 单项可验收成果 | 前置单元 | Evidence profile | 验收方式 |
| --- | --- | --- | --- | --- | --- | --- |
| `{{UNIT_ID}}` | `{{NOTE_PATH}}` | {{DOCUMENT_TYPE}} | {{ONE_MEASURABLE_OUTCOME}} | 无 | `{{EVIDENCE_PROFILE}}` | {{ONE_ACCEPTANCE_METHOD}} |

## 知识点唯一归属

| 知识点 ID | 唯一所属单元 |
| --- | --- |
| `{{KNOWLEDGE_POINT_ID}}` | `{{UNIT_ID}}` |

## 机器可读课程合同

<!-- learn-topic-curriculum:start -->
```json
{{CURRICULUM_PLAN_JSON}}
```
<!-- learn-topic-curriculum:end -->

## 路线调整记录

> [!warning] 调整门禁
> 新增、拆分、合并或重排单元前，先展示依赖、编号、Wikilink 和学习记录影响；确认后再用 Obsidian CLI 更新。

## 来源与核验

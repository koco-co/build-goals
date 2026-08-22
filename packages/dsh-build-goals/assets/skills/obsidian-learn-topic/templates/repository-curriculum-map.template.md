---
title: "{{TOPIC_DISPLAY}}学习路线图"
aliases: []
tags:
  - "学习路线/{{TOPIC_TAG}}"
date: {{VERIFIED_AT}}
updated: {{VERIFIED_AT}}
status: 待核验
category: "{{CATEGORY}}"
record_type: curriculum-map
schema_version: 3
roadmap_topic: "{{TOPIC_DISPLAY}}"
roadmap_kind: repository
roadmap_root: "{{ROADMAP_ROOT}}"
roadmap_status: 进行中
learning_goal: "{{LEARNING_GOAL}}"
stage_title: "01-项目概述"
stage_order: 1
lesson_order: 1
version_baseline: "{{FULL_COMMIT}}"
version_scope: "{{VERSION_SCOPE}}"
source_checked_at: {{VERIFIED_AT}}
upstream_status: {{UPSTREAM_STATUS}}
verified_at: {{VERIFIED_AT}}
sources: []
repository_provider: github
repository_name: "{{REPOSITORY_NAME}}"
repository_url: "{{REPOSITORY_URL}}"
repository_default_branch: "{{DEFAULT_BRANCH}}"
repository_target_ref: "{{TARGET_REF}}"
repository_commit: "{{FULL_COMMIT}}"
repository_license_spdx: "{{LICENSE_SPDX}}"
repository_verified_at: {{VERIFIED_AT}}
repository_scope: "{{REPOSITORY_SCOPE}}"
core_slice: "{{CORE_SLICE}}"
upstream_checked_at: {{UPSTREAM_CHECKED_AT}}
graduation_status: pending-evidence
---

# {{TOPIC_DISPLAY}}学习路线图

> [!abstract] 最终成果
> {{LEARNING_GOAL}}

## Commit 与资料基线

- Provider：`github`
- 仓库：`{{REPOSITORY_NAME}}`
- Canonical URL：`{{REPOSITORY_URL}}`
- 默认分支：`{{DEFAULT_BRANCH}}`
- 目标 ref：`{{TARGET_REF}}`
- Commit：`{{FULL_COMMIT}}`
- 许可证：`{{LICENSE_SPDX}}`
- 学习范围：{{REPOSITORY_SCOPE}}
- 核心切片：{{CORE_SLICE}}
- 上游检查：`{{UPSTREAM_CHECKED_AT}}`
- 上游状态：`{{UPSTREAM_STATUS}}`
- 仓库核验：`{{VERIFIED_AT}}`
- 毕业状态：`pending-evidence`

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

## 来源与核验

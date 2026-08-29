# 文档职责目录

本表是选型参考，不是必须创建的清单。先沿用项目已有等价文档及路径；只有当前开发、交接或验收确实需要某项职责且现有文档无法承载时才新增文件。编写某份文档时按需读取对应模板，保留项目原有语言和排版。

| 文档职责 | 建议文件名 | 何时需要 | 模板 |
| --- | --- | --- | --- |
| 项目状态与导航 | `AGENT_BRIEF.md` | 多份开发文档需要稳定入口，或跨会话交接需要当前状态与下一步 | `templates/agent-brief.template.md` |
| 产品需求 | `PRD.md` | 需要记录功能范围、用户流程、输入输出、状态与验收 | `templates/prd.template.md` |
| 路线计划 | `ROADMAP.md` | 存在多阶段、依赖顺序和可验证完成条件 | `templates/roadmap.template.md` |
| 领域术语 | `GLOSSARY.md` | 多份材料对同一术语或 ID 含义存在歧义 | `templates/glossary.template.md` |
| 系统架构 | `ARCHITECTURE.md` | 需要说明模块边界、目录、依赖和结构约束 | `templates/architecture.template.md` |
| 数据模型 | `DATA_MODEL.md` | 核心实体、字段和关系需要机器 Schema 之外的说明 | `templates/data-model.template.md` |
| 架构决策 | `adr/` | 已作出需要长期保留背景、备选与理由的重大决策 | `templates/adr.template.md` |
| 编码约定 | `CODING_STANDARDS.md` | 项目存在无法由格式化器、Lint 或 AGENTS.md 简洁表达的特有规则 | `templates/coding-standards.template.md` |
| 测试策略 | `TESTING_STRATEGY.md` | 多层测试职责、覆盖目标或调试规则需要统一说明 | `templates/testing-strategy.template.md` |
| 环境搭建 | `ENVIRONMENT_SETUP.md` | 开发环境包含多步安装、启动、Lint 或测试流程 | `templates/environment-setup.template.md` |
| 变更记录 | `CHANGELOG.md` | 项目已经维护变更日志，或用户明确要求建立发布/项目变更记录 | `templates/changelog.template.md` |
| 风险与已知问题 | `RISKS_AND_KNOWN_ISSUES.md` | 已知限制、技术债或开放问题需要跨任务跟踪 | `templates/risks-and-known-issues.template.md` |
| 审查取舍 | 对话内汇总 | 外部文档审查需要记录采纳、部分采纳和不采纳理由 | `templates/review-summary.template.md` |

路径由现有项目结构决定。项目没有文档约定且确需新增多份文档时，可建议放入 `docs/` 下按主题分组，但不能仅为匹配模板创建目录层级。

没有机器 Schema 时不为补文档创建 Schema；没有可记录的重大决策时不创建空 ADR；没有持续维护机制时不创建空 CHANGELOG。一个现有文档能够清楚承担多项职责时，在不同章节中承载，不复制第二份正文。

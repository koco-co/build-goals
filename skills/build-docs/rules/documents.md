# 文档职责

规划时读取本表；编写某份文档时只读取对应模板。默认路径位于项目 `docs/`，已有等价文档沿用实际路径。模板规定内容结构；已有文档按相同职责补齐，不强制替换其标题和排版。

| 文档 | 唯一职责与边界 | 模板 |
| --- | --- | --- |
| `PRD.md` | 功能范围、模块、业务实体语义、分阶段输入输出与业务状态机；不决定技术实现，不复制字段字典。 | `templates/prd.template.md` |
| `ARCHITECTURE.md` | 系统分层、目录、模块依赖与结构约束；说明部件如何协作，关键选择链接 ADR。 | `templates/architecture.template.md` |
| `ROADMAP.md` | 有依赖顺序和逐任务 Definition of Done 的开发清单；完成标记对应验收证据。 | `templates/roadmap.template.md` |
| `DATA_MODEL.md` | 核心实体字段、关系和机器 Schema 的可读说明；沿用现有 Schema，冲突列为待确认项。 | `templates/data-model.template.md` |
| `CODING_STANDARDS.md` | 项目特有命名、代码组织、错误处理模式与反模式；引用已有格式化、Lint 配置。 | `templates/coding-standards.template.md` |
| `TESTING_STRATEGY.md` | 单元、集成、端到端的职责、覆盖预期和调试重试规则；执行命令引用环境文档。 | `templates/testing-strategy.template.md` |
| `adr/` | 每个重大决策单独记录背景、选择、备选及理由；保留历史，当前架构引用生效记录。 | `templates/adr.template.md` |
| `GLOSSARY.md` | 领域术语与通用 ID、命名格式的定义；其他文档引用，不各自定义同名概念。 | `templates/glossary.template.md` |
| `AGENT_BRIEF.md` | 简短的当前状态、已完成工作、下一步和全套文档索引；详细规则与历史留在对应文档。 | `templates/agent-brief.template.md` |
| `CHANGELOG.md` | 按日期记录实际实施的工作与确认的决策；区分产品变更与文档整理，不充当未来任务清单。 | `templates/changelog.template.md` |
| `ENVIRONMENT_SETUP.md` | 前置条件、安装启动、Lint 和测试的准确命令及执行目录；区分已有可运行命令与待实现方案。 | `templates/environment-setup.template.md` |
| `RISKS_AND_KNOWN_ISSUES.md` | 已知限制、不稳定点、技术债、开放问题及其影响；记录问题不等于批准修复。 | `templates/risks-and-known-issues.template.md` |

PRD 定义业务状态，架构引用它并补充技术协作；ROADMAP 的任务对应 PRD 范围，验收采用 TESTING_STRATEGY 的验证方式。AGENT_BRIEF 负责导航，不复制这些契约。

没有机器 Schema 时说明字段依据，不为补文档创建 Schema。没有可记录的重大决策时，在文档索引注明 ADR 尚无记录，暂不创建空目录或虚构决策。

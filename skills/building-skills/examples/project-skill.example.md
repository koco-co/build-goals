# 项目级 Skill 示例：`service-release`

本示例强调项目探索和已有能力复用，不代表固定目录模板。

## 场景

目标项目已有：

- `./tools/release` CLI；
- `make verify` 检查入口；
- `.github/workflows/release.yml` 发布流程；
- `docs/release-policy.md` 版本与审批规则。

用户希望构建一个项目级 Skill，帮助准备发布清单、运行预检并生成交付摘要，但不得自动发布。

## 探索结论

- 版本计算、变更日志生成和制品校验已经由 `./tools/release` 实现；
- Skill 不应在自己的 `scripts/` 中复制这些逻辑；
- 每次合并到发布分支后的自动检查属于 CI，不属于 Skill；
- Skill 只负责收集上下文、确认发布范围、编排已有命令、解释结果和生成报告。

## 推荐结构

```text
.agents/skills/service-release/
├── SKILL.md
├── workflows/
│   ├── §01-prepare.md
│   ├── §02-verify.md
│   └── §03-handoff.md
├── templates/
│   └── release-summary.template.md
└── checklists/
    └── release-readiness.md
```

Claude Code 通过项目适配安装到 `.claude/skills/service-release/`，核心文件由同一规范源生成或同步。

## 边界划分

| 能力           | 位置                     | 理由                       |
| -------------- | ------------------------ | -------------------------- |
| 版本与制品校验 | `./tools/release`        | 已有确定性实现             |
| 合并后自动检查 | GitHub Actions           | 必须由事件可靠触发         |
| 发布审批规则   | `docs/release-policy.md` | 项目唯一规范源             |
| 命令编排与解释 | Skill 工作流             | 需要上下文判断             |
| 发布摘要结构   | Skill 模板               | 固定交付格式               |
| 最终发布       | 不在 Skill 默认范围      | 具有外部副作用，需单独授权 |

## 关键 Guardrail

“准备发布”不等于“执行发布”。即使所有检查通过，也只能输出交接摘要；执行发布命令必须获得用户针对本次发布的明确授权。

## 验收场景

1. 能读取项目发布规则而不重复询问版本约定；
2. `make verify` 失败时停止，不生成“可发布”结论；
3. 不复制 `./tools/release` 的业务逻辑；
4. 未授权时不会触发发布工作流；
5. 报告能够区分通过、未验证和阻塞项。

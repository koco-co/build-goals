---
name: health-check
description: 检查项目的 Skill、Plugin、README、AGENTS.md/CLAUDE.md 与正式 PRD；用户要求健康检查或上层流程需要基线/交付复核时使用，不用于代码质量、安全、依赖、测试、CI 或性能审计。
metadata:
  author: koco-co
  version: "1.0.0"
---

# Outcome

先只读检查并一次性报告真实问题，确认后修复、验证并复检。

## Routing

- 独立调用检查五个规范领域：Agent Skill、Plugin、README、AGENTS.md/CLAUDE.md 和正式 PRD。
- 由 `vibe-coding` 受控调用时，只检查上层指定的基线、就绪或最终交付范围；无问题时直接返回。
- 本 Skill 只随完整 `build-goals` Plugin 分发；代码质量、安全、依赖、测试覆盖率、CI 和性能审计不属于本 Skill。

## Steps

1. 读取 `rules/domain-contract.md` 与 `workflows/§01-inspection.md`，保护现场并确定适用范围。
2. 只读调用适用领域 Skill；Plugin 内的 Skills 由 Plugin 领域统一检查，去重后每项只返回问题、证据、修复方案、影响文件和验证方式。
3. 使用 `templates/health-check-report.template.md` 输出一次性报告；无问题时结束，有问题时只请求一次修复确认。
4. 确认后读取 `workflows/§02-remediation.md`，按领域修复、验证并重新运行同一范围的健康检查。
5. 读取 `checklists/semantic-acceptance.md`，交付已修复项、复检结果、未验证项和剩余问题。

## Rules

- 检查阶段只读；只报告有证据的问题，不创建持久化报告或扩张审计范围。
- 不自动 commit、push、发布、部署或更新本地 Plugin。

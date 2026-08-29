---
name: audit-agent-setup
description: 检查项目的 Skill、Plugin、README、AGENTS.md/CLAUDE.md；用户要求项目规范健康检查时使用，不用于代码质量、安全、依赖、测试、CI 或性能审计。
license: MIT
metadata:
  author: koco-co
  version: "3.0.0"
---

# Outcome

先只读检查并一次性报告真实问题，再按用户已有授权修复、验证并复检。

## Routing

- 单独调用本 Skill 时，检查四个规范领域：Agent Skill、Plugin、README、AGENTS.md/CLAUDE.md。
- 用户只要求检查时保持只读并在报告后询问是否修复；用户明确要求检查并修复时，报告后直接修复成立问题，不重复确认。
- 本 Skill 只随完整 `agent-build-kit` 分发包提供；代码质量、安全、依赖、测试覆盖率、CI 和性能审计不属于本 Skill。

## Steps

1. 读取 `rules/domain-contract.md` 与 `workflows/§01-inspection.md`，记录并保留工作区现状，确定适用范围。
2. 只读调用适用领域 Skill；Plugin 内的 Skills 由 Plugin 领域统一检查，去重后每项只返回问题、证据、修复方案、影响文件和验证方式。
3. 使用 `templates/audit-agent-setup-report.template.md` 输出一次性报告；无问题时结束。用户只要求检查时，有问题才请求一次修复确认；用户已明确要求修复时直接继续。
4. 获得修复授权后读取 `workflows/§02-remediation.md`，按领域修复、验证并重新运行同一范围的健康检查。
5. 读取 `checklists/semantic-acceptance.md`，交付已修复项、复检结果、未验证项和剩余问题。

## Rules

- 检查阶段只读；只报告有证据的问题，不创建持久化报告或扩张审计范围。
- 不自动 commit、push、发布、部署或更新本地 Plugin。

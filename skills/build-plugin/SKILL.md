---
name: build-plugin
description: 创建、升级或迁移 Claude Code、Codex Plugin；涉及打包、平台适配、安装或分发时使用，不用于单独构建 Skill 或普通编码。
compatibility: 需要互联网访问和 Python 3.9+ 运行内置静态校验脚本。
metadata:
  author: koco-co
  version: "2.2.0"
---

# Outcome

把明确的插件需求转化为可安装、可验证且权限可控的 Claude Code/Codex Plugin。

## Routing

- 新建、升级或迁移 Plugin 时进入对应分支；双平台需求只维护一份核心内容，分别配置 Manifest。
- Plugin 包含 Skill 时交给 `build-skill`；单独构建 Skill 且没有打包、安装或分发需求时退出并转交。
- 由 `health-check` 受控调用时，审查阶段保持只读；上层取得修复确认后再修复。
- 普通代码、文档或其他平台适配不属于本 Skill。

## Steps

1. 读取 `workflows/§01-research.md`，确认平台、组件、安装、权限、版本和发布事实。
2. 读取 `workflows/§02-clarification.md`，只确认会改变 Plugin 形态或验收的决策。
3. 读取 `workflows/§03-design.md`、`rules/plugin-architecture.md`、`rules/platform-compatibility.md` 和 `rules/security-and-permissions.md`；Plugin 含 Skill 时再读取对应的 `build-skill` 规范，展示设计并等待实施确认；确认前不写入。
4. 读取 `workflows/§04-skill-delegation.md`，将 Skill 子任务交给 `build-skill` 并复核结果。
5. 读取 `workflows/§05-implementation.md`，实现确认组件，保持单一规范源和平台隔离。
6. 读取 `workflows/§06-validation.md`，运行静态校验、安装检查和适用的真实平台场景。
7. 读取 `workflows/§07-delivery.md`，报告文件、版本、验证状态和恢复条件。

## Rules

- 不复制相同工作流，不依赖安装器保留嵌套软链接；共享文件按清单同步并校验。
- Commit、push、Marketplace、发布和本地 Plugin 更新必须分别授权。

# Plugin 设计

## Phase 1：确定插件形态

选择最小可用形态：

```text
Skills-only
MCP-only
Skills + MCP
Skills + Hooks / Agents
Skills + MCP + UI
已有仓库迁移
多平台封装
```

只纳入用户当前需要的组件。

## Phase 2：划分职责

逐项判断应放在：

- Skill：模型驱动、可复用的工作流；
- Agent：具有独立角色、工具和返回格式的子任务；
- Hook：必须由固定事件自动触发的行为；
- MCP：外部工具、服务或数据接入；
- UI：需要交互呈现的 MCP 资源；
- CLI / script：可确定性执行的转换和校验；
- Manifest：身份、组件路径和平台元数据；
- CI：每次提交都必须执行的自动检查。

## Phase 3：设计平台层

多平台方案必须：

- 核心组件只维护一份；
- `.claude-plugin/plugin.json` 只描述 Claude Code 差异；
- `.codex-plugin/plugin.json` 只描述 Codex 差异；
- 目标包含 ZCode 时增加 `.zcode-plugin/plugin.json`，且三份 Manifest 的 name、version 和 Skills 路径一致；
- 跨 Skill 运行依赖使用清单声明的普通镜像，并说明如何同步，以及如何校验镜像内容与规范源是否一致；
- 无法等价实现的能力明确分支或降级。

只设计当前方案实际需要的文件，不为未采用的平台入口、组件或目录创建占位结构。

创建平台 Manifest 时按需读取 `templates/claude-plugin.template.json`、`templates/codex-plugin.template.json` 或 `templates/zcode-plugin.template.json`；模板只提供字段结构，不扩大组件范围。

## Phase 4：输出方案

使用 `templates/plugin-design-proposal.template.md` 汇总目标、分支、目录、组件职责、Skill 委派、权限、平台、安装发布、验证、实施范围和回滚；不在本工作流重复维护模板字段清单。

输出后只请求一次实施确认。确认前保持只读。

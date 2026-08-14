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
双平台封装
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

双平台方案必须：

- 核心组件只维护一份；
- `.claude-plugin/plugin.json` 只描述 Claude Code 差异；
- `.codex-plugin/plugin.json` 只描述 Codex 差异；
- 跨 Skill 运行依赖使用清单声明的普通镜像，并设计同步与漂移校验；
- 无法等价实现的能力明确分支或降级。

只设计当前方案实际需要的文件，不为未采用的平台入口、组件或目录生成占位骨架。

## Phase 4：输出方案

使用 `templates/plugin-design-proposal.template.md`，至少包含：

- 目标与非目标；
- 输入、输出和主要分支；
- `tree` 风格目录；
- 每个文件、共享镜像与必要链接的职责；
- Skill 子任务及委派方式；
- 权限和数据流；
- 安装、更新和发布方式；
- 机械检查、语义验收和真实客户端测试；
- 实施范围与回滚方式。

输出后只请求一次实施确认。确认前保持只读。

# 调研与现状探索

## Phase 1：读取任务

整理用户已经明确的目标、非目标、平台、仓库、组件、交付物、权限和验收条件。不要把已知内容重新变成问题。

## Phase 2：探索仓库

对新建任务检查目标目录；对升级或迁移任务完整检查：

- `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`；
- `skills/`、`agents/`、`hooks/`、`.mcp.json`、`.app.json`、UI、脚本和测试；
- Marketplace、安装脚本、CI、版本和发布配置；
- 现有 CLI、公共模块和可复用校验器；
- 软链接、子模块、生成文件及其安装后行为。

记录当前可用能力、重复实现、失效路径、兼容接口和潜在破坏性变化。

## Phase 3：核对平台契约

只核对本次目标平台：

- Claude Code：Manifest、组件目录、命名空间、权限、缓存、软链接、安装和验证；
- Codex：Manifest、Skills、MCP、Hooks、Marketplace、调用策略和安装表面。

平台规范可能变化，实施前以当前官方文档和本地客户端行为为准。其他 Coding Agent 只记录为后续项。

## Phase 4：整理结果

输出：

```text
已确认事实
合理推断
仍需决定
发现的问题
可复用能力
平台差异
风险与边界
```

完成条件：足以决定插件形态和设计范围，且没有把可自行查明的事实留给用户回答。

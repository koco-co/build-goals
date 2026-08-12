# Plugin 平台兼容规则

## 当前范围

当前只支持：

- Claude Code；
- Codex。

其他 Coding Agent 不写入兼容声明，不创建空 Manifest。

## Claude Code

- Manifest：`.claude-plugin/plugin.json`；
- 仓库 Marketplace：`.claude-plugin/marketplace.json`；
- Skills：Plugin 根目录 `skills/`；
- 调用：`/<plugin-name>:<skill-name>`；
- 本地加载：`claude --plugin-dir <plugin-root>`；
- Marketplace 安装：`claude plugin marketplace add <owner>/<repo>@<ref>`，再执行 `claude plugin install <plugin-name>@<marketplace-name>`；
- 官方校验：`claude plugin validate <plugin-root> --strict`；
- 仅限用户调用的 Skill 使用 `disable-model-invocation: true`；允许模型调用时不设置该字段，并优先在跨平台 `description` 中写清触发条件和排除条件。

## Codex

- Manifest：`.codex-plugin/plugin.json`；
- Skills：Plugin 根目录 `skills/`；
- 调用：`$<skill-name>`；
- 调用权限：仅限用户调用时，在 `agents/openai.yaml` 中设置 `allow_implicit_invocation: false`；允许模型调用时使用默认值或设为 `true`，并在 `description` 中写清触发条件和排除条件；
- 仓库 Marketplace：`.agents/plugins/marketplace.json`；
- Manifest 组件路径以 `./` 开头，并相对 Plugin 根目录解析。

## 双平台

- `name` 与 `version` 默认保持一致；
- 共用组件只维护一份；
- Manifest 分开维护；
- Claude 专属 Frontmatter 与 Codex 适配文件可以同时存在于共用 Skill 源；
- Codex 独立安装副本只保留通用 Agent Skills Frontmatter，完整移除 Claude 专属字段及其嵌套内容；
- 独立安装时，由安装器生成平台专用副本；
- 平台无法支持的能力必须明确分支或降级。

## 软链接

软链接目标在 Plugin 根目录内时可以复用。发布前验证平台安装、缓存或打包后的实际解析结果。只有静态检查时，不声称客户端已经支持。

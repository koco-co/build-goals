# Plugin 平台兼容规则

本文件必须随 `build-plugin` 独立安装并保持自包含，不依赖兄弟 Skill 或原始仓库路径。平台能力会持续演进；实施前仍需核对目标平台当前官方契约。

## 当前范围

当前通用构建流程支持 Claude Code、Codex、ZCode 与 Pi。其他 Agent 平台只有在发现方式、Manifest、调用策略、安装和验证契约均已查明后才能加入；不能只创建空 Manifest 并宣称兼容。

## 平台入口

| 平台 | Manifest | Marketplace | 调用策略 |
| --- | --- | --- | --- |
| Claude Code | `.claude-plugin/plugin.json` | `.claude-plugin/marketplace.json` | Claude Code 专用 Frontmatter |
| Codex | `.codex-plugin/plugin.json` | `.agents/plugins/marketplace.json` | `agents/openai.yaml` |
| ZCode | `.zcode-plugin/plugin.json`（优先探测） | 复用 `.claude-plugin/marketplace.json` | 无独立适配文件 |
| Pi | `package.json` 的 `pi` 对象 | Git 或 npm Package | Skill Frontmatter |

组件仍位于 Plugin 根目录。Manifest 中的组件路径使用以 `./` 开头、相对 Plugin 根目录解析的路径，不把 Skills、Hooks 或资源塞进 Manifest 目录。

## 多平台规范源

- 各平台 Manifest 的 `name`、`version` 默认保持一致，Manifest 分开维护。
- 共用 Skill 的核心工作流、规则、模板、示例和脚本只维护一份。
- Claude Code 专用字段与 Codex 的 `agents/openai.yaml` 可以同时存在于共用源；独立安装时再生成平台专用副本。
- Codex 独立副本只保留通用 Agent Skills Frontmatter，并完整移除 Claude Code 专用字段及其嵌套内容。
- ZCode 优先读取 `.zcode-plugin/plugin.json`，再回退到 `.claude-plugin/` 和 `.codex-plugin/`；ZCode 市场按探测顺序读取 `.claude-plugin/marketplace.json` 或根目录 `marketplace.json`。
- ZCode 只识别 `name`、`description`、`when_to_use`、`license` 和 `metadata` 等 Skill Frontmatter 键，未识别的键在加载时被忽略，不阻塞加载。
- ZCode 独立副本保留完整 Frontmatter 并移除 `agents/`。
- Pi Package 通过 `pi.skills` 指向共用 Skill 根目录；Pi 读取 `disable-model-invocation` 并忽略其他不识别的 Frontmatter 字段。
- Pi 独立副本保留完整 Frontmatter 并移除 `agents/`。
- 平台缺少等价能力时明确记录降级或退出条件，不伪造兼容行为。

## Pi Package

Pi Package 的 `package.json` 至少声明名称、版本、非空描述和 `pi.skills`。通过 Git 分发时使用 `pi install git:<host>/<owner>/<repo>`，通过本地路径验收时使用 `pi install <absolute-path>`；安装后用 `pi list` 核对，并在交互会话中确认 Skill 发现与调用。`pi-package` keyword 用于包检索，不替代 `pi` Manifest。

## 共享文件与链接

跨 Skill 运行依赖不得假设客户端安装缓存会保留嵌套软链接。确需保留 Skill 内本地入口时，使用共享文件清单声明唯一规范源和普通镜像，并通过同步脚本逐字节校验。

必要符号链接必须使用仓库内相对路径，最终解析位置仍在 Plugin 根目录。发布前检查真实安装产物；源仓库静态通过不能代替客户端加载结果。

## 验证结果

交付报告分别记录共用源静态检查、各平台 Plugin Manifest 与 Pi Package 检查、真实安装或加载结果，以及没有运行的平台和原因。

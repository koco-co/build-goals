# 平台兼容规则

平台能力会持续演进。实施平台专属配置前，重新核对目标平台当前官方文档；本文件只规定隔离方式，不替代平台契约。字段选择遵循 `rules/frontmatter.md`。

## 1. 多平台规范源

本仓库当前直接作为 Claude Code、Codex 与 ZCode Plugin 及 Pi Package 使用，因此 `skills/*/SKILL.md` 是各平台共用的规范源：

- 通用字段遵循 Agent Skills 规范；
- Claude Code 的调用权限字段保留在共用源中；
- Codex 的调用策略保留在 `agents/openai.yaml`；
- 核心工作流、模板、示例、规则、脚本和清单只维护一份；
- Plugin Manifest 分别放在根目录 `.claude-plugin/`、`.codex-plugin/` 与 `.zcode-plugin/`，Pi Package 配置放在根目录 `package.json`。

独立安装器会生成平台专用副本，字段分类遵循 `rules/frontmatter.md`：

```text
多平台 Skill 源
├── Claude Code：保留通用字段和 Claude Code 字段，移除 agents/
├── Codex：只保留通用 Agent Skills 字段，保留 agents/openai.yaml
├── ZCode：保留全部字段（未识别的键被忽略），移除 agents/
└── Pi：保留全部字段（未识别的键被忽略），移除 agents/
```

## 2. Claude Code

Plugin Manifest：

```text
.claude-plugin/plugin.json
```

仓库 Marketplace：

```text
.claude-plugin/marketplace.json
```

Skill 位于 Plugin 根目录的：

```text
skills/<skill-name>/SKILL.md
```

仅限用户主动调用时，共用源包含：

```yaml
disable-model-invocation: true
```

其他 Claude Code 专属字段只有在 `rules/frontmatter.md` 的决策条件成立时才添加。不得因为平台支持就统一补齐。

Plugin 内调用使用命名空间：

```text
/<plugin-name>:<skill-name>
```

开发期本地加载：

```bash
claude --plugin-dir .
```

Marketplace 安装：

```bash
claude plugin marketplace add <owner>/<repo>@<ref>
claude plugin install <plugin-name>@<marketplace-name> --scope user
```

平台侧验证：

```bash
claude plugin validate . --strict
```

## 3. Codex

Plugin Manifest：

```text
.codex-plugin/plugin.json
```

仅限用户主动调用时，Skill 的 Codex 适配文件包含：

```yaml
# agents/openai.yaml
policy:
  allow_implicit_invocation: false
```

用户调用：

```text
$<skill-name>
```

仓库 Marketplace 位于：

```text
.agents/plugins/marketplace.json
```

核心工作流不得复制到 Codex 适配文件。

生成 Codex 独立安装副本时，只保留通用 Agent Skills Frontmatter：

```text
name, description, license, compatibility, metadata, allowed-tools
```

Claude Code 专属字段及其嵌套 YAML 内容必须完整移除；不能只删除字段首行而遗留子项。

## 4. Pi

Pi Package 在根目录 `package.json` 的 `pi.skills` 中声明 Skill 目录；没有 Manifest 时也会从约定目录 `skills/` 自动发现。完整包通过以下命令安装：

```bash
pi install git:github.com/<owner>/<repo>
```

用户通过 `/skill:<skill-name>` 调用。Pi 读取 Agent Skills 通用 Frontmatter 和 `disable-model-invocation`；后者为 `true` 时不向模型公布 Skill，只允许用户显式调用。Pi 会忽略其他不识别的 Frontmatter 字段，因此完整 Package 可以直接加载共用源。用户级独立副本安装到 `~/.pi/agent/skills/<skill-name>/`，项目级副本安装到 `.pi/skills/<skill-name>/`；两者都保留共用 Frontmatter 并移除 Codex 的 `agents/`。

安装后使用 `pi list` 核对 Package，并在交互会话启动信息或 `/reload` 后确认 Skills 被发现；再分别验证显式调用、应自动触发和不应自动触发的场景。

## 5. 共享文件与软链接

已在 Codex 的实际 Plugin 安装缓存中观察到嵌套软链接被省略，因此多平台 Plugin 的跨 Skill 运行依赖不应依赖软链接。优先使用同一路径直接共用；确需保留 Skill 内本地入口时，使用清单声明、脚本同步和逐字节校验的普通镜像。

项目级 `CLAUDE.md` 应为普通文件，内容精确为 `@AGENTS.md`，不使用符号链接。受控构建流程中其他必要软链接必须同时满足：

- 使用相对路径；
- 目标真实存在；
- 最终解析位置仍在当前 Plugin 根目录；
- 不指向凭据、用户目录、系统目录或仓库外文件；
- CI 能够检查链接目标；
- 安装或打包后仍能读取目标内容。

普通镜像不是第二个规范源；清单必须标明规范源，校验器拒绝缺失、使用软链接或与规范源内容不一致的镜像。独立安装时仍可在受控临时产物中安全解引用。

项目根目录 `.agents/scripts/` 是项目公共能力位置，不是 Agent Skills 规范保证会随单个 Skill 安装的目录。多个项目级 Skills 可以在项目或整体安装包明确携带该目录时调用其中脚本；独立 Skill 安装、复制或发布无法证明共享目录存在时，必须保留 Skill 自有 `scripts/`，不得留下失效的项目根目录调用命令。Claude Code、Codex 或其他平台能读取项目文件，不等于其 Skill 或 Plugin 安装流程会自动携带该目录，交付验证必须分别证明。

## 6. 其他平台

当前不声明其他 Coding Agent 的兼容性。新增平台前确认：

1. Plugin 或 Skill 的发现方式；
2. Manifest 与 Frontmatter 契约；
3. 用户调用和模型调用的权限控制；
4. 脚本、资源和软链接处理；
5. 安装、缓存、升级与卸载行为；
6. 平台是否拒绝未知字段。

只有真实差异才新增适配。无法提供等价行为时，明确记录降级，不伪造兼容性。

## 7. 验证状态

交付报告分别标明：

- 各平台共用源的静态检查；
- Claude Code Manifest 与真实加载结果；
- Codex Manifest、Marketplace 与真实安装结果；
- ZCode Manifest 与真实加载结果；
- Pi Package、Skill 发现与真实调用结果；
- 未运行平台及其具体限制。

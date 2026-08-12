# 平台兼容规则

平台能力会持续演进。实施平台专属配置前，重新核对目标平台当前官方文档；本文件只规定隔离方式，不替代平台契约。

## 1. 双平台规范源

本仓库当前直接作为 Claude Code 与 Codex Plugin 使用，因此 `skills/*/SKILL.md` 是两个平台共用的规范源：

- 通用字段遵循 Agent Skills 规范；
- Claude Code 的调用权限字段保留在共用源中；
- Codex 的调用策略保留在 `agents/openai.yaml`；
- 核心工作流、模板、示例、规则、脚本和清单只维护一份；
- 平台 Manifest 分别放在根目录 `.claude-plugin/` 与 `.codex-plugin/`。

独立安装器会生成平台专用副本：

```text
双平台 Skill 源
├── Claude Code：保留 disable-model-invocation，移除 agents/openai.yaml
└── Codex：移除 Claude 专属 Frontmatter，保留 agents/openai.yaml
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

## 4. 软链接

同一 Plugin 内重复使用的文件优先通过相对软链接共享。

软链接必须同时满足：

- 使用相对路径；
- 目标真实存在；
- 最终解析位置仍在当前 Plugin 根目录；
- 不指向凭据、用户目录、系统目录或仓库外文件；
- CI 能够检查链接目标；
- 安装或打包后仍能读取目标内容。

不能确认目标平台会保留软链接时，发布流程应在临时产物中安全解引用，而不是复制第二份规范源回仓库。

## 5. 其他平台

当前不声明其他 Coding Agent 的兼容性。新增平台前确认：

1. Plugin 或 Skill 的发现方式；
2. Manifest 与 Frontmatter 契约；
3. 用户调用和模型调用的权限控制；
4. 脚本、资源和软链接处理；
5. 安装、缓存、升级与卸载行为；
6. 平台是否拒绝未知字段。

只有真实差异才新增适配。无法提供等价行为时，明确记录降级，不伪造兼容性。

## 6. 验证状态

交付报告分别标明：

- 双平台共用源的静态检查；
- Claude Code Manifest 与真实加载结果；
- Codex Manifest、Marketplace 与真实安装结果；
- 未运行平台及其具体限制。

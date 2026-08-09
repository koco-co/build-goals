# 平台兼容规则

平台能力会演进。实施平台专属配置前，必须重新核对目标平台当前官方文档；本文件定义隔离原则，不替代官方契约。

## 1. 可移植规范源

仓库中的规范源应优先使用开放 Agent Skills Frontmatter：

- `name`；
- `description`；
- 可选的 `license`、`compatibility`、`metadata`、`allowed-tools`。

平台专属字段不要混入可移植源文件，除非该仓库明确只服务该平台。

核心工作流、模板、示例、规则、脚本和清单保持一份。平台适配层只能描述安装位置、调用策略、展示元数据和平台独有能力。

## 2. Claude Code

常见安装位置：

```text
~/.claude/skills/<skill-name>/SKILL.md
<project>/.claude/skills/<skill-name>/SKILL.md
```

仅限用户主动调用的 Claude 安装副本应包含：

```yaml
disable-model-invocation: true
```

该字段属于 Claude Code 扩展，不应直接写入需要通过开放规范校验的源 `SKILL.md`。本仓库的安装脚本在复制到 Claude 目录时注入该字段，并移除仅供 Codex 使用的 `agents/` 适配目录。

显式调用通常使用：

```text
/<skill-name>
```

## 3. Codex

常见安装位置：

```text
~/.agents/skills/<skill-name>/SKILL.md
<project>/.agents/skills/<skill-name>/SKILL.md
```

仅限用户主动调用时，在 Skill 的 Codex 适配文件中设置：

```yaml
# agents/openai.yaml
policy:
  allow_implicit_invocation: false
```

显式调用使用：

```text
$<skill-name>
```

Codex 适配文件可以保存展示名称、简短描述、默认提示和调用策略，但不得复制核心工作流。

## 4. 安装适配

推荐流程：

```text
可移植 Skill 源
    ├── Codex 安装：保留标准 SKILL.md + agents/openai.yaml
    └── Claude 安装：注入 Claude 手动调用字段 + 移除 Codex 适配目录
```

适配必须：

- 由脚本或生成流程完成；
- 可重复执行；
- 有自动化测试；
- 不直接修改规范源；
- 覆盖前要求明确授权；
- 安装后按目标平台配置重新校验。

## 5. 其他平台

新增平台时先判断：

1. 是否原生支持开放 Agent Skills；
2. 支持哪些 Frontmatter 字段；
3. Skill 的发现和安装路径；
4. 显式与隐式调用控制；
5. 脚本和资源访问权限；
6. 平台是否会拒绝未知字段。

只有真实差异才新增适配。无法提供等价行为时，明确降级，不伪造兼容性。

## 6. 验证状态

交付报告分别标注：

- 源文件通过开放规范静态检查；
- Claude 安装副本通过静态检查或真实调用；
- Codex 安装副本通过静态检查或真实调用；
- 未运行平台的具体限制。

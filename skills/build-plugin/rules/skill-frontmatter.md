# Frontmatter 设计规则

Frontmatter 只承载目标平台会读取的元数据和运行策略。每个字段都必须对应真实需求；平台默认行为已经满足需求时，不重复声明默认值。

## 1. 字段决策矩阵

新建或升级 Skill 时，先从已确认行为识别适用字段。下表用于查找字段，不要求逐项列出不适用的字段：

| Skill 特征                | 字段或配置                       | 判断规则                                                                  |
| ------------------------- | -------------------------------- | ------------------------------------------------------------------------- |
| 所有 Skill                | `name`                           | 必填，并与目录名一致                                                      |
| 所有 Skill                | `description`                    | 必填，说明能力与适用场景                                                  |
| 需要声明许可证            | `license`                        | 有分发要求、第三方内容或仓库明确约定时添加                                |
| 存在硬性环境要求          | `compatibility`                  | 只描述目标产品、运行时、系统软件或网络等必要条件                          |
| 确有程序或仓库约定需要读取元数据        | `metadata`                       | 注册表、安装器或仓库约定会读取时添加                                      |
| 需要临时预授权工具        | `allowed-tools`                  | 目标平台支持且完成权限评估后添加；不等同于限制其他工具                    |
| 需要临时移除工具          | `disallowed-tools`               | Claude Code 专属；Skill 活跃期间必须禁止特定工具时添加                    |
| 仅限用户调用              | `disable-model-invocation: true` | Claude Code 与 Pi 支持；副作用或执行时机必须由用户控制                    |
| 仅限模型调用              | `user-invocable: false`          | Claude Code 专属；只提供背景知识且不适合作为命令                          |
| 需要补充模型触发语境      | `when_to_use`                    | Claude Code 专属；仅在 `description` 无法简洁表达时使用                   |
| 自动调用受文件路径限制    | `paths`                          | Claude Code 专属；只在匹配指定 Glob 的文件时激活                          |
| 自动完成需要参数提示      | `argument-hint`                  | Claude Code 专属；只改善调用界面，不代表需要命名参数                      |
| 正文使用命名位置参数      | `arguments`                      | Claude Code 专属；只有正文使用 `$name` 替换时添加                         |
| 需要隔离上下文            | `context: fork`                  | Claude Code 专属；任务应在独立 Subagent 上下文运行时添加                  |
| Fork 需要指定 Agent       | `agent`                          | Claude Code 专属；仅与 `context: fork` 配合，默认 Agent 不合适时添加      |
| Fork 必须在当前轮等待结果 | `background: false`              | Claude Code 专属；仅与 `context: fork` 配合；默认后台执行不符合流程时添加 |
| 需要固定模型              | `model`                          | Claude Code 专属；有可验证理由时添加，不默认用统一配置覆盖用户偏好      |
| 需要固定推理强度          | `effort`                         | Claude Code 专属；任务确有稳定的推理要求时添加                            |
| 需要 Skill 级 Hooks       | `hooks`                          | Claude Code 专属；事件必须随该 Skill 的生命周期生效时添加                 |
| 内联命令必须指定 Shell    | `shell`                          | Claude Code 专属；Skill 使用动态命令且默认 Shell 不满足要求时添加         |
| Codex 需要展示或调用策略  | `agents/openai.yaml`             | 存放 `interface` 和 `policy`，不复制核心工作流                            |

设计方案只记录必填字段、拟新增或保留的可选字段，以及用户明确要求审查的字段；每项包含目标平台和事实依据。没有触发特征的字段直接省略，不为证明“考虑过”而生成全字段矩阵。

## 2. `description` 与调用策略

- 允许模型调用时，优先在跨平台 `description` 中写清适用场景、排除条件和相邻 Skill 边界；
- 仅限用户调用时，由平台配置限制调用，不在正文重复权限说明；
- 调用策略变化属于行为变化，必须来自明确需求或已确认设计，并验证应触发与不应触发场景；
- 多平台 Skill 不依赖 Claude Code 的 `when_to_use` 承担唯一触发语义；ZCode 会把 `when_to_use` 与截断后的 `description` 一并交给模型；Pi 读取 `disable-model-invocation`，并忽略其他不识别的 Frontmatter 字段。

## 3. `compatibility`

默认省略。只有存在以下硬性条件时才填写：

- 必需的目标产品；
- 必需的运行时及最低版本；
- 必需的系统命令、软件或硬件；
- 必需的网络访问；
- Skill 无法自行携带、安装或安全降级的环境条件。

推荐写法：

```yaml
compatibility: 需要 Python 3.9+ 运行内置校验脚本。
```

```yaml
compatibility: 需要 Git、Docker 和互联网访问。
```

不要写入：

- 笼统的平台支持说明；
- `当前`、`目前`等容易过时的描述；
- Skill 会读取或修改哪些文件；
- 调用权限、用户确认要求和副作用；
- 只在部分分支中可能用到的工具；
- 已由 Manifest、README 或正文维护的信息。

## 4. 平台隔离

多平台共用源可以包含 Claude Code 字段和 `agents/openai.yaml`，但独立安装产物必须隔离：

```text
Claude Code 副本：保留通用字段和 Claude Code 字段，移除 agents/
Codex 副本：只保留通用 Agent Skills 字段，保留 agents/openai.yaml
ZCode 副本：保留全部字段（未识别的键被忽略），移除 agents/
Pi 副本：保留全部字段（未识别的键被忽略），移除 agents/
```

不得把未知字段直接假定为跨平台字段。平台规范变化后，先更新字段分类、安装转换和测试，再在 Skill 中使用新字段。

## 5. 完成标准

- 每个保留或新增字段都有真实判断依据；
- 默认值和装饰性字段已省略；
- 平台专属字段只进入对应安装产物；
- 实际使用的调用权限、参数、工具授权和上下文行为有对应场景验证；
- `compatibility` 只包含仍然有效的硬性环境要求。

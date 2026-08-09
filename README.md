# Awesome Agent Skills

这是一个个人维护的通用 Agent Skills 仓库，用于沉淀可复用、可验证，并能同时适配 Claude Code 与 Codex 的 Skills。

当前已收录：

| Skill | 用途 | 调用方式 |
| --- | --- | --- |
| `building-skills` | 从零构建或系统升级高质量 Agent Skill | 仅限用户显式调用 |

## 设计原则

- **单一规范源**：核心工作流只维护一份，不复制 Claude Code 与 Codex 两套正文。
- **先设计，后实施**：调研、澄清和目录设计完成，并经用户确认后，才能修改目标文件。
- **确定性优先**：优先复用 CLI 和脚本，其次使用模板、Few-shot 示例、规则与提示词。
- **渐进式读取**：`SKILL.md` 只保留路由和主流程，复杂细节按条件读取。
- **可验证交付**：机械检查、语义验收和真实场景验证彼此分离。
- **平台差异隔离**：开放规范保留在源文件中，平台专属配置由适配文件或安装过程处理。

## 仓库结构

```text
awesome-agent-skills/
├── .github/workflows/validate-skills.yml
├── scripts/install_skill.py
├── skills/
│   └── building-skills/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       ├── workflows/
│       ├── templates/
│       ├── examples/
│       ├── rules/
│       ├── scripts/
│       ├── checklists/
│       └── prompts/
└── tests/
```

## 安装 `building-skills`

安装脚本只使用 Python 标准库，建议使用 Python 3.9 或更高版本。

### Codex：用户级安装

```bash
python3 scripts/install_skill.py building-skills \
  --platform codex \
  --scope user
```

安装位置：

```text
~/.agents/skills/building-skills
```

Codex 适配文件 `agents/openai.yaml` 已关闭隐式调用。安装后通过以下方式显式调用：

```text
$building-skills
```

### Claude Code：用户级安装

```bash
python3 scripts/install_skill.py building-skills \
  --platform claude \
  --scope user
```

安装位置：

```text
~/.claude/skills/building-skills
```

安装脚本会在安装副本的 Frontmatter 中注入：

```yaml
disable-model-invocation: true
```

安装后通过以下方式显式调用：

```text
/building-skills
```

### 项目级安装

Codex：

```bash
python3 scripts/install_skill.py building-skills \
  --platform codex \
  --scope project \
  --project-dir /path/to/project
```

Claude Code：

```bash
python3 scripts/install_skill.py building-skills \
  --platform claude \
  --scope project \
  --project-dir /path/to/project
```

目标目录已存在时，安装脚本默认拒绝覆盖。确认覆盖后显式添加 `--force`。

## 验证

验证单个 Skill：

```bash
python3 skills/building-skills/scripts/validate_skill.py \
  skills/building-skills \
  --profile portable \
  --strict
```

运行全部测试：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

持续集成会在每次 Push 和 Pull Request 中执行相同检查。

## 当前范围

本次只完成 `building-skills`。仓库尚未提前创建第二个 Skill 的目录或占位文件。

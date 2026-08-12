# Skills-only Plugin 示例

## 目标

将两个已经通过 `build-skill` 验收的 Skills 组合为 Claude Code 与 Codex 双平台 Plugin。

## 推荐结构

```text
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── .codex-plugin/
│   └── plugin.json
└── skills/
    ├── first-skill/
    │   ├── SKILL.md
    │   └── agents/openai.yaml
    └── second-skill/
        ├── SKILL.md
        └── agents/openai.yaml
```

## 关键处理

- 两个平台 Manifest 指向同一个 `./skills/`；
- Skill 核心文件不复制；
- Claude Code 使用命名空间调用；
- Codex 使用 `$skill-name`；
- 仅限用户调用的 Skill 同时配置 Claude Frontmatter 与 Codex policy；
- 先校验每个 Skill，再校验整个 Plugin。

## 验收

```bash
python3 skills/build-plugin/scripts/validate_plugin.py . --platform dual --strict
```

真实客户端验证分别记录，不得用一端结果替代另一端。

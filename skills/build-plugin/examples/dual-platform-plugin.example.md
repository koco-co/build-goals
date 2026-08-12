# 双平台 Plugin 示例

## 场景

已有一个 Claude Code Plugin，需要增加 Codex 支持，同时避免复制 Skills、脚本和规则。

## 做法

1. 保留根目录 `skills/` 作为唯一实现；
2. 新增 `.codex-plugin/plugin.json`；
3. 为仅限用户调用的 Skill 增加 `agents/openai.yaml`，并设置对应调用权限；
4. Claude Code Manifest 与 Codex Manifest 使用相同的 `name`、`version` 和 `skills` 路径；
5. 平台专属能力保留在各自 Manifest 或适配文件；
6. 共享文件使用 Plugin 根目录内的相对软链接；
7. 分别完成平台真实测试。

## 不推荐

```text
skills-claude/
skills-codex/
```

当两份内容只有 Frontmatter 或少量元数据不同，不应复制整个 Skill。优先保留双平台源，并在独立安装或发布产物中做确定性适配。

# Plugin 验证

## Phase 1：仓库级静态检查

运行：

```bash
python3 scripts/validate_plugin.py <plugin-root> --platform <dual|claude|codex> --strict
```

检查：

- Manifest JSON、名称、版本和组件路径；
- 双平台身份与版本一致；
- Skills 遵循同一质量规范；
- `prompts/` 文件使用 `*.agent.md`；
- 软链接相对、有效且没有越界；
- Marketplace 路径；
- 空文件、失效引用和错误目录。

## Phase 2：平台官方检查

Claude Code：

```bash
claude plugin validate <plugin-root> --strict
claude --plugin-dir <plugin-root>
```

进入后验证命名空间调用、目标 Skill 的调用权限和 `/reload-plugins`。

Codex：

- 验证 `.codex-plugin/plugin.json`；
- 验证 Marketplace 能解析并列出 Plugin；
- 在支持 Plugin 的客户端完成安装；
- 按每个 Skill 的设计验证用户调用与模型调用权限；
- 检查 `agents/openai.yaml` 中的调用配置。

## Phase 3：场景验收

至少覆盖：

1. 新建 Plugin；
2. 升级已有 Plugin；
3. 仓库迁移；
4. 双平台共用组件；
5. Skill 委派；
6. Manifest 路径错误；
7. 失效或越界软链接；
8. 用户确认步骤；
9. 安装、更新和失败回滚；
10. 每个 Skill 的实际调用行为与平台配置一致。

## Phase 4：结果分类

分别记录：

- 已验证；
- 静态检查通过但未真实运行；
- 未验证；
- 无法完成的内容和原因；
- 失败后已修复并复验。

完成条件：所有静态检查通过，关键路径有实际结果，未运行的平台没有被描述为已通过。

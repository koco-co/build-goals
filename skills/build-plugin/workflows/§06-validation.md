# Plugin 验证

## Phase 1：仓库级静态检查

运行：

```bash
python3 scripts/validate_plugin.py <plugin-root> --platform <dual|claude|codex> --strict
```

该脚本已覆盖 Manifest、双平台身份与版本、Skill 质量与 Frontmatter、共享镜像（存在、非软链接、与规范源一致且不越界）、必要链接、空文件、失效引用及 Claude Marketplace；本清单只处理脚本无法判断的内容与场景项。

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

先执行 `checklists/plugin-design-review.md` 和 `checklists/plugin-semantic-acceptance.md`；清单只补充脚本无法判断的设计与场景问题。

至少覆盖：

1. 新建 Plugin；
2. 升级已有 Plugin；
3. 仓库迁移；
4. 双平台共用组件；
5. Skill 委派；
6. 缺失、漂移或被软链接替代的共享镜像，以及失效或越界的必要链接；
7. 安装、更新和失败回滚；
8. 每个 Skill 的实际调用行为与平台配置一致。

其余场景遵循 `rules/skill-quality-standard.md` 的决策与确认原则。

## Phase 4：结果分类

分别记录：

- 已验证；
- 静态检查通过但未真实运行；
- 未验证；
- 无法完成的内容和原因；
- 失败后已修复并复验。

完成条件：所有静态检查通过，关键路径有实际结果，未运行的平台没有被描述为已通过。

Plugin 包含新建、整体重构或改变触发、Frontmatter、权限与平台行为的 Skill 时，还必须完成 `build-skill` 规定的内容审查、文案审查、内容回归和独立 Reviewer 复查。

# Repository Instructions

## 项目定位

- 本仓库维护面向 Claude Code 与 Codex 的双平台 `build-goals` Plugin，以及可独立安装的 Agent Skills。
- `skills/` 是 Skill 行为的权威来源；平台差异只放在各平台 Manifest、`agents/openai.yaml` 或安装适配代码中。
- `AGENTS.md` 是仓库级 Agent 指令的唯一规范源；`CLAUDE.md` 必须保持为指向它的相对软链接，不得复制维护两份内容。
- README 面向使用者，Skill 负责按需工作流，脚本和测试负责机械保证；不要在本文件重复它们的详细内容。

## 开始修改前

- 先读取当前任务涉及的 Skill、测试、Manifest、README 和适用官方文档，再决定改动范围。
- 先执行 `git status --short --branch` 并检查相关差异。未提交修改、新文件和并行工作均属于用户资产，不得回滚、覆盖、删除或擅自纳入提交。
- 新功能、架构、跨模块、安全、集成或发布策略变更必须先完成事实核查，明确范围、风险和验收标准，并在用户确认后实施；小型明确修复可直接执行。
- 只修改当前任务授权的文件。发现无法安全分离的并发改动时停止发布，并说明冲突位置和所需决定。

## 实施约定

- 行为变更遵循 TDD：先添加或更新失败测试，再实现，最后重构并运行验证。
- 保持主 `SKILL.md` 简洁，详细流程放在 `workflows/`、`rules/`、`checklists/`、`templates/` 或 `examples/` 中，并通过相对路径引用。
- 仓库内共享文件使用解析范围仍在 Plugin 根目录内的相对软链接；不得创建绝对链接、失效链接或越界链接。
- 同一规则只保留一个权威定义。修改 Skill、Plugin 或平台行为时，同步更新直接受影响的文档、适配器、Manifest 和回归测试。
- 不得把静态校验、安装成功、测试发现或模拟结果描述为真实客户端、用户流程、视觉、外部服务或生产验收。
- 不得读取、打印、提交或上传凭据、Cookie、Token、私有配置或其他敏感数据。

## 验证要求

- 先运行受影响测试和受影响 Skill 的严格校验，再运行完整门禁：

  ```bash
  python3 -m unittest discover -s tests -p 'test_*.py'
  python3 skills/build-plugin/scripts/validate_plugin.py . --platform dual --strict
  git diff --check
  ```

- 修改单个 Skill 时，还要运行：

  ```bash
  python3 skills/build-skill/scripts/validate_skill.py \
    skills/<skill-name> \
    --profile dual \
    --plugin-root . \
    --strict
  ```

- Skill 行为变化需要在适用客户端上做真实语义验收；若当前环境无法执行，明确记为未验证，不得以静态结果替代。
- 交付时分开报告已验证、未验证和阻塞项，并列出可复现命令。

## 版本策略

- 修复、文档和兼容规则调整递增 patch；新增向后兼容能力递增 minor。
- 破坏兼容性需要用户先确认 major 版本，不得自动发布。
- 每次发布必须同步以下正式版本源：
  - `.claude-plugin/plugin.json`
  - `.claude-plugin/marketplace.json` 中 `build-goals` 条目
  - `.codex-plugin/plugin.json`
- Skill 自身 `metadata.version` 按该 Skill 的行为变化独立递增。

## 完成后的自动发布

- 每个验证通过的逻辑变更完成后执行一次发布链路；不得提交或推送中间状态。
- 发布前确认当前分支是跟踪 `origin/main` 的 `main`，远端没有未整合提交，工作区改动均能明确归属于当前任务；否则停止并报告。
- 选择并同步版本，重新运行完整门禁，只暂存当前任务文件，检查 staged diff 后创建一个有意义的原子提交。
- 使用显式目标推送并核对远端提交：

  ```bash
  git push origin HEAD:refs/heads/main
  git ls-remote origin refs/heads/main
  ```

- 推送成功后刷新正式 Claude Code Plugin，并核验安装版本与关键变更：

  ```bash
  claude plugin marketplace update build-goals
  claude plugin update build-goals@build-goals --scope user
  claude plugin list
  ```

- 随后刷新正式 Codex Plugin，并核验安装版本与关键变更：

  ```bash
  codex plugin marketplace upgrade build-goals --json
  codex plugin list --json
  ```

- 保留两端插件原有 enabled/disabled 状态；不得修改独立的 `build-goals-local` 测试插件，不得把“需要重启”描述为已生效。
- 任一测试、校验、版本同步、提交、push、远端 SHA 或客户端刷新核验失败时，立即停止后续发布步骤并报告真实状态；禁止 force push、跳过门禁或伪造成功。
- 用户明确要求不提交、不 push 或不更新插件时，以该次用户指令为准。

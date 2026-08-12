# build-goals Agent Guide

## 项目定位

- 本仓库同时分发 Claude Code 与 Codex 的 `build-goals` Plugin，并支持从 `skills/` 独立安装单个 Skill。
- `skills/` 是行为权威来源；Claude Code 扩展写在 `SKILL.md` Frontmatter，Codex 调用策略写在 `agents/openai.yaml`。
- 根 `AGENTS.md` 是仓库指令的单一正文；`CLAUDE.md` 必须保持为指向它的相对符号链接。

## 工作地图

- `skills/<name>/SKILL.md`：Skill 路由与主流程；复杂细节按需放入同目录的 `workflows/`、`rules/`、`templates/`、`examples/` 和 `checklists/`。
- `skills/build-skill/scripts/validate_skill.py`：单个 Skill 的结构与双平台契约校验。
- `skills/build-plugin/scripts/validate_plugin.py`：Plugin Manifest、组件、链接和版本同步校验。
- `scripts/install_skill.py`：Claude Code 与 Codex 的独立安装适配器。
- `.claude-plugin/`、`.codex-plugin/`、`.agents/plugins/`：三个分发入口；正式版本号只存在于前两个平台的三个 Manifest 位置。
- `tests/`：校验器、安装器及仓库契约的回归测试。
- `README.md`：面向使用者的能力、安装和验证入口，不承载 Skill 运行细节。

## 关键命令

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`：完整回归测试。
- `python3 skills/build-plugin/scripts/validate_plugin.py . --platform dual --strict`：双平台 Plugin 门禁。
- `python3 skills/build-skill/scripts/validate_skill.py skills/build-agents-md --profile dual --plugin-root . --strict`：单 Skill 严格校验；修改其他 Skill 时替换目标路径。
- `python3 skills/build-agents-md/scripts/validate_agents_md.py . --strict --require-symlink`：仓库指令与单一来源校验。
- `python3 skills/build-readme/scripts/validate_readme.py README.md --project-root . --strict`：README 结构与本地引用校验。
- `git diff --check`：空白和补丁格式检查。

## 项目不变量

- 所有 Skill 仅允许显式调用：Claude Code 使用 `disable-model-invocation: true`，Codex 使用 `allow_implicit_invocation: false`。
- 主 `SKILL.md` 保持渐进式读取入口；新增的本地引用必须存在，工作流文件遵循 `§NN-name.md`。
- 仓库内共享文件只使用相对符号链接，且解析目标必须留在 Plugin 根目录内。
- Claude Code 安装副本必须移除 Claude 不支持以外的平台适配内容；Codex 安装副本必须移除 Claude 专有 Frontmatter 并保留 `agents/openai.yaml`。
- 新增向后兼容能力递增 Plugin minor 版本；修复递增 patch；三个正式版本源必须一致。Skill 的 `metadata.version` 独立维护。
- 静态校验、安装成功和测试发现不代表真实 Claude Code/Codex 客户端已加载或 Skill 行为已验收。

## 变更与验证

| 变更类型 | 最小验证 |
| --- | --- |
| 新建或修改 Skill | 先固定行为测试，再运行目标 Skill 严格校验与相关单元测试 |
| Manifest、平台适配或共享链接 | 运行双平台 Plugin 门禁、安装器测试及完整回归 |
| `AGENTS.md` / `CLAUDE.md` | 运行 `validate_agents_md.py --strict --require-symlink` 并检查 Git 链接模式 |
| README | 运行 `validate_readme.py`，再检查其中公开命令与当前仓库一致 |
| 正式版本 | 同步 `.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json` 的 Plugin 条目和 `.codex-plugin/plugin.json` |

- 行为变化还需在适用的真实客户端执行语义验收；当前环境不能完成时明确报告“未验证”。
- 完成前运行受影响测试、完整回归、双平台门禁和 `git diff --check`，并分别报告结果。

## 交付边界

- 详细的 Skill 与 Plugin 交付流程分别由 `skills/build-skill/workflows/§06-delivery.md` 和 `skills/build-plugin/workflows/§07-delivery.md` 维护，本文件不复制命令清单。
- 实现和验证结束后，主动询问用户是否执行当前任务实际适用的 commit、push、Claude Code Plugin 更新和 Codex Plugin 更新；允许只授权部分动作。
- 不得自动 commit、push 或更新本地 Plugin；各动作必须取得对应授权，且一个动作的授权不推导另一个。

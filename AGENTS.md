# build-goals 开发指南

## 项目概览

- 本仓库同时分发 Claude Code、Codex 与 DeepSeek Harness 三个版本的 `build-goals` Plugin，也支持从 `skills/` 单独安装某个 Skill。
- `skills/` 是 Skill 行为的权威来源；Claude Code 专用配置写在 `SKILL.md` Frontmatter，Codex 专用配置写在 `agents/openai.yaml`，DSH 插件包资产由同步脚本显式镜像。
- `AGENTS.md` 是仓库开发说明的唯一正文；`CLAUDE.md` 必须保持为指向它的相对符号链接。

## 仓库结构

- `skills/<name>/SKILL.md`：Skill 的入口与主流程；详细内容按需放入同目录的 `workflows/`、`rules/`、`templates/`、`examples/` 和 `checklists/`。
- `skills/build-skill/scripts/validate_skill.py`：检查单个 Skill 的结构和双平台配置。
- `skills/build-plugin/scripts/validate_plugin.py`：检查 Plugin Manifest、组件、共享文件镜像、符号链接安全和版本号。
- `scripts/install_skill.py`：将单个 Skill 安装到 Claude Code、Codex 或 DeepSeek Harness。
- `.plugin-shared-files.json`、`skills/build-plugin/scripts/sync_shared_files.py`：声明并显式同步跨 Skill 的普通镜像文件，兼容不会保留嵌套软链接的客户端缓存。
- `.claude-plugin/`、`.codex-plugin/`、`.agents/plugins/`、`packages/dsh-build-goals/`：四个 Plugin 分发入口；正式版本号维护在 Claude Code、Codex 和 DSH 包的全部 Manifest 位置。
- `packages/dsh-build-goals/scripts/sync_skills.py`：从 `skills/` 显式同步 DSH 插件包的 `assets/skills/` 镜像与 `lib/skills.generated.js` 清单（剥离 `agents/`），产物提交入库、安装时零构建；镜像路径由 `.gitattributes` 标记为生成物，漂移由只读检查拒绝。
- `tests/`：校验器、安装器和仓库约定的回归测试。
- `README.md`：面向使用者说明能力、安装方法和验证命令，不重复 Skill 的详细流程。

## 常用命令

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`：运行全部回归测试。
- `python3 skills/build-plugin/scripts/validate_plugin.py . --platform dual --strict`：检查双平台 Plugin。
- `python3 skills/build-skill/scripts/validate_skill.py skills/build-agents-md --profile dual --plugin-root . --strict`：检查单个 Skill；修改其他 Skill 时替换目标路径。
- `python3 skills/build-agents-md/scripts/validate_agents_md.py . --strict`：检查项目指令和 `CLAUDE.md` 符号链接。
- `python3 skills/build-readme/scripts/validate_readme.py README.md --project-root . --strict`：检查 README 结构和本地引用。
- `python3 skills/build-plugin/scripts/sync_shared_files.py --root .`：只读检查跨 Skill 镜像是否与规范源一致；需要刷新时显式添加 `--write`。
- `python3 packages/dsh-build-goals/scripts/sync_skills.py --root .`：只读检查 DSH 插件包资产是否与 `skills/` 一致；需要刷新时显式添加 `--write`。
- `git diff --check`：检查空白和补丁格式问题。

## 关键约定

- 最高优先级：禁止防御性编程和防御性提示词。只实现有用户需求、仓库事实、平台契约、可复现缺陷或明确安全要求支持的行为；不得为未经证实的假设增加代码、分支、兜底、兼容、校验、权限门禁、提示词或流程。必要的输入校验、数据安全、权限边界和错误处理必须能指出上述依据。
- 主 `SKILL.md` 只保留入口和主流程；新增的本地引用必须存在，工作流文件使用 `§NN-name.md` 命名。
- 调用策略写在平台配置中；目标 Skill 允许模型调用时，按 `skills/build-skill/rules/quality-standard.md` 写清触发条件和排除条件。
- 跨 Skill 运行依赖在 `.plugin-shared-files.json` 中声明，仓库保存普通镜像；修改规范源后显式同步，严格校验必须拒绝缺失、软链接或内容漂移。
- `CLAUDE.md` 等确需使用的符号链接必须是仓库内相对链接；不得假设 Plugin 客户端缓存会保留嵌套软链接。
- Claude Code 安装副本保留 Claude Code 支持的 Frontmatter，并移除 `agents/`；Codex 安装副本移除 Claude Code 专用 Frontmatter，并保留 `agents/openai.yaml`；DSH 安装副本保留全部 Frontmatter（DSH 容忍未知字段），并移除 `agents/`。
- 新增向后兼容能力时递增 Plugin minor 版本，修复时递增 patch 版本；四个正式版本号（`.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、`.codex-plugin/plugin.json` 与 `packages/dsh-build-goals/package.json`）必须一致。Skill 的 `metadata.version` 独立维护。
- 静态校验、安装成功和测试发现都不能代替真实 Claude Code/Codex/DeepSeek Harness 客户端中的行为验证。

## 验证流程

| 修改内容                     | 至少运行                                                                                                                                     |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 新建或修改 Skill             | 先补行为测试，再运行目标 Skill 检查和相关单元测试                                                                                            |
| Manifest、平台适配或共享文件 | 镜像检查、双平台 Plugin 检查、安装器测试和完整回归                                                                                           |
| DSH 插件包                   | `sync_skills.py --root .` 只读检查、DSH 插件包结构测试、安装器测试和完整回归                                                                 |
| `AGENTS.md` / `CLAUDE.md`    | `validate_agents_md.py --strict`，并检查 Git 中的链接模式                                                                                    |
| README                       | `validate_readme.py`，并核对公开命令与当前仓库一致                                                                                           |
| 正式版本                     | 核对 `.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、`.codex-plugin/plugin.json` 和 `packages/dsh-build-goals/package.json` |

- 行为变化还要在适用的真实客户端中验证；当前环境无法完成时，明确标为“未验证”。
- 交付前运行相关测试、完整回归、双平台 Plugin 检查和 `git diff --check`，分别报告结果。

## 提交与发布

- Skill 与 Plugin 的详细交付流程分别维护在 `skills/build-skill/workflows/§06-delivery.md` 和 `skills/build-plugin/workflows/§07-delivery.md`，本文件不复制具体发布命令。
- 实现和验证结束后，主动询问用户是否执行当前任务需要的 commit、push、Claude Code Plugin 更新、Codex Plugin 更新和 DSH 插件包资产同步；允许只授权部分操作。
- 不得自动 commit、push 或更新本地 Plugin；每项操作都需要单独授权，一项授权不能推导出另一项。

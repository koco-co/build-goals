# 开源仓库学习合同

## 路由与目标

- GitHub URL、`owner/repo`，或“读懂项目并能修改/贡献”的目标进入 `workflows/§07-open-source.md`。
- 学习成果必须同时包含：能运行受控基线、画出项目地图、解释一条核心调用链、定位测试边界，并完成一条真实最小 Patch 及相关测试。
- 外层路线固定为：`01-项目概述`、`02-运行与测试基线`、`03-架构与模块地图`、`04-核心调用链`、`05-测试与质量体系`、`06-Issue与PR考古`、`07-最小修复实践`、`08-深入与拓展`、`09-复习与贡献准备`、`99-assets`。只允许在这些阶段内细分连续编号子目录。
- 整体地图只建立一次；正式学习只选择一条能从入口追到行为与测试的核心切片，避免按文件逐个漫游。

## 仓库事实基线

路线确认前核验并持久化：

- canonical GitHub URL、`owner/repo`、默认分支、canonical 完整目标 ref（`refs/heads/...` 或 `refs/tags/...`）/完整 Commit OID、核验日期。
- 许可证 SPDX 标识、归档/禁用状态、最近发布与维护信号。
- 学习范围、核心切片、运行入口、测试入口和上游检查时间。

README 是导航，不是源码事实。关键结论使用固定 Commit 的 GitHub permalink、源码、测试、发布记录、Issue 或 PR 交叉证明。没有许可证时可进行只读学习，但阻断 Patch/贡献毕业；仓库已归档时明确历史学习价值，不把它描述为活跃贡献目标。

## 源码隔离

- 完整源码、依赖、构建产物和 Git 元数据不得写入 Vault；Vault 只保存笔记、图、permalink、Patch 摘要与测试证据。
- 用户已有 checkout 时先只读审计 remote、Commit 与 dirty 状态；dirty 或 Commit 不符时不得覆盖、清理或复用为受控实践环境。
- 没有合格 checkout 时，使用 `scripts/repository_cli.py` 在 Vault 外的本轮独立目录准备 detached Commit 基线。
- 初始准备不递归 submodule，不安装依赖，不运行 hooks、postinstall、仓库脚本、容器或需要凭据的命令。任何额外执行仍遵守用户确认和仓库风险边界。

## Patch 与毕业门槛

候选 Patch 必须可复现、范围小、与核心切片相关、可由现有或新增相关测试验证，并排除凭据、安全敏感改动、生产配置、依赖大升级和无关重构。执行前展示问题证据、计划文件、测试命令、学习价值和风险，等待单独确认。

`graduation_status` 允许 `pending`、`blocked`、`passed`：

- `passed`：HEAD 仍是记录的 Commit；变更只在批准文件；Patch 非空且 `git diff --check` 通过；相关测试真实运行且退出码为 0；证据文件记录 Commit、Patch hash、测试 argv、退出码和时间。
- `blocked`：许可证、权限、依赖、环境或上游状态使真实 Patch/测试无法完成；不得以阅读、伪代码或静态推理替代毕业。
- 未满足任一条件保持 `pending`，路线和相关单元不得标记完成。

未经独立授权，不 commit、push、fork、创建 Issue/PR，也不发送外部消息。

## 上游变化

每次恢复仓库路线前运行只读 `upstream-check`：分别比较远端默认分支、目标 ref、归档状态和记录的 Commit；不自动 fetch、pull、merge、rebase 或改写工作区。上游有变化时先标记 `changed`，判断迁移路线或经用户确认继续固定 Commit；后者持久化为 `fixed-baseline`，避免稳定 tag 因默认分支前进而永久阻塞。不可访问时标记 `blocked`，不伪装“未变化”。

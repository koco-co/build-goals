# 学习一个开源仓库

## 1. 固定仓库事实与切片

1. 读取 `rules/repository-learning-policy.md`、`rules/research-policy.md`、`rules/vault-audit-policy.md` 和 `rules/curriculum-design.md`。
2. 核验 canonical GitHub 身份、默认分支、目标 ref、完整 Commit、许可证、维护状态、运行与测试入口。
3. 选择一条能从入口追到行为与测试的核心切片；整体地图只建一次。
4. 审计 Vault 前置与相似内容。硬前置失败时阻断。

## 2. 源码环境

1. 用户已有 checkout 只运行 `repository_cli.py audit`；dirty、remote 或 Commit 不符时不清理、不覆盖。
2. 需要隔离 checkout 时使用用户确认的 Vault 外位置，先 `prepare` dry-run，再 Apply。
3. 初始准备不隐式安装依赖、运行脚本、容器、submodule、账号或凭据操作。

## 3. 固定路线与三层记录

仓库外层固定为 `01`～`09` 阶段、`10-学习记录` 和 `99-assets`。`01-项目概述/§01-学习路线图.md` 保存 Commit、核心切片、依赖、单元成果和验收；每篇仓库正文使用四类正文之一，每个已创建单元对应一份学习记录。

路线确认后转入 `workflows/§02-scaffold.md`。

## 4. Patch 毕业

1. 进入最小修复前展示问题、批准文件、测试 argv、预期 Patch、学习价值和风险，等待单独确认。
2. 使用 `repository_cli.py verify-patch` 先 dry-run，再 Apply。
3. Patch 摘要和测试结果写入对应学习记录；正文只保留稳定机制与修复说明。
4. 只有 HEAD、批准文件、非空 Patch、`git diff --check` 和相关测试全部通过，才满足 `repository-patch` 学习毕业门。
5. `09-复习与贡献准备` 只说明贡献准备度；它不能替代 Patch 学习证据，外部贡献仍需独立授权。
6. 恢复前运行只读 `upstream-check`；不自动 fetch、pull、merge、rebase、commit、push 或创建 Issue/PR。

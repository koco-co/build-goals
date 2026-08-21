# 学习一个开源仓库

## 1. 绑定仓库事实

1. 完整读取 `rules/repository-learning-policy.md`、`rules/research-policy.md` 和 `rules/vault-audit-policy.md`。
2. 把 GitHub URL 或 `owner/repo` 规范化为 canonical 身份；核验默认分支、目标 ref、完整 Commit、许可证、维护/归档状态、运行和测试入口。
3. 明确可验证成果与一条核心切片；单仓路线只保留一条主切片，其余模块进入项目地图或拓展阶段。
4. 审计 Vault 中已有仓库笔记和前置知识；硬前置失败时按启动工作流阻断。

## 2. 审计或准备源码

1. 在 Vault 外创建本轮独立计划目录，填写 `templates/repository-workspace-plan.template.json`。
2. 已有 checkout 只运行 `audit`；记录 remote、HEAD 和 dirty hash，不修改工作区。只有 remote/Commit 匹配且状态满足当前实践边界时才可复用。
3. 需要隔离环境时先 dry-run，再经用户确认执行：

```bash
python3 "<SKILL_DIR>/scripts/repository_cli.py" prepare --plan "<PLAN_DIR>/repository-plan.json"
python3 "<SKILL_DIR>/scripts/repository_cli.py" prepare --plan "<PLAN_DIR>/repository-plan.json" --apply
```

4. 安装依赖、运行仓库脚本、容器、submodule、账号或凭据操作不由 prepare 隐式执行；按风险单独确认。

## 3. 预览固定路线

1. 使用 `templates/repository-scaffold-spec.template.json` 和 `templates/repository-prerequisites.template.md`。
2. 展示固定外层路线、每阶段成果、核心切片、源码隔离位置类型、Commit 基线、许可证与上游状态；机器绝对路径不写入 Vault。
3. 等待路线确认后转到 `workflows/§02-scaffold.md`；仓库路线设置 `roadmap_kind: repository`，Base 仍命名为 `<主题路径段>-Roadmap.base`。

## 4. 推进与毕业

1. `01`～`06` 依次证明：项目边界、可运行基线、模块地图、核心调用链、测试边界、Issue/PR 历史。
2. 进入 `07-最小修复实践` 前，给出问题、批准文件、测试 argv、预期 Patch 与风险，等待单独确认。
3. 实施后运行：

```bash
python3 "<SKILL_DIR>/scripts/repository_cli.py" verify-patch --plan "<PLAN_DIR>/repository-plan.json"
python3 "<SKILL_DIR>/scripts/repository_cli.py" verify-patch --plan "<PLAN_DIR>/repository-plan.json" --apply
```

4. 把 `templates/repository-patch-evidence.template.md` 填为 Vault 笔记摘要；不写入源码、完整日志、凭据或机器绝对路径。只有 `repository_cli.py` 生成的 Patch 与 JSON 证据经 note plan 的 `repository_patch_file`、`repository_evidence_file` 重新核对后，才把 `graduation_status` 改为 `passed`；整条路线完成还必须同时满足 `roadmap_status: 已完成` 与 `graduation_status: passed`。
5. 每次恢复前运行 `upstream-check`。发现变化、归档或访问失败时先处理状态，不静默更新本地源码。

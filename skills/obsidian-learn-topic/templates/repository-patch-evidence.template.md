# 最小 Patch 验收证据

> [!info] 固定基线
> 仓库：`{{REPOSITORY_NAME}}`
> Commit：`{{FULL_COMMIT}}`
> 核验日期：`{{VERIFIED_AT}}`

## 问题与核心切片

- 问题证据：{{ISSUE_EVIDENCE}}
- 核心切片：{{CORE_SLICE}}
- 批准文件：{{APPROVED_FILES}}

## Patch

- Patch SHA-256：`{{PATCH_SHA256}}`
- `git diff --check`：{{DIFF_CHECK_RESULT}}
- 机器绝对路径：不持久化

## 相关测试

- argv：`{{TEST_ARGV}}`
- 退出码：`{{TEST_EXIT_CODE}}`
- 证据 SHA-256：`{{EVIDENCE_SHA256}}`

## 毕业判定

- `graduation_status`: {{GRADUATION_STATUS}}
- 未满足条件与下一步：{{BLOCKER_OR_NEXT_STEP}}

# 普通代码练习合同

本合同适用于非仓库路线中需要编写或修改代码的单元。纯概念、架构判断和阅读单元选择更合适的 evidence profile；开源仓库 Patch 遵守 `rules/repository-learning-policy.md`。

## 粒度与文件名

- 每个代码型单元只有一个必做核心练习，验证一组紧密相关的能力。
- 练习目录使用 `NN-练习名/`。独立脚本使用 `NN-名称.扩展名`；多文件项目只编号练习目录，内部保留生态约定文件名。
- 变式按学习价值添加，不设固定数量。综合项目作为独立单元并公开验收标准。

## 外部工作区确认门

- 完整代码放在持久的 Vault 外工作区；Vault 只保存说明、证据摘要和 Wikilink。
- 模型只能推荐位置。用户必须提供并最终确认一个已经存在的绝对根路径；驱动不会猜测或创建根目录。
- 确认后，`scaffold` 只可在该根下创建已预览的 `NN-练习名/` 子目录。归档或删除另行确认。
- 笔记不保存机器绝对路径，只保存 `exercise_id`、相对目录名和 `attempt_id`。

## 用户先写与渐进提示

- 模型可以创建 starter、公开测试和配置，首次真实尝试前不写核心答案或等价实现。
- 提示先指出失败现象和相关知识，再按需要揭示文件、函数、边界、伪代码或最小片段；不强制固定层数。
- 只有用户明确索要完整答案，或已有可验证尝试后，才展示完整解法。
- 修改用户代码需要独立授权；先固化当前尝试。模型代写后的绿灯不能单独证明掌握。

## 公开验收

- 尝试前公开 starter、测试 argv、必要测试点、通过标准和 rubric；不使用隐藏测试或秘密扣分。
- rubric 可用 pass/fail，也可用正权重加权；权重只需为正且内部一致，不强制原始总数等于 100。
- 新增变式前完整公开，并作为新的已确认命令授权。
- 用户还要解释关键实现、失败边界或取舍；一次偶然绿灯不等于掌握。

## 驱动职责

`scripts/exercise_cli.py` 只有四个命令：

- `scaffold`：创建已确认的练习包和 manifest。
- `authorize`：固化某条公开命令的确认合同。
- `record-attempt`：追加宿主或用户提供的执行证据。
- `add-variant`：在已有尝试后添加公开非必需变式，并使旧授权失效。

驱动不运行学习命令。真实 argv 由用户确认的宿主终端、用户 CI 或用户确认容器执行；没有安全执行环境时记录阻塞。不得把进程运行能力重新塞回驱动。

## Manifest 与证据

```text
NN-练习名/
  .learn-topic/
    manifest.json
    authorization.json
    evidence/
      attempt-01.json
  <starter 与公开测试>
```

- attempt 只追加不覆盖，记录 manifest hash、命令 ID、来源、状态、摘要、允许列表内的测试统计和外部 run ID；所有持久字段递归执行类型、秘密与机器路径检查，发现可疑值时拒绝整条 evidence，不保存完整日志、秘密或机器路径。
- 来源只允许 `host-tool`、`user-ci`、`user-supplied`。
- `host-tool` 与 `user-ci` 必须附带外部适配器生成的 HMAC attestation：绑定 adapter、外部 run ID、manifest hash、精确 argv、exit code、状态和时间。验证密钥由用户确认的宿主或 CI 保存在练习包之外，通过 `--trust-key-file` 临时提供；密钥不得写入 manifest、evidence、笔记、命令参数或环境合同。
- `user-supplied` 即使自报通过，也保持未独立核验，不能单独满足 `code-practice` 毕业门。
- Obsidian 学习记录保存尝试摘要和关联 ID，不复制外部完整 evidence。

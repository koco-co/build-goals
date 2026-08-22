# 执行普通代码练习

本流程只服务非仓库代码型单元，遵守 `rules/code-exercise-policy.md`。

## 1. 设计与路径确认

1. 只设计一个必做核心练习；按学习价值决定是否添加公开变式。公开 starter、测试 argv、必要测试点、通过标准、rubric 和渐进提示。
2. 模型推荐外部位置，但用户必须提供并最终确认一个已存在的 Vault 外绝对根路径。未确认时只交付预览，不创建根路径。
3. 独立脚本使用 `NN-名称.扩展名`；多文件项目只编号练习目录，内部保留生态文件名。

## 2. 初始化与命令授权

1. 从 `templates/code-exercise-manifest.template.json` 生成计划，先运行 `exercise_cli.py scaffold` dry-run，再 Apply。
2. 用户先完成真实尝试；首次尝试前不提供核心解答。
3. 运行前展示 cwd、argv、环境、超时和预期副作用，通过 `authorize` 固化确认。manifest 或命令变化后重新确认。
4. 驱动不执行命令。用户在已确认的宿主终端、CI 或容器运行，并保留可核验结果；没有安全执行环境时停止并标记阻塞。

## 3. 证据与掌握

1. 提示从失败现象与知识点开始，按需逐步揭示位置、边界、伪代码或最小片段；首次尝试前不提供答案。
2. 使用 `record-attempt` 追加 `attempt-NN.json`。`host-tool` 与 `user-ci` 需要读取 `templates/code-exercise-attestation.template.json`，由外部适配器签名，并用练习包之外的 `--trust-key-file` 验签；`user-supplied` 不接受 attestation。学习记录保存 ID、摘要、关键失败、专项 rubric 和用户解释，不保存绝对路径、完整日志或信任密钥。
3. 测试通过后仍要求独立应用和边界解释；模型代写结果不能单独证明掌握。
4. 未独立核验的 `user-supplied` 结果不能单独毕业。证据写回并读回后，返回 `workflows/§04-learn-unit.md` 判断双状态。

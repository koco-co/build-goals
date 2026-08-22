# 学习一个知识单元

本流程同时遵守 `rules/curriculum-design.md`、`rules/content-quality.md` 和 `rules/learning-record-contract.md`。

## 1. 章前核验与类型选择

1. 从 `§01-学习路线图.md` 的 v3 机器合同读取当前 `unit_id`、计划路径、单项成果、前置、知识点归属、正文类型、`evidence_profile` 和验收方式。
2. 重新核验本章一手来源、版本、API/CLI、失败边界和相似笔记；未解决的动态事实保持 `待核验` 并停止。
3. 按计划只读取一种正文模板：
   - 教程：`templates/tutorial.template.md`
   - 原理解释：`templates/explanation.template.md`
   - 操作指南：`templates/how-to.template.md`
   - 参考资料：`templates/reference.template.md`
4. 同时读取 `templates/learning-record.template.md`。普通代码型单元先标记后续需要 `workflows/§08-code-exercise.md`，但必须完成下一节的正文与学习记录事务后才能转入；仓库 Patch 仍走 `§07-open-source.md`。

## 2. 创建正文与学习记录

1. 正文只讲授当前单元权威拥有的知识点，使用一个贯穿案例或连贯问题；其他知识通过 Wikilink 指向所属单元。
2. 正文不得包含学习计数、覆盖矩阵、题目状态、用户回答、内部评定和复习流水账。
3. 在同一个 note plan 中携带路线图路径、路线图精确快照、唯一 `records_directory`，以及相同 `unit_id` 的正文与学习记录两项 write；记录写入正文 Wikilink、主 profile、通过标准和第一个待回答检查点。
4. 通过 `roadmap_cli.py write-note` 先 dry-run、再 Apply 执行双文件 CAS，并分别精确读回；更新既有单元时也提供两份 expected-current 快照。
5. 两份文件均成功且双向链接正确后才开始教学。整个事务失败即回滚，不把记录重新塞回正文。
6. 普通代码型单元此时才进入 `workflows/§08-code-exercise.md`；练习证据回写后返回本流程完成能力判断。

## 3. 推进一个可恢复检查点

1. 根据主 profile 选择解释、场景、代码、操作、调用链或诊断任务。
2. 一个检查点只验证一种主要能力；需要连续操作时允许少量相互依赖的子步骤。
3. 首次尝试前不直接给答案；提示按用户表现逐步揭示。
4. 发送检查点后立即停止本轮。用户回答后用三句以内反馈，再通过 compare-and-swap 写回原始回答、结论、证据缺口和下一步；读回前不继续。

## 4. 证据与状态

按 `rules/evidence-profiles.md` 判断证据。单元流程结束时可设 `progress_status: 已完成`；只有独立应用、迁移或间隔保持分别成立时，才提升 `mastery_status`。一次只完成一个单元。

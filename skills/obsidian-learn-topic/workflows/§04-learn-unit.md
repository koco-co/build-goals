# 学习一个知识单元

本流程同时遵守 `rules/curriculum-design.md`、`rules/content-quality.md` 和 `rules/learning-record-contract.md`。

## 1. 章前核验与类型选择

1. 从 `§01-学习路线图.md` 的机器合同读取当前 `unit_id`、计划路径、单项成果、前置、知识点归属、正文类型和验收方式；可见表格只用于阅读，不替代合同身份。
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
3. 在 note plan 中携带本轮 `curriculum_plan_file` 与唯一 `records_directory`，通过 `roadmap_cli.py write-note` 先 dry-run、再 Apply 创建正文并精确读回。
4. 以相同 `unit_id` 创建对应学习记录，写入正文 Wikilink、通过标准、知识点状态和第一道待回答题；再次 dry-run、Apply、读回。
5. 两份文件均成功且双向链接正确后才开始教学。任一步失败都停止，不把记录重新塞回正文。
6. 普通代码型单元此时才进入 `workflows/§08-code-exercise.md`；练习证据回写后返回本流程第 3、4 节完成迁移验证与分类毕业。

## 3. 示范到迁移验证

1. **示范**：用户阅读正文中的完整案例和机制解释。
2. **补全**：在学习记录提出一道只缺一个关键步骤的题；发送后立即停止本轮。
3. **独立应用**：更换场景，让用户完成一项不能照抄的任务。
4. **迁移验证**：要求解释失败原因、比较替代方案或应用到新问题。
5. 用户每次回答后用三句以内反馈，再通过 compare-and-swap 写回原始回答、结论、遗漏和下一步；读回前不继续。

## 4. 分类毕业

- 原理解释：自己的话解释机制并分析新场景。
- 教程：独立复现并修改贯穿案例。
- 操作指南：完成真实任务并验证。
- 参考资料：准确查找并应用。
- 开源仓库：真实最小 Patch 和相关测试。

正文必须已发布且覆盖完整；学习记录的全部必需知识点、证据、验收和复习字段齐全后，才能标记 `已掌握`。一次只完成一个单元。

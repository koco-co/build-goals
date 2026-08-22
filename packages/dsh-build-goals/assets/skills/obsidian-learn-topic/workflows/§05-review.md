# 到期复习

1. 通过 Base 的 `review-due` 语义能力选择一个 `learning-evidence`，读取正文链接、主 profile、原证据、薄弱点和精确快照。
2. 根据证据强度、独立程度、错误类型和遗忘风险选择一个能力复查；形式可以是主动回忆、变式实践、诊断或迁移场景。按 `rules/learning-record-contract.md` 的提问消息格式发送后立即停止本轮。
3. 用户回答后用三句以内反馈，再通过 `write-note` compare-and-swap 把回答、结论、薄弱点和复习结果追加到学习记录；正文保持不变。
4. 复习验证能力保持或迁移，不要求原句背诵；原子事实可导出 Anki/FSRS，本 Skill 不维护卡片调度。
5. 通过后更新 `last_reviewed`、`next_review`、`review_count`、`mastery_status`、`mastery_evidence`、`assessment_type` 和 `assessment_at`；失败时记录证据缺口，必要时将 `progress_status` 调整为 `学习中`。
6. 对应正文不再发布、覆盖不足或版本失效时，先进入内容维护，不把课程缺陷记成用户失败。
7. 每次只复习一个单元。

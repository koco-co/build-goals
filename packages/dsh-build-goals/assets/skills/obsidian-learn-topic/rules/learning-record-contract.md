# 学习证据合同

每个已创建单元恰好对应一份独立学习记录。正文与记录通过 Wikilink 和相同 `unit_id` 双向关联。

## 状态模型

- `progress_status`：`未开始`、`学习中`、`阻塞`、`已完成`。
- `mastery_status`：`未证明`、`已独立应用`、`已迁移`、`已保持`。
- 两个维度不得互相推断：完成内容不等于掌握；复习到期也不改变进度。
- 不使用通用掌握分。专项公开 rubric 可以保留，但不得映射为统一掌握等级。

## 记录位置与职责

- 学习记录放在路线末尾连续编号的 `NN-学习记录/`，文件使用 `§NN-<单元>-学习记录.md`。
- 使用 `templates/learning-record.template.md`，并设置 `record_type: learning-evidence`；需要校准“一轮只留一个可恢复检查点”时完整读取 `examples/recoverable-checkpoint.example.md`。
- 路线图本身不创建学习记录；正文保存稳定知识，记录保存检查点、用户原始回答、评定、实践证据、薄弱点和复习历史。

## 强制事务顺序

1. 用 Obsidian CLI 读取路线图机器契约、知识正文、对应记录和精确快照。
2. 确认当前 `unit_id`、可观察成果、主 `evidence_profile` 和通过标准。
3. 新单元把正文和记录放进同一个双文件 CAS 事务，Apply 后分别读回；任一步失败都回滚且不开始教学。
4. 使用 compare-and-swap 在记录中写入一个待回答检查点并读回。
5. 只向用户发送当前检查点，随后立即停止本轮。
6. 用户回答后，把原始回答、结论、原因或遗漏、下一步和证据写回，再读回。

没有完成第 3 步不得教学；没有完成第 6 步不得进入下一个检查点或单元。

## 可恢复检查点

- 每个检查点只验证一种主要能力，但允许少量有依赖关系的子步骤。
- 形式可以是解释、场景判断、代码、真实操作、调用链追踪或故障诊断。
- 提问消息只包含进度状态、场景、任务与按需提示；提示逐步揭示，首次尝试前不直接给答案。
- 回答后先用三句以内说明结论、证据缺口和下一步，再写入记录。

## 掌握门

- `已独立应用`：用户在未代写的情况下完成主证据要求，并解释关键取舍或边界。
- `已迁移`：用户把能力用于明显不同的新场景，且结果可核验。
- `已保持`：经过一段间隔后再次独立完成能力检查。
- 用户提供但无法独立核验的证据可以记录，不能单独提升掌握状态。
- 每条用于提升掌握状态的 `mastery_evidence` 必须包含唯一 `evidence_id`、匹配单元的 `evidence_profile`、`capability_level`、可信来源或复核方、非空摘要、`observed_at` 和可追溯 `verification_ref`。这些字段必须与 Vault 外 HMAC 签名的 `templates/verification-receipt.template.json`、原始 artifact hash 和单元合同逐项一致；只改 Frontmatter、伪造 `host-tool` 或自填 `verified: true` 一律失败。
- `code-practice` 回执只接受 `status: passed` 的验签 attempt；回执 ID、adapter、origin、observed time、摘要 hash 和 `code-attempt:<attempt_id>:<external_run_id>` 引用必须逐字段等于 attempt/attestation。信任密钥使用至少 32 bytes、仅 owner 可读的独立普通文件，并位于练习包、manifest、artifact 和 receipt 之外。
- 具体毕业证据遵守 `rules/evidence-profiles.md`。

## 复习

- 根据证据强度、独立程度、错误类型和遗忘风险安排下次能力复查，不使用固定卡片间隔冒充适应性调度。
- 原子事实可导出到 Anki/FSRS；本 Skill 不实现卡片调度器。
- 每次复习把任务、结果、证据来源和下一次日期追加到同一学习记录。

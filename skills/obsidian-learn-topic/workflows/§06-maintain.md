# 维护路线与迁移旧内容

## 1. 只读审计

1. 读取 `rules/vault-audit-policy.md`、`rules/curriculum-design.md`、`rules/content-quality.md` 和 `rules/obsidian-cli-contract.md`。
2. 用 Obsidian CLI 检查路线图、正文、学习记录、Properties、出链、反链、版本、Base 和目录。
3. 对每个知识点建立“唯一所属单元 → 正文 → 学习记录 → 验收证据”映射，标出重复归属、依赖倒置、缺失成果和版本漂移。
4. 迁移候选分为 Wikilink 复用、原地更新、拆分、合并、移动、归档和回收站删除。

## 2. 旧版路线迁移预览

对把正文与问答流水账混在一起的既有路线，只生成预览：

- 新 v3 `§01-学习路线图.md` 的完整单元、依赖与 evidence profile；
- 正文按四种类型的保留、拆分和唯一归属；
- 用户回答、评分、练习和复习历史迁移到逐单元学习记录；
- 新学习记录目录编号及后续目录重编号映射；
- `learning_status` 和通用分数向双状态模型的保守推断；证据不足一律 `mastery_status: 未证明`；
- Base 重建、Properties、Wikilink 和导航影响；
- 无价值内部流水账的建议处置与可恢复方式。

使用 `roadmap_cli.py migrate --plan ...` 只生成确定性预览；`unit_id`、知识归属或 profile 有歧义时停止。预览确认前不修改 Vault。每条路线分别授权；不双写 v2/v3，也不把真实用户路线固化为分发示例。

## 3. 执行已确认维护

1. 先生成迁移事务计划，把旧路线图和受影响文件的精确快照作为 CAS 前提；Apply 只写 v3。
2. 结构变化从 `templates/renumber-plan.template.json` 生成 v3 事务，必须列出变更前/后目录合同、移动、所有受影响 Markdown 的 Properties CAS、路线图三段快照，并让 `expected_links` 覆盖每个受影响 Markdown、让 Base `expected_paths` 精确覆盖变更后的全部 Markdown；使用 `roadmap_cli.py renumber` dry-run，展示完整映射后再 Apply。仓库路线固定外层目录，不接受 renumber。
3. 受影响正文和记录用新版课程计划逐项执行 `write-note` 精确快照替换；移动使用 Obsidian `move`；删除默认进入回收站。
4. 合并保留来源、版本、独有信息和用户证据；不能用短文件覆盖长文件。
5. 操作后验证 Base 五项语义能力、Wikilink、断链和 `dev:errors`；回答、练习、复习与尝试历史必须保留。

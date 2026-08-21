# 维护路线与迁移旧内容

## 1. 只读审计

1. 读取 `rules/vault-audit-policy.md`、`rules/curriculum-design.md`、`rules/content-quality.md` 和 `rules/obsidian-cli-contract.md`。
2. 用 Obsidian CLI 检查路线图、正文、学习记录、Properties、出链、反链、版本、Base 和目录。
3. 对每个知识点建立“唯一所属单元 → 正文 → 学习记录 → 验收证据”映射，标出重复归属、依赖倒置、缺失成果和版本漂移。
4. 迁移候选分为 Wikilink 复用、原地更新、拆分、合并、移动、归档和回收站删除。

## 2. 旧单层路线迁移预览

对把正文与问答流水账混在一起的既有路线，只生成预览：

- 新 `§01-学习路线图.md` 的完整单元与依赖；
- 正文按四种类型的保留、拆分和唯一归属；
- 用户回答、评分、练习和复习历史迁移到逐单元学习记录；
- 新学习记录目录编号及后续目录重编号映射；
- Base 视图、Properties、Wikilink 和导航影响；
- 无价值内部流水账的建议处置与可恢复方式。

预览确认前不修改 Vault。每条现有路线都必须分别授权迁移；本轮 CLI 审计结果不能固化为随 Skill 分发的用户知识库示例。

## 3. 执行已确认维护

1. 先生成新版 Vault 外课程计划，把旧路线图作为 `expected_current_file`，用 `write-note` compare-and-swap 替换 `§01-学习路线图.md`；新版可见表格、机器合同和 note plan 课程必须一致。
2. 结构变化使用 `roadmap_cli.py renumber` dry-run，展示完整映射后再 Apply。
3. 受影响正文和记录用新版课程计划逐项执行 `write-note` 精确快照替换；移动使用 Obsidian `move`；删除默认进入回收站。
4. 合并保留来源、版本、独有信息和用户证据；不能用短文件覆盖长文件。
5. 操作后重新查询全部三层 Base 视图、Wikilink、断链和 `dev:errors`。

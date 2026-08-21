# 维护路线与相似内容

## 1. 只读影响分析

1. 读取 `rules/vault-audit-policy.md` 和 `rules/obsidian-cli-contract.md`。
2. 用 Obsidian CLI 检查目标文件的 Properties、出链、反向链接、嵌入、别名、版本范围和来源。
3. 先做主题级清单：分别统计路线根目录、Vault 内同主题命中、Clippings/外部资料、归档、敏感正文和排除目录；不把“搜索命中”直接当成“应合并”。
4. 对正式路线建立内容覆盖矩阵，至少列出学习目标、术语/API、机制、边界、实践和验收证据，并标注完整、部分覆盖或待核验。
5. 将候选动作分为：Wikilink 复用、原地更新、迁移、合并、归档、回收站删除。
6. 展示每个文件的保留内容、目标路径、链接影响、覆盖状态和回滚方式；同时核对笔记中引用的代码路径、命令和版本是否仍与受控练习工作区一致。

## 2. 独立确认

路线创建确认不授权内容处置。迁移、合并、归档或删除必须逐项确认；永久删除不属于默认流程。

## 3. 结构重编号

1. 生成旧目录到新目录的完整映射，并先运行：

```bash
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" renumber --plan "<TEMP_DIR>/renumber.json"
```

2. Dry-run 无冲突且用户确认后运行：

```bash
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" renumber --plan "<TEMP_DIR>/renumber.json" --apply
```

3. 插入新目录时把后续目录的批量映射、`add_directories` 和受影响笔记的 `property_updates` 放在同一计划中；操作后验证阶段 Properties、Base、链接均已同步，且不存在临时目录、旧路径或新增断链。

## 4. 内容操作

- 迁移使用 `obsidian move` 或经 CLI 调用的 Vault API，以保留 Obsidian 链接更新。
- 合并前读取双方完整内容，保留来源、别名、版本和独有信息；不得把较短文件直接覆盖较长文件。正文更新使用 `write-note` 的精确快照替换。
- 删除使用不带 `permanent` 的 `obsidian delete`，默认进入回收站。
- 外部资料、归档和敏感正文遵守保护范围，不自动规范化。
- 整条路线归档时通过 `write-note` 同步把锚点 `roadmap_status` 设为 `已归档`；硬前置阻塞时设为 `阻塞`，解除后经验证恢复为 `进行中`。

## 5. 验证

重新查询 Base、覆盖视图、导航、出链、反向链接、未解析链接和 UI；按通过、失败、错误、跳过报告结果。若内容审计导致单元回退，必须确认已有用户证据仍保留，且 `learning_status` 与 `coverage_status` 没有被混写。

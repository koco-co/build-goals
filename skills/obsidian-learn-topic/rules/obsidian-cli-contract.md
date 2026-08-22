# Obsidian CLI 驱动合同

所有 Vault 操作必须通过 Obsidian CLI。CLI 不可用、Vault 身份不符或读回失败时停止；不降级为直接文件系统写 Vault。

## 入口

```bash
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" probe
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" validate-curriculum --plan "<TEMP_DIR>/curriculum-plan.json"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" validate-base --base "<TEMP_DIR>/<TOPIC>-Roadmap.base" --root "<ROADMAP_ROOT>"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" scaffold --spec "<TEMP_DIR>/spec.json"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" scaffold --spec "<TEMP_DIR>/spec.json" --apply
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" write-note --plan "<TEMP_DIR>/note-plan.json"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" renumber --plan "<TEMP_DIR>/renumber-plan.json"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" migrate --plan "<TEMP_DIR>/migration-plan.json"
```

默认 dry-run；Apply 必须来自相应确认。计划文件放在 `mktemp -d` 等 Vault 外临时目录。

## v3 权威与 CAS

- `curriculum-plan.json` 是创建或迁移事务输入；写入后，路线图 `learn-topic-curriculum` 块是唯一持久化课程权威。
- 新建路线只接受 `schema_version: 3`。v1/v2 只能进入 `migrate` 预览，不能通过 `scaffold` 或 `write-note` 写回。
- `write-note` 必须携带路线图路径与精确 SHA-256，并把同一单元的知识正文与学习记录作为一个双文件 CAS 事务；目标已有内容时分别携带完整 expected-current 文件。任一变化均阻断，不能留下“有正文无记录”或“有记录无正文”。
- 正文路径、类型、成果、知识归属、前置、profile 和验收必须与路线图合同一致。
- 提升 `mastery_status` 时，事务还必须读取 `templates/verification-receipt.template.json` 生成的外部签名收据、原始 artifact 和 Vault 外信任密钥；`code-practice` 额外解析并验签真实 attempt 与 manifest。
- note plan 的 `trusted_evidence` 每项使用 `receipt_file`、`artifact_file`、`trust_key_file`；代码证据再提供 `manifest_file`。这些文件都必须位于 Vault 外，路径只存在于临时事务计划，不写入笔记。
- `trust_key_file` 还必须位于代码练习包之外、与 receipt/artifact/manifest 物理分离，并限制为 owner-only 权限；公开 manifest、artifact 或 receipt 不能充当 HMAC key。

## Scaffold 与 Base

- 根目录只有 `<根名>-Roadmap.base` 与编号目录；目录 `01-`～`99-`，Markdown `§01-`～`§99-`。
- Base 验证按 `route`、`current`、`review-due`、`blocked`、`evidence` 五项精确过滤语义，不固定视图名称、顺序或附加视图；恒真、恒假、冲突或附加收窄条件不能冒充能力，根过滤必须是完整且唯一的路线根表达式。
- 双文件 `batch-write` 在任一写入或回读失败时逐项恢复旧内容/不存在状态并回读验证；任何回滚失败必须连同未恢复路径显式报错，不能只返回原始写入错误。
- 首次 `batch-create` 在调用 `mkdir`/`write` 前登记回滚意图，因此即使适配器“先产生副作用再报错”也会清理；文件与目录按逆序移除并验证不存在，清理失败以 `batch-create failed and rollback was incomplete` 连同路径报告。调用层没有原子所有权证明，因此遇到 CAS 冲突或传输结果未知时不得删除任何计划目标；它只报告状态未知并要求先只读核查。
- `待核验`、`待补齐` 可以存在，但不是写门禁。
- Apply 后逐文件读回，并实际执行 Base query；UI 打开和 `dev:errors` 属于真实客户端验收。

## 代码练习

```bash
python3 "<SKILL_DIR>/scripts/exercise_cli.py" scaffold --plan "<EXERCISE_PLAN>"
python3 "<SKILL_DIR>/scripts/exercise_cli.py" authorize --manifest "<MANIFEST>" --command "<ID>" --confirmed-at "<ISO_DATETIME>"
python3 "<SKILL_DIR>/scripts/exercise_cli.py" record-attempt --manifest "<MANIFEST>" --evidence "<EVIDENCE_JSON>" --attestation "<ATTESTATION_JSON>" --trust-key-file "<EXTERNAL_KEY_FILE>"
python3 "<SKILL_DIR>/scripts/exercise_cli.py" add-variant --manifest "<MANIFEST>" --variant "<VARIANT_JSON>"
```

驱动只管理脚手架、命令授权和追加证据，不执行 argv。可信来源必须由练习包外的 HMAC 信任密钥验签；`user-supplied` 省略 attestation 与 key，并始终保持未核验。

## 仓库学习

`repository_cli.py audit|prepare|verify-patch|upstream-check` 保持独立。外部 checkout 路径由用户提供并确认；固定 Commit、批准文件、非空 Patch、`git diff --check` 和相关测试是学习毕业门。外部贡献另行授权。

## 验证层级

1. 静态：模板、schema、引用、命名和禁用合同。
2. 机械：CLI dry-run、单元测试、eval fixture。
3. 生成：脚手架与迁移预览的确定性内容。
4. Obsidian：CLI read-back、Base query、打开 Base、`dev:errors`。
5. 真实学习：新会话路由、可恢复检查点、宿主/CI 练习证据、真实仓库 Patch。

低层通过不能冒充高层通过；未运行的高层报告 `NOT VERIFIED`。

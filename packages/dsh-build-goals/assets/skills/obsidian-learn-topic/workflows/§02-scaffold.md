# 初始化已确认路线

仅在用户确认完整预览后执行。

## 1. 准备三层产物

1. 读取 `rules/obsidian-cli-contract.md`、`rules/curriculum-design.md`、`rules/properties-and-base.md` 和所需模板。
2. 解析当前 `SKILL.md` 真实目录，并用 `mktemp -d` 创建本轮独立 Vault 外目录。
3. 生成并验证 `curriculum-plan.json`；它必须与已确认预览逐项一致。
4. 生成：
   - `<主题路径段>-Roadmap.base`
   - `§01-学习路线图.md`
   - `§02-前置准备.md`
   - `§03-<主题>概述.md`
   - 前置与概述各自的学习记录
   - `scaffold-spec.json`
5. 仓库路线使用 `repository-curriculum-map`、仓库前置和固定外层目录；普通路线使用通用模板。
6. 路线图的单元、依赖、唯一归属、正文类型和验收必须与课程计划一致；把规范化后的完整 JSON 写入 `learn-topic-curriculum` 机器合同。删除空章节与未替换占位符。

## 2. Dry-run 与 Apply

```bash
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" scaffold --spec "<TEMP_DIR>/spec.json"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" scaffold --spec "<TEMP_DIR>/spec.json" --apply
```

Dry-run 必须证明：

- 根目录只有 Roadmap Base 和编号目录；
- 初始化正文只在概述目录；
- 初始化学习记录只在 `NN-学习记录`；
- 其他阶段保留 `.gitkeep`，`99-assets` 只用于资产；
- 正文与记录使用相同 `unit_id` 并双向链接；
- Vault 外课程计划、路线图机器合同、可见目录和 Base 视图语义一致。

Apply 前记录未解析链接和 `dev:errors` 基线。不得绕过驱动直接写 Vault。

## 3. 验证与停止

1. 运行 `roadmap_cli.py validate`，查询 `学习路线`、`课程路线`、`知识正文`、`学习记录`、`学习中`、`阻塞`、`待复习`、`已掌握`、`待核验` 和 `待补齐`。
2. 用 Obsidian CLI 读回全部初始文件、Properties、Wikilink 与 Base；打开 Base 并检查 `dev:errors`。
3. 导航入口更新仍使用 Obsidian CLI，写前读、写后读，避免重复。
4. 满足类型质量门的正文才设 `已发布`；学习记录保持真实初始状态。
5. 让用户先阅读前置与概述，本轮不进入正式阶段。

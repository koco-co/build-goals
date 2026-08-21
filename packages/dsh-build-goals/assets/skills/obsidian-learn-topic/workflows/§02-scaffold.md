# 初始化已确认路线

仅在用户确认完整预览后执行。

## 1. 准备产物

1. 完整读取 `rules/obsidian-cli-contract.md`、`rules/properties-and-base.md` 和所有需要的模板。
2. 解析当前 `SKILL.md` 的真实目录作为 `<SKILL_DIR>`；用 `mktemp -d` 创建本轮独立的 Vault 外 `<TEMP_DIR>`，不复用固定临时路径。
3. 在 `<TEMP_DIR>` 复制并填写：
   - `templates/topic-roadmap.template.base`
   - `templates/overview-prerequisites.template.md`
   - `templates/overview-5w1h.template.md`
   - 其他已确认的概述笔记
   - `templates/scaffold-spec.template.json`
   - 仓库路线改用 `templates/repository-scaffold-spec.template.json` 与 `templates/repository-prerequisites.template.md`，并在所有初始笔记保留 `roadmap_kind: repository`；不使用通用外层目录。
4. 用安全的 JSON/YAML 序列化写显示名、路径段、Tag、成果与版本，禁止对原始主题名做裸字符串替换；将 `file.inFolder(<JSON 编码的根路径>)` 整体再次 JSON 编码后填入 Base 的 `{{ROADMAP_FILTER_JSON}}`。
5. 删除无信息价值的空章节和所有未替换占位符。
6. Base 根过滤器必须锁定最终主题根路径，`学习路线` 按稳定路线序号升序。

## 2. Dry-run

运行：

```bash
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" scaffold --spec "<TEMP_DIR>/spec.json"
```

检查：

- 路径为 Vault 相对路径，且不在保护区。
- 根目录只有 `<主题路径段>-Roadmap.base` 文件和编号目录。
- 只有 `01-<主题>概述` 在初始化时含 Markdown。
- 仓库路线只有 `01-项目概述` 在初始化时含 Markdown，并严格使用 `rules/repository-learning-policy.md` 的固定外层路线。
- 其他空目录和固定预留的 `99-assets` 都会创建 `.gitkeep`。
- 目标路径不存在且没有命名冲突。

Dry-run 与用户确认的树不一致时停止。

## 3. Apply

Apply 前记录目标笔记相关的 `obsidian unresolved` 基线，并运行 `obsidian dev:errors clear`，避免把旧错误算作本次失败。

运行：

```bash
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" scaffold --spec "<TEMP_DIR>/spec.json" --apply
```

不得绕过脚本直接写 Vault。

## 4. 导航与验证

1. 通过 `obsidian read` 读取最近的导航入口。
2. 通过 `obsidian append` 加入仅由已验证 Base 路径构成的 Wikilink；路径必须先通过本合同的安全字符检查，不附加未经序列化的主题显示名，不覆盖整篇导航。追加后立即读回并确认链接只新增一次；发现并发变化或重复入口时停止并进入维护流程。
3. 运行：

```bash
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" validate --spec "<TEMP_DIR>/spec.json"
```

4. 分别查询六个约定视图，使用 `obsidian open path="<主题 Base 路径>"`、`obsidian base:views`、`obsidian dev:errors` 和截图确认 Base 能真实渲染且排序有效。
5. 对新增笔记检查 Properties、H1、Wikilink、来源、版本和空章节，并比较本次目标的未解析链接基线。
6. 满足发布门槛的概述笔记通过 `write-note` 快照替换改为 `status: 已发布` 并读回；未满足的保持 `待核验`，本轮按阻塞报告。
7. 验收完成后只清理本轮精确 `<TEMP_DIR>`；路径无法证明时保留并报告。

## 5. 停止点

展示概述文件、Base 入口、已验证项和未验证项，让用户先阅读概述。给出：

```text
Codex: $obsidian-learn-topic 继续学习 <主题>
Claude: /obsidian-learn-topic 继续学习 <主题>
```

本轮不进入正式阶段。

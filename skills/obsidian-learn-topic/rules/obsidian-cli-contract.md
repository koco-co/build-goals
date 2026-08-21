# Obsidian CLI 操作合同

## 不可绕过的边界

- Vault 内容只通过 `obsidian` CLI 或由 `obsidian eval` 调用的 Vault API 读写。
- Skill 自身文件、Vault 外临时规格和测试夹具不属于 Vault 内容，可使用正常开发工具。
- 首次运行先执行 `obsidian help`；CLI 不可用时停止。
- 当前 CLI 某些失败仍可能返回退出码 0。除退出码外，必须检查 `Error:`、脚本 sentinel 和操作后状态。
- `.gitkeep` 不进入 Obsidian 文件索引；只用 `app.vault.adapter.exists/write/remove` 处理，不用 `obsidian read/file/create`。
- 每条命令都显式选择计划中的 Vault；先比较 `obsidian vault=<名称> vault info=path` 与计划内绝对路径，完全一致才继续。

## 驱动脚本

所有脚本使用 Python 标准库，并通过子进程调用 `obsidian`。默认 dry-run。

`scripts/repository_cli.py` 是例外的 Vault 外源码驱动：它只用 argv-safe Git/GitHub CLI 子进程准备或审计隔离 checkout、生成 Patch 与测试证据，永不写 Vault。Vault 内仓库学习笔记仍只能经 `roadmap_cli.py` 和 Obsidian CLI 写入。

`scripts/exercise_cli.py` 是普通代码练习的另一项 Vault 外驱动：它要求用户确认的外部根路径已存在，只在该根下创建一个已预览的编号练习目录；用 argv、清洁环境、显式授权和 append-only evidence 运行公开命令。它不创建根路径、不写 Vault、不初始化 Git，也不替代仓库 Patch 驱动。

先把 `<SKILL_DIR>` 解析为当前 `SKILL.md` 所在的真实目录，不依赖当前工作目录。每次运行用 `mktemp -d` 创建独立临时目录并记录其精确路径，不使用共享的固定 `/tmp/learn-topic`。

```bash
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" probe
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" scaffold --spec "<TEMP_DIR>/spec.json"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" scaffold --spec "<TEMP_DIR>/spec.json" --apply
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" validate --spec "<TEMP_DIR>/spec.json"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" write-note --plan "<TEMP_DIR>/note-plan.json"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" write-note --plan "<TEMP_DIR>/note-plan.json" --apply
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" renumber --plan "<TEMP_DIR>/renumber.json"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" renumber --plan "<TEMP_DIR>/renumber.json" --apply
```

普通代码练习使用独立入口：

```bash
python3 "<SKILL_DIR>/scripts/exercise_cli.py" scaffold --plan "<TEMP_DIR>/exercise-plan.json"
python3 "<SKILL_DIR>/scripts/exercise_cli.py" authorize --manifest "<EXERCISE_DIR>/.learn-topic/manifest.json" --command "<COMMAND_ID>" --confirmed-at "<ISO_DATETIME>"
python3 "<SKILL_DIR>/scripts/exercise_cli.py" run --manifest "<EXERCISE_DIR>/.learn-topic/manifest.json" --command "<COMMAND_ID>"
python3 "<SKILL_DIR>/scripts/exercise_cli.py" add-variant --plan "<TEMP_DIR>/variant-plan.json"
```

所有入口默认 dry-run；对应 Apply 需要追加 `--apply`。执行前完整读取 `rules/code-exercise-policy.md`。

`trash-validation` 只用于清理带随机运行标识、路径名和标记笔记三重校验的验收夹具，不属于正常学习路线维护入口：

```bash
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" trash-validation --spec "<TEMP_DIR>/spec.json" --run-id "<RUN_ID>"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" trash-validation --spec "<TEMP_DIR>/spec.json" --run-id "<RUN_ID>" --apply
```

它只能把精确命名为 `99-Learn-Topic-Validation-<RUN_ID>` 且库存与标记匹配的测试根目录放入回收站；不得用于用户路线或普通临时目录。

验收和报告完成后，只清理本轮 `mktemp` 返回的精确目录；路径不明确时保留并报告，不扩大删除范围。

## Scaffold spec

从 `templates/scaffold-spec.template.json` 复制到 Vault 外临时目录并填写。内容文件也放在临时目录；脚本读取后通过 `obsidian eval` 写入 Vault。

约束：

- `root` 必须是安全的 Vault 相对路径。
- `base.path` 必须是根目录下的 `<根目录名>-Roadmap.base`；例如主题根为 `.../Playwright` 时，Base 为 `.../Playwright/Playwright-Roadmap.base`。
- 主题根内所有目录（包括正式阶段子目录）都使用两位数字前缀；初始化固定预留 `99-assets`，资产统一进入其中。
- 顶层目录通过 `role` 明确标记 `overview`、一个或多个 `formal`、`extension`、`review`、`records` 和 `assets`。学习记录目录位于 `99-assets` 前最后一个连续编号；仓库路线固定为 `10-学习记录`。
- 初始化 Markdown 只能位于 `01-<主题>概述` 与学习记录目录，文件使用各自连续的 `§NN-`；概述中创建路线图、前置与主题概述，记录目录中为两篇正文各创建独立记录。
- 已填充的 overview 与 records 不保留 `.gitkeep`；其余空目录设置 `keep: true`。
- `curriculum_plan_file` 必须指向 Vault 外的完整课程计划 JSON；脚手架验证其单元 ID、计划路径、知识点唯一归属、前置拓扑、正文类型和验收方式，并要求 `§01-学习路线图.md` 在确定性可见表格与 `learn-topic-curriculum` 机器合同中完整保存同一计划；任一可见行漂移都会阻断。
- 主题必须拆分为 `topic.display`、安全的 `topic.path_segment` 与 Obsidian-safe 的 `topic.tag`；JSON/YAML 用安全序列化生成，不对原始主题名做裸替换。
- Base 根过滤器先生成 `file.inFolder(<JSON 编码的 root>)`，再把整个表达式 JSON 编码后填入 `{{ROADMAP_FILTER_JSON}}`。例如 root 为 `Learning/Python` 时填入 `"file.inFolder(\"Learning/Python\")"`；含单引号的合法路径也必须通过同一序列化过程处理。Vault 路径和主题路径段拒绝双引号、反引号、`$`、反斜杠和控制字符。
- 目标存在、路径逃逸、保护区路径、重复路径或未替换占位符都会阻断。
- `roadmap_kind: repository` 时必须使用固定仓库外层路线、仓库专用模板和完整 Commit 锚点；驱动拒绝缺失、改名或重排的外层阶段。

## Repository workspace plan

从 `templates/repository-workspace-plan.template.json` 复制到 Vault 外独立计划目录。`checkout_path` 的外部根位置必须由用户提供并最终确认，模型只可推荐；先运行 `audit` 或 dry-run `prepare`。Apply 只对该精确路径创建 detached Commit checkout，不递归 submodule、不执行 hooks 或安装脚本。`audit` 只回传脱敏 canonical 身份与 hash，错误 origin 直接阻断。Patch 验收仅接受批准文件、非空二进制 Patch、`git diff --check` 和 argv 形式的相关测试；测试使用清洁环境且前后重新核对 HEAD、文件集合与 Patch hash。证据输出必须留在计划目录，且不得包含凭据、完整日志或机器路径写回 Vault。

## Ordinary code exercise plan

从 `templates/code-exercise-manifest.template.json` 复制到本轮 Vault 外计划目录。`workspace_root` 必须由用户提供并最终确认、已经存在且位于 Vault 外；驱动不会创建它。starter 和公开测试的 `content_file` 只能来自计划目录。

- `scaffold` 只创建一个尚不存在的 `NN-练习名/`；独立脚本也使用 `NN-名称.扩展名`，多文件项目保留生态文件名。
- 计划必须公开一个必需核心测试、全部 argv、环境、超时、运行时写入、清理范围、评分规则和三级提示；隐藏命令、solution/answer 文件、shell 命令字符串或敏感环境会被拒绝。
- `authorize` 把用户对当前 manifest hash 与精确命令的确认写入包内；manifest 改变使旧授权失效。
- `run` 使用 argv、清洁环境和 macOS `sandbox-exec` 写隔离，不继承宿主秘密；只放行 manifest 声明的运行时路径与独立临时 HOME，默认禁止网络。隔离不可用时写入 `blocked` attempt 并停止，不降级执行。
- 非用户可编辑的公开测试、配置和变式以 SHA-256 绑定 manifest；变化后旧授权不能继续。运行同时核对外部工作区兄弟内容与 `.learn-topic` 元数据，恢复被篡改的既有 evidence 并把结果记为阻塞。
- 每次 Apply 新增 `attempt-NN.json`；超时、启动崩溃、失败、越界写入或元数据破坏都不会报告为通过。
- `add-variant` 只在已有真实尝试后增加公开、非必需的变式命令；最多两个挑战，并使旧授权失效。
- 自动清理只触及 manifest 同时列入 runtime/cleanup 的临时输出；源码、manifest、authorization 和 evidence 不删除。

## Note write plan

从 `templates/note-plan.template.json` 复制到本轮 Vault 外临时目录；Markdown 内容和旧快照文件也必须位于该临时目录或其子目录。`write-note` 是主题路线内学习笔记及其属性状态更新的统一写入入口；它不用于路线外导航笔记。

- `mode: create` 要求目标不存在；首次写入空阶段时可设 `remove_gitkeep: true`。
- `mode: replace` 要求 `expected_current_file`，且 Vault 当前内容必须与快照逐字一致；发现并发变化时停止。
- 两种模式都要求主题根存在 `<根目录名>-Roadmap.base`，且 Base 的精确根过滤器和十个三层视图仍有效；普通编号目录不能伪装成学习路线。
- Create 只接受该阶段下一个连续 `§NN`：空阶段必须从 `§01` 开始并同时移除现有 `.gitkeep`；已有课程笔记时 `.gitkeep` 必须已经不存在。实验项目的生态文件名不参与课程编号。
- 三层合同用 `content_contract: three-layer`。路线图、知识正文、学习记录分别使用 `curriculum-map`、`knowledge-note`、`learning-evidence`；四类正文还必须声明 `document_type`。旧 note plan 未声明时只用于既有合同兼容，不作为新路线模板。
- 三层 note plan 必须同时提供 `curriculum_plan_file` 与 `records_directory`。驱动先把外部计划与 Vault 内路线图的机器合同逐字段比较，再校验正文的计划路径、类型、成果、知识点归属、硬前置和验收方式；学习记录只能直属于指定记录目录并链接计划正文。Base 的十个视图不仅要同名存在，其记录层过滤器也必须保持正确。
- 新学习记录为 `学习中` 时，路线内不能还有另一个 `learning-evidence` 处于 `学习中`；正文、路线图、`99-assets` 和非 `§NN` 实验 Markdown 不参与这项扫描。
- 知识正文 `已发布` 要求非空来源和有效 `verified_at`；学习记录 `已掌握` 还要求双向链接的正文已发布且 `coverage_status: 完整`，并具有真实掌握证据、验收方式、验收日期及复习日期。`§01-学习路线图.md` 必须保留合法 `roadmap_status`。
- 仓库锚点不得通过省略 `roadmap_kind` 降级为普通主题。写入 `graduation_status: passed` 或 `roadmap_status: 已完成` 时，note plan 必须同时提供本轮计划目录内的 `repository_patch_file` 和 `repository_evidence_file`；驱动核对仓库、Commit、许可证、上游状态、批准/实际文件、Patch hash、测试 argv 与退出码。
- Dry-run 会用 Obsidian YAML 解析器检查 Frontmatter、必需 Properties、规范元数据、H1、路径和占位符。
- Apply 通过 base64 JSON payload 调用 `obsidian eval`，写入后逐字读回；失败时恢复旧内容，或将刚创建的笔记放入可恢复回收站并恢复 `.gitkeep`。
- Markdown、路径、Tag 和属性值不得直接插入 shell 命令、JavaScript 字符串或 `content="..."`；所有动态数据都交给驱动的 argv 与 JSON/base64 边界。

## Renumber plan

从 `templates/renumber-plan.template.json` 复制并填写。所有来源和目标必须在同一主题根目录内。脚本先把来源移动到唯一的 `__lt_tmp_<run_id>_<n>` 可见临时目录，再移动到目标，避免 `02 → 03` 与既有 `03` 冲突。插入新目录时把批量映射、`add_directories` 和受影响笔记的 `property_updates` 放在同一计划内；`stage_title` 与 `stage_order` 必须同步为最终目录编号。

用户确认前只运行 dry-run。Apply 后检查：

- 来源不存在，目标存在。
- 不残留 `__lt_tmp_*` 或 `__lt_rollback_*`。
- Base 查询仍成功。
- 受影响笔记的 `stage_title`、`stage_order` 与最终目录一致。
- Wikilink、嵌入和导航没有新增真实断链。

## 普通命令

使用 `obsidian help` 中实际存在的命令：

- 搜索：`search`、`search:context`
- 读取：`read`、`properties`、`outline`、`links`、`backlinks`
- 创建和维护：学习笔记正文与属性使用 `write-note` 驱动；路径移动使用 `move`、`rename`；删除使用 `delete`
- Base：`bases`、`base:views`、`base:query`
- 验收：`open`、`dev:errors`、`dev:console`、`dev:screenshot`

不使用帮助中不存在的 `silent` 或假定命令。删除默认不加 `permanent`。

创建第一篇正式笔记时，只有 `write-note --apply` 写入和读回成功后，驱动才用 Adapter 删除 `.gitkeep` 并验证其已不存在。普通删除命令无法看见这个点文件。

## 结果报告

记录精确命令、退出码、结构化 sentinel、通过/失败/错误/跳过数量和目标路径。若 UI、联网、第三方运行或用户掌握未被真实观察，单独列为未验证。

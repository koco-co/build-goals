# 学习一个知识单元

本工作流必须遵守 `rules/learning-record-contract.md`。教学不是聊天输出，而是一次“笔记落盘 → 一题一答 → 证据回写”的可恢复事务。

## 1. 章前核验

1. 读取 `rules/research-policy.md`、`rules/obsidian-cli-contract.md`、`rules/properties-and-base.md` 和 `templates/lesson.template.md`。
2. 对本章进行当前版本深度核验；至少包含一手来源。
3. 检查本章硬前置、既有相似笔记和上游/下游 Wikilink。
4. 先建立本章覆盖矩阵：把学习目标拆成必需术语/API、核心机制、边界/反例、最小实践和验收证据；对框架主题还要核对官方文档目录与当前绑定签名。未纳入本章的内容写入明确的后续单元，不用含糊的“等深入再说”代替边界。
5. 仓库路线同时读取 `rules/repository-learning-policy.md`：所有源码结论锁定锚点 Commit；只沿已确认核心切片推进。进入 `07-最小修复实践` 时，完整执行 `workflows/§07-open-source.md` 的 Patch 确认与验证门。
6. 仅对非仓库普通路线判断本单元是否为代码型：目标包含编写、修改或运行代码时，完整读取 `rules/code-exercise-policy.md`，并在笔记预览后执行 `workflows/§08-code-exercise.md`；纯概念单元只安排主动回忆或场景题。`roadmap_kind: repository` 不执行本步，继续使用第 5 步的仓库 Patch 分支。
7. 一手资料不足时保持 `待核验` 并停止，不提供貌似可运行的完整实现。

## 2. 创建或更新笔记

1. 选择所在编号目录的下一个 `§NN-标题.md`。
2. 把本单元拆成可单独解释和验收的知识点，给每个知识点稳定 ID，建立“本单元知识点清单”和覆盖矩阵；同步计算 `knowledge_points_total`、`knowledge_points_covered`、`knowledge_points_pending`。
3. 在本轮 Vault 外 `<TEMP_DIR>` 中生成完整 Markdown 和 `templates/note-plan.template.json` 的副本。新建使用 `mode: create`；更新先用 CLI 读取精确快照，把快照保存到 `expected_current_file`，使用 `mode: replace`。
4. 先 dry-run，再执行已确认范围内的写入；首次向空阶段写笔记时设 `remove_gitkeep: true`：

```bash
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" write-note --plan "<TEMP_DIR>/note-plan.json"
python3 "<SKILL_DIR>/scripts/roadmap_cli.py" --vault "<VAULT_NAME>" write-note --plan "<TEMP_DIR>/note-plan.json" --apply
```

驱动会通过 base64 JSON 把内容交给 `obsidian eval`，创建或比较后替换、精确读回，并仅在新建成功后用 Adapter 删除和验证该阶段 `.gitkeep`。不得把 Markdown、路径或属性值裸拼进 shell/JavaScript。
5. Apply 后必须用 Obsidian CLI 精确读回；读回失败时停止，不在聊天中继续教学。笔记按内容需要包含：
   - 一句话结论与学习目标。
   - 准确机制、类比及类比边界。
   - 替代方案或竞品比较。
   - 由浅入深的步骤、例子或实践。
   - 有来源和版本范围的真实踩坑、解决方案和失败边界。
   - 重点、面试问题、追问和解答技巧。
   - 主动回忆题、最小实践与通过标准。
   - `## 本单元知识点清单`、题目状态和逐题作答记录；没有用户回答的知识点写为待回答或需补充。
   - 关联 Wikilink、来源、`verified_at` 和 `version_scope`。
5. 普通代码型单元在正文中公开一个核心练习的目标、文件顺序、测试点、argv、通过标准、评分规则、三级提示和最多两个可选挑战。实际代码不写入 Vault。
6. 普通实验文件按 `rules/code-exercise-policy.md` 编号：独立脚本使用 `NN-名称.扩展名`；多文件项目只编号练习目录，内部保留生态标准名称。

## 3. 教学与验收

1. 笔记读回成功后，先讲当前知识块，再只发送一道自洽短题；题目发送后立即停止本轮，不追加新知识或第二道题。
2. 每次主动回忆、场景题或复习追问都按 `SKILL.md` 的 `Question contract` 组织，只发送四部分：进度状态行、`场景`、`问题`、`提示`。场景只放必要的 1～3 句和代码片段；问题只问一个核心点。对仓库/Vibe Coding 单元默认问架构、职责、边界和用户流程，不把内部状态、API 或生成代码细节当作题目主体；提示只说明回答方式；验证目标、通过标准和答案留在模型内部评定或笔记中，不要全部展示给用户。
3. 用户回答后用三句以内反馈：`结论`、`原因/遗漏`、`下一步`；随后读取精确旧快照，通过 `write-note` compare-and-swap 回写题目状态、作答记录、薄弱点、知识点计数和掌握证据。回写读回完成前不得发下一题或进入下一单元。
4. 阅读第三方源码无需额外确认；安装、脚本执行、Docker、系统修改、账号、付费 API 或敏感凭据按安全门请求确认。
5. 代码型单元先让用户完成真实尝试，再按 `workflows/§08-code-exercise.md` 授权和运行公开命令；笔记只持久化 `exercise_id`、`attempt_id`、结果摘要、关键失败和得分，不保存机器绝对路径或完整日志。
6. 根据回答或实际运行证据评分：
   - 未通过：`learning_status: 学习中`，记录薄弱点。
   - 通过：先检查内容发布门槛，写入 `mastery_score`、`mastery_evidence`、`assessment_type`、`assessment_at`、`last_reviewed`、`next_review` 和 `review_count`；只有 `status: 已发布` 且证据非空时才设 `learning_status: 已掌握`。
   - 覆盖不足：无论用户局部回答或实验是否通过，都保持 `coverage_status: 部分覆盖`；补齐内容后重新核验，不删除原有掌握证据。
7. 代码命令通过后仍要求用户解释关键实现和边界；模型代写后的绿灯不能单独作为掌握证据。
8. 首次掌握安排 `+1d`；第 1 次复习通过后 `+7d`；第 2 次通过后 `+30d`；薄弱时缩短间隔。
9. 所有属性更新都重新读取当前快照，生成完整更新内容，并经 `write-note` 的 compare-and-swap 替换后读回；发布门槛未通过时保持 `待核验` 和 `学习中`。只讲过但没有用户答案的知识点保持 `knowledge_points_pending`，不得写入掌握证据。
10. 如果后续审计发现课程遗漏，执行“内容纠偏”而不是“用户重考”：保留原 `mastery_evidence`，把 `content_audit_note` 写明遗漏、补充来源和影响范围；只有新增目标影响掌握标准时，才安排针对性补测。
11. 当前单元通过后，锚点 `roadmap_status` 仍保持 `进行中`；若下一篇概述笔记已存在，把它切换为 `学习中`。正式阶段下一篇尚未创建时不造空笔记，由下一次“继续学习”请求依据概述中的持久路线计划创建。

## 4. 停止

汇报课程笔记路径、知识点总数/已验收/待回答数量、当前题目状态和已写回证据。若正在等待用户回答，只发送该题并停止；不要在同一轮给出第二个单元。单元事务完成后再给出可直接发送的下一次自然语言指令；显式 Skill 语法仅作为可选补充。

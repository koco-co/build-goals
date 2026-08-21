# 执行普通代码练习

本工作流只服务 `roadmap_kind` 非 `repository` 的普通路线。GitHub 仓库路线即使包含写代码或运行测试，也只执行 `workflows/§07-open-source.md` 与 `scripts/repository_cli.py`，不得进入本分支。

## 1. 判定与设计

1. 完整读取 `rules/code-exercise-policy.md`、`rules/obsidian-cli-contract.md` 和 `templates/code-exercise-manifest.template.json`。
2. 只有本单元目标要求编写、修改或运行代码时进入本分支；纯概念单元返回主动回忆或场景题。
3. 设计一个必做核心练习和最多两个可选挑战。公开文件、核心测试、argv、必要测试点、通过标准、评分规则和三级提示；交给用户的任务只发必要场景、唯一任务和反馈格式，详细评分标准留在练习说明或内部评定中。
4. starter 与测试可以由模型提供；核心解答不得出现在首次尝试前。不要用“把它写出来”“试着修一下”这类缺少文件范围和验收标准的孤立指令。

## 2. 确认外部根路径

1. 根据技术生态给出一个推荐位置和理由，但不把推荐当成事实路径。
2. 要求用户提供并最终确认一个已经存在的 Vault 外绝对根路径。没有确认时只交付练习预览，不运行 scaffold，也不创建根目录。
3. 展示将在根路径下创建的 `NN-练习名/`、文件清单、执行顺序和持久化的 `.learn-topic/` 证据结构。

## 3. 初始化练习包

1. 在本轮独立 `<TEMP_DIR>` 中复制并填写 `templates/code-exercise-manifest.template.json`；starter 与公开测试正文也放在该计划目录或子目录。
2. 先 dry-run，再对已确认范围 Apply：

```bash
python3 "<SKILL_DIR>/scripts/exercise_cli.py" scaffold --plan "<TEMP_DIR>/exercise-plan.json"
python3 "<SKILL_DIR>/scripts/exercise_cli.py" scaffold --plan "<TEMP_DIR>/exercise-plan.json" --apply
```

3. Apply 只创建已存在外部根下的练习子目录，绝不创建根路径、初始化 Git 或写入 Vault。

## 4. 用户尝试与命令授权

1. 让用户先写；不得把完整解法写入 starter。用户报告完成后，先固化当前文件状态，不替用户改代码。
2. 运行前 dry-run 展示命令合同：

```bash
python3 "<SKILL_DIR>/scripts/exercise_cli.py" authorize --manifest "<EXERCISE_DIR>/.learn-topic/manifest.json" --command core-test --confirmed-at "<ISO_DATETIME>"
python3 "<SKILL_DIR>/scripts/exercise_cli.py" authorize --manifest "<EXERCISE_DIR>/.learn-topic/manifest.json" --command core-test --confirmed-at "<ISO_DATETIME>" --apply
python3 "<SKILL_DIR>/scripts/exercise_cli.py" run --manifest "<EXERCISE_DIR>/.learn-topic/manifest.json" --command core-test
python3 "<SKILL_DIR>/scripts/exercise_cli.py" run --manifest "<EXERCISE_DIR>/.learn-topic/manifest.json" --command core-test --apply
```

3. 用户的确认必须覆盖 dry-run 展示的 cwd、argv、环境、超时、写入和清理范围。命令或 manifest 改变后重新确认。
4. 需要新增公开变式测试时，完整展示后使用 `add-variant` 的 dry-run/Apply；旧授权随 manifest hash 改变而失效。

## 5. 反馈、证据与掌握

1. 失败时按知识点 → 文件/函数/边界 → 局部伪代码/最小片段的顺序给提示。完整解法只在用户明确请求或已有真实尝试后提供。
2. 每次 Apply 都生成新的 `attempt-NN.json`；不得覆盖。只把 `exercise_id`、`attempt_id`、测试摘要、关键失败和得分写回 Obsidian 笔记。
3. 模型修改用户代码前先保留本次尝试，并另行取得修改授权；模型代写结果不得单独作为掌握证据。
4. 测试通过后仍要求用户解释关键实现与边界。满足 `rules/code-exercise-policy.md` 的掌握门后，才按 `workflows/§04-learn-unit.md` 更新课程笔记。
5. 停在当前单元，不自动开始下一个练习。

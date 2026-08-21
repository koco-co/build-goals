# 恢复学习主题

## 1. 定位主题

1. 运行 `obsidian bases` 得到候选；逐个用 `obsidian read` 验证它同时包含 `学习路线`、`学习中`、`阻塞`、`待复习`、`已掌握`、`待核验` 六个视图和精确主题根过滤器，排除普通 Base。
2. 对每个合格 Base 定位 `01-*概述/§01-前置准备.md` 锚点，通过 CLI 读取 `roadmap_status`；再查询 `学习中`、`阻塞` 和 `待复习`，按 Base 路径聚合为主题，不把多个单元误算成多个主题。
3. 用户未给主题时：
   - 只有一个 `roadmap_status: 进行中` 的主题：恢复它；即使刚完成一个单元、暂时没有 `learning_status: 学习中` 也不能漏掉。
   - 多个进行中主题：列出主题、当前或上次完成单元和上次更新时间，只询问选择哪一个。
   - 没有进行中主题：再区分阻塞、已完成和不存在，并询问要开始或恢复的主题。
4. 不从聊天记忆猜测主题，不自动恢复已掌握、已归档或阻塞主题。

## 2. 确认状态

1. 读取主题 Base、锚点、概述中的“学习路线与阶段成果”、当前阶段最近笔记和到期复习项。
2. 对当前 `学习中` 笔记读取 `knowledge_points_total`、`knowledge_points_covered`、`knowledge_points_pending` 和最近一题的状态。存在待回答题或待验收知识点时，恢复到该题；在题目完成回写前不得选择新的单元。
3. 锚点为 `roadmap_kind: repository` 时，先完整读取 `rules/repository-learning-policy.md`，用 `scripts/repository_cli.py upstream-check` 只读比较上游。始终报告 `changed` 信号，但只有 `requires_decision: true` 才暂停并确认继续固定基线、迁移基线或阻断；已经确认的稳定 tag 使用 `fixed-baseline`，默认分支继续前进时不重复卡门。不自动更新 checkout。
4. 若存在到期复习，建议“先复习还是继续新课”，等待用户选择。
5. 若主题被硬前置阻塞，报告阻塞证据和可直接发送的前置主题学习指令，不继续主线。
6. 若概述尚未通过扫盲检查，返回概述问答，不创建正式单元。

## 3. 选择下一单元

若当前笔记仍有待回答题或待验收知识点，先按 `rules/learning-record-contract.md` 发送并完成当前题；题目发送后立即停止本轮，用户回答后通过 `write-note` compare-and-swap 回写，在回写前不得选择新单元。只有当前单元事务完成后，才按照持久路线计划、目录顺序、依赖和现有 `learning_status` 选择下一个单元。若下一篇已存在且是 `未开始`，通过 `write-note` 快照替换把它切换为 `学习中`；若正式单元尚未创建，按 `workflows/§04-learn-unit.md` 创建它。已掌握内容不重复创建；失效内容先进入核验或维护流程。

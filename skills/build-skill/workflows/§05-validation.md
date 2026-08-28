# 验证

按变更事实选择静态检查、设计落实审查、内容审查、文案审查、内容回归、独立审查、场景验证和平台验证；没有适用依据的检查不执行。已选检查不能互相替代。

## Phase 1：静态检查

优先运行目标仓库已有命令。没有等价能力时，使用本 Skill 的校验器：

```bash
python3 scripts/validate_skill.py /path/to/skill --profile portable --strict
```

根据目标平台选择：

```bash
python3 scripts/validate_skill.py /path/to/skill --profile claude --strict
python3 scripts/validate_skill.py /path/to/skill --profile codex --strict
python3 scripts/validate_skill.py /path/to/skill --profile zcode --strict
```

该脚本已覆盖结构、Frontmatter、引用、工作流编号、命名、空文件与软链接；后续各项清单只处理脚本无法判断的内容与场景项。

## Phase 2：设计落实审查

逐项执行 `checklists/design-review.md`：

- 设计中的每个目标是否实现；
- Frontmatter 是否与字段决策矩阵一致；
- 每个目录是否仍然必要；
- Hooks、CLI、脚本和 Skill 的职责是否正确；
- 是否出现重复规范源；
- 是否存在未经确认的范围扩张。

发现偏差时先修复设计或实现，再继续验证。

## Phase 3：内容审查

逐项执行 `checklists/content-review.md`，回答“行为是否正确、完整”：

- 已确认路由、步骤、可复现失败和完成条件是否闭合；
- 决策、权限和平台行为是否符合确认结果；
- Frontmatter 可选字段是否有真实依据；
- 输出与验证是否足以完成用户目标；
- 未验证和阻塞内容是否准确。

存在语义歧义时必须在本阶段解决，不把行为决策留给文案审查。

## Phase 4：文案审查

内容审查通过后执行 `checklists/copy-review.md`。需要改写参考时读取 `examples/copy-review.example.md`。

检查自然度、清晰度、简洁度、术语一致性、正反向表达和示例质量。只修改表达，不改变触发、流程、范围、权限、失败处理或验收标准。

## Phase 5：内容回归

文案发生修改后重新执行受影响的 `checklists/content-review.md` 项目，并重跑相关静态检查。确认：

- 行为和顺序没有变化；
- 确认门禁与权限没有被弱化；
- 必要条件和完成证据没有被删减；
- 新措辞没有产生歧义或平台差异。

## Phase 6：独立 Reviewer

以下变更必须读取 `prompts/reviewer.agent.md` 并调用独立 Reviewer：

- 新建 Skill；
- 整体重构；
- 改变触发或 Frontmatter；
- 改变权限、上下文或平台行为。

Reviewer 只读审查并分别输出内容审查结果与文案审查结果。主 Agent 修复 Finding 后，再请求 Reviewer 复查。微小且不改变语义的修改可以省略；平台无法提供独立 Agent 时标记“未完成独立审查”，不得伪造结果。

## Phase 7：真实场景验证

只验证本次目标实际包含的场景：调用策略、输入分支、可复现缺陷、平台差异和交付状态。不得为了覆盖用户调用、模型调用、参数化、通用、项目级、升级、失败等类别而制造目标 Skill 不具备的行为。

其余场景遵循 `rules/quality-standard.md` 的决策与确认原则。

使用临时目录、夹具或隔离分支，避免验证污染真实项目。

## Phase 8：跨平台验证

分别记录：

- 平台的安装位置和调用配置；
- 调用权限是否符合目标设计；
- 平台专属配置是否隔离；
- 核心工作流是否保持单一规范源；
- 是否执行了真实运行测试；
- 未能运行时，完成了哪些静态检查。

## Phase 9：失败闭环

实际出现的失败项记录：

```text
失败项：
复现命令或场景：
原因：
修复：
重跑范围：
最终结果：
```

只有修复后重新执行受影响检查并通过，才可标记为已验证。

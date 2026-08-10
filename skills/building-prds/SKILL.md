---
name: building-prds
description: 针对已有软件项目的全部产品功能，或尚未成形的产品想法，必须联网调研当前竞品、活跃开源项目与适用的官方规范，逐项确认所有产品决策，并在当前目录生成或更新 docs/PRD需求文档.md。
compatibility: 当前适配 Claude Code 与 Codex；需要联网调研、读取项目文件，并写入当前目录的 docs/PRD需求文档.md。
disable-model-invocation: true
metadata:
  author: koco-co
  version: "1.0.0"
---

# Outcome

将已有项目的完整功能与用户体验，或尚不完整的产品想法，整理成所有决策均已确认、可以直接验收且不含技术实现设计的单一 PRD 文档。

## Routing

- 用户提供已有项目并要求梳理全部功能时，执行“已有项目”分支，覆盖所有产品角色、产品界面、入口、交互状态和用户可见行为。
- 用户只提供初步想法或零散思路时，执行“产品想法”分支，先调研并补全产品定义，再生成完整 PRD。
- 当前会话已通过 `grill-me` 确认同一主题时，复用确认结论；规定的调研已经完成则直接写入 PRD，否则只补充缺失调研及其引出的新决策。
- 普通编码、现有 PRD 评审、技术架构、数据库、API、部署、任务拆解或商业计划不属于本 Skill；明确说明适用边界后停止，不生成其他文档代替 PRD。

## Steps

1. 调研产品事实
   - 完整读取 `workflows/§01-research.md`。
   - 区分项目事实、用户已确认决策和外部最佳实践，不向用户询问能够自行查明的内容。
   - 完成条件：产品界面、入口与流程已经完整盘点，规定的联网调研覆盖已经完成，所有来源均可复核。

2. 确认所有产品决策
   - 若当前会话已经通过 `grill-me` 得到确认结论，且调研充分，直接沿用确认结论，不重复提问。否则按照决策顺序，一次只询问一个会改变 PRD 的问题；每题都给出基于事实与调研的推荐答案，直到用户明确确认所有产品决策。
   - 不得用假设、待定项或开放问题代替确认；全部确定前不得写入目标 PRD。
   - 完成条件：功能范围、角色、输入、输出、交互、状态、最终文案、产品质量要求和验收结果都已确定，不存在冲突或多种解释。

3. 编写或更新 PRD
   - 完整读取 `rules/prd-quality-standard.md`、`workflows/§02-authoring.md` 和 `templates/prd.template.md`。
   - 用户需要输入范式时读取 `templates/prd-intake.template.md`；需要核对输出范式时读取 `examples/prd.example.md`。
   - 将完整内容一次性创建或规范化更新到当前目录的 `docs/PRD需求文档.md`。
   - 完成条件：固定路径只有一份权威 PRD，现有有效需求已保留，冲突、重复和已确认废弃内容已处理。

4. 验证并交付
   - 完整读取 `workflows/§03-validation.md` 和 `checklists/semantic-acceptance.md`。
   - 使用当前 Skill 目录中的 `scripts/validate_prd.py` 对目标文件运行严格校验；失败时修复并重跑。
   - 完成条件：机械检查和语义清单均通过，目标项目没有发生 PRD 之外的写入。

## Delivery

- 最终产物固定为当前目录的 `docs/PRD需求文档.md`。
- PRD 必须包含产品定位、用户与角色、范围、功能地图、逐功能设计、用户预输入、期望输出、完整交互与最终文案、产品质量要求、验收标准和调研来源。
- 最终回复给出目标文件路径、实际调研的竞品、开源项目和官方规范数量，以及实际执行的校验命令与结果；不得把未执行的真实产品流程描述为已验证。

## Guardrails

- 显式调用只授权创建或更新目标 PRD；不得修改目标项目代码、配置、数据、凭据、任务系统或外部服务状态。
- 联网调研必须优先读取公开的一手来源，不上传项目私有代码、用户数据、凭据或未公开文档。
- 可以检查代码和运行安全的本地产品流程以查明产品事实，但不得把架构、技术栈、数据库、API、部署或工程任务写进 PRD。
- 无法完成规定的联网调研或产品事实核查时，不得生成不完整文档；应先取得必要的访问条件，或请用户确认可复核的替代证据，再继续完成同一流程。
- 最终 PRD 不得包含 TODO、TBD、假设、开放问题、待确认项、阻塞项或模糊占位文案。

## References

- 调研已有项目、产品想法及外部实践时，完整读取 `workflows/§01-research.md`。
- 编写或合并目标文档时，完整读取 `workflows/§02-authoring.md`、`rules/prd-quality-standard.md` 和 `templates/prd.template.md`。
- 用户需要输入范式时读取 `templates/prd-intake.template.md`；需要输出范式时读取 `examples/prd.example.md`。
- 交付前完整读取 `workflows/§03-validation.md` 和 `checklists/semantic-acceptance.md`，并执行 `scripts/validate_prd.py`。

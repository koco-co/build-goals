---
name: build-prd
description: 将项目行为或产品想法整理为可复制的正式需求包，包含真实输入输出与行为样例；用户要求正式需求包，或已启动的 vibe-coding 流程缺少合格需求包时使用，不用于架构、实现或普通代码修改。
compatibility: 需要互联网访问、Python 3.9+，以及对来源项目和目标文档目录的本地读写权限。
metadata:
  author: koco-co
  version: "2.3.0"
---

# Outcome

生成一份可跨项目实施、只描述外部可观察行为的正式产品需求包。

## Routing

- 已有项目只提取用户可见能力和公开契约；产品想法从描述、调研和决策补全需求，不编造实现。
- 已有 `docs/产品需求/` 时先校验并保留仍有效的稳定编号；同主题的 `shape-idea` 结论直接复用。
- 由 `health-check` 受控调用时，审查阶段保持只读；上层取得修复确认后再修复。
- 技术架构、数据库、内部 API、部署、实施任务和商业计划不属于本 Skill。

## Steps

1. 读取 `workflows/§01-research.md`，区分用户输入、产品事实、公开契约、已确认目标和外部实践。
2. 建立功能域地图并只确认一次；确认前不进入逐域访谈或写入正式包。
3. 读取 `workflows/§02-domain-confirmation.md`，逐域一次问一个决策；涉及 UI 时展示全部可见状态和产品状态流。每域确认后才写入 `.build-goals/build-prd/` 检查点，检查点不能实施。
4. 读取 `workflows/§03-authoring.md` 和 `rules/prd-quality-standard.md`，完成跨域确认后再写入 `docs/产品需求/`。
5. 读取 `workflows/§04-validation.md`，运行 `scripts/validate_prd.py --strict` 和语义验收，确认没有修改来源项目。

## Rules

- 正式包只保留已确认的外部行为、输入、输出、样例和验收；不写内部架构、推理、私有路径或开放问题。
- 只写入 `.build-goals/build-prd/` 与 `docs/产品需求/`；其他代码、配置、数据和外部服务保持不变。

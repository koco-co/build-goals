# 正式需求包编写与更新

## Phase 1：写入条件

只有同时满足以下条件，才写 `docs/产品需求/`：

- 当前产品决策所需的调研已有可复核证据；
- 功能域地图已经确认；
- 本次纳入的每个功能域都已有确认检查点；
- 已执行跨域总结与新增跨域决策（见 `§02-domain-confirmation.md`）；
- 不存在假设、待定项、开放问题、冲突或模板占位。

完整包包含全部已确认功能域。正式阶段包只允许在本阶段范围闭合、验收可独立完成、未纳入功能域及其依赖契约明确、用户确认可以单独实施时生成。普通过程检查点不得伪装成阶段包。

## Phase 2：处理已有需求包

目标固定为当前项目的 `docs/产品需求/`。目录已存在时：

1. 运行严格校验并完整读取清单；
2. 保留仍有效的功能域 ID、`F-NNN`、验收 ID 和行为样例 ID；
3. 比较本次确认结论与现有对外行为；
4. 对输入、输出、公开契约或验收结果的变化逐项确认；
5. 删除已明确废弃或被替代的内容，不保留第二套历史正文；
6. 包版本按兼容性影响递增，并重新计算全部文件哈希。

旧路径 `docs/PRD需求文档.md` 已停用。发现旧文件时，先将有效内容迁移到新包并确认，再删除旧文件；不得长期双写或创建符号链接。

## Phase 3：写入顺序

依次使用以下模板：

1. `templates/prd.template.md` → `docs/产品需求/PRD需求文档.md`；
2. `templates/domain-requirements.template.md` → 每个 `功能域/<功能域>.md`；
3. `templates/domain-behavior.template.yaml` → 每个 `行为样例/<功能域>.yaml`；
4. `templates/behavior-index.template.yaml` → `行为样例/产品行为样例集.yaml`；
5. `templates/requirement-manifest.template.yaml` → 最后写 `需求包清单.yaml`。

先完成并复核所有内容文件，再计算 SHA-256 写入清单。`.yaml` 文件使用 YAML 1.2 兼容的 JSON 对象形式。

## Phase 4：清单与阶段包

清单字段遵循 `templates/requirement-manifest.template.yaml` 并由 `validate_prd.py` 强制；重点写清阶段包的纳入范围、延后范围和独立验收边界，以及包外依赖的已确认输入输出契约。

完成条件：正式目录是一份自包含、可复制、可校验的需求快照，没有指向来源项目的符号链接或运行时引用。

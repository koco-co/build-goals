# Skill 子任务委派

## 1. 盘点 Plugin 中的 Skills

对每个 Skill 标记：

```text
可直接复用
需要升级
需要新建
不应纳入 Plugin
```

可直接复用的 Skill 仍需通过当前规范校验。

## 2. 统一规范

Plugin 中的每个 Skill 必须满足 `build-skill` 的结构、命名、渐进式读取、静态校验和内容审查要求。

执行：

```bash
python3 scripts/validate_skill.py <skill-dir> --profile <profile> --strict
```

再使用：

- `checklists/skill-design-review.md`；
- `checklists/skill-semantic-acceptance.md`。

## 3. 委派方式

需要新建或升级 Skill 时：

- 平台支持受控委派：明确调用 `build-skill` 并传递已确认范围；
- 平台不支持嵌套调用：输出可直接交给 `build-skill` 的交接内容，由用户继续调用；
- 不在本工作流中复制 `build-skill` 的完整实现。

交接内容包含目标、非目标、输入、输出、平台、目录位置、复用能力、验收标准和 Plugin 接入点。

## 4. 返回 Plugin 流程

Skill 完成后重新检查：

- 名称与目录；
- Manifest 发现路径；
- 调用权限与触发文案；
- 平台适配文件；
- 引用和软链接；
- 与其他组件的接口；
- 实际验证状态。

完成条件：Plugin 内全部 Skills 均有明确来源和验收结果。

# §04 验证

## 机械校验

从 Skill 目录执行：

```bash
python3 scripts/validate_agents_md.py /path/to/project --strict
```

项目要求所有 `CLAUDE.md` 必须为符号链接时追加：

```bash
python3 scripts/validate_agents_md.py /path/to/project --strict --require-symlink
```

校验器检查根文件、嵌套文件、单一来源、相对链接、断开的本地 Markdown 链接、遗留占位符和软长度预算。软长度提示不因 `--strict` 变成失败。

## 项目验证

根据预览中的证据计划运行安全、低成本且与修改相关的命令。例如文档链接检查、Manifest 校验或仓库现有测试。不要为了验证指令自动安装依赖、连接生产、发布或执行迁移。

命令未运行时必须写成“来源已确认、运行未验证”，并注明来源和原因。静态读取脚本只能证明命令存在，不能证明命令在当前环境成功。

## 语义验收

逐项执行 `checklists/semantic-acceptance.md`。机械 PASS 不证明内容简洁、事实完整或嵌套边界合理；语义审查必须回看实际仓库证据和最终差异。

若可安全使用真实 Claude Code 与 Codex 客户端，可分别从根目录与一个嵌套目录启动新会话，确认指令被加载且作用域正确。未做真实客户端检查时明确标为未验证，不以文件存在代替加载成功。

## 差异检查

最后检查：

- 变更只包含确认过的 `AGENTS.md`、`CLAUDE.md` 及本次 Skill 开发自身文件；
- 符号链接在 Git 中仍表现为链接；
- 没有占位符、绝对本地路径、失效链接或复制的双正文；
- 用户原有不相关改动未被覆盖。

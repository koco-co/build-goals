# @koco-co/dsh-build-goals

`build-goals` 的 **DeepSeek Harness** 插件包：把仓库 `skills/` 下的 10 个
Skill 以 DSH 官方「内置技能 provider」模式（同 `dsh-skill-badge`）打包，
通过 `dsh plugin add` 一条命令安装。9 个配套 Skill 既可由模型按描述调用，
也可通过 `/name` 显式调用；`vibe-coding` 仅通过 `/vibe-coding` 启动。

## 安装

```bash
dsh plugin --profile web add 'github:koco-co/build-goals#path:packages/dsh-build-goals'
```

- 需要 pnpm 9+（git 子目录语法）；本机开发可用本地路径：
  `dsh plugin --profile web add /path/to/build-goals/packages/dsh-build-goals`。
- 安装后**重启**对应 profile 的 dsh 进程，新会话的 `/` 菜单即可看到
  `shape-idea`、`health-check`、`build-skill`、`build-plugin`、`build-prd`、`vibe-coding`、
  `build-readme`、`build-agents-md`、`handoff`、`obsidian-learn-topic`。
- 升级 = 重跑 add（git 渠道装的是仓库快照）。npm 发布为预留渠道。
- 用户可在 `~/.dsh/skills/<name>/` 放同名技能覆盖内置版本
  （filesystem provider rank 400 高于内置 rank 600）。

## 资产与生成

`assets/skills/` 与 `lib/skills.generated.js` 由
`scripts/sync_skills.py` 从仓库根 `skills/` 显式同步并**提交入库**
（剥离 `agents/`，安装时零构建）。只读检查：

```bash
python3 packages/dsh-build-goals/scripts/sync_skills.py --root .
```

确认修改后刷新：

```bash
python3 packages/dsh-build-goals/scripts/sync_skills.py --root . --write
```

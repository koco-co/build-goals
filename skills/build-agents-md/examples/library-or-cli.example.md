# Library / CLI 范例

以下内容展示一个 Python CLI 仓库的根 `AGENTS.md` 粒度。项目名、路径和命令均为示例，不得复制到未核实的目标仓库。

```markdown
# streamlint Agent Guide

## 项目概览

streamlint 是 Python 3.10+ 的流式文本检查 CLI。`src/streamlint/` 是实现源，`tests/` 是行为契约，`pyproject.toml` 定义命令入口和工具配置；`dist/` 是生成物，不直接编辑。

## 仓库结构

- `src/streamlint/cli.py`：参数解析、退出码和用户输出。
- `src/streamlint/rules/`：内置规则；公共协议在 `base.py`。
- `tests/fixtures/`：可复现输入，不放真实客户数据。

## 常用命令

- `python -m pytest`：完整测试。
- `python -m pytest tests/test_cli.py -q`：运行 CLI 相关回归测试。
- `python -m ruff check src tests`：静态检查。
- `python -m build`：构建 wheel 与 sdist。

## 关键约定

- 新规则必须通过 `Rule` 协议注册；不要在 `cli.py` 写规则特例。
- 退出码 `0` 表示无违规，`1` 表示发现违规，`2` 表示调用或运行错误；脚本依赖此契约。
- 用户可见诊断写到 stdout，运行错误写到 stderr。
- 版本只从 `src/streamlint/__init__.py` 读取，不能在构建配置中维护第二份。

## 验证流程

- 规则行为：增加通过、失败和边界 fixture，运行对应规则测试及完整测试。
- CLI 参数或输出：运行 `tests/test_cli.py`，并手动检查一次 `python -m streamlint --help`。
- 打包元数据：运行完整测试和 `python -m build`，检查生成包内容。
```

同目录 `CLAUDE.md` 应为只包含 `@AGENTS.md` 的普通文件。

<div align="center">

# 𝓑𝓾𝓲𝓵𝓭 𝓖𝓸𝓪𝓵𝓼

<p align="center">从目标澄清到可验证的软件项目、𝑺𝒌𝒊𝒍𝒍、𝑷𝒍𝒖𝒈𝒊𝒏、𝑷𝑹𝑫 与 𝑹𝑬𝑨𝑫𝑴𝑬 交付 · 𝑭𝒓𝒐𝒎 𝑰𝒅𝒆𝒂𝒔 𝒕𝒐 𝑽𝒆𝒓𝒊𝒇𝒊𝒂𝒃𝒍𝒆 𝑫𝒆𝒍𝒊𝒗𝒆𝒓𝒚</p>

[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-D97757?logo=anthropic&logoColor=white&cacheSeconds=3600)](https://code.claude.com/docs/en/plugins)
[![Codex](https://img.shields.io/badge/Codex-Supported-000000?style=flat-square&logo=openai&logoColor=white&cacheSeconds=3600)](https://developers.openai.com/plugins/)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-Compatible-2563EB?cacheSeconds=3600)](https://github.com/agentskills/agentskills)
[![Validate Plugin](https://github.com/koco-co/build-goals/actions/workflows/validate-skills.yml/badge.svg)](https://github.com/koco-co/build-goals/actions/workflows/validate-skills.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white&cacheSeconds=3600)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Not_declared-lightgrey?cacheSeconds=3600)](#license)

</div>

<a id="overview"></a>

<h2 align="center">𝑶𝒗𝒆𝒓𝒗𝒊𝒆𝒘 · 简介</h2>

<p><code>build-goals</code> 是一个持续演进与沉淀的 _Agent_ 目标构建仓库。它既是可以直接加载的 _Claude Code_ 与 _Codex_ 双平台 _Plugin_，也保留单个 _Skill_ 的独立安装方式。</p>

- 当前适配 _Claude Code_ 与 _Codex_。
- 其他 _Coding Agent_ 尚未声明兼容；新增平台前会先核对真实能力与契约。
- 所有 _Skill_ 仅限用户显式调用，普通提示词润色、一般编码和文档任务不会自动进入这些工作流。

<a id="capabilities"></a>

<h2 align="center">𝑪𝒂𝒑𝒂𝒃𝒊𝒍𝒊𝒕𝒊𝒆𝒔 · 已收录能力</h2>

| _Skill_                           | 作用                                                   | _Claude Code_          | _Codex_    |
| -------------------------------------- | ------------------------------------------------------------- | --------------------------- | --------------- |
| [`shape-idea`](skills/shape-idea/)     | 将初步想法塑造成完整、无歧义的定义                     | `/build-goals:shape-idea`   | `$shape-idea`   |
| [`build-skill`](skills/build-skill/)   | 从零构建或系统升级高质量 _Agent Skill_                   | `/build-goals:build-skill`  | `$build-skill`  |
| [`build-plugin`](skills/build-plugin/) | 构建、升级或迁移双平台 _Plugin_                          | `/build-goals:build-plugin` | `$build-plugin` |
| [`build-prd`](skills/build-prd/)       | 调研并生成决策完整的产品 _PRD_                           | `/build-goals:build-prd`    | `$build-prd`    |
| [`vibe-coding`](skills/vibe-coding/)   | 从 _PRD_ 或旧项目编排架构、_TDD_、多 _Agent_ 开发与全链路验收 | `/build-goals:vibe-coding`  | `$vibe-coding`  |
| [`build-readme`](skills/build-readme/) | 探索项目并创建或更新 _GitHub_ 风格 _README_                | `/build-goals:build-readme` | `$build-readme` |
| [`handoff`](skills/handoff/)           | 将当前会话整理为供下一位 _Agent_ 接续的文档              | `/build-goals:handoff`      | `$handoff`      |

<p><code>build-prd</code> 支持已有项目的全功能梳理，也能把尚不完整的想法完善为详细 _PRD_。它会调研当前竞品、活跃开源项目与适用的官方规范，逐项确认产品决策，并生成或规范化更新项目唯一的 <code>docs/PRD需求文档.md</code>。</p>

<p><code>vibe-coding</code> 是端到端软件交付总控：它可以实现 <code>build-prd</code> 的确认产物，也可以审查并迁移已有低质量项目。架构方案和任务列表分别经过用户确认后，才会搭建脚手架、组织 _TDD_ 功能切片、按依赖使用多 _Agent_ 与 _Git worktrees_、创建原子提交，并完成单元、集成、_E2E_、条件式视觉/交互、安全和正常测试数据验收。</p>

<p><code>build-readme</code> 会先探索代码、命令、测试、_CI_、文档和资源，提交具体写入预览；用户确认后才创建或更新 _README_，并分别报告机械检查、_GitHub_ 渲染和未验证项。</p>

<a id="workflow"></a>

<h2 align="center">𝑾𝒐𝒓𝒌𝒇𝒍𝒐𝒘 · 从想法到交付</h2>

```mermaid
flowchart LR
    A[Shape Idea] --> B{Build Goal}
    B --> C[Skill]
    B --> D[Plugin]
    B --> E[PRD]
    B --> F[README]
    E --> G[Vibe Coding]
    G --> H[Architecture Approval]
    H --> I[Task Approval]
    I --> J[TDD Agent Team]
    C --> K[Validate]
    D --> K
    F --> K
    J --> K
    K --> L[Handoff]
```

<a id="principles"></a>

<h2 align="center">𝑷𝒓𝒊𝒏𝒄𝒊𝒑𝒍𝒆𝒔 · 核心原则</h2>

- 先查明，再设计：先读取需求、仓库与平台约定，再提出方案。
- 确认后实施：用户确认目录、边界和验收标准前，不修改目标文件。
- 保护当前工作：最新 _HEAD_、未提交修改和新增文件都视为用户资产，不回滚、不覆盖。
- 单一规范源：共享能力使用仓库内相对软链接，不复制多份相同文件。
- 确定性优先：已有 _CLI_ → 脚本 → 模板 → _Few-shot_ → 规则 → 提示词。
- 渐进式读取：主 <code>SKILL.md</code> 只保留路由和主流程，复杂内容按需读取。
- 验证可复现：机械检查、语义验收与真实平台测试分别记录。
- 平台差异隔离：_Claude Code_ 与 _Codex_ 的 _Manifest_、调用策略和平台扩展分别配置。

<a id="structure"></a>

<h2 align="center">𝑺𝒕𝒓𝒖𝒄𝒕𝒖𝒓𝒆 · 仓库结构</h2>

```text
build-goals/
├── .agents/
│   └── plugins/
│       └── marketplace.json
├── .claude-plugin/
│   └── plugin.json
├── .codex-plugin/
│   └── plugin.json
├── .github/
│   └── workflows/
│       └── validate-skills.yml
├── scripts/
│   └── install_skill.py
├── skills/
│   ├── shape-idea/
│   ├── build-skill/
│   ├── build-plugin/
│   ├── build-prd/
│   ├── vibe-coding/
│   ├── build-readme/
│   └── handoff/
└── tests/
```

<p><code>build-plugin</code> 中复用的 _Skill_ 模板、质量规则、校验器、检查清单和 _Reviewer Agent_ 均通过相对软链接指向 <code>build-skill</code>。<code>vibe-coding</code> 同样通过相对软链接复用 <code>build-prd</code> 的 _PRD_ 校验器和 <code>build-skill</code> 的独立 _Reviewer_。所有链接必须解析在当前 _Plugin_ 根目录内；_CI_ 会拒绝绝对链接、失效链接和越界链接。</p>

<a id="quick-start"></a>

<h2 align="center">𝑸𝒖𝒊𝒄𝒌 𝑺𝒕𝒂𝒓𝒕 · 快速开始</h2>

<a id="claude-code"></a>

<h3 align="center">𝑪𝒍𝒂𝒖𝒅𝒆 𝑪𝒐𝒅𝒆 · 本地加载整个 𝑷𝒍𝒖𝒈𝒊𝒏</h3>

```bash
git clone https://github.com/koco-co/build-goals.git
cd build-goals
claude --plugin-dir .
```

<p>进入 _Claude Code_ 后显式调用：</p>

```text
/build-goals:shape-idea
/build-goals:build-skill
/build-goals:build-plugin
/build-goals:build-prd
/build-goals:vibe-coding
/build-goals:build-readme
/build-goals:handoff
```

<p>修改 _Plugin_ 后执行：</p>

```text
/reload-plugins
```

<p>可使用 _Claude Code_ 官方命令补充平台侧检查：</p>

```bash
claude plugin validate . --strict
```

<a id="codex"></a>

<h3 align="center">𝑪𝒐𝒅𝒆𝒙 · 添加仓库 𝑴𝒂𝒓𝒌𝒆𝒕𝒑𝒍𝒂𝒄𝒆</h3>

```bash
codex plugin marketplace add koco-co/build-goals --ref main
codex plugin marketplace list
```

<p>随后在支持 _Plugin_ 的 _Codex_ / _ChatGPT_ 界面中安装 <code>build-goals</code>，并显式调用：</p>

```text
$shape-idea
$build-skill
$build-plugin
$build-prd
$vibe-coding
$build-readme
$handoff
```

<p>仓库内的 <code>.agents/plugins/marketplace.json</code> 指向仓库根目录的 _Plugin_。</p>

<a id="standalone-skills"></a>

<h2 align="center">𝑺𝒕𝒂𝒏𝒅𝒂𝒍𝒐𝒏𝒆 𝑺𝒌𝒊𝒍𝒍𝒔 · 独立安装</h2>

<p>_Plugin_ 是推荐分发方式。确实只需要一个 _Skill_ 时，仍可使用兼容安装器。</p>

<p>_Codex_：</p>

```bash
python3 scripts/install_skill.py build-skill \
  --platform codex \
  --scope user
```

<p>_Claude Code_：</p>

```bash
python3 scripts/install_skill.py build-skill \
  --platform claude \
  --scope user
```

<p>将 <code>build-skill</code> 替换为 <code>build-plugin</code>、<code>build-prd</code>、<code>vibe-coding</code>、<code>build-readme</code>、<code>shape-idea</code> 或 <code>handoff</code> 即可安装另一个 _Skill_。目标目录已存在时默认拒绝覆盖；明确确认后添加 <code>--force</code>。</p>

<a id="validation"></a>

<h2 align="center">𝑽𝒂𝒍𝒊𝒅𝒂𝒕𝒊𝒐𝒏 · 验证</h2>

<p>验证整个双平台 _Plugin_：</p>

```bash
python3 skills/build-plugin/scripts/validate_plugin.py \
  . \
  --platform dual \
  --strict
```

<p>验证单个 _Skill_：</p>

```bash
python3 skills/build-skill/scripts/validate_skill.py \
  skills/vibe-coding \
  --profile dual \
  --plugin-root . \
  --strict
```

<p>验证 <code>build-prd</code> 生成的目标文档：</p>

```bash
python3 skills/build-prd/scripts/validate_prd.py \
  /path/to/project/docs/PRD需求文档.md \
  --strict
```

<p>验证 <code>vibe-coding</code> 的架构、任务追踪和最终交付：</p>

```bash
python3 skills/vibe-coding/scripts/validate_delivery.py \
  /path/to/project \
  --mode greenfield \
  --phase delivery \
  --require-clean \
  --strict
```

<p>验证 <code>build-readme</code> 创建或更新的 _GitHub README_：</p>

```bash
python3 skills/build-readme/scripts/validate_readme.py \
  /path/to/project/README.md \
  --project-root /path/to/project \
  --strict
```

<p>运行全部测试：</p>

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

<p>_GitHub Actions_ 会在 _Push_ 和 _Pull Request_ 中执行 _Plugin_ 严格校验与全部单元测试。</p>

<a id="naming"></a>

<h2 align="center">𝑵𝒂𝒎𝒊𝒏𝒈 · 文件命名约定</h2>

| 目录  | 命名格式         |
| ------------ | ----------------------- |
| `workflows/` | `§NN-name.md`           |
| `templates/` | `<name>.template.<ext>` |
| `examples/`  | `<name>.example.<ext>`  |
| `prompts/`   | `<name>.agent.md`       |

<a id="platform-support"></a>

<h2 align="center">𝑷𝒍𝒂𝒕𝒇𝒐𝒓𝒎 𝑺𝒖𝒑𝒑𝒐𝒓𝒕 · 平台支持</h2>

| 平台              | _Manifest_              | 静态校验  | 真实客户端验证                      |
| ------------------------ | ---------------------------- | ---------------- | ------------------------------------------ |
| _Claude Code_       | `.claude-plugin/plugin.json` | 已接入 _CI_ | 需在本地 _Claude Code_ 完成           |
| _Codex_             | `.codex-plugin/plugin.json`  | 已接入 _CI_ | 需在支持 _Plugin_ 的 _Codex_ 客户端完成 |
| 其他 _Coding Agent_ | 暂无                  | 暂无      | 暂无                                |

<a id="license"></a>

<h2 align="center">𝑳𝒊𝒄𝒆𝒏𝒔𝒆 · 许可证</h2>

<p>当前仓库尚未声明开源许可证。在许可证明确前，保留全部权利。</p>

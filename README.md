<div align="center">

# 𝓑𝓾𝓲𝓵𝓭 𝓖𝓸𝓪𝓵𝓼

<p align="center">从目标澄清到可验证的软件项目、𝑺𝒌𝒊𝒍𝒍、𝑷𝒍𝒖𝒈𝒊𝒏、𝑷𝑹𝑫 与 𝑹𝑬𝑨𝑫𝑴𝑬 交付 · 𝑭𝒓𝒐𝒎 𝑰𝒅𝒆𝒂𝒔 𝒕𝒐 𝑽𝒆𝒓𝒊𝒇𝒊𝒂𝒃𝒍𝒆 𝑫𝒆𝒍𝒊𝒗𝒆𝒓𝒚</p>

[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-D97757?logo=anthropic&logoColor=white&cacheSeconds=3600)](https://code.claude.com/docs/en/plugins)
[![Codex](https://img.shields.io/badge/Codex-Supported-000000?style=flat-square&logo=openai&logoColor=white&cacheSeconds=3600)](https://developers.openai.com/plugins/)
[![DeepSeek Harness](https://img.shields.io/badge/DeepSeek_Harness-Plugin-4D6BFE?cacheSeconds=3600)](https://github.com/deepseek-ai/deepseek-harness)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-Compatible-2563EB?cacheSeconds=3600)](https://github.com/agentskills/agentskills)
[![Validate Plugin](https://github.com/koco-co/build-goals/actions/workflows/validate-skills.yml/badge.svg)](https://github.com/koco-co/build-goals/actions/workflows/validate-skills.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white&cacheSeconds=3600)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Not_declared-lightgrey?cacheSeconds=3600)](#license)

</div>

<a id="overview"></a>

<h2 align="center">𝑶𝒗𝒆𝒓𝒗𝒊𝒆𝒘 · 简介</h2>

<p><code>build-goals</code> 是一个持续演进与沉淀的 <b>Agent</b> 目标构建仓库。它既是可以直接加载的 <b>Claude Code</b>、<b>Codex</b> 与 <b>DeepSeek Harness</b> 三平台 <b>Plugin</b>，也保留单个 <b>Skill</b> 的独立安装方式。</p>

- 当前适配 <b>Claude Code</b>、<b>Codex</b> 与 <b>DeepSeek Harness</b>。
- 其他 <b>Coding Agent</b> 尚未声明兼容；新增平台前会先核对真实能力与契约。

<a id="capabilities"></a>

<h2 align="center">𝑪𝒂𝒑𝒂𝒃𝒊𝒍𝒊𝒕𝒊𝒆𝒔 · 已收录能力</h2>

| <b>Skill</b>                                 | 作用                                                                     |
| -------------------------------------------- | ------------------------------------------------------------------------ |
| [`shape-idea`](skills/shape-idea/)           | 将初步想法塑造成完整、无歧义的定义                                       |
| [`build-skill`](skills/build-skill/)         | 按能力设计 <b>Frontmatter</b>，构建并审查高质量 <b>Agent Skill</b>       |
| [`build-plugin`](skills/build-plugin/)       | 构建、升级或迁移双平台 <b>Plugin</b>                                     |
| [`build-prd`](skills/build-prd/)             | 生成包含真实输入输出与行为样例的可复制产品需求包                         |
| [`vibe-coding`](skills/vibe-coding/)         | 按需求包与项目路线编排架构、<b>TDD</b>、多 <b>Agent</b> 开发与全链路验收 |
| [`build-readme`](skills/build-readme/)       | 探索项目并创建或更新 <b>GitHub</b> 风格 <b>README</b>                    |
| [`build-agents-md`](skills/build-agents-md/) | 初始化或整体重构跨平台 <b>AGENTS.md</b> 与 <b>CLAUDE.md</b>              |
| [`handoff`](skills/handoff/)                 | 整理跨会话交接文档并生成可直接复制的接续提示词                           |

<p><code>build-prd</code> 支持从已有项目提取完整对外行为，也能把尚不完整的想法完善为产品需求包。它先确认功能域地图，再逐域确认用户输入、追问、输出固定结构与语义、对外契约、异常边界和行为样例；大项目可在 <code>.build-goals/build-prd/</code> 保存已确认的逐域检查点，最终生成可独立复制和校验的 <code>docs/产品需求/</code>。</p>

<p><code>build-skill</code> 会根据调用方式、参数、权限、上下文与硬性环境要求形成 <b>Frontmatter</b> 字段决策矩阵；实现后分别完成内容审查、文案审查、内容回归和适用的独立 <b>Reviewer</b> 审查。</p>

<p><code>vibe-coding</code> 是端到端软件交付总控：它按用户原话选择“新项目只按需求实现”“新项目仅参考旧项目指定部分”“现有项目按需求续建”或“现有项目架构/技术栈迁移”。外部需求包会复制为目标项目本地快照，不与来源实时联动；架构方案和整体实施路线经过两次全局确认后，按功能域组织 <b>TDD</b>、多 <b>Agent</b> 与可选 <b>Git worktrees</b>，最终执行跨域端到端验收。</p>

<p><code>build-readme</code> 会先了解代码、命令、测试、<b>CI</b>、文档和资源并提供具体修改预览；用户确认后才创建或更新 <b>README</b>，并分别报告静态检查、<b>GitHub</b> 渲染和未验证内容。</p>

<p><code>build-agents-md</code> 会根据仓库证据筛选项目特有指令，并按应用、库、<b>CLI</b> 或 <b>Monorepo</b> 的实际结构组织根目录和子目录 <code>AGENTS.md</code>；用户确认完整内容预览后，才创建同目录 <code>CLAUDE.md</code> 相对符号链接，供两个平台共用正文。</p>

<a id="workflow"></a>

<h2 align="center">𝑾𝒐𝒓𝒌𝒇𝒍𝒐𝒘 · 从想法到交付</h2>

```mermaid
flowchart LR
    A[Shape Idea] --> B{Build Goal}
    B --> C[Skill]
    B --> D[Plugin]
    B --> E[Requirement Package]
    B --> F[README]
    B --> M[AGENTS.md]
    E --> G[Vibe Coding]
    G --> H[Architecture Approval]
    H --> I[Task Approval]
    I --> N[Scaffold]
    N --> O{Agent Instructions Ready?}
    O -->|Update required| P[Build AGENTS.md]
    P --> O
    O -->|Ready| J[TDD Agent Team]
    C --> K[Validate]
    D --> K
    F --> K
    M --> K
    J --> K
    K --> L[Handoff]
```

<a id="principles"></a>

<h2 align="center">𝑷𝒓𝒊𝒏𝒄𝒊𝒑𝒍𝒆𝒔 · 核心原则</h2>

- 先查明，再设计：先读取需求、仓库与平台约定，再提出方案。
- 确认后实施：用户确认目录、边界和验收标准前，不修改目标文件。
- 保护当前工作：最新 <b>HEAD</b>、未提交修改和新增文件都视为用户资产，不回滚、不覆盖。
- 单一规范源：跨 <b>Skill</b> 运行依赖由清单声明，并以可校验、可同步的普通镜像兼容两端客户端缓存。
- 确定性优先：已有 <b>CLI</b> → 脚本 → 模板 → <b>Few-shot</b> → 规则 → 提示词。
- 渐进式读取：主 <code>SKILL.md</code> 只保留路由和主流程，复杂内容按需读取。
- 验证可复现：静态检查、内容审查、文案审查与真实平台测试分别记录。
- 平台差异隔离：<b>Claude Code</b> 与 <b>Codex</b> 的 <b>Manifest</b>、调用策略和平台扩展分别配置。

<a id="structure"></a>

<h2 align="center">𝑺𝒕𝒓𝒖𝒄𝒕𝒖𝒓𝒆 · 仓库结构</h2>

```text
build-goals/
├── AGENTS.md
├── CLAUDE.md -> AGENTS.md
├── .plugin-shared-files.json
├── .agents/
│   └── plugins/
│       └── marketplace.json
├── .claude-plugin/
│   ├── marketplace.json
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
│   ├── build-agents-md/
│   └── handoff/
├── packages/
│   └── dsh-build-goals/
│       ├── package.json
│       ├── cordis.patch.yml
│       ├── lib/
│       │   ├── index.js
│       │   └── skills.generated.js
│       ├── assets/
│       │   └── skills/
│       └── scripts/
│           └── sync_skills.py
└── tests/
```

<p><code>build-plugin</code> 与 <code>vibe-coding</code> 复用的规则、模板、校验器和 <b>Reviewer Agent</b> 在 <code>.plugin-shared-files.json</code> 中声明规范源。仓库保存内容一致的普通镜像，避免 <b>Codex</b> 运行缓存省略嵌套软链接；<code>skills/build-plugin/scripts/sync_shared_files.py</code> 负责显式同步，严格校验会拒绝缺失、软链接或内容漂移。</p>

<a id="quick-start"></a>

<h2 align="center">𝑸𝒖𝒊𝒄𝒌 𝑺𝒕𝒂𝒓𝒕 · 快速开始</h2>

<a id="claude-code"></a>

<h3 align="center">𝑪𝒍𝒂𝒖𝒅𝒆 𝑪𝒐𝒅𝒆 · 添加仓库 𝑴𝒂𝒓𝒌𝒆𝒕𝒑𝒍𝒂𝒄𝒆</h3>

```bash
claude plugin marketplace add koco-co/build-goals@main
claude plugin marketplace list
claude plugin install build-goals@build-goals --scope user
```

<a id="codex"></a>

<h3 align="center">𝑪𝒐𝒅𝒆𝒙 · 添加仓库 𝑴𝒂𝒓𝒌𝒆𝒕𝒑𝒍𝒂𝒄𝒆</h3>

```bash
codex plugin marketplace add koco-co/build-goals --ref main
codex plugin marketplace list
codex plugin add build-goals@build-goals
```

<a id="deepseek-harness"></a>

<h3 align="center">𝑫𝒆𝒆𝒑𝑺𝒆𝒆𝒌 𝑯𝒂𝒓𝒏𝒆𝒔𝒔 · 添加 𝑫𝑺𝑯 𝑷𝒍𝒖𝒈𝒊𝒏</h3>

```bash
dsh plugin --profile web add 'github:koco-co/build-goals#path:packages/dsh-build-goals'
```

<p>需要 <b>pnpm</b> 9+；本地开发可用绝对路径替代 <b>git</b> 地址。安装后重启对应 <code>profile</code> 的 <code>dsh</code> 进程，新会话的 <code>/</code> 菜单即可调用 8 个 <b>Skill</b>。升级 = 重跑 <code>add</code>（<b>git</b> 渠道装的是仓库快照）；<b>npm</b> 注册表为预留发布渠道。</p>

<a id="standalone-skills"></a>

<h2 align="center">𝑺𝒕𝒂𝒏𝒅𝒂𝒍𝒐𝒏𝒆 𝑺𝒌𝒊𝒍𝒍𝒔 · 独立安装</h2>

<p><b>Plugin</b> 是推荐分发方式。确实只需要一个 <b>Skill</b> 时，仍可使用兼容安装器。</p>

<p><b>Codex</b>：</p>

```bash
python3 scripts/install_skill.py build-skill \
  --platform codex \
  --scope user
```

<p><b>Claude Code</b>：</p>

```bash
python3 scripts/install_skill.py build-skill \
  --platform claude \
  --scope user
```

<p><b>DeepSeek Harness</b>：</p>

```bash
python3 scripts/install_skill.py build-skill \
  --platform dsh \
  --scope user
```

<p>将 <code>build-skill</code> 替换为 <code>build-plugin</code>、<code>build-prd</code>、<code>vibe-coding</code>、<code>build-readme</code>、<code>build-agents-md</code>、<code>shape-idea</code> 或 <code>handoff</code> 即可安装另一个 <b>Skill</b>。目标目录已存在时默认拒绝覆盖；明确确认后添加 <code>--force</code>。</p>

<a id="validation"></a>

<h2 align="center">𝑽𝒂𝒍𝒊𝒅𝒂𝒕𝒊𝒐𝒏 · 验证</h2>

<p>验证整个双平台 <b>Plugin</b>：</p>

```bash
python3 skills/build-plugin/scripts/sync_shared_files.py --root .
python3 skills/build-plugin/scripts/validate_plugin.py \
  . \
  --platform dual \
  --strict
```

<p>检查 <b>DSH</b> 插件包资产与 <code>skills/</code> 一致（默认只读；确认修改后添加 <code>--write</code> 刷新）：</p>

```bash
python3 packages/dsh-build-goals/scripts/sync_skills.py --root .
```

<p>验证单个 <b>Skill</b>：</p>

```bash
python3 skills/build-skill/scripts/validate_skill.py \
  skills/vibe-coding \
  --profile dual \
  --plugin-root . \
  --strict
```

<p>验证 <code>build-prd</code> 生成的正式需求包：</p>

```bash
python3 skills/build-prd/scripts/validate_prd.py \
  /path/to/project \
  --strict
```

<p>验证 <code>build-prd</code> 的逐功能域过程检查点：</p>

```bash
python3 skills/build-prd/scripts/validate_checkpoint.py \
  /path/to/project \
  --strict
```

<p>比较并导入外部需求包快照（默认只读；确认后添加 <code>--write</code>）：</p>

```bash
python3 skills/vibe-coding/scripts/import_requirements.py \
  /path/to/source/docs/产品需求 \
  /path/to/target
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

<p>验证 <code>build-readme</code> 创建或更新的 <b>GitHub README</b>：</p>

```bash
python3 skills/build-readme/scripts/validate_readme.py \
  /path/to/project/README.md \
  --project-root /path/to/project \
  --strict
```

<p>验证 <code>build-agents-md</code> 创建或重构的跨平台项目指令：</p>

```bash
python3 skills/build-agents-md/scripts/validate_agents_md.py \
  /path/to/project \
  --strict
```

<p>运行全部测试：</p>

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

<p><b>GitHub Actions</b> 会在 <b>Push</b> 和 <b>Pull Request</b> 中执行 <b>Plugin</b> 严格校验与全部单元测试。</p>

<a id="naming"></a>

<h2 align="center">𝑵𝒂𝒎𝒊𝒏𝒈 · 文件命名约定</h2>

| 目录         | 命名格式                |
| ------------ | ----------------------- |
| `workflows/` | `§NN-name.md`           |
| `templates/` | `<name>.template.<ext>` |
| `examples/`  | `<name>.example.<ext>`  |
| `prompts/`   | `<name>.agent.md`       |

<a id="platform-support"></a>

<h2 align="center">𝑷𝒍𝒂𝒕𝒇𝒐𝒓𝒎 𝑺𝒖𝒑𝒑𝒐𝒓𝒕 · 平台支持</h2>

| 平台                     | <b>Manifest</b>                         | 静态校验         | 真实客户端验证                                    |
| ------------------------ | --------------------------------------- | ---------------- | ------------------------------------------------- |
| <b>Claude Code</b>       | `.claude-plugin/plugin.json`            | 已接入 <b>CI</b> | 需在本地 <b>Claude Code</b> 完成                  |
| <b>Codex</b>             | `.codex-plugin/plugin.json`             | 已接入 <b>CI</b> | 需在支持 <b>Plugin</b> 的 <b>Codex</b> 客户端完成 |
| <b>DeepSeek Harness</b>  | `packages/dsh-build-goals/package.json` | 已接入 <b>CI</b> | 已在本机 <b>DSH</b> web/headless 完成             |
| 其他 <b>Coding Agent</b> | 暂无                                    | 暂无             | 暂无                                              |

<a id="license"></a>

<h2 align="center">𝑳𝒊𝒄𝒆𝒏𝒔𝒆 · 许可证</h2>

<p>当前仓库尚未声明开源许可证。在许可证明确前，保留全部权利。</p>

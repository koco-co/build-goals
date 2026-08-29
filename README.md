<div align="center">

# 𝓑𝓾𝓲𝓵𝓭 𝓖𝓸𝓪𝓵𝓼

<p align="center">从目标澄清到可验证的能力与文档 · 𝑭𝒓𝒐𝒎 𝑰𝒅𝒆𝒂𝒔 𝒕𝒐 𝑺𝒌𝒊𝒍𝒍𝒔 𝒂𝒏𝒅 𝑫𝒐𝒄𝒔</p>

[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-D97757?logo=anthropic&logoColor=white&cacheSeconds=3600)](https://code.claude.com/docs/en/plugins)
[![Codex](https://img.shields.io/badge/Codex-Supported-000000?style=flat-square&logo=openai&logoColor=white&cacheSeconds=3600)](https://developers.openai.com/plugins/)
[![ZCode](https://img.shields.io/badge/ZCode-Plugin-7B5CFF?cacheSeconds=3600)](https://z.ai)
[![Pi](https://img.shields.io/badge/Pi-Package-7C3AED?cacheSeconds=3600)](https://pi.dev)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-Compatible-2563EB?cacheSeconds=3600)](https://github.com/agentskills/agentskills)
[![Validate Plugin](https://github.com/koco-co/build-goals/actions/workflows/validate-skills.yml/badge.svg)](https://github.com/koco-co/build-goals/actions/workflows/validate-skills.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white&cacheSeconds=3600)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Not_declared-lightgrey?cacheSeconds=3600)](#license)

</div>

<a id="overview"></a>

<h2 align="center">𝑶𝒗𝒆𝒓𝒗𝒊𝒆𝒘 · 简介</h2>

<p><code>build-goals</code> 用于澄清目标、构建 <b>Agent Skill</b> 与 <b>Plugin</b>、维护项目文档和检查项目规范，不负责组织软件项目的完整开发流程。你可以在 <b>Claude Code</b>、<b>Codex</b> 或 <b>ZCode</b> 中安装完整 <b>Plugin</b>，在 <b>Pi</b> 中安装完整 <b>Package</b>，也可以单独安装不依赖其他 <b>Skill</b> 的能力。</p>

- 当前直接适配 <b>Claude Code</b>、<b>Codex</b>、<b>ZCode</b> 与 <b>Pi</b>。
- 本仓库不再提供 <b>DeepSeek Harness</b> 专用包；<b>DSH</b> 使用其自身的 <b>Codex</b> 兼容能力，本仓库不单独验证该路径。
- 其他 <b>Coding Agent</b> 的兼容性尚未确认；新增支持前会先核对平台能力与使用规范。

<a id="capabilities"></a>

<h2 align="center">𝑪𝒂𝒑𝒂𝒃𝒊𝒍𝒊𝒕𝒊𝒆𝒔 · 已收录能力</h2>

| <b>Skill</b>                                 | 作用                                                                     |
| -------------------------------------------- | ------------------------------------------------------------------------ |
| [`shape-idea`](skills/shape-idea/)           | 综合调研后明确目标、方案与改动范围，涉及界面时展示交互和业务状态流        |
| [`health-check`](skills/health-check/)       | 检查项目规范文件，报告问题，并在确认后修复、验证和复检                    |
| [`build-skill`](skills/build-skill/)         | 根据实际需求设计 <b>Frontmatter</b>，构建并审查 <b>Agent Skill</b>      |
| [`build-plugin`](skills/build-plugin/)       | 构建、升级或迁移多平台 <b>Plugin</b>                                     |
| [`build-readme`](skills/build-readme/)       | 了解项目现状，创建或更新 <b>GitHub</b> 风格 <b>README</b>                |
| [`build-agents-md`](skills/build-agents-md/) | 初始化或整体重构跨平台 <b>AGENTS.md</b> 与 <b>CLAUDE.md</b>              |
| [`build-docs`](skills/build-docs/)           | 为大型项目建立、提取、更新开发文档，并复核外部审查报告                    |
| [`handoff`](skills/handoff/)                 | 整理跨会话交接文档，生成供下一位助手继续工作的提示词                      |

<p><code>health-check</code> 统一检查项目中的 <b>Agent Skill</b>、<b>Plugin</b>、<b>README</b>、<code>AGENTS.md</code> / <code>CLAUDE.md</code>。检查阶段不修改文件，一次性报告已查实的问题；用户确认后，调用相应能力完成修复、验证和复检，报告只展示在对话中。</p>

<p><code>build-skill</code> 会根据调用方式、参数、权限、上下文和必要环境条件，逐项说明 <b>Frontmatter</b> 字段的选择依据；实现后分别检查行为和措辞，复核润色是否改变原意，并在适用时交由独立 <b>Reviewer</b> 审查。</p>

<p><code>build-readme</code> 会先了解代码、命令、测试、<b>CI</b>、文档和资源并提供具体修改预览；用户确认后才创建或更新 <b>README</b>，并分别报告静态检查、<b>GitHub</b> 渲染和未验证内容。</p>

<p><code>build-agents-md</code> 会根据仓库事实筛选项目特有指令，并按应用、库、<b>CLI</b> 或 <b>Monorepo</b> 的实际结构安排根目录和子目录的 <code>AGENTS.md</code>。用户确认完整内容预览后，才写入指南及同目录的普通文件 <code>CLAUDE.md</code>；后者的内容精确为 <code>@AGENTS.md</code>，供 <b>Claude Code</b> 导入同一正文。</p>

<p><code>build-docs</code> 覆盖需求、架构、路线图、数据、编码、测试、决策、术语、工作交接、变更、环境和风险共 12 类文档。它先确认整体规划，再分批预览、确认并写入；对于已有项目，从代码、配置、测试和记录中提取事实，沿用职责相同的已有文档路径，并在 <code>AGENTS.md</code> 中维护一行入口说明，其中用 <code>@</code> 加相对路径引用文档。它不处理小问题、小需求，也不开发产品代码。</p>

<p>收到针对已有文档的外部审查报告时，进入独立的「审查报告复核」分支：逐项说明采纳、部分采纳或不采纳的依据与理由，展示文档修改 <b>Diff</b>；一次确认同时授权所展示的修改与 <code>commit</code>，验证通过后仅提交本次改动，不 <code>push</code>。该分支不重复整体规划或逐批确认，也不新建文档；原有三个分支仍不提交。</p>

<p><code>build-docs</code> 新建的文档统一放在 <code>docs/spec/</code>，按 <code>product/</code>、<code>architecture/</code>、<code>engineering/</code> 和 <code>status/</code> 分组；下一位助手从 <code>docs/spec/AGENT_BRIEF.md</code> 了解当前状态并继续工作。完整路径见 <a href="skills/build-docs/rules/documents.md">文档职责表</a>。已有文档沿用原路径，目录迁移另行确认。</p>

<p><code>build-docs</code> 在 <b>Claude Code</b>、<b>Codex</b> 和 <b>Pi</b> 中仅限用户主动调用；<b>ZCode</b> 允许模型按上述适用范围调用。<a href="https://zcode.z.ai/en/docs/skill">ZCode 的 Skill 列表同时面向用户和模型</a>，不提供等价的仅用户调用开关。配置与安装校验不代表真实客户端行为已验证。</p>

<a id="workflow"></a>

<h2 align="center">𝑾𝒐𝒓𝒌𝒇𝒍𝒐𝒘 · 从想法到交付</h2>

```mermaid
flowchart LR
    A[Shape Idea] --> B{Build Goal}
    B --> C[Skill]
    B --> D[Plugin]
    B --> F[README]
    B --> M[AGENTS.md]
    B --> N[开发文档]
    C --> K[Validate]
    D --> K
    F --> K
    M --> K
    N --> K
    K --> L[Handoff]
```

<a id="principles"></a>

<h2 align="center">𝑷𝒓𝒊𝒏𝒄𝒊𝒑𝒍𝒆𝒔 · 核心原则</h2>

- 先了解事实，再设计：阅读需求和项目内容，核对平台规范，再提出方案。
- 确认后实施：用户确认目录、边界和验收标准前，不修改目标文件。
- 保留已有工作：保留最新 <b>HEAD</b>、未提交修改和新增文件，不擅自回滚或覆盖。
- 单一规范源：跨 <b>Skill</b> 依赖由清单声明，以可校验、可同步的普通文件副本适配客户端缓存。
- 优先使用可靠工具：已有 <b>CLI</b> → 脚本 → 模板 → 示例 → 规则 → 提示词。
- 按需读取：主 <code>SKILL.md</code> 只保留适用范围和主流程，详细规则需要时再读取。
- 验证可复现：静态检查、内容审查、文案审查与真实平台测试分别记录。
- 平台差异隔离：<b>Claude Code</b>、<b>Codex</b> 与 <b>ZCode</b> 的 <b>Manifest</b>、<b>Pi Package</b>、调用策略和平台扩展分别配置。

<a id="structure"></a>

<h2 align="center">𝑺𝒕𝒓𝒖𝒄𝒕𝒖𝒓𝒆 · 仓库结构</h2>

```text
build-goals/
├── AGENTS.md
├── CLAUDE.md
├── package.json
├── .plugin-shared-files.json
├── .agents/
│   └── plugins/
│       └── marketplace.json
├── .claude-plugin/
│   ├── marketplace.json
│   └── plugin.json
├── .codex-plugin/
│   └── plugin.json
├── .zcode-plugin/
│   └── plugin.json
├── .github/
│   └── workflows/
│       └── validate-skills.yml
├── scripts/
│   └── install_skill.py
├── skills/
│   ├── shape-idea/
│   ├── health-check/
│   ├── build-skill/
│   ├── build-plugin/
│   ├── build-readme/
│   ├── build-agents-md/
│   ├── build-docs/
│   └── handoff/
└── tests/
```

<p><code>build-plugin</code> 从 <code>build-skill</code> 复用的规则、模板、校验器和 <b>Reviewer Agent</b>，均在 <code>.plugin-shared-files.json</code> 中记录规范源。仓库保存内容一致的普通文件副本，避免 <b>Codex</b> 缓存遗漏嵌套软链接。修改规范源后，使用 <code>skills/build-plugin/scripts/sync_shared_files.py</code> 同步；副本缺失、使用软链接或内容与规范源不一致时，严格校验不会通过。</p>

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

<a id="zcode"></a>

<h3 align="center">𝒁𝑪𝒐𝒅𝒆 · 添加仓库 𝑴𝒂𝒓𝒌𝒆𝒕𝒑𝒍𝒂𝒄𝒆</h3>

<p>在 <b>ZCode</b> 客户端中打开 <b>Settings → Plugin Management → Discover</b>，通过 <code>+</code> 按钮添加 <b>GitHub</b> 仓库 <code>koco-co/build-goals</code> 并安装 <b>Plugin</b>，或选择本地仓库目录。<b>ZCode</b> 沿用 <code>.claude-plugin/marketplace.json</code> 解析 <b>Marketplace</b>，并优先读取 <code>.zcode-plugin/plugin.json</code> 作为 <b>Plugin Manifest</b>。</p>

<a id="pi"></a>

<h3 align="center">𝑷𝒊 · 安装 𝑷𝒂𝒄𝒌𝒂𝒈𝒆</h3>

```bash
pi install git:github.com/koco-co/build-goals
pi list
```

<p>安装完整包后，可在 <b>Claude Code</b> 中调用 <code>/build-goals:health-check</code>，在 <b>Codex</b> 中调用 <code>$build-goals:health-check</code>，在 <b>ZCode</b> 输入框的 <code>/</code> 菜单 <b>Skills</b> 分组中选择对应能力，在 <b>Pi</b> 中调用 <code>/skill:health-check</code>。请求符合项目规范检查的适用范围时，模型也可以直接调用。</p>

<a id="standalone-skills"></a>

<h2 align="center">𝑺𝒕𝒂𝒏𝒅𝒂𝒍𝒐𝒏𝒆 𝑺𝒌𝒊𝒍𝒍𝒔 · 独立安装</h2>

<p>建议安装完整分发包。如果只需要一个不依赖其他 <b>Skill</b> 的能力，也可以使用独立安装脚本；<code>health-check</code> 需要其他 <b>Skill</b> 配合，只随完整分发包提供，不能独立安装。</p>

<p><b>Pi</b>：</p>

```bash
python3 scripts/install_skill.py build-skill \
  --platform pi \
  --scope user
```

<p><b>ZCode</b>：</p>

```bash
python3 scripts/install_skill.py build-skill \
  --platform zcode \
  --scope user
```

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

<p>将 <code>build-skill</code> 替换为 <code>build-plugin</code>、<code>build-readme</code>、<code>build-agents-md</code>、<code>build-docs</code>、<code>shape-idea</code> 或 <code>handoff</code> 即可安装另一个独立 <b>Skill</b>。目标目录已存在时默认拒绝覆盖；明确确认后添加 <code>--force</code>。</p>

<a id="validation"></a>

<h2 align="center">𝑽𝒂𝒍𝒊𝒅𝒂𝒕𝒊𝒐𝒏 · 验证</h2>

<p>验证整个多平台分发包（三份 <b>Plugin Manifest</b>、<b>Pi Package</b> 及版本一致性）：</p>

```bash
python3 skills/build-plugin/scripts/sync_shared_files.py --root .
python3 skills/build-plugin/scripts/validate_plugin.py \
  . \
  --platform all \
  --strict
```

<p>验证单个 <b>Skill</b>：</p>

```bash
python3 skills/build-skill/scripts/validate_skill.py \
  skills/health-check \
  --profile dual \
  --plugin-root . \
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
| <b>ZCode</b>             | `.zcode-plugin/plugin.json`（优先探测） | 已接入 <b>CI</b> | 需在本地 <b>ZCode</b> 客户端完成                  |
| <b>Pi</b>                | `package.json`                          | 已接入 <b>CI</b> | 已在 <b>Pi 0.84.4</b> 完成本地路径安装与 Skill 发现 |
| 其他 <b>Coding Agent</b> | 暂无                                    | 暂无             | 暂无                                              |

<a id="license"></a>

<h2 align="center">𝑳𝒊𝒄𝒆𝒏𝒔𝒆 · 许可证</h2>

<p>当前仓库尚未声明开源许可证。在许可证明确前，保留全部权利。</p>

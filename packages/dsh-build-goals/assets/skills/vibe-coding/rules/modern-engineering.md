# 现代化工程规范

## 1. 选择原则

现代化意味着：

- 当前仍受官方支持；
- 社区与生态维护活跃；
- 配置集中、命令可重复；
- 默认严格、错误尽早暴露；
- 能够自动格式化、Lint、类型检查和测试；
- 新成员容易理解和运行；
- 对项目规模不过度设计。

“版本号最新”不是充分理由。每项选型必须比较稳定性、官方支持、迁移成本、团队能力、运行环境和实际收益。

## 2. 通用基线

优先建立：

- 单一依赖与配置源；
- 锁文件；
- 可重复安装命令；
- 格式化、Lint、类型检查、测试、构建命令；
- pre-commit 或等价本地门禁；
- CI 同步执行相同命令；
- `.env.example` 或结构化配置说明；
- 结构化日志和清晰错误；
- 依赖与秘密检查；
- 开发、测试和生产配置隔离。

职责重叠的工具只保留一个权威实现。

## 3. 生态候选

以下是调研起点，不是强制组合。

### Python

通常优先评估：

```text
uv
pyproject.toml
Ruff
Pyright
pytest
pre-commit
Rich / Typer（仅 CLI 需要）
```

要求：

- `src/` 布局按包类型评估；
- 全面类型注解；
- `pathlib`、上下文管理器和标准异常链；
- 配置使用 typed settings；
- 不保留 `requirements.txt`、Poetry、pip-tools 与 uv 的重复权威源。

### TypeScript / JavaScript

通常优先评估：

```text
Corepack + pnpm
TypeScript strict
Biome 或 ESLint + Prettier
Vitest
Playwright
```

根据产品选择 Vite、Next.js、Nuxt、SvelteKit 或其他框架，不默认把网站等同于 Next.js。

### Go

通常优先评估：

```text
Go modules
gofmt / gofmt-compatible formatter
golangci-lint
go test
govulncheck
```

### Rust

通常优先评估：

```text
Cargo
rustfmt
Clippy
cargo-nextest
cargo-audit
```

### JVM

优先使用受支持的 JDK LTS、Gradle/Maven Wrapper、JUnit 5，以及项目一致的格式和静态检查工具。

## 4. 命名与结构

- 文件、模块、包、函数、类、组件和变量遵循语言生态主流规范；
- 名称表达业务职责，不使用 `utils2`、`common_new`、`temp`、`final_final`；
- 一个模块有清晰单一职责；
- 依赖从外层指向稳定核心，避免循环引用；
- 公共接口最小化；
- 文件大小和函数复杂度由实际可读性决定，不以机械数字替代设计；
- 生成代码与手写代码分离。

## 5. 注释与文档

- 注释解释“为什么”和约束，不复述代码；
- 优先使用用户交流语言；
- API、协议、类型名、命令和技术名词保留英文；
- 公共接口使用生态标准 docstring/doc comment；
- 不用注释掩盖无法理解的结构；
- 删除失效注释、调试记录和需求原文。

## 6. 前端与设计

有 UI 时：

- 先定义设计 token、布局、状态和组件契约；
- 相同语义只保留一个组件和一种字段命名；
- 支持键盘、焦点、对比度和语义化结构；
- 不把 PRD 段落、用户口述或开发备注直接呈现在界面；
- 空、加载、错误、权限和成功状态完整；
- 视觉效果服务于产品层级，不堆叠无目的动画和装饰。

## 7. 决策记录

架构文档对每个关键工具记录：

- 选择；
- 版本策略；
- 采用原因；
- 被否决方案；
- 迁移与锁定风险；
- 验证命令。

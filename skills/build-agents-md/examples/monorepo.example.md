# Monorepo 范例

这个范例说明何时需要根文件和子目录文件。根文件记录共享事实；`services/api` 使用独立语言、命令和数据库约定，因此补充自己的指令；`packages/ui` 没有不同约定，因此不创建额外文件。

```text
orbit/
├── AGENTS.md
├── CLAUDE.md -> AGENTS.md
├── package.json
├── packages/
│   └── ui/
└── services/
    └── api/
        ├── AGENTS.md
        ├── CLAUDE.md -> AGENTS.md
        └── go.mod
```

根 `AGENTS.md`：

```markdown
# Orbit Agent Guide

## 项目概览

Orbit 是 pnpm 与 Turborepo 管理的产品 Monorepo。TypeScript 工作区共享根锁文件和任务图；`services/api` 是独立 Go module，其差异由该目录的嵌套指令补充。

## 仓库结构

- `apps/console/`：React 管理端。
- `packages/ui/`：共享组件，API 由包根导出。
- `packages/config/`：共享 TypeScript、ESLint 和构建配置。
- `services/api/`：Go API；进入该目录时同时遵循其 `AGENTS.md`。

## 常用命令

- `pnpm install --frozen-lockfile`：安装 JS 工作区依赖。
- `pnpm turbo test lint typecheck`：执行受任务图影响的质量检查。
- `pnpm turbo test --filter=...[HEAD^]`：聚焦当前变更影响范围。

## 关键约定

- JavaScript 依赖只使用根 `pnpm-lock.yaml`，子包不得新增锁文件。
- 跨包导入使用公开 package export，禁止依赖其他包的 `src/` 内部路径。
- 共享任务必须声明 Turborepo 输入和输出，避免缓存复用过期生成物。

## 验证流程

- 包内行为：运行目标包测试，再运行受影响任务图。
- 公共 export 或共享配置：运行所有下游包的类型检查与测试。
- `services/api` 变更：按该目录的增量指令验证。
```

`services/api/AGENTS.md`：

```markdown
# API 增量指令

本文件只覆盖 `services/api/`。继续遵循仓库根指令；以下规则优先适用于 Go API。

## 仓库结构

- `cmd/server/`：进程装配，不放业务规则。
- `internal/http/`：传输与鉴权边界。
- `internal/domain/`：业务模型和用例。
- `migrations/`：按编号追加的 PostgreSQL 迁移。

## 常用命令

- `go test ./...`：API 单元与集成测试。
- `golangci-lint run`：Go 静态检查。

## 关键约定

- `internal/domain` 不依赖 HTTP 或数据库适配器。
- 已合并迁移只读；结构调整必须新增迁移并覆盖升级与回滚。
- HTTP 错误通过统一 mapper 转换，handler 不自行拼接响应结构。

## 验证流程

- 领域逻辑：运行目标 package 与 `go test ./...`。
- SQL 或迁移：运行数据库集成测试，并验证从上一版本升级和回滚。
```

两个作用域各自拥有 `CLAUDE.md -> AGENTS.md`。嵌套文件不重复根命令或通用 JS 规则。

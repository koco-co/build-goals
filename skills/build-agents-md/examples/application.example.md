# Application 范例

以下内容展示一个前后端应用如何在根 `AGENTS.md` 中说明架构职责和验证流程，而不复制完整开发手册。项目名、路径和命令均为示例，不得复制到未核实的目标仓库。

```markdown
# Atlas Desk Agent Guide

## 项目概览

Atlas Desk 是 TypeScript 客服工单应用：`apps/web` 为 Next.js 前端，`apps/api` 为 Fastify API，`packages/contracts` 是两端共享的运行时 schema。PostgreSQL 迁移位于 `apps/api/migrations`，生成的 API 类型不得手改。

## 仓库结构

- `apps/web/app/`：路由与服务端组件；浏览器交互组件就近放置。
- `apps/web/lib/api/`：唯一的前端 API 访问层。
- `apps/api/src/routes/`：HTTP 边界，只负责鉴权、校验和服务编排。
- `apps/api/src/services/`：业务规则与事务边界。
- `packages/contracts/`：请求、响应和事件 schema 的单一来源。

## 常用命令

- `pnpm dev`：启动本地 web 与 API。
- `pnpm test`：运行工作区单元测试。
- `pnpm lint && pnpm typecheck`：静态质量检查。
- `pnpm --filter api test:integration`：使用隔离数据库运行 API 集成测试。
- `pnpm --filter web test:e2e`：运行浏览器关键路径。

## 关键约定

- API 契约先改 `packages/contracts`，再更新服务端和客户端；禁止在两端重复声明响应类型。
- 路由层不直接访问数据库，事务由 service 层拥有。
- 数据库结构变化必须新增迁移；已合并迁移不可改写。
- 前端只能通过 `apps/web/lib/api` 调用后端，确保鉴权刷新与错误映射一致。
- UI 中“禁用”表示控件可见但不可交互，不得改为隐藏。

## 验证流程

- 共享契约：运行 contracts、API 与 web 类型检查，并覆盖兼容性负例。
- API 或数据库：运行相关单元测试、API 集成测试和迁移回滚检查。
- UI 行为：运行相关组件测试，并在真实浏览器验证桌面与窄屏的加载、空、错误和禁用状态。
- 跨端流程：运行对应 E2E；未执行时不得声称用户流程通过。

## 本地数据边界

- 测试只使用可清理的合成账号和工单，不复制生产数据。
- `.env.local` 只保存本机配置，任何凭据都不得进入 fixture、日志或提交。
```

根目录 `CLAUDE.md` 应为 `AGENTS.md` 的相对符号链接。若各应用没有额外差异，不应仅因目录存在而创建嵌套文件。

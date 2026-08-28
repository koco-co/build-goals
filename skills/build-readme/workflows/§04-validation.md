# README 验证

验证分为机械检查、项目检查、渲染检查和语义验收，不能互相替代。

## Phase 1：机械检查

使用当前 Skill 目录中的校验器，执行 `python3 <skill-dir>/scripts/validate_readme.py <project-root>/README.md --project-root <project-root> --strict`；仅用户已授权联网时加 `--verify-remote`，远程失败显示具体 URL。

## Phase 2：项目检查

运行项目已经存在且与文档相关的格式化、Markdown Lint、链接检查或测试。不要为了 README 验收临时安装新的依赖。

检查 `git diff --check`，再审阅完整 README Diff，确认没有覆盖并行工作或改动项目代码。

## Phase 3：GitHub 与视觉检查

- 项目已有 Mermaid CLI 时实际解析图表；没有时不临时安装，改用可用的 GitHub 渲染路径或标记 Mermaid 真实渲染未验证。
- 只有预览已批准外部传输并且当前环境具备可用的渲染 API 认证凭据时，才可调用渲染 API 检查 GFM HTML。
- 所有新增或修改图片必须实际查看；检查浅色、深色背景、裁切、可读性和替代文本。
- 验证 Shields、远程图片和外部链接时记录访问时间与结果。

API 返回 HTML 只证明 Markdown 转换成功；没有在 GitHub 仓库页面查看时，不得声称 GitHub 页面视觉验收已完成。

## Phase 4：语义验收

使用 `checklists/semantic-acceptance.md`，逐项核对：

- 项目定位和功能是否准确；
- 安装与快速开始能否形成最短成功路径；
- 图表是否比文字更清楚；
- 视觉样式是否保持内容清晰易读；
- 限制、许可证和未验证项是否诚实。

发现失败时修复并重跑受影响检查。完成条件是所有检查都有结果，未运行项有明确原因。

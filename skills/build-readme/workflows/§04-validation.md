# README 验证

验证分为机械检查、项目检查、渲染检查和语义验收，不能互相替代。

## Phase 1：机械检查

使用当前 Skill 目录中的校验器：

```bash
python3 <skill-dir>/scripts/validate_readme.py \
  <project-root>/README.md \
  --project-root <project-root> \
  --strict
```

它检查：

- 居中首屏、精确花体标题、HTML 斜体描述和 Shields 数量；
- 居中章节标题、稳定锚点、正文斜体、粗体冲突和未解决占位符；
- HTML 标签配对、代码块语言标签和格式转换残留；
- 本地链接、远程热链、图片替代文本和 SVG XML/安全内容；
- Mermaid 代码块的基础声明。

只有用户已允许联网验证时增加 `--verify-remote`。远程检查失败必须显示具体 URL，不得静默忽略。

## Phase 2：项目检查

运行项目已经存在且与文档相关的格式化、Markdown Lint、链接检查或测试。不要为了 README 验收临时安装新的依赖。

检查 `git diff --check`，再审阅完整 README Diff，确认没有覆盖并行工作或改动项目代码。

## Phase 3：GitHub 与视觉检查

- 项目已有 Mermaid CLI 时实际解析图表；没有时不临时安装，改用可用的 GitHub 渲染路径或标记 Mermaid 真实渲染未验证。
- 只有预览已批准外部传输并且 `gh` 已认证时，才可调用 GitHub Markdown API 检查 GFM HTML。
- 所有新增或修改图片必须实际查看；检查浅色、深色背景、裁切、可读性和替代文本。
- 验证 Shields、远程图片和外部链接时记录访问时间与结果。

API 返回 HTML只证明 Markdown 转换成功；没有在 GitHub 仓库页面查看时，不得声称 GitHub 页面视觉验收已完成。

## Phase 4：语义验收

使用 `checklists/semantic-acceptance.md`，逐项核对：

- 项目定位和功能是否准确；
- 安装与快速开始能否形成最短成功路径；
- 图表是否比文字更清楚；
- 视觉样式是否没有损害可读性；
- 限制、许可证和未验证项是否诚实。

发现失败时修复并重跑受影响检查。完成条件是所有检查都有结果，未运行项有明确原因。

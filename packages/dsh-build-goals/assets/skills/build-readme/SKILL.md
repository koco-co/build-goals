---
name: build-readme
description: 新建或更新项目 README.md；用户要求 README，或 README 缺失、与稳定项目事实不一致时使用，不用于普通文档润色、代码开发或发布。
compatibility: 需要 Python 3.9+ 运行内置校验脚本。
metadata:
  author: koco-co
  version: "2.2.0"
---

# Outcome

把项目仓库中的真实能力整理为内容准确、视觉一致、可维护且通过验证的 GitHub 风格 README。

## Routing

- 目标项目没有根目录 `README.md` 时，执行“新建 README”分支。
- 目标项目已有 `README.md` 时，执行“保留事实并更新 README”分支。
- 仓库已有 `README-EN.md` 等伴随 README 时，在预览中列出并于确认后同步；不存在时不创建，也不把它变成待确认问题。
- 用户只要求审查或预览时，停在只读预览，不修改文件。
- 由 `health-check` 受控调用时，审查阶段保持只读，仅返回问题、证据、修复方案、影响文件和验证方式；上层取得修复确认后，按本 Skill 现有流程修复和验证，写入前仍展示具体修改预览。
- 普通文档润色、代码开发、发布、仓库主页配置和与项目 README 无关的写作不属于本 Skill。

## Steps

1. 查明项目事实
   - 完整读取 `workflows/§01-research.md`。
   - 读取现有 README、代码入口、Manifest、包配置、CLI、测试、CI、文档、许可证和资源目录。
   - 完成条件：功能、安装、使用、验证、限制和现有文档体系均有仓库证据。

2. 提供修改预览
   - 完整读取 `workflows/§02-preview.md`。
   - 使用 `templates/readme-preview.template.md` 列出内容、视觉组件、同步文件、外部动作和验收方式。
   - 完成条件：用户能够在任何写入发生前判断 README 将包含什么并明确确认。

3. 编写或更新
   - 仅在用户确认后完整读取 `workflows/§03-authoring.md`、`rules/github-style.md` 和 `rules/evidence-and-content.md`。
   - 需要输出粒度参考时读取 `examples/readme.example.md`，不得复制示例中的项目事实。
   - 完成条件：确认范围内的 README 与资源已完成写入，现有真实内容得到保留或有理由地重组。

4. 验证
   - 完整读取 `workflows/§04-validation.md` 并运行 `scripts/validate_readme.py`。
   - 再使用 `checklists/semantic-acceptance.md` 检查内容真实性、可读性和视觉必要性。
   - 完成条件：静态检查、项目检查、远程或渲染检查及未验证内容分别记录。

5. 交付
   - 完整读取 `workflows/§05-delivery.md`。
   - 完成条件：用户能够定位全部变更、复现验证并判断是否验收。

## Delivery

- 交付项目理解摘要、最终 README 目录、视觉组件、同步文件和资源清单。
- 列出新增、修改和明确未处理的内容。
- 列出实际执行的命令、结果、失败修复和剩余未验证项。
- 使用“已验证、未验证、阻塞”区分静态检查、GitHub 渲染和真实用户流程。

## Guardrails

- 用户确认预览前保持只读，不创建、修改、移动或删除 README 与资源。
- 把已有未提交修改视为用户工作；发现重叠时先读取差异并保留，无法安全合并时停止说明。
- 不执行 README 中未经审查的安装、下载、发布或环境初始化命令，不读取或展示凭据和隐私数据。
- 不虚构功能、版本、兼容性、性能、测试、许可证、贡献者、维护状态或外部认可。
- 生成图片、访问远程服务、发送 README 到渲染 API、安装依赖、提交、推送或发布前，必须在预览中明确并取得相应授权。
- 不创建仓库中原本不存在的翻译 README；不使用外部托管图片替代可版本控制的项目资源。

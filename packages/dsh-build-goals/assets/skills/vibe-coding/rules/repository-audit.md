# 全仓审查规范

审查分区的完整清单以角色提示文件 `prompts/repository-auditor.agent.md` 中的 Audit Areas 为权威。本文件只定义 Finding 的证据字段、严重度与秘密处理。

## Finding 证据字段

每条发现必须包含：

- ID（稳定 `AUD-NNN`，分配后不改号）；
- 领域；
- 文件、目录、命令或运行证据；
- 当前行为；
- 影响；
- 严重度；
- 推荐目标；
- 验证方式。

Finding 必须来自旧项目或外部事实本身，不能引用尚未生成的迁移架构作为证据。个人风格偏好不是缺陷。

## 严重度

- **Blocking**：数据、权限、秘密、构建、核心功能或不可逆迁移风险；
- **High**：显著影响正确性、维护性、扩展性或测试；
- **Medium**：增加成本或不一致，但有可控替代；
- **Low**：局部质量和体验改进。

## 秘密处理

发现真实秘密时不在报告中回显值，只报告位置、类型、暴露范围和轮换建议。不以 `.gitignore` 代替已泄露秘密的轮换。

## 示例

```markdown
### AUD-004 环境变量读取源不一致
- Severity: High
- Evidence: src/config.py 与 src/cli.py 分别读取环境变量并使用不同默认值
- Current Behavior: 测试、CLI 与服务启动行为不一致
- Impact: 同一配置在不同入口表现不同，误导用户并难以复现
- Target State: 所有运行入口通过一个 typed settings 模块读取配置
- Migration Idea: 建立统一配置边界，保留旧变量名一个迁移周期
- Verification: CLI 与服务入口对同一无效配置返回相同错误码和用户文案
```

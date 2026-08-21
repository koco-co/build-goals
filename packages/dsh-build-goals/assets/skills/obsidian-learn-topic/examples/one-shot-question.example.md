# One-shot 提问示例

实际发给用户的题目统一保留：进度状态、场景、问题、提示。验证目标和通过标准留在内部评定中。

## 合格示例

本单元知识点已验收 `0/1`，当前题目状态为“待回答”。

### 场景

`admin_login` 依赖 `page`；`page` 默认是 `function` scope。现在 `admin_login` 被声明成 `session` scope：

```python
@pytest.fixture(scope="session")
def admin_login(page: Page) -> Page:
    page.goto("/login")
    return page
```

### 问题

执行使用 `admin_login` 的测试时，会发生什么？

### 提示

请说明：错误类型，以及造成错误的 scope 关系。

## 内部评定

- 验证目标：识别 pytest fixture 的 scope mismatch。
- 通过标准：指出 `session` fixture 依赖 `function` fixture，并说明 pytest 无法建立这条生命周期关系。
- 参考结论：pytest 会报告 `ScopeMismatch`，测试不会正常执行。

## 不合格示例

```text
为什么 test_order(base_url) 不会创建 admin_login、Page 或登录 Context？
```

问题：没有给出 `admin_login` 定义和依赖关系，而且把 fixture 解析、Page 创建和 Context 生命周期混在一个问题里。

# 故障列表时间选择器中文化 Implementation Plan

> **For agentic workers:** 在当前工作区按 TDD 执行；未经用户明确要求不创建分支、worktree 或 Git 提交。

**Goal:** 将故障列表筛选页的 Flatpickr 时间选择界面中文化，且不自动填入筛选时间。

**Architecture:** 复用现有中文 locale 模板，通过 `disable_default_now` 参数隔离本地化和自动填时行为。列表页传入禁用参数，编辑页保持现状。

**Tech Stack:** Django Templates、JavaScript、unittest

---

### Task 1: 回归测试

- [ ] 新增 `tests/test_otnfault_list_datetime_locale.py`，断言列表页加载中文 locale 且禁用自动填时。
- [ ] 断言 locale 模板仅在未禁用时注册 `onOpen` 自动填时钩子。
- [ ] 运行测试并确认因功能缺失失败。

### Task 2: 最小实现

- [ ] 在 `flatpickr_zh.html` 中用 `{% if not disable_default_now %}` 包裹自动填时逻辑。
- [ ] 在 `otnfault_list.html` 中以 `disable_default_now=True` 引入中文 locale 模板。
- [ ] 运行新测试并确认通过。

### Task 3: 验证

- [ ] 运行时间筛选和模板相关回归测试。
- [ ] 运行 Python 编译、差异检查并确认修改范围。

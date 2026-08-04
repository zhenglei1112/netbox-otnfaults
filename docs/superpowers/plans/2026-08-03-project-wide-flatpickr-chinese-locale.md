# 全项目 Flatpickr 中文化 Implementation Plan

> **For agentic workers:** 在当前工作区按 TDD 执行；未经用户明确要求不创建分支、worktree 或 Git 提交。

**Goal:** 为插件当前全部 NetBox `DateTimePicker`/`DatePicker` 页面提供中文 Flatpickr 界面。

**Architecture:** 使用三个共享包装模板覆盖 NetBox 通用列表、编辑和批量编辑模板；已有自定义模板直接加载中文模板。新增覆盖均禁用自动填时，避免语言修复改变字段值。

**Tech Stack:** Django Templates、NetBox 4 通用视图、JavaScript、unittest

---

### Task 1: 失败覆盖测试

- [ ] 新增源码审计测试，锁定所有遗漏列表、编辑、批量编辑和割接生成故障页面。
- [ ] 断言共享模板加载中文 locale 并设置 `disable_default_now=True`。
- [ ] 运行测试并确认因共享模板和视图绑定缺失而失败。

### Task 2: 共享模板与视图接入

- [ ] 新增列表、编辑、批量编辑三个共享模板。
- [ ] 为割接任务/影响列表、重要保障编辑和全部相关批量编辑视图设置共享模板。
- [ ] 为故障影响列表、重要保障列表、割接生成故障自定义模板加载中文 locale。
- [ ] 运行新测试并确认通过。

### Task 3: 项目级审计验证

- [ ] 重新统计全部日期控件及其模板覆盖路径。
- [ ] 运行日期相关回归、Python 编译和差异检查。

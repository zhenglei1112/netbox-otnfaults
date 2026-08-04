# 今明割接通报结构化提示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 9 点、18 点割接通报改为带 24 小时时间窗和逐条字段明细的结构化格式，同时保留业务分组。

**Architecture:** 扩展纯 Python 格式化器，集中处理字段清洗、条目正文和时间窗标题；`dashboard.py` 继续负责查询和现有分组，只补充字段映射及组内编号。

**Tech Stack:** Python 3.10+、Django 5.0、NetBox Dashboard Widget、`unittest`

---

### Task 1: 锁定结构化单条通报

**Files:**
- Modify: `tests/test_cutover_report_text.py`
- Modify: `netbox_otnfaults/services/cutover_report_text.py`

- [x] **Step 1:** 更新测试，传入编号、割接类型和地点，断言截图所示六行结构。
- [x] **Step 2:** 运行 `python -m unittest tests.test_cutover_report_text -v`，确认旧签名或旧正文导致失败。
- [x] **Step 3:** 扩展带类型提示的格式化器，生成最小合规正文。
- [x] **Step 4:** 重跑格式化器测试并确认通过。

### Task 2: 接入小组件并保持业务分组

**Files:**
- Modify: `tests/test_dashboard_today_tomorrow_cutover_widget.py`
- Modify: `netbox_otnfaults/dashboard.py`

- [x] **Step 1:** 增加失败断言，要求传入编号、割接类型、地点并构建 24 小时标题；保留原分组断言。
- [x] **Step 2:** 运行 `python -m unittest tests.test_dashboard_today_tomorrow_cutover_widget -v` 并确认预期失败。
- [x] **Step 3:** 在现有分组循环维护组内编号并补充字段；完整报告增加时间窗标题。
- [x] **Step 4:** 运行两个相关测试模块并确认通过。

### Task 3: 静态验证

**Files:**
- Modify: `PLAN.md`

- [x] **Step 1:** 运行 Python 编译检查：

```powershell
python -m py_compile netbox_otnfaults/services/cutover_report_text.py netbox_otnfaults/dashboard.py tests/test_cutover_report_text.py tests/test_dashboard_today_tomorrow_cutover_widget.py
```

- [x] **Step 2:** 运行 `git diff --check`。
- [x] **Step 3:** 将 `PLAN.md` 对应任务更新为已完成。

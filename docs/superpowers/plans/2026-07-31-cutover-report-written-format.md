# 割接通报书面化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 9 点和 18 点割接通报正文统一为无空格、无中括号的书面化固定模板。

**Architecture:** 在独立的纯 Python 格式化模块中集中处理动态字段空白清理、中文日期格式和正文拼接，`dashboard.py` 只负责查询业务数据并调用格式化函数。现有租户组分组、数量统计和复制逻辑保持不变。

**Tech Stack:** Python 3.10+、Django 5.0、`unittest`

---

### Task 1: 增加可独立测试的割接通报正文格式化器

**Files:**
- Create: `netbox_otnfaults/services/cutover_report_text.py`
- Create: `tests/test_cutover_report_text.py`

- [ ] **Step 1: 编写失败测试**

创建 `tests/test_cutover_report_text.py`，传入含普通空格和制表符的省份、原因、业务名称及站点，断言输出严格等于已确认样例，并断言正文不含空格、中括号或箭头。

- [ ] **Step 2: 运行测试并确认因模块不存在而失败**

Run: `python -m unittest tests.test_cutover_report_text -v`

Expected: `ERROR`，提示 `netbox_otnfaults.services.cutover_report_text` 不存在。

- [ ] **Step 3: 编写最小实现**

创建带完整类型提示的 `_remove_whitespace(value: object) -> str` 和 `build_cutover_report_line(...) -> str`。前者使用 `''.join(str(value).split())` 清理动态字段，后者按 `YYYY年M月D日HH:MM` 和确认的书面模板拼接正文。

- [ ] **Step 4: 运行测试并确认通过**

Run: `python -m unittest tests.test_cutover_report_text -v`

Expected: `Ran 1 test ... OK`

### Task 2: 将 9 点/18 点通报接入统一格式化器

**Files:**
- Modify: `netbox_otnfaults/dashboard.py:1-12,425-437`
- Modify: `tests/test_dashboard_today_tomorrow_cutover_widget.py:44-62`

- [ ] **Step 1: 更新源码回归测试并确认失败**

断言 `dashboard.py` 导入并调用 `build_cutover_report_line`，传入省份、原因、时间、时长、业务名称和 A/Z 站点；删除旧的中括号箭头正文断言。

Run: `python -m unittest tests.test_dashboard_today_tomorrow_cutover_widget.DashboardTodayTomorrowCutoverWidgetTestCase.test_widget_report_groups_bare_fiber_impacts_by_tenant_group -v`

Expected: `FAIL`，提示格式化器导入或调用不存在。

- [ ] **Step 2: 接入格式化器**

在 `dashboard.py` 导入 `build_cutover_report_line`，将本地化后的计划时间及各动态字段传给该函数；不改变分组、数量统计和复制数据结构。

- [ ] **Step 3: 运行割接通报定向测试**

Run: `python -m unittest tests.test_cutover_report_text tests.test_dashboard_today_tomorrow_cutover_widget -v`

Expected: 所有测试通过，输出以 `OK` 结束。

- [ ] **Step 4: 运行 Python 编译检查**

Run: `python -m py_compile netbox_otnfaults/services/cutover_report_text.py netbox_otnfaults/dashboard.py tests/test_cutover_report_text.py tests/test_dashboard_today_tomorrow_cutover_widget.py`

Expected: 退出码为 `0`，无错误输出。

- [ ] **Step 5: 检查变更范围**

Run: `git diff --check`

Expected: 退出码为 `0`，无空白错误。

> 根据项目 `AGENTS.md`，本计划不创建分支或 worktree，也不暂存、提交、推送或创建 Pull Request。

### Task 3: 修正未关联业务的正文措辞

**Files:**
- Modify: `tests/test_cutover_report_text.py`
- Modify: `netbox_otnfaults/services/cutover_report_text.py`

- [x] **Step 1: 编写未关联业务失败测试**

在 `tests/test_cutover_report_text.py` 增加 `test_reports_no_business_impact_when_service_is_unlinked()`，调用 `build_cutover_report_line()` 并传入 `service_name="未关联业务"`；断言完整正文包含“不影响业务，A端”，且不包含“影响未关联业务业务”。

- [x] **Step 2: 运行测试并确认因旧模板而失败**

Run: `python -m unittest tests.test_cutover_report_text.CutoverReportTextTestCase.test_reports_no_business_impact_when_service_is_unlinked -v`

Expected: `FAIL`，实际正文仍包含“影响未关联业务业务”。

- [x] **Step 3: 编写最小实现**

在 `build_cutover_report_line()` 中先清洗 `service_name`，当清洗结果严格等于 `未关联业务` 时使用 `不影响业务`，否则继续使用 `影响{service_name}业务`；正文其他部分不变。

- [x] **Step 4: 运行定向测试并确认通过**

Run: `python -m unittest tests.test_cutover_report_text -v`

Expected: `Ran 2 tests ... OK`

- [x] **Step 5: 运行相关回归和静态验证**

Run: `python -m unittest tests.test_cutover_report_text tests.test_dashboard_today_tomorrow_cutover_widget -v`

Expected: 所有测试通过，输出以 `OK` 结束。

Run: `python -m py_compile netbox_otnfaults/services/cutover_report_text.py tests/test_cutover_report_text.py`

Expected: 退出码为 `0`，无错误输出。

Run: `git diff --check`

Expected: 退出码为 `0`，无空白错误。

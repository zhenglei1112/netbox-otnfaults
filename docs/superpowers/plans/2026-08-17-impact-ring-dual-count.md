# 故障等级环形图双口径中心数字 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让三张故障等级环形图中心同时显示总数与不含挂起数量。

**Architecture:** 在前端共用的 `buildRingOption()` 中从现有扇区列表计算总数、挂起数和非挂起数，再生成统一的两行 ECharts 中心标题。不修改后端接口或下钻事件，只提升脚本查询版本以使新文案及时生效。

**Tech Stack:** JavaScript、ECharts、Django 模板、Python `unittest`

---

### Task 1: 锁定双口径中心文案

**Files:**
- Modify: `tests/test_statistics_impact_level.py`
- Test: `tests/test_statistics_impact_level.py`

- [x] **Step 1: 写入失败源码测试**

在 `StatisticsImpactLevelTestCase` 中增加：

```python
def test_ring_chart_centers_show_total_and_non_suspended_counts(self) -> None:
    js_source = _read(DASHBOARD_JS_PATH)
    html_source = _read(DASHBOARD_HTML_PATH)
    ring_source = js_source.split(
        "const buildRingOption = (titleText, dataList) => {", 1
    )[1].split("if (chartsData.ring_fiber)", 1)[0]

    self.assertIn("const suspendedItem = dataList.find(item => item.name === '挂起');", ring_source)
    self.assertIn("const suspended = suspendedItem ? (suspendedItem.value || 0) : 0;", ring_source)
    self.assertIn("const nonSuspended = total - suspended;", ring_source)
    self.assertIn("text: `${total}/${nonSuspended}起`,", ring_source)
    self.assertIn("subtext: '总数/不含挂起',", ring_source)
    self.assertNotIn("text: total + '起',", ring_source)
    self.assertIn("statistics_dashboard.js' %}?v=42", html_source)
```

- [x] **Step 2: 运行测试并确认按预期失败**

Run: `python -m unittest tests.test_statistics_impact_level.StatisticsImpactLevelTestCase.test_ring_chart_centers_show_total_and_non_suspended_counts -v`

Expected: `FAIL`，提示共用环形图配置中尚无挂起数量计算或双口径文案。

### Task 2: 实现共用双口径中心标题

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js:2275`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html:1395`

- [x] **Step 1: 计算挂起与非挂起数量**

在 `total` 计算之后增加：

```javascript
const suspendedItem = dataList.find(item => item.name === '挂起');
const suspended = suspendedItem ? (suspendedItem.value || 0) : 0;
const nonSuspended = total - suspended;
```

- [x] **Step 2: 修改中心两行文案**

将 ECharts `title` 文案改为：

```javascript
text: `${total}/${nonSuspended}起`,
subtext: '总数/不含挂起',
```

- [x] **Step 3: 提升脚本查询版本**

将模板底部的脚本地址从 `statistics_dashboard.js?v=41` 改为 `statistics_dashboard.js?v=42`。

- [x] **Step 4: 运行定向测试并确认通过**

Run: `python -m unittest tests.test_statistics_impact_level.StatisticsImpactLevelTestCase.test_ring_chart_centers_show_total_and_non_suspended_counts -v`

Expected: `OK`。

### Task 3: 回归验证与计划收尾

**Files:**
- Modify: `PLAN.md`

- [x] **Step 1: 运行相关测试**

Run: `python -m unittest tests.test_statistics_impact_level tests.test_statistics_cable_break_overview`

Expected: 100 项以上相关测试全部通过。

- [x] **Step 2: 检查差异格式**

Run: `git diff --check`

Expected: 退出码为 0，无空白错误。

- [x] **Step 3: 更新项目计划状态**

将 `PLAN.md` 中本任务三项由 `[ ]` 更新为 `[x]`。

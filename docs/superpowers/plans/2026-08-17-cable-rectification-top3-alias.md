# 原因 TOP3 光缆整改展示别名 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在物理故障的原因 TOP3 起数和历时卡片中把“光缆整改”显示为“光缆整改未报备”，同时保留原始下钻筛选值。

**Architecture:** 为共用卡片项增加可选 `displayName`，显示和弹窗文案使用它，趋势匹配及筛选值继续使用原始 `name`。局部别名函数只处理两个物理故障原因 TOP3 当前列表，不修改后端或分公司卡片。

**Tech Stack:** JavaScript、Django 模板、Python `unittest`

---

### Task 1: 锁定展示别名与原始筛选值

**Files:**
- Modify: `tests/test_statistics_cable_break_overview.py`
- Test: `tests/test_statistics_cable_break_overview.py`

- [x] **Step 1: 写入失败源码测试**

在 `StatisticsCableBreakOverviewTestCase` 中增加：

```python
def test_reason_top3_uses_unreported_rectification_display_alias(self) -> None:
    source = JS_PATH.read_text(encoding="utf-8")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    flex_source = source.split("function buildFlexGroup(", 1)[1].split(
        "function normalizeTopItems", 1
    )[0]
    overview_source = source.split("function renderCableBreakOverview(", 1)[1].split(
        "function renderBareFiberInterruption", 1
    )[0]
    branch_source = source.split("function renderBranchCompanyOverview(", 1)[1].split(
        "function renderBranchCompanyBarCharts", 1
    )[0]

    self.assertIn("function withCableRectificationDisplayName(items) {", source)
    self.assertIn("item.name !== '光缆整改'", source)
    self.assertIn("displayName: '光缆整改未报备'", source)
    self.assertIn("const displayName = item && item.displayName !== undefined ? item.displayName : name;", flex_source)
    self.assertIn("const itemFilterValue = item && item.filterValue !== undefined ? item.filterValue : name;", flex_source)
    self.assertIn("const itemFilterLabel = item && item.filterLabel !== undefined ? item.filterLabel : displayName;", flex_source)
    self.assertIn("buildFlexItemCore(val, itemUnit, displayName,", flex_source)
    self.assertIn("withCableRectificationDisplayName(normalizeTopItems(overview.reason_top3 || [], 3))", overview_source)
    self.assertIn("withCableRectificationDisplayName(normalizeTopItems((overview.reason_duration_top3 || []).map", overview_source)
    self.assertNotIn("withCableRectificationDisplayName", branch_source)
    self.assertIn("statistics_dashboard.js' %}?v=43", template)
```

- [x] **Step 2: 运行测试并确认按预期失败**

Run: `python -m unittest tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_reason_top3_uses_unreported_rectification_display_alias -v`

Expected: `FAIL`，提示缺少别名函数或 `displayName` 处理。

### Task 2: 实现显示名与筛选值分离

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js:1600-1820`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html:1427`

- [x] **Step 1: 扩展共用卡片项显示名**

在 `buildFlexGroup()` 中保留原始 `name`，并增加：

```javascript
const displayName = item && item.displayName !== undefined ? item.displayName : name;
```

默认 `itemFilterValue` 继续取 `name`，默认 `itemFilterLabel` 改取 `displayName`，传给 `buildFlexItemCore()` 的标签参数也改为 `displayName`。

- [x] **Step 2: 增加局部原因别名函数**

在 TOP3 归一化函数附近增加：

```javascript
function withCableRectificationDisplayName(items) {
    return (items || []).map(item => {
        if (!item || item.name !== '光缆整改') return item;
        return {...item, displayName: '光缆整改未报备'};
    });
}
```

- [x] **Step 3: 仅应用于两个物理故障原因 TOP3 列表**

将起数列表改为：

```javascript
const reasonTop3 = withCableRectificationDisplayName(
    normalizeTopItems(overview.reason_top3 || [], 3)
);
```

将历时列表改为：

```javascript
const durReasonItems = withCableRectificationDisplayName(
    normalizeTopItems((overview.reason_duration_top3 || []).map(i => ({
        name: i.name || i.title,
        value: Number(i.value || 0),
    })), 3)
);
```

- [x] **Step 4: 提升脚本查询版本**

将模板底部 `statistics_dashboard.js?v=42` 改为 `statistics_dashboard.js?v=43`。

- [x] **Step 5: 运行定向测试并确认通过**

Run: `python -m unittest tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_reason_top3_uses_unreported_rectification_display_alias -v`

Expected: `OK`。

### Task 3: 回归验证与计划收尾

**Files:**
- Modify: `PLAN.md`

- [x] **Step 1: 检查 JavaScript 语法并运行相关测试**

Run: `node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`

Expected: 退出码为 0，无输出。

Run: `python -m unittest tests.test_statistics_cable_break_overview tests.test_statistics_impact_level`

Expected: 101 项以上相关测试全部通过。

- [x] **Step 2: 检查差异格式**

Run: `git diff --check`

Expected: 退出码为 0，无空白错误。

- [x] **Step 3: 更新项目计划状态**

将 `PLAN.md` 中本任务三项由 `[ ]` 更新为 `[x]`。

### Task 4: 将别名扩展到主要原因图

**Files:**
- Modify: `tests/test_statistics_cable_break_overview.py`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js:1645-2265`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html:1427`
- Modify: `PLAN.md`

- [x] **Step 1: 写入失败源码测试**

在 `StatisticsCableBreakOverviewTestCase` 中增加：

```python
def test_main_reason_chart_uses_rectification_display_alias_without_changing_filter_name(self) -> None:
    source = JS_PATH.read_text(encoding="utf-8")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    reason_source = source.split("// 3. 一级原因 (Pie)", 1)[1].split(
        "function renderRingCharts", 1
    )[0]

    self.assertIn("function getCableRectificationDisplayName(name) {", source)
    self.assertIn("return name === '光缆整改' ? '光缆整改未报备' : name;", source)
    self.assertIn("displayName: getCableRectificationDisplayName(item.name)", source)
    self.assertIn("const reasonDisplayName = getCableRectificationDisplayName(params.name);", reason_source)
    self.assertIn("`${params.marker}${reasonDisplayName}:", reason_source)
    self.assertIn("const reasonDisplayName = getCableRectificationDisplayName(name);", reason_source)
    self.assertIn("return isReasonCount ? `${reasonDisplayName}", reason_source)
    self.assertIn("const reasonData = chartsData.reason.map(item => ({name: item.name,", reason_source)
    self.assertIn("chartReason.on('click', params => handleChartClick(params, 'reason', 'cable_break', currentMetricReason));", source)
    self.assertIn("chartReason.on('legendselectchanged', params => { updateExcludedSet('reason', params.selected);", source)
    self.assertIn("statistics_dashboard.js' %}?v=44", template)
```

- [x] **Step 2: 运行测试并确认按预期失败**

Run: `python -m unittest tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_main_reason_chart_uses_rectification_display_alias_without_changing_filter_name -v`

Expected: `FAIL`，提示缺少统一展示名函数或主要原因图尚未调用它。

- [x] **Step 3: 提取统一原因展示名函数**

在已有 TOP3 别名函数之前增加：

```javascript
function getCableRectificationDisplayName(name) {
    return name === '光缆整改' ? '光缆整改未报备' : name;
}
```

将 `withCableRectificationDisplayName()` 返回项改为：

```javascript
return {...item, displayName: getCableRectificationDisplayName(item.name)};
```

- [x] **Step 4: 修改主要原因图图例和提示框**

提示框格式化中使用：

```javascript
const reasonDisplayName = getCableRectificationDisplayName(params.name);
```

图例格式化中使用：

```javascript
const reasonDisplayName = getCableRectificationDisplayName(name);
```

两处输出展示 `reasonDisplayName`，但 `reasonData` 的 `name`、点击事件和图例选择事件保持原样。

- [x] **Step 5: 提升脚本查询版本**

将模板底部 `statistics_dashboard.js?v=43` 改为 `statistics_dashboard.js?v=44`。

- [x] **Step 6: 运行定向测试并确认通过**

Run: `python -m unittest tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_main_reason_chart_uses_rectification_display_alias_without_changing_filter_name -v`

Expected: `OK`。

- [x] **Step 7: 运行完整相关验证**

Run: `node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`

Expected: 退出码为 0，无输出。

Run: `python -m unittest tests.test_statistics_cable_break_overview tests.test_statistics_impact_level`

Expected: 103 项以上相关测试全部通过。

Run: `git diff --check`

Expected: 退出码为 0，无空白错误。

- [x] **Step 8: 更新项目计划状态**

将 `PLAN.md` 中本次“主要原因”图三项由 `[ ]` 更新为 `[x]`。

# 故障统计标题筛选口径标签化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将故障统计物理故障页两个区域标题中的筛选口径说明改成独立的橙色标签。

**Architecture:** 保留现有标题容器、主标题和地图按钮，只拆分标题 HTML 文本并使用 Bootstrap 5 原生警告徽章。用源码级模板测试验证 DOM 结构，不改变后端统计或前端交互逻辑。

**Tech Stack:** Django 模板、Bootstrap 5、Python `unittest`

---

### Task 1: 锁定筛选口径标签结构

**Files:**
- Modify: `tests/test_statistics_cable_break_overview.py`
- Test: `tests/test_statistics_cable_break_overview.py`

- [x] **Step 1: 写入失败测试**

在 `StatisticsCableBreakOverviewTestCase` 中增加：

```python
def test_statistics_scope_notes_use_separate_warning_badges(self) -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    compact_template = _compact_html(template)

    self.assertIn(
        '<span>故障和异常事件（按影响程度划分等级）</span> '
        '<span class="badge bg-warning text-dark">不含报备割接</span>',
        compact_template,
    )
    self.assertIn(
        '<span>光缆中断情况</span> '
        '<span class="badge bg-warning text-dark">不含报备割接</span> '
        '<span class="badge bg-warning text-dark">不含挂起</span>',
        compact_template,
    )
    self.assertNotIn("故障和异常事件（按影响程度划分等级）- 不含报备割接", template)
    self.assertNotIn("光缆中断情况 - 不含报备割接，不含挂起", template)
```

- [x] **Step 2: 运行测试并确认按预期失败**

Run: `python -m unittest tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_statistics_scope_notes_use_separate_warning_badges -v`

Expected: `FAIL`，提示找不到拆分后的 `badge bg-warning text-dark` 标签结构。

### Task 2: 使用 Bootstrap 标签渲染筛选口径

**Files:**
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html:320`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html:435`

- [x] **Step 1: 修改影响等级标题**

将标题内容替换为：

```html
<span>故障和异常事件（按影响程度划分等级）</span>
<span class="badge bg-warning text-dark">不含报备割接</span>
```

- [x] **Step 2: 修改光缆中断标题**

在现有地图按钮之前放置：

```html
<span>光缆中断情况</span>
<span class="badge bg-warning text-dark">不含报备割接</span>
<span class="badge bg-warning text-dark">不含挂起</span>
```

- [x] **Step 3: 运行定向测试并确认通过**

Run: `python -m unittest tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_statistics_scope_notes_use_separate_warning_badges -v`

Expected: `OK`。

### Task 3: 回归验证与差异检查

**Files:**
- Modify: `PLAN.md`

- [x] **Step 1: 运行相关模板测试集**

Run: `python -m unittest tests.test_statistics_cable_break_overview tests.test_statistics_impact_level -v`

Expected: 全部测试通过，无错误或失败。

- [x] **Step 2: 检查改动范围**

Run: `git diff --check`

Expected: 无输出，退出码为 0。

- [x] **Step 3: 更新项目计划状态**

将 `PLAN.md` 中本任务三项由 `[ ]` 更新为 `[x]`，记录测试先行、模板修改和回归验证均已完成。

### Task 4: 缩小筛选口径标签

**Files:**
- Modify: `tests/test_statistics_cable_break_overview.py`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html:321`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/css/statistics_dashboard.css:1389`
- Modify: `PLAN.md`

- [x] **Step 1: 写入失败样式测试并更新结构断言**

在 `StatisticsCableBreakOverviewTestCase` 中增加：

```python
def test_statistics_scope_badges_use_compact_dimensions(self) -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    css = CSS_PATH.read_text(encoding="utf-8")

    self.assertEqual(
        template.count('class="badge bg-warning text-dark statistics-scope-badge"'),
        3,
    )
    self.assertIn(".statistics-scope-badge {", css)
    self.assertIn("font-size: 0.75rem;", css)
    self.assertIn("line-height: 1;", css)
    self.assertIn("padding: 0.2rem 0.45rem;", css)
```

同时将既有标签结构测试中的类名更新为 `badge bg-warning text-dark statistics-scope-badge`，使预期结构与设计一致。

- [x] **Step 2: 运行两个标签测试并确认按预期失败**

Run: `python -m unittest tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_statistics_scope_notes_use_separate_warning_badges tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_statistics_scope_badges_use_compact_dimensions -v`

Expected: `FAIL`，提示模板缺少 `statistics-scope-badge`，且样式表缺少对应尺寸规则。

- [x] **Step 3: 为三个标签增加专用类**

三个标签统一使用：

```html
<span class="badge bg-warning text-dark statistics-scope-badge">标签文字</span>
```

- [x] **Step 4: 增加局部紧凑尺寸样式**

在标题样式附近增加：

```css
.statistics-scope-badge {
    font-size: 0.75rem;
    line-height: 1;
    padding: 0.2rem 0.45rem;
}
```

- [x] **Step 5: 运行两个标签测试并确认通过**

Run: `python -m unittest tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_statistics_scope_notes_use_separate_warning_badges tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_statistics_scope_badges_use_compact_dimensions -v`

Expected: 两项测试均为 `ok`，最终输出 `OK`。

- [x] **Step 6: 运行相关回归与差异检查**

Run: `python -m unittest tests.test_statistics_cable_break_overview tests.test_statistics_impact_level && git diff --check`

Expected: 99 项以上相关测试全部通过，`git diff --check` 退出码为 0。

- [x] **Step 7: 更新项目计划状态**

将 `PLAN.md` 中本次尺寸调整的三项由 `[ ]` 更新为 `[x]`。

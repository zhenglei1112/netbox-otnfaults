# 故障统计可见指标说明分 Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将指标说明改为覆盖全部可见页面的 5 个说明 Tab，并在每次打开时默认同步当前主页面 Tab。

**Architecture:** 模板使用 Bootstrap 5 原生 nav-tabs/tab-pane 承载静态说明内容；现有统计脚本只负责在弹窗打开前建立主页面 Tab 与说明 Tab 的固定映射并激活目标说明。统计 API、数据结构和主页面切换逻辑保持不变。

**Tech Stack:** Django 模板、Bootstrap 5、原生 JavaScript、Python `unittest` 源码级回归测试。

---

### Task 1: 锁定说明结构和可见内容边界

**Files:**
- Modify: `tests/test_statistics_dashboard_assets.py:189-228`
- Test: `tests/test_statistics_dashboard_assets.py`

- [x] **Step 1: 编写失败测试**

在 `StatisticsDashboardAssetsTestCase` 中将原有说明弹窗测试更新为以下断言：

```python
self.assertIn('id="statistics-help-tab-physical"', template)
self.assertIn('id="statistics-help-tab-bare-fiber"', template)
self.assertIn('id="statistics-help-tab-circuit"', template)
self.assertIn('id="statistics-help-tab-branch-company"', template)
self.assertIn('id="statistics-help-tab-branch-performance"', template)
self.assertIn("不含计划报备整改", template)
self.assertIn("上须阈值", template)
self.assertIn("所选省份范围内的历史挂起故障总数", template)
self.assertNotIn("考核评分（100分制）", template)
self.assertNotIn("频次扣分", template)
self.assertNotIn("I类和II类（阻断故障）", template)
```

- [x] **Step 2: 运行测试确认 RED**

Run: `python -m unittest tests.test_statistics_dashboard_assets.StatisticsDashboardAssetsTestCase.test_statistics_dashboard_exposes_metric_explanation_modal`

Expected: FAIL，原因是 5 个说明 Tab 和新口径文案尚不存在。

### Task 2: 实现 5 个可见页面说明 Tab

**Files:**
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html:1216-1331`
- Test: `tests/test_statistics_dashboard_assets.py`

- [x] **Step 1: 用 Bootstrap 5 Tab 重组弹窗**

在弹窗正文中加入固定导航：

```html
<ul class="nav nav-tabs statistics-metric-help-tabs" role="tablist">
  <li class="nav-item" role="presentation">
    <button class="nav-link active" id="statistics-help-tab-physical"
      data-bs-toggle="tab" data-bs-target="#statistics-help-pane-physical"
      type="button" role="tab" aria-controls="statistics-help-pane-physical"
      aria-selected="true">物理故障</button>
  </li>
  <!-- 按主页面顺序继续加入裸纤业务故障、电路业务故障、子公司（省份）故障、子公司绩效 -->
</ul>
```

对应建立 5 个 `tab-pane`。每个 pane 只保留该主页面实际渲染内容的说明；删除隐藏总体情况、隐藏 I+II 指标、评分、评级、扣分和责任权重说明。物理故障说明明确计划报备整改排除、箱线图上须阈值和挂起历史总数省份范围。

- [x] **Step 2: 更新静态脚本版本号**

将模板末尾 `statistics_dashboard.js` 查询版本从 `v=44` 更新为 `v=45`。

- [x] **Step 3: 运行说明内容测试确认 GREEN**

Run: `python -m unittest tests.test_statistics_dashboard_assets.StatisticsDashboardAssetsTestCase.test_statistics_dashboard_exposes_metric_explanation_modal`

Expected: PASS。

### Task 3: 打开弹窗时同步当前主页面 Tab

**Files:**
- Modify: `tests/test_statistics_dashboard_assets.py`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js:4-120`
- Test: `tests/test_statistics_dashboard_assets.py`

- [x] **Step 1: 编写失败测试**

新增源码级测试锁定映射与事件：

```python
self.assertIn("const statisticsMetricHelpTabMap", script)
self.assertIn("'tab-physical-btn': 'statistics-help-tab-physical'", script)
self.assertIn("'tab-service-btn': 'statistics-help-tab-bare-fiber'", script)
self.assertIn("'tab-circuit-service-btn': 'statistics-help-tab-circuit'", script)
self.assertIn("'tab-branch-company-btn': 'statistics-help-tab-branch-company'", script)
self.assertIn("'tab-branch-performance-btn': 'statistics-help-tab-branch-performance'", script)
self.assertIn("statisticsMetricHelpModal.addEventListener('show.bs.modal'", script)
self.assertIn("bootstrap.Tab.getOrCreateInstance(helpTab).show()", script)
```

- [x] **Step 2: 运行测试确认 RED**

Run: `python -m unittest tests.test_statistics_dashboard_assets.StatisticsDashboardAssetsTestCase.test_metric_help_defaults_to_active_dashboard_tab`

Expected: FAIL，原因是映射和 `show.bs.modal` 监听尚不存在。

- [x] **Step 3: 实现最小同步逻辑**

在 DOM 初始化作用域中加入：

```javascript
const statisticsMetricHelpTabMap = {
    'tab-physical-btn': 'statistics-help-tab-physical',
    'tab-service-btn': 'statistics-help-tab-bare-fiber',
    'tab-circuit-service-btn': 'statistics-help-tab-circuit',
    'tab-branch-company-btn': 'statistics-help-tab-branch-company',
    'tab-branch-performance-btn': 'statistics-help-tab-branch-performance',
};
const statisticsMetricHelpModal = document.getElementById('statisticsMetricHelpModal');
if (statisticsMetricHelpModal) {
    statisticsMetricHelpModal.addEventListener('show.bs.modal', () => {
        const activeMainTab = document.querySelector('#statisticsTab .nav-link.active');
        const helpTabId = statisticsMetricHelpTabMap[activeMainTab && activeMainTab.id]
            || 'statistics-help-tab-physical';
        const helpTab = document.getElementById(helpTabId);
        if (helpTab) bootstrap.Tab.getOrCreateInstance(helpTab).show();
    });
}
```

- [x] **Step 4: 运行同步测试确认 GREEN**

Run: `python -m unittest tests.test_statistics_dashboard_assets.StatisticsDashboardAssetsTestCase.test_metric_help_defaults_to_active_dashboard_tab`

Expected: PASS。

### Task 4: 全量验证与文档同步

**Files:**
- Modify: `PLAN.md`

- [x] **Step 1: 运行完整说明资产测试**

Run: `python -m unittest tests.test_statistics_dashboard_assets`

Expected: 全部 PASS；同时修正该测试文件中已经过期的 CSS/JS 版本断言。

- [x] **Step 2: 运行故障统计相关回归测试**

Run: `python -m unittest tests.test_statistics_dashboard_assets tests.test_statistics_branch_company tests.test_statistics_cable_break_overview`

Expected: 全部 PASS。

- [x] **Step 3: 检查 JavaScript 语法**

Run: `node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`

Expected: exit code 0，无输出。

- [x] **Step 4: 更新计划状态并检查差异**

在 `PLAN.md` 对应条目勾选已完成步骤；运行 `git diff --check` 和 `git diff --stat`，确认没有空白错误或范围外修改。

根据项目约定，不创建分支/worktree，不暂存、不提交、不推送。

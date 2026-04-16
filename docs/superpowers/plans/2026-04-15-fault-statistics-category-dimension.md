# Fault Statistics Category Dimension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fourth physical fault statistics chart for fault category, wire it into drill-down and exclusion filtering, and cover the change with source-level regression tests.

**Architecture:** Keep the existing `FaultStatisticsDataAPI` response shape and extend `charts` with a new `category` collection derived from `fault.get_fault_category_display()`. Update the statistics dashboard template to host a fourth chart card, and extend the existing plain-JS dashboard controller with a `chartCategory` instance plus unified category filtering logic while removing duplicate chart click bindings in the same file.

**Tech Stack:** Django view, Django template, NetBox plugin static assets, plain JavaScript, ECharts, `unittest`

---

### Task 1: Add failing source-level tests for the new category dimension

**Files:**
- Create: `tests/test_fault_statistics_category_dimension.py`
- Test: `tests/test_fault_statistics_category_dimension.py`

- [ ] **Step 1: Write the failing test file**

```python
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STATISTICS_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
STATISTICS_TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
)
STATISTICS_JS_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"
)


class FaultStatisticsCategoryDimensionTestCase(unittest.TestCase):
    def test_statistics_view_exposes_category_chart_data(self) -> None:
        source = STATISTICS_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("category_stats = {}", source)
        self.assertIn("category = fault.get_fault_category_display()", source)
        self.assertIn("'category': [{'name': k, 'value': v['count'], 'duration': round(v['duration'], 2)}", source)

    def test_statistics_template_renders_fourth_category_chart_card(self) -> None:
        source = STATISTICS_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn('id="chart-category"', source)
        self.assertIn("故障类型分布", source)
        self.assertIn("col-md-6 col-xl-3", source)

    def test_statistics_dashboard_js_wires_category_chart_filtering(self) -> None:
        source = STATISTICS_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("let chartCategory = null;", source)
        self.assertIn("category: new Set()", source)
        self.assertIn("chartCategory = echarts.init(document.getElementById('chart-category'));", source)
        self.assertIn("chartCategory.on('click', params => handleChartClick(params, 'category'));", source)
        self.assertIn("chartCategory.on('legendselectchanged', params => { updateExcludedSet('category', params.selected); renderDetailsTable(); });", source)
        self.assertIn("filteredDetails = filteredDetails.filter(item => !excludedCategories.category.has(item.category));", source)
        self.assertIn("else if (activeFilterField === 'category') filterName = '故障类型';", source)
        self.assertIn("chartCategory.dispatchAction({ type: 'legendAllSelect' });", source)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_fault_statistics_category_dimension -v`

Expected: FAIL with missing assertions for `category_stats = {}`, `chart-category`, and `chartCategory`.

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/test_fault_statistics_category_dimension.py
git commit -m "test: cover fault statistics category dimension"
```

### Task 2: Extend the backend chart payload with fault category aggregation

**Files:**
- Modify: `netbox_otnfaults/statistics_views.py`
- Test: `tests/test_fault_statistics_category_dimension.py`

- [ ] **Step 1: Add a category aggregation bucket beside the existing chart dictionaries**

Insert this near the current chart accumulator setup:

```python
        resource_stats = {}
        province_stats = {}
        reason_stats = {}
        category_stats = {}
```

- [ ] **Step 2: Update the fault loop to aggregate `fault_category` display names**

Add this immediately after the current reason aggregation block:

```python
            category = fault.get_fault_category_display()
            if category not in category_stats:
                category_stats[category] = {'count': 0, 'duration': 0.0}
            category_stats[category]['count'] += 1
            category_stats[category]['duration'] += duration_hours
```

- [ ] **Step 3: Return the new `charts.category` payload**

Extend the `charts` object like this:

```python
            'charts': {
                'resource': [{'name': k, 'value': v['count'], 'duration': round(v['duration'], 2), 'key': v['id']} for k, v in resource_stats.items()],
                'province': [{'name': k, 'value': v['count'], 'duration': round(v['duration'], 2)} for k, v in sorted(province_stats.items(), key=lambda item: item[1]['count'], reverse=True)],
                'reason': [{'name': k, 'value': v['count'], 'duration': round(v['duration'], 2)} for k, v in sorted(reason_stats.items(), key=lambda item: item[1]['count'], reverse=True)],
                'category': [{'name': k, 'value': v['count'], 'duration': round(v['duration'], 2)} for k, v in sorted(category_stats.items(), key=lambda item: item[1]['count'], reverse=True)],
            },
```

- [ ] **Step 4: Re-run the targeted test**

Run: `python -m unittest tests.test_fault_statistics_category_dimension -v`

Expected: The backend assertion now passes, while template and JS assertions still fail.

- [ ] **Step 5: Commit the backend change**

```bash
git add netbox_otnfaults/statistics_views.py
git commit -m "feat: add fault category statistics chart data"
```

### Task 3: Add the fourth chart card to the physical statistics template

**Files:**
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`
- Test: `tests/test_fault_statistics_category_dimension.py`

- [ ] **Step 1: Change the physical chart grid from three fixed columns to a responsive four-card layout**

Replace the current chart row block with this structure:

```html
                <div class="row mb-4 g-3">
                    <div class="col-md-6 col-xl-3">
                        <div class="card shadow-sm h-100">
                            <div class="card-header border-bottom-0"><h3 class="card-title">光缆属性分布</h3></div>
                            <div class="card-body p-0">
                                <div id="chart-resource" style="width: 100%; height: 320px;"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 col-xl-3">
                        <div class="card shadow-sm h-100">
                            <div class="card-header border-bottom-0"><h3 class="card-title">各省份故障 Top 10</h3></div>
                            <div class="card-body p-0">
                                <div id="chart-province" style="width: 100%; height: 320px;"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 col-xl-3">
                        <div class="card shadow-sm h-100">
                            <div class="card-header border-bottom-0"><h3 class="card-title">主要原因分析</h3></div>
                            <div class="card-body p-0">
                                <div id="chart-reason" style="width: 100%; height: 320px;"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 col-xl-3">
                        <div class="card shadow-sm h-100">
                            <div class="card-header border-bottom-0"><h3 class="card-title">故障类型分布</h3></div>
                            <div class="card-body p-0">
                                <div id="chart-category" style="width: 100%; height: 320px;"></div>
                            </div>
                        </div>
                    </div>
                </div>
```

- [ ] **Step 2: Re-run the targeted test**

Run: `python -m unittest tests.test_fault_statistics_category_dimension -v`

Expected: The template assertion now passes, while the JS assertion still fails.

- [ ] **Step 3: Commit the template change**

```bash
git add netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html
git commit -m "feat: add category chart card to fault statistics dashboard"
```

### Task 4: Extend the statistics dashboard controller for category chart rendering and filtering

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
- Test: `tests/test_fault_statistics_category_dimension.py`

- [ ] **Step 1: Add the new chart instance and extend the exclusion state**

Update the top of the file to this shape:

```javascript
    let chartResource = null;
    let chartProvince = null;
    let chartReason = null;
    let chartCategory = null;

    let excludedCategories = {
        resource_type: new Set(),
        province: new Set(),
        reason: new Set(),
        category: new Set()
    };
```

- [ ] **Step 2: Initialize and resize the fourth chart instance**

Replace the current init/resize block with:

```javascript
    chartResource = echarts.init(document.getElementById('chart-resource'));
    chartProvince = echarts.init(document.getElementById('chart-province'));
    chartReason = echarts.init(document.getElementById('chart-reason'));
    chartCategory = echarts.init(document.getElementById('chart-category'));

    window.addEventListener('resize', () => {
        chartResource.resize();
        chartProvince.resize();
        chartReason.resize();
        chartCategory.resize();
    });
```

- [ ] **Step 3: Keep only one set of chart click bindings and extend it to category**

Use one binding block:

```javascript
    chartResource.on('click', params => handleChartClick(params, 'resource_type'));
    chartProvince.on('click', params => handleChartClick(params, 'province'));
    chartReason.on('click', params => handleChartClick(params, 'reason'));
    chartCategory.on('click', params => handleChartClick(params, 'category'));
```

Delete the later duplicate click binding block near the bottom of the file so the handler is registered once per chart.

- [ ] **Step 4: Extend legend exclusion handling to category**

Add this alongside the existing legend handlers:

```javascript
    chartCategory.on('legendselectchanged', params => { updateExcludedSet('category', params.selected); renderDetailsTable(); });
```

- [ ] **Step 5: Render the category pie chart with explicit fault-category colors**

Add this inside `renderCharts(chartsData)` after the reason chart:

```javascript
        const categoryColorMap = {
            '光缆中断': '#8B5CF6',
            '空调故障': '#14B8A6',
            '光缆劣化': '#F97316',
            '光缆抖动': '#06B6D4',
            '设备故障': '#EC4899',
            '供电故障': '#6366F1'
        };

        chartCategory.setOption({
            tooltip: {
                trigger: 'item',
                formatter: params => {
                    let avg = params.value > 0 ? (params.data._duration / params.value).toFixed(2) : "0.00";
                    return `${params.marker}${params.name}: ${params.value}次 (${params.percent}%)<br/>` +
                           `<span style="margin-left:14px;">总历时: ${params.data._duration} 小时</span><br/>` +
                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;
                }
            },
            legend: { bottom: 0, type: 'scroll' },
            series: [{
                type: 'pie',
                radius: '50%',
                center: ['50%', '45%'],
                itemStyle: {
                    color: params => categoryColorMap[params.name] || '#5470c6'
                },
                data: (chartsData.category || []).map(item => ({ name: item.name, value: item.value, _duration: item.duration })),
                emphasis: {
                    itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
                }
            }]
        });
```

- [ ] **Step 6: Extend detail filtering and filter labels to category**

Add the exclusion branch:

```javascript
        if (excludedCategories.category.size > 0) {
            filteredDetails = filteredDetails.filter(item => !excludedCategories.category.has(item.category));
            activeConditions.push(`排除故障类型[${Array.from(excludedCategories.category).join(', ')}]`);
        }
```

Extend the drill-down label mapping:

```javascript
            else if (activeFilterField === 'category') filterName = '故障类型';
```

- [ ] **Step 7: Extend clear-filter logic to category**

Update the clear block to:

```javascript
        excludedCategories.resource_type.clear();
        excludedCategories.province.clear();
        excludedCategories.reason.clear();
        excludedCategories.category.clear();

        chartResource.dispatchAction({ type: 'legendAllSelect' });
        chartReason.dispatchAction({ type: 'legendAllSelect' });
        chartCategory.dispatchAction({ type: 'legendAllSelect' });
```

- [ ] **Step 8: Re-run the targeted test**

Run: `python -m unittest tests.test_fault_statistics_category_dimension -v`

Expected: PASS.

- [ ] **Step 9: Run a JavaScript syntax check**

Run: `node --check netbox_otnfaults\static\netbox_otnfaults\js\statistics_dashboard.js`

Expected: No syntax errors. If `node` is unavailable, note that limitation and do a manual source review for braces and template strings.

- [ ] **Step 10: Commit the front-end change**

```bash
git add netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js
git commit -m "feat: add category chart filtering to fault statistics dashboard"
```

### Task 5: Final verification and plan closeout

**Files:**
- Modify: `netbox_otnfaults/statistics_views.py`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
- Test: `tests/test_fault_statistics_category_dimension.py`

- [ ] **Step 1: Re-run the targeted regression test**

Run: `python -m unittest tests.test_fault_statistics_category_dimension -v`

Expected: PASS with 3 passing tests.

- [ ] **Step 2: Run Python syntax validation on the updated backend file**

Run: `@'
from pathlib import Path
compile(Path("netbox_otnfaults/statistics_views.py").read_text(encoding="utf-8"), "netbox_otnfaults/statistics_views.py", "exec")
print("syntax ok")
'@ | python -`

Expected: `syntax ok`

- [ ] **Step 3: Review the acceptance checklist against the touched files**

Checklist:

- `netbox_otnfaults/statistics_views.py` returns `charts.category`
- `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html` contains `chart-category`
- `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js` has one chart click binding block, not duplicates
- category drill-down and legend exclusion both target `details[].category`
- clear-filter resets category legend state too

- [ ] **Step 4: Commit the final verification-only changes if any cleanup was needed**

```bash
git add netbox_otnfaults/statistics_views.py netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js tests/test_fault_statistics_category_dimension.py
git commit -m "chore: finalize fault statistics category dimension"
```

Skip this commit if Task 4 already captured the final file state.

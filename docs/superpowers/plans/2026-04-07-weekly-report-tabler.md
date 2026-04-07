# Weekly Report Tabler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the weekly report page as a Tabler-style dashboard while preserving the existing weekly report API and ECharts-driven data display.

**Architecture:** Keep the current Django view and JSON API as the data source, replace the page shell with a Tabler-oriented template, restyle the screen with dashboard cards instead of big-screen visuals, and update the plain-JS rendering helpers to target the new DOM structure. Avoid NetBox core changes and keep backend changes minimal and additive.

**Tech Stack:** Django template, NetBox plugin static assets, Bootstrap-compatible Tabler markup, plain JavaScript, ECharts

---

### Task 1: Prepare the page contract and optional backend metadata

**Files:**
- Modify: `netbox_otnfaults/weekly_report_views.py`

- [ ] **Step 1: Write the failing backend expectation as a comment-backed checklist**

Use this checklist to drive the edit:

```python
# Weekly report page contract after refactor:
# 1. Existing keys remain available:
#    period, summary, reasons_analysis, top_provinces, major_events, bare_fiber
# 2. Optional additive metadata may be returned:
#    generated_at
# 3. The page view still renders the same template path.
```

- [ ] **Step 2: Inspect whether the API already includes all fields needed by the new dashboard**

Run: `Get-Content netbox_otnfaults\weekly_report_views.py`

Expected: The response already contains `period`, `summary`, `reasons_analysis`, `top_provinces`, `major_events`, and `bare_fiber`, with no need for structural changes.

- [ ] **Step 3: Add only the minimal backend field if the template needs a refresh timestamp**

If needed, extend the JSON payload with an additive field like this:

```python
return JsonResponse({
    "timestamp": now.isoformat(),
    "generated_at": timezone.localtime().strftime("%Y-%m-%d %H:%M"),
    "period": {
        "start": st_dt.strftime("%Y.%m.%d"),
        "end": ed_dt.strftime("%Y.%m.%d"),
    },
    # existing fields unchanged
}, json_dumps_params={"ensure_ascii": False})
```

- [ ] **Step 4: Run a Python syntax smoke check**

Run: `python -m py_compile netbox_otnfaults\weekly_report_views.py`

Expected: Command exits with no output.

- [ ] **Step 5: Commit the backend contract update if a change was made**

```bash
git add netbox_otnfaults/weekly_report_views.py
git commit -m "feat: add weekly report dashboard metadata"
```

If no backend change was needed, skip this commit and continue.

### Task 2: Rebuild the weekly report template as a Tabler-style dashboard

**Files:**
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/weekly_report_dashboard.html`

- [ ] **Step 1: Replace the current big-screen shell with a dashboard page structure**

Use this template structure as the target:

```html
{% load static %}
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每周通报</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
    <link href="{% static 'netbox_otnfaults/css/weekly_report_dashboard.css' %}" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
</head>
<body class="weekly-report-page">
    <div class="page">
        <div class="page-wrapper">
            <div class="container-xl">
                <div class="page-header">
                    <div>
                        <div class="page-pretitle">OTN / Weekly Report</div>
                        <h1 class="page-title">每周通报驾驶舱</h1>
                        <div class="page-meta">
                            <span class="meta-chip" id="period-display">--</span>
                            <span class="meta-chip" id="generated-at-display">自动汇总</span>
                        </div>
                    </div>
                </div>
                <!-- KPI grid -->
                <!-- analysis cards -->
                <!-- bare fiber table card -->
            </div>
        </div>
    </div>
    <script>
        window.WEEKLY_REPORT_API = "{% url 'plugins:netbox_otnfaults:weekly_report_data' %}";
    </script>
    <script src="{% static 'netbox_otnfaults/js/weekly_report_dashboard.js' %}"></script>
</body>
</html>
```

- [ ] **Step 2: Add semantic placeholders for every data block the JS will fill**

Include these IDs in the template:

```html
<span id="kpi-total-cnt">--</span>
<span id="kpi-total-diff">--</span>
<span id="kpi-total-dur">--</span>
<span id="kpi-total-dur-diff">--</span>
<span id="kpi-self-built">--</span>
<span id="kpi-leased">--</span>
<div id="reasonsChart"></div>
<div id="provinces-container"></div>
<div id="major-events-container"></div>
<div id="no-const-dur-info"></div>
<tbody id="bare-fiber-tbody"></tbody>
```

- [ ] **Step 3: Structure the dashboard into clear cards and responsive sections**

Use a layout shaped like this:

```html
<section class="stats-grid">
    <article class="report-card report-card-hero">...</article>
    <article class="report-card report-card-hero">...</article>
    <article class="report-card">...</article>
    <article class="report-card">...</article>
</section>

<section class="analysis-grid">
    <article class="report-card chart-card">...</article>
    <article class="report-card list-card">...</article>
    <article class="report-card event-card">...</article>
</section>

<section class="table-section">
    <article class="report-card table-card">...</article>
</section>
```

- [ ] **Step 4: Validate the template for missing IDs and obvious markup issues**

Run: `Get-Content netbox_otnfaults\templates\netbox_otnfaults\weekly_report_dashboard.html`

Expected: All rendering targets are present exactly once and the page no longer contains the old big-screen title shell.

- [ ] **Step 5: Commit the template rewrite**

```bash
git add netbox_otnfaults/templates/netbox_otnfaults/weekly_report_dashboard.html
git commit -m "feat: rebuild weekly report dashboard template"
```

### Task 3: Replace the big-screen stylesheet with Tabler-aligned dashboard styling

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/css/weekly_report_dashboard.css`

- [ ] **Step 1: Replace the current root palette and page shell variables**

Start the stylesheet with a clean token block like this:

```css
:root {
    --report-bg: #f4f6f9;
    --report-surface: #ffffff;
    --report-surface-soft: #f8fafc;
    --report-border: #dce3ea;
    --report-text: #182433;
    --report-muted: #667382;
    --report-primary: #206bc4;
    --report-info: #4299e1;
    --report-success: #2fb344;
    --report-warning: #f59f00;
    --report-danger: #d63939;
    --report-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    --report-radius: 18px;
}

body.weekly-report-page {
    margin: 0;
    background: linear-gradient(180deg, #eef3f8 0%, #f8fafc 100%);
    color: var(--report-text);
    font-family: "Inter", "Noto Sans SC", sans-serif;
}
```

- [ ] **Step 2: Define the card, grid, badge, and table system**

Add styles like these:

```css
.container-xl {
    max-width: 1440px;
    margin: 0 auto;
    padding: 32px 24px 48px;
}

.report-card {
    background: var(--report-surface);
    border: 1px solid var(--report-border);
    border-radius: var(--report-radius);
    box-shadow: var(--report-shadow);
    padding: 24px;
}

.stats-grid,
.analysis-grid {
    display: grid;
    gap: 24px;
}

.stats-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}

.analysis-grid {
    grid-template-columns: 1.35fr 0.9fr 1fr;
}
```

- [ ] **Step 3: Add mobile and narrower desktop breakpoints**

Include responsive rules like this:

```css
@media (max-width: 1200px) {
    .stats-grid,
    .analysis-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 768px) {
    .container-xl {
        padding: 20px 16px 32px;
    }

    .stats-grid,
    .analysis-grid {
        grid-template-columns: 1fr;
    }

    .table-responsive {
        overflow-x: auto;
    }
}
```

- [ ] **Step 4: Check CSS syntax and remove obsolete selectors**

Run: `Get-Content netbox_otnfaults\static\netbox_otnfaults\css\weekly_report_dashboard.css`

Expected: Old selectors such as `.light-saas-theme`, `.header-section`, `.kpi-section`, and `.middle-section` are removed or no longer drive the layout.

- [ ] **Step 5: Commit the stylesheet rewrite**

```bash
git add netbox_otnfaults/static/netbox_otnfaults/css/weekly_report_dashboard.css
git commit -m "feat: restyle weekly report dashboard with tabler layout"
```

### Task 4: Refactor the client-side renderer for the new DOM and UX states

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/weekly_report_dashboard.js`

- [ ] **Step 1: Replace the current bootstrap logic with a small async loader**

Use this structure:

```javascript
document.addEventListener("DOMContentLoaded", () => {
    void fetchReportData();
});

async function fetchReportData() {
    try {
        const response = await fetch(window.WEEKLY_REPORT_API, {
            headers: { Accept: "application/json" },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        renderHeader(data);
        renderKPIs(data);
        renderChart(data.reasons_analysis || []);
        renderProvinces(data.top_provinces || []);
        renderMajorEvents(data.major_events || [], data.summary?.no_const_duration ?? 0);
        renderBareFiberTable(data.bare_fiber || []);
    } catch (error) {
        renderPageError(error);
        console.error("Weekly report fetch error:", error);
    }
}
```

- [ ] **Step 2: Split rendering into focused functions that match the new template**

Use helpers shaped like this:

```javascript
function renderHeader(data) {
    document.getElementById("period-display").textContent =
        `${data.period.start} - ${data.period.end}`;

    const generatedAt = data.generated_at || "自动汇总";
    const target = document.getElementById("generated-at-display");
    if (target) {
        target.textContent = generatedAt;
    }
}

function renderTrendText(diff, suffix = "") {
    if (diff > 0) return `较上周 +${diff}${suffix}`;
    if (diff < 0) return `较上周 ${diff}${suffix}`;
    return `较上周持平`;
}
```

- [ ] **Step 3: Rewrite province, event, and table rendering to produce cleaner dashboard markup**

Use output patterns like these:

```javascript
container.insertAdjacentHTML(
    "beforeend",
    `
    <div class="province-item">
        <div class="province-item__title">${p.province}</div>
        <div class="province-item__meta">故障 ${p.count} 次 / ${p.duration} 小时</div>
        <div class="province-item__reason">${p.main_reason}</div>
        <div class="province-item__paths">${p.paths || "无路径信息"}</div>
    </div>
    `
);
```

```javascript
tbody.insertAdjacentHTML(
    "beforeend",
    `
    <tr>
        <td>${s.name}</td>
        <td><span class="status-badge status-badge--danger">中断</span></td>
        <td>${s.break_cnt}</td>
        <td>${s.block_cnt}</td>
        <td>${s.duration}h</td>
        <td>${s.segments || "-"}</td>
    </tr>
    `
);
```

- [ ] **Step 4: Add empty-state and error-state rendering**

Include helpers such as:

```javascript
function renderEmptyState(container, message) {
    container.innerHTML = `<div class="empty-state">${message}</div>`;
}

function renderPageError(error) {
    const target = document.getElementById("major-events-container");
    if (target) {
        target.innerHTML = `<div class="empty-state empty-state--error">数据加载失败，请稍后重试。</div>`;
    }
}
```

- [ ] **Step 5: Run a JavaScript syntax smoke check**

Run: `node --check netbox_otnfaults\static\netbox_otnfaults\js\weekly_report_dashboard.js`

Expected: Command exits with no syntax error. If `node` is unavailable, document that limitation and perform a manual code review of all template string boundaries.

- [ ] **Step 6: Commit the JS refactor**

```bash
git add netbox_otnfaults/static/netbox_otnfaults/js/weekly_report_dashboard.js
git commit -m "feat: refactor weekly report dashboard renderer"
```

### Task 5: End-to-end verification and polish

**Files:**
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/weekly_report_dashboard.html`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/css/weekly_report_dashboard.css`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/weekly_report_dashboard.js`
- Modify: `netbox_otnfaults/weekly_report_views.py`

- [ ] **Step 1: Run Python syntax validation on the touched backend file**

Run: `python -m py_compile netbox_otnfaults\weekly_report_views.py`

Expected: No output.

- [ ] **Step 2: Re-run JavaScript syntax validation**

Run: `node --check netbox_otnfaults\static\netbox_otnfaults\js\weekly_report_dashboard.js`

Expected: No output.

- [ ] **Step 3: Do a template/manual review against the acceptance criteria**

Open and verify these files:

```text
netbox_otnfaults/templates/netbox_otnfaults/weekly_report_dashboard.html
netbox_otnfaults/static/netbox_otnfaults/css/weekly_report_dashboard.css
netbox_otnfaults/static/netbox_otnfaults/js/weekly_report_dashboard.js
```

Checklist:

- The page header is dashboard-style, not a big-screen hero banner.
- KPI cards read clearly in a normal desktop window.
- The chart, province list, event list, and bare-fiber table each live in their own card.
- Empty and error states are present for dynamic sections.
- Chinese strings shown to the user are normalized to readable UTF-8 text.

- [ ] **Step 4: If a browser test environment is available, load the page and verify data rendering**

Run the project-specific page manually and confirm:

- KPI values render
- ECharts mounts successfully
- Province cards populate
- Major event items populate
- Bare-fiber rows render and horizontal overflow remains usable on narrow screens

- [ ] **Step 5: Create the final implementation commit**

```bash
git add netbox_otnfaults/weekly_report_views.py netbox_otnfaults/templates/netbox_otnfaults/weekly_report_dashboard.html netbox_otnfaults/static/netbox_otnfaults/css/weekly_report_dashboard.css netbox_otnfaults/static/netbox_otnfaults/js/weekly_report_dashboard.js
git commit -m "feat: redesign weekly report dashboard with tabler"
```

# Branch Company Performance Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add six branch-company performance cards to the fault statistics branch-company tab, with responsibility and overall scores plus deduction details.

**Architecture:** Extend the existing branch-company statistics payload with `performance_cards`, using pure helpers in `statistics_views.py` so score rules are testable. Render the cards in the existing branch-company tab before the current summary/chart sections, reusing the page's compact Bootstrap card visual language and existing detail-filter state.

**Tech Stack:** Django 5 / NetBox plugin view code, Jinja2 template, vanilla JavaScript, Bootstrap 5, source-level unittest checks, `node --check`, `python -m py_compile`.

---

### Task 1: Lock Backend Payload Contract

**Files:**
- Modify: `tests/test_statistics_branch_company.py`
- Modify: `netbox_otnfaults/statistics_views.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting `_classify_branch_fault_responsibility`, `_calculate_branch_performance_score`, `_build_branch_company_performance_cards`, `performance_cards`, `responsibility_score`, `overall_score`, `deductions`, `responsibility_metrics`, `overall_metrics`, and six province card generation are present.

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_statistics_branch_company`

Expected: fails because the new helpers and `performance_cards` field do not exist.

- [ ] **Step 3: Implement backend helpers**

Add typed helper functions after `_count_repeat_fiber_faults()` and call `_build_branch_company_performance_cards()` inside `_build_branch_company_statistics()`.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_statistics_branch_company`

Expected: passes.

### Task 2: Add Frontend Card Container And Renderer

**Files:**
- Modify: `tests/test_statistics_branch_company.py`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/css/statistics_dashboard.css`

- [ ] **Step 1: Write failing tests**

Add source tests for `branch-company-performance-cards`, `renderBranchCompanyPerformanceCards`, card click filtering, score/deduction markup, and CSS classes.

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_statistics_branch_company`

Expected: fails because the template, JS, and CSS entries do not exist.

- [ ] **Step 3: Implement frontend**

Add the template container before existing branch-company overview sections, render the cards from `branchData.performance_cards`, and add compact grid/card CSS.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_statistics_branch_company`

Expected: passes.

### Task 3: Verify Syntax And Focused Regression

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: Run syntax checks**

Run:
- `node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
- `python -m py_compile netbox_otnfaults/statistics_views.py`

Expected: both commands pass.

- [ ] **Step 2: Update project plan**

Mark the new `PLAN.md` checklist items complete after verification.

# Fault Statistics Metric Help Tab Sync Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the fault statistics metric-help modal open on the help tab matching the active dashboard tab.

**Architecture:** Keep the existing main-to-help tab ID map. Bind synchronization to the metric-help button click and activate the mapped help tab through its existing declarative Bootstrap tab click behavior, avoiding a direct global Bootstrap Tab API dependency.

**Tech Stack:** JavaScript, Bootstrap 5 data attributes, Python `unittest` source regression tests

---

### Task 1: Add an executable-path regression assertion

**Files:**
- Modify: `tests/test_statistics_dashboard_assets.py`

- [x] Replace the existing modal-event/API string assertions with assertions requiring a `statisticsMetricHelpButton` click listener, the active main-tab lookup, and `helpTab.click()`.
- [x] Add a negative assertion preventing `bootstrap.Tab.getOrCreateInstance(helpTab).show()` from returning.
- [x] Run `python -m unittest tests.test_statistics_dashboard_assets.StatisticsDashboardAssetsTestCase.test_metric_help_defaults_to_active_dashboard_tab -v` and confirm it fails because the click-based behavior is absent.

### Task 2: Implement the minimal synchronization fix

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`

- [x] Query `statistics-metric-help-btn` and bind its click event.
- [x] Reuse `statisticsMetricHelpTabMap`, resolve the currently active main Tab, and invoke `helpTab.click()` for the mapped help Tab.
- [x] Remove the obsolete modal `show.bs.modal` listener and direct Bootstrap Tab API call.
- [x] Increase the statistics JavaScript cache version in the template.
- [x] Re-run the focused test and confirm it passes.

### Task 3: Verify the change

**Files:**
- Verify: `tests/test_statistics_dashboard_assets.py`
- Verify: `tests/test_statistics_cable_break_overview.py`
- Verify: `tests/test_statistics_impact_level.py`

- [x] Run `node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js` and confirm exit code 0.
- [x] Run the focused statistics asset tests and related cache-version tests.
- [x] Inspect `git diff --check` and `git diff` to confirm only the planned behavior, tests, cache version, and planning documents changed.

### Task 4: Remove the active help Tab bottom line

**Files:**
- Modify: `tests/test_statistics_dashboard_assets.py`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/css/statistics_dashboard.css`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`
- Modify: `tests/test_statistics_cable_break_overview.py`
- Modify: `tests/test_statistics_impact_level_hover.py`

- [x] Add a regression assertion requiring `.statistics-metric-help-tabs .nav-link.active` to set `border-bottom-color: var(--statistics-surface, #ffffff) !important;`.
- [x] Run the focused test and confirm it fails because the modal-scoped active Tab override is absent.
- [x] Add only the modal-scoped active Tab bottom-border override.
- [x] Increase the statistics CSS cache version from `v35` to `v36` and align existing cache-version assertions.
- [x] Re-run the statistics asset, cable-break overview, and impact-hover tests; run `git diff --check`.

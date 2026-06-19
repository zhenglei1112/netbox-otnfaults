# Restore Statistics Logic and Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Restore every statistics filter, drill-down, sorting, and display behavior changed by `d093d50`, without introducing lazy loading or pagination.

**Architecture:** Keep the split summary/detail APIs and full-result frontend caches. Centralize request-value normalization and queryset filtering in `statistics_views.py`, keep legend exclusions local in JavaScript, and lock the model/database state with an explicit migration.

**Tech Stack:** Django 5, NetBox 4 plugin APIs, vanilla JavaScript, Python unittest.

---

### Task 1: Lock the missing filter contract

**Files:**
- Modify: `tests/test_statistics_cable_break_overview.py`
- Modify: `tests/test_statistics_branch_company.py`

- [x] Add source-level regression assertions requiring category display mapping, source group, occurrence period, cause group, duration min/max, histogram bucket, and repeat filters.
- [x] Assert frontend no longer sends `exclude_resource_type`, `exclude_province`, or `exclude_reason`.
- [x] Run `python -m unittest tests.test_statistics_cable_break_overview tests.test_statistics_branch_company -q`.
- [x] Confirm the new assertions fail because the backend branches are absent and invalid frontend parameters remain.

### Task 2: Restore queryset filters and display-value mappings

**Files:**
- Modify: `netbox_otnfaults/statistics_views.py`
- Test: `tests/test_statistics_cable_break_overview.py`
- Test: `tests/test_statistics_branch_company.py`

- [x] Add typed helpers mapping category display names, source groups, occurrence periods, cause groups, and numeric duration parameters.
- [x] Apply all non-repeat filters before evaluating the queryset.
- [x] Build repeat IDs against the filtered current result and preceding 60-day candidates; apply `is_repeat=true` without losing matched preceding rows.
- [x] Run the two statistics test modules and confirm all filter-contract assertions pass.

### Task 3: Restore frontend local exclusion behavior

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
- Test: `tests/test_statistics_cable_break_overview.py`

- [x] Remove unsupported `exclude_*` query parameters from `loadFaultDetails()`.
- [x] Keep resource, province, and reason legend exclusions in `renderDetailsTable()` over `currentAllDetails`.
- [x] Run the statistics tests and `node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`.

### Task 4: Correct historical cache isolation

**Files:**
- Modify: `tests/test_statistics_cable_break_overview.py`
- Modify: `netbox_otnfaults/statistics_views.py`

- [x] Add a failing assertion that the fault-summary cache key contains `calendar_year` and `calendar_month`.
- [x] Move calendar parameter parsing before cache lookup and append both values to the cache key.
- [x] Run the statistics tests and confirm the cache assertion passes.

### Task 5: Add the missing statistics index migration

**Files:**
- Create: `netbox_otnfaults/migrations/0087_statistics_query_indexes.py`
- Modify: `tests/test_statistics_cable_break_overview.py`

- [x] Add a failing test requiring migration operations for `otnfault_cat_occ_idx`, `otnfault_susp_stat_occ_idx`, and `otnimpact_type_biz_time_idx`.
- [x] Create migration `0087_statistics_query_indexes.py` depending on `0086_circuitservice_is_important_and_more`.
- [x] Use three `migrations.AddIndex` operations matching `models.py`.
- [x] Run the statistics tests and compile the migration source.

### Task 6: Verify the restored behavior

**Files:**
- Modify: `PLAN.md`

- [x] Mark the restoration checklist complete.
- [x] Run `python -m unittest tests.test_statistics_branch_company tests.test_statistics_cable_break_overview -q`.
- [x] Run the service sorting assertions in `tests/test_statistics_service_sorting.py`.
- [x] Run JavaScript syntax checking and in-memory Python compilation for views and migration.
- [x] Run `git diff --check` and review the final diff against the design.


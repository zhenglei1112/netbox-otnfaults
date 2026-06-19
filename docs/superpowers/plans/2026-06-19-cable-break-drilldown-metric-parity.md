# Cable Break Drill-down Metric Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make every cable-break dashboard drill-down use the same scope and aggregation semantics as its displayed metric.

**Architecture:** Keep the existing summary and detail endpoints, but make the detail endpoint return an exact server-side summary for the filtered current-period faults. The browser records the clicked metric type/value and renders a metric-specific explanation from that summary.

**Tech Stack:** Django 5, NetBox 4 plugin APIs, vanilla JavaScript, ECharts, unittest source regression tests.

---

### Task 1: Shared scope

- [x] Add failing assertions that resource, reason and province chart clicks pass `cable_break`.
- [x] Add a failing assertion that province statistics use the currently filtered cable-break list.
- [x] Apply the shared scope and make the focused test pass.

### Task 2: Repeat KPI parity

- [x] Add a failing assertion that cable-break repeat filtering uses `kpi_repeat_ids`.
- [x] Preserve both repeat ID sets and select the KPI set for `detail_scope=cable_break`.
- [x] Make the focused test pass.

### Task 3: Exact server summary

- [x] Add failing assertions for count, duration, average, long count, repeat count and scope total.
- [x] Compute the summary from current-period model objects before row-duration rounding.
- [x] Return `summary` beside `results` and make the focused test pass.

### Task 4: Metric-specific explanation

- [x] Add failing assertions for metric metadata and count/duration/average/rate/percentile explanations.
- [x] Record metadata for static cards, dynamic cards and chart clicks.
- [x] Render the server-backed parity explanation and make the focused test pass.

### Task 5: Verification

- [x] Run the focused and complete statistics tests.
- [x] Run JavaScript syntax and Python compile checks.
- [x] Mark `PLAN.md` complete only after verification succeeds.

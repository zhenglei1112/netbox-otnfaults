# Dashboard Cutover Coordinate Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make dashboard cutover markers use the same resolved coordinates and station identifiers as fault markers.

**Architecture:** Keep coordinate policy in `services/fault_coordinates.py`. The dashboard API resolves each cutover before serialization and sends the resolved point plus A/Z station IDs to the existing frontend renderer and focus logic.

**Tech Stack:** Python 3, Django 5, unittest source-regression tests, MapLibre consumer payload

---

### Task 1: Lock the dashboard payload contract

**Files:**
- Modify: `tests/test_fault_coordinate_resolution.py`

- [x] Add assertions that `dashboard_views.py` imports and calls `resolve_cutover_coordinates`, preserves unresolved cutovers with null coordinates, and serializes `lat`, `lng`, `site_a_id`, and `site_z_ids`.

```python
self.assertIn("resolve_cutover_coordinates", dashboard_source)
self.assertIn("resolved = resolve_cutover_coordinates(cutover)", dashboard_source)
self.assertIn("'lat': resolved.lat if resolved is not None else None", dashboard_source)
self.assertIn("'lng': resolved.lng if resolved is not None else None", dashboard_source)
self.assertIn("'site_a_id': cutover.interruption_location_a_id", dashboard_source)
self.assertIn("'site_z_ids': [site.pk for site in z_site_objects]", dashboard_source)
```

- [x] Run `python -m unittest tests.test_fault_coordinate_resolution` and confirm it fails because the dashboard integration is missing.

### Task 2: Resolve dashboard cutover coordinates

**Files:**
- Modify: `netbox_otnfaults/dashboard_views.py:23`
- Modify: `netbox_otnfaults/dashboard_views.py:315-335`

- [x] Import `resolve_cutover_coordinates` beside `resolve_fault_coordinates`.
- [x] Materialize the prefetched Z sites and resolve each cutover without removing unresolved items from the dashboard list.

```python
z_site_objects = list(cutover.interruption_location.all())
resolved = resolve_cutover_coordinates(cutover)
z_sites = [site.name for site in z_site_objects]
```

- [x] Add the resolved point and station IDs to the serialized dictionary.

```python
'lat': resolved.lat if resolved is not None else None,
'lng': resolved.lng if resolved is not None else None,
'site_a_id': cutover.interruption_location_a_id,
'site_z_ids': [site.pk for site in z_site_objects],
```

- [x] Run `python -m unittest tests.test_fault_coordinate_resolution tests.test_dashboard_situation_board` and confirm all tests pass.

### Task 3: Verify and document completion

**Files:**
- Modify: `PLAN.md`

- [x] Run `python -m unittest tests.test_fault_coordinate_resolution tests.test_dashboard_situation_board tests.test_dashboard_fault_focus_site_labels`.
- [x] Run `python -m py_compile netbox_otnfaults/dashboard_views.py tests/test_fault_coordinate_resolution.py`.
- [x] Run `git diff --check` and inspect the scoped diff.

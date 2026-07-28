# Cutover List Column Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose every business field defined directly on `CutoverTask` in the cutover list's column settings without changing the default visible columns.

**Architecture:** Keep `CutoverTaskTable` as the single list-column definition. Add explicit columns where relations, choices, dates, or multi-value data need specialized behavior; list every model business field in `Meta.fields` and preserve the existing `default_columns`.

**Tech Stack:** Python 3, Django 5, NetBox 4, django-tables2, pytest.

---

### Task 1: Lock the column contract with a regression test

**Files:**
- Create: `tests/test_cutover_task_table_columns.py`

- [ ] **Step 1: Write the failing source-level test**

Create an AST-based test that reads `models.py` and `tables.py`, collects fields declared directly on `CutoverTask`, and asserts:

```python
assert model_business_fields <= table_fields
assert table_fields[-1] == "actions"
```

- [ ] **Step 2: Run the test to verify RED**

Run `python -m pytest tests/test_cutover_task_table_columns.py -q`.

Expected: failure listing the 31 fields currently absent from `CutoverTaskTable.Meta.fields`.

### Task 2: Add all missing configurable columns

**Files:**
- Modify: `netbox_otnfaults/tables.py:982-1048`
- Test: `tests/test_cutover_task_table_columns.py`

- [ ] **Step 1: Declare specialized columns**

Add linked relationship columns, a `ManyToManyColumn` for the Z end, `ChoiceFieldColumn` instances for choice fields, `DateTimeColumn` instances for time fields, and ordinary columns for text, JSON, numeric, and array data.

- [ ] **Step 2: Complete `Meta.fields`**

Order fields by the edit form's business sections. Keep `pk` first, `tags` immediately before `actions`, and `actions` last. Do not add entries to `default_columns`.

- [ ] **Step 3: Add export display values**

For each newly exposed choice field, return its display label through `_display_or_empty`. Format arrays and JSON lists into readable text for list and CSV output.

- [ ] **Step 4: Run the regression test to verify GREEN**

Run `python -m pytest tests/test_cutover_task_table_columns.py -q`.

Expected: all tests pass.

### Task 3: Verify compatibility

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: Run related cutover tests**

Run `python -m pytest tests/test_cutover_management_scaffold.py tests/test_cutover_task_table_columns.py -q`.

Expected: all tests pass.

- [ ] **Step 2: Run compile checks**

Run `python -m py_compile netbox_otnfaults/tables.py tests/test_cutover_task_table_columns.py`.

Expected: exit code 0.

- [ ] **Step 3: Check the final diff**

Run `git diff --check` and `git status --short`.

Expected: no whitespace errors and only the planned files changed.

- [ ] **Step 4: Mark `PLAN.md` complete**

Change all four checklist items in the new `2026-07-28` section from `[ ]` to `[x]` after verification succeeds.

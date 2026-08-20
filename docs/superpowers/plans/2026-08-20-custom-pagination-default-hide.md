# Custom Pagination Default-Hide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or execute inline with superpowers:test-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every page that supplies a custom paginator hides the django-tables2/NetBox default paginator.

**Architecture:** Keep pagination data and links unchanged. Scope CSS to each rendered table container, while custom paginator footers remain outside those containers; list pages additionally exclude `.custom-pagination` when hiding NetBox-generated footers.

**Tech Stack:** Django templates, django-tables2, NetBox 4.x, Python `unittest` source assertions.

---

### Task 1: Add cross-template regression coverage

**Files:**
- Create: `tests/test_custom_pagination_templates.py`
- Modify: `tests/test_cutover_detail_pagination.py`
- Modify: `tests/test_heavy_duty.py`

- [x] **Step 1: Write failing tests**

Create a table-driven test covering the six detail templates and three list templates. Assert that every relevant table container has both `ul.pagination` and `.pagination` selectors, custom pagination markup remains present, and `cutovertask.html` uses `{% block head %}` with `{{ block.super }}` instead of `extra_styles`.

- [x] **Step 2: Verify RED**

Run:

```powershell
python -m unittest tests.test_custom_pagination_templates tests.test_cutover_detail_pagination tests.test_otnfault_detail_pagination tests.test_heavy_duty
```

Expected: FAIL because templates other than `otnfault.html` lack the complete selector pairs and `cutovertask.html` still uses `extra_styles`.

### Task 2: Correct detail-page pagination CSS

**Files:**
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/barefiberservice.html`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/circuitservice.html`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/heavyduty.html`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/otnpathgroup.html`
- Verify: `netbox_otnfaults/templates/netbox_otnfaults/otnfault.html`

- [x] **Step 1: Fix the cutover style block**

Replace `extra_styles` with:

```django
{% block head %}
{{ block.super }}
```

- [x] **Step 2: Add tag-specific and tag-independent selectors**

For each detail table scope, use:

```css
.scope ul.pagination,
.scope .pagination {
  display: none !important;
}
```

For pages containing multiple tables, repeat both selectors for every table-specific container.

### Task 3: Correct object-list pagination CSS

**Files:**
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/barefiberservice_list.html`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/circuitservice_list.html`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/heavyduty_list.html`

- [x] **Step 1: Expand the default paginator selectors**

Use this list-page rule, retaining the heavy-duty footer exclusion where already present:

```css
.table-container ul.pagination,
.table-container .pagination,
.table-responsive ul.pagination,
.table-responsive .pagination {
  display: none !important;
}
```

- [x] **Step 2: Preserve the custom paginator boundary**

Keep the custom footer class and JavaScript behavior unchanged:

```html
<div class="card-footer ... custom-pagination">
```

### Task 4: Verify GREEN and regression safety

**Files:**
- Modify: `PLAN.md`

- [x] **Step 1: Run focused pagination tests**

```powershell
python -m unittest tests.test_custom_pagination_templates tests.test_cutover_detail_pagination tests.test_otnfault_detail_pagination tests.test_heavy_duty
```

Expected: all focused tests pass.

- [x] **Step 2: Run source and diff checks**

```powershell
python -m py_compile tests/test_custom_pagination_templates.py tests/test_cutover_detail_pagination.py tests/test_otnfault_detail_pagination.py tests/test_heavy_duty.py
git diff --check
```

Expected: exit code 0 with no syntax or whitespace errors.

- [x] **Step 3: Record completion**

Mark the matching `PLAN.md` checklist complete only after the verification commands succeed. Do not stage, commit, push, or create a PR.

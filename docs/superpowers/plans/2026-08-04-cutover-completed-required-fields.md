# Cutover Completed Required Fields Implementation Plan

> **For agentic workers:** Execute this plan inline with `superpowers:test-driven-development`; project instructions prohibit creating a worktree, branch, commit, push, or pull request unless the user explicitly requests one.

**Goal:** Require all six completion fields when a cutover task is saved as completed, show every missing-field error inline, and scroll/focus the first missing field.

**Architecture:** Put the field list and missing-field selection in a small pure validation service so behavior can be tested without a NetBox runtime. `CutoverTaskForm.clean()` translates returned field names into Django field errors. The edit template emits ordered hidden markers beside errored completion fields and uses one initializer to scroll and focus the first marker target.

**Tech Stack:** Python 3, Django/NetBox model forms, Django templates, browser JavaScript, unittest/pytest-compatible tests.

---

### Task 1: Pure completion validation

**Files:**
- Create: `netbox_otnfaults/services/cutover_completion.py`
- Create: `tests/test_cutover_completed_required_fields.py`

- [ ] **Step 1: Write failing behavior tests**

```python
from netbox_otnfaults.services.cutover_completion import (
    CUTOVER_COMPLETION_REQUIRED_FIELDS,
    find_missing_cutover_completion_fields,
)


def test_completed_cutover_returns_all_missing_fields() -> None:
    assert find_missing_cutover_completion_fields(
        {'status': 'completed'}, completed_status='completed'
    ) == (
        'started_at', 'completed_at', 'closed_at', 'is_timeout',
        'cutover_result', 'rectification_status',
    )


def test_completed_cutover_returns_only_missing_fields() -> None:
    values = {
        'status': 'completed', 'started_at': object(), 'completed_at': object(),
        'closed_at': object(), 'is_timeout': 'no', 'cutover_result': '',
        'rectification_status': '',
    }
    assert find_missing_cutover_completion_fields(values, completed_status='completed') == (
        'cutover_result', 'rectification_status',
    )


def test_completed_cutover_with_all_fields_returns_no_missing_fields() -> None:
    values = {
        'status': 'completed',
        **{field_name: object() for field_name in CUTOVER_COMPLETION_REQUIRED_FIELDS},
    }
    assert find_missing_cutover_completion_fields(values, completed_status='completed') == ()


def test_non_completed_cutover_does_not_require_completion_fields() -> None:
    assert find_missing_cutover_completion_fields(
        {'status': 'pending_implementation'}, completed_status='completed'
    ) == ()
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cutover_completed_required_fields.py -v`

Expected: collection fails with `ModuleNotFoundError` for `services.cutover_completion`.

- [ ] **Step 3: Implement the pure validator**

```python
from __future__ import annotations

from collections.abc import Mapping


CUTOVER_COMPLETION_REQUIRED_FIELDS: tuple[str, ...] = (
    'started_at', 'completed_at', 'closed_at', 'is_timeout',
    'cutover_result', 'rectification_status',
)


def find_missing_cutover_completion_fields(
    values: Mapping[str, object], *, completed_status: str,
) -> tuple[str, ...]:
    if values.get('status') != completed_status:
        return ()
    return tuple(
        field_name
        for field_name in CUTOVER_COMPLETION_REQUIRED_FIELDS
        if values.get(field_name) in (None, '')
    )
```

- [ ] **Step 4: Run tests and verify GREEN**

Run the Task 1 test command. Expected: four behavior tests pass.

### Task 2: Bind all missing fields to form errors

**Files:**
- Modify: `netbox_otnfaults/forms.py`
- Modify: `tests/test_cutover_completed_required_fields.py`

- [ ] **Step 1: Add a failing source integration test**

```python
def test_cutover_form_binds_every_missing_completion_field_error() -> None:
    forms_source = (REPO_ROOT / 'netbox_otnfaults' / 'forms.py').read_text(encoding='utf-8')
    form_source = forms_source.split('class CutoverTaskForm(NetBoxModelForm):', 1)[1].split(
        'class CutoverTaskFilterForm', 1
    )[0]
    assert 'find_missing_cutover_completion_fields(' in form_source
    assert 'completed_status=CutoverStatusChoices.COMPLETED' in form_source
    assert "self.add_error(field_name, '状态为已完成时，此字段必填。')" in form_source
```

- [ ] **Step 2: Run the integration test and verify RED**

Run the named test with pytest. Expected: it fails because the form does not call the validator.

- [ ] **Step 3: Add the form integration**

Import `find_missing_cutover_completion_fields`, then add:

```python
    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            cleaned_data = getattr(self, 'cleaned_data', None) or {}
        missing_fields = find_missing_cutover_completion_fields(
            cleaned_data,
            completed_status=CutoverStatusChoices.COMPLETED,
        )
        for field_name in missing_fields:
            self.add_error(field_name, '状态为已完成时，此字段必填。')
        return cleaned_data
```

- [ ] **Step 4: Run feature tests and verify GREEN**

Run the feature test file. Expected: all current tests pass.

### Task 3: Render field markers and focus the first missing field

**Files:**
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html`
- Modify: `tests/test_cutover_completed_required_fields.py`

- [ ] **Step 1: Add failing template tests**

```python
def test_cutover_edit_marks_each_completion_field_error_inline() -> None:
    template = CUTOVER_EDIT_TEMPLATE.read_text(encoding='utf-8')
    for field_name in CUTOVER_COMPLETION_REQUIRED_FIELDS:
        assert f'form.{field_name}.errors' in template
        assert f'data-cutover-completion-error-for="id_{field_name}"' in template
    assert 'inc/form_errors.html' not in template


def test_cutover_edit_scrolls_and_focuses_first_completion_error() -> None:
    template = CUTOVER_EDIT_TEMPLATE.read_text(encoding='utf-8')
    assert 'function focusFirstCutoverCompletionError()' in template
    assert "document.querySelector('[data-cutover-completion-error-for]')" in template
    assert 'marker.dataset.cutoverCompletionErrorFor' in template
    assert "scrollIntoView({ behavior: 'smooth', block: 'center' })" in template
    assert 'field.tomselect.focus();' in template
    assert 'field.focus({ preventScroll: true });' in template
    assert 'setTimeout(focusFirstCutoverCompletionError, 200);' in template
```

- [ ] **Step 2: Run template tests and verify RED**

Run the feature test file. Expected: template tests fail because markers and focus logic are absent.

- [ ] **Step 3: Add ordered inline error markers**

Immediately before each of the six existing `{% render_field %}` calls, add its marker:

```django
{% if form.started_at.errors %}<span hidden data-cutover-completion-error-for="id_started_at"></span>{% endif %}
{% render_field form.started_at %}
```

Repeat in page order for `completed_at`, `closed_at`, `is_timeout`, `cutover_result`, and `rectification_status`. Do not include a top-level error summary.

- [ ] **Step 4: Add the scroll/focus initializer**

```javascript
function focusFirstCutoverCompletionError() {
    const marker = document.querySelector('[data-cutover-completion-error-for]');
    if (!marker) return;
    const field = document.getElementById(marker.dataset.cutoverCompletionErrorFor);
    if (!field) return;
    const fieldRow = field.closest('.row') || field;
    fieldRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
    window.setTimeout(function() {
        if (field.tomselect) {
            field.tomselect.focus();
        } else {
            field.focus({ preventScroll: true });
        }
    }, 300);
}
```

Call `setTimeout(focusFirstCutoverCompletionError, 200);` in both existing page-ready branches.

- [ ] **Step 5: Run feature tests and verify GREEN**

Run the feature test file. Expected: all behavior, integration, and template tests pass.

### Task 4: Regression and syntax verification

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: Run related cutover tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cutover_completed_required_fields.py tests/test_cutover_edit_template.py tests/test_cutover_status_auto_set.py tests/test_cutover_management_scaffold.py -v`

Expected: all selected tests pass.

- [ ] **Step 2: Compile changed Python files**

Run: `.venv\Scripts\python.exe -m py_compile netbox_otnfaults/services/cutover_completion.py netbox_otnfaults/forms.py tests/test_cutover_completed_required_fields.py`

Expected: exit code 0 with no output.

- [ ] **Step 3: Review the final diff**

Run `git diff --check` and inspect the scoped diff. Expected: only the approved behavior, tests, and documentation.

- [ ] **Step 4: Mark `PLAN.md` complete**

Change this feature's four checklist items from `[ ]` to `[x]` only after verification succeeds.


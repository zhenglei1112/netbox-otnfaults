# Cutover Generate Fault Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a prefilled confirmation workflow that generates one `OtnFault` and its `OtnFaultImpact` records from one `CutoverTask`, with a structured source relation and no `rectification_*` mapping.

**Architecture:** Add `OtnFault.source_cutover_task` as the durable relation, keep mapping logic in a focused service module, and expose the workflow through a `CutoverTaskGenerateFaultView` confirmation page. The view handles GET/POST orchestration, while service functions own deterministic field mapping and transactional creation.

**Tech Stack:** Django 5, NetBox 4 plugin views/forms/models, Bootstrap 5 templates, Python source-level tests.

---

## File Structure

- Modify: `PLAN.md` to record the feature plan.
- Modify: `netbox_otnfaults/models.py` to add `OtnFault.source_cutover_task`.
- Create: `netbox_otnfaults/migrations/0075_otnfault_source_cutover_task.py`.
- Create: `netbox_otnfaults/services/cutover_fault_generation.py` for mapping and transactional creation.
- Modify: `netbox_otnfaults/forms.py` to add `CutoverFaultGenerationForm`.
- Modify: `netbox_otnfaults/views.py` to add `CutoverTaskGenerateFaultView`.
- Modify: `netbox_otnfaults/urls.py` to register `cutovertask_generate_fault`.
- Modify: `netbox_otnfaults/api/serializers.py` to expose `source_cutover_task`.
- Modify: `netbox_otnfaults/filtersets.py` and `netbox_otnfaults/forms.py` filter form to support source cutover filtering.
- Create: `netbox_otnfaults/templates/netbox_otnfaults/cutovertask_generate_fault.html`.
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html` to add the entry and generated-fault link.
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/otnfault.html` to show the source cutover.
- Create: `tests/test_cutover_generate_fault_plan.py` for source-level regression tests.

## Task 1: Source-Level Contract Tests

**Files:**
- Create: `tests/test_cutover_generate_fault_plan.py`

- [ ] **Step 1: Write tests that describe the expected code shape**

```python
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_otnfault_has_source_cutover_task_relation() -> None:
    text = read("netbox_otnfaults/models.py")
    otn_fault = text.split("class OtnFault(", 1)[1].split("class ServiceTypeChoices", 1)[0]
    assert "source_cutover_task = models.ForeignKey(" in otn_fault
    assert "to='CutoverTask'" in otn_fault or 'to="CutoverTask"' in otn_fault
    assert "related_name='generated_faults'" in otn_fault


def test_generation_form_excludes_rectification_fields() -> None:
    text = read("netbox_otnfaults/forms.py")
    form = text.split("class CutoverFaultGenerationForm", 1)[1].split("class ", 1)[0]
    assert "fault_occurrence_time" in form
    assert "fault_recovery_time" in form
    assert "rectification_status" not in form
    assert "rectification_measures" not in form
    assert "rectification_description" not in form


def test_generation_service_has_transaction_and_no_rectification_mapping() -> None:
    text = read("netbox_otnfaults/services/cutover_fault_generation.py")
    assert "def build_fault_initial_data(" in text
    assert "def create_fault_from_cutover(" in text
    assert "transaction.atomic()" in text
    assert "source_cutover_task" in text
    assert "rectification_status" not in text
    assert "rectification_measures" not in text


def test_generate_fault_route_precedes_cutover_detail_include() -> None:
    text = read("netbox_otnfaults/urls.py")
    generate_index = text.index("cutovertask_generate_fault")
    detail_index = text.index("cutovers/<int:pk>/', include")
    assert generate_index < detail_index


def test_templates_expose_generation_flow() -> None:
    cutover_detail = read("netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html")
    confirm = read("netbox_otnfaults/templates/netbox_otnfaults/cutovertask_generate_fault.html")
    fault_detail = read("netbox_otnfaults/templates/netbox_otnfaults/otnfault.html")
    assert "cutovertask_generate_fault" in cutover_detail
    assert "确认生成故障" in confirm
    assert "影响业务" in confirm
    assert "source_cutover_task" in fault_detail or "来源割接" in fault_detail
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_cutover_generate_fault_plan`

Expected: FAIL because the new model field, service, form, route, and templates do not exist yet.

## Task 2: Model Relation and Migration

**Files:**
- Modify: `netbox_otnfaults/models.py`
- Create: `netbox_otnfaults/migrations/0075_otnfault_source_cutover_task.py`

- [ ] **Step 1: Add the relation to `OtnFault`**

Add this field inside `class OtnFault`, near the other core relation fields:

```python
    source_cutover_task = models.ForeignKey(
        to='CutoverTask',
        on_delete=models.SET_NULL,
        related_name='generated_faults',
        verbose_name='来源割接',
        blank=True,
        null=True,
    )
```

- [ ] **Step 2: Generate migration**

Run: `python manage.py makemigrations netbox_otnfaults`

Expected: a migration adding only `source_cutover_task` to `OtnFault`.

- [ ] **Step 3: If no NetBox runtime is available, create an equivalent migration manually**

Use this migration body:

```python
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0074_drop_legacy_cutovertask_maintenance_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfault',
            name='source_cutover_task',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='generated_faults',
                to='netbox_otnfaults.cutovertask',
                verbose_name='来源割接',
            ),
        ),
    ]
```

## Task 3: Mapping Service

**Files:**
- Create: `netbox_otnfaults/services/cutover_fault_generation.py`

- [ ] **Step 1: Implement deterministic mapping helpers**

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.db import transaction
from django.utils import timezone

from netbox_otnfaults.models import (
    BusinessImpactChoices,
    CutoverTask,
    CutoverTimeoutStatusChoices,
    FaultCategoryChoices,
    FaultStatusChoices,
    OtnFault,
    OtnFaultImpact,
    ServiceTypeChoices,
    UrgencyChoices,
)


def _fault_occurrence_time(cutover: CutoverTask) -> Any:
    return cutover.planned_cutover_time or cutover.started_at or timezone.now()


def _timeout_value(cutover: CutoverTask) -> bool:
    if cutover.is_timeout == CutoverTimeoutStatusChoices.YES:
        return False
    return True


def build_fault_initial_data(cutover: CutoverTask, user: Any) -> dict[str, Any]:
    occurrence_time = _fault_occurrence_time(cutover)
    details = [
        f"由割接 {cutover.cutover_no} 生成。",
        "",
        "割接原因：",
        cutover.cutover_reason or "",
    ]
    handler_parts = [value for value in (cutover.implementation_unit, cutover.cutover_contact) if value]
    return {
        "source_cutover_task": cutover,
        "duty_officer": user if getattr(user, "is_authenticated", False) else cutover.registrant,
        "interruption_location_a": cutover.interruption_location_a,
        "fault_occurrence_time": occurrence_time,
        "fault_recovery_time": cutover.completed_at,
        "closure_time": cutover.closed_at,
        "fault_category": FaultCategoryChoices.FIBER_BREAK,
        "interruption_reason": "cable_rectification",
        "interruption_reason_detail": "planned_reporting",
        "fault_details": "\n".join(details).strip(),
        "interruption_longitude": cutover.cutover_longitude,
        "interruption_latitude": cutover.cutover_latitude,
        "province": cutover.province,
        "urgency": UrgencyChoices.LOW,
        "line_manager": cutover.line_supervisor,
        "maintenance_mode": cutover.maintenance_mode,
        "handling_unit": cutover.handling_unit,
        "contract": cutover.contract,
        "timeout": _timeout_value(cutover),
        "timeout_reason": cutover.timeout_reason,
        "resource_type": cutover.resource_type,
        "resource_owner": cutover.resource_owner,
        "cable_route": cutover.cable_route,
        "handler": " / ".join(handler_parts),
        "fault_status": FaultStatusChoices.CLOSED if cutover.completed_at else FaultStatusChoices.PROCESSING,
        "comments": cutover.comments,
    }
```

- [ ] **Step 2: Implement transactional creation**

```python
def create_fault_from_cutover(
    *,
    cutover: CutoverTask,
    fault_data: Mapping[str, Any],
    user: Any,
) -> OtnFault:
    with transaction.atomic():
        if cutover.generated_faults.exists():
            raise ValueError("当前割接已经生成过故障。")

        fault = OtnFault(**dict(fault_data))
        fault.source_cutover_task = cutover
        fault.full_clean(exclude=["fault_number"])
        fault.save()
        fault.interruption_location.set(cutover.interruption_location.all())

        for cutover_impact in cutover.impacts.all():
            service_interruption_time = cutover_impact.service_interruption_time or fault.fault_occurrence_time
            service_recovery_time = cutover_impact.service_recovery_time or fault.fault_recovery_time
            impact = OtnFaultImpact.objects.create(
                otn_fault=fault,
                service_type=cutover_impact.service_type,
                bare_fiber_service=cutover_impact.bare_fiber_service,
                circuit_service=cutover_impact.circuit_service,
                service_site_a=cutover_impact.service_site_a,
                business_impact=cutover_impact.business_impact or BusinessImpactChoices.INTERRUPTED,
                service_interruption_time=service_interruption_time,
                service_recovery_time=service_recovery_time,
                comments=cutover_impact.comments,
            )
            if cutover_impact.service_type == ServiceTypeChoices.BARE_FIBER:
                impact.service_site_z.set(cutover_impact.service_site_z.all())

        return fault
```

## Task 4: Confirmation Form

**Files:**
- Modify: `netbox_otnfaults/forms.py`

- [ ] **Step 1: Add `CutoverFaultGenerationForm`**

```python
class CutoverFaultGenerationForm(forms.Form):
    duty_officer = DynamicModelChoiceField(queryset=get_user_model().objects.all(), label='值守人员')
    fault_category = forms.ChoiceField(choices=FaultCategoryChoices, label='故障分类')
    urgency = forms.ChoiceField(choices=UrgencyChoices, label='紧急程度')
    fault_status = forms.ChoiceField(choices=FaultStatusChoices, label='处理状态')
    interruption_reason = forms.ChoiceField(choices=OtnFault.INTERRUPTION_REASON_CHOICES, label='一级原因')
    interruption_reason_detail = forms.ChoiceField(
        choices=OtnFault.INTERRUPTION_REASON_DETAIL_CHOICES,
        required=False,
        label='二级原因',
    )
    cutover_report_status = forms.ChoiceField(
        choices=add_blank_choice(CutoverReportStatusChoices),
        required=False,
        label='割接报备情况',
    )
    cutover_report_time = forms.DateTimeField(required=False, label='报备时间', widget=DateTimePicker())
    fault_occurrence_time = forms.DateTimeField(label='故障起始时间', widget=DateTimePicker())
    fault_recovery_time = forms.DateTimeField(required=False, label='故障恢复时间', widget=DateTimePicker())
    closure_time = forms.DateTimeField(required=False, label='封包完成时间', widget=DateTimePicker())
    comments = CommentField(label='评论', required=False)

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        occurrence = cleaned_data.get('fault_occurrence_time')
        recovery = cleaned_data.get('fault_recovery_time')
        closure = cleaned_data.get('closure_time')
        if occurrence and recovery and recovery < occurrence:
            self.add_error('fault_recovery_time', '故障恢复时间需晚于故障起始时间。')
        if occurrence and closure and closure < occurrence:
            self.add_error('closure_time', '封包完成时间需晚于故障起始时间。')
        return cleaned_data
```

## Task 5: View and URL

**Files:**
- Modify: `netbox_otnfaults/views.py`
- Modify: `netbox_otnfaults/urls.py`

- [ ] **Step 1: Add the view**

```python
class CutoverTaskGenerateFaultView(PermissionRequiredMixin, View):
    permission_required = 'netbox_otnfaults.add_otnfault'
    template_name = 'netbox_otnfaults/cutovertask_generate_fault.html'

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        cutover = get_object_or_404(CutoverTask.objects.prefetch_related('impacts'), pk=pk)
        existing_fault = cutover.generated_faults.order_by('-created').first()
        initial = build_fault_initial_data(cutover, request.user)
        form = CutoverFaultGenerationForm(initial=initial)
        return render(request, self.template_name, {
            'object': cutover,
            'form': form,
            'existing_fault': existing_fault,
            'impacts': cutover.impacts.all(),
        })

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        cutover = get_object_or_404(CutoverTask.objects.prefetch_related('impacts'), pk=pk)
        existing_fault = cutover.generated_faults.order_by('-created').first()
        form = CutoverFaultGenerationForm(request.POST)
        if existing_fault:
            messages.error(request, '当前割接已经生成过故障。')
            return redirect(existing_fault.get_absolute_url())
        if not form.is_valid():
            return render(request, self.template_name, {
                'object': cutover,
                'form': form,
                'existing_fault': existing_fault,
                'impacts': cutover.impacts.all(),
            })
        initial = build_fault_initial_data(cutover, request.user)
        fault_data = {**initial, **form.cleaned_data}
        try:
            fault = create_fault_from_cutover(cutover=cutover, fault_data=fault_data, user=request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect(cutover.get_absolute_url())
        messages.success(request, f'已从割接 {cutover.cutover_no} 生成故障 {fault.fault_number}。')
        return redirect(fault.get_absolute_url())
```

- [ ] **Step 2: Register URL before the detail include**

```python
path('cutovers/<int:pk>/generate-fault/', views.CutoverTaskGenerateFaultView.as_view(), name='cutovertask_generate_fault'),
```

## Task 6: Templates

**Files:**
- Create: `netbox_otnfaults/templates/netbox_otnfaults/cutovertask_generate_fault.html`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/otnfault.html`

- [ ] **Step 1: Create confirmation page**

The page must include:
- 来源割接摘要。
- `CutoverFaultGenerationForm` fields.
- 影响业务 preview table.
- “确认生成故障” submit button.
- “返回割接” link.
- Existing generated fault warning when `existing_fault` is present.

- [ ] **Step 2: Add cutover detail entry**

Add a button linking to `{% url 'plugins:netbox_otnfaults:cutovertask_generate_fault' object.pk %}`.

- [ ] **Step 3: Show source cutover on fault detail**

```django
{% if object.source_cutover_task %}
<tr>
  <th scope="row">来源割接</th>
  <td>{{ object.source_cutover_task|linkify }}</td>
</tr>
{% endif %}
```

## Task 7: Serializer, Filter, and Table Exposure

**Files:**
- Modify: `netbox_otnfaults/api/serializers.py`
- Modify: `netbox_otnfaults/filtersets.py`
- Modify: `netbox_otnfaults/forms.py`
- Modify: `netbox_otnfaults/tables.py`

- [ ] **Step 1: Expose `source_cutover_task` in serializer**

Add it to `OtnFaultSerializer.Meta.fields` near other relation fields.

- [ ] **Step 2: Add filter support**

Add a filter for `source_cutover_task` in `OtnFaultFilterSet`, and a `DynamicModelChoiceField` in `OtnFaultFilterForm`.

- [ ] **Step 3: Show source cutover carefully**

If adding a table column, place it before `actions` in `OtnFaultTable.Meta.fields`. Do not append business fields after `actions`.

## Task 8: Verification

**Files:**
- Test: `tests/test_cutover_generate_fault_plan.py`
- Compile: `netbox_otnfaults`, `tests`

- [ ] **Step 1: Run source-level tests**

Run: `python -m unittest tests.test_cutover_generate_fault_plan`

Expected: PASS.

- [ ] **Step 2: Run compile check**

Run: `python -m compileall netbox_otnfaults tests`

Expected: PASS.

- [ ] **Step 3: NetBox environment verification**

When a NetBox runtime is available:

Run: `python manage.py migrate`

Manual checks:
- Open one cutover detail page.
- Click “生成故障”.
- Confirm prefilled data.
- Submit.
- Verify new fault has `source_cutover_task`.
- Verify generated fault impacts match cutover impacts.
- Verify `rectification_*` fields are empty/default on the new fault.

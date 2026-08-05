from datetime import datetime
from typing import Any, Iterable

from django.urls import reverse
from django.utils import timezone

from ..models import (
    CutoverStatusChoices,
    CutoverTask,
    FaultStatusChoices,
    HeavyDuty,
    HeavyDutyTypeChoices,
    OtnFault,
)
from .shift_handover_text import (
    CutoverHandoverItem,
    FaultHandoverItem,
    HeavyDutyHandoverItem,
    build_handover_text,
    handover_window_end,
    latest_timeline_stage,
)


def _ordered_unique(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))


def _localtime(value: datetime | None) -> datetime | None:
    return timezone.localtime(value) if value is not None else None


def _display(value: object) -> str:
    text = str(value).strip() if value is not None else ''
    return text or '-'


def _joined_display(values: Iterable[object]) -> str:
    names = tuple(_display(value) for value in values)
    visible_names = tuple(name for name in names if name != '-')
    return '、'.join(visible_names) if visible_names else '-'


def get_overdue_pending_cutovers(
    *,
    user: Any,
    now: datetime,
) -> list[dict[str, str]]:
    """Return overdue pending cutovers visible to the current user."""
    cutovers = (
        CutoverTask.objects.restrict(user, 'view')
        .filter(
            status=CutoverStatusChoices.PENDING_IMPLEMENTATION,
            planned_cutover_time__lt=now,
        )
        .select_related('province', 'interruption_location_a')
        .prefetch_related('interruption_location')
        .order_by('planned_cutover_time', 'pk')
    )
    result: list[dict[str, str]] = []
    for cutover in cutovers:
        planned_time = _localtime(cutover.planned_cutover_time)
        result.append({
            'cutover_no': _display(cutover.cutover_no),
            'planned_cutover_time': _display(
                planned_time.strftime('%Y-%m-%d %H:%M') if planned_time else None
            ),
            'province': _display(cutover.province),
            'cutover_type': _display(cutover.get_cutover_type_display()),
            'a_end': _display(cutover.interruption_location_a),
            'z_end': _joined_display(cutover.interruption_location.all()),
            'location': _display(cutover.cutover_location),
            'edit_url': reverse(
                'plugins:netbox_otnfaults:cutovertask_edit',
                args=[cutover.pk],
            ),
        })
    return result


def _fault_item(fault: OtnFault) -> FaultHandoverItem:
    service_names: list[str] = []
    for impact in fault.impacts.all():
        if impact.bare_fiber_service_id and impact.bare_fiber_service:
            service_names.append(impact.bare_fiber_service.name)
        elif impact.circuit_service_id and impact.circuit_service:
            service_names.append(
                impact.circuit_service.special_line_name
                or impact.circuit_service.name
            )

    stages: list[tuple[str, datetime | None]] = [
        ('故障起始', fault.fault_occurrence_time),
        ('处理派发', fault.dispatch_time),
        ('维修出发', fault.departure_time),
        ('到达现场', fault.arrival_time),
        ('故障恢复', fault.fault_recovery_time),
    ]
    if fault.is_fiber_fault:
        stages.append(('封包完成时间', fault.closure_time))
    latest_stage = latest_timeline_stage(tuple(stages))

    return FaultHandoverItem(
        number=fault.fault_number,
        occurred_at=timezone.localtime(fault.fault_occurrence_time),
        reason=fault.get_interruption_reason_display() if fault.interruption_reason else '',
        service_names=_ordered_unique(service_names),
        handler=fault.handler or '',
        progress_at=_localtime(latest_stage[1]) if latest_stage else None,
        progress_stage=latest_stage[0] if latest_stage else '',
    )


def _cutover_item(cutover: CutoverTask) -> CutoverHandoverItem:
    bare_fiber_services = _ordered_unique([
        impact.bare_fiber_service.name
        for impact in cutover.impacts.all()
        if impact.bare_fiber_service_id and impact.bare_fiber_service
    ])
    site_z = _ordered_unique([
        site.name
        for site in cutover.interruption_location.all()
    ])
    item = CutoverHandoverItem(
        province=cutover.province.name if cutover.province else '',
        cutover_type=cutover.get_cutover_type_display(),
        planned_at=timezone.localtime(cutover.planned_cutover_time),
        impact_minutes=cutover.planned_impact_minutes,
        site_a=(
            cutover.interruption_location_a.name
            if cutover.interruption_location_a
            else ''
        ),
        site_z=site_z,
        location=cutover.cutover_location or '',
        reason=cutover.cutover_reason or '',
        bare_fiber_services=bare_fiber_services,
    )
    return item


def _heavy_duty_item(heavy_duty: HeavyDuty) -> HeavyDutyHandoverItem:
    return HeavyDutyHandoverItem(
        starts_at=timezone.localtime(heavy_duty.start_time),
        ends_at=timezone.localtime(heavy_duty.end_time),
        title=heavy_duty.name,
        description=heavy_duty.description,
    )


def generate_shift_handover_text(
    *,
    user: Any,
    shift_start: datetime,
    now: datetime,
) -> str:
    """Query permission-limited data and build the current shift handover text."""
    window_end = handover_window_end(now)
    fault_queryset = (
        OtnFault.objects.restrict(user, 'view')
        .filter(
            fault_status=FaultStatusChoices.PROCESSING,
            is_suspended=False,
        )
        .prefetch_related(
            'impacts__bare_fiber_service',
            'impacts__circuit_service',
        )
        .order_by('fault_occurrence_time', 'pk')
    )
    faults = tuple(_fault_item(fault) for fault in fault_queryset)

    cutover_queryset = (
        CutoverTask.objects.restrict(user, 'view')
        .filter(
            status=CutoverStatusChoices.PENDING_IMPLEMENTATION,
            planned_cutover_time__gte=now,
            planned_cutover_time__lt=window_end,
        )
        .select_related('province', 'interruption_location_a')
        .prefetch_related(
            'interruption_location',
            'impacts__bare_fiber_service',
            'impacts__circuit_service',
        )
        .order_by('planned_cutover_time', 'pk')
    )
    bare_fiber_cutovers: list[CutoverHandoverItem] = []
    other_cutovers: list[CutoverHandoverItem] = []
    for cutover in cutover_queryset:
        item = _cutover_item(cutover)
        bare_fiber_services = item.bare_fiber_services
        if bare_fiber_services:
            bare_fiber_cutovers.append(item)
        else:
            other_cutovers.append(item)

    heavy_duty_queryset = (
        HeavyDuty.objects.restrict(user, 'view')
        .filter(
            type__in=(
                HeavyDutyTypeChoices.IMPORTANT,
                HeavyDutyTypeChoices.COMPANY_NOTICE,
            ),
            end_time__gte=now,
            start_time__lt=window_end,
        )
        .order_by('start_time', 'pk')
    )
    heavy_duties: list[HeavyDutyHandoverItem] = []
    notices: list[HeavyDutyHandoverItem] = []
    for heavy_duty in heavy_duty_queryset:
        item = _heavy_duty_item(heavy_duty)
        if heavy_duty.type == HeavyDutyTypeChoices.IMPORTANT:
            heavy_duties.append(item)
        elif heavy_duty.type == HeavyDutyTypeChoices.COMPANY_NOTICE:
            notices.append(item)

    user_name = user.get_full_name().strip() or user.get_username()
    return build_handover_text(
        user_name=user_name,
        now=now,
        shift_start=shift_start,
        faults=faults,
        bare_fiber_cutovers=tuple(bare_fiber_cutovers),
        other_cutovers=tuple(other_cutovers),
        heavy_duties=tuple(heavy_duties),
        notices=tuple(notices),
    )

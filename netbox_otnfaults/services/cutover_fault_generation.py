from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.db import transaction
from django.utils import timezone

from netbox_otnfaults.models import (
    BusinessImpactChoices,
    CutoverReportStatusChoices,
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
    return cutover.started_at or cutover.planned_cutover_time or timezone.localtime()


def _timeout_value(cutover: CutoverTask) -> bool:
    return cutover.is_timeout != CutoverTimeoutStatusChoices.YES


def build_fault_initial_data(cutover: CutoverTask, user: Any) -> dict[str, Any]:
    details = [
        f"由割接 {cutover.cutover_no} 生成。",
        "",
        "割接原因：",
        cutover.cutover_reason or "",
    ]
    handler_parts = [
        value
        for value in (cutover.implementation_unit, cutover.cutover_contact)
        if value
    ]
    return {
        'source_cutover_task': cutover,
        'duty_officer': user if getattr(user, 'is_authenticated', False) else cutover.registrant,
        'interruption_location_a': cutover.interruption_location_a,
        'fault_occurrence_time': _fault_occurrence_time(cutover),
        'fault_recovery_time': cutover.completed_at,
        'closure_time': cutover.closed_at,
        'fault_category': FaultCategoryChoices.FIBER_BREAK,
        'interruption_reason': 'cable_rectification',
        'interruption_reason_detail': 'planned_reporting',
        'cutover_report_status': CutoverReportStatusChoices.REPORTED,
        'fault_details': '\n'.join(details).strip(),
        'interruption_longitude': cutover.cutover_longitude,
        'interruption_latitude': cutover.cutover_latitude,
        'province': cutover.province,
        'urgency': UrgencyChoices.LOW,
        'line_manager': cutover.line_supervisor,
        'maintenance_mode': cutover.maintenance_mode,
        'handling_unit': cutover.handling_unit,
        'contract': cutover.contract,
        'timeout': _timeout_value(cutover),
        'timeout_reason': cutover.timeout_reason,
        'resource_type': cutover.resource_type,
        'resource_owner': cutover.resource_owner,
        'cable_route': cutover.cable_route,
        'handler': ' / '.join(handler_parts),
        'fault_status': (
            FaultStatusChoices.CLOSED
            if cutover.completed_at
            else FaultStatusChoices.PROCESSING
        ),
        'comments': cutover.comments,
    }


def create_fault_from_cutover(
    *,
    cutover: CutoverTask,
    fault_data: Mapping[str, Any],
    user: Any,
) -> OtnFault:
    with transaction.atomic():
        if cutover.generated_faults.exists():
            raise ValueError('当前割接已经生成过故障。')

        fault = OtnFault(**dict(fault_data))
        fault.source_cutover_task = cutover
        fault.full_clean(exclude=['fault_number'])
        fault.save()
        fault.interruption_location.set(cutover.interruption_location.all())

        for cutover_impact in cutover.impacts.all():
            service_interruption_time = (
                cutover_impact.service_interruption_time
                or fault.fault_occurrence_time
            )
            service_recovery_time = (
                cutover_impact.service_recovery_time
                or fault.fault_recovery_time
            )
            is_bare_fiber = cutover_impact.service_type == ServiceTypeChoices.BARE_FIBER
            impact = OtnFaultImpact.objects.create(
                otn_fault=fault,
                service_type=cutover_impact.service_type,
                bare_fiber_service=cutover_impact.bare_fiber_service if is_bare_fiber else None,
                circuit_service=cutover_impact.circuit_service if not is_bare_fiber else None,
                service_site_a=cutover_impact.service_site_a if is_bare_fiber else None,
                business_impact=(
                    cutover_impact.business_impact
                    or BusinessImpactChoices.INTERRUPTED
                ),
                service_interruption_time=service_interruption_time,
                service_recovery_time=service_recovery_time,
                comments=cutover_impact.comments,
            )
            if is_bare_fiber:
                impact.service_site_z.set(cutover_impact.service_site_z.all())

        return fault

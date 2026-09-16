from datetime import datetime, time, timedelta
import math
import hashlib
import json
from typing import Any

from django.core.cache import cache
from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from dcim.models import Site

from ..models import (
    BusinessImpactChoices,
    FaultStatusChoices,
    OtnFault,
    OtnFaultImpact,
    ServiceTypeChoices,
    CutoverTask,
    HeavyDuty,
)
from .fault_coordinates import load_fault_path_midpoints, resolve_fault_coordinates, resolve_cutover_coordinates


FAULT_CATEGORY_SEVERITY: dict[str, str] = {
    "fiber_break": "critical",
    "power_fault": "major",
    "device_fault": "major",
    "fiber_degradation": "minor",
    "fiber_jitter": "minor",
    "ac_fault": "minor",
}


def _format_elapsed_duration(start: datetime | None, end: datetime) -> str:
    if start is None:
        return "—"
    total_seconds = max(0, int((end - start).total_seconds()))
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    if days:
        return f"{days}天{hours}小时{minutes}分"
    if hours:
        return f"{hours}小时{minutes}分"
    return f"{minutes}分"


def _impact_service_name(impact: OtnFaultImpact) -> str:
    if impact.service_type == ServiceTypeChoices.BARE_FIBER:
        return impact.bare_fiber_service.name if impact.bare_fiber_service else "裸纤业务"
    if impact.service_type == ServiceTypeChoices.CIRCUIT:
        return impact.circuit_service.name if impact.circuit_service else "电路业务"
    return "未知业务"


def _fault_priority_score(fault: OtnFault, now: datetime, impact_count: int) -> float:
    age_minutes = 0.0
    if fault.fault_occurrence_time:
        age_minutes = max(0.0, (now - fault.fault_occurrence_time).total_seconds() / 60)
    severity = FAULT_CATEGORY_SEVERITY.get(fault.fault_category or "", "minor")
    severity_weight = {"critical": 10, "major": 5, "minor": 2}.get(severity, 1)
    urgency_weight = {"high": 3, "medium": 2, "low": 1}.get(fault.urgency, 1)
    freshness = math.exp(-0.005 * age_minutes)
    return round(severity_weight * urgency_weight * max(impact_count, 1) * freshness, 2)


def build_dashboard_v2_data(sites_version: str | None = None, user: Any = None) -> dict[str, Any]:
    now = timezone.localtime()
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    next_year_start = year_start.replace(year=year_start.year + 1)
    today_start = datetime.combine(timezone.localdate(), time.min, tzinfo=now.tzinfo)
    tomorrow_start = today_start + timedelta(days=1)

    fault_counts = OtnFault.objects.aggregate(
        total_faults=Count(
            "pk",
            filter=Q(
                fault_occurrence_time__gte=year_start,
                fault_occurrence_time__lt=next_year_start,
            ),
        ),
        today_faults=Count(
            "pk",
            filter=Q(
                fault_occurrence_time__gte=today_start,
                fault_occurrence_time__lt=tomorrow_start,
            ),
        ),
    )
    active_business_interruptions = OtnFaultImpact.objects.filter(
        business_impact=BusinessImpactChoices.INTERRUPTED,
        service_recovery_time__isnull=True,
    ).count()

    processing_queryset = (
        OtnFault.objects.filter(fault_status=FaultStatusChoices.PROCESSING)
        .select_related("province", "interruption_location_a", "handling_unit")
        .prefetch_related(
            "interruption_location",
            Prefetch(
                "impacts",
                queryset=OtnFaultImpact.objects.select_related(
                    "bare_fiber_service",
                    "circuit_service",
                ),
                to_attr="dashboard_impacts",
            ),
        )
    )

    processing_queryset = list(processing_queryset)
    path_midpoints = load_fault_path_midpoints(processing_queryset)
    processing_faults: list[dict[str, Any]] = []
    for fault in processing_queryset:
        resolved_coordinates = resolve_fault_coordinates(fault, path_midpoints=path_midpoints)
        impacts = list(getattr(fault, "dashboard_impacts", []))
        active_interrupted_impacts = [
            impact
            for impact in impacts
            if impact.business_impact == BusinessImpactChoices.INTERRUPTED
            and impact.service_recovery_time is None
        ]
        priority_score = _fault_priority_score(fault, now, len(impacts))
        occurrence_time = fault.fault_occurrence_time
        processing_faults.append(
            {
                "id": fault.pk,
                "url": fault.get_absolute_url(),
                "fault_number": fault.fault_number or "未编号故障",
                "category_color": fault.get_fault_category_color() or "gray",
                "category_display": (
                    fault.get_fault_category_display() if fault.fault_category else "未知类型"
                ),
                "urgency_display": (
                    fault.get_urgency_display() if fault.urgency else "未定"
                ),
                "severity": FAULT_CATEGORY_SEVERITY.get(
                    fault.fault_category or "", "minor"
                ),
                "priority_score": priority_score,
                "lng": (
                    resolved_coordinates.lng if resolved_coordinates is not None else None
                ),
                "lat": (
                    resolved_coordinates.lat if resolved_coordinates is not None else None
                ),
                "coords_source": (
                    resolved_coordinates.source if resolved_coordinates is not None else None
                ),
                "coords_from_site": (
                    resolved_coordinates.coords_from_site
                    if resolved_coordinates is not None
                    else False
                ),
                "province": fault.province.name if fault.province else "",
                "site_a": (
                    fault.interruption_location_a.name
                    if fault.interruption_location_a
                    else ""
                ),
                "sites_z": [site.name for site in fault.interruption_location.all()],
                "occurrence_time": (
                    timezone.localtime(occurrence_time).isoformat()
                    if occurrence_time
                    else None
                ),
                "occurrence_time_display": (
                    timezone.localtime(occurrence_time).strftime("%m-%d %H:%M")
                    if occurrence_time
                    else "—"
                ),
                "duration": _format_elapsed_duration(occurrence_time, now),
                "handling_unit": fault.handling_unit.name if fault.handling_unit else "",
                "handler": fault.handler or "",
                "affected_business_names": [_impact_service_name(impact) for impact in impacts],
                "affected_business_count": len(impacts),
                "interrupted_business_count": len(active_interrupted_impacts),
                "interrupted_business_names": [
                    _impact_service_name(impact) for impact in active_interrupted_impacts
                ],
                "reason": (
                    fault.get_interruption_reason_display()
                    if fault.interruption_reason
                    else ""
                ),
                "details": (fault.fault_details or "")[:200],
            }
        )

    processing_faults.sort(
        key=lambda item: (
            item["priority_score"],
            datetime.fromisoformat(item["occurrence_time"]).timestamp()
            if item["occurrence_time"]
            else float("-inf"),
            item["id"],
        ),
        reverse=True,
    )

    sites_snapshot = cache.get("otnfaults:dashboard-v2:sites:v1")
    if sites_snapshot is None:
        sites_snapshot = load_dashboard_sites()
        cache.set("otnfaults:dashboard-v2:sites:v1", sites_snapshot, timeout=30)
    version, sites = sites_snapshot
    result = {
        **build_dashboard_cutovers(user),
        **build_dashboard_heavy_duties(user, now),
        "timestamp": now.isoformat(),
        "summary": {
            "total_faults": fault_counts["total_faults"],
            "processing_faults": len(processing_faults),
            "today_faults": fault_counts["today_faults"],
            "active_business_interruptions": active_business_interruptions,
        },
        "processing_faults": processing_faults,
        "sites_version": version,
    }
    if sites_version != version:
        result["sites"] = sites
    return result


def build_dashboard_heavy_duties(user: Any, now: datetime) -> dict[str, Any]:
    """V1 active window, including notices and memos, with view permissions."""
    if user is None:
        return {'heavy_duties': []}
    tasks = HeavyDuty.objects.restrict(user, 'view').filter(
        start_time__lte=now, end_time__gte=now,
    ).order_by('-start_time', '-pk')
    records = [{
        'id': task.pk, 'url': task.get_absolute_url(), 'name': task.name,
        'type': task.type, 'type_display': task.get_type_display(),
        'type_color': task.get_type_color() or 'gray',
        'description': task.description or '',
        'start_time': task.start_time.isoformat(), 'end_time': task.end_time.isoformat(),
        'start_time_display': timezone.localtime(task.start_time).strftime('%m-%d %H:%M'),
        'end_time_display': timezone.localtime(task.end_time).strftime('%m-%d %H:%M'),
    } for task in tasks]
    return {'heavy_duties': records}


def build_dashboard_cutovers(user: Any) -> dict[str, Any]:
    """Match OtnTodayTomorrowCutoverWidget, including object-level permissions."""
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)
    tasks = []
    if user is not None:
        tasks = (CutoverTask.objects.restrict(user, 'view')
                 .filter(planned_cutover_time__date__in=[today, tomorrow])
                 .select_related('province', 'line_supervisor', 'interruption_location_a')
                 .prefetch_related('interruption_location')
                 .order_by('planned_cutover_time', 'pk'))
    records = []
    for task in tasks:
        planned = timezone.localtime(task.planned_cutover_time)
        position = resolve_cutover_coordinates(task)
        records.append({
            'id': task.pk, 'url': task.get_absolute_url(),
            'cutover_no': task.cutover_no,
            'day': 'today' if planned.date() == today else 'tomorrow',
            'planned_time': planned.isoformat(),
            'planned_time_display': planned.strftime('%m-%d %H:%M'),
            'type_display': task.get_cutover_type_display(),
            'status': task.status, 'status_display': task.get_status_display(),
            'status_color': task.get_status_color() or 'gray',
            'province': task.province.name if task.province else '',
            'site_a': task.interruption_location_a.name if task.interruption_location_a else '',
            'sites_z': [site.name for site in task.interruption_location.all()],
            'location': task.cutover_location or '',
            'supervisor': str(task.line_supervisor) if task.line_supervisor else '',
            'is_my_task': task.line_supervisor_id == user.pk,
            'lat': position.lat if position else None,
            'lng': position.lng if position else None,
        })
    return {'cutovers': records, 'cutover_summary': {
        'today': sum(item['day'] == 'today' for item in records),
        'tomorrow': sum(item['day'] == 'tomorrow' for item in records),
        'total': len(records),
    }}


def load_dashboard_sites() -> tuple[str, list[dict[str, Any]]]:
    site_rows = Site.objects.exclude(
        latitude__isnull=True
    ).exclude(
        longitude__isnull=True
    ).order_by("pk").values("id", "name", "latitude", "longitude")
    sites = [
        {
            "id": row["id"],
            "name": row["name"],
            "lat": float(row["latitude"]),
            "lng": float(row["longitude"]),
        }
        for row in site_rows
    ]
    version = hashlib.sha256(json.dumps(sites, sort_keys=True).encode()).hexdigest()
    return version, sites

from datetime import datetime, time, timedelta
import math
from typing import Any

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Prefetch, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from dcim.models import Site

from .models import (
    BusinessImpactChoices,
    FaultStatusChoices,
    OtnFault,
    OtnFaultImpact,
    ServiceTypeChoices,
)
from .services.fault_coordinates import resolve_fault_coordinates


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


def _get_dashboard_v2_config() -> dict[str, Any]:
    plugin_settings: dict[str, Any] = settings.PLUGINS_CONFIG.get("netbox_otnfaults", {})
    return {
        "mapCenter": plugin_settings.get("dashboard_v2_map_center", [103.0, 34.3]),
        "mapZoom": plugin_settings.get("dashboard_v2_map_zoom", 4.0),
        "mapBearing": plugin_settings.get("dashboard_v2_map_bearing", 0.0),
        "basemapMode": plugin_settings.get(
            "dashboard_v2_basemap_mode", "protomaps"
        ),
        "protomapsTilesUrl": plugin_settings.get(
            "dashboard_v2_protomaps_tiles_url",
            "/maps/protomaps-z0-z6.pmtiles",
        ),
        "otnPathsPmtilesUrl": plugin_settings.get(
            "otn_paths_pmtiles_url", "/maps/otn_paths.pmtiles"
        ),
        "chinaProvincesPmtilesUrl": plugin_settings.get(
            "dashboard_v2_china_provinces_pmtiles_url",
            "/maps/china_provinces.pmtiles",
        ),
        "useLocalBasemap": plugin_settings.get("use_local_basemap", False),
        "localTilesUrl": plugin_settings.get("local_tiles_url", "/maps/china.pmtiles"),
        "localGlyphsUrl": plugin_settings.get(
            "local_glyphs_url", "/maps/fonts/{fontstack}/{range}.pbf"
        ),
        "dataUrl": reverse("plugins:netbox_otnfaults:dashboard_v2_data"),
    }


class DashboardV2PageView(PermissionRequiredMixin, View):
    permission_required = "netbox_otnfaults.view_otnfault"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            "netbox_otnfaults/dashboard_v2.html",
            {"dashboard_v2_config": _get_dashboard_v2_config()},
        )


class DashboardV2DataView(PermissionRequiredMixin, View):
    permission_required = "netbox_otnfaults.view_otnfault"

    def get(self, request: HttpRequest) -> JsonResponse:
        now = timezone.localtime()
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        today_start = datetime.combine(timezone.localdate(), time.min, tzinfo=now.tzinfo)
        tomorrow_start = today_start + timedelta(days=1)

        fault_counts = OtnFault.objects.aggregate(
            total_faults=Count(
                "pk",
                filter=Q(fault_occurrence_time__gte=year_start),
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

        processing_faults: list[dict[str, Any]] = []
        for fault in processing_queryset:
            resolved_coordinates = resolve_fault_coordinates(fault)
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

        site_rows = Site.objects.exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        ).values("id", "name", "latitude", "longitude")
        sites = [
            {
                "id": row["id"],
                "name": row["name"],
                "lat": float(row["latitude"]),
                "lng": float(row["longitude"]),
            }
            for row in site_rows
        ]
        return JsonResponse(
            {
                "timestamp": now.isoformat(),
                "summary": {
                    "total_faults": fault_counts["total_faults"],
                    "processing_faults": len(processing_faults),
                    "today_faults": fault_counts["today_faults"],
                    "active_business_interruptions": active_business_interruptions,
                },
                "processing_faults": processing_faults,
                "sites": sites,
            },
            json_dumps_params={"ensure_ascii": False},
        )

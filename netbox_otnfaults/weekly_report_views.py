"""Weekly report dashboard views."""

from collections import Counter, defaultdict
from datetime import datetime, time, timedelta

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from .models import (
    FaultCategoryChoices,
    OtnFault,
    OtnFaultImpact,
    ResourceTypeChoices,
    ServiceTypeChoices,
)


class WeeklyReportPageView(PermissionRequiredMixin, View):
    """Render the weekly report dashboard page."""

    permission_required = "netbox_otnfaults.view_otnfault"

    def get(self, request, *args, **kwargs):
        return render(request, "netbox_otnfaults/weekly_report_dashboard.html")


class WeeklyReportDataAPI(PermissionRequiredMixin, View):
    """Return the aggregated weekly report payload."""

    permission_required = "netbox_otnfaults.view_otnfault"

    @staticmethod
    def _shorten_name(value: str) -> str:
        return value.replace("\u8282\u70b9", "").replace("\u673a\u623f", "")

    @staticmethod
    def _fallback_name(value: str, default: str) -> str:
        return value if value else default

    def _build_event_location(self, fault: OtnFault) -> str:
        a_site = self._shorten_name(fault.interruption_location_a.name) if fault.interruption_location_a else ""
        z_sites = [self._shorten_name(location.name) for location in fault.interruption_location.all()]
        z_site = z_sites[0] if z_sites else ""
        if a_site and z_site:
            return f"{a_site}-{z_site}"
        if a_site:
            return a_site
        return fault.fault_number or "未知"

    def _get_fault_duration(self, fault: OtnFault) -> float:
        if not fault.fault_occurrence_time:
            return 0.0
        end_time = fault.fault_recovery_time or timezone.now()
        return (end_time - fault.fault_occurrence_time).total_seconds() / 3600.0

    def get(self, request, *args, **kwargs) -> JsonResponse:
        current_local = timezone.localtime()
        current_date = current_local.date()

        days_since_friday = (current_date.weekday() - 4) % 7
        if days_since_friday == 0 and current_date.weekday() == 4:
            period_end = current_date
        else:
            period_end = current_date - timedelta(days=days_since_friday)
        period_start = period_end - timedelta(days=6)

        period_start_dt = timezone.make_aware(datetime.combine(period_start, time.min))
        period_end_dt = timezone.make_aware(datetime.combine(period_end, time.max))
        previous_start_dt = period_start_dt - timedelta(days=7)
        previous_end_dt = period_end_dt - timedelta(days=7)

        faults = list(
            OtnFault.objects.filter(
                fault_occurrence_time__range=(period_start_dt, period_end_dt)
            )
            .select_related("province", "interruption_location_a")
            .prefetch_related("interruption_location")
        )
        previous_faults = list(
            OtnFault.objects.filter(
                fault_occurrence_time__range=(previous_start_dt, previous_end_dt)
            )
        )

        total_count = len(faults)
        previous_count = len(previous_faults)
        diff_count = total_count - previous_count

        self_built_count = sum(
            1 for fault in faults if fault.resource_type == ResourceTypeChoices.SELF_BUILT
        )
        leased_count = sum(
            1
            for fault in faults
            if fault.resource_type in (ResourceTypeChoices.COORDINATED, ResourceTypeChoices.LEASED)
        )

        total_duration = sum(self._get_fault_duration(fault) for fault in faults)
        previous_duration = sum(self._get_fault_duration(fault) for fault in previous_faults)
        diff_duration = total_duration - previous_duration

        self_built_duration = sum(
            self._get_fault_duration(fault)
            for fault in faults
            if fault.resource_type == ResourceTypeChoices.SELF_BUILT
        )
        leased_duration = sum(
            self._get_fault_duration(fault)
            for fault in faults
            if fault.resource_type in (ResourceTypeChoices.COORDINATED, ResourceTypeChoices.LEASED)
        )

        reasons_stats: dict[str, int] = {}
        for fault in faults:
            if (
                fault.interruption_reason == "cable_rectification"
                or fault.fault_category == FaultCategoryChoices.FIBER_JITTER
            ):
                continue

            reason_text = "未知"
            if fault.interruption_reason:
                reason_text = fault.get_interruption_reason_display()
            elif fault.fault_category:
                reason_text = fault.get_fault_category_display()

            reasons_stats[reason_text] = reasons_stats.get(reason_text, 0) + 1

        reason_chart_data = [{"name": name, "value": value} for name, value in reasons_stats.items()]
        reason_chart_data.sort(key=lambda item: item["value"], reverse=True)

        province_counts: Counter[str] = Counter()
        province_durations: Counter[str] = Counter()
        for fault in faults:
            province_name = fault.province.name if fault.province else "未知"
            province_counts[province_name] += 1
            province_durations[province_name] += self._get_fault_duration(fault)

        top_provinces = []
        for province_name, count in province_counts.most_common(4):
            province_faults = [
                fault
                for fault in faults
                if (fault.province.name if fault.province else "未知") == province_name
            ]
            province_reasons = Counter(
                fault.get_interruption_reason_display()
                for fault in province_faults
                if fault.interruption_reason
            )
            top_reason = province_reasons.most_common(1)[0][0] if province_reasons else "未知"

            paths = []
            for fault in province_faults:
                a_site = fault.interruption_location_a.name if fault.interruption_location_a else ""
                z_sites = [location.name for location in fault.interruption_location.all()]
                z_site = z_sites[0] if z_sites else ""

                a_site = self._shorten_name(a_site)
                z_site = self._shorten_name(z_site)

                if a_site and z_site:
                    paths.append(f"{a_site}-{z_site}")
                elif a_site:
                    paths.append(a_site)

            top_provinces.append(
                {
                    "province": province_name,
                    "count": count,
                    "duration": round(province_durations[province_name], 1),
                    "main_reason": top_reason,
                    "paths": " | ".join(list(dict.fromkeys(paths))[:2]),
                }
            )

        no_const_duration = sum(
            self._get_fault_duration(fault)
            for fault in faults
            if fault.interruption_reason != "construction"
        )

        long_faults = []
        for fault in faults:
            if fault.interruption_reason == "construction":
                continue

            duration = self._get_fault_duration(fault)
            if duration <= 8.0:
                continue

            long_faults.append(
                {
                    "prov": fault.province.name if fault.province else "未知",
                    "loc": self._build_event_location(fault),
                    "duration": round(duration, 1),
                    "reason": fault.get_interruption_reason_display()
                    if fault.interruption_reason
                    else "未知",
                    "details": (fault.fault_details or "").replace("\n", " ")[:60],
                }
            )

        impacts = list(
            OtnFaultImpact.objects.filter(
                service_type=ServiceTypeChoices.BARE_FIBER,
                service_interruption_time__range=(period_start_dt, period_end_dt),
            ).select_related(
                "otn_fault",
                "otn_fault__province",
                "otn_fault__interruption_location_a",
                "bare_fiber_service",
            )
        )

        grouped_impacts: dict[str, list[OtnFaultImpact]] = defaultdict(list)
        for impact in impacts:
            service_name = "未知业务"
            if impact.bare_fiber_service and impact.bare_fiber_service.name:
                service_name = impact.bare_fiber_service.name
            grouped_impacts[service_name].append(impact)

        services_data = []
        for service_name in sorted(grouped_impacts):
            service_impacts = grouped_impacts[service_name]
            break_cnt = 0
            block_cnt = 0
            jitter_cnt = 0
            service_duration = 0.0
            segments = []

            for impact in service_impacts:
                fault = impact.otn_fault
                if fault.fault_category == FaultCategoryChoices.FIBER_JITTER:
                    jitter_cnt += 1
                else:
                    break_cnt += 1
                    block_cnt += 1
                    end_time = impact.service_recovery_time or timezone.now()
                    service_duration += (
                        end_time - impact.service_interruption_time
                    ).total_seconds() / 3600.0

                province = self._fallback_name(fault.province.name if fault.province else "", "未知")
                location = self._shorten_name(
                    fault.interruption_location_a.name if fault.interruption_location_a else ""
                )
                reason = (
                    fault.get_interruption_reason_display()
                    if fault.interruption_reason
                    else (fault.get_fault_category_display() if fault.fault_category else "未知")
                )
                segments.append(f"{province} {location} {reason}".strip())

            status = "jitter" if break_cnt == 0 and jitter_cnt > 0 else "interruption"
            services_data.append(
                {
                    "id": len(services_data) + 1,
                    "name": service_name,
                    "status": status,
                    "break_cnt": break_cnt,
                    "block_cnt": block_cnt,
                    "jitter_cnt": jitter_cnt,
                    "duration": round(service_duration, 1),
                    "segments": " | ".join(list(dict.fromkeys(filter(None, segments)))[:3]),
                }
            )

        return JsonResponse(
            {
                "timestamp": current_date.isoformat(),
                "generated_at": current_local.strftime("%Y-%m-%d %H:%M"),
                "period": {
                    "start": period_start_dt.strftime("%Y.%m.%d"),
                    "end": period_end_dt.strftime("%Y.%m.%d"),
                },
                "summary": {
                    "total_count": total_count,
                    "diff_count": diff_count,
                    "total_duration": round(total_duration, 1),
                    "diff_duration": round(diff_duration, 1),
                    "self_built": {
                        "count": self_built_count,
                        "duration": round(self_built_duration, 1),
                    },
                    "leased": {
                        "count": leased_count,
                        "duration": round(leased_duration, 1),
                    },
                    "no_const_duration": round(no_const_duration, 1),
                },
                "reasons_analysis": reason_chart_data,
                "top_provinces": top_provinces,
                "major_events": long_faults,
                "bare_fiber": services_data,
            },
            json_dumps_params={"ensure_ascii": False},
        )

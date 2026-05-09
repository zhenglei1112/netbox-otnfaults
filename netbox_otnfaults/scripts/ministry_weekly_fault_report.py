from __future__ import annotations

import csv
import datetime as dt
from io import StringIO
from types import SimpleNamespace
from typing import Any, Iterable, NamedTuple

from django.utils import timezone
from extras.scripts import DateVar, Script

from netbox_otnfaults.models import OtnFault


CSV_HEADERS: tuple[str, ...] = (
    "故障编号",
    "故障分类",
    "值守人员",
    "A端",
    "Z端",
    "起始时间",
    "故障历时",
    "一级原因",
    "二级原因",
    "对部周报",
)

FIBER_CATEGORIES: frozenset[str] = frozenset(
    ("fiber_break", "fiber_degradation", "fiber_jitter")
)


class _FallbackFaultReportRecord(NamedTuple):
    fault_number: str
    fault_category: str
    fault_category_label: str
    duty_officer: str
    site_a: str
    site_z: tuple[str, ...]
    occurrence_time: dt.datetime
    duration_seconds: int
    primary_reason: str
    primary_reason_label: str
    secondary_reason_label: str


class _FallbackMergedFault(NamedTuple):
    carrier: _FallbackFaultReportRecord
    duration_seconds: int
    merged_fault_numbers: tuple[str, ...]


class MinistryWeeklyFaultReport(Script):
    class Meta:
        name = "涉及88系统故障对部周报CSV"
        description = "按输入日期所在自然周统计带“涉及88系统”标签的故障，合并同日同口径故障并输出CSV。"
        commit_default = False

    report_date = DateVar(
        label="统计日期",
        description="统计该日期所在周，范围为周一 0 点至下周一 0 点。",
        required=False,
    )

    def run(self, data: dict[str, Any], commit: bool) -> str:
        report_service = _load_report_service()
        report_date = data.get("report_date") or timezone.localdate()
        self.output_mime_type = "text/csv; charset=utf-8"
        self.output_extension = "csv"
        self.output_filename = f"ministry_weekly_fault_report_{report_date:%Y%m%d}.csv"
        current_timezone = timezone.get_current_timezone()
        start, end = report_service.build_week_range(report_date, timezone=current_timezone)

        self.log_info(f"统计范围：{start:%Y-%m-%d %H:%M:%S} 至 {end:%Y-%m-%d %H:%M:%S}（不含结束时刻）")
        faults = (
            OtnFault.objects.filter(
                fault_occurrence_time__gte=start,
                fault_occurrence_time__lt=end,
                tags__name__icontains="涉及88系统",
            )
            .select_related("duty_officer", "interruption_location_a")
            .prefetch_related("interruption_location", "tags")
            .order_by("-fault_occurrence_time", "-fault_number")
            .distinct()
        )

        records = [_record_from_fault(fault, report_service.FaultReportRecord) for fault in faults]
        rows = report_service.build_weekly_report_rows(records)
        csv_text = report_service.render_csv(rows)

        self.log_success(
            f"生成 {len(rows)} 条对部周报CSV记录。可复制脚本返回内容保存为CSV，"
            f"建议文件名：{self.output_filename}"
        )
        return csv_text

    def get_job_data(self) -> dict[str, Any]:
        data = super().get_job_data()
        data["output_mime_type"] = getattr(self, "output_mime_type", "text/csv; charset=utf-8")
        data["output_extension"] = getattr(self, "output_extension", "csv")
        data["output_filename"] = getattr(self, "output_filename", "ministry_weekly_fault_report.csv")
        return data


def _load_report_service() -> Any:
    return _fallback_report_service()


def _fallback_report_service() -> SimpleNamespace:
    return SimpleNamespace(
        FaultReportRecord=_FallbackFaultReportRecord,
        build_week_range=_fallback_build_week_range,
        build_weekly_report_rows=_fallback_build_weekly_report_rows,
        render_csv=_fallback_render_csv,
    )


def _fallback_build_week_range(report_date: dt.date, timezone: dt.tzinfo) -> tuple[dt.datetime, dt.datetime]:
    week_start_date = report_date - dt.timedelta(days=report_date.weekday())
    start = dt.datetime.combine(week_start_date, dt.time.min, tzinfo=timezone)
    end = start + dt.timedelta(days=7)
    return start, end


def _fallback_build_weekly_report_rows(records: Iterable[_FallbackFaultReportRecord]) -> list[dict[str, str]]:
    return [_fallback_row_from_merged_fault(item) for item in _fallback_merge_faults(records)]


def _fallback_render_csv(rows: Iterable[dict[str, str]]) -> str:
    output = StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(output, fieldnames=CSV_HEADERS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def _fallback_merge_faults(records: Iterable[_FallbackFaultReportRecord]) -> list[_FallbackMergedFault]:
    grouped_records: dict[tuple[dt.date, str, str, tuple[str, ...], str], list[_FallbackFaultReportRecord]] = {}
    for record in sorted(records, key=lambda item: (item.occurrence_time, item.fault_number)):
        grouped_records.setdefault(_fallback_merge_key(record), []).append(record)

    merged_faults: list[_FallbackMergedFault] = []
    for group in grouped_records.values():
        carrier = _fallback_select_carrier(group)
        merged_numbers = tuple(record.fault_number for record in group if record.fault_number != carrier.fault_number)
        merged_faults.append(
            _FallbackMergedFault(
                carrier=carrier,
                duration_seconds=sum(record.duration_seconds for record in group),
                merged_fault_numbers=merged_numbers,
            )
        )
    return sorted(merged_faults, key=lambda item: (item.carrier.occurrence_time, item.carrier.fault_number), reverse=True)


def _fallback_merge_key(record: _FallbackFaultReportRecord) -> tuple[dt.date, str, str, tuple[str, ...], str]:
    category_group = "fiber" if record.fault_category in FIBER_CATEGORIES else record.fault_category
    return (
        record.occurrence_time.date(),
        category_group,
        record.site_a,
        tuple(sorted(record.site_z)),
        record.primary_reason,
    )


def _fallback_select_carrier(records: list[_FallbackFaultReportRecord]) -> _FallbackFaultReportRecord:
    fiber_break_records = [record for record in records if record.fault_category == "fiber_break"]
    if fiber_break_records:
        return fiber_break_records[0]
    return records[0]


def _fallback_row_from_merged_fault(merged_fault: _FallbackMergedFault) -> dict[str, str]:
    fault = merged_fault.carrier
    weekly_report = ""
    if merged_fault.merged_fault_numbers:
        weekly_report = f"合并了{'、'.join(merged_fault.merged_fault_numbers)}"
    elif fault.primary_reason == "cable_rectification":
        weekly_report = "否，整改"

    return {
        "故障编号": fault.fault_number,
        "故障分类": fault.fault_category_label,
        "值守人员": fault.duty_officer,
        "A端": fault.site_a,
        "Z端": "、".join(fault.site_z),
        "起始时间": _fallback_format_datetime(fault.occurrence_time),
        "故障历时": _fallback_format_duration(merged_fault.duration_seconds),
        "一级原因": fault.primary_reason_label,
        "二级原因": fault.secondary_reason_label,
        "对部周报": weekly_report,
    }


def _fallback_format_datetime(value: dt.datetime) -> str:
    return f"{value.year}/{value.month}/{value.day} {value.hour}:{value.minute:02d}"


def _fallback_format_duration(total_seconds: int) -> str:
    remaining = max(0, int(total_seconds))
    days, remaining = divmod(remaining, 86400)
    hours, remaining = divmod(remaining, 3600)
    minutes, seconds = divmod(remaining, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    if minutes:
        parts.append(f"{minutes}分")
    if seconds or not parts:
        parts.append(f"{seconds}秒")
    return "".join(parts)


def _record_from_fault(fault: OtnFault, record_class: Any) -> Any:
    occurrence_time = timezone.localtime(fault.fault_occurrence_time)
    recovery_time = timezone.localtime(fault.fault_recovery_time) if fault.fault_recovery_time else timezone.localtime()
    duration_seconds = int(max(0, (recovery_time - occurrence_time).total_seconds()))

    return record_class(
        fault_number=fault.fault_number or "",
        fault_category=fault.fault_category or "",
        fault_category_label=_display(fault, "get_fault_category_display", fault.fault_category),
        duty_officer=_user_name(fault.duty_officer),
        site_a=_object_name(fault.interruption_location_a),
        site_z=tuple(_object_name(site) for site in fault.interruption_location.all()),
        occurrence_time=occurrence_time,
        duration_seconds=duration_seconds,
        primary_reason=fault.interruption_reason or "",
        primary_reason_label=_display(fault, "get_interruption_reason_display", fault.interruption_reason),
        secondary_reason_label=_display(
            fault,
            "get_interruption_reason_detail_display",
            fault.interruption_reason_detail,
        ),
    )


def _display(obj: object, method_name: str, fallback: object) -> str:
    if not fallback:
        return ""
    display_method = getattr(obj, method_name, None)
    if callable(display_method):
        return str(display_method())
    return str(fallback)


def _user_name(user: object) -> str:
    full_name_method = getattr(user, "get_full_name", None)
    if callable(full_name_method):
        full_name = full_name_method()
        if full_name:
            return str(full_name)
    return str(user) if user else ""


def _object_name(value: object) -> str:
    name = getattr(value, "name", None)
    return str(name) if name else str(value) if value else ""

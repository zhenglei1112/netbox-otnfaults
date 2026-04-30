"""
OTN 故障统计展示页面 - 后端视图

提供独立的统计看板以及聚合API（兼容ECharts等前端工具及下钻查询）。
"""
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q, F, Func, DurationField, ExpressionWrapper, QuerySet
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import View
from datetime import timedelta, date
from django.db.models.functions import TruncDate, Coalesce, Cast
from decimal import Decimal
import math
from urllib.parse import quote

from .models import (
    OtnFault, OtnFaultImpact, OtnPath,
    FaultCategoryChoices, ResourceTypeChoices, CableTypeChoices,
    ServiceTypeChoices, FaultStatusChoices
)
from dcim.models import Region
from .statistics_period import build_period_display


FAULT_CATEGORY_SUMMARY_ORDER: list[tuple[str, str]] = [
    (FaultCategoryChoices.FIBER_BREAK, '光缆中断'),
    (FaultCategoryChoices.AC_FAULT, '空调故障'),
    (FaultCategoryChoices.POWER_FAULT, '供电故障'),
    (FaultCategoryChoices.DEVICE_FAULT, '设备故障'),
]

PHYSICAL_DAILY_CATEGORY_ORDER: list[tuple[str, str, str]] = [
    (FaultCategoryChoices.FIBER_BREAK, '光缆中断', '#dc3545'),
    (FaultCategoryChoices.POWER_FAULT, '供电故障', '#6f42c1'),
    (FaultCategoryChoices.AC_FAULT, '空调故障', '#0d6efd'),
    (FaultCategoryChoices.DEVICE_FAULT, '设备故障', '#fd7e14'),
]

PHYSICAL_WEEK_MONTH_LABELS: dict[int, str] = {
    1: '一月',
    2: '二月',
    3: '三月',
    4: '四月',
    5: '五月',
    6: '六月',
    7: '七月',
    8: '八月',
    9: '九月',
    10: '十月',
    11: '十一月',
    12: '十二月',
}

OVERALL_EXCLUDED_TOTAL_CATEGORIES: set[str] = {
    FaultCategoryChoices.FIBER_DEGRADATION,
    FaultCategoryChoices.FIBER_JITTER,
}

SOURCE_SUMMARY_ORDER: list[str] = ['自控', '第三方', '其他/未填']

RESOURCE_TYPE_ORDER = [
    ResourceTypeChoices.SELF_BUILT,
    ResourceTypeChoices.COORDINATED,
    ResourceTypeChoices.LEASED,
    'unfilled',
]


def _source_group_for_fault(fault) -> str:
    if fault.resource_type in [ResourceTypeChoices.SELF_BUILT, ResourceTypeChoices.COORDINATED]:
        return '自控'
    if fault.resource_type == ResourceTypeChoices.LEASED:
        return '第三方'
    return '其他/未填'


def _sorted_count_items(counts: dict[str, int]) -> list[dict[str, int]]:
    return [
        {'name': name, 'value': count}
        for name, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]


def _ordered_source_items(counts: dict[str, int | float]) -> list[dict[str, int | float]]:
    return [
        {'name': name, 'value': counts.get(name, 0)}
        for name in SOURCE_SUMMARY_ORDER
    ]


def _build_resource_chart_data(resource_stats: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    resource_by_key = {
        str(stats['id']): (name, stats)
        for name, stats in resource_stats.items()
    }
    return [
        {
            'name': name,
            'value': stats['count'],
            'duration': round(float(stats['duration']), 2),
            'key': stats['id'],
        }
        for resource_key in RESOURCE_TYPE_ORDER
        if resource_key in resource_by_key
        for name, stats in [resource_by_key[resource_key]]
    ]


def _build_fault_category_summary(faults: list, now) -> list[dict[str, str | int | float]]:
    category_counts: dict[str, dict[str, int | float]] = {
        label: {'count': 0, 'duration': 0.0}
        for _, label in FAULT_CATEGORY_SUMMARY_ORDER
    }
    category_labels = dict(FAULT_CATEGORY_SUMMARY_ORDER)

    for fault in faults:
        label = category_labels.get(fault.fault_category, '未知')
        if label not in category_counts:
            category_counts[label] = {'count': 0, 'duration': 0.0}

        category_counts[label]['count'] += 1

        if fault.fault_occurrence_time:
            end_t = fault.fault_recovery_time if fault.fault_recovery_time else now
            duration_hours = (end_t - fault.fault_occurrence_time).total_seconds() / 3600.0
            category_counts[label]['duration'] += duration_hours

    return [
        {
            'name': label,
            'value': int(category_counts[label]['count']),
            'duration': round(float(category_counts[label]['duration']), 2),
        }
        for _, label in FAULT_CATEGORY_SUMMARY_ORDER
    ]


def _add_fault_duration_to_daily_buckets(
    fault,
    duration_buckets: dict[str, float],
    period_start,
    period_end,
    now,
    duration_samples: dict[str, list[float]] | None = None,
) -> None:
    if not fault.fault_occurrence_time:
        return

    fault_start = timezone.localtime(fault.fault_occurrence_time)
    fault_end = timezone.localtime(fault.fault_recovery_time) if fault.fault_recovery_time else now
    if fault_end <= period_start or fault_start >= period_end:
        return

    current_start = max(fault_start, period_start)
    while current_start < min(fault_end, period_end):
        day_start = timezone.datetime.combine(
            current_start.date(),
            timezone.datetime.min.time(),
            tzinfo=timezone.get_current_timezone(),
        )
        day_end = day_start + timedelta(days=1)
        day_key = day_start.date().isoformat()
        overlap_start = max(current_start, day_start)
        overlap_end = min(fault_end, day_end)
        if day_key in duration_buckets and overlap_end > overlap_start:
            duration_hours = (overlap_end - overlap_start).total_seconds() / 3600.0
            duration_buckets[day_key] += duration_hours
            if duration_samples is not None:
                duration_samples[day_key].append(duration_hours)
        current_start = day_end


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] + ((sorted_values[upper] - sorted_values[lower]) * weight)


def _calculate_boxplot_values(values: list[float]) -> list[float]:
    if not values:
        return [0, 0, 0, 0, 0]
    sorted_values = sorted(values)
    q1 = _percentile(sorted_values, 0.25)
    median = _percentile(sorted_values, 0.5)
    q3 = _percentile(sorted_values, 0.75)
    iqr = q3 - q1
    upper_whisker = q3 + (1.5 * iqr)
    return [
        round(sorted_values[0], 2),
        round(q1, 2),
        round(median, 2),
        round(q3, 2),
        round(upper_whisker, 2),
    ]


def _calculate_boxplot_outliers(values: list[float]) -> list[float]:
    if not values:
        return []
    sorted_values = sorted(values)
    q1 = _percentile(sorted_values, 0.25)
    q3 = _percentile(sorted_values, 0.75)
    iqr = q3 - q1
    upper_whisker = q3 + (1.5 * iqr)
    return [round(value, 2) for value in sorted_values if value > upper_whisker]


def _build_boxplot_outlier_points(labels: list[str], samples: dict[str, list[float]]) -> list[list[str | float]]:
    return [
        [day, value]
        for day in labels
        for value in _calculate_boxplot_outliers(samples[day])
    ]


def _resolve_physical_daily_range(now) -> tuple:
    current_timezone = timezone.get_current_timezone()
    year_start = timezone.datetime(now.year, 1, 1, tzinfo=current_timezone)
    year_end = timezone.datetime(now.year + 1, 1, 1, tzinfo=current_timezone)
    return year_start, year_end


def _format_physical_week_label(week_start: date, month_week_counts: dict[int, int]) -> str:
    month_week_counts[week_start.month] = month_week_counts.get(week_start.month, 0) + 1
    return f"{PHYSICAL_WEEK_MONTH_LABELS[week_start.month]}第{month_week_counts[week_start.month]}周"


def _build_physical_week_ranges(period_start, period_end) -> list[dict[str, str]]:
    ranges: list[dict[str, str]] = []
    month_week_counts: dict[int, int] = {}
    cursor = period_start.date()
    end_day = period_end.date()
    while cursor < end_day:
        week_end = min(cursor + timedelta(days=7), end_day)
        label_end = week_end - timedelta(days=1)
        ranges.append({
            'key': cursor.isoformat(),
            'label': _format_physical_week_label(cursor, month_week_counts),
            'start': cursor.isoformat(),
            'end': label_end.isoformat(),
        })
        cursor = week_end
    return ranges


def _build_physical_daily_fault_series(period_start, period_end, faults: list, now=None) -> dict[str, list]:
    now = now or timezone.localtime()

    day_labels: list[str] = []
    cursor = period_start.date()
    end_day = period_end.date()
    while cursor < end_day:
        day_labels.append(cursor.isoformat())
        cursor += timedelta(days=1)
    week_ranges = _build_physical_week_ranges(period_start, period_end)

    daily_counts: dict[str, int] = {day: 0 for day in day_labels}
    weekly_counts: dict[str, int] = {week['key']: 0 for week in week_ranges}
    daily_durations: dict[str, float] = {day: 0.0 for day in day_labels}
    weekly_durations: dict[str, float] = {week['key']: 0.0 for week in week_ranges}
    duration_samples: dict[str, list[float]] = {day: [] for day in day_labels}
    boxplot_samples: dict[str, dict[str, list[float]]] = {
        'all': {day: [] for day in day_labels},
        'exclude_short': {day: [] for day in day_labels},
        'exclude_rectification': {day: [] for day in day_labels},
        'exclude_short_rectification': {day: [] for day in day_labels},
    }

    for fault in faults:
        if not fault.fault_occurrence_time:
            continue
        fault_start = timezone.localtime(fault.fault_occurrence_time)
        local_day = fault_start.date().isoformat()
        if local_day in daily_counts:
            daily_counts[local_day] += 1
            fault_end = timezone.localtime(fault.fault_recovery_time) if fault.fault_recovery_time else now
            total_duration = (fault_end - fault_start).total_seconds() / 3600.0
            duration_hours = total_duration
            duration_samples[local_day].append(total_duration)
            daily_durations[local_day] += total_duration
            week_key = next((week['key'] for week in week_ranges if week['start'] <= local_day <= week['end']), None)
            if week_key:
                weekly_counts[week_key] += 1
                weekly_durations[week_key] += total_duration
            reason = fault.get_interruption_reason_display() if fault.interruption_reason else ''
            boxplot_samples['all'][local_day].append(total_duration)
            if duration_hours > 0.5:
                boxplot_samples['exclude_short'][local_day].append(total_duration)
            if reason != '光缆整改':
                boxplot_samples['exclude_rectification'][local_day].append(total_duration)
            if duration_hours > 0.5 and reason != '光缆整改':
                boxplot_samples['exclude_short_rectification'][local_day].append(total_duration)

    return {
        'labels': day_labels,
        'day_labels': day_labels,
        'week_labels': [week['label'] for week in week_ranges],
        'day_counts': [daily_counts[day] for day in day_labels],
        'week_counts': [weekly_counts[week['key']] for week in week_ranges],
        'day_durations': [round(daily_durations[day], 2) for day in day_labels],
        'week_durations': [round(weekly_durations[week['key']], 2) for week in week_ranges],
        'durations': [round(daily_durations[day], 2) for day in day_labels],
        'boxplot': [_calculate_boxplot_values(duration_samples[day]) for day in day_labels],
        'boxplot_outliers': _build_boxplot_outlier_points(day_labels, duration_samples),
        'boxplot_options': {
            'all': [_calculate_boxplot_values(boxplot_samples['all'][day]) for day in day_labels],
            'exclude_short': [_calculate_boxplot_values(boxplot_samples['exclude_short'][day]) for day in day_labels],
            'exclude_rectification': [_calculate_boxplot_values(boxplot_samples['exclude_rectification'][day]) for day in day_labels],
            'exclude_short_rectification': [_calculate_boxplot_values(boxplot_samples['exclude_short_rectification'][day]) for day in day_labels],
        },
        'boxplot_outlier_options': {
            'all': _build_boxplot_outlier_points(day_labels, boxplot_samples['all']),
            'exclude_short': _build_boxplot_outlier_points(day_labels, boxplot_samples['exclude_short']),
            'exclude_rectification': _build_boxplot_outlier_points(day_labels, boxplot_samples['exclude_rectification']),
            'exclude_short_rectification': _build_boxplot_outlier_points(day_labels, boxplot_samples['exclude_short_rectification']),
        },
        'series': [
            {
                'name': '光缆中断',
                'color': '#dc3545',
                'data': [daily_counts[day] for day in day_labels],
            }
        ],
    }


def _build_other_fault_summary(faults: list, suspended_faults_count: int) -> dict[str, int]:
    return {
        'fiber_degradation': sum(1 for f in faults if f.fault_category == FaultCategoryChoices.FIBER_DEGRADATION),
        'fiber_jitter': sum(1 for f in faults if f.fault_category == FaultCategoryChoices.FIBER_JITTER),
        'suspended_faults': suspended_faults_count,
    }


def get_cable_break_base_queryset(start_date, end_date) -> QuerySet:
    """Return the shared cable-break queryset used by statistics and map views."""
    return (
        OtnFault.objects.select_related('province', 'interruption_location_a')
        .prefetch_related('interruption_location')
        .filter(
            fault_occurrence_time__gte=start_date,
            fault_occurrence_time__lt=end_date,
            fault_category=FaultCategoryChoices.FIBER_BREAK,
        )
        .exclude(fault_status=FaultStatusChoices.SUSPENDED)
    )


def _occurrence_period_for_fault(fault) -> str:
    """Return the daytime/nighttime bucket based on the fault start time."""
    if not fault.fault_occurrence_time:
        return '夜间'

    local_occurrence = timezone.localtime(fault.fault_occurrence_time)
    return '日间' if 6 <= local_occurrence.hour < 18 else '夜间'


def _format_local_datetime(value) -> str:
    """Format a timezone-aware datetime in the active local timezone."""
    return timezone.localtime(value).strftime('%Y-%m-%d %H:%M')


def _duration_histogram_bucket_index(duration_hours: float) -> int:
    return min(25, max(1, math.ceil(duration_hours)))


def _duration_histogram_bucket_label(bucket: int) -> str:
    return str(bucket) if bucket <= 24 else '>24'


def _compute_cable_break_overview(faults: list, now) -> dict:
    """从故障列表中筛选光缆中断并计算概览统计数据（可复用于当前期与上周期）。"""
    cable_break_faults = [
        f for f in faults
        if f.fault_category == FaultCategoryChoices.FIBER_BREAK
        and f.fault_status != FaultStatusChoices.SUSPENDED
    ]

    reason_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    total_duration: float = 0.0
    reason_duration: dict[str, float] = {}
    source_duration: dict[str, float] = {}
    long_duration_buckets: dict[str, int] = {
        '6-8小时': 0, '8-10小时': 0, '10-12小时': 0, '12小时以上': 0,
    }
    long_duration_bucket_durations: dict[str, float] = {
        '6-8小时': 0.0, '8-10小时': 0.0, '10-12小时': 0.0, '12小时以上': 0.0,
    }
    long_duration_total: float = 0.0

    cb_valid_count = 0
    cb_valid_dur = 0.0
    cb_day_count = 0
    cb_day_dur = 0.0
    cb_night_count = 0
    cb_night_dur = 0.0
    cb_cons_count = 0
    cb_cons_dur = 0.0
    cb_noncons_count = 0
    cb_noncons_dur = 0.0
    duration_values: list[float] = []
    timeout_count = 0
    histogram: dict[int, int] = {i: 0 for i in range(1, 26)}

    for fault in cable_break_faults:
        reason = fault.get_interruption_reason_display() if fault.interruption_reason else '未填/未知'
        source = _source_group_for_fault(fault)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1

        end_t = fault.fault_recovery_time if fault.fault_recovery_time else now
        duration_hours = (end_t - fault.fault_occurrence_time).total_seconds() / 3600.0
        duration_values.append(duration_hours)
        if duration_hours >= 4.0:
            timeout_count += 1

        hist_bucket = _duration_histogram_bucket_index(duration_hours)
        histogram[hist_bucket] += 1

        total_duration += duration_hours
        reason_duration[reason] = reason_duration.get(reason, 0.0) + duration_hours
        source_duration[source] = source_duration.get(source, 0.0) + duration_hours

        if 6.0 <= duration_hours < 8.0:
            long_duration_buckets['6-8小时'] += 1
            long_duration_bucket_durations['6-8小时'] += duration_hours
            long_duration_total += duration_hours
        elif 8.0 <= duration_hours < 10.0:
            long_duration_buckets['8-10小时'] += 1
            long_duration_bucket_durations['8-10小时'] += duration_hours
            long_duration_total += duration_hours
        elif 10.0 <= duration_hours < 12.0:
            long_duration_buckets['10-12小时'] += 1
            long_duration_bucket_durations['10-12小时'] += duration_hours
            long_duration_total += duration_hours
        elif duration_hours >= 12.0:
            long_duration_buckets['12小时以上'] += 1
            long_duration_bucket_durations['12小时以上'] += duration_hours
            long_duration_total += duration_hours

        valid_duration = duration_hours > 0.5
        if valid_duration:
            cb_valid_count += 1
            cb_valid_dur += duration_hours

        occurrence_period = _occurrence_period_for_fault(fault)
        if valid_duration:
            if occurrence_period == '日间':
                cb_day_count += 1
                cb_day_dur += duration_hours
            else:
                cb_night_count += 1
                cb_night_dur += duration_hours

            if reason == '施工':
                cb_cons_count += 1
                cb_cons_dur += duration_hours
            else:
                cb_noncons_count += 1
                cb_noncons_dur += duration_hours

    cb_count = len(cable_break_faults)
    duration_values = sorted(duration_values)
    avg_metrics = {
        'overall_avg': round(total_duration / cb_count if cb_count > 0 else 0.0, 2),
        'p50_repair_duration': round(_percentile(duration_values, 0.5), 2),
        'p90_repair_duration': round(_percentile(duration_values, 0.9), 2),
        'timeout_rate': round(timeout_count * 100.0 / cb_count if cb_count > 0 else 0.0, 1),
        'valid_avg': round(cb_valid_dur / cb_valid_count if cb_valid_count > 0 else 0.0, 2),
        'daytime_avg': round(cb_day_dur / cb_day_count if cb_day_count > 0 else 0.0, 2),
        'nighttime_avg': round(cb_night_dur / cb_night_count if cb_night_count > 0 else 0.0, 2),
        'construction_avg': round(cb_cons_dur / cb_cons_count if cb_cons_count > 0 else 0.0, 2),
        'non_construction_avg': round(cb_noncons_dur / cb_noncons_count if cb_noncons_count > 0 else 0.0, 2),
    }

    hist_data = []
    for i in range(1, 26):
        label = _duration_histogram_bucket_label(i)
        count = histogram[i]
        pct = round(count * 100.0 / cb_count, 1) if cb_count > 0 else 0.0
        hist_data.append({'label': label, 'value': count, 'percent': pct})

    long_duration_bucket_durations = {
        name: round(duration, 2)
        for name, duration in long_duration_bucket_durations.items()
    }

    return {
        'total_count': cb_count,
        'total_duration': round(total_duration, 2),
        'long_duration_total': round(long_duration_total, 2),
        'reason_top3': _sorted_count_items(reason_counts)[:3],
        'source_counts': _ordered_source_items(source_counts),
        'reason_duration_top3': _sorted_count_items(reason_duration)[:3],
        'source_duration_counts': _ordered_source_items(source_duration),
        'long_duration_buckets': long_duration_buckets,
        'long_duration_bucket_durations': long_duration_bucket_durations,
        'avg_metrics': avg_metrics,
        'histogram': hist_data,
    }


def _parse_time_range(request):
    """从请求参数解析时间范围，返回 (start_date, end_date, prev_start_date, prev_end_date, filter_type)"""
    filter_type: str = request.GET.get('filter_type', 'year')
    year: int = int(request.GET.get('year', timezone.localdate().year))
    now = timezone.localtime()
    tz = timezone.get_current_timezone()

    start_date = None
    end_date = None
    prev_start_date = None
    prev_end_date = None

    if filter_type == 'year':
        start_date = timezone.datetime(year, 1, 1, tzinfo=tz)
        end_date = timezone.datetime(year + 1, 1, 1, tzinfo=tz)
        prev_start_date = timezone.datetime(year - 1, 1, 1, tzinfo=tz)
        prev_end_date = start_date
    elif filter_type == 'half':
        half = int(request.GET.get('half', 1 if now.month <= 6 else 2))
        half = 1 if half <= 1 else 2
        start_month = 1 if half == 1 else 7
        end_month = 7 if half == 1 else 1
        end_year = year if half == 1 else year + 1
        prev_start_year = year - 1 if half == 1 else year
        prev_start_month = 7 if half == 1 else 1
        start_date = timezone.datetime(year, start_month, 1, tzinfo=tz)
        end_date = timezone.datetime(end_year, end_month, 1, tzinfo=tz)
        prev_start_date = timezone.datetime(prev_start_year, prev_start_month, 1, tzinfo=tz)
        prev_end_date = start_date
    elif filter_type == 'quarter':
        quarter = int(request.GET.get('quarter', ((now.month - 1) // 3) + 1))
        quarter = min(max(quarter, 1), 4)
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 3
        end_year = year
        if end_month > 12:
            end_month = 1
            end_year = year + 1
        prev_quarter = 4 if quarter == 1 else quarter - 1
        prev_year = year - 1 if quarter == 1 else year
        prev_start_month = (prev_quarter - 1) * 3 + 1
        start_date = timezone.datetime(year, start_month, 1, tzinfo=tz)
        end_date = timezone.datetime(end_year, end_month, 1, tzinfo=tz)
        prev_start_date = timezone.datetime(prev_year, prev_start_month, 1, tzinfo=tz)
        prev_end_date = start_date
    elif filter_type == 'month':
        month = int(request.GET.get('month', now.month))
        start_date = timezone.datetime(year, month, 1, tzinfo=tz)
        next_month = (month % 12) + 1
        next_month_year = year + (1 if month == 12 else 0)
        end_date = timezone.datetime(next_month_year, next_month, 1, tzinfo=tz)
        prev_month = (month - 2) % 12 + 1
        prev_month_year = year - (1 if month == 1 else 0)
        prev_start_date = timezone.datetime(prev_month_year, prev_month, 1, tzinfo=tz)
        prev_end_date = start_date
    elif filter_type == 'week':
        week = int(request.GET.get('week', now.isocalendar()[1]))
        first_day_of_year = date(year, 1, 4)
        start_of_week1 = first_day_of_year - timedelta(days=first_day_of_year.isoweekday() - 1)
        start_date_dt = start_of_week1 + timedelta(weeks=week - 1)
        start_date = timezone.datetime.combine(start_date_dt, timezone.datetime.min.time(), tzinfo=tz)
        end_date = start_date + timedelta(days=7)
        prev_start_date = start_date - timedelta(days=7)
        prev_end_date = start_date
    else:
        start_date = timezone.datetime(year, 1, 1, tzinfo=tz)
        end_date = timezone.datetime(year + 1, 1, 1, tzinfo=tz)
        prev_start_date = timezone.datetime(year - 1, 1, 1, tzinfo=tz)
        prev_end_date = start_date

    return start_date, end_date, prev_start_date, prev_end_date, filter_type


def _build_recent_calendar_months(year: int, month: int, tz) -> list[dict[str, object]]:
    """Return month metadata for previous-previous, previous, and current month."""
    months: list[dict[str, object]] = []
    for offset in (2, 1, 0):
        month_index = (year * 12 + month - 1) - offset
        item_year = month_index // 12
        item_month = (month_index % 12) + 1
        next_month_index = month_index + 1
        next_year = next_month_index // 12
        next_month = (next_month_index % 12) + 1
        month_start = timezone.datetime(item_year, item_month, 1, tzinfo=tz)
        month_end = timezone.datetime(next_year, next_month, 1, tzinfo=tz)
        months.append({
            'key': f'{item_year:04d}-{item_month:02d}',
            'year': item_year,
            'month': item_month,
            'label': f'{item_month}月',
            'start': month_start,
            'end': month_end,
            'weekday_offset': month_start.weekday(),
            'days': (month_end.date() - month_start.date()).days,
        })
    return months


def _statistics_page_context(request: HttpRequest) -> dict[str, object]:
    default_filter_type = 'week'
    default_date: date = timezone.localdate()
    default_year = default_date.isocalendar()[0]
    default_week = default_date.isocalendar()[1]
    default_month = default_date.month

    context: dict[str, object] = {
        'default_filter_type': default_filter_type,
        'default_year': default_year,
        'default_month': default_month,
        'default_week': default_week,
        'default_date': default_date.isoformat(),
        'statistics_data_api_url': reverse('plugins:netbox_otnfaults:statistics_data'),
        'statistics_service_data_api_url': reverse('plugins:netbox_otnfaults:statistics_service_data'),
        'statistics_cable_break_map_url': reverse('plugins:netbox_otnfaults:statistics_cable_break_map'),
    }

    return context


class FaultStatisticsPageView(PermissionRequiredMixin, View):
    """
    故障多维统计与下钻展示页面 - 渲染主HTML
    """
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            'netbox_otnfaults/statistics_dashboard.html',
            _statistics_page_context(request),
        )




class FaultStatisticsDataAPI(PermissionRequiredMixin, View):
    """
    独立聚合接口。
    URL params:
      - filter_type: 'year', 'month', 'week'
      - year: int (e.g., 2024)
      - month: int (e.g., 10) 仅 filter_type=month 时使用
      - week: int (e.g., 42, ISO date) 仅 filter_type=week 时使用
    """
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request) -> JsonResponse:
        start_date, end_date, prev_start_date, prev_end_date, filter_type = _parse_time_range(request)
        now = timezone.localtime()

        # 先预抓取一段无过滤条件的全量当前期基础查询集，仅用于提取“总体情况面板” Banner 数据
        qs_all = OtnFault.objects.select_related('province', 'interruption_location_a').prefetch_related('interruption_location')
        all_current_qs = qs_all.filter(fault_occurrence_time__gte=start_date, fault_occurrence_time__lt=end_date)
        all_faults = list(all_current_qs)
        all_suspended_faults_count = qs_all.filter(fault_status=FaultStatusChoices.SUSPENDED).count()

        overall_faults = [
            f for f in all_faults
            if f.fault_category not in OVERALL_EXCLUDED_TOTAL_CATEGORIES
        ]
        overall_total_count = len(overall_faults)
        overall_category_stats = _build_fault_category_summary(overall_faults, now)
        other_overview = _build_other_fault_summary(all_faults, all_suspended_faults_count)
        physical_daily_start, physical_daily_end = _resolve_physical_daily_range(now)
        physical_daily_faults = list(
            qs_all.filter(
                fault_occurrence_time__gte=physical_daily_start,
                fault_occurrence_time__lt=physical_daily_end,
                fault_category=FaultCategoryChoices.FIBER_BREAK,
            ).exclude(
                fault_status=FaultStatusChoices.SUSPENDED
            )
        )
        physical_daily_stats = _build_physical_daily_fault_series(physical_daily_start, physical_daily_end, physical_daily_faults, now)

        # 提取当前期光缆中断故障
        physical_duration_boxplot_faults = list(get_cable_break_base_queryset(start_date, end_date))
        physical_duration_boxplot_stats = _build_physical_daily_fault_series(start_date, end_date, physical_duration_boxplot_faults, now)
        faults = physical_duration_boxplot_faults
        
        # 提取上一期故障并计算其 KPI
        prev_total_count = 0
        prev_total_duration = 0.0
        prev_long_faults = 0
        prev_repeat_faults = 0
        prev_avg_duration = 0.0
        prev_faults = []
        
        if prev_start_date and prev_end_date:
            prev_faults = list(get_cable_break_base_queryset(prev_start_date, prev_end_date))
            prev_total_count = len(prev_faults)
            
            if prev_faults:
                # 重复检测准备
                p_fiber_faults = [f for f in prev_faults if f.is_fiber_fault]
                if p_fiber_faults:
                    p_min_occ = min([f.fault_occurrence_time for f in p_fiber_faults])
                    p_check_start = p_min_occ - timedelta(days=60)
                    p_past_qs = OtnFault.objects.filter(
                        fault_occurrence_time__gte=p_check_start,
                        fault_occurrence_time__lt=prev_end_date,
                        fault_category__in=[FaultCategoryChoices.FIBER_BREAK, FaultCategoryChoices.FIBER_DEGRADATION, FaultCategoryChoices.FIBER_JITTER]
                    ).select_related('interruption_location_a').prefetch_related('interruption_location')
                    p_past_list = list(p_past_qs)
                else:
                    p_past_list = []
                p_z_cache = {pf.id: set(s.id for s in pf.interruption_location.all()) for pf in p_past_list}
                
                for f in prev_faults:
                    occ = f.fault_occurrence_time
                    rec = f.fault_recovery_time if f.fault_recovery_time else now
                    dur = (rec - occ).total_seconds() / 3600.0
                    prev_total_duration += dur
                    if dur >= 6.0:
                        prev_long_faults += 1
                    
                    is_r = False
                    if f.is_fiber_fault:
                        fz_ids = p_z_cache.get(f.id, set(s.id for s in f.interruption_location.all()))
                        for pf in p_past_list:
                            if pf.id != f.id and pf.fault_occurrence_time < f.fault_occurrence_time:
                                if (f.fault_occurrence_time - pf.fault_occurrence_time).days <= 60:
                                    if pf.interruption_location_a_id == f.interruption_location_a_id:
                                        if p_z_cache.get(pf.id, set()).intersection(fz_ids):
                                            is_r = True
                                            break
                        if is_r:
                            prev_repeat_faults += 1
            prev_avg_duration = prev_total_duration / prev_total_count if prev_total_count > 0 else 0.0
        
        # 1. 统计 KPI
        total_count = len(faults)
        total_duration_hours = 0.0
        long_faults_count = 0
        repeat_faults_count = 0
        
        # 为了检查重复，获取范围内所有光缆类故障过去60天的故障字典进行比对
        # 构建需比对重复的故障的子集（只查光纤中断/抖动/劣化）
        fiber_faults = [f for f in faults if f.is_fiber_fault]
        
        # 用预查过去60天的全量故障加速重复检测
        if fiber_faults:
            min_occurrence = min([f.fault_occurrence_time for f in fiber_faults])
            check_start = min_occurrence - timedelta(days=60)
            
            # 把当前范围内和此前60天的故障全部拿出来准备对比
            past_faults_qs = OtnFault.objects.filter(
                fault_occurrence_time__gte=check_start,
                fault_occurrence_time__lt=end_date if end_date else now,
                fault_category__in=[FaultCategoryChoices.FIBER_BREAK, 
                                    FaultCategoryChoices.FIBER_DEGRADATION, 
                                    FaultCategoryChoices.FIBER_JITTER]
            ).select_related('interruption_location_a').prefetch_related('interruption_location')
            
            past_faults_list = list(past_faults_qs)
        else:
            past_faults_list = []

        # 辅助字典提取Z端
        fault_z_sites_cache = {}
        for pf in past_faults_list:
            fault_z_sites_cache[pf.id] = set(s.id for s in pf.interruption_location.all())

        # Detail List (供下钻表结构)
        details = []

        # 统计图表维度
        resource_stats = {}
        province_stats = {}
        reason_stats = {}

        # 预先初始化所有的地区(作为省份展示)，保证没有故障的省份也显示为 0
        all_provinces = Region.objects.values_list('name', flat=True)
        for p_name in all_provinces:
            if p_name:
                province_stats[p_name] = {'count': 0, 'duration': 0.0}

        for fault in faults:
            # 持续时间计算
            occ_time = fault.fault_occurrence_time
            end_t = fault.fault_recovery_time if fault.fault_recovery_time else now
            
            duration_delta = end_t - occ_time
            duration_hours = duration_delta.total_seconds() / 3600.0
            
            total_duration_hours += duration_hours
            if duration_hours >= 6.0:
                long_faults_count += 1
                
            # 重复故障判断
            is_repeat = False
            if fault.is_fiber_fault:
                fault_z_site_ids = fault_z_sites_cache.get(fault.id, set(s.id for s in fault.interruption_location.all()))
                
                # 在 past_faults_list 中寻找符合条件的
                for pf in past_faults_list:
                    # 不能是自己，且发生时间符合区间
                    if pf.id != fault.id and pf.fault_occurrence_time < fault.fault_occurrence_time:
                        if (fault.fault_occurrence_time - pf.fault_occurrence_time) <= timedelta(days=60):
                            if pf.interruption_location_a_id == fault.interruption_location_a_id:
                                pf_z_site_ids = fault_z_sites_cache.get(pf.id, set())
                                if pf_z_site_ids.intersection(fault_z_site_ids):
                                    is_repeat = True
                                    break
                if is_repeat:
                    repeat_faults_count += 1

            # 填充图表分配
            # 1. 属性 (自建/协调/租赁/未填写)
            r_type = fault.resource_type or 'unfilled'
            r_type_display = fault.get_resource_type_display() if fault.resource_type else '未填写'
            if r_type_display not in resource_stats:
                resource_stats[r_type_display] = {'id': r_type, 'count': 0, 'duration': 0.0}
            resource_stats[r_type_display]['count'] += 1
            resource_stats[r_type_display]['duration'] += duration_hours

            # 2. 省份
            prov_name = fault.province.name if fault.province else '未知'
            if prov_name not in province_stats:
                province_stats[prov_name] = {'count': 0, 'duration': 0.0}
            province_stats[prov_name]['count'] += 1
            province_stats[prov_name]['duration'] += duration_hours

            # 3. 原因 (一级)
            reason = fault.get_interruption_reason_display() if fault.interruption_reason else '未填/未知'
            if reason not in reason_stats:
                reason_stats[reason] = {'count': 0, 'duration': 0.0}
            reason_stats[reason]['count'] += 1
            reason_stats[reason]['duration'] += duration_hours

            source_group = _source_group_for_fault(fault)
            if 6.0 <= duration_hours < 8.0:
                duration_bucket = '6-8小时'
            elif 8.0 <= duration_hours < 10.0:
                duration_bucket = '8-10小时'
            elif 10.0 <= duration_hours < 12.0:
                duration_bucket = '10-12小时'
            elif duration_hours >= 12.0:
                duration_bucket = '12小时以上'
            else:
                duration_bucket = ''

            occurrence_period = _occurrence_period_for_fault(fault)
            cause_group = '施工类' if reason == '施工' else '非施工类'
            duration_histogram_bucket = _duration_histogram_bucket_label(_duration_histogram_bucket_index(duration_hours))

            
            # 明细存储（仅返回精简信息给前端作本地过滤或列表展示)
            z_site_names = [s.name for s in fault.interruption_location.all()]
            
            details.append({
                'id': fault.id,
                'fault_number': fault.fault_number,
                'fault_occurrence_time': _format_local_datetime(occ_time),
                'fault_recovery_time': _format_local_datetime(fault.fault_recovery_time) if fault.fault_recovery_time else '未恢复',
                'duration': round(duration_hours, 2),
                'category': fault.get_fault_category_display(),
                'resource_type': r_type_display,
                'source_group': source_group,
                'province': prov_name,
                'reason': reason,
                'duration_bucket': duration_bucket,
                'duration_histogram_bucket': duration_histogram_bucket,
                'is_valid_duration': duration_hours > 0.5,
                'occurrence_period': occurrence_period,
                'cause_group': cause_group,
                'site_a': fault.interruption_location_a.name if fault.interruption_location_a else '',
                'site_z': ', '.join(z_site_names),
                'is_repeat': is_repeat,
                'is_long': duration_hours >= 6.0,
                'url': fault.get_absolute_url()
            })

        # 使用辅助函数计算当前期光缆中断概览
        cable_break_overview = _compute_cable_break_overview(faults, now)

        avg_duration_hours = total_duration_hours / total_count if total_count > 0 else 0.0

        # 计算上周期的全维度对比数据
        prev_overall_category_stats = _build_fault_category_summary([], now)
        prev_cable_break_overview = {}
        prev_other_overview = _build_other_fault_summary([], all_suspended_faults_count)
        if prev_start_date and prev_end_date:
            # 上周期全量故障（用于总体情况分类对比）
            prev_all_qs = qs_all.filter(fault_occurrence_time__gte=prev_start_date, fault_occurrence_time__lt=prev_end_date)
            prev_all_faults = list(prev_all_qs)
            prev_overall_faults = [
                f for f in prev_all_faults
                if f.fault_category not in OVERALL_EXCLUDED_TOTAL_CATEGORIES
            ]
            prev_overall_category_stats = _build_fault_category_summary(prev_overall_faults, now)
            prev_other_overview = _build_other_fault_summary(prev_all_faults, all_suspended_faults_count)

            # 上周期光缆中断概览（用于各子指标趋势对比）
            prev_cable_break_overview = _compute_cable_break_overview(prev_faults, now)

        # 为了展示准确的截止自然日（例如周日而非下周一，10月31日而非11月1日），展示日期需减去一天
        display_end_date_str = ''
        if end_date:
            display_end_date = end_date - timedelta(days=1)
            display_end_date_str = display_end_date.strftime('%Y-%m-%d')

        # 返回 JSON 结构
        return JsonResponse({
            'period': build_period_display(start_date, end_date, now),
            'kpis': {
                'total_count': overall_total_count,
                'total_duration': round(total_duration_hours, 2),
                'avg_duration': round(avg_duration_hours, 2),
                'long_faults_count': long_faults_count,
                'repeat_faults_count': repeat_faults_count,
            },
            'prev_kpis': {
                'total_count': prev_total_count,
                'total_duration': round(prev_total_duration, 2),
                'avg_duration': round(prev_avg_duration, 2),
                'long_faults_count': prev_long_faults,
                'repeat_faults_count': prev_repeat_faults,
            },
            'charts': {
                'resource': _build_resource_chart_data(resource_stats),
                'province': [{'name': k, 'value': v['count'], 'duration': round(v['duration'], 2)} for k, v in sorted(province_stats.items(), key=lambda item: item[1]['count'], reverse=True)],
                'reason': [{'name': k, 'value': v['count'], 'duration': round(v['duration'], 2)} for k, v in sorted(reason_stats.items(), key=lambda item: item[1]['count'], reverse=True)],
                'category': overall_category_stats,
                'physical_daily': physical_daily_stats,
                'physical_duration_boxplot': physical_duration_boxplot_stats,
            },
            'prev_charts': {
                'category': prev_overall_category_stats,
            },
            'cable_break_overview': cable_break_overview,
            'prev_cable_break_overview': prev_cable_break_overview,
            'other_overview': other_overview,
            'prev_other_overview': prev_other_overview,
            'details': details
        })





class ServiceStatisticsDataAPI(PermissionRequiredMixin, View):
    """
    业务故障统计聚合API。
    按业务（BareFiberService / CircuitService）聚合 OtnFaultImpact 数据，
    返回每个业务的统计卡片数据。
    """
    permission_required = 'netbox_otnfaults.view_otnfaultimpact'

    def get(self, request) -> JsonResponse:
        start_date, end_date, prev_start_date, prev_end_date, filter_type = _parse_time_range(request)
        now = timezone.localtime()
        selected_year = int(request.GET.get('year', start_date.year))
        tz = timezone.get_current_timezone()
        year_start = timezone.datetime(selected_year, 1, 1, tzinfo=tz)
        year_end = timezone.datetime(selected_year + 1, 1, 1, tzinfo=tz)
        calendar_year = int(request.GET.get('calendar_year', selected_year))
        calendar_month = int(request.GET.get('calendar_month', timezone.localtime(start_date).month))
        calendar_months = _build_recent_calendar_months(calendar_year, calendar_month, tz)
        calendar_start = calendar_months[0]['start']
        calendar_end = calendar_months[-1]['end']

        # 查询当前期的所有 FaultImpact
        impacts_qs = OtnFaultImpact.objects.select_related(
            'otn_fault', 'bare_fiber_service', 'circuit_service'
        ).filter(
            service_interruption_time__gte=start_date,
            service_interruption_time__lt=end_date
        )
        impacts = list(impacts_qs)
        yearly_impacts_qs = OtnFaultImpact.objects.select_related(
            'otn_fault', 'bare_fiber_service', 'circuit_service'
        ).filter(
            service_interruption_time__gte=year_start,
            service_interruption_time__lt=year_end
        )
        yearly_impacts = list(yearly_impacts_qs)
        calendar_impacts_qs = OtnFaultImpact.objects.select_related(
            'otn_fault', 'bare_fiber_service', 'circuit_service'
        ).filter(
            service_interruption_time__gte=calendar_start,
            service_interruption_time__lt=calendar_end
        )
        calendar_impacts = list(calendar_impacts_qs)

        # 计算周期总小时数（用于 SLA）
        period_total_hours: float = (end_date - start_date).total_seconds() / 3600.0

        # 按业务 key 聚合
        service_map: dict = {}  # key -> stats dict
        service_details: list[dict[str, str | int | float | bool]] = []

        for imp in impacts:
            # 确定业务标识和名称
            if imp.service_type == ServiceTypeChoices.BARE_FIBER and imp.bare_fiber_service:
                svc_key = f'bf_{imp.bare_fiber_service_id}'
                svc_name = imp.bare_fiber_service.name
                svc_type_label = '裸纤业务'
                svc_sort_rank = 0
            elif imp.service_type == ServiceTypeChoices.CIRCUIT and imp.circuit_service:
                svc_key = f'cs_{imp.circuit_service_id}'
                svc_name = imp.circuit_service.special_line_name or imp.circuit_service.name
                svc_type_label = '电路业务'
                svc_sort_rank = 1
            else:
                svc_key = f'unknown_{imp.id}'
                svc_name = str(imp)
                svc_type_label = '未知'
                svc_sort_rank = 2

            if svc_key not in service_map:
                monthly_stats = {month: {'count': 0, 'duration': 0.0} for month in range(1, 13)}
                service_map[svc_key] = {
                    'name': svc_name,
                    'type': svc_type_label,
                    'sort_rank': svc_sort_rank,
                    'count': 0,
                    'break_count': 0,   # 中断
                    'jitter_count': 0,  # 抖动
                    'degrade_count': 0, # 劣化
                    'other_count': 0,
                    'category_stats': {
                        label: {
                            'count': 0,
                            'duration': 0.0,
                        }
                        for _value, label, *_rest in FaultCategoryChoices.CHOICES
                    },
                    'monthly_stats': monthly_stats,
                    'interrupt_calendar': {
                        month_info['key']: {day: 0 for day in range(1, month_info['days'] + 1)}
                        for month_info in calendar_months
                    },
                    'total_duration': 0.0,
                    'long_count': 0,
                    'intervals': [],  # 用于 SLA 合并时段
                    'occurrence_times': [],  # 用于重复判断
                }

            stats = service_map[svc_key]
            stats['count'] += 1

            # 分类计数
            fault_cat = imp.otn_fault.fault_category if imp.otn_fault else None
            category_label = imp.otn_fault.get_fault_category_display() if imp.otn_fault else '未知'
            if category_label not in stats['category_stats']:
                stats['category_stats'][category_label] = {
                    'count': 0,
                    'duration': 0.0,
                }
            stats['category_stats'][category_label]['count'] += 1
            if fault_cat == FaultCategoryChoices.FIBER_BREAK:
                stats['break_count'] += 1
            elif fault_cat == FaultCategoryChoices.FIBER_JITTER:
                stats['jitter_count'] += 1
            elif fault_cat == FaultCategoryChoices.FIBER_DEGRADATION:
                stats['degrade_count'] += 1
            else:
                stats['other_count'] += 1

            # 业务中断时长
            svc_start = imp.service_interruption_time
            svc_end = imp.service_recovery_time if imp.service_recovery_time else now
            dur_hours = (svc_end - svc_start).total_seconds() / 3600.0
            stats['total_duration'] += dur_hours
            stats['category_stats'][category_label]['duration'] += dur_hours

            if dur_hours >= 6.0:
                stats['long_count'] += 1

            service_details.append({
                'id': imp.id,
                'service_key': svc_key,
                'service_name': svc_name,
                'service_type': svc_type_label,
                'fault_number': imp.otn_fault.fault_number if imp.otn_fault else '',
                'fault_category': imp.otn_fault.get_fault_category_display() if imp.otn_fault else '未知',
                'service_interruption_time': _format_local_datetime(svc_start),
                'service_recovery_time': _format_local_datetime(imp.service_recovery_time) if imp.service_recovery_time else '未恢复',
                'duration': round(dur_hours, 2),
                'is_long': dur_hours >= 6.0,
                'impact_url': imp.get_absolute_url(),
                'fault_url': imp.otn_fault.get_absolute_url() if imp.otn_fault else '',
            })

            # 记录时段供 SLA 计算（合并重叠）
            stats['intervals'].append((svc_start, svc_end))
            # 记录发生时间供重复判断
            stats['occurrence_times'].append(svc_start)

        for year_imp in yearly_impacts:
            if year_imp.service_type == ServiceTypeChoices.BARE_FIBER and year_imp.bare_fiber_service:
                svc_key = f'bf_{year_imp.bare_fiber_service_id}'
            elif year_imp.service_type == ServiceTypeChoices.CIRCUIT and year_imp.circuit_service:
                svc_key = f'cs_{year_imp.circuit_service_id}'
            else:
                svc_key = f'unknown_{year_imp.id}'
            if svc_key not in service_map:
                continue

            month_index = timezone.localtime(year_imp.service_interruption_time).month
            month_end = year_imp.service_recovery_time if year_imp.service_recovery_time else now
            month_dur_hours = (month_end - year_imp.service_interruption_time).total_seconds() / 3600.0
            stats = service_map[svc_key]
            stats['monthly_stats'][month_index]['count'] += 1
            stats['monthly_stats'][month_index]['duration'] += month_dur_hours

        for calendar_imp in calendar_impacts:
            if calendar_imp.service_type == ServiceTypeChoices.BARE_FIBER and calendar_imp.bare_fiber_service:
                svc_key = f'bf_{calendar_imp.bare_fiber_service_id}'
            elif calendar_imp.service_type == ServiceTypeChoices.CIRCUIT and calendar_imp.circuit_service:
                svc_key = f'cs_{calendar_imp.circuit_service_id}'
            else:
                svc_key = f'unknown_{calendar_imp.id}'
            if svc_key not in service_map:
                continue

            calendar_day = timezone.localtime(calendar_imp.service_interruption_time)
            calendar_key = f'{calendar_day.year:04d}-{calendar_day.month:02d}'
            stats = service_map[svc_key]
            if calendar_key in stats['interrupt_calendar'] and calendar_day.day in stats['interrupt_calendar'][calendar_key]:
                stats['interrupt_calendar'][calendar_key][calendar_day.day] += 1

        # 构建返回结果
        services_result = []
        for svc_key, stats in service_map.items():
            count = stats['count']
            total_dur = stats['total_duration']
            avg_dur = total_dur / count if count > 0 else 0.0

            # 重复故障：同一业务 60 天内有多次影响
            repeat_count = 0
            times_sorted = sorted(stats['occurrence_times'])
            for i in range(1, len(times_sorted)):
                if (times_sorted[i] - times_sorted[i - 1]).days <= 60:
                    repeat_count += 1

            # SLA：合并重叠时段后计算不可用总时长
            intervals = sorted(stats['intervals'], key=lambda x: x[0])
            merged: list = []
            for s, e in intervals:
                if merged and s <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], e))
                else:
                    merged.append((s, e))
            unavailable_hours = sum(
                (e - s).total_seconds() / 3600.0 for s, e in merged
            )
            sla = ((period_total_hours - unavailable_hours) / period_total_hours * 100.0) if period_total_hours > 0 else 100.0
            sla = max(0.0, sla)  # 防止负值

            category_order = {
                label: index for index, (_value, label, *_rest) in enumerate(FaultCategoryChoices.CHOICES)
            }
            category_stats_payload = [
                {
                    'label': label,
                    'count': category_stats['count'],
                    'duration': round(category_stats['duration'], 2),
                }
                for label, category_stats in sorted(
                    stats['category_stats'].items(),
                    key=lambda item: (category_order.get(item[0], len(category_order)), item[0])
                )
            ]
            monthly_stats_payload = [
                {
                    'month': month,
                    'label': f'{month}月',
                    'count': month_stats['count'],
                    'duration': round(month_stats['duration'], 2),
                }
                for month, month_stats in stats['monthly_stats'].items()
            ]
            interrupt_calendar_payload = [
                {
                    'key': month_info['key'],
                    'label': month_info['label'],
                    'year': month_info['year'],
                    'month': month_info['month'],
                    'weekday_offset': month_info['weekday_offset'],
                    'days': [
                        {
                            'day': day,
                            'count': stats['interrupt_calendar'][month_info['key']][day],
                        }
                        for day in range(1, month_info['days'] + 1)
                    ],
                }
                for month_info in calendar_months
            ]

            services_result.append({
                'key': svc_key,
                'name': stats['name'],
                'type': stats['type'],
                'sort_rank': stats['sort_rank'],
                'count': count,
                'break_count': stats['break_count'],
                'jitter_count': stats['jitter_count'],
                'degrade_count': stats['degrade_count'],
                'other_count': stats['other_count'],
                'category_stats': category_stats_payload,
                'monthly_stats': monthly_stats_payload,
                'interrupt_calendar': interrupt_calendar_payload,
                'total_duration': round(total_dur, 2),
                'avg_duration': round(avg_dur, 2),
                'long_count': stats['long_count'],
                'repeat_count': repeat_count,
                'sla': round(sla, 4),
            })

        # 按业务类型分组：裸纤在前，电路在后；组内按故障总数降序，名称升序兜底。
        services_result.sort(key=lambda x: (x['sort_rank'], -x['count'], x['name']))
        for result in services_result:
            result.pop('sort_rank', None)

        # 展示日期
        display_end_date_str = ''
        if end_date:
            display_end_date = end_date - timedelta(days=1)
            display_end_date_str = display_end_date.strftime('%Y-%m-%d')

        return JsonResponse({
            'period': build_period_display(start_date, end_date, now),
            'period_total_hours': round(period_total_hours, 2),
            'services': services_result,
            'details': service_details,
        })

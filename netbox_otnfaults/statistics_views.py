"""
OTN 故障统计展示页面 - 后端视图

提供独立的统计看板以及聚合API（兼容ECharts等前端工具及下钻查询）。
"""
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q, F, Func, DurationField, ExpressionWrapper, QuerySet, Exists, OuterRef
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import View
from datetime import timedelta, date
from django.db.models.functions import TruncDate, Coalesce, Cast
from decimal import Decimal
import math
from urllib.parse import quote
from typing import Any

from .models import (
    OtnFault, OtnFaultImpact, BareFiberService,
    FaultCategoryChoices, ResourceTypeChoices, CableTypeChoices,
    ServiceTypeChoices, FaultStatusChoices, BusinessImpactChoices,
    PowerFaultImpactChoices, CutoverTask
)
from dcim.models import Region
from .statistics_period import build_period_display
from .utils import detect_repeat_faults


def _annotate_class_i_business_impact(queryset: QuerySet) -> QuerySet:
    class_i_impact_exists = OtnFaultImpact.objects.filter(
        otn_fault_id=OuterRef("pk"),
        business_impact=BusinessImpactChoices.INTERRUPTED,
    ).filter(
        Q(service_type=ServiceTypeChoices.BARE_FIBER)
        | Q(
            service_type=ServiceTypeChoices.CIRCUIT,
            circuit_service__is_important=True,
        )
    )
    return queryset.annotate(has_class_i_business_impact=Exists(class_i_impact_exists))


def _get_impact_level_display(fault: OtnFault, has_class_i_business_impact: bool) -> str:
    if fault.source_cutover_task_id is not None:
        return "割接排除"
    if fault.fault_status == FaultStatusChoices.SUSPENDED or fault.is_suspended:
        return "V类"
    
    is_class_i_fiber = (
        fault.fault_category == FaultCategoryChoices.FIBER_BREAK 
        and has_class_i_business_impact
    )
    is_class_i_power = (
        fault.fault_category == FaultCategoryChoices.POWER_FAULT 
        and fault.power_fault_impact == PowerFaultImpactChoices.HOSTED
    )
    is_class_i_ac = (
        fault.fault_category == FaultCategoryChoices.AC_FAULT 
        and getattr(fault, 'ac_fault_is_class_i', False)
    )
    is_class_i_device = (
        fault.fault_category == FaultCategoryChoices.DEVICE_FAULT 
        and getattr(fault, 'device_fault_is_class_i', False)
    )
    
    if is_class_i_fiber or is_class_i_power or is_class_i_ac or is_class_i_device:
        return "I类"
        
    if fault.fault_category == FaultCategoryChoices.FIBER_BREAK:
        return "II类"
        
    if fault.fault_category in [
        FaultCategoryChoices.POWER_FAULT,
        FaultCategoryChoices.AC_FAULT,
        FaultCategoryChoices.DEVICE_FAULT
    ]:
        return "III类"
        
    if fault.fault_category in [
        FaultCategoryChoices.FIBER_DEGRADATION,
        FaultCategoryChoices.FIBER_JITTER
    ]:
        return "IV类"
        
    return "未知"


# 声明等级 Q 查询条件组合
Q_NOT_CUTOVER = Q(source_cutover_task__isnull=True)
Q_NOT_SUSPENDED = ~Q(fault_status=FaultStatusChoices.SUSPENDED) & Q(is_suspended=False)

Q_CLASS_V = Q_NOT_CUTOVER & (Q(fault_status=FaultStatusChoices.SUSPENDED) | Q(is_suspended=True))

Q_CLASS_IV = Q_NOT_CUTOVER & Q_NOT_SUSPENDED & Q(fault_category__in=[
    FaultCategoryChoices.FIBER_DEGRADATION, 
    FaultCategoryChoices.FIBER_JITTER
])

Q_CLASS_I = Q_NOT_CUTOVER & Q_NOT_SUSPENDED & (
    (Q(fault_category=FaultCategoryChoices.FIBER_BREAK) & Q(has_class_i_business_impact=True))
    | Q(fault_category=FaultCategoryChoices.POWER_FAULT, power_fault_impact=PowerFaultImpactChoices.HOSTED)
    | Q(fault_category=FaultCategoryChoices.AC_FAULT, ac_fault_is_class_i=True)
    | Q(fault_category=FaultCategoryChoices.DEVICE_FAULT, device_fault_is_class_i=True)
)

Q_CLASS_II = Q_NOT_CUTOVER & Q_NOT_SUSPENDED & Q(fault_category=FaultCategoryChoices.FIBER_BREAK) & Q(has_class_i_business_impact=False)

Q_CLASS_III = Q_NOT_CUTOVER & Q_NOT_SUSPENDED & (
    (Q(fault_category=FaultCategoryChoices.POWER_FAULT) & ~Q(power_fault_impact=PowerFaultImpactChoices.HOSTED))
    | (Q(fault_category=FaultCategoryChoices.AC_FAULT) & Q(ac_fault_is_class_i=False))
    | (Q(fault_category=FaultCategoryChoices.DEVICE_FAULT) & Q(device_fault_is_class_i=False))
)

Q_CLASS_I_II = Q_CLASS_I | Q_CLASS_II
Q_CLASS_TOTAL = Q_NOT_CUTOVER


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

BRANCH_PROVINCE_NAMES: list[str] = ['浙江', '山东', '内蒙', '陕西', '四川', '江西']

BRANCH_PROVINCE_PATH_LENGTHS: dict[str, float] = {
    '江西': 3545.0,
    '浙江': 2804.0,
    '陕西': 2182.0,
    '山东': 1464.0,
    '四川': 985.0,
    '内蒙': 972.0,
}

BRANCH_PROVINCE_ALIASES: dict[str, str] = {
    '浙江': '浙江',
    '山东': '山东',
    '内蒙': '内蒙',
    '内蒙古': '内蒙',
    '陕西': '陕西',
    '四川': '四川',
    '江西': '江西',
}

BRANCH_PERFORMANCE_DEDUCTION_LABELS: dict[str, str] = {
    'frequency': '频次',
    'duration': '历时',
    'valid_duration': '有效平均',
    'severity': '长时/超时',
    'repeat': '重复',
    'trend': '趋势',
}

EXCLUDED_HANDLING_UNITS: set[str] = {
    '山东瑞阳云技术有限公司',
    '嘉兴广信信息科技有限公司',
    '杭州骏云科技有限公司',
    '上海信智通网络技术有限公司',
}


def _should_exclude_for_branch(fault) -> bool:
    """如果在统计子公司数据时需要排除该故障"""
    if fault.handling_unit_id:
        try:
            return fault.handling_unit.name in EXCLUDED_HANDLING_UNITS
        except Exception:
            return False
    return False


def _is_branch_company_fault(fault) -> bool:
    return _branch_province_for_fault(fault) in BRANCH_PROVINCE_NAMES and not _should_exclude_for_branch(fault)


def truncate_sla(value: float) -> float:
    return math.trunc(value * 100.0) / 100.0


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


def _build_other_fault_summary(
    faults: list,
    suspended_faults_count: int,
    suspended_faults_total_count: int | None = None,
) -> dict[str, int]:
    return {
        'fiber_degradation': sum(1 for f in faults if f.fault_category == FaultCategoryChoices.FIBER_DEGRADATION),
        'fiber_jitter': sum(1 for f in faults if f.fault_category == FaultCategoryChoices.FIBER_JITTER),
        'suspended_faults': suspended_faults_count,
        'suspended_faults_total': suspended_faults_total_count if suspended_faults_total_count is not None else suspended_faults_count,
    }


def _is_non_suspended_fault(fault) -> bool:
    return (
        fault.fault_status != FaultStatusChoices.SUSPENDED
        and not fault.is_suspended
    )


def _suspended_fault_q() -> Q:
    return Q(fault_status=FaultStatusChoices.SUSPENDED) | Q(is_suspended=True)


def get_cable_break_base_queryset(start_date, end_date) -> QuerySet:
    """Return the shared cable-break queryset used by statistics and map views."""
    return (
        OtnFault.objects.select_related('province', 'interruption_location_a', 'handling_unit')
        .prefetch_related('interruption_location')
        .filter(
            fault_occurrence_time__gte=start_date,
            fault_occurrence_time__lt=end_date,
            fault_category=FaultCategoryChoices.FIBER_BREAK,
        )
        .filter(is_suspended=False)
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
        and _is_non_suspended_fault(f)
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


def _normalize_branch_province_name(name: str | None) -> str | None:
    if not name:
        return None
    normalized = str(name).strip()
    for suffix in ('省', '市', '自治区', '回族自治区', '壮族自治区', '维吾尔自治区'):
        normalized = normalized.replace(suffix, '')
    for alias, province in BRANCH_PROVINCE_ALIASES.items():
        if normalized.startswith(alias):
            return province
    return None


def _branch_province_for_fault(fault) -> str | None:
    province_name = fault.province.name if getattr(fault, 'province', None) else None
    return _normalize_branch_province_name(province_name)


def _duration_hours_for_fault(fault, now) -> float:
    if not fault.fault_occurrence_time:
        return 0.0
    end_t = fault.fault_recovery_time if fault.fault_recovery_time else now
    return (end_t - fault.fault_occurrence_time).total_seconds() / 3600.0


def _per_1000km(value: float, length_km: float) -> float:
    if length_km <= 0:
        return 0.0
    return round(value * 1000.0 / length_km, 2)


def _build_branch_week_ranges(year_start, year_end) -> list[dict[str, str]]:
    ranges: list[dict[str, str]] = []
    cursor = year_start.date()
    end_day = year_end.date()
    while cursor < end_day:
        week_end = min(cursor + timedelta(days=7), end_day)
        ranges.append({
            'key': cursor.isoformat(),
            'label': f"{cursor.month}/{cursor.day}",
            'start': cursor.isoformat(),
            'end': (week_end - timedelta(days=1)).isoformat(),
        })
        cursor = week_end
    return ranges


def _count_repeat_fiber_faults(faults: list, end_date, now) -> int:
    fiber_faults = [
        fault for fault in faults
        if getattr(fault, 'is_fiber_fault', False) and fault.fault_occurrence_time
    ]
    if not fiber_faults:
        return 0

    min_occurrence = min(fault.fault_occurrence_time for fault in fiber_faults)
    check_start = min_occurrence - timedelta(days=60)
    comparison_end = end_date if end_date else now
    comparison_faults = list(
        OtnFault.objects.filter(
            fault_occurrence_time__gte=check_start,
            fault_occurrence_time__lt=comparison_end,
            fault_category__in=[
                FaultCategoryChoices.FIBER_BREAK,
                FaultCategoryChoices.FIBER_DEGRADATION,
                FaultCategoryChoices.FIBER_JITTER,
            ],
        )
        .select_related('interruption_location_a')
        .prefetch_related('interruption_location')
    )
    z_sites_cache = {
        fault.id: set(site.id for site in fault.interruption_location.all())
        for fault in comparison_faults
    }

    repeat_count = 0
    for fault in fiber_faults:
        fault_z_site_ids = z_sites_cache.get(
            fault.id,
            set(site.id for site in fault.interruption_location.all()),
        )
        for previous_fault in comparison_faults:
            if previous_fault.id == fault.id:
                continue
            if previous_fault.fault_occurrence_time >= fault.fault_occurrence_time:
                continue
            if (fault.fault_occurrence_time - previous_fault.fault_occurrence_time) > timedelta(days=60):
                continue
            if previous_fault.interruption_location_a_id != fault.interruption_location_a_id:
                continue
            if z_sites_cache.get(previous_fault.id, set()).intersection(fault_z_site_ids):
                repeat_count += 1
                break
    return repeat_count


def _classify_branch_fault_responsibility(fault) -> dict[str, object]:
    if fault.interruption_reason == 'natural_disaster' or fault.interruption_reason_detail == 'planned_reporting':
        return {
            'weight': 0.0,
            'scope': 'overall_only',
            'label': '仅全量计入',
            'basis': '自然灾害或计划报备不纳入责任考核',
        }
    if fault.resource_type == ResourceTypeChoices.LEASED or fault.interruption_reason in {'construction', 'traffic_accident'}:
        return {
            'weight': 0.5,
            'scope': 'weighted',
            'label': '降权计入',
            'basis': '租赁资源、第三方施工或交通事故按 50% 计入责任考核',
        }
    return {
        'weight': 1.0,
        'scope': 'responsibility',
        'label': '责任计入',
        'basis': '按责任口径全量计入',
    }


def _calculate_branch_performance_score(metrics: dict[str, float]) -> dict[str, object]:
    deductions = {
        'frequency': min(30.0, metrics.get('count_per_1000km', 0.0) * 1.8),
        'duration': min(25.0, metrics.get('duration_per_1000km', 0.0) * 0.4),
        'valid_duration': min(15.0, max(0.0, metrics.get('valid_duration', 0.0) - 4.0) * 3.0),
        'severity': min(
            15.0,
            (metrics.get('long_count', 0.0) * 2.0)
            + (metrics.get('timeout_count', 0.0) * 2.0)
            + (metrics.get('open_count', 0.0) * 3.0),
        ),
        'repeat': min(10.0, metrics.get('repeat_count', 0.0) * 2.0),
        'trend': min(5.0, max(0.0, metrics.get('trend_delta', 0.0)) * 2.0),
    }
    total_deduction = sum(deductions.values())
    score = max(0.0, round(100.0 - total_deduction, 2))
    if score >= 90.0:
        grade = '优秀'
        status = 'stable'
    elif score >= 80.0:
        grade = '良好'
        status = 'good'
    elif score >= 70.0:
        grade = '关注'
        status = 'warning'
    else:
        grade = '待整改'
        status = 'danger'
    return {
        'score': score,
        'grade': grade,
        'status': status,
        'deductions': [
            {
                'key': key,
                'label': BRANCH_PERFORMANCE_DEDUCTION_LABELS[key],
                'value': round(value, 2),
            }
            for key, value in deductions.items()
        ],
        'total_deduction': round(total_deduction, 2),
    }


def _build_repeat_fault_id_set(faults: list, end_date, now) -> set[int]:
    fiber_faults = [
        fault for fault in faults
        if getattr(fault, 'is_fiber_fault', False) and fault.fault_occurrence_time
    ]
    if not fiber_faults:
        return set()

    min_occurrence = min(fault.fault_occurrence_time for fault in fiber_faults)
    check_start = min_occurrence - timedelta(days=60)
    comparison_end = end_date if end_date else now
    comparison_faults = list(
        OtnFault.objects.filter(
            fault_occurrence_time__gte=check_start,
            fault_occurrence_time__lt=comparison_end,
            fault_category__in=[
                FaultCategoryChoices.FIBER_BREAK,
                FaultCategoryChoices.FIBER_DEGRADATION,
                FaultCategoryChoices.FIBER_JITTER,
            ],
        )
        .select_related('interruption_location_a')
        .prefetch_related('interruption_location')
    )
    z_sites_cache = {
        fault.id: set(site.id for site in fault.interruption_location.all())
        for fault in comparison_faults
    }

    repeat_ids: set[int] = set()
    for fault in fiber_faults:
        fault_z_site_ids = z_sites_cache.get(
            fault.id,
            set(site.id for site in fault.interruption_location.all()),
        )
        for previous_fault in comparison_faults:
            if previous_fault.id == fault.id:
                continue
            if previous_fault.fault_occurrence_time >= fault.fault_occurrence_time:
                continue
            if (fault.fault_occurrence_time - previous_fault.fault_occurrence_time) > timedelta(days=60):
                continue
            if previous_fault.interruption_location_a_id != fault.interruption_location_a_id:
                continue
            if z_sites_cache.get(previous_fault.id, set()).intersection(fault_z_site_ids):
                repeat_ids.add(fault.id)
                break
    return repeat_ids


def _empty_branch_performance_metrics(length_km: float) -> dict[str, float]:
    return {
        'count': 0.0,
        'duration': 0.0,
        'valid_duration': 0.0,
        'valid_duration_total': 0.0,
        'valid_count': 0.0,
        'count_per_1000km': 0.0,
        'duration_per_1000km': 0.0,
        'long_count': 0.0,
        'timeout_count': 0.0,
        'repeat_count': 0.0,
        'open_count': 0.0,
        'path_length': length_km,
    }


def _finalize_branch_performance_metrics(metrics: dict[str, float], length_km: float) -> dict[str, float]:
    valid_count = metrics.get('valid_count', 0.0)
    valid_duration_total = metrics.get('valid_duration_total', 0.0)
    metrics['valid_duration'] = round(valid_duration_total / valid_count, 2) if valid_count > 0 else 0.0
    metrics['count_per_1000km'] = _per_1000km(metrics.get('count', 0.0), length_km)
    metrics['duration_per_1000km'] = _per_1000km(metrics.get('duration', 0.0), length_km)
    return {
        key: round(value, 2) if isinstance(value, float) else value
        for key, value in metrics.items()
    }


def _build_empty_branch_performance_calendar_stats(
    calendar_months: list[dict[str, object]],
    calendar_full_months: list[dict[str, object]],
) -> dict[str, object]:
    return {
        'monthly_stats': {
            month: {'count': 0, 'duration': 0.0}
            for month in range(1, 13)
        },
        'interrupt_calendar': {
            str(month_info['key']): {
                day: 0
                for day in range(1, int(month_info['days']) + 1)
            }
            for month_info in calendar_months
        },
        'interrupt_calendar_full': {
            str(month_info['key']): {
                day: 0
                for day in range(1, int(month_info['days']) + 1)
            }
            for month_info in calendar_full_months
        },
    }


def _build_branch_performance_calendar_payload(
    month_info_list: list[dict[str, object]],
    calendar_counts: dict[str, dict[int, int]],
) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for month_info in month_info_list:
        month_key = str(month_info['key'])
        day_counts = calendar_counts.get(month_key, {})
        payload.append({
            'key': month_key,
            'label': month_info['label'],
            'weekday_offset': month_info['weekday_offset'],
            'days': [
                {'day': day, 'count': day_counts.get(day, 0)}
                for day in range(1, int(month_info['days']) + 1)
            ],
        })
    return payload


def _build_branch_performance_bare_fiber_annual_stats(
    year_start,
    year_end,
    now,
) -> dict[str, dict[str, float | int]]:
    stats: dict[str, dict[str, float | int]] = {
        province: {
            'total_count': 0,
            'distinct_count': 0,
            'total_duration': 0.0,
            'distinct_duration': 0.0,
        }
        for province in BRANCH_PROVINCE_NAMES
    }
    fault_durations: dict[str, dict[int, float]] = {
        province: {}
        for province in BRANCH_PROVINCE_NAMES
    }
    impacts = OtnFaultImpact.objects.select_related(
        'otn_fault',
        'otn_fault__province',
        'otn_fault__handling_unit',
    ).filter(
        service_interruption_time__gte=year_start,
        service_interruption_time__lt=year_end,
        service_type=ServiceTypeChoices.BARE_FIBER,
        otn_fault__is_suspended=False,
    ).exclude(
        otn_fault__fault_status=FaultStatusChoices.SUSPENDED,
    )

    for imp in impacts:
        if imp.business_impact == BusinessImpactChoices.NOT_INTERRUPTED:
            continue

        fault = imp.otn_fault
        province = _branch_province_for_fault(fault)
        if province not in BRANCH_PROVINCE_NAMES or _should_exclude_for_branch(fault):
            continue

        is_rectification_planned = (
            fault.interruption_reason == 'cable_rectification' and
            fault.interruption_reason_detail == 'planned_reporting'
        )
        is_approved = imp.coordination_status == 'approved'
        if is_rectification_planned and is_approved:
            continue

        end_t = imp.service_recovery_time if imp.service_recovery_time else now
        duration_hours = (end_t - imp.service_interruption_time).total_seconds() / 3600.0
        stats[province]['total_count'] += 1
        stats[province]['total_duration'] += duration_hours
        if imp.otn_fault_id:
            fault_durations[province][imp.otn_fault_id] = max(
                fault_durations[province].get(imp.otn_fault_id, 0.0),
                duration_hours,
            )

    for province in BRANCH_PROVINCE_NAMES:
        durations = fault_durations[province].values()
        stats[province]['distinct_count'] = len(fault_durations[province])
        stats[province]['total_duration'] = round(float(stats[province]['total_duration']), 2)
        stats[province]['distinct_duration'] = round(sum(durations), 2)

    return stats


def _build_branch_company_performance_cards(
    branch_faults: list,
    year_faults: list,
    year_all_faults: list,
    path_lengths: dict[str, float],
    calendar_months: list[dict[str, object]],
    calendar_full_months: list[dict[str, object]],
    start_date,
    end_date,
    now,
) -> list[dict[str, object]]:
    repeat_fault_ids = _build_repeat_fault_id_set(branch_faults, end_date, now)
    fault_groups: dict[str, list] = {province: [] for province in BRANCH_PROVINCE_NAMES}
    for fault in branch_faults:
        province = _branch_province_for_fault(fault)
        if province in fault_groups:
            fault_groups[province].append(fault)

    calendar_stats: dict[str, dict[str, object]] = {
        province: _build_empty_branch_performance_calendar_stats(calendar_months, calendar_full_months)
        for province in BRANCH_PROVINCE_NAMES
    }
    for fault in year_faults:
        province = _branch_province_for_fault(fault)
        if province not in calendar_stats or not fault.fault_occurrence_time:
            continue
        occurrence = timezone.localtime(fault.fault_occurrence_time)
        duration_hours = _duration_hours_for_fault(fault, now)
        monthly_stats = calendar_stats[province]['monthly_stats']
        monthly_stats[occurrence.month]['count'] += 1
        monthly_stats[occurrence.month]['duration'] += duration_hours
        month_key = f'{occurrence.year:04d}-{occurrence.month:02d}'
        interrupt_calendar = calendar_stats[province]['interrupt_calendar']
        if month_key in interrupt_calendar and occurrence.day in interrupt_calendar[month_key]:
            interrupt_calendar[month_key][occurrence.day] += 1
        interrupt_calendar_full = calendar_stats[province]['interrupt_calendar_full']
        if month_key in interrupt_calendar_full and occurrence.day in interrupt_calendar_full[month_key]:
            interrupt_calendar_full[month_key][occurrence.day] += 1

    tz = timezone.get_current_timezone()
    selected_year = start_date.year
    year_start = timezone.datetime(selected_year, 1, 1, tzinfo=tz)
    year_end = now if now.year == selected_year else timezone.datetime(selected_year + 1, 1, 1, tzinfo=tz)
    week_ranges = _build_branch_week_ranges(year_start, year_end)
    week_labels = [week['label'] for week in week_ranges]
    bare_fiber_annual_stats = _build_branch_performance_bare_fiber_annual_stats(year_start, year_end, now)
    year_fault_groups: dict[str, list] = {province: [] for province in BRANCH_PROVINCE_NAMES}
    for fault in year_all_faults:
        province = _branch_province_for_fault(fault)
        if province in year_fault_groups:
            year_fault_groups[province].append(fault)
    year_cable_break_groups: dict[str, list] = {province: [] for province in BRANCH_PROVINCE_NAMES}
    for fault in year_faults:
        province = _branch_province_for_fault(fault)
        if province in year_cable_break_groups:
            year_cable_break_groups[province].append(fault)
    year_repeat_fault_ids = _build_repeat_fault_id_set(year_faults, year_end, now)

    cards: list[dict[str, object]] = []
    for province in BRANCH_PROVINCE_NAMES:
        length_km = path_lengths.get(province, 0.0)
        responsibility_metrics = _empty_branch_performance_metrics(length_km)
        overall_metrics = _empty_branch_performance_metrics(length_km)
        responsibility_reason_counts: dict[str, float] = {}
        overall_reason_counts: dict[str, int] = {}
        responsibility_basis: dict[str, int] = {'责任计入': 0, '降权计入': 0, '仅全量计入': 0}

        for fault in fault_groups[province]:
            duration_hours = _duration_hours_for_fault(fault, now)
            weight = float(_classify_branch_fault_responsibility(fault)['weight'])
            responsibility_label = str(_classify_branch_fault_responsibility(fault)['label'])
            responsibility_basis[responsibility_label] = responsibility_basis.get(responsibility_label, 0) + 1
            reason = fault.get_interruption_reason_display() if fault.interruption_reason else '未填/未知'

            overall_metrics['count'] += 1.0
            overall_metrics['duration'] += duration_hours
            if duration_hours > 0.5:
                overall_metrics['valid_duration_total'] += duration_hours
                overall_metrics['valid_count'] += 1.0
            if duration_hours >= 6.0:
                overall_metrics['long_count'] += 1.0
            if getattr(fault, 'timeout', False):
                overall_metrics['timeout_count'] += 1.0
            if not getattr(fault, 'fault_recovery_time', None):
                overall_metrics['open_count'] += 1.0
            if fault.id in repeat_fault_ids:
                overall_metrics['repeat_count'] += 1.0
            overall_reason_counts[reason] = overall_reason_counts.get(reason, 0) + 1

            if weight > 0:
                responsibility_metrics['count'] += weight
                responsibility_metrics['duration'] += duration_hours * weight
                if duration_hours > 0.5:
                    responsibility_metrics['valid_duration_total'] += duration_hours * weight
                    responsibility_metrics['valid_count'] += weight
                if duration_hours >= 6.0:
                    responsibility_metrics['long_count'] += weight
                if getattr(fault, 'timeout', False):
                    responsibility_metrics['timeout_count'] += weight
                if not getattr(fault, 'fault_recovery_time', None):
                    responsibility_metrics['open_count'] += weight
                if fault.id in repeat_fault_ids:
                    responsibility_metrics['repeat_count'] += weight
                responsibility_reason_counts[reason] = responsibility_reason_counts.get(reason, 0.0) + weight

        responsibility_metrics = _finalize_branch_performance_metrics(responsibility_metrics, length_km)
        overall_metrics = _finalize_branch_performance_metrics(overall_metrics, length_km)
        responsibility_score = _calculate_branch_performance_score(responsibility_metrics)
        overall_score = _calculate_branch_performance_score(overall_metrics)
        province_calendar_stats = calendar_stats[province]
        province_monthly_stats = province_calendar_stats['monthly_stats']
        cable_break_annual_faults = year_cable_break_groups[province]
        cable_break_durations = [
            _duration_hours_for_fault(fault, now)
            for fault in cable_break_annual_faults
        ]
        cable_break_duration_total = sum(cable_break_durations)
        cable_break_valid_durations = [
            duration
            for duration in cable_break_durations
            if duration > 0.5
        ]
        cable_break_valid_avg_duration = (
            sum(cable_break_valid_durations) / len(cable_break_valid_durations)
            if cable_break_valid_durations else 0.0
        )
        cable_break_long_count = sum(
            1
            for duration in cable_break_durations
            if duration >= 6.0
        )
        cable_break_repeat_count = sum(
            1
            for fault in cable_break_annual_faults
            if fault.id in year_repeat_fault_ids
        )
        power_faults = [
            fault for fault in year_fault_groups[province]
            if fault.fault_category == FaultCategoryChoices.POWER_FAULT
            and _is_non_suspended_fault(fault)
        ]
        power_hosted_count = sum(
            1
            for fault in power_faults
            if getattr(fault, 'power_fault_impact', None) == PowerFaultImpactChoices.HOSTED
        )
        cards.append({
            'province': province,
            'label': f'{province}分公司',
            'responsibility_score': responsibility_score['score'],
            'overall_score': overall_score['score'],
            'grade': responsibility_score['grade'],
            'status': responsibility_score['status'],
            'deductions': responsibility_score['deductions'],
            'responsibility_metrics': responsibility_metrics,
            'overall_metrics': overall_metrics,
            'responsibility_reason_top3': _sorted_count_items(responsibility_reason_counts)[:3],
            'overall_reason_top3': _sorted_count_items(overall_reason_counts)[:3],
            'annual_stats': {
                'year': selected_year,
                'bare_fiber': bare_fiber_annual_stats.get(province, {}),
                'cable_break': {
                    'total_count': len(cable_break_annual_faults),
                    'count_per_1000km': _per_1000km(len(cable_break_annual_faults), length_km),
                    'total_duration': round(cable_break_duration_total, 2),
                    'duration_per_1000km': _per_1000km(cable_break_duration_total, length_km),
                    'valid_avg_duration': round(cable_break_valid_avg_duration, 2),
                    'long_count': cable_break_long_count,
                    'repeat_count': cable_break_repeat_count,
                },
                'power': {
                    'total_count': len(power_faults),
                    'hosted_count': power_hosted_count,
                },
            },
            'monthly_stats': [
                {
                    'month': month,
                    'label': f'{month}月',
                    'count': int(province_monthly_stats[month]['count']),
                    'duration': round(float(province_monthly_stats[month]['duration']), 2),
                    'count_per_1000km': _per_1000km(province_monthly_stats[month]['count'], length_km),
                    'duration_per_1000km': _per_1000km(province_monthly_stats[month]['duration'], length_km),
                }
                for month in range(1, 13)
            ],
            'interrupt_calendar': _build_branch_performance_calendar_payload(
                calendar_months,
                province_calendar_stats['interrupt_calendar'],
            ),
            'interrupt_calendar_full': _build_branch_performance_calendar_payload(
                calendar_full_months,
                province_calendar_stats['interrupt_calendar_full'],
            ),
            'weekly_trend': {
                'labels': week_labels,
                'responsibility_scores': [],
                'overall_scores': [],
            },
            'responsibility_basis': [
                {'label': label, 'count': count}
                for label, count in responsibility_basis.items()
            ],
        })
    cards.sort(key=lambda card: card['annual_stats']['cable_break']['count_per_1000km'], reverse=True)
    return cards


def _build_branch_company_statistics(
    all_faults: list,
    cable_break_faults: list,
    suspended_faults_count: int,
    start_date,
    end_date,
    now,
    calendar_year: int | None = None,
    calendar_month: int | None = None,
) -> dict[str, object]:
    path_lengths = BRANCH_PROVINCE_PATH_LENGTHS.copy()
    branch_all_faults = [
        fault for fault in all_faults
        if _is_branch_company_fault(fault)
    ]
    branch_cable_break_faults = [
        fault for fault in cable_break_faults
        if _is_branch_company_fault(fault)
    ]
    branch_suspended_faults_count = sum(
        1
        for fault in OtnFault.objects.select_related('province', 'handling_unit').filter(_suspended_fault_q())
        if _is_branch_company_fault(fault)
    )

    overview_faults = [
        fault for fault in branch_all_faults
        if fault.fault_category not in OVERALL_EXCLUDED_TOTAL_CATEGORIES
    ]
    province_stats: dict[str, dict[str, float | int]] = {
        province: {'count': 0, 'duration': 0.0, 'valid_duration': 0.0, 'valid_count': 0}
        for province in BRANCH_PROVINCE_NAMES
    }
    province_samples: dict[str, list[float]] = {province: [] for province in BRANCH_PROVINCE_NAMES}

    for fault in branch_cable_break_faults:
        province = _branch_province_for_fault(fault)
        if province not in province_stats:
            continue
        duration_hours = _duration_hours_for_fault(fault, now)
        province_stats[province]['count'] += 1
        province_stats[province]['duration'] += duration_hours
        province_samples[province].append(duration_hours)
        if duration_hours > 0.5:
            province_stats[province]['valid_duration'] += duration_hours
            province_stats[province]['valid_count'] += 1

    province_bars = []
    duration_boxplot = []
    valid_duration_bars = []
    for province in BRANCH_PROVINCE_NAMES:
        length_km = path_lengths.get(province, 0.0)
        count = int(province_stats[province]['count'])
        duration = float(province_stats[province]['duration'])
        valid_duration = float(province_stats[province]['valid_duration'])
        valid_count = int(province_stats[province]['valid_count'])
        valid_duration_avg = valid_duration / valid_count if valid_count > 0 else 0.0
        province_bars.append({
            'name': province,
            'value': count,
            'count': count,
            'duration': round(duration, 2),
            'path_length': length_km,
            'count_per_1000km': _per_1000km(count, length_km),
            'duration_per_1000km': _per_1000km(duration, length_km),
            'per_1000km': _per_1000km(count, length_km),
        })
        duration_boxplot.append({
            'name': province,
            'value': _calculate_boxplot_values(province_samples[province]),
            'per_1000km': [
                _per_1000km(value, length_km)
                for value in _calculate_boxplot_values(province_samples[province])
            ],
        })
        valid_duration_bars.append({
            'name': province,
            'value': round(valid_duration_avg, 2),
            'valid_duration': round(valid_duration_avg, 2),
            'valid_duration_total': round(valid_duration, 2),
            'valid_count': valid_count,
            'path_length': length_km,
            'valid_duration_per_1000km': _per_1000km(valid_duration_avg, length_km),
            'per_1000km': _per_1000km(valid_duration_avg, length_km),
        })

    tz = timezone.get_current_timezone()
    selected_year = start_date.year
    year_start = timezone.datetime(selected_year, 1, 1, tzinfo=tz)
    year_end = now if now.year == selected_year else timezone.datetime(selected_year + 1, 1, 1, tzinfo=tz)
    if year_end <= year_start:
        year_end = timezone.datetime(selected_year + 1, 1, 1, tzinfo=tz)
    week_ranges = _build_branch_week_ranges(year_start, year_end)
    month_end_index = 12 if year_end.year > selected_year else year_end.month
    month_ranges = _build_year_to_month_calendar_months(selected_year, month_end_index, tz)
    weekly_by_province = {
        province: {
            week['key']: {'count': 0, 'duration': 0.0, 'valid_duration': 0.0}
            for week in week_ranges
        }
        for province in BRANCH_PROVINCE_NAMES
    }
    monthly_by_province = {
        province: {
            month['key']: {'count': 0, 'duration': 0.0, 'valid_duration': 0.0}
            for month in month_ranges
        }
        for province in BRANCH_PROVINCE_NAMES
    }

    year_all_faults = [
        fault for fault in OtnFault.objects.select_related('province', 'interruption_location_a', 'handling_unit')
        .prefetch_related('interruption_location')
        .filter(
            fault_occurrence_time__gte=year_start,
            fault_occurrence_time__lt=year_end,
        )
        if _is_branch_company_fault(fault)
    ]
    year_faults = [
        fault for fault in get_cable_break_base_queryset(year_start, year_end)
        if _is_branch_company_fault(fault)
    ]
    for fault in year_faults:
        province = _branch_province_for_fault(fault)
        if not province or not fault.fault_occurrence_time:
            continue
        local_day = timezone.localtime(fault.fault_occurrence_time).date().isoformat()
        week_key = next((week['key'] for week in week_ranges if week['start'] <= local_day <= week['end']), None)
        month_key = local_day[:7]
        if not week_key:
            continue
        duration_hours = _duration_hours_for_fault(fault, now)
        weekly_by_province[province][week_key]['count'] += 1
        weekly_by_province[province][week_key]['duration'] += duration_hours
        if month_key in monthly_by_province[province]:
            monthly_by_province[province][month_key]['count'] += 1
            monthly_by_province[province][month_key]['duration'] += duration_hours
        if duration_hours > 0.5:
            weekly_by_province[province][week_key]['valid_duration'] += duration_hours
            if month_key in monthly_by_province[province]:
                monthly_by_province[province][month_key]['valid_duration'] += duration_hours

    weekly_trends = {
        'labels': [week['label'] for week in week_ranges],
        'weeks': week_ranges,
        'series': [],
    }
    monthly_trends = {
        'labels': [month['label'] for month in month_ranges],
        'months': [{'key': month['key'], 'label': month['label']} for month in month_ranges],
        'series': [],
    }
    selected_calendar_year = calendar_year or selected_year
    selected_calendar_month = calendar_month or timezone.localtime(start_date).month
    calendar_months = _build_recent_calendar_months(selected_calendar_year, selected_calendar_month, tz)
    calendar_full_months = _build_year_to_month_calendar_months(selected_calendar_year, selected_calendar_month, tz)
    for province in BRANCH_PROVINCE_NAMES:
        length_km = path_lengths.get(province, 0.0)
        weekly_trends['series'].append({
            'name': province,
            'counts': [weekly_by_province[province][week['key']]['count'] for week in week_ranges],
            'durations': [round(weekly_by_province[province][week['key']]['duration'], 2) for week in week_ranges],
            'valid_durations': [round(weekly_by_province[province][week['key']]['valid_duration'], 2) for week in week_ranges],
            'week_count_per_1000km': [_per_1000km(weekly_by_province[province][week['key']]['count'], length_km) for week in week_ranges],
            'week_duration_per_1000km': [_per_1000km(weekly_by_province[province][week['key']]['duration'], length_km) for week in week_ranges],
            'week_valid_duration_per_1000km': [_per_1000km(weekly_by_province[province][week['key']]['valid_duration'], length_km) for week in week_ranges],
        })
        monthly_trends['series'].append({
            'name': province,
            'counts': [monthly_by_province[province][month['key']]['count'] for month in month_ranges],
            'durations': [round(monthly_by_province[province][month['key']]['duration'], 2) for month in month_ranges],
            'valid_durations': [round(monthly_by_province[province][month['key']]['valid_duration'], 2) for month in month_ranges],
            'month_count_per_1000km': [_per_1000km(monthly_by_province[province][month['key']]['count'], length_km) for month in month_ranges],
            'month_duration_per_1000km': [_per_1000km(monthly_by_province[province][month['key']]['duration'], length_km) for month in month_ranges],
            'month_valid_duration_per_1000km': [_per_1000km(monthly_by_province[province][month['key']]['valid_duration'], length_km) for month in month_ranges],
        })

    branch_cable_break_overview = _compute_cable_break_overview(branch_cable_break_faults, now)

    branch_cable_break_overview = _compute_cable_break_overview(branch_cable_break_faults, now)
    branch_bare_fiber_interruption = _compute_bare_fiber_interruption_overview(
        start_date,
        end_date,
        [],
        now,
        branch_company_scope=True,
    )
    branch_cable_break_overview['repeat_faults_count'] = _count_repeat_fiber_faults(
        branch_cable_break_faults,
        end_date,
        now,
    )
    performance_cards = _build_branch_company_performance_cards(
        branch_cable_break_faults,
        year_faults,
        year_all_faults,
        path_lengths,
        calendar_months,
        calendar_full_months,
        start_date,
        end_date,
        now,
    )

    return {
        'provinces': BRANCH_PROVINCE_NAMES,
        'path_lengths': path_lengths,
        'overview': {
            'total_count': len(overview_faults),
            'categories': _build_fault_category_summary(overview_faults, now),
            'other': _build_other_fault_summary(branch_all_faults, branch_suspended_faults_count),
        },
        'bare_fiber_interruption': branch_bare_fiber_interruption,
        'cable_break_overview': branch_cable_break_overview,
        'province_bars': province_bars,
        'duration_boxplot': duration_boxplot,
        'valid_duration_bars': valid_duration_bars,
        'weekly_trends': weekly_trends,
        'monthly_trends': monthly_trends,
        'performance_cards': performance_cards,
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


def _build_recent_calendar_months(year: int, month: int, tz, num_months: int = 6) -> list[dict[str, object]]:
    """Return month metadata for the recent months ending at the requested month."""
    months: list[dict[str, object]] = []
    for offset in range(num_months - 1, -1, -1):
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


def _build_year_to_month_calendar_months(year: int, month: int, tz) -> list[dict[str, object]]:
    """Return month metadata from January through the requested month."""
    month = min(max(month, 1), 12)
    months: list[dict[str, object]] = []
    for item_month in range(1, month + 1):
        next_month = item_month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year = year + 1
        month_start = timezone.datetime(year, item_month, 1, tzinfo=tz)
        month_end = timezone.datetime(next_year, next_month, 1, tzinfo=tz)
        months.append({
            'key': f'{year:04d}-{item_month:02d}',
            'year': year,
            'month': item_month,
            'label': f'{item_month}月',
            'start': month_start,
            'end': month_end,
            'weekday_offset': month_start.weekday(),
            'days': (month_end.date() - month_start.date()).days,
        })
    return months


def _parse_selected_provinces(request: HttpRequest) -> list[str]:
    provinces = [
        province.strip()
        for province in request.GET.getlist('provinces')
        if province and province.strip()
    ]
    return list(dict.fromkeys(provinces))


def _apply_physical_province_filter(queryset: QuerySet, selected_provinces: list[str]) -> QuerySet:
    if not selected_provinces:
        return queryset
    return queryset.filter(province__name__in=selected_provinces)


def _compute_bare_fiber_interruption_overview(
    start_date,
    end_date,
    selected_provinces: list[str],
    now,
    branch_company_scope: bool = False,
) -> dict[str, float | int]:
    """计算统计周期内裸纤业务的中断概览指标。"""
    impacts = OtnFaultImpact.objects.select_related(
        'otn_fault',
        'otn_fault__province'
    ).filter(
        service_interruption_time__gte=start_date,
        service_interruption_time__lt=end_date,
        service_type=ServiceTypeChoices.BARE_FIBER,
        otn_fault__is_suspended=False
    ).exclude(
        otn_fault__fault_status=FaultStatusChoices.SUSPENDED
    )

    if selected_provinces:
        impacts = impacts.filter(otn_fault__province__name__in=selected_provinces)

    filtered_impacts = []
    for imp in impacts:
        if imp.business_impact == BusinessImpactChoices.NOT_INTERRUPTED:
            continue

        fault = imp.otn_fault
        if branch_company_scope:
            if (
                _branch_province_for_fault(fault) not in BRANCH_PROVINCE_NAMES
                or _should_exclude_for_branch(fault)
            ):
                continue

        is_rectification_planned = (
            fault.interruption_reason == 'cable_rectification' and
            fault.interruption_reason_detail == 'planned_reporting'
        )
        is_approved = imp.coordination_status == 'approved'

        if is_rectification_planned and is_approved:
            continue

        filtered_impacts.append(imp)

    total_count = len(filtered_impacts)

    distinct_fault_ids = {imp.otn_fault_id for imp in filtered_impacts if imp.otn_fault_id}
    distinct_count = len(distinct_fault_ids)

    total_duration = 0.0
    for imp in filtered_impacts:
        end_t = imp.service_recovery_time if imp.service_recovery_time else now
        duration_hours = (end_t - imp.service_interruption_time).total_seconds() / 3600.0
        total_duration += duration_hours

    fault_durations = {}
    for imp in filtered_impacts:
        end_t = imp.service_recovery_time if imp.service_recovery_time else now
        dur = (end_t - imp.service_interruption_time).total_seconds() / 3600.0
        fid = imp.otn_fault_id
        if fid:
            if fid not in fault_durations or dur > fault_durations[fid]:
                fault_durations[fid] = dur
    distinct_duration = sum(fault_durations.values())

    return {
        'total_count': total_count,
        'distinct_count': distinct_count,
        'total_duration': round(total_duration, 2),
        'distinct_duration': round(distinct_duration, 2),
    }



def _build_physical_province_chart_stats(faults: list, now) -> dict[str, dict[str, float | int]]:
    province_stats: dict[str, dict[str, float | int]] = {}
    all_provinces = Region.objects.values_list('name', flat=True)
    for p_name in all_provinces:
        if p_name:
            province_stats[p_name] = {'count': 0, 'duration': 0.0}

    for fault in faults:
        if not fault.fault_occurrence_time:
            continue
        end_t = fault.fault_recovery_time if fault.fault_recovery_time else now
        duration_hours = (end_t - fault.fault_occurrence_time).total_seconds() / 3600.0
        prov_name = fault.province.name if fault.province else '未知'
        if prov_name not in province_stats:
            province_stats[prov_name] = {'count': 0, 'duration': 0.0}
        province_stats[prov_name]['count'] += 1
        province_stats[prov_name]['duration'] += duration_hours
    return province_stats


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
        'province_filter_options': list(Region.objects.exclude(name='').values_list('name', flat=True).order_by('name')),
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
        
        is_ended = end_date and end_date <= now
        selected_provinces = _parse_selected_provinces(request)
        calendar_year = int(request.GET.get('calendar_year', start_date.year))
        calendar_month = int(request.GET.get('calendar_month', timezone.localtime(start_date).month))
        
        from django.core.cache import cache
        import hashlib
        
        version_key = "otnfaults:stats:version"
        cache_version = cache.get(version_key)
        if cache_version is None:
            cache_version = 1
            cache.set(version_key, cache_version, timeout=None)
            
        provinces_str = ",".join(sorted(selected_provinces))
        provinces_hash = hashlib.md5(provinces_str.encode('utf-8')).hexdigest() if provinces_str else "all"
        
        cache_key = f"otnfaults:stats:v{cache_version}:fault-summary:{filter_type}:{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}:{provinces_hash}:{calendar_year}:{calendar_month}"
        
        if is_ended:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return JsonResponse(cached_data)

        # 计算当前期裸纤业务中断情况
        bare_fiber_interruption = _compute_bare_fiber_interruption_overview(
            start_date, end_date, selected_provinces, now
        )

        prev_bare_fiber_interruption = {}
        if prev_start_date and prev_end_date:
            prev_bare_fiber_interruption = _compute_bare_fiber_interruption_overview(
                prev_start_date, prev_end_date, selected_provinces, now
            )

        # 先预抓取一段无过滤条件的全量当前期基础查询集，仅用于提取“总体情况面板” Banner 数据
        qs_all = OtnFault.objects.select_related('province', 'interruption_location_a', 'handling_unit').prefetch_related('interruption_location')
        all_current_qs = qs_all.filter(fault_occurrence_time__gte=start_date, fault_occurrence_time__lt=end_date)
        filtered_current_qs = _apply_physical_province_filter(all_current_qs, selected_provinces)
        all_faults = list(filtered_current_qs)

        # 计算当前期影响程度等级指标卡片数据
        annotated_current_qs = _annotate_class_i_business_impact(filtered_current_qs)
        current_level_stats = annotated_current_qs.aggregate(
            total=Count('id', filter=Q_CLASS_TOTAL),
            class_i_ii=Count('id', filter=Q_CLASS_I_II),
            class_i=Count('id', filter=Q_CLASS_I),
            class_ii=Count('id', filter=Q_CLASS_II),
            class_iii=Count('id', filter=Q_CLASS_III),
            class_iv=Count('id', filter=Q_CLASS_IV),
            class_v=Count('id', filter=Q_CLASS_V),
        )
        current_cutover_count = CutoverTask.objects.filter(
            started_at__gte=start_date,
            started_at__lt=end_date
        )
        if selected_provinces:
            current_cutover_count = current_cutover_count.filter(province__name__in=selected_provinces)
        current_level_stats['cutover_implemented'] = current_cutover_count.count()

        # 计算上周期影响程度等级指标卡片数据
        prev_level_stats = {
            "total": 0, "class_i_ii": 0, "class_i": 0, "class_ii": 0,
            "class_iii": 0, "class_iv": 0, "class_v": 0, "cutover_implemented": 0
        }
        if prev_start_date and prev_end_date:
            prev_qs = qs_all.filter(fault_occurrence_time__gte=prev_start_date, fault_occurrence_time__lt=prev_end_date)
            filtered_prev_qs = _apply_physical_province_filter(prev_qs, selected_provinces)
            annotated_prev_qs = _annotate_class_i_business_impact(filtered_prev_qs)
            prev_level_stats = annotated_prev_qs.aggregate(
                total=Count('id', filter=Q_CLASS_TOTAL),
                class_i_ii=Count('id', filter=Q_CLASS_I_II),
                class_i=Count('id', filter=Q_CLASS_I),
                class_ii=Count('id', filter=Q_CLASS_II),
                class_iii=Count('id', filter=Q_CLASS_III),
                class_iv=Count('id', filter=Q_CLASS_IV),
                class_v=Count('id', filter=Q_CLASS_V),
            )
            prev_cutover_count = CutoverTask.objects.filter(
                started_at__gte=prev_start_date,
                started_at__lt=prev_end_date
            )
            if selected_provinces:
                prev_cutover_count = prev_cutover_count.filter(province__name__in=selected_provinces)
            prev_level_stats['cutover_implemented'] = prev_cutover_count.count()

        # 计算当前期影响程度等级占比环形图数据
        ring_fiber = {"class_i": 0, "class_ii": 0, "suspended": 0}
        ring_power = {"class_i": 0, "class_iii": 0, "suspended": 0}
        ring_environment = {"class_i": 0, "class_iii": 0, "suspended": 0}

        for fault in annotated_current_qs:
            if fault.source_cutover_task_id is not None:
                continue
            is_suspended = fault.fault_status == FaultStatusChoices.SUSPENDED or fault.is_suspended
            
            if fault.fault_category == FaultCategoryChoices.FIBER_BREAK:
                if is_suspended:
                    ring_fiber["suspended"] += 1
                elif fault.has_class_i_business_impact:
                    ring_fiber["class_i"] += 1
                else:
                    ring_fiber["class_ii"] += 1
            elif fault.fault_category == FaultCategoryChoices.POWER_FAULT:
                if is_suspended:
                    ring_power["suspended"] += 1
                elif fault.power_fault_impact == PowerFaultImpactChoices.HOSTED:
                    ring_power["class_i"] += 1
                else:
                    ring_power["class_iii"] += 1
            elif fault.fault_category in [FaultCategoryChoices.AC_FAULT, FaultCategoryChoices.DEVICE_FAULT]:
                is_class_i_ac = fault.fault_category == FaultCategoryChoices.AC_FAULT and getattr(fault, 'ac_fault_is_class_i', False)
                is_class_i_device = fault.fault_category == FaultCategoryChoices.DEVICE_FAULT and getattr(fault, 'device_fault_is_class_i', False)
                if is_suspended:
                    ring_environment["suspended"] += 1
                elif is_class_i_ac or is_class_i_device:
                    ring_environment["class_i"] += 1
                else:
                    ring_environment["class_iii"] += 1

        # 计算上周期影响程度等级占比环形图数据
        prev_ring_fiber = {"class_i": 0, "class_ii": 0, "suspended": 0}
        prev_ring_power = {"class_i": 0, "class_iii": 0, "suspended": 0}
        prev_ring_environment = {"class_i": 0, "class_iii": 0, "suspended": 0}

        if prev_start_date and prev_end_date:
            for fault in annotated_prev_qs:
                if fault.source_cutover_task_id is not None:
                    continue
                is_suspended = fault.fault_status == FaultStatusChoices.SUSPENDED or fault.is_suspended
                
                if fault.fault_category == FaultCategoryChoices.FIBER_BREAK:
                    if is_suspended:
                        prev_ring_fiber["suspended"] += 1
                    elif fault.has_class_i_business_impact:
                        prev_ring_fiber["class_i"] += 1
                    else:
                        prev_ring_fiber["class_ii"] += 1
                elif fault.fault_category == FaultCategoryChoices.POWER_FAULT:
                    if is_suspended:
                        prev_ring_power["suspended"] += 1
                    elif fault.power_fault_impact == PowerFaultImpactChoices.HOSTED:
                        prev_ring_power["class_i"] += 1
                    else:
                        prev_ring_power["class_iii"] += 1
                elif fault.fault_category in [FaultCategoryChoices.AC_FAULT, FaultCategoryChoices.DEVICE_FAULT]:
                    is_class_i_ac = fault.fault_category == FaultCategoryChoices.AC_FAULT and getattr(fault, 'ac_fault_is_class_i', False)
                    is_class_i_device = fault.fault_category == FaultCategoryChoices.DEVICE_FAULT and getattr(fault, 'device_fault_is_class_i', False)
                    if is_suspended:
                        prev_ring_environment["suspended"] += 1
                    elif is_class_i_ac or is_class_i_device:
                        prev_ring_environment["class_i"] += 1
                    else:
                        prev_ring_environment["class_iii"] += 1

        unfiltered_current_faults = list(all_current_qs)
        all_suspended_faults_total_count = _apply_physical_province_filter(qs_all.filter(_suspended_fault_q()), selected_provinces).count()
        all_open_suspended_faults_count = _apply_physical_province_filter(
            qs_all.filter(_suspended_fault_q()).exclude(fault_status=FaultStatusChoices.CLOSED),
            selected_provinces,
        ).count()
        unfiltered_open_suspended_faults_count = qs_all.filter(_suspended_fault_q()).exclude(fault_status=FaultStatusChoices.CLOSED).count()

        overall_faults = [
            f for f in all_faults
            if f.fault_category not in OVERALL_EXCLUDED_TOTAL_CATEGORIES
        ]
        overall_total_count = len(overall_faults)
        overall_category_stats = _build_fault_category_summary(overall_faults, now)
        other_overview = _build_other_fault_summary(
            all_faults,
            all_open_suspended_faults_count,
            all_suspended_faults_total_count,
        )
        physical_daily_start, physical_daily_end = _resolve_physical_daily_range(now)
        physical_daily_faults = list(
            _apply_physical_province_filter(
                qs_all.filter(
                    fault_occurrence_time__gte=physical_daily_start,
                    fault_occurrence_time__lt=physical_daily_end,
                    fault_category=FaultCategoryChoices.FIBER_BREAK,
                ).filter(
                    is_suspended=False
                ).exclude(
                    fault_status=FaultStatusChoices.SUSPENDED
                ),
                selected_provinces,
            )
        )
        physical_daily_stats = _build_physical_daily_fault_series(physical_daily_start, physical_daily_end, physical_daily_faults, now)

        # 提取当前期光缆中断故障
        global_cable_break_faults = list(get_cable_break_base_queryset(start_date, end_date))
        physical_duration_boxplot_faults = list(_apply_physical_province_filter(
            get_cable_break_base_queryset(start_date, end_date),
            selected_provinces,
        ))
        physical_duration_boxplot_stats = _build_physical_daily_fault_series(start_date, end_date, physical_duration_boxplot_faults, now)
        faults = physical_duration_boxplot_faults
        branch_company_stats = _build_branch_company_statistics(
            unfiltered_current_faults,
            global_cable_break_faults,
            unfiltered_open_suspended_faults_count,
            start_date,
            end_date,
            now,
            calendar_year,
            calendar_month,
        )
        prev_branch_company_stats = {}
        
        # 提取上一期故障并计算其 KPI
        prev_total_count = 0
        prev_total_duration = 0.0
        prev_long_faults = 0
        prev_repeat_faults = 0
        prev_avg_duration = 0.0
        prev_faults = []
        
        if prev_start_date and prev_end_date:
            prev_global_cable_break_faults = list(get_cable_break_base_queryset(prev_start_date, prev_end_date))
            prev_faults = list(_apply_physical_province_filter(
                get_cable_break_base_queryset(prev_start_date, prev_end_date),
                selected_provinces,
            ))
            prev_total_count = len(prev_faults)
            
            if prev_faults:
                p_fiber_faults = [f for f in prev_faults if f.is_fiber_fault]
                if p_fiber_faults:
                    p_min_occ = min([f.fault_occurrence_time for f in p_fiber_faults])
                    p_check_start = p_min_occ - timedelta(days=60)
                    p_past_qs = OtnFault.objects.filter(
                        fault_occurrence_time__gte=p_check_start,
                        fault_occurrence_time__lt=prev_end_date,
                        fault_category__in=[FaultCategoryChoices.FIBER_BREAK, 
                                            FaultCategoryChoices.FIBER_DEGRADATION, 
                                            FaultCategoryChoices.FIBER_JITTER]
                    ).select_related('interruption_location_a').prefetch_related('interruption_location')
                    p_past_list = list(p_past_qs)
                else:
                    p_past_list = []
                
                prev_repeat_result = detect_repeat_faults(prev_faults, p_past_list)
                prev_repeat_faults = len(prev_repeat_result.kpi_repeat_ids)
                
                for f in prev_faults:
                    occ = f.fault_occurrence_time
                    rec = f.fault_recovery_time if f.fault_recovery_time else now
                    dur = (rec - occ).total_seconds() / 3600.0
                    prev_total_duration += dur
                    if dur >= 6.0:
                        prev_long_faults += 1
            prev_avg_duration = prev_total_duration / prev_total_count if prev_total_count > 0 else 0.0
        
        # 1. 统计 KPI
        total_count = len(faults)
        total_duration_hours = 0.0
        long_faults_count = 0
        repeat_faults_count = 0
        
        fiber_faults = [f for f in faults if f.is_fiber_fault]
        if fiber_faults:
            min_occurrence = min([f.fault_occurrence_time for f in fiber_faults])
            check_start = min_occurrence - timedelta(days=60)
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

        # 统一计算当前期的重复故障
        repeat_result = detect_repeat_faults(faults, past_faults_list)
        repeat_faults_count = len(repeat_result.kpi_repeat_ids)

        # 统计图表维度
        resource_stats = {}
        province_stats = _build_physical_province_chart_stats(global_cable_break_faults, now)
        reason_stats = {}

        for fault in faults:
            occ_time = fault.fault_occurrence_time
            end_t = fault.fault_recovery_time if fault.fault_recovery_time else now
            duration_delta = end_t - occ_time
            duration_hours = duration_delta.total_seconds() / 3600.0
            
            total_duration_hours += duration_hours
            if duration_hours >= 6.0:
                long_faults_count += 1
                
            r_type = fault.resource_type or 'unfilled'
            r_type_display = fault.get_resource_type_display() if fault.resource_type else '未填写'
            if r_type_display not in resource_stats:
                resource_stats[r_type_display] = {'id': r_type, 'count': 0, 'duration': 0.0}
            resource_stats[r_type_display]['count'] += 1
            resource_stats[r_type_display]['duration'] += duration_hours

            reason = fault.get_interruption_reason_display() if fault.interruption_reason else '未填/未知'
            if reason not in reason_stats:
                reason_stats[reason] = {'count': 0, 'duration': 0.0}
            reason_stats[reason]['count'] += 1
            reason_stats[reason]['duration'] += duration_hours

        # 使用辅助函数计算当前期光缆中断概览
        cable_break_overview = _compute_cable_break_overview(faults, now)
        avg_duration_hours = total_duration_hours / total_count if total_count > 0 else 0.0

        # 计算上周期的全维度对比数据
        prev_overall_category_stats = _build_fault_category_summary([], now)
        prev_cable_break_overview = {}
        prev_other_overview = _build_other_fault_summary(
            [],
            all_open_suspended_faults_count,
            all_suspended_faults_total_count,
        )
        if prev_start_date and prev_end_date:
            prev_all_qs = qs_all.filter(fault_occurrence_time__gte=prev_start_date, fault_occurrence_time__lt=prev_end_date)
            prev_unfiltered_all_faults = list(prev_all_qs)
            prev_all_faults = list(_apply_physical_province_filter(prev_all_qs, selected_provinces))
            prev_overall_faults = [
                f for f in prev_all_faults
                if f.fault_category not in OVERALL_EXCLUDED_TOTAL_CATEGORIES
            ]
            prev_overall_category_stats = _build_fault_category_summary(prev_overall_faults, now)
            prev_other_overview = _build_other_fault_summary(
                prev_all_faults,
                all_open_suspended_faults_count,
                all_suspended_faults_total_count,
            )

            prev_cable_break_overview = _compute_cable_break_overview(prev_faults, now)
            prev_branch_company_stats = _build_branch_company_statistics(
                prev_unfiltered_all_faults,
                prev_global_cable_break_faults,
                unfiltered_open_suspended_faults_count,
                prev_start_date,
                prev_end_date,
                now,
                calendar_year,
                calendar_month,
            )

        display_end_date_str = ''
        if end_date:
            display_end_date = end_date - timedelta(days=1)
            display_end_date_str = display_end_date.strftime('%Y-%m-%d')

        response_data = {
            'period': build_period_display(start_date, end_date, now),
            'impact_level_summary': current_level_stats,
            'prev_impact_level_summary': prev_level_stats,
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
                'ring_fiber': [
                    {"name": "I类", "value": ring_fiber["class_i"]},
                    {"name": "II类", "value": ring_fiber["class_ii"]},
                    {"name": "挂起", "value": ring_fiber["suspended"]}
                ],
                'ring_power': [
                    {"name": "I类", "value": ring_power["class_i"]},
                    {"name": "III类", "value": ring_power["class_iii"]},
                    {"name": "挂起", "value": ring_power["suspended"]}
                ],
                'ring_environment': [
                    {"name": "I类", "value": ring_environment["class_i"]},
                    {"name": "III类", "value": ring_environment["class_iii"]},
                    {"name": "挂起", "value": ring_environment["suspended"]}
                ]
            },
            'prev_charts': {
                'category': prev_overall_category_stats,
                'ring_fiber': [
                    {"name": "I类", "value": prev_ring_fiber["class_i"]},
                    {"name": "II类", "value": prev_ring_fiber["class_ii"]},
                    {"name": "挂起", "value": prev_ring_fiber["suspended"]}
                ],
                'ring_power': [
                    {"name": "I类", "value": prev_ring_power["class_i"]},
                    {"name": "III类", "value": prev_ring_power["class_iii"]},
                    {"name": "挂起", "value": prev_ring_power["suspended"]}
                ],
                'ring_environment': [
                    {"name": "I类", "value": prev_ring_environment["class_i"]},
                    {"name": "III类", "value": prev_ring_environment["class_iii"]},
                    {"name": "挂起", "value": prev_ring_environment["suspended"]}
                ]
            },
            'cable_break_overview': cable_break_overview,
            'prev_cable_break_overview': prev_cable_break_overview,
            'bare_fiber_interruption': bare_fiber_interruption,
            'prev_bare_fiber_interruption': prev_bare_fiber_interruption,
            'branch_company': branch_company_stats,
            'prev_branch_company': prev_branch_company_stats,
            'other_overview': other_overview,
            'prev_other_overview': prev_other_overview,
            'selected_provinces': selected_provinces,
        }

        if is_ended:
            cache.set(cache_key, response_data, timeout=12 * 3600)

        return JsonResponse(response_data)





class ServiceStatisticsDataAPI(PermissionRequiredMixin, View):
    """
    业务故障统计聚合API。
    按业务（BareFiberService / CircuitService）聚合 OtnFaultImpact 数据，
    返回每个业务的统计卡片数据。
    """
    permission_required = 'netbox_otnfaults.view_otnfaultimpact'

    def get(self, request) -> JsonResponse:
        start_date, end_date, prev_start_date, prev_end_date, filter_type = _parse_time_range(request)
        include_all_bare_fiber: bool = request.GET.get('include_all_bare_fiber') == '1'
        now = timezone.localtime()
        selected_year = int(request.GET.get('year', start_date.year))
        tz = timezone.get_current_timezone()
        year_start = timezone.datetime(selected_year, 1, 1, tzinfo=tz)
        year_end = timezone.datetime(selected_year + 1, 1, 1, tzinfo=tz)
        
        # 1. 过滤当前周期的 impacts
        impacts_qs = OtnFaultImpact.objects.select_related(
            'otn_fault', 'bare_fiber_service', 'bare_fiber_service__tenant_group', 'circuit_service'
        ).filter(
            service_interruption_time__gte=start_date,
            service_interruption_time__lt=end_date
        ).filter(
            Q(service_type=ServiceTypeChoices.BARE_FIBER, business_impact=BusinessImpactChoices.INTERRUPTED)
            | Q(service_type=ServiceTypeChoices.CIRCUIT, business_impact=BusinessImpactChoices.INTERRUPTED)
        )
        impacts = list(impacts_qs)
        
        # 提取当前期受影响的业务 ID 集合
        affected_bf_ids = {imp.bare_fiber_service_id for imp in impacts if imp.service_type == ServiceTypeChoices.BARE_FIBER and imp.bare_fiber_service_id}
        affected_cs_ids = {imp.circuit_service_id for imp in impacts if imp.service_type == ServiceTypeChoices.CIRCUIT and imp.circuit_service_id}
        all_bare_fiber_services = list(
            BareFiberService.objects.select_related('tenant_group').order_by('name')
        ) if include_all_bare_fiber else []
        statistics_bf_ids = affected_bf_ids | {service.pk for service in all_bare_fiber_services}

        # 2. 默认仅对当前周期有影响的业务获取年度 impacts 和日历；
        # 请求全部裸纤业务时，为全部裸纤业务补充年度和日历统计。
        yearly_impacts = []
        calendar_impacts = []
        
        calendar_year = int(request.GET.get('calendar_year', selected_year))
        calendar_month = int(request.GET.get('calendar_month', timezone.localtime(start_date).month))
        calendar_months = _build_recent_calendar_months(calendar_year, calendar_month, tz, num_months=3)
        calendar_full_months = _build_year_to_month_calendar_months(calendar_year, calendar_month, tz)
        
        if statistics_bf_ids or affected_cs_ids:
            # 获取年度 impacts
            yearly_impacts_qs = OtnFaultImpact.objects.select_related(
                'otn_fault', 'bare_fiber_service', 'bare_fiber_service__tenant_group', 'circuit_service'
            ).filter(
                service_interruption_time__gte=year_start,
                service_interruption_time__lt=year_end
            ).filter(
                Q(service_type=ServiceTypeChoices.BARE_FIBER, business_impact=BusinessImpactChoices.INTERRUPTED)
                | Q(service_type=ServiceTypeChoices.CIRCUIT, business_impact=BusinessImpactChoices.INTERRUPTED)
            ).filter(otn_fault__is_suspended=False).exclude(otn_fault__fault_status=FaultStatusChoices.SUSPENDED)
            
            yearly_impacts_qs = yearly_impacts_qs.filter(
                Q(service_type=ServiceTypeChoices.BARE_FIBER, bare_fiber_service_id__in=statistics_bf_ids)
                | Q(service_type=ServiceTypeChoices.CIRCUIT, circuit_service_id__in=affected_cs_ids)
            )
            yearly_impacts = list(yearly_impacts_qs)

            # 获取日历 impacts
            calendar_start = calendar_months[0]['start']
            calendar_end = calendar_months[-1]['end']
            calendar_full_start = calendar_full_months[0]['start']
            calendar_full_end = calendar_full_months[-1]['end']
            calendar_query_start = min(calendar_start, calendar_full_start)
            calendar_query_end = max(calendar_end, calendar_full_end)

            calendar_impacts_qs = OtnFaultImpact.objects.select_related(
                'otn_fault', 'bare_fiber_service', 'bare_fiber_service__tenant_group', 'circuit_service'
            ).filter(
                service_interruption_time__gte=calendar_query_start,
                service_interruption_time__lt=calendar_query_end
            ).filter(
                Q(service_type=ServiceTypeChoices.BARE_FIBER, business_impact=BusinessImpactChoices.INTERRUPTED)
                | Q(service_type=ServiceTypeChoices.CIRCUIT, business_impact=BusinessImpactChoices.INTERRUPTED)
            ).filter(otn_fault__is_suspended=False).exclude(otn_fault__fault_status=FaultStatusChoices.SUSPENDED)
            
            calendar_impacts_qs = calendar_impacts_qs.filter(
                Q(service_type=ServiceTypeChoices.BARE_FIBER, bare_fiber_service_id__in=statistics_bf_ids)
                | Q(service_type=ServiceTypeChoices.CIRCUIT, circuit_service_id__in=affected_cs_ids)
            )
            calendar_impacts = list(calendar_impacts_qs)

        period_total_hours: float = (end_date - start_date).total_seconds() / 3600.0
        annual_total_hours: float = (year_end - year_start).total_seconds() / 3600.0

        service_map: dict = {}

        def initialize_service_stats(
            svc_name: str,
            svc_type_label: str,
            svc_group_label: str,
            svc_sort_rank: int,
        ) -> dict[str, Any]:
            monthly_stats = {month: {'count': 0, 'duration': 0.0, 'intervals': []} for month in range(1, 13)}
            return {
                'name': svc_name,
                'type': svc_type_label,
                'group_label': svc_group_label,
                'sort_rank': svc_sort_rank,
                'has_current_period_faults': False,
                'count': 0,
                'break_count': 0,
                'jitter_count': 0,
                'degrade_count': 0,
                'other_count': 0,
                'category_stats': {
                    label: {
                        'count': 0,
                        'duration': 0.0,
                    }
                    for _value, label, *_rest in FaultCategoryChoices.CHOICES
                },
                'monthly_stats': monthly_stats,
                'annual_summary': {
                    'count': 0,
                    'total_duration': 0.0,
                    'intervals': [],
                },
                'interrupt_calendar': {
                    month_info['key']: {day: 0 for day in range(1, month_info['days'] + 1)}
                    for month_info in calendar_months
                },
                'interrupt_calendar_full': {
                    month_info['key']: {day: 0 for day in range(1, month_info['days'] + 1)}
                    for month_info in calendar_full_months
                },
                'total_duration': 0.0,
                'long_count': 0,
                'intervals': [],
                'occurrence_times': [],
            }

        if include_all_bare_fiber:
            for service in all_bare_fiber_services:
                svc_key = f'bf_{service.pk}'
                svc_group_label = service.tenant_group.name if service.tenant_group else '未分组'
                service_map[svc_key] = initialize_service_stats(
                    service.name,
                    '裸纤业务',
                    svc_group_label,
                    0,
                )

        # 遍历 impacts 填充受到故障影响的业务卡片
        for imp in impacts:
            if imp.service_type == ServiceTypeChoices.BARE_FIBER and imp.bare_fiber_service:
                svc_key = f'bf_{imp.bare_fiber_service_id}'
                svc_name = imp.bare_fiber_service.name
                svc_type_label = '裸纤业务'
                svc_group_label = imp.bare_fiber_service.tenant_group.name if imp.bare_fiber_service.tenant_group else '未分组'
                svc_sort_rank = 0
            elif imp.service_type == ServiceTypeChoices.CIRCUIT and imp.circuit_service:
                svc_key = f'cs_{imp.circuit_service_id}'
                svc_name = imp.circuit_service.special_line_name or imp.circuit_service.name
                svc_type_label = '电路业务'
                svc_group_label = imp.circuit_service.get_business_category_display() if imp.circuit_service.business_category else '未分组'
                svc_sort_rank = 1
            else:
                continue

            if svc_key not in service_map:
                service_map[svc_key] = initialize_service_stats(
                    svc_name,
                    svc_type_label,
                    svc_group_label,
                    svc_sort_rank,
                )

            stats = service_map[svc_key]
            stats['has_current_period_faults'] = True
            stats['count'] += 1

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

            svc_start = imp.service_interruption_time
            svc_end = imp.service_recovery_time if imp.service_recovery_time else now
            dur_hours = (svc_end - svc_start).total_seconds() / 3600.0
            stats['total_duration'] += dur_hours
            stats['category_stats'][category_label]['duration'] += dur_hours

            if dur_hours >= 6.0:
                stats['long_count'] += 1

            stats['intervals'].append((svc_start, svc_end))
            stats['occurrence_times'].append(svc_start)

        # 填充年度 impacts
        for year_imp in yearly_impacts:
            if year_imp.service_type == ServiceTypeChoices.BARE_FIBER and year_imp.bare_fiber_service:
                svc_key = f'bf_{year_imp.bare_fiber_service_id}'
            elif year_imp.service_type == ServiceTypeChoices.CIRCUIT and year_imp.circuit_service:
                svc_key = f'cs_{year_imp.circuit_service_id}'
            else:
                continue
            
            if svc_key not in service_map:
                continue

            month_index = timezone.localtime(year_imp.service_interruption_time).month
            month_end = year_imp.service_recovery_time if year_imp.service_recovery_time else now
            month_dur_hours = (month_end - year_imp.service_interruption_time).total_seconds() / 3600.0
            stats = service_map[svc_key]
            stats['monthly_stats'][month_index]['count'] += 1
            stats['monthly_stats'][month_index]['duration'] += month_dur_hours
            stats['monthly_stats'][month_index]['intervals'].append((year_imp.service_interruption_time, month_end))
            stats['annual_summary']['count'] += 1
            stats['annual_summary']['total_duration'] += month_dur_hours
            stats['annual_summary']['intervals'].append((year_imp.service_interruption_time, month_end))

        # 填充日历
        for calendar_imp in calendar_impacts:
            if calendar_imp.service_type == ServiceTypeChoices.BARE_FIBER and calendar_imp.bare_fiber_service:
                svc_key = f'bf_{calendar_imp.bare_fiber_service_id}'
            elif calendar_imp.service_type == ServiceTypeChoices.CIRCUIT and calendar_imp.circuit_service:
                svc_key = f'cs_{calendar_imp.circuit_service_id}'
            else:
                continue
            
            if svc_key not in service_map:
                continue

            calendar_day = timezone.localtime(calendar_imp.service_interruption_time)
            calendar_key = f'{calendar_day.year:04d}-{calendar_day.month:02d}'
            stats = service_map[svc_key]
            if calendar_key in stats['interrupt_calendar'] and calendar_day.day in stats['interrupt_calendar'][calendar_key]:
                stats['interrupt_calendar'][calendar_key][calendar_day.day] += 1
            if calendar_key in stats['interrupt_calendar_full'] and calendar_day.day in stats['interrupt_calendar_full'][calendar_key]:
                stats['interrupt_calendar_full'][calendar_key][calendar_day.day] += 1

        def calculate_merged_interval_sla(
            intervals: list[tuple[Any, Any]],
            scope_start: Any,
            scope_end: Any,
        ) -> float:
            total_hours = (scope_end - scope_start).total_seconds() / 3600.0
            clipped_intervals = [
                (max(start, scope_start), min(end, scope_end))
                for start, end in intervals
                if start < scope_end and end > scope_start
            ]
            merged_intervals: list[tuple[Any, Any]] = []
            for start, end in sorted(clipped_intervals, key=lambda item: item[0]):
                if start >= end:
                    continue
                if merged_intervals and start <= merged_intervals[-1][1]:
                    merged_intervals[-1] = (merged_intervals[-1][0], max(merged_intervals[-1][1], end))
                else:
                    merged_intervals.append((start, end))
            unavailable_hours = sum(
                (end - start).total_seconds() / 3600.0 for start, end in merged_intervals
            )
            sla_value = ((total_hours - unavailable_hours) / total_hours * 100.0) if total_hours > 0 else 100.0
            return max(0.0, sla_value)

        services_result = []
        for svc_key, stats in service_map.items():
            count = stats['count']
            total_dur = stats['total_duration']
            avg_dur = total_dur / count if count > 0 else 0.0

            repeat_count = 0
            times_sorted = sorted(stats['occurrence_times'])
            for i in range(1, len(times_sorted)):
                if (times_sorted[i] - times_sorted[i - 1]).days <= 60:
                    repeat_count += 1

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
            sla = max(0.0, sla)
            
            annual_intervals = sorted(stats['annual_summary']['intervals'], key=lambda x: x[0])
            annual_merged: list = []
            for s, e in annual_intervals:
                if annual_merged and s <= annual_merged[-1][1]:
                    annual_merged[-1] = (annual_merged[-1][0], max(annual_merged[-1][1], e))
                else:
                    annual_merged.append((s, e))
            annual_unavailable_hours = sum(
                (e - s).total_seconds() / 3600.0 for s, e in annual_merged
            )
            annual_sla = ((annual_total_hours - annual_unavailable_hours) / annual_total_hours * 100.0) if annual_total_hours > 0 else 100.0
            annual_sla = max(0.0, annual_sla)

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
            
            monthly_stats_payload = []
            for month, month_stats in stats['monthly_stats'].items():
                month_start = timezone.datetime(selected_year, month, 1, tzinfo=tz)
                month_end_boundary = (
                    timezone.datetime(selected_year + 1, 1, 1, tzinfo=tz)
                    if month == 12 else timezone.datetime(selected_year, month + 1, 1, tzinfo=tz)
                )
                monthly_sla = calculate_merged_interval_sla(
                    month_stats['intervals'],
                    month_start,
                    month_end_boundary,
                )
                monthly_stats_payload.append({
                    'month': month,
                    'label': f'{month}月',
                    'count': month_stats['count'],
                    'duration': round(month_stats['duration'], 2),
                    'sla': truncate_sla(monthly_sla),
                })
                
            annual_summary_payload = {
                'year': selected_year,
                'count': stats['annual_summary']['count'],
                'total_duration': round(stats['annual_summary']['total_duration'], 2),
                'sla': truncate_sla(annual_sla),
            }
            
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
            
            interrupt_calendar_full_payload = [
                {
                    'key': month_info['key'],
                    'label': month_info['label'],
                    'year': month_info['year'],
                    'month': month_info['month'],
                    'weekday_offset': month_info['weekday_offset'],
                    'days': [
                        {
                            'day': day,
                            'count': stats['interrupt_calendar_full'][month_info['key']][day],
                        }
                        for day in range(1, month_info['days'] + 1)
                    ],
                }
                for month_info in calendar_full_months
            ]

            services_result.append({
                'key': svc_key,
                'name': stats['name'],
                'type': stats['type'],
                'group_label': stats['group_label'],
                'sort_rank': stats['sort_rank'],
                'has_current_period_faults': stats['has_current_period_faults'],
                'count': count,
                'break_count': stats['break_count'],
                'jitter_count': stats['jitter_count'],
                'degrade_count': stats['degrade_count'],
                'other_count': stats['other_count'],
                'category_stats': category_stats_payload,
                'annual_summary': annual_summary_payload,
                'monthly_stats': monthly_stats_payload,
                'interrupt_calendar': interrupt_calendar_payload,
                'interrupt_calendar_full': interrupt_calendar_full_payload,
                'total_duration': round(total_dur, 2),
                'avg_duration': round(avg_dur, 2),
                'long_count': stats['long_count'],
                'repeat_count': repeat_count,
                'sla': truncate_sla(sla),
            })

        services_result.sort(key=lambda x: (x['sort_rank'], -x['count'], x['name']))
        for result in services_result:
            result.pop('sort_rank', None)

        display_end_date_str = ''
        if end_date:
            display_end_date = end_date - timedelta(days=1)
            display_end_date_str = display_end_date.strftime('%Y-%m-%d')

        return JsonResponse({
            'period': build_period_display(start_date, end_date, now),
            'period_total_hours': round(period_total_hours, 2),
            'services': services_result,
        })


class FaultStatisticsDetailsAPI(PermissionRequiredMixin, View):
    """
    故障明细过滤接口。
    """
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request) -> JsonResponse:
        start_date, end_date, prev_start_date, prev_end_date, filter_type = _parse_time_range(request)
        now = timezone.localtime()
        selected_provinces = _parse_selected_provinces(request)

        qs = OtnFault.objects.select_related('province', 'interruption_location_a', 'handling_unit').prefetch_related('interruption_location')
        qs = qs.filter(fault_occurrence_time__gte=start_date, fault_occurrence_time__lt=end_date)
        qs = _apply_physical_province_filter(qs, selected_provinces)
        qs = _annotate_class_i_business_impact(qs)

        category_aliases: dict[str, str] = {
            '光缆中断': FaultCategoryChoices.FIBER_BREAK,
            '空调故障': FaultCategoryChoices.AC_FAULT,
            '光缆劣化': FaultCategoryChoices.FIBER_DEGRADATION,
            '光缆抖动': FaultCategoryChoices.FIBER_JITTER,
            '设备故障': FaultCategoryChoices.DEVICE_FAULT,
            '供电故障': FaultCategoryChoices.POWER_FAULT,
        }
        resource_type_aliases: dict[str, str] = {
            '自建': ResourceTypeChoices.SELF_BUILT,
            '协调': ResourceTypeChoices.COORDINATED,
            '租赁': ResourceTypeChoices.LEASED,
            '未填写': 'unfilled',
        }
        reason_aliases: dict[str, str] = {
            '施工': 'construction', '人为': 'human_factor', '交通事故': 'traffic_accident',
            '动物破坏': 'animal_damage', '自然灾害': 'natural_disaster', '火灾故障': 'fire',
            '无法查明': 'unknown', '光缆整改': 'cable_rectification',
        }

        impact_level = request.GET.get('impact_level')
        category = request.GET.get('category')
        resource_type = request.GET.get('resource_type')
        source_group = request.GET.get('source_group')
        reason = request.GET.get('reason')
        is_valid_duration = request.GET.get('is_valid_duration')
        is_long = request.GET.get('is_long')
        duration_bucket = request.GET.get('duration_bucket')
        duration_histogram_bucket = request.GET.get('duration_histogram_bucket')
        duration_min = request.GET.get('duration_min')
        duration_max = request.GET.get('duration_max')
        occurrence_period = request.GET.get('occurrence_period')
        cause_group = request.GET.get('cause_group')
        scope = request.GET.get('scope')
        province = request.GET.get('province')
        is_repeat = request.GET.get('is_repeat')

        def parse_duration_hours(value: str | None) -> float | None:
            if value in (None, ''):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def apply_detail_filters(queryset: QuerySet) -> QuerySet:
            if impact_level:
                impact_filters: dict[str, Q] = {
                    'total': Q_CLASS_TOTAL,
                    'class_i_ii': Q_CLASS_I_II,
                    'class_i': Q_CLASS_I,
                    'class_ii': Q_CLASS_II,
                    'class_iii': Q_CLASS_III,
                    'class_iv': Q_CLASS_IV,
                    'class_v': Q_CLASS_V,
                }
                if impact_level in impact_filters:
                    queryset = queryset.filter(impact_filters[impact_level])
            if category == 'overall_total':
                queryset = queryset.exclude(fault_category__in=OVERALL_EXCLUDED_TOTAL_CATEGORIES)
            elif category:
                queryset = queryset.filter(fault_category=category_aliases.get(category, category))

            normalized_resource_type = resource_type_aliases.get(resource_type, resource_type)
            if normalized_resource_type == 'unfilled':
                queryset = queryset.filter(Q(resource_type='') | Q(resource_type__isnull=True))
            elif normalized_resource_type:
                queryset = queryset.filter(resource_type=normalized_resource_type)

            if source_group == '自控':
                queryset = queryset.filter(
                    resource_type__in=[ResourceTypeChoices.SELF_BUILT, ResourceTypeChoices.COORDINATED]
                )
            elif source_group == '第三方':
                queryset = queryset.filter(resource_type=ResourceTypeChoices.LEASED)
            elif source_group == '其他/未填':
                queryset = queryset.filter(
                    Q(resource_type='') | Q(resource_type__isnull=True)
                    | ~Q(resource_type__in=[ResourceTypeChoices.SELF_BUILT, ResourceTypeChoices.COORDINATED, ResourceTypeChoices.LEASED])
                )

            if reason:
                queryset = queryset.filter(interruption_reason=reason_aliases.get(reason, reason))
            if occurrence_period == '日间':
                queryset = queryset.filter(fault_occurrence_time__hour__gte=6, fault_occurrence_time__hour__lt=18)
            elif occurrence_period == '夜间':
                queryset = queryset.filter(Q(fault_occurrence_time__hour__lt=6) | Q(fault_occurrence_time__hour__gte=18))
            if cause_group == '施工类':
                queryset = queryset.filter(interruption_reason='construction')
            elif cause_group == '非施工类':
                queryset = queryset.exclude(interruption_reason='construction')

            minimum_hours = parse_duration_hours(duration_min)
            maximum_hours = parse_duration_hours(duration_max)
            needs_duration = any([is_valid_duration == 'true', is_long == 'true', bool(duration_bucket), bool(duration_histogram_bucket), minimum_hours is not None, maximum_hours is not None])
            if needs_duration:
                queryset = queryset.annotate(
                    duration=ExpressionWrapper(
                        Coalesce(F('fault_recovery_time'), now) - F('fault_occurrence_time'),
                        output_field=DurationField(),
                    )
                )
            if is_valid_duration == 'true':
                queryset = queryset.filter(duration__gt=timedelta(minutes=30))
            if is_long == 'true':
                queryset = queryset.filter(duration__gte=timedelta(hours=6))

            duration_ranges: dict[str, tuple[float, float | None]] = {
                '6-8小时': (6, 8), '8-10小时': (8, 10),
                '10-12小时': (10, 12), '12小时以上': (12, None),
            }
            if duration_bucket in duration_ranges:
                lower, upper = duration_ranges[duration_bucket]
                queryset = queryset.filter(duration__gte=timedelta(hours=lower))
                if upper is not None:
                    queryset = queryset.filter(duration__lt=timedelta(hours=upper))

            if duration_histogram_bucket:
                if duration_histogram_bucket == '>24':
                    queryset = queryset.filter(duration__gt=timedelta(hours=24))
                else:
                    try:
                        histogram_upper = int(duration_histogram_bucket)
                    except (TypeError, ValueError):
                        histogram_upper = 0
                    if 1 <= histogram_upper <= 24:
                        if histogram_upper > 1:
                            queryset = queryset.filter(duration__gt=timedelta(hours=histogram_upper - 1))
                        queryset = queryset.filter(duration__lte=timedelta(hours=histogram_upper))
            if minimum_hours is not None:
                queryset = queryset.filter(duration__gte=timedelta(hours=minimum_hours))
            if maximum_hours is not None:
                queryset = queryset.filter(duration__lte=timedelta(hours=maximum_hours))

            if scope == 'branch_company':
                queryset = queryset.filter(province__name__in=BRANCH_PROVINCE_NAMES).exclude(handling_unit__name__in=EXCLUDED_HANDLING_UNITS)
            if province:
                queryset = queryset.filter(province__name=province)
            return queryset

        qs = apply_detail_filters(qs)
        ordering = request.GET.get('ordering', '-fault_occurrence_time')
        if ordering.replace('-', '') in ['fault_occurrence_time', 'duration']:
            if 'duration' in ordering:
                qs = qs.annotate(
                    duration=ExpressionWrapper(
                        Coalesce(F('fault_recovery_time'), now) - F('fault_occurrence_time'),
                        output_field=DurationField()
                    )
                )
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('-fault_occurrence_time')

        current_faults = list(qs)
        ui_repeat_ids: set[int] = set()
        matched_preceding_faults: list[OtnFault] = []
        if current_faults:
            fiber_faults = [fault for fault in current_faults if fault.is_fiber_fault]
            if fiber_faults:
                min_t = min(f.fault_occurrence_time for f in fiber_faults)
                preceding_qs = OtnFault.objects.filter(
                    fault_occurrence_time__gte=min_t - timedelta(days=60),
                    fault_occurrence_time__lt=start_date,
                    fault_category__in=[FaultCategoryChoices.FIBER_BREAK, 
                                        FaultCategoryChoices.FIBER_DEGRADATION, 
                                        FaultCategoryChoices.FIBER_JITTER]
                ).select_related(
                    'province', 'interruption_location_a', 'handling_unit'
                ).prefetch_related('interruption_location')
                preceding_qs = _apply_physical_province_filter(preceding_qs, selected_provinces)
                if scope == 'branch_company':
                    preceding_qs = preceding_qs.filter(
                        province__name__in=BRANCH_PROVINCE_NAMES
                    ).exclude(handling_unit__name__in=EXCLUDED_HANDLING_UNITS)
                if province:
                    preceding_qs = preceding_qs.filter(province__name=province)
                preceding_qs = apply_detail_filters(_annotate_class_i_business_impact(preceding_qs))
                preceding_faults = list(preceding_qs)
                repeat_result = detect_repeat_faults(
                    current_faults,
                    preceding_faults,
                    preceding_faults=preceding_faults,
                )
                ui_repeat_ids = repeat_result.ui_repeat_ids
                matched_preceding_faults = repeat_result.matched_preceding_faults
        if is_repeat == 'true':
            current_faults = [fault for fault in current_faults if fault.id in ui_repeat_ids]
        elif is_repeat == 'false':
            current_faults = [fault for fault in current_faults if fault.id not in ui_repeat_ids]
            matched_preceding_faults = []

        results = []
        for fault in current_faults:
            occ_time = fault.fault_occurrence_time
            end_t = fault.fault_recovery_time if fault.fault_recovery_time else now
            duration_hours = (end_t - occ_time).total_seconds() / 3600.0
            z_site_names = [s.name for s in fault.interruption_location.all()]
            
            results.append({
                'id': fault.id,
                'fault_number': fault.fault_number,
                'fault_occurrence_time': _format_local_datetime(occ_time),
                'fault_recovery_time': _format_local_datetime(fault.fault_recovery_time) if fault.fault_recovery_time else '未恢复',
                'duration': round(duration_hours, 2),
                'category': fault.get_fault_category_display(),
                'impact_level': _get_impact_level_display(fault, getattr(fault, 'has_class_i_business_impact', False)),
                'resource_type': fault.get_resource_type_display() if fault.resource_type else '未填写',
                'source_group': _source_group_for_fault(fault),
                'province': fault.province.name if fault.province else '未知',
                'reason': fault.get_interruption_reason_display() if fault.interruption_reason else '未填/未知',
                'site_a': fault.interruption_location_a.name if fault.interruption_location_a else '',
                'site_z': ', '.join(z_site_names),
                'is_repeat': fault.id in ui_repeat_ids,
                'is_long': duration_hours >= 6.0,
                'url': fault.get_absolute_url(),
                'in_period': True
            })

        for fault in matched_preceding_faults:
            occ_time = fault.fault_occurrence_time
            end_t = fault.fault_recovery_time if fault.fault_recovery_time else now
            duration_hours = (end_t - occ_time).total_seconds() / 3600.0
            z_site_names = [site.name for site in fault.interruption_location.all()]
            results.append({
                'id': fault.id,
                'fault_number': fault.fault_number,
                'fault_occurrence_time': _format_local_datetime(occ_time),
                'fault_recovery_time': _format_local_datetime(fault.fault_recovery_time) if fault.fault_recovery_time else '未恢复',
                'duration': round(duration_hours, 2),
                'category': fault.get_fault_category_display(),
                'impact_level': _get_impact_level_display(fault, getattr(fault, 'has_class_i_business_impact', False)),
                'resource_type': fault.get_resource_type_display() if fault.resource_type else '未填写',
                'source_group': _source_group_for_fault(fault),
                'province': fault.province.name if fault.province else '未知',
                'reason': fault.get_interruption_reason_display() if fault.interruption_reason else '未填/未知',
                'site_a': fault.interruption_location_a.name if fault.interruption_location_a else '',
                'site_z': ', '.join(z_site_names),
                'is_repeat': True,
                'is_long': duration_hours >= 6.0,
                'url': fault.get_absolute_url(),
                'in_period': False,
            })

        return JsonResponse({'results': results})


class FaultRepeatsAPI(PermissionRequiredMixin, View):
    """
    特定故障的关联重复故障列表接口。
    """
    permission_required = 'netbox_otnfaults.view_otnfault'
    
    def get(self, request) -> JsonResponse:
        fault_id = request.GET.get('fault_id')
        if not fault_id:
            return JsonResponse({'results': []})
        try:
            fault = OtnFault.objects.prefetch_related('interruption_location').get(pk=fault_id)
        except OtnFault.DoesNotExist:
            return JsonResponse({'results': []})
            
        if not fault.is_fiber_fault or not fault.fault_occurrence_time:
            return JsonResponse({'results': []})
            
        t = fault.fault_occurrence_time
        past_qs = OtnFault.objects.filter(
            fault_occurrence_time__gte=t - timedelta(days=60),
            fault_occurrence_time__lt=t + timedelta(days=60),
            fault_category__in=[FaultCategoryChoices.FIBER_BREAK, 
                                FaultCategoryChoices.FIBER_DEGRADATION, 
                                FaultCategoryChoices.FIBER_JITTER]
        ).select_related('province', 'interruption_location_a', 'handling_unit').prefetch_related('interruption_location')
        
        z_ids = set(s.id for s in fault.interruption_location.all())
        matched_faults = []
        for f in past_qs:
            if f.id == fault.id:
                continue
            if f.interruption_location_a_id == fault.interruption_location_a_id:
                f_z_ids = set(s.id for s in f.interruption_location.all())
                if z_ids.intersection(f_z_ids):
                    matched_faults.append(f)
        
        all_matched = [fault] + sorted(matched_faults, key=lambda x: x.fault_occurrence_time)
        
        results = []
        now = timezone.localtime()
        for f in all_matched:
            occ_time = f.fault_occurrence_time
            end_t = f.fault_recovery_time if f.fault_recovery_time else now
            duration_hours = (end_t - occ_time).total_seconds() / 3600.0
            z_site_names = [s.name for s in f.interruption_location.all()]
            results.append({
                'id': f.id,
                'fault_number': f.fault_number,
                'fault_occurrence_time': _format_local_datetime(occ_time),
                'fault_recovery_time': _format_local_datetime(f.fault_recovery_time) if f.fault_recovery_time else '未恢复',
                'duration': round(duration_hours, 2),
                'category': f.get_fault_category_display(),
                'resource_type': f.get_resource_type_display() if f.resource_type else '未填写',
                'source_group': _source_group_for_fault(f),
                'province': f.province.name if f.province else '未知',
                'reason': f.get_interruption_reason_display() if f.interruption_reason else '未填/未知',
                'site_a': f.interruption_location_a.name if f.interruption_location_a else '',
                'site_z': ', '.join(z_site_names),
                'is_repeat': True,
                'is_long': duration_hours >= 6.0,
                'url': f.get_absolute_url(),
                'in_period': True if (t - timedelta(seconds=1)) <= f.fault_occurrence_time <= (t + timedelta(seconds=1)) else False
            })
        return JsonResponse({'results': results})


class ServiceStatisticsDetailsAPI(PermissionRequiredMixin, View):
    """
    业务受影响明细接口。
    """
    permission_required = 'netbox_otnfaults.view_otnfaultimpact'
    
    def get(self, request) -> JsonResponse:
        start_date, end_date, prev_start_date, prev_end_date, filter_type = _parse_time_range(request)
        now = timezone.localtime()
        
        impacts_qs = OtnFaultImpact.objects.select_related(
            'otn_fault', 'bare_fiber_service', 'bare_fiber_service__tenant_group', 'circuit_service'
        ).filter(
            service_interruption_time__gte=start_date,
            service_interruption_time__lt=end_date
        ).filter(
            Q(service_type=ServiceTypeChoices.BARE_FIBER, business_impact=BusinessImpactChoices.INTERRUPTED)
            | Q(service_type=ServiceTypeChoices.CIRCUIT, business_impact=BusinessImpactChoices.INTERRUPTED)
        )
        
        service_type = request.GET.get('service_type')
        service_type_aliases: dict[str, str] = {
            '裸纤业务': ServiceTypeChoices.BARE_FIBER,
            '电路业务': ServiceTypeChoices.CIRCUIT,
        }
        service_type = service_type_aliases.get(service_type, service_type)
        if service_type:
            impacts_qs = impacts_qs.filter(service_type=service_type)
            
        service_key = request.GET.get('service_key')
        if service_key:
            if service_key.startswith('bf_'):
                impacts_qs = impacts_qs.filter(bare_fiber_service_id=service_key.split('_')[1])
            elif service_key.startswith('cs_'):
                impacts_qs = impacts_qs.filter(circuit_service_id=service_key.split('_')[1])
                
        is_long = request.GET.get('is_long')
        if is_long == 'true':
            impacts_qs = impacts_qs.annotate(
                duration=ExpressionWrapper(
                    Coalesce(F('service_recovery_time'), now) - F('service_interruption_time'),
                    output_field=DurationField()
                )
            ).filter(duration__gte=timedelta(hours=6))
            
        ordering = request.GET.get('ordering', '-service_interruption_time')
        if ordering.replace('-', '') in ['service_interruption_time', 'duration']:
            if 'duration' in ordering:
                impacts_qs = impacts_qs.annotate(
                    duration=ExpressionWrapper(
                        Coalesce(F('service_recovery_time'), now) - F('service_interruption_time'),
                        output_field=DurationField()
                    )
                )
            impacts_qs = impacts_qs.order_by(ordering)
        else:
            impacts_qs = impacts_qs.order_by('-service_interruption_time')
            
        page_impacts = list(impacts_qs)
        
        results = []
        for imp in page_impacts:
            svc_start = imp.service_interruption_time
            svc_end = imp.service_recovery_time if imp.service_recovery_time else now
            dur_hours = (svc_end - svc_start).total_seconds() / 3600.0
            
            if imp.service_type == ServiceTypeChoices.BARE_FIBER and imp.bare_fiber_service:
                svc_key = f'bf_{imp.bare_fiber_service_id}'
                svc_name = imp.bare_fiber_service.name
                svc_type_label = '裸纤业务'
            elif imp.service_type == ServiceTypeChoices.CIRCUIT and imp.circuit_service:
                svc_key = f'cs_{imp.circuit_service_id}'
                svc_name = imp.circuit_service.special_line_name or imp.circuit_service.name
                svc_type_label = '电路业务'
            else:
                svc_key = f'unknown_{imp.id}'
                svc_name = str(imp)
                svc_type_label = '未知'
                
            results.append({
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
            
        return JsonResponse({'results': results})

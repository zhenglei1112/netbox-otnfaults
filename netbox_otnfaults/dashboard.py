import json
import traceback
import calendar
from datetime import date, timedelta
from urllib.parse import urlencode
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from extras.dashboard.widgets import DashboardWidget, register_widget
from .models import OtnFault, FaultCategoryChoices


# --- 故障分类 → CSS 颜色映射 ---
CATEGORY_CSS_COLORS: dict[str, str] = {
    FaultCategoryChoices.AC_FAULT: '#F4C542',
    FaultCategoryChoices.FIBER_BREAK: '#E53935',
    FaultCategoryChoices.POWER_FAULT: '#2F6BFF',
    FaultCategoryChoices.DEVICE_FAULT: '#8B5CF6',
}


CALENDAR_VISIBLE_FAULT_CATEGORIES: tuple[str, ...] = (
    FaultCategoryChoices.AC_FAULT,
    FaultCategoryChoices.FIBER_BREAK,
    FaultCategoryChoices.POWER_FAULT,
    FaultCategoryChoices.DEVICE_FAULT,
)


CHINA_PUBLIC_HOLIDAYS: set[date] = {
    date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3),
    date(2026, 2, 15), date(2026, 2, 16), date(2026, 2, 17),
    date(2026, 2, 18), date(2026, 2, 19), date(2026, 2, 20),
    date(2026, 2, 21), date(2026, 2, 22), date(2026, 2, 23),
    date(2026, 4, 4), date(2026, 4, 5), date(2026, 4, 6),
    date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3),
    date(2026, 5, 4), date(2026, 5, 5),
    date(2026, 6, 19), date(2026, 6, 20), date(2026, 6, 21),
    date(2026, 9, 25), date(2026, 9, 26), date(2026, 9, 27),
    date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3),
    date(2026, 10, 4), date(2026, 10, 5), date(2026, 10, 6),
    date(2026, 10, 7),
}

CHINA_MAKEUP_WORKDAYS: set[date] = {
    date(2026, 1, 4),
    date(2026, 2, 14),
    date(2026, 2, 28),
    date(2026, 5, 9),
    date(2026, 9, 20),
    date(2026, 10, 10),
}


def _get_china_holiday_marker(day: date) -> str:
    if day in CHINA_PUBLIC_HOLIDAYS:
        return '休'
    if day in CHINA_MAKEUP_WORKDAYS:
        return '班'
    return ''


@register_widget
class OtnFaultsCalendarWidget(DashboardWidget):
    """月历热点小组件：用彩色圆点标注每天发生的故障"""
    default_title = "故障月历"
    description = "以当月日历展示每日故障分布，不同颜色圆点代表不同故障分类。"
    width = 4
    height = 4

    def render(self, request) -> str:
        try:
            now = timezone.localtime()
            year, month = now.year, now.month
            today_day = now.day

            # 本月起止范围
            first_day = date(year, month, 1)
            _, days_in_month = calendar.monthrange(year, month)
            last_day = date(year, month, days_in_month)
            first_weekday = first_day.weekday()  # 0=周一
            calendar_start = first_day - timedelta(days=first_weekday)

            # 查询当前日历可见范围内的故障（按 fault_occurrence_time）
            faults = OtnFault.objects.restrict(request.user, 'view').filter(
                fault_occurrence_time__date__gte=calendar_start,
                fault_occurrence_time__date__lte=last_day,
                fault_category__in=CALENDAR_VISIBLE_FAULT_CATEGORIES,
            ).values_list('fault_occurrence_time', 'fault_category')

            # 按日期分组 → {date: [color, color, ...]}
            day_dots: dict[date, list[str]] = {}
            for occ_time, cat in faults:
                if cat not in CALENDAR_VISIBLE_FAULT_CATEGORIES:
                    continue
                fault_day = timezone.localtime(occ_time).date()
                color = CATEGORY_CSS_COLORS.get(cat, '#adb5bd')
                day_dots.setdefault(fault_day, []).append(color)

            # 构造日历网格 (weeks × 7)
            fault_list_base_url = reverse('plugins:netbox_otnfaults:otnfault_list')
            cal_cells: list[dict[str, object] | None] = []
            for offset in range(first_weekday):
                day_date = calendar_start + timedelta(days=offset)
                holiday_marker = _get_china_holiday_marker(day_date)
                fault_list_query = urlencode({
                    'fault_occurrence_time_after': f'{day_date.isoformat()} 00:00:00',
                    'fault_occurrence_time_before': f'{day_date.isoformat()} 23:59:59',
                })
                cal_cells.append({
                    'day': day_date.day,
                    'date': day_date.isoformat(),
                    'dots': day_dots.get(day_date, []),
                    'is_today': False,
                    'is_current_month': day_date.month == month,
                    'fault_list_url': f'{fault_list_base_url}?{fault_list_query}',
                    'holiday_marker': holiday_marker,
                })
            for d in range(1, days_in_month + 1):
                day_date = date(year, month, d)
                holiday_marker = _get_china_holiday_marker(day_date)
                fault_list_query = urlencode({
                    'fault_occurrence_time_after': f'{day_date.isoformat()} 00:00:00',
                    'fault_occurrence_time_before': f'{day_date.isoformat()} 23:59:59',
                })
                cal_cells.append({
                    'day': d,
                    'date': day_date.isoformat(),
                    'dots': day_dots.get(day_date, []),
                    'is_today': d == today_day,
                    'is_current_month': day_date.month == month,
                    'fault_list_url': f'{fault_list_base_url}?{fault_list_query}',
                    'holiday_marker': holiday_marker,
                })
            # 补齐最后一行到 7 的倍数
            while len(cal_cells) % 7 != 0:
                cal_cells.append(None)

            # 分行
            weeks = [cal_cells[i:i + 7] for i in range(0, len(cal_cells), 7)]

            # 图例 (去重保留出现过的分类)
            seen_cats: set[str] = set()
            legend: list[dict[str, str]] = []
            cat_label_map = {c[0]: str(c[1]) for c in FaultCategoryChoices.CHOICES}
            for _, cat in faults:
                if cat and cat in CALENDAR_VISIBLE_FAULT_CATEGORIES and cat not in seen_cats:
                    seen_cats.add(cat)
                    legend.append({
                        'color': CATEGORY_CSS_COLORS.get(cat, '#adb5bd'),
                        'label': cat_label_map.get(cat, cat),
                    })

            return render_to_string(
                'netbox_otnfaults/inc/dashboard_calendar_widget.html',
                {
                    'year': year,
                    'month': month,
                    'weeks': weeks,
                    'legend': legend,
                    'weeks_json': json.dumps(weeks, ensure_ascii=False),
                },
                request=request,
            )
        except Exception as e:
            error_trace = traceback.format_exc()
            return f'<div class="alert alert-danger"><pre style="font-size:11px;white-space:pre-wrap">{error_trace}</pre></div>'


@register_widget
class OtnFaultsPendingReviewWidget(DashboardWidget):
    """待复核故障小组件：显示当前用户作为线路主管的待复核故障数"""
    default_title = "待复核故障"
    description = "显示当前登录用户作为线路主管、尚未完成线路主管复核的故障数量。"
    width = 2
    height = 2

    def render(self, request) -> str:
        try:
            from django.urls import reverse
            from django.db.models import Q

            # 查询：线路主管未复核(manager_reviewed) 或 网管人员未复核(noc_reviewed)
            pending_count = OtnFault.objects.restrict(request.user, 'view').filter(
                Q(line_manager=request.user, manager_reviewed=False) |
                Q(operations_manager=request.user, noc_reviewed=False),
            ).distinct().count()

            # 构造跳转 URL：因为内置的过滤器通过字典查询是 AND 关系，
            # 我们在 filtersets 中加了一个 my_pending_review_faults 自动支持 OR 组过滤
            review_url = (
                reverse('plugins:netbox_otnfaults:otnfault_list')
                + f'?my_pending_review_faults={request.user.pk}'
            )

            return render_to_string(
                'netbox_otnfaults/inc/dashboard_pending_review_widget.html',
                {
                    'pending_count': pending_count,
                    'review_url': review_url,
                },
                request=request,
            )
        except Exception as e:
            error_trace = traceback.format_exc()
            return f'<div class="alert alert-danger"><pre style="font-size:11px;white-space:pre-wrap">{error_trace}</pre></div>'

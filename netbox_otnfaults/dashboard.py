import json
import traceback
import calendar
from datetime import date
from django.template.loader import render_to_string
from django.utils import timezone
from extras.dashboard.widgets import DashboardWidget, register_widget
from .models import OtnFault, FaultCategoryChoices


# --- 故障分类 → CSS 颜色映射 ---
CATEGORY_CSS_COLORS: dict[str, str] = {
    'fiber_break': '#dc3545',       # 红
    'ac_fault': '#0d6efd',          # 蓝
    'fiber_degradation': '#fd7e14', # 橙
    'fiber_jitter': '#ffc107',      # 黄
    'device_fault': '#d63384',      # 粉
    'power_fault': '#6f42c1',       # 紫
}


@register_widget
class OtnFaultsCalendarWidget(DashboardWidget):
    """月历热点小组件：用彩色圆点标注每天发生的故障"""
    default_title = "故障月历"
    description = "以当月日历展示每日故障分布，不同颜色圆点代表不同故障分类。"
    width = 4
    height = 4

    def render(self, request) -> str:
        try:
            now = timezone.localtime(timezone.now())
            year, month = now.year, now.month
            today_day = now.day

            # 本月起止范围
            first_day = date(year, month, 1)
            _, days_in_month = calendar.monthrange(year, month)
            last_day = date(year, month, days_in_month)

            # 查询本月所有故障（按 fault_occurrence_time）
            faults = OtnFault.objects.restrict(request.user, 'view').filter(
                fault_occurrence_time__date__gte=first_day,
                fault_occurrence_time__date__lte=last_day,
            ).values_list('fault_occurrence_time', 'fault_category')

            # 按天分组 → {day: [color, color, ...]}
            day_dots: dict[int, list[str]] = {}
            for occ_time, cat in faults:
                day = timezone.localtime(occ_time).day
                color = CATEGORY_CSS_COLORS.get(cat, '#adb5bd')
                day_dots.setdefault(day, []).append(color)

            # 限制每天最多显示 5 个点（避免爆格）
            for day in day_dots:
                day_dots[day] = day_dots[day][:5]

            # 构造日历网格 (weeks × 7)
            # weekday: 0=Monday, 6=Sunday
            first_weekday = first_day.weekday()  # 0=周一
            cal_cells: list[dict | None] = [None] * first_weekday
            for d in range(1, days_in_month + 1):
                cal_cells.append({
                    'day': d,
                    'dots': day_dots.get(d, []),
                    'is_today': d == today_day,
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
                if cat and cat not in seen_cats:
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

"""
OTN 故障统计展示页面 - 后端视图

提供独立的统计看板以及聚合API（兼容ECharts等前端工具及下钻查询）。
"""
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q, F, Func, DurationField, ExpressionWrapper
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import View
from datetime import timedelta, date
from django.db.models.functions import TruncDate, Coalesce, Cast
from decimal import Decimal
from urllib.parse import quote

from .models import (
    OtnFault, OtnFaultImpact, OtnPath,
    FaultCategoryChoices, ResourceTypeChoices, CableTypeChoices,
    ServiceTypeChoices, FaultStatusChoices
)
from dcim.models import Region
from .statistics_period import build_period_display


def _sorted_count_items(counts: dict[str, int]) -> list[dict[str, int]]:
    return [
        {'name': name, 'value': count}
        for name, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]


def _parse_time_range(request):
    """从请求参数解析时间范围，返回 (start_date, end_date, prev_start_date, prev_end_date, filter_type)"""
    filter_type: str = request.GET.get('filter_type', 'year')
    year: int = int(request.GET.get('year', timezone.now().year))
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
        
        overall_total_count = len(all_faults)
        overall_category_stats = {}
        for f in all_faults:
            cat_display = f.get_fault_category_display() if f.fault_category else '未知'
            if cat_display not in overall_category_stats:
                overall_category_stats[cat_display] = {'count': 0, 'duration': 0.0}
            overall_category_stats[cat_display]['count'] += 1

        # 然后再构建基础查询集（现根据要求，后续绝大多数统计详情均采用“光缆中断概览”约束条件，即仅限光缆中断）
        qs = qs_all.filter(fault_category=FaultCategoryChoices.FIBER_BREAK)

        # 提取当前期光缆中断故障
        qs_current = qs.filter(fault_occurrence_time__gte=start_date, fault_occurrence_time__lt=end_date)
        faults = list(qs_current)
        
        # 提取上一期故障并计算其 KPI
        prev_total_count = 0
        prev_total_duration = 0.0
        prev_long_faults = 0
        prev_repeat_faults = 0
        prev_avg_duration = 0.0
        
        if prev_start_date and prev_end_date:
            qs_prev = qs.filter(fault_occurrence_time__gte=prev_start_date, fault_occurrence_time__lt=prev_end_date)
            prev_faults = list(qs_prev)
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
        category_stats = {}

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
            # 1. 属性 (自建/租赁/协调)
            r_type = fault.resource_type or '未指定'
            r_type_display = fault.get_resource_type_display() if fault.resource_type else '未指定'
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


            
            # 明细存储（仅返回精简信息给前端作本地过滤或列表展示)
            dt_end = fault.fault_recovery_time.strftime('%Y-%m-%d %H:%M') if fault.fault_recovery_time else '未恢复'
            z_site_names = [s.name for s in fault.interruption_location.all()]
            
            details.append({
                'id': fault.id,
                'fault_number': fault.fault_number,
                'fault_occurrence_time': occ_time.strftime('%Y-%m-%d %H:%M'),
                'fault_recovery_time': dt_end,
                'duration': round(duration_hours, 2),
                'category': fault.get_fault_category_display(),
                'resource_type': r_type_display,
                'province': prov_name,
                'reason': reason,
                'site_a': fault.interruption_location_a.name if fault.interruption_location_a else '',
                'site_z': ', '.join(z_site_names),
                'is_repeat': is_repeat,
                'is_long': duration_hours >= 6.0,
                'url': fault.get_absolute_url()
            })

        cable_break_faults = [
            fault for fault in faults
            if fault.fault_category == FaultCategoryChoices.FIBER_BREAK
            and fault.fault_status != FaultStatusChoices.SUSPENDED
        ]
        cable_break_reason_counts: dict[str, int] = {}
        cable_break_source_counts: dict[str, int] = {}
        cable_break_total_duration: float = 0.0
        cable_break_reason_duration: dict[str, float] = {}
        cable_break_source_duration: dict[str, float] = {}
        cable_break_long_duration_buckets: dict[str, int] = {
            '6-8小时': 0,
            '8-10小时': 0,
            '10-12小时': 0,
            '12小时以上': 0,
        }
        
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
        
        cable_break_histogram: dict[int, int] = {i: 0 for i in range(13)}

        for fault in cable_break_faults:
            reason = fault.get_interruption_reason_display() if fault.interruption_reason else '未填/未知'
            if fault.resource_type == ResourceTypeChoices.SELF_BUILT:
                source = '自控'
            elif fault.resource_type in [ResourceTypeChoices.COORDINATED, ResourceTypeChoices.LEASED]:
                source = '第三方'
            else:
                source = '其他/未填'
            cable_break_reason_counts[reason] = cable_break_reason_counts.get(reason, 0) + 1
            cable_break_source_counts[source] = cable_break_source_counts.get(source, 0) + 1

            end_t = fault.fault_recovery_time if fault.fault_recovery_time else now
            duration_hours = (end_t - fault.fault_occurrence_time).total_seconds() / 3600.0
            
            hist_bucket = min(12, int(duration_hours))
            cable_break_histogram[hist_bucket] += 1
            
            cable_break_total_duration += duration_hours
            cable_break_reason_duration[reason] = cable_break_reason_duration.get(reason, 0.0) + duration_hours
            cable_break_source_duration[source] = cable_break_source_duration.get(source, 0.0) + duration_hours
            
            if 6.0 <= duration_hours < 8.0:
                cable_break_long_duration_buckets['6-8小时'] += 1
            elif 8.0 <= duration_hours < 10.0:
                cable_break_long_duration_buckets['8-10小时'] += 1
            elif 10.0 <= duration_hours < 12.0:
                cable_break_long_duration_buckets['10-12小时'] += 1
            elif duration_hours >= 12.0:
                cable_break_long_duration_buckets['12小时以上'] += 1
                
            if duration_hours > 0.5:
                cb_valid_count += 1
                cb_valid_dur += duration_hours
                
            occ_hour = fault.fault_occurrence_time.astimezone(timezone.get_current_timezone()).hour if fault.fault_occurrence_time else 0
            if 6 <= occ_hour < 18:
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
                
        cable_break_avg_metrics = {
             'overall_avg': round(cable_break_total_duration / len(cable_break_faults) if len(cable_break_faults) > 0 else 0.0, 2),
             'valid_avg': round(cb_valid_dur / cb_valid_count if cb_valid_count > 0 else 0.0, 2),
             'daytime_avg': round(cb_day_dur / cb_day_count if cb_day_count > 0 else 0.0, 2),
             'nighttime_avg': round(cb_night_dur / cb_night_count if cb_night_count > 0 else 0.0, 2),
             'construction_avg': round(cb_cons_dur / cb_cons_count if cb_cons_count > 0 else 0.0, 2),
             'non_construction_avg': round(cb_noncons_dur / cb_noncons_count if cb_noncons_count > 0 else 0.0, 2),
        }

        avg_duration_hours = total_duration_hours / total_count if total_count > 0 else 0.0
        
        hist_data = []
        cb_count_total = len(cable_break_faults)
        for i in range(13):
            label = f"[{i}, {i+1})" if i < 12 else "≥12"
            count = cable_break_histogram[i]
            pct = round(count * 100.0 / cb_count_total, 1) if cb_count_total > 0 else 0.0
            hist_data.append({'label': label, 'value': count, 'percent': pct})

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
                'resource': [{'name': k, 'value': v['count'], 'duration': round(v['duration'], 2), 'key': v['id']} for k, v in resource_stats.items()],
                'province': [{'name': k, 'value': v['count'], 'duration': round(v['duration'], 2)} for k, v in sorted(province_stats.items(), key=lambda item: item[1]['count'], reverse=True)],
                'reason': [{'name': k, 'value': v['count'], 'duration': round(v['duration'], 2)} for k, v in sorted(reason_stats.items(), key=lambda item: item[1]['count'], reverse=True)],
                'category': [{'name': k, 'value': v['count'], 'duration': round(v['duration'], 2)} for k, v in sorted(overall_category_stats.items(), key=lambda item: item[1]['count'], reverse=True)],
            },
            'cable_break_overview': {
                'total_count': len(cable_break_faults),
                'total_duration': round(cable_break_total_duration, 2),
                'reason_top3': _sorted_count_items(cable_break_reason_counts)[:3],
                'source_counts': _sorted_count_items(cable_break_source_counts),
                'reason_duration_top3': _sorted_count_items(cable_break_reason_duration)[:3],
                'source_duration_counts': _sorted_count_items(cable_break_source_duration),
                'long_duration_buckets': cable_break_long_duration_buckets,
                'avg_metrics': cable_break_avg_metrics,
                'histogram': hist_data,
            },
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

        # 查询当前期的所有 FaultImpact
        impacts_qs = OtnFaultImpact.objects.select_related(
            'otn_fault', 'bare_fiber_service', 'circuit_service'
        ).filter(
            service_interruption_time__gte=start_date,
            service_interruption_time__lt=end_date
        )
        impacts = list(impacts_qs)

        # 计算周期总小时数（用于 SLA）
        period_total_hours: float = (end_date - start_date).total_seconds() / 3600.0

        # 按业务 key 聚合
        service_map: dict = {}  # key -> stats dict

        for imp in impacts:
            # 确定业务标识和名称
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

            if svc_key not in service_map:
                service_map[svc_key] = {
                    'name': svc_name,
                    'type': svc_type_label,
                    'count': 0,
                    'break_count': 0,   # 中断
                    'jitter_count': 0,  # 抖动
                    'degrade_count': 0, # 劣化
                    'other_count': 0,
                    'total_duration': 0.0,
                    'long_count': 0,
                    'intervals': [],  # 用于 SLA 合并时段
                    'occurrence_times': [],  # 用于重复判断
                }

            stats = service_map[svc_key]
            stats['count'] += 1

            # 分类计数
            fault_cat = imp.otn_fault.fault_category if imp.otn_fault else None
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

            if dur_hours >= 6.0:
                stats['long_count'] += 1

            # 记录时段供 SLA 计算（合并重叠）
            stats['intervals'].append((svc_start, svc_end))
            # 记录发生时间供重复判断
            stats['occurrence_times'].append(svc_start)

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

            services_result.append({
                'key': svc_key,
                'name': stats['name'],
                'type': stats['type'],
                'count': count,
                'break_count': stats['break_count'],
                'jitter_count': stats['jitter_count'],
                'degrade_count': stats['degrade_count'],
                'other_count': stats['other_count'],
                'total_duration': round(total_dur, 2),
                'avg_duration': round(avg_dur, 2),
                'long_count': stats['long_count'],
                'repeat_count': repeat_count,
                'sla': round(sla, 4),
            })

        # 按故障总数降序排列
        services_result.sort(key=lambda x: x['count'], reverse=True)

        # 展示日期
        display_end_date_str = ''
        if end_date:
            display_end_date = end_date - timedelta(days=1)
            display_end_date_str = display_end_date.strftime('%Y-%m-%d')

        return JsonResponse({
            'period': build_period_display(start_date, end_date, now),
            'period_total_hours': round(period_total_hours, 2),
            'services': services_result,
        })




"""
OTN 故障统计展示页面 - 后端视图

提供独立的统计看板以及聚合API（兼容ECharts等前端工具及下钻查询）。
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q, F, Func, DurationField, ExpressionWrapper
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import View
from datetime import timedelta, date
from django.db.models.functions import TruncDate, Coalesce, Cast
from decimal import Decimal

from .models import (
    OtnFault, OtnFaultImpact, OtnPath,
    FaultCategoryChoices, ResourceTypeChoices, CableTypeChoices
)

class FaultStatisticsPageView(PermissionRequiredMixin, View):
    """
    故障多维统计与下钻展示页面 - 渲染主HTML
    """
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request):
        now = timezone.now()
        # 传入可选年份给前端
        oldest_fault = OtnFault.objects.order_by('fault_occurrence_time').first()
        start_year = oldest_fault.fault_occurrence_time.year if oldest_fault and oldest_fault.fault_occurrence_time else max(now.year - 5, 2020)
        
        years = list(range(start_year, now.year + 1))
        years.reverse()
        
        # 计算智能默认值：如果是每个月第一周（前7天），显示上月；否则显示上周
        if now.day <= 7:
            default_filter_type = 'month'
            if now.month == 1:
                default_year = now.year - 1
                default_month = 12
            else:
                default_year = now.year
                default_month = now.month - 1
            default_week = now.isocalendar()[1]
        else:
            default_filter_type = 'week'
            last_week_date = now - timedelta(days=7)
            default_year = last_week_date.isocalendar()[0]
            default_week = last_week_date.isocalendar()[1]
            default_month = now.month

        if default_year not in years:
            years.append(default_year)
            years.sort(reverse=True)
        
        return render(request, 'netbox_otnfaults/statistics_dashboard.html', {
            'years': years,
            'default_filter_type': default_filter_type,
            'default_year': default_year,
            'default_month': default_month,
            'default_week': default_week,
        })

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
        filter_type = request.GET.get('filter_type', 'year')
        year = int(request.GET.get('year', timezone.now().year))

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
            # ISO 周的起点 (周一)
            first_day_of_year = date(year, 1, 4) # Jan 4 is always in week 1
            start_of_week1 = first_day_of_year - timedelta(days=first_day_of_year.isoweekday() - 1)
            start_date_dt = start_of_week1 + timedelta(weeks=week - 1)
            start_date = timezone.datetime.combine(start_date_dt, timezone.datetime.min.time(), tzinfo=tz)
            
            end_date = start_date + timedelta(days=7)
            prev_start_date = start_date - timedelta(days=7)
            prev_end_date = start_date

        else:
            # 默认今年
            start_date = timezone.datetime(year, 1, 1, tzinfo=tz)
            end_date = timezone.datetime(year + 1, 1, 1, tzinfo=tz)
            prev_start_date = timezone.datetime(year - 1, 1, 1, tzinfo=tz)
            prev_end_date = start_date

        # 构建基础查询集
        qs = OtnFault.objects.select_related('province', 'interruption_location_a').prefetch_related('interruption_location')

        # 提取当前期故障
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

        avg_duration_hours = total_duration_hours / total_count if total_count > 0 else 0.0

        # 为了展示准确的截止自然日（例如周日而非下周一，10月31日而非11月1日），展示日期需减去一天
        display_end_date_str = ''
        if end_date:
            display_end_date = end_date - timedelta(days=1)
            display_end_date_str = display_end_date.strftime('%Y-%m-%d')

        # 返回 JSON 结构
        return JsonResponse({
            'period': {
                'start': start_date.strftime('%Y-%m-%d') if start_date else '',
                'end': display_end_date_str
            },
            'kpis': {
                'total_count': total_count,
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
            },
            'details': details
        })

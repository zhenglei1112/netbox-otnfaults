"""
OTN 全国网络故障自动化大屏 - 后端视图

提供大屏页面渲染和聚合数据 API。
"""
from django.shortcuts import render
from django.templatetags.static import static
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from django.db.models import Count
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import View
from django.core.serializers.json import DjangoJSONEncoder
from datetime import timedelta
import json

from .models import (
    OtnFault, OtnFaultImpact, OtnPath, OtnPathGroup,
    CutoverTask, HeavyDuty,
    CutoverStatusChoices, FaultCategoryChoices, FaultStatusChoices, UrgencyChoices,
)
from .dashboard_topology import build_fault_path_overlays
from .services.fault_coordinates import resolve_fault_coordinates


def get_plugin_settings() -> dict:
    """获取插件配置"""
    return settings.PLUGINS_CONFIG.get('netbox_otnfaults', {})


# 告警色彩配置
ALERT_COLORS = {
    'critical': '#FF1E1E',
    'major': '#FF8A00',
    'minor': '#FADB14',
    'normal': '#00D2FF',
}

# 故障分类到告警级别的映射
CATEGORY_SEVERITY = {
    'fiber_break': 'critical',
    'power_fault': 'major',
    'device_fault': 'major',
    'fiber_degradation': 'minor',
    'fiber_jitter': 'minor',
    'ac_fault': 'minor',
}

# 故障分类颜色（HEX）
CATEGORY_COLORS = {
    'fiber_break': '#6F42C1',
    'power_fault': '#6610F2',
    'device_fault': '#FF8A00',
    'fiber_degradation': '#FF8A00',
    'fiber_jitter': '#0DCAF0',
    'ac_fault': '#20C997',
}

CATEGORY_NAMES = {
    'fiber_break': '光缆中断',
    'power_fault': '供电故障',
    'device_fault': '设备故障',
    'fiber_degradation': '光缆劣化',
    'fiber_jitter': '光缆抖动',
    'ac_fault': '空调故障',
}

STATUS_COLORS = {
    'processing': '#FF1E1E',
    'temporary_recovery': '#3B82F6',
    'suspended': '#FADB14',
    'closed': '#10B981',
}

STATUS_NAMES = {
    'processing': '处理中',
    'temporary_recovery': '临时恢复',
    'suspended': '延后处置',
    'closed': '已关闭',
}


def _format_duration_seconds(total_seconds: int) -> str:
    if total_seconds < 0:
        return ""
    d = total_seconds // 86400
    h = (total_seconds % 86400) // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    
    units = [
        (d, "天"),
        (h, "小时"),
        (m, "分"),
        (s, "秒"),
    ]
    for index, (value, _) in enumerate(units):
        if value > 0:
            return "".join(f"{amount}{label}" for amount, label in units[index:])
    return "0秒"


class DashboardPageView(PermissionRequiredMixin, View):
    """大屏页面视图 - 渲染全屏 HTML"""
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request):
        plugin_settings = get_plugin_settings()

        return render(request, 'netbox_otnfaults/dashboard.html', {
            'apikey': plugin_settings.get('map_api_key', ''),
            'map_center': json.dumps(plugin_settings.get('map_default_center', [104.0, 34.3])),
            'map_zoom': plugin_settings.get('map_default_zoom', 4.0),
            'map_pitch': plugin_settings.get('map_default_pitch', 32),
            'use_local_basemap': plugin_settings.get('use_local_basemap', False),
            'local_tiles_url': plugin_settings.get('local_tiles_url', ''),
            'local_glyphs_url': plugin_settings.get('local_glyphs_url', ''),
            'otn_paths_pmtiles_url': plugin_settings.get('otn_paths_pmtiles_url', ''),
            'colors_config': json.dumps({
                'category_colors': CATEGORY_COLORS,
                'category_names': CATEGORY_NAMES,
                'status_colors': STATUS_COLORS,
                'status_names': STATUS_NAMES,
                'alert_colors': ALERT_COLORS,
                'category_severity': CATEGORY_SEVERITY,
            }, cls=DjangoJSONEncoder),
        })


class DashboardDataAPI(PermissionRequiredMixin, View):
    """大屏聚合数据 API - 一次返回所有大屏所需数据"""
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request) -> JsonResponse:
        now = timezone.localtime()
        twenty_four_hours_ago = now - timedelta(hours=24)
        cutover_window_end = now + timedelta(days=7)
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # ── 1. 活跃故障（处理中）──
        processing_faults_qs = OtnFault.objects.filter(
            fault_status=FaultStatusChoices.PROCESSING
        )

        active_faults_qs = processing_faults_qs.select_related(
            'province', 'interruption_location_a', 'handling_unit'
        ).prefetch_related(
            'interruption_location', 'impacts', 'impacts__bare_fiber_service', 'impacts__circuit_service'
        )

        active_faults = []
        for fault in active_faults_qs:
            resolved = resolve_fault_coordinates(fault)
            if resolved is None:
                continue
            lat, lng = resolved.lat, resolved.lng

            # ── 智能对位纠偏 (中国区域特征检测) ──
            # 标准: 经度 [73, 135], 纬度 [4, 53]
            # 逻辑: 若 lat > 70 且 lng < 60，极大概率是录入时填反了，进行逻辑交换
            if lat > 70.0 and lng < 60.0:
                old_lat, old_lng = lat, lng
                lat, lng = old_lng, old_lat
                # 此处不直接触发 print，但在调试时可通过 fault_number 追踪
                # print(f"检测到坐标反置，已自动校正: {fault.fault_number} -> ({lat}, {lng})")

            z_sites = [s.name for s in fault.interruption_location.all()]
            impact_count = fault.impacts.count()
            impact_names = []
            for imp in fault.impacts.all():
                if imp.service_type == 'bare_fiber' and imp.bare_fiber_service:
                    impact_names.append(imp.bare_fiber_service.name)
                elif imp.service_type == 'circuit' and imp.circuit_service:
                    impact_names.append(imp.circuit_service.name)

            # 计算优先级得分
            age_minutes = (now - fault.fault_occurrence_time).total_seconds() / 60 if fault.fault_occurrence_time else 0
            severity = CATEGORY_SEVERITY.get(fault.fault_category, 'minor')
            severity_weight = {'critical': 10, 'major': 5, 'minor': 2}.get(severity, 1)
            urgency_weight = {'high': 3, 'medium': 2, 'low': 1}.get(fault.urgency, 1)
            import math
            freshness = math.exp(-0.005 * age_minutes)
            priority_score = severity_weight * urgency_weight * max(impact_count, 1) * freshness

            # 计算故障历时
            duration_text = ''
            if fault.fault_occurrence_time:
                _end = fault.fault_recovery_time or now
                _delta = _end - fault.fault_occurrence_time
                _ts = int(_delta.total_seconds())
                duration_text = _format_duration_seconds(_ts)

            active_faults.append({
                'id': fault.pk,
                'fault_number': fault.fault_number,
                'lat': lat,
                'lng': lng,
                'category': fault.fault_category or 'unknown',
                'category_display': fault.get_fault_category_display() if fault.fault_category else '未知',
                'status': fault.fault_status,
                'status_display': fault.get_fault_status_display() if fault.fault_status else '未知',
                'urgency': fault.urgency,
                'urgency_display': fault.get_urgency_display() if fault.urgency else '未知',
                'severity': severity,
                'priority_score': round(priority_score, 2),
                'site_a': fault.interruption_location_a.name if fault.interruption_location_a else '',
                'site_a_id': fault.interruption_location_a_id,
                'sites_z': z_sites,
                'site_z_ids': [s.pk for s in fault.interruption_location.all()],
                'province': fault.province.name if fault.province else '',
                'reason': fault.get_interruption_reason_display() if fault.interruption_reason else '',
                'occurrence_time': fault.fault_occurrence_time.isoformat() if fault.fault_occurrence_time else None,
                'recovery_time': fault.fault_recovery_time.isoformat() if fault.fault_recovery_time else None,
                'duration': duration_text,
                'dispatch_time': fault.dispatch_time.isoformat() if fault.dispatch_time else None,
                'departure_time': fault.departure_time.isoformat() if fault.departure_time else None,
                'arrival_time': fault.arrival_time.isoformat() if fault.arrival_time else None,
                'repair_time': fault.repair_time.isoformat() if fault.repair_time else None,
                'handler': fault.handler or '',
                'handling_unit': fault.handling_unit.name if fault.handling_unit else '',
                'impact_count': impact_count,
                'impact_names': impact_names,
                'details': (fault.fault_details or '')[:200],
            })

        # 按优先级排序
        active_faults.sort(key=lambda x: x['priority_score'], reverse=True)

        # ── 2. 运行看板核心数字 ──
        all_faults = OtnFault.objects.filter(fault_occurrence_time__gte=year_start)
        total_count = all_faults.count()
        active_count = processing_faults_qs.count()
        temporary_recovery_count = all_faults.filter(fault_status='temporary_recovery').count()
        suspended_count = all_faults.filter(fault_status='suspended').count()

        # ── 3. 24H 趋势 ──
        trend_data = []
        for i in range(24):
            hour_start = twenty_four_hours_ago + timedelta(hours=i)
            hour_end = hour_start + timedelta(hours=1)
            count = OtnFault.objects.filter(
                fault_occurrence_time__gte=hour_start,
                fault_occurrence_time__lt=hour_end
            ).count()
            trend_data.append({
                'hour': hour_start.strftime('%H:%M'),
                'count': count,
            })

        # ── 4. 站点坐标 ──
        from dcim.models import Site
        sites = []
        for site in Site.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True):
            sites.append({
                'id': site.pk,
                'name': site.name,
                'lat': float(site.latitude),
                'lng': float(site.longitude),
            })

        # ── 5. 故障关联路径覆盖层数据 ──
        # 仅按故障 A/Z 站点对定位关联路径，避免单端命中带来相邻路径误判
        fault_site_pairs: set[tuple[int, int]] = set()
        for f in active_faults_qs:
            for s in f.interruption_location.all():
                if f.interruption_location_a_id and s.pk:
                    fault_site_pairs.add((f.interruption_location_a_id, s.pk))

        fault_paths = build_fault_path_overlays(
            OtnPath.objects.select_related('site_a', 'site_z').prefetch_related('groups'),
            fault_site_pairs=fault_site_pairs,
        )

        # ── 6. 处理中故障事件（用于底部事件流）──
        recent_faults = processing_faults_qs.select_related(
            'interruption_location_a'
        ).prefetch_related(
            'interruption_location'
        ).order_by('-fault_occurrence_time')[:20]
        ticker_events = []
        for fault in recent_faults:
            z_sites = [s.name for s in fault.interruption_location.all()]
            # 计算故障历时
            duration_text = ''
            if fault.fault_occurrence_time:
                end_time = fault.fault_recovery_time or now
                delta = end_time - fault.fault_occurrence_time
                total_seconds = int(delta.total_seconds())
                duration_text = _format_duration_seconds(total_seconds)
            ticker_events.append({
                'fault_number': fault.fault_number,
                'category': fault.get_fault_category_display() if fault.fault_category else '未知',
                'site_a': fault.interruption_location_a.name if fault.interruption_location_a else '',
                'sites_z': z_sites,
                'time': fault.fault_occurrence_time.strftime('%m-%d %H:%M') if fault.fault_occurrence_time else '',
                'duration': duration_text,
                'status': fault.get_fault_status_display() if fault.fault_status else '',
                'severity': CATEGORY_SEVERITY.get(fault.fault_category, 'minor'),
            })

        # ── 7. 即将到来的割接 ──
        upcoming_cutovers_qs = CutoverTask.objects.filter(
            planned_cutover_time__gte=now,
            planned_cutover_time__lte=cutover_window_end,
            status__in=[CutoverStatusChoices.APPLYING, CutoverStatusChoices.PENDING_IMPLEMENTATION],
        ).select_related(
            'province', 'interruption_location_a'
        ).prefetch_related(
            'interruption_location', 'impacts'
        ).annotate(
            impact_count=Count('impacts', distinct=True)
        ).order_by('planned_cutover_time', 'pk')[:20]

        cutovers_data = []
        for cutover in upcoming_cutovers_qs:
            z_sites = [s.name for s in cutover.interruption_location.all()]
            minutes_until = int((cutover.planned_cutover_time - now).total_seconds() // 60)
            cutovers_data.append({
                'id': cutover.pk,
                'cutover_no': cutover.cutover_no,
                'status': cutover.status,
                'status_display': cutover.get_status_display() if cutover.status else '',
                'planned_cutover_time': cutover.planned_cutover_time.isoformat(),
                'planned_time_display': cutover.planned_cutover_time.strftime('%m-%d %H:%M'),
                'minutes_until': minutes_until,
                'province': cutover.province.name if cutover.province else '',
                'location': cutover.cutover_location,
                'site_a': cutover.interruption_location_a.name if cutover.interruption_location_a else '',
                'sites_z': z_sites,
                'impact_count': getattr(cutover, 'impact_count', 0),
                'implementation_unit': cutover.implementation_unit,
                'contact': cutover.cutover_contact,
                'url': cutover.get_absolute_url(),
            })

        # ── 8. 重要保障通知（仅文字展示）──
        active_heavy_duties = HeavyDuty.objects.filter(
            start_time__lte=now,
            end_time__gte=now
        )
        heavy_duties_data = []
        for hd in active_heavy_duties:
            heavy_duties_data.append({
                'id': hd.pk,
                'name': hd.name,
                'description': hd.description,
                'start_time_display': hd.start_time.strftime('%m月%d日 %H:%M') if hd.start_time else '',
                'end_time_display': hd.end_time.strftime('%m月%d日 %H:%M') if hd.end_time else '',
                'url': hd.get_absolute_url(),
            })

        return JsonResponse({
            'timestamp': now.isoformat(),
            'summary': {
                'total_faults': total_count,
                'active_faults': active_count,
                'temporary_recovery_faults': temporary_recovery_count,
                'suspended_faults': suspended_count,
                'upcoming_cutovers': len(cutovers_data),
                'active_heavy_duties': len(heavy_duties_data),
                'health_score': max(0, 100 - active_count * 5),  # 简单健康度公式
            },
            'active_faults': active_faults,
            'trend_24h': trend_data,
            'sites': sites,
            'fault_paths': fault_paths,
            'ticker_events': ticker_events,
            'cutovers': cutovers_data,
            'heavy_duties': heavy_duties_data,
        }, json_dumps_params={'ensure_ascii': False})


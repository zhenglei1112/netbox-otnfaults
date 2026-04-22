"""
OTN 全国网络故障自动化大屏 - 后端视图

提供大屏页面渲染和聚合数据 API。
"""
from django.shortcuts import render
from django.templatetags.static import static
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from django.db.models import Count, Q
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views import View
from django.core.serializers.json import DjangoJSONEncoder
from datetime import timedelta
import json

from .models import (
    OtnFault, OtnFaultImpact, OtnPath, OtnPathGroup,
    FaultCategoryChoices, FaultStatusChoices, UrgencyChoices,
)
from .dashboard_topology import build_fault_path_overlays


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
    'suspended': '挂起',
    'closed': '已关闭',
}


class DashboardPageView(PermissionRequiredMixin, View):
    """大屏页面视图 - 渲染全屏 HTML"""
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request):
        plugin_settings = get_plugin_settings()

        return render(request, 'netbox_otnfaults/dashboard.html', {
            'apikey': plugin_settings.get('map_api_key', ''),
            'map_center': json.dumps(plugin_settings.get('map_default_center', [108.9, 34.3])),
            'map_zoom': plugin_settings.get('map_default_zoom', 4.2),
            'map_pitch': plugin_settings.get('map_default_pitch', 45),
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
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # ── 1. 活跃故障（处理中）──
        processing_faults_qs = OtnFault.objects.filter(
            fault_status='processing'
        )

        active_faults_qs = OtnFault.objects.filter(
            Q(fault_status='processing') | Q(fault_occurrence_time__gte=twenty_four_hours_ago)
        ).select_related(
            'province', 'interruption_location_a', 'handling_unit'
        ).prefetch_related(
            'interruption_location', 'impacts', 'impacts__bare_fiber_service', 'impacts__circuit_service'
        )

        active_faults = []
        for fault in active_faults_qs:
            coords = self._get_fault_coords(fault)
            if not coords:
                continue
            lat, lng = coords

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
            age_minutes = (now - fault.fault_occurrence_time).total_seconds() / 60
            severity = CATEGORY_SEVERITY.get(fault.fault_category, 'minor')
            severity_weight = {'critical': 10, 'major': 5, 'minor': 2}.get(severity, 1)
            urgency_weight = {'high': 3, 'medium': 2, 'low': 1}.get(fault.urgency, 1)
            import math
            freshness = math.exp(-0.005 * age_minutes)
            priority_score = severity_weight * urgency_weight * max(impact_count, 1) * freshness

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
                'sites_z': z_sites,
                'province': fault.province.name if fault.province else '',
                'reason': fault.get_interruption_reason_display() if fault.interruption_reason else '',
                'occurrence_time': fault.fault_occurrence_time.isoformat() if fault.fault_occurrence_time else None,
                'recovery_time': fault.fault_recovery_time.isoformat() if fault.fault_recovery_time else None,
                'duration': fault.fault_duration or '',
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

        # ── 2. 故障统计（当年）──
        all_faults = OtnFault.objects.filter(fault_occurrence_time__gte=year_start)
        total_count = all_faults.count()
        active_count = processing_faults_qs.count()
        temporary_recovery_count = all_faults.filter(fault_status='temporary_recovery').count()
        suspended_count = all_faults.filter(fault_status='suspended').count()
        closed_count = all_faults.filter(fault_status='closed').count()

        # 按分类统计
        category_stats = list(
            all_faults.values('fault_category')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # 按状态统计
        status_stats = list(
            all_faults.values('fault_status')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # 按省份统计（年度故障）
        province_stats = list(
            all_faults.values('province__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

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

        # ── 6. 已关闭故障坐标（用于热力图）──
        closed_faults_qs = OtnFault.objects.filter(
            fault_status='closed',
            fault_occurrence_time__gte=year_start
        ).select_related('interruption_location_a')

        closed_fault_points = []
        for fault in closed_faults_qs:
            coords = self._get_fault_coords(fault)
            if not coords or coords[0] is None:
                continue
            lat, lng = coords

            # 智能对位纠偏（与活跃故障逻辑一致）
            if lat > 70.0 and lng < 60.0:
                lat, lng = lng, lat

            # 根据故障分类确定权重（严重度越高权重越大）
            severity = CATEGORY_SEVERITY.get(fault.fault_category, 'minor')
            weight = {'critical': 1.0, 'major': 0.7, 'minor': 0.4}.get(severity, 0.3)

            closed_fault_points.append({
                'lat': lat,
                'lng': lng,
                'weight': weight,
                'category': fault.fault_category or 'unknown',
            })

        # ── 7. 最近故障事件（用于 Ticker）──
        recent_faults = OtnFault.objects.select_related(
            'interruption_location_a'
        ).prefetch_related(
            'interruption_location'
        ).order_by('-fault_occurrence_time')[:20]
        ticker_events = []
        for fault in recent_faults:
            z_sites = [s.name for s in fault.interruption_location.all()]
            # 计算故障历时（简短格式）
            duration_text = ''
            if fault.fault_occurrence_time:
                end_time = fault.fault_recovery_time or now
                delta = end_time - fault.fault_occurrence_time
                total_seconds = int(delta.total_seconds())
                if total_seconds >= 0:
                    days = total_seconds // 86400
                    hours = (total_seconds % 86400) // 3600
                    minutes = (total_seconds % 3600) // 60
                    parts = []
                    if days > 0:
                        parts.append(f'{days}天')
                    if hours > 0:
                        parts.append(f'{hours}小时')
                    if minutes > 0 or not parts:
                        parts.append(f'{minutes}分')
                    duration_text = ''.join(parts)
                    if not fault.fault_recovery_time:
                        duration_text += '(进行中)'
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

        return JsonResponse({
            'timestamp': now.isoformat(),
            'summary': {
                'total_faults': total_count,
                'active_faults': active_count,
                'temporary_recovery_faults': temporary_recovery_count,
                'suspended_faults': suspended_count,
                'closed_faults': closed_count,
                'health_score': max(0, 100 - active_count * 5),  # 简单健康度公式
            },
            'active_faults': active_faults,
            'category_stats': category_stats,
            'status_stats': status_stats,
            'province_stats': province_stats,
            'trend_24h': trend_data,
            'sites': sites,
            'fault_paths': fault_paths,
            'ticker_events': ticker_events,
            'closed_fault_points': closed_fault_points,
        }, json_dumps_params={'ensure_ascii': False})

    def _get_fault_coords(self, fault) -> tuple:
        """获取故障坐标，优先使用故障经纬度，其次使用A端站点"""
        if fault.interruption_latitude and fault.interruption_longitude:
            return float(fault.interruption_latitude), float(fault.interruption_longitude)
        if (fault.interruption_location_a and
                fault.interruption_location_a.latitude and
                fault.interruption_location_a.longitude):
            return (float(fault.interruption_location_a.latitude),
                    float(fault.interruption_location_a.longitude))
        return None, None

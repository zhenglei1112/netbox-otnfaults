from datetime import timedelta
from typing import Any

from dcim.models import Site
from django.utils import timezone

from ..models import FaultCategoryChoices, FaultStatusChoices, OtnFault, CutoverTask, CutoverStatusChoices
from ..statistics_views import _source_group_for_fault
from .fault_coordinates import resolve_fault_coordinates


VALID_FAULT_CATEGORIES: set[str] = {
    'power_fault',
    'fiber_break',
    'fiber_degradation',
    'fiber_jitter',
    'ac_fault',
    'device_fault',
}


def _category_key(fault: OtnFault) -> str:
    fault_category = fault.fault_category
    if fault_category and fault_category in VALID_FAULT_CATEGORIES:
        return fault_category
    return 'other'


def _format_fault_datetime(value: Any, empty_label: str) -> str:
    if not value:
        return empty_label
    return timezone.localtime(value).strftime('%Y-%m-%d %H:%M:%S')


def _reason_display(fault: OtnFault, empty_label: str) -> str:
    reason_display = fault.get_interruption_reason_display()
    if not reason_display or reason_display == fault.interruption_reason:
        return empty_label
    return reason_display


def get_sites_data() -> list[dict]:
    """Return shared site marker data for all unified map modes."""
    return [
        {
            'id': site.pk,
            'name': site.name,
            'latitude': float(site.latitude),
            'longitude': float(site.longitude),
            'url': site.get_absolute_url(),
            'status': site.get_status_display(),
            'status_color': site.get_status_color(),
            'tenant': site.tenant.name if site.tenant else None,
            'region': site.region.name if site.region else None,
            'group': site.group.name if site.group else None,
            'facility': site.facility,
            'description': site.description,
        }
        for site in Site.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
        ).select_related('tenant', 'region', 'group')
    ]


class FaultMapMarkerSerializer:
    """Serialize a fault into the legacy fault-map marker payload."""

    def __init__(self, fault: OtnFault) -> None:
        self.fault = fault

    def data(self) -> dict | None:
        fault = self.fault
        resolved = resolve_fault_coordinates(fault)
        if resolved is None:
            return None

        z_sites = [site.name for site in fault.interruption_location.all()]
        all_impacts = list(fault.impacts.all()) + list(fault.secondary_impacts.all())
        unique_impacts = {impact.pk: impact for impact in all_impacts}.values()

        impacted_businesses: list[str] = []
        impacts_details: list[dict] = []
        for impact in unique_impacts:
            business_name = None
            if impact.service_type == 'bare_fiber' and impact.bare_fiber_service:
                business_name = impact.bare_fiber_service.name
            elif impact.service_type == 'circuit' and impact.circuit_service:
                business_name = impact.circuit_service.name

            if business_name:
                impacted_businesses.append(business_name)
                impacts_details.append({
                    'name': business_name,
                    'duration_hours': impact.service_duration_hours,
                })

        return {
            'lat': resolved.lat,
            'lng': resolved.lng,
            'coords_from_site': resolved.coords_from_site,
            'coords_source': resolved.source,
            'number': fault.fault_number,
            'url': fault.get_absolute_url(),
            'details': f"{fault.fault_number}: {fault.get_fault_category_display() or '未知类型'}",
            'category': _category_key(fault),
            'category_display': fault.get_fault_category_display() or '未知类型',
            'province': fault.province.name if fault.province else '未指定',
            'a_site': fault.interruption_location_a.name if fault.interruption_location_a else '未指定',
            'a_site_id': fault.interruption_location_a.pk if fault.interruption_location_a else None,
            'z_sites': '、'.join(z_sites) if z_sites else '未指定',
            'z_site_ids': [site.pk for site in fault.interruption_location.all()],
            'impacted_business': '、'.join(impacted_businesses) if impacted_businesses else '无重要影响业务',
            'impacts_details': impacts_details,
            'status': fault.get_fault_status_display() or '未知状态',
            'status_key': fault.fault_status or 'processing',
            'status_color': fault.get_fault_status_color(),
            'occurrence_time': _format_fault_datetime(fault.fault_occurrence_time, '未记录'),
            'recovery_time': _format_fault_datetime(fault.fault_recovery_time, '未恢复'),
            'fault_duration': fault.fault_duration if getattr(fault, 'fault_duration', None) else '无法计算',
            'reason': _reason_display(fault, '-'),
            'fault_details': fault.fault_details or '无详细描述',
            'process': fault.fault_details or '无处理过程',
            'resource_type': fault.get_resource_type_display() or '-',
            'cable_route': fault.get_cable_route_display() or '-',
            'cable_break_location': fault.get_cable_break_location_display() or '-',
            'recovery_mode': fault.get_recovery_mode_display() or '-',
            'maintenance_mode': fault.get_maintenance_mode_display() or '-',
            'handling_unit': fault.handling_unit.name if fault.handling_unit else '-',
            'handler': fault.handler or '-',
            'images': [
                {'name': image.name, 'url': image.image.url}
                for image in fault.images.all()
            ] if hasattr(fault, 'images') else [],
            'has_images': fault.images.exists() if hasattr(fault, 'images') else False,
            'image_count': fault.images.count() if hasattr(fault, 'images') else 0,
        }

class StatisticsCableBreakMapMarkerSerializer:
    """Serialize a cable-break fault into the statistics map marker payload."""

    def __init__(
        self,
        fault: OtnFault,
        now: Any,
        past_faults_list: list[OtnFault],
        fault_z_sites_cache: dict[int, set[int]],
    ) -> None:
        self.fault = fault
        self.now = now
        self.past_faults_list = past_faults_list
        self.fault_z_sites_cache = fault_z_sites_cache

    def data(self) -> dict | None:
        fault = self.fault
        resolved = resolve_fault_coordinates(fault)
        if resolved is None:
            return None

        end_time = fault.fault_recovery_time if fault.fault_recovery_time else self.now
        duration_hours = (end_time - fault.fault_occurrence_time).total_seconds() / 3600.0
        z_sites = [site.name for site in fault.interruption_location.all()]

        return {
            'id': fault.pk,
            'lat': resolved.lat,
            'lng': resolved.lng,
            'coords_from_site': resolved.coords_from_site,
            'coords_source': resolved.source,
            'number': fault.fault_number,
            'url': fault.get_absolute_url(),
            'details': f"{fault.fault_number}: {fault.get_fault_category_display() or '未知类型'}",
            'category': fault.fault_category or 'other',
            'category_display': fault.get_fault_category_display() or '未知类型',
            'province': fault.province.name if fault.province else '未指定',
            'a_site': fault.interruption_location_a.name if fault.interruption_location_a else '未指定',
            'a_site_id': fault.interruption_location_a.pk if fault.interruption_location_a else None,
            'z_sites': '、'.join(z_sites) if z_sites else '未指定',
            'status': fault.get_fault_status_display(),
            'status_key': fault.fault_status,
            'status_color': FaultStatusChoices.colors.get(fault.fault_status, 'secondary'),
            'occurrence_time': _format_fault_datetime(fault.fault_occurrence_time, '未记录'),
            'recovery_time': _format_fault_datetime(fault.fault_recovery_time, '未恢复'),
            'fault_duration': fault.fault_duration if getattr(fault, 'fault_duration', None) else '无法计算',
            'duration_hours': round(duration_hours, 2),
            'source_group': _source_group_for_fault(fault),
            'is_long': duration_hours >= 6.0,
            'is_valid_duration': duration_hours > 0.5,
            'is_repeat': self._is_repeat_fault(),
            'reason': _reason_display(fault, '-'),
            'fault_details': fault.fault_details or '',
            'cable_route': fault.get_cable_route_display() if fault.cable_route else '-',
            'cable_break_location': fault.get_cable_break_location_display() if fault.cable_break_location else '-',
            'recovery_mode': fault.get_recovery_mode_display() if fault.recovery_mode else '-',
            'maintenance_mode': fault.get_maintenance_mode_display() if fault.maintenance_mode else '-',
            'handling_unit': str(fault.handling_unit) if fault.handling_unit else '-',
            'handler': fault.handler or '-',
            'has_images': fault.images.exists(),
            'image_count': fault.images.count(),
            'images': [
                {'url': image.image.url, 'name': image.name or '故障图片'}
                for image in fault.images.all()
            ],
        }

    def _is_repeat_fault(self) -> bool:
        fault = self.fault
        if not fault.is_fiber_fault:
            return False

        fault_z_site_ids = self.fault_z_sites_cache.get(
            fault.id,
            set(site.id for site in fault.interruption_location.all()),
        )

        for past_fault in self.past_faults_list:
            if past_fault.id == fault.id:
                continue
            if past_fault.fault_occurrence_time >= fault.fault_occurrence_time:
                continue
            if (fault.fault_occurrence_time - past_fault.fault_occurrence_time) > timedelta(days=60):
                continue
            if past_fault.interruption_location_a_id != fault.interruption_location_a_id:
                continue
            if self.fault_z_sites_cache.get(past_fault.id, set()).intersection(fault_z_site_ids):
                return True

        return False


def build_fault_map_payload() -> dict[str, list[dict]]:
    """Build the legacy fault distribution map payload."""
    now = timezone.localtime()
    twelve_months_ago = now - timedelta(days=365)
    all_faults = OtnFault.objects.filter(fault_occurrence_time__gte=twelve_months_ago)

    marker_faults = all_faults.select_related(
        'province',
        'interruption_location_a',
        'handling_unit',
    ).prefetch_related(
        'interruption_location',
        'images',
        'impacts',
        'impacts__bare_fiber_service',
        'impacts__circuit_service',
        'secondary_impacts',
        'secondary_impacts__bare_fiber_service',
        'secondary_impacts__circuit_service',
    )

    marker_data = [
        marker
        for marker in (FaultMapMarkerSerializer(fault).data() for fault in marker_faults)
        if marker is not None
    ]
    heatmap_data = [
        {
            'lat': marker['lat'],
            'lng': marker['lng'],
            'count': 1,
            'occurrence_time': marker['occurrence_time'],
            'category': marker['category'],
        }
        for marker in marker_data
    ]

    return {
        'heatmap_data': heatmap_data,
        'marker_data': marker_data,
    }


def build_statistics_cable_break_map_payload(
    faults: list[OtnFault],
    end_date: Any,
    now: Any,
) -> dict[str, Any]:
    """Build map data for the statistics cable-break map."""
    if faults:
        min_occurrence = min(fault.fault_occurrence_time for fault in faults)
        check_start = min_occurrence - timedelta(days=60)
        past_faults_list = list(
            OtnFault.objects.filter(
                fault_occurrence_time__gte=check_start,
                fault_occurrence_time__lt=end_date,
                fault_category__in=[
                    FaultCategoryChoices.FIBER_BREAK,
                    FaultCategoryChoices.FIBER_DEGRADATION,
                    FaultCategoryChoices.FIBER_JITTER,
                ],
            )
            .select_related('interruption_location_a')
            .prefetch_related('interruption_location')
        )
    else:
        past_faults_list = []

    fault_z_sites_cache = {
        past_fault.id: set(site.id for site in past_fault.interruption_location.all())
        for past_fault in past_faults_list
    }

    marker_data: list[dict] = []
    skipped_count = 0
    defaulted_count = 0
    for fault in faults:
        marker = StatisticsCableBreakMapMarkerSerializer(
            fault,
            now,
            past_faults_list,
            fault_z_sites_cache,
        ).data()
        if marker is None:
            skipped_count += 1
            continue
        if marker.get('coords_from_site'):
            defaulted_count += 1
        marker_data.append(marker)

    heatmap_data = [
        {
            'lat': marker['lat'],
            'lng': marker['lng'],
            'count': 1,
            'occurrence_time': marker['occurrence_time'],
            'category': marker['category'],
        }
        for marker in marker_data
    ]

    return {
        'heatmap_data': heatmap_data,
        'marker_data': marker_data,
        'skipped_count': skipped_count,
        'defaulted_count': defaulted_count,
    }


class CutoverMapMarkerSerializer:
    """Serialize a cutover task into the legacy fault-map marker payload."""

    def __init__(self, cutover: CutoverTask) -> None:
        self.cutover = cutover

    def data(self) -> dict | None:
        cutover = self.cutover
        
        # 1. 优先经纬度定位，其次用 A端站点 的经纬度
        lat = None
        lng = None
        coords_from_site = False
        coords_source = 'direct'
        
        if cutover.cutover_latitude is not None and cutover.cutover_longitude is not None:
            lat = float(cutover.cutover_latitude)
            lng = float(cutover.cutover_longitude)
        elif cutover.interruption_location_a and cutover.interruption_location_a.latitude is not None and cutover.interruption_location_a.longitude is not None:
            lat = float(cutover.interruption_location_a.latitude)
            lng = float(cutover.interruption_location_a.longitude)
            coords_from_site = True
            coords_source = 'site_a'
            
        if lat is None or lng is None:
            return None # 无法定位，不上图
            
        # 2. 关联Z端站点
        z_sites = [site.name for site in cutover.interruption_location.all()]
        z_site_ids = [site.pk for site in cutover.interruption_location.all()]
        
        # 3. 关联影响业务和受影响业务数
        impacted_businesses: list[str] = []
        impacts_details: list[dict] = []
        for impact in cutover.impacts.all():
            business_name = None
            if impact.service_type == 'bare_fiber' and impact.bare_fiber_service:
                business_name = impact.bare_fiber_service.name
            elif impact.service_type == 'circuit' and impact.circuit_service:
                business_name = impact.circuit_service.name

            if business_name:
                impacted_businesses.append(business_name)
                
                duration_hours = None
                if impact.service_recovery_time and impact.service_interruption_time:
                    duration_hours = round((impact.service_recovery_time - impact.service_interruption_time).total_seconds() / 3600.0, 2)
                
                impacts_details.append({
                    'name': business_name,
                    'service_type': impact.service_type,
                    'duration_hours': duration_hours,
                })
                
        return {
            'id': cutover.pk,
            'lat': lat,
            'lng': lng,
            'coords_from_site': coords_from_site,
            'coords_source': coords_source,
            'number': cutover.cutover_no,
            'url': cutover.get_absolute_url(),
            'status': cutover.get_status_display() or '未知状态',
            'status_key': cutover.status or 'pending_implementation',
            'status_color': cutover.get_status_color() or 'orange',
            'planned_cutover_time': _format_fault_datetime(cutover.planned_cutover_time, '未记录'),
            'started_at': _format_fault_datetime(cutover.started_at, '未开始'),
            'completed_at': _format_fault_datetime(cutover.completed_at, '未完成'),
            'cutover_location': cutover.cutover_location or '-',
            'a_site': cutover.interruption_location_a.name if cutover.interruption_location_a else '未指定',
            'a_site_id': cutover.interruption_location_a.pk if cutover.interruption_location_a else None,
            'z_sites': '、'.join(z_sites) if z_sites else '未指定',
            'z_site_ids': z_site_ids,
            'impacted_business': '、'.join(impacted_businesses) if impacted_businesses else '无影响业务',
            'impacts_details': impacts_details,
            'impact_count': len(impacted_businesses),
            'reason': cutover.cutover_reason or '-',
            'implementation_unit': cutover.implementation_unit or '-',
            'cutover_contact': cutover.cutover_contact or '-',
            'cutover_contact_phone': cutover.cutover_contact_phone or '-',
        }


def build_cutover_map_payload(status_list=None, time_range=None) -> list[dict]:
    """Build the map payload for Cutover Tasks."""
    now = timezone.localtime()
    
    # 默认只显示 pending_implementation 状态
    if not status_list:
        status_list = [CutoverStatusChoices.PENDING_IMPLEMENTATION]
        
    queryset = CutoverTask.objects.filter(status__in=status_list)
    
    if time_range and time_range != 'all':
        if time_range == '24h':
            start_time = now
            end_time = now + timedelta(hours=24)
            queryset = queryset.filter(planned_cutover_time__gte=start_time, planned_cutover_time__lte=end_time)
        elif time_range == '7d':
            start_time = now
            end_time = now + timedelta(days=7)
            queryset = queryset.filter(planned_cutover_time__gte=start_time, planned_cutover_time__lte=end_time)
        elif time_range == '30d':
            start_time = now
            end_time = now + timedelta(days=30)
            queryset = queryset.filter(planned_cutover_time__gte=start_time, planned_cutover_time__lte=end_time)
        elif time_range == 'past30d':
            start_time = now - timedelta(days=30)
            end_time = now
            queryset = queryset.filter(planned_cutover_time__gte=start_time, planned_cutover_time__lte=end_time)
            
    marker_cutovers = queryset.select_related(
        'interruption_location_a',
        'province',
    ).prefetch_related(
        'interruption_location',
        'impacts',
        'impacts__bare_fiber_service',
        'impacts__circuit_service',
    )
    
    marker_data = []
    for cutover in marker_cutovers:
        data = CutoverMapMarkerSerializer(cutover).data()
        if data is not None:
            marker_data.append(data)
            
    return marker_data

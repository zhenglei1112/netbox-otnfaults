from netbox.filtersets import NetBoxModelFilterSet
from .models import OtnFault, OtnFaultImpact, OtnPath
from django.db.models import Q
import django_filters

class OtnFaultFilterSet(NetBoxModelFilterSet):
    bidirectional_pair = django_filters.CharFilter(method='filter_bidirectional_pair', label='双向站点对筛选 (id1,id2)')
    single_site_a_id = django_filters.NumberFilter(method='filter_single_site_a_id', label='单站点故障筛选 (A端站点ID)')
    site = django_filters.NumberFilter(method='filter_site', label='站点筛选 (A端或Z端)')

    class Meta:
        model = OtnFault
        fields = (
            'id', 'fault_number', 'duty_officer',
            'interruption_location_a', 'interruption_location',
            'fault_occurrence_time', 'fault_recovery_time', 'fault_category',
            'interruption_reason', 'fault_details', 'interruption_longitude',
            'interruption_latitude', 'province', 'urgency', 'first_report_source',
            'line_manager', 'maintenance_mode', 'handling_unit', 'contract',
            'dispatch_time', 'departure_time', 'arrival_time',
            'timeout', 'timeout_reason', 'resource_type', 'cable_route',
            'handler', 'cable_break_location', 'recovery_mode', 'comments',
            'fault_status',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(fault_number__icontains=value) |
            Q(fault_details__icontains=value) |
            Q(handler__icontains=value) |
            Q(timeout_reason__icontains=value) |
            Q(comments__icontains=value)
        )

    def filter_bidirectional_pair(self, queryset, name, value):
        try:
            ids = [int(v) for v in value.split(',')]
            if len(ids) != 2:
                return queryset.none()
            id1, id2 = ids
            # interruption_location 是 ManyToMany 字段，使用 __in 查询检查是否包含该站点
            # 只筛选光缆故障 (fault_category='fiber')
            return queryset.filter(
                fault_category='fiber'
            ).filter(
                Q(interruption_location_a_id=id1, interruption_location__in=[id2]) |
                Q(interruption_location_a_id=id2, interruption_location__in=[id1])
            ).distinct()
        except (ValueError, TypeError):
            return queryset.none()

    def filter_single_site_a_id(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(interruption_location_a_id=value, interruption_location__isnull=True)

    def filter_site(self, queryset, name, value):
        """
        筛选涉及到指定站点的故障（作为A端或包含在Z端列表中）。
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(interruption_location_a_id=value) |
            Q(interruption_location__id=value)
        ).distinct()

class OtnFaultImpactFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = OtnFaultImpact
        fields = (
            'id', 'service_interruption_time',
            'service_recovery_time', 'comments',
        )

class OtnPathFilterSet(NetBoxModelFilterSet):
    site = django_filters.NumberFilter(method='filter_site', label='站点筛选 (A端或Z端)')

    class Meta:
        model = OtnPath
        fields = (
            'id', 'name', 'cable_type',
            'site_a', 'site_z',
            'calculated_length', 'description',
        )

    def filter_site(self, queryset, name, value):
        """
        筛选 A 端或 Z 端为指定站点的光缆路径。
        使用 Q 对象实现 OR 逻辑：(site_a_id == value) OR (site_z_id == value)
        """
        if not value:
            return queryset
        return queryset.filter(
            Q(site_a_id=value) |
            Q(site_z_id=value)
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(comments__icontains=value)
        )

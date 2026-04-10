from django.db.models import Q
import django_filters
from netbox.filtersets import NetBoxModelFilterSet

from .models import (
    BareFiberService,
    CircuitService,
    OtnFault,
    OtnFaultImpact,
    OtnPath,
    OtnPathGroup,
)


class OtnFaultFilterSet(NetBoxModelFilterSet):
    bidirectional_pair = django_filters.CharFilter(
        method='filter_bidirectional_pair',
        label='双向站点对筛选 (id1,id2)',
    )
    single_site_a_id = django_filters.NumberFilter(
        method='filter_single_site_a_id',
        label='单站点故障筛选 (A站点ID)',
    )
    site = django_filters.NumberFilter(
        method='filter_site',
        label='站点筛选 (A站或Z站)',
    )
    my_pending_review_faults = django_filters.NumberFilter(
        method='filter_my_pending_review_faults',
        label='我的待复核故障',
    )

    class Meta:
        model = OtnFault
        fields = (
            'id', 'fault_number', 'duty_officer',
            'interruption_location_a', 'interruption_location',
            'fault_occurrence_time', 'fault_recovery_time', 'fault_category',
            'interruption_reason', 'fault_details', 'interruption_longitude',
            'interruption_latitude', 'province', 'urgency', 'first_report_source',
            'line_manager', 'operations_manager', 'maintenance_mode', 'handling_unit', 'contract',
            'dispatch_time', 'departure_time', 'arrival_time',
            'timeout', 'timeout_reason', 'resource_type', 'resource_owner', 'cable_route',
            'handler', 'cable_break_location', 'recovery_mode', 'comments',
            'fault_status', 'manager_reviewed',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(fault_number__icontains=value)
            | Q(fault_details__icontains=value)
            | Q(handler__icontains=value)
            | Q(timeout_reason__icontains=value)
            | Q(comments__icontains=value)
            | Q(interruption_location_a__name__icontains=value)
            | Q(interruption_location__name__icontains=value)
        ).distinct()

    def filter_bidirectional_pair(self, queryset, name, value):
        try:
            ids = [int(v) for v in value.split(',')]
            if len(ids) != 2:
                return queryset.none()
            id1, id2 = ids

            fiber_categories = [
                'fiber',
                'fiber_break',
                'fiber_degradation',
                'fiber_jitter',
            ]

            return queryset.filter(
                fault_category__in=fiber_categories,
            ).filter(
                Q(interruption_location_a_id=id1, interruption_location=id2)
                | Q(interruption_location_a_id=id2, interruption_location=id1)
            ).distinct()
        except (ValueError, TypeError):
            return queryset.none()

    def filter_my_pending_review_faults(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(line_manager_id=value, manager_reviewed=False)
            | Q(operations_manager__id=value, noc_reviewed=False)
        ).distinct()

    def filter_single_site_a_id(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            interruption_location_a_id=value,
            interruption_location__isnull=True,
        )

    def filter_site(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(interruption_location_a_id=value)
            | Q(interruption_location__id=value)
        ).distinct()


class OtnFaultImpactFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = OtnFaultImpact
        fields = (
            'id',
            'otn_fault',
            'secondary_faults',
            'service_type',
            'bare_fiber_service',
            'circuit_service',
            'service_interruption_time',
            'service_recovery_time',
            'comments',
        )


class OtnPathFilterSet(NetBoxModelFilterSet):
    site = django_filters.NumberFilter(
        method='filter_site',
        label='站点筛选 (A站或Z站)',
    )
    groups = django_filters.ModelMultipleChoiceFilter(
        queryset=OtnPathGroup.objects.all(),
        label='所属路径组',
    )

    class Meta:
        model = OtnPath
        fields = (
            'id', 'name', 'cable_type',
            'site_a', 'site_z', 'groups',
            'calculated_length', 'description',
        )

    def filter_site(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(site_a_id=value) | Q(site_z_id=value))

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )


class CircuitServiceFilterSet(NetBoxModelFilterSet):
    """电路业务过滤器"""

    is_external_business = django_filters.BooleanFilter(label='对外业务')

    class Meta:
        model = CircuitService
        fields = (
            'id',
            'special_line_name',
            'name',
            'slug',
            'service_group',
            'business_category',
            'bandwidth',
            'business_manager',
            'is_external_business',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(slug__icontains=value)
            | Q(comments__icontains=value)
        )


class BareFiberServiceFilterSet(NetBoxModelFilterSet):
    """裸纤业务过滤器"""

    class Meta:
        model = BareFiberService
        fields = ('id', 'name', 'slug', 'tenant_group', 'business_manager')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(slug__icontains=value)
            | Q(comments__icontains=value)
        )


class OtnPathGroupFilterSet(NetBoxModelFilterSet):
    """路径组过滤器"""

    class Meta:
        model = OtnPathGroup
        fields = (
            'id', 'name', 'slug', 'description',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(slug__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )

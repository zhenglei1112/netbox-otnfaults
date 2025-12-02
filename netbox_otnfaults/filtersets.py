from netbox.filtersets import NetBoxModelFilterSet
from .models import OtnFault, OtnFaultImpact
from django.db.models import Q

class OtnFaultFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = OtnFault
        fields = (
            'id', 'fault_number', 'duty_officer', 'interruption_location',
            'fault_occurrence_time', 'fault_recovery_time', 'fault_category',
            'interruption_reason', 'fault_details', 'interruption_longitude',
            'interruption_latitude', 'province', 'urgency', 'first_report_source',
            'planned', 'line_manager', 'maintenance_mode', 'handling_unit',
            'dispatch_time', 'departure_time', 'arrival_time', 'repair_time',
            'timeout', 'timeout_reason', 'resource_type', 'cable_route',
            'handler', 'recovery_mode', 'comments',
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

class OtnFaultImpactFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = OtnFaultImpact
        fields = (
            'id', 'otn_fault', 'impacted_service',
        )

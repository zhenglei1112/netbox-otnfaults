from netbox.filtersets import NetBoxModelFilterSet
from .models import OtnFault, OtnFaultImpact
from django.db.models import Q

class OtnFaultFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = OtnFault
        fields = (
            'id', 'fault_number', 'duty_officer', 'interruption_location',
            'fault_category', 'interruption_reason',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(fault_number__icontains=value) |
            Q(fault_details__icontains=value)
        )

class OtnFaultImpactFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = OtnFaultImpact
        fields = (
            'id', 'otn_fault', 'impacted_service',
        )

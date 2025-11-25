from rest_framework import serializers
from netbox.api.serializers import NetBoxModelSerializer, WritableNestedSerializer
from ..models import OtnFault, OtnFaultImpact
from django.contrib.auth import get_user_model
from dcim.models import Site
from tenancy.models import Tenant

# Custom nested serializers
class NestedSiteSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='dcim-api:site-detail'
    )

    class Meta:
        model = Site
        fields = ('id', 'url', 'display', 'name', 'slug')
        brief_fields = ('id', 'url', 'display', 'name')

class NestedTenantSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='tenancy-api:tenant-detail'
    )

    class Meta:
        model = Tenant
        fields = ('id', 'url', 'display', 'name', 'slug')
        brief_fields = ('id', 'url', 'display', 'name')

class NestedUserSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='users-api:user-detail'
    )

    class Meta:
        model = get_user_model()
        fields = ('id', 'url', 'display', 'username', 'email')
        brief_fields = ('id', 'url', 'display', 'username')

class OtnFaultSerializer(NetBoxModelSerializer):
    duty_officer = NestedUserSerializer()
    interruption_location = NestedSiteSerializer(many=True, required=False)
    
    class Meta:
        model = OtnFault
        fields = (
            'id', 'url', 'display', 'fault_number', 'duty_officer', 'interruption_location',
            'fault_occurrence_time', 'fault_recovery_time', 'fault_duration',
            'fault_category', 'interruption_reason', 'fault_details',
            'tags', 'custom_fields', 'created', 'last_updated',
        )
        brief_fields = (
            'id', 'url', 'display', 'fault_number', 'duty_officer', 'fault_occurrence_time',
            'fault_category', 'interruption_reason',
        )
        read_only_fields = ('fault_number', 'fault_duration')

class OtnFaultImpactSerializer(NetBoxModelSerializer):
    otn_fault = serializers.PrimaryKeyRelatedField(queryset=OtnFault.objects.all())
    impacted_service = NestedTenantSerializer()

    class Meta:
        model = OtnFaultImpact
        fields = (
            'id', 'url', 'display', 'otn_fault', 'impacted_service',
            'service_interruption_time', 'service_recovery_time', 'service_duration',
            'tags', 'custom_fields', 'created', 'last_updated',
        )
        brief_fields = (
            'id', 'url', 'display', 'otn_fault', 'impacted_service',
            'service_interruption_time', 'service_recovery_time',
        )
        read_only_fields = ('service_duration',)

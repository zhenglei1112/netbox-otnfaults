from rest_framework import serializers
from netbox.api.serializers import NetBoxModelSerializer, WritableNestedSerializer
from ..models import OtnFault, OtnFaultImpact, OtnPath, OtnPathGroup
from django.contrib.auth import get_user_model
from dcim.models import Site, Region
from tenancy.models import Tenant
from netbox_contract.models import ServiceProvider
from extras.models import JournalEntry

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

class NestedRegionSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='dcim-api:region-detail'
    )

    class Meta:
        model = Region
        fields = ('id', 'url', 'display', 'name', 'slug')
        brief_fields = ('id', 'url', 'display', 'name')

class NestedServiceProviderSerializer(WritableNestedSerializer):
    # 简化处理，避免URL解析问题
    class Meta:
        model = ServiceProvider
        fields = ('id', 'display', 'name')
        brief_fields = ('id', 'display', 'name')

class NestedJournalEntrySerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='extras-api:journalentry-detail'
    )
    
    class Meta:
        model = JournalEntry
        fields = ('id', 'url', 'display', 'created', 'created_by', 'kind', 'comments')
        brief_fields = ('id', 'url', 'display', 'created', 'kind')

class OtnFaultSerializer(NetBoxModelSerializer):
    duty_officer = NestedUserSerializer()
    interruption_location_a = NestedSiteSerializer()
    interruption_location = NestedSiteSerializer(many=True, required=False)
    province = NestedRegionSerializer(required=False)
    line_manager = NestedUserSerializer(required=False)
    handling_unit = NestedServiceProviderSerializer(required=False)
    journal_entries = NestedJournalEntrySerializer(many=True, read_only=True)
    
    class Meta:
        model = OtnFault
        fields = (
            'id', 'url', 'display', 'fault_number', 'duty_officer', 'interruption_location_a', 'interruption_location',
            'fault_occurrence_time', 'fault_recovery_time', 'fault_duration',
            'fault_category', 'interruption_reason', 'fault_details',
            'interruption_longitude', 'interruption_latitude',
            'province', 'urgency', 'first_report_source',
            'line_manager', 'resource_type', 'cable_route',
            'maintenance_mode', 'dispatch_time', 'departure_time',
            'arrival_time', 'repair_time', 'repair_duration', 'timeout', 'timeout_reason',
            'handler', 'recovery_mode', 'handling_unit', 'fault_status',
            'tags', 'comments', 'custom_fields', 'created', 'last_updated',
            'journal_entries',
        )
        brief_fields = (
            'id', 'url', 'display', 'fault_number', 'duty_officer', 'fault_occurrence_time',
            'fault_category', 'interruption_reason', 'urgency', 'first_report_source',
            'fault_status',
        )
        read_only_fields = ('fault_number', 'fault_duration', 'repair_duration', 'journal_entries')

class OtnFaultImpactSerializer(NetBoxModelSerializer):
    otn_fault = serializers.PrimaryKeyRelatedField(queryset=OtnFault.objects.all())
    impacted_service = NestedTenantSerializer()
    journal_entries = NestedJournalEntrySerializer(many=True, read_only=True)

    class Meta:
        model = OtnFaultImpact
        fields = (
            'id', 'url', 'display', 'otn_fault', 'impacted_service',
            'service_interruption_time', 'service_recovery_time', 'service_duration',
            'tags', 'comments', 'custom_fields', 'created', 'last_updated',
            'journal_entries',
        )
        brief_fields = (
            'id', 'url', 'display', 'otn_fault', 'impacted_service',
            'service_interruption_time', 'service_recovery_time',
        )
        read_only_fields = ('service_duration', 'journal_entries')

class NestedOtnPathGroupSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_otnfaults-api:otnpathgroup-detail'
    )

    class Meta:
        model = OtnPathGroup
        fields = ('id', 'url', 'display', 'name', 'slug')
        brief_fields = ('id', 'url', 'display', 'name')


class OtnPathSerializer(NetBoxModelSerializer):
    site_a = NestedSiteSerializer()
    site_z = NestedSiteSerializer()
    groups = NestedOtnPathGroupSerializer(many=True, required=False)

    class Meta:
        model = OtnPath
        fields = (
            'id', 'url', 'display', 'name', 'groups', 'cable_type', 'site_a', 'site_z',
            'geometry', 'calculated_length', 'description', 'comments', 'tags',
            'custom_fields', 'created', 'last_updated',
        )


class OtnPathGroupSerializer(NetBoxModelSerializer):
    """路径组序列化器"""
    path_count = serializers.SerializerMethodField()

    class Meta:
        model = OtnPathGroup
        fields = (
            'id', 'url', 'display', 'name', 'slug', 'description', 
            'path_count', 'comments', 'tags',
            'custom_fields', 'created', 'last_updated',
        )

    def get_path_count(self, obj):
        return obj.paths.count()


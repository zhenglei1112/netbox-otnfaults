import django_tables2 as tables
from django.utils.html import format_html
from netbox.tables import NetBoxTable, columns
from .models import OtnFault, OtnFaultImpact

class OtnFaultTable(NetBoxTable):
    fault_number = tables.Column(
        linkify=True
    )
    duty_officer = tables.Column(
        linkify=True
    )
    interruption_location = columns.ManyToManyColumn(
        linkify_item=True
    )
    fault_category = columns.ChoiceFieldColumn(
        verbose_name='故障分类'
    )
    fault_duration = tables.Column(
        verbose_name='中断历时',
        orderable=False
    )

    class Meta(NetBoxTable.Meta):
        model = OtnFault
        fields = (
            'pk', 'fault_number', 'duty_officer', 'interruption_location',
            'fault_occurrence_time', 'fault_recovery_time', 'fault_duration',
            'fault_category', 'interruption_reason', 'actions',
        )
        default_columns = (
            'fault_number', 'duty_officer', 'interruption_location',
            'fault_occurrence_time', 'fault_duration', 'fault_category',
        )

class OtnFaultImpactTable(NetBoxTable):
    otn_fault = tables.Column(
        linkify=True
    )
    impacted_service = tables.Column(
        linkify=True
    )
    service_duration = tables.Column(
        verbose_name='中断历时',
        orderable=False
    )

    class Meta(NetBoxTable.Meta):
        model = OtnFaultImpact
        fields = (
            'pk', 'otn_fault', 'impacted_service',
            'service_interruption_time', 'service_recovery_time', 'service_duration',
            'actions',
        )
        default_columns = (
            'otn_fault', 'impacted_service',
            'service_interruption_time', 'service_duration',
        )

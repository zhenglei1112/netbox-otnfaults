import django_tables2 as tables
from django.utils.html import format_html
from netbox.tables import NetBoxTable, columns
from .models import OtnFault, OtnFaultImpact

class OtnFaultTable(NetBoxTable):
    fault_number = tables.Column(
        linkify=True,
        verbose_name='故障编号'
    )
    duty_officer = tables.Column(
        linkify=True,
        verbose_name='值守人员'
    )
    interruption_location = columns.ManyToManyColumn(
        linkify_item=True,
        verbose_name='中断位置'
    )
    fault_occurrence_time = tables.DateTimeColumn(
        format='Y-m-d H:i:s',
        verbose_name='故障中断时间'
    )
    fault_recovery_time = tables.DateTimeColumn(
        format='Y-m-d H:i:s',
        verbose_name='故障恢复时间'
    )
    fault_category = columns.ChoiceFieldColumn(
        verbose_name='故障分类'
    )
    interruption_reason = columns.ChoiceFieldColumn(
        verbose_name='中断原因'
    )
    fault_duration = tables.Column(
        verbose_name='中断历时',
        orderable=False
    )
    urgency = columns.ChoiceFieldColumn(
        verbose_name='紧急程度'
    )
    first_report_source = columns.ChoiceFieldColumn(
        verbose_name='第一报障来源'
    )
    planned = columns.BooleanColumn(
        verbose_name='计划内'
    )
    maintenance_mode = columns.ChoiceFieldColumn(
        verbose_name='维护方式'
    )
    recovery_mode = columns.ChoiceFieldColumn(
        verbose_name='恢复方式'
    )
    resource_type = columns.ChoiceFieldColumn(
        verbose_name='资源类型'
    )
    cable_route = columns.ChoiceFieldColumn(
        verbose_name='光缆路由属性'
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_otnfaults:otnfault_list'
    )

    class Meta(NetBoxTable.Meta):
        model = OtnFault
        fields = (
            'pk', 'fault_number', 'duty_officer', 'interruption_location',
            'fault_occurrence_time', 'fault_recovery_time', 'fault_duration',
            'fault_category', 'interruption_reason', 'urgency', 'first_report_source', 'planned',
            'province', 'line_manager', 'resource_type', 'cable_route',
            'maintenance_mode', 'dispatch_time', 'departure_time', 'arrival_time', 'repair_time',
            'repair_duration', 'timeout', 'handler', 'recovery_mode', 'handling_unit',
            'comments', 'tags', 'actions',
        )
        default_columns = (
            'fault_number', 'duty_officer', 'interruption_location',
            'fault_occurrence_time', 'fault_duration', 'fault_category', 'urgency', 'tags',
        )

class OtnFaultImpactTable(NetBoxTable):
    otn_fault = tables.Column(
        linkify=True,
        verbose_name='关联故障'
    )
    impacted_service = tables.Column(
        linkify=True,
        verbose_name='影响业务'
    )
    service_interruption_time = tables.DateTimeColumn(
        format='Y-m-d H:i:s',
        verbose_name='业务中断时间'
    )
    service_recovery_time = tables.DateTimeColumn(
        format='Y-m-d H:i:s',
        verbose_name='业务恢复时间'
    )
    service_duration = tables.Column(
        verbose_name='中断历时',
        orderable=False
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_otnfaults:otnfaultimpact_list'
    )

    class Meta(NetBoxTable.Meta):
        model = OtnFaultImpact
        fields = (
            'pk', 'otn_fault', 'impacted_service',
            'service_interruption_time', 'service_recovery_time', 'service_duration',
            'comments', 'tags', 'actions',
        )
        default_columns = (
            'otn_fault', 'impacted_service',
            'service_interruption_time', 'service_duration', 'tags',
        )

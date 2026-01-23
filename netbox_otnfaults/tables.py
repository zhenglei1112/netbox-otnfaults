import django_tables2 as tables
from django.utils.html import format_html
from netbox.tables import NetBoxTable, columns
from .models import OtnFault, OtnFaultImpact, OtnPath, OtnPathGroup, OtnPathGroupSite, PathGroupSiteRoleChoices

class OtnPathGroupSiteTable(NetBoxTable):
    """路径组站点关联表"""
    site = tables.Column(
        linkify=True,
        verbose_name='站点'
    )
    role = columns.ChoiceFieldColumn(
        verbose_name='角色'
    )
    position = tables.Column(
        verbose_name='排序'
    )
    actions = columns.ActionsColumn(
        actions=('edit', 'delete'),
        extra_buttons='''
            <a href="{% url 'plugins:netbox_otnfaults:otnpathgroupsite_edit' pk=record.pk %}" class="btn btn-sm btn-warning">
                <i class="mdi mdi-pencil"></i>
            </a>
            <a href="{% url 'plugins:netbox_otnfaults:otnpathgroupsite_delete' pk=record.pk %}" class="btn btn-sm btn-danger">
                <i class="mdi mdi-trash-can-outline"></i>
            </a>
        '''
    )

    class Meta(NetBoxTable.Meta):
        model = OtnPathGroupSite
        fields = ('pk', 'site', 'role', 'position', 'actions')
        default_columns = ('site', 'role', 'position', 'actions')

class OtnFaultTable(NetBoxTable):
    fault_number = tables.Column(
        linkify=True,
        verbose_name='故障编号'
    )
    duty_officer = tables.Column(
        linkify=True,
        verbose_name='值守人员'
    )
    contract = tables.Column(
        linkify=True,
        verbose_name='代维合同'
    )
    interruption_location_a = tables.Column(
        linkify=True,
        verbose_name='故障位置A端站点'
    )
    interruption_location = columns.ManyToManyColumn(
        linkify_item=True,
        verbose_name='故障位置Z端站点'
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
        verbose_name='故障原因'
    )
    fault_duration = tables.Column(
        verbose_name='故障历时',
        orderable=False
    )
    urgency = columns.ChoiceFieldColumn(
        verbose_name='紧急程度'
    )
    first_report_source = columns.ChoiceFieldColumn(
        verbose_name='第一报障来源'
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
    cable_break_location = columns.ChoiceFieldColumn(
        verbose_name='光缆中断部位'
    )
    fault_status = columns.ChoiceFieldColumn(
        verbose_name='处理状态'
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_otnfaults:otnfault_list'
    )

    class Meta(NetBoxTable.Meta):
        model = OtnFault
        fields = (
            'pk', 'fault_number', 'duty_officer', 'interruption_location_a', 'interruption_location',
            'fault_occurrence_time', 'fault_recovery_time', 'fault_duration',
            'fault_category', 'interruption_reason', 'urgency', 'first_report_source',
            'province', 'line_manager', 'resource_type', 'cable_route',
            'maintenance_mode', 'dispatch_time', 'departure_time', 'arrival_time',
            'timeout', 'handler', 'cable_break_location', 'recovery_mode', 'handling_unit', 'contract',
            'fault_status', 'comments', 'tags', 'actions',
        )
        default_columns = (
            'fault_number', 'duty_officer', 'interruption_location',
            'fault_occurrence_time', 'fault_duration', 'fault_category', 'urgency', 'fault_status', 'tags',
        )

    def render_fault_duration(self, record):
        """渲染故障历时为可视化进度条（使用内联样式）"""
        info = record.fault_duration_info
        if not info:
            return '—'
        
        # 颜色映射
        color_map = {
            'green': 'linear-gradient(90deg, #28a745, #34ce57)',
            'yellow': 'linear-gradient(90deg, #ffc107, #ffda47)',
            'orange': 'linear-gradient(90deg, #fd7e14, #ff9636)',
            'red': 'linear-gradient(90deg, #dc3545, #f34b5b)',
        }
        fill_bg = color_map.get(info['color'], color_map['green'])
        
        return format_html(
            '<div style="position:relative;width:120px;height:22px;background:#e9ecef;'
            'border-radius:4px;overflow:hidden;display:inline-block" title="{}">'
            '<div style="position:absolute;left:0;top:0;bottom:0;width:{}%;'
            'border-radius:4px;background:{}"></div>'
            '<span style="position:absolute;width:100%;text-align:center;'
            'font-size:12px;font-weight:500;line-height:22px;color:#333;'
            'text-shadow:0 0 2px rgba(255,255,255,0.8)">{}</span>'
            '</div>',
            info['full_text'],
            info['percentage'],
            fill_bg,
            info['display']
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
        verbose_name='业务故障时间'
    )
    service_recovery_time = tables.DateTimeColumn(
        format='Y-m-d H:i:s',
        verbose_name='业务恢复时间'
    )
    service_duration = tables.Column(
        verbose_name='故障历时',
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

    def render_service_duration(self, record):
        """渲染业务中断历时为可视化进度条（使用内联样式）"""
        info = record.service_duration_info
        if not info:
            return '—'
        
        # 颜色映射
        color_map = {
            'green': 'linear-gradient(90deg, #28a745, #34ce57)',
            'yellow': 'linear-gradient(90deg, #ffc107, #ffda47)',
            'orange': 'linear-gradient(90deg, #fd7e14, #ff9636)',
            'red': 'linear-gradient(90deg, #dc3545, #f34b5b)',
        }
        fill_bg = color_map.get(info['color'], color_map['green'])
        
        return format_html(
            '<div style="position:relative;width:120px;height:22px;background:#e9ecef;'
            'border-radius:4px;overflow:hidden;display:inline-block" title="{}">'
            '<div style="position:absolute;left:0;top:0;bottom:0;width:{}%;'
            'border-radius:4px;background:{}"></div>'
            '<span style="position:absolute;width:100%;text-align:center;'
            'font-size:12px;font-weight:500;line-height:22px;color:#333;'
            'text-shadow:0 0 2px rgba(255,255,255,0.8)">{}</span>'
            '</div>',
            info['full_text'],
            info['percentage'],
            fill_bg,
            info['display']
        )

class OtnPathTable(NetBoxTable):
    name = tables.Column(
        linkify=True,
        verbose_name='名称'
    )
    groups_count = tables.Column(
        verbose_name='所属路径组',
        orderable=False
    )
    cable_type = columns.ChoiceFieldColumn(
        verbose_name='光缆类型'
    )
    site_a = tables.Column(
        linkify=True,
        verbose_name='A端站点'
    )
    site_z = tables.Column(
        linkify=True,
        verbose_name='Z端站点'
    )
    calculated_length = tables.Column(
        verbose_name='计算长度'
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_otnfaults:otnpath_list'
    )

    class Meta(NetBoxTable.Meta):
        model = OtnPath
        fields = (
            'pk', 'name', 'groups_count', 'cable_type', 'site_a', 'site_z',
            'calculated_length', 'description', 'comments', 'tags', 'actions',
        )
        default_columns = (
            'name', 'cable_type', 'site_a', 'site_z', 'calculated_length', 'tags',
        )

    def render_groups_count(self, record):
        count = record.groups.count()
        return f'{count} 个' if count else '—'


class OtnPathGroupTable(NetBoxTable):
    """路径组表格"""
    name = tables.Column(
        linkify=True,
        verbose_name='名称'
    )
    slug = tables.Column(
        verbose_name='缩写'
    )
    description = tables.Column(
        verbose_name='描述'
    )
    path_count = tables.Column(
        verbose_name='路径数量',
        orderable=False
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_otnfaults:otnpathgroup_list'
    )

    class Meta(NetBoxTable.Meta):
        model = OtnPathGroup
        fields = (
            'pk', 'name', 'slug', 'description', 'path_count', 'comments', 'tags', 'actions',
        )
        default_columns = (
            'name', 'slug', 'description', 'path_count', 'tags',
        )

    def render_path_count(self, record):
        return record.paths.count()


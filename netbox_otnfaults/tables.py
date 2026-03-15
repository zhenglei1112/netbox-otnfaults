import django_tables2 as tables
from django.utils.html import format_html
from netbox.tables import NetBoxTable, columns
from .models import OtnFault, OtnFaultImpact, OtnPath, OtnPathGroup, OtnPathGroupSite, PathGroupSiteRoleChoices, BareFiberService, CircuitService

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
        verbose_name='一级原因'
    )
    interruption_reason_detail = columns.ChoiceFieldColumn(
        verbose_name='二级原因'
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
        verbose_name='光纤来源'
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
            'pk', 'fault_number', 'fault_category', 'duty_officer', 'interruption_location_a', 'interruption_location',
            'fault_occurrence_time', 'fault_recovery_time', 'fault_duration',
            'interruption_reason', 'interruption_reason_detail', 'urgency', 'first_report_source',
            'province', 'line_manager', 'resource_type', 'cable_route',
            'maintenance_mode', 'dispatch_time', 'departure_time', 'arrival_time',
            'timeout', 'handler', 'cable_break_location', 'recovery_mode', 'handling_unit', 'contract',
            'fault_status', 'comments', 'tags', 'actions',
        )
        default_columns = (
            'fault_number', 'fault_category', 'duty_officer', 'interruption_location_a', 'interruption_location',
            'fault_occurrence_time', 'fault_duration', 'fault_status',
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

class ContractOtnFaultTable(NetBoxTable):
    """用于在合同详情页精简显示的故障表格"""
    fault_number = tables.Column(
        linkify=True,
        verbose_name='故障编号'
    )
    duty_officer = tables.Column(
        linkify=True,
        verbose_name='值守人员'
    )
    fault_occurrence_time = tables.DateTimeColumn(
        format='Y-m-d H:i:s',
        verbose_name='故障中断时间'
    )
    fault_category = columns.ChoiceFieldColumn(
        verbose_name='故障分类'
    )
    urgency = columns.ChoiceFieldColumn(
        verbose_name='紧急程度'
    )
    fault_status = columns.ChoiceFieldColumn(
        verbose_name='处理状态'
    )
    fault_duration = tables.Column(
        verbose_name='故障历时',
        orderable=False
    )

    class Meta(NetBoxTable.Meta):
        model = OtnFault
        fields = (
            'pk', 'fault_number', 'duty_officer', 'fault_occurrence_time',
            'fault_category', 'urgency', 'fault_status', 'fault_duration',
        )
        default_columns = (
            'fault_number', 'duty_officer', 'fault_occurrence_time',
            'fault_category', 'urgency', 'fault_status', 'fault_duration',
        )

    def render_fault_duration(self, record):
        """复用故障历时渲染逻辑"""
        info = record.fault_duration_info
        if not info:
            return '—'
        
        color_map = {
            'green': 'linear-gradient(90deg, #28a745, #34ce57)',
            'yellow': 'linear-gradient(90deg, #ffc107, #ffda47)',
            'orange': 'linear-gradient(90deg, #fd7e14, #ff9636)',
            'red': 'linear-gradient(90deg, #dc3545, #f34b5b)',
        }
        fill_bg = color_map.get(info['color'], color_map['green'])
        
        from django.utils.html import format_html
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
        verbose_name='直接故障'
    )
    service_type = columns.ChoiceFieldColumn(
        verbose_name='业务类型'
    )
    service_name = tables.Column(
        verbose_name='业务名称',
        orderable=False,
        empty_values=()
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
    secondary_faults = tables.ManyToManyColumn(
        linkify_item=True,
        verbose_name='其他关联故障'
    )
    service_group = tables.Column(
        verbose_name='业务组',
        orderable=False,
        empty_values=()
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_otnfaults:otnfaultimpact_list'
    )

    class Meta(NetBoxTable.Meta):
        model = OtnFaultImpact
        fields = (
            'pk', 'service_type', 'service_name', 'service_interruption_time', 'service_recovery_time',
            'service_duration', 'otn_fault', 'secondary_faults', 'service_group',
            'comments', 'tags', 'actions',
        )
        default_columns = (
            'pk', 'service_type', 'service_name', 'service_interruption_time',
            'service_recovery_time', 'service_duration', 'otn_fault',
        )

    def render_service_name(self, record):
        from django.utils.html import format_html
        if record.service_type == 'bare_fiber' and record.bare_fiber_service:
            url = record.bare_fiber_service.get_absolute_url()
            name = record.bare_fiber_service.name
            return format_html('<a href="{}">{}</a>', url, name)
        elif record.service_type == 'circuit' and record.circuit_service:
            url = record.circuit_service.get_absolute_url()
            name = record.circuit_service.name
            return format_html('<a href="{}">{}</a>', url, name)
        return '—'

    def render_service_group(self, record):
        if record.service_type == 'circuit' and record.circuit_service:
            return record.circuit_service.get_service_group_display()
        return '—'

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

class OtnFaultImpactDetailTable(NetBoxTable):
    """用于业务详情页的故障详情化显示表格（镜像故障列表样式）"""
    otn_fault = tables.Column(
        linkify=True,
        verbose_name='故障编号'
    )
    # 通过关联获取主故障字段
    fault_category = columns.ChoiceFieldColumn(
        accessor='otn_fault__fault_category',
        verbose_name='故障分类'
    )
    interruption_location_a = tables.Column(
        accessor='otn_fault__interruption_location_a',
        linkify=True,
        verbose_name='故障位置A端站点'
    )
    interruption_location = columns.ManyToManyColumn(
        accessor='otn_fault__interruption_location',
        linkify_item=True,
        verbose_name='故障位置Z端站点'
    )
    # 业务级时间与历时
    service_interruption_time = tables.DateTimeColumn(
        format='Y-m-d H:i:s',
        verbose_name='业务中断时间'
    )
    service_duration = tables.Column(
        verbose_name='业务中断历时',
        orderable=False
    )

    class Meta(NetBoxTable.Meta):
        model = OtnFaultImpact
        fields = (
            'otn_fault', 'fault_category', 'interruption_location_a', 'interruption_location',
            'service_interruption_time', 'service_duration', 'actions',
        )
        default_columns = (
            'otn_fault', 'fault_category', 'interruption_location_a', 'interruption_location',
            'service_interruption_time', 'service_duration',
        )

    def render_service_duration(self, record):
        """复用进度条渲染逻辑"""
        info = record.service_duration_info
        if not info:
            return '—'
        
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

class OtnFaultImpactSummaryTable(OtnFaultImpactTable):
    """故障详情页关联业务的精简表格渲染"""
    class Meta(OtnFaultImpactTable.Meta):
        fields = (
            'pk', 'secondary_faults', 'service_type', 'service_name', 'service_group',
            'service_interruption_time', 'service_recovery_time', 'service_duration',
            'comments', 'tags', 'actions',
        )
        default_columns = (
            'service_type', 'service_name', 'service_group',
            'service_interruption_time', 'service_recovery_time', 'service_duration',
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


class BareFiberServiceTable(NetBoxTable):
    """裸纤业务列表表格"""
    name = tables.Column(
        linkify=True,
        verbose_name='名称'
    )
    slug = tables.Column(
        verbose_name='缩写'
    )
    tenant_group = tables.Column(
        linkify=True,
        verbose_name='租户组'
    )
    business_manager = tables.Column(
        linkify=True,
        verbose_name='业务主管'
    )
    billing_start_time = tables.DateColumn(
        format='Y年n月j日',
        verbose_name='计费起始时间'
    )
    billing_end_time = tables.DateColumn(
        format='Y年n月j日',
        verbose_name='计费结束时间'
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_otnfaults:barefiberservice_list'
    )

    class Meta(NetBoxTable.Meta):
        model = BareFiberService
        fields = (
            'pk', 'name', 'slug', 'tenant_group', 'business_manager', 'billing_start_time', 'billing_end_time', 'tags', 'actions',
        )
        default_columns = (
            'name', 'slug', 'tenant_group', 'business_manager', 'billing_start_time', 'billing_end_time', 'tags',
        )


class CircuitServiceTable(NetBoxTable):
    """电路业务列表表格"""
    name = tables.Column(
        linkify=True,
        verbose_name='编号'
    )
    slug = tables.Column(
        verbose_name='缩写'
    )
    service_group = columns.ChoiceFieldColumn(
        verbose_name='业务组'
    )
    bandwidth = columns.ChoiceFieldColumn(
        verbose_name='带宽'
    )
    business_manager = tables.Column(
        linkify=True,
        verbose_name='业务主管'
    )
    billing_start_time = tables.DateColumn(
        format='Y年n月j日',
        verbose_name='计费起始时间'
    )
    billing_end_time = tables.DateColumn(
        format='Y年n月j日',
        verbose_name='计费结束时间'
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_otnfaults:circuitservice_list'
    )

    class Meta(NetBoxTable.Meta):
        model = CircuitService
        fields = (
            'pk', 'name', 'slug', 'service_group', 'bandwidth', 'business_manager', 'billing_start_time', 'billing_end_time', 'tags', 'actions',
        )
        default_columns = (
            'name', 'slug', 'service_group', 'bandwidth', 'business_manager', 'billing_start_time', 'billing_end_time', 'tags',
        )


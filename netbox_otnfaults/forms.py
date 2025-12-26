from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm, NetBoxModelImportForm
from .models import (
    OtnFault, OtnFaultImpact, FaultCategoryChoices, UrgencyChoices, 
    MaintenanceModeChoices, ResourceTypeChoices, CableRouteChoices,
    FaultStatusChoices, CableBreakLocationChoices, RecoveryModeChoices,
    OtnPath, CableTypeChoices, OtnPathGroup
)
from django import forms
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, CommentField, CSVModelChoiceField, CSVModelMultipleChoiceField
from utilities.forms.rendering import FieldSet
from utilities.forms.widgets import DateTimePicker
from dcim.models import Site, Region
from tenancy.models import Tenant
from django.contrib.auth import get_user_model
from netbox_contract.models import ServiceProvider, Contract

class OtnFaultForm(NetBoxModelForm):
    duty_officer = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        label='值守人员'
    )
    interruption_location_a = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        label='故障位置A端站点'
    )
    interruption_location = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='故障位置Z端站点'
    )
    province = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label='省份'
    )
    line_manager = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='线路主管'
    )
    handling_unit = DynamicModelChoiceField(
        queryset=ServiceProvider.objects.all(),
        required=False,
        label='处理单位'
    )
    contract = DynamicModelChoiceField(
        queryset=Contract.objects.all(),
        required=False,
        label='代维合同',
        query_params={
            'service_provider_id': '$handling_unit',
        }
    )
    comments = CommentField(
        label='评论',
        help_text='<span class="form-text">支持 <i class="mdi mdi-information-outline"></i> <a href="/static/docs/reference/markdown/" target="_blank" tabindex="-1">Markdown</a> 语法</span>'
    )
    
    fieldsets = (
        ('故障信息', (
            'urgency', 'province', 'interruption_location_a', 'interruption_location',
            'interruption_longitude', 'interruption_latitude', 'fault_category',
            'interruption_reason', 'fault_occurrence_time', 'fault_recovery_time',
            'first_report_source', 'line_manager', 'duty_officer', 'fault_details',
            'fault_status',
        )),
        ('光缆中断补充信息', (
            'resource_type', 'cable_route', 'cable_break_location', 'recovery_mode',
            'maintenance_mode', 'handling_unit', 'contract', 'dispatch_time',
            'departure_time', 'arrival_time', 'repair_time', 'timeout',
            'timeout_reason', 'handler',
        )),
        (None, (
            'comments', 'tags',
        )),
    )

    class Meta:
        model = OtnFault
        fields = (
            # 故障信息组字段
            'urgency', 'province', 'interruption_location_a', 'interruption_location',
            'interruption_longitude', 'interruption_latitude', 'fault_category',
            'interruption_reason', 'fault_occurrence_time', 'fault_recovery_time',
            'first_report_source', 'line_manager', 'duty_officer', 'fault_details',
            'fault_status',
            # 光缆中断补充信息组字段
            'resource_type', 'cable_route', 'cable_break_location', 'recovery_mode',
            'maintenance_mode', 'handling_unit', 'contract', 'dispatch_time',
            'departure_time', 'arrival_time', 'repair_time', 'timeout',
            'timeout_reason', 'handler',
            # 其他字段
            'comments', 'tags',
        )
        widgets = {
            'fault_occurrence_time': DateTimePicker(),
            'fault_recovery_time': DateTimePicker(),
            'dispatch_time': DateTimePicker(),
            'departure_time': DateTimePicker(),
            'arrival_time': DateTimePicker(),
            'repair_time': DateTimePicker(),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 对于现有故障，添加只读的故障编号显示字段
        if self.instance.pk:
            # 添加一个只读字段来显示故障编号
            self.fields['fault_number_display'] = forms.CharField(
                initial=self.instance.fault_number,
                label='故障编号',
                disabled=True,
                help_text='故障编号创建后不可修改'
            )
            # 重新排序字段，将显示字段放在最前面
            field_order = list(self.fields.keys())
            field_order.insert(0, 'fault_number_display')
            self.order_fields(field_order)




class OtnFaultImportForm(NetBoxModelImportForm):
    duty_officer = CSVModelChoiceField(
        queryset=get_user_model().objects.all(),
        to_field_name='username',
        required=False,
        help_text='值守人员用户名'
    )
    province = CSVModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        to_field_name='slug',
        help_text='省份（Slug）'
    )
    line_manager = CSVModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        to_field_name='username',
        help_text='线路主管用户名'
    )
    handling_unit = CSVModelChoiceField(
        queryset=ServiceProvider.objects.all(),
        required=False,
        to_field_name='name',
        help_text='处理单位名称'
    )
    contract = CSVModelChoiceField(
        queryset=Contract.objects.all(),
        required=False,
        to_field_name='name',
        help_text='代维合同名称'
    )
    interruption_location_a = CSVModelChoiceField(
        queryset=Site.objects.all(),
        to_field_name='name',
        help_text='故障位置A端站点名称'
    )
    interruption_location = CSVModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        to_field_name='name',
        help_text='故障机房名称'
    )

    class Meta:
        model = OtnFault
        fields = (
            'fault_number', 'duty_officer', 'province', 'interruption_location_a', 'interruption_location', 
            'fault_category', 'interruption_reason', 'fault_occurrence_time', 
            'fault_recovery_time', 'urgency', 'first_report_source', 
            'resource_type', 'cable_route', 'line_manager', 
            'maintenance_mode', 'handling_unit', 'contract', 'dispatch_time', 
            'departure_time', 'arrival_time', 'repair_time', 
            'timeout', 'timeout_reason', 'handler', 'cable_break_location', 'recovery_mode', 
            'interruption_longitude', 'interruption_latitude', 
            'fault_details', 'comments', 'tags'
        )



class OtnFaultImpactImportForm(NetBoxModelImportForm):
    otn_fault = CSVModelChoiceField(
        queryset=OtnFault.objects.all(),
        to_field_name='fault_number',
        help_text='故障编号'
    )
    impacted_service = CSVModelChoiceField(
        queryset=Tenant.objects.all(),
        to_field_name='name',
        help_text='影响业务（租户名称）'
    )

    class Meta:
        model = OtnFaultImpact
        fields = (
            'otn_fault', 'impacted_service', 
            'service_interruption_time', 'service_recovery_time', 
            'comments', 'tags'
        )


class OtnFaultImpactForm(NetBoxModelForm):
    otn_fault = DynamicModelChoiceField(
        queryset=OtnFault.objects.all(),
        label='关联故障'
    )
    impacted_service = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        label='影响业务'
    )
    comments = CommentField(
        label='评论',
        help_text='<span class="form-text">支持 <i class="mdi mdi-information-outline"></i> <a href="/static/docs/reference/markdown/" target="_blank" tabindex="-1">Markdown</a> 语法</span>'
    )

    class Meta:
        model = OtnFaultImpact
        fields = (
            'otn_fault', 'impacted_service',
            'service_interruption_time', 'service_recovery_time',
            'comments', 'tags',
        )
        widgets = {
            'service_interruption_time': DateTimePicker(),
            'service_recovery_time': DateTimePicker(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 如果从URL参数传递了故障ID，设置默认值
        if 'initial' in kwargs and 'otn_fault' in kwargs['initial']:
            try:
                fault_id = kwargs['initial']['otn_fault']
                fault = OtnFault.objects.get(pk=fault_id)
                
                # 设置默认时间值
                if fault.fault_occurrence_time:
                    self.fields['service_interruption_time'].initial = fault.fault_occurrence_time
                if fault.fault_recovery_time:
                    self.fields['service_recovery_time'].initial = fault.fault_recovery_time
                    
            except (OtnFault.DoesNotExist, ValueError):
                pass

from utilities.forms.utils import add_blank_choice
from utilities.forms.fields import TagFilterField, CommentField
from netbox.forms import NetBoxModelBulkEditForm

class OtnFaultBulkEditForm(NetBoxModelBulkEditForm):
    """OTN故障批量编辑表单"""
    model = OtnFault
    
    # 可批量编辑的字段
    duty_officer = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='值守人员'
    )
    province = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label='省份'
    )
    line_manager = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='线路主管'
    )
    handling_unit = DynamicModelChoiceField(
        queryset=ServiceProvider.objects.all(),
        required=False,
        label='处理单位'
    )
    contract = DynamicModelChoiceField(
        queryset=Contract.objects.all(),
        required=False,
        label='代维合同',
        query_params={
            'service_provider_id': '$handling_unit',
        }
    )
    interruption_location_a = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='故障位置A端站点'
    )
    fault_category = forms.ChoiceField(
        choices=add_blank_choice(FaultCategoryChoices),
        required=False,
        label='故障分类'
    )
    interruption_reason = forms.ChoiceField(
        choices=add_blank_choice(OtnFault.INTERRUPTION_REASON_CHOICES),
        required=False,
        label='故障原因'
    )
    urgency = forms.ChoiceField(
        choices=add_blank_choice(UrgencyChoices),
        required=False,
        label='紧急程度'
    )
    first_report_source = forms.ChoiceField(
        choices=add_blank_choice(OtnFault.FIRST_REPORT_SOURCE_CHOICES),
        required=False,
        label='第一报障来源'
    )

    maintenance_mode = forms.ChoiceField(
        choices=add_blank_choice(MaintenanceModeChoices),
        required=False,
        label='维护方式'
    )
    resource_type = forms.ChoiceField(
        choices=add_blank_choice(ResourceTypeChoices),
        required=False,
        label='资源类型'
    )
    cable_route = forms.ChoiceField(
        choices=add_blank_choice(CableRouteChoices),
        required=False,
        label='光缆路由属性'
    )
    cable_break_location = forms.ChoiceField(
        choices=add_blank_choice(CableBreakLocationChoices),
        required=False,
        label='光缆中断部位'
    )
    recovery_mode = forms.ChoiceField(
        choices=add_blank_choice(RecoveryModeChoices),
        required=False,
        label='恢复方式'
    )
    fault_status = forms.ChoiceField(
        choices=add_blank_choice(FaultStatusChoices),
        required=False,
        label='处理状态'
    )
    timeout = forms.BooleanField(
        required=False,
        label='规定时间内完成修复'
    )
    handler = forms.CharField(
        required=False,
        label='故障处理人'
    )
    timeout_reason = forms.CharField(
        required=False,
        label='超时原因'
    )
    comments = CommentField(
        required=False,
        label='评论'
    )
    
    nullable_fields = (
        'province', 'line_manager', 'handling_unit', 'fault_category',
        'interruption_reason', 'maintenance_mode', 'resource_type',
        'cable_break_location', 'recovery_mode', 'fault_status', 'handler', 'timeout_reason', 'comments',
        'interruption_location_a', 'first_report_source', 'cable_route'
    )

    # fieldsets = (
    #     ('故障信息', (
    #         'duty_officer', 'province', 'line_manager', 'handling_unit',
    #         'fault_category', 'interruption_reason', 'urgency',
    #         'first_report_source', 'planned', 'resource_type', 'cable_route',
    #     )),
    #     ('处理信息', (
    #         'maintenance_mode', 'recovery_mode', 'timeout',
    #         'handler', 'timeout_reason',
    #     )),
    #     ('其他', (
    #         'comments',
    #     )),
    # )

class OtnFaultImpactBulkEditForm(NetBoxModelBulkEditForm):
    otn_fault = DynamicModelChoiceField(
        queryset=OtnFault.objects.all(),
        required=False,
        label='关联故障'
    )
    impacted_service = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        label='影响业务'
    )
    service_interruption_time = forms.DateTimeField(
        required=False,
        label='业务故障时间',
        widget=DateTimePicker()
    )
    service_recovery_time = forms.DateTimeField(
        required=False,
        label='业务恢复时间',
        widget=DateTimePicker()
    )
    comments = CommentField(
        label='评论'
    )

    model = OtnFaultImpact
    fieldsets = (
        ('故障影响业务', (
            'otn_fault', 'impacted_service', 'service_interruption_time', 'service_recovery_time', 'comments',
        )),
    )
    nullable_fields = (
        'service_interruption_time', 'service_recovery_time', 'comments',
    )

class OtnFaultFilterForm(NetBoxModelFilterSetForm):
    tag = TagFilterField(OtnFault)
    model = OtnFault
    
    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet(
            'fault_status', 'urgency', 'province', 'interruption_location_a', 
            'interruption_location', 'interruption_longitude', 'interruption_latitude',
            'fault_category', 'interruption_reason', 'fault_occurrence_time', 
            'fault_recovery_time', 'first_report_source', 'line_manager', 
            'duty_officer', 'fault_details',
            name='故障信息'
        ),
        FieldSet(
            'resource_type', 'cable_route', 'cable_break_location', 'recovery_mode',
            'maintenance_mode', 'handling_unit', 'contract', 'dispatch_time',
            'departure_time', 'arrival_time', 'timeout',
            'timeout_reason', 'handler', 'comments',
            name='光缆中断补充信息'
        ),
    )
    
    duty_officer = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='值守人员'
    )
    interruption_location_a = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='故障位置A端站点'
    )
    interruption_location = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='故障位置Z端站点'
    )
    province = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label='省份'
    )
    line_manager = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='线路主管'
    )
    handling_unit = DynamicModelChoiceField(
        queryset=ServiceProvider.objects.all(),
        required=False,
        label='处理单位'
    )
    contract = DynamicModelChoiceField(
        queryset=Contract.objects.all(),
        required=False,
        label='代维合同',
        query_params={
            'service_provider_id': '$handling_unit',
        }
    )
    fault_category = forms.ChoiceField(
        choices=add_blank_choice(FaultCategoryChoices),
        required=False,
        label='故障分类'
    )
    interruption_reason = forms.ChoiceField(
        choices=add_blank_choice(OtnFault.INTERRUPTION_REASON_CHOICES),
        required=False,
        label='故障原因'
    )
    urgency = forms.ChoiceField(
        choices=add_blank_choice(UrgencyChoices),
        required=False,
        label='紧急程度'
    )
    first_report_source = forms.ChoiceField(
        choices=add_blank_choice(OtnFault.FIRST_REPORT_SOURCE_CHOICES),
        required=False,
        label='第一报障来源'
    )

    maintenance_mode = forms.ChoiceField(
        choices=add_blank_choice(MaintenanceModeChoices),
        required=False,
        label='维护方式'
    )
    resource_type = forms.ChoiceField(
        choices=add_blank_choice(ResourceTypeChoices),
        required=False,
        label='资源类型'
    )
    cable_route = forms.ChoiceField(
        choices=add_blank_choice(CableRouteChoices),
        required=False,
        label='光缆路由属性'
    )
    cable_break_location = forms.ChoiceField(
        choices=add_blank_choice(CableBreakLocationChoices),
        required=False,
        label='光缆中断部位'
    )
    recovery_mode = forms.ChoiceField(
        choices=add_blank_choice(RecoveryModeChoices),
        required=False,
        label='恢复方式'
    )
    fault_status = forms.ChoiceField(
        choices=add_blank_choice(FaultStatusChoices),
        required=False,
        label='处理状态'
    )
    timeout = forms.BooleanField(
        required=False,
        label='规定时间内完成修复'
    )
    fault_occurrence_time = forms.DateTimeField(
        required=False,
        label='故障中断时间',
        widget=DateTimePicker()
    )
    fault_recovery_time = forms.DateTimeField(
        required=False,
        label='故障恢复时间',
        widget=DateTimePicker()
    )
    dispatch_time = forms.DateTimeField(
        required=False,
        label='处理派发时间',
        widget=DateTimePicker()
    )
    departure_time = forms.DateTimeField(
        required=False,
        label='维修出发时间',
        widget=DateTimePicker()
    )
    arrival_time = forms.DateTimeField(
        required=False,
        label='到达现场时间',
        widget=DateTimePicker()
    )
    repair_time = forms.DateTimeField(
        required=False,
        label='故障修复时间',
        widget=DateTimePicker()
    )
    fault_details = forms.CharField(
        required=False,
        label='故障详情和处理过程'
    )
    timeout_reason = forms.CharField(
        required=False,
        label='超时原因'
    )
    handler = forms.CharField(
        required=False,
        label='故障处理人'
    )
    interruption_longitude = forms.DecimalField(
        required=False,
        label='故障位置经度',
        max_digits=9,
        decimal_places=6
    )
    interruption_latitude = forms.DecimalField(
        required=False,
        label='故障位置纬度',
        max_digits=8,
        decimal_places=6
    )
    comments = forms.CharField(
        required=False,
        label='评论'
    )

class OtnFaultImpactFilterForm(NetBoxModelFilterSetForm):
    tag = TagFilterField(OtnFaultImpact)
    model = OtnFaultImpact
    otn_fault = DynamicModelChoiceField(
        queryset=OtnFault.objects.all(),
        required=False,
        label='关联故障'
    )
    impacted_service = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        label='影响业务'
    )

class OtnPathForm(NetBoxModelForm):
    site_a = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        label='A端站点'
    )
    site_z = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        label='Z端站点'
    )
    comments = CommentField(
        label='评论'
    )

    class Meta:
        model = OtnPath
        fields = (
            'name', 'cable_type', 'site_a', 'site_z', 'geometry',
            'calculated_length', 'description', 'comments', 'tags',
        )

class OtnPathImportForm(NetBoxModelImportForm):
    site_a = CSVModelChoiceField(
        queryset=Site.objects.all(),
        to_field_name='name',
        help_text='A端站点名称'
    )
    site_z = CSVModelChoiceField(
        queryset=Site.objects.all(),
        to_field_name='name',
        help_text='Z端站点名称'
    )

    class Meta:
        model = OtnPath
        fields = (
            'name', 'cable_type', 'site_a', 'site_z', 'geometry',
            'calculated_length', 'description', 'comments', 'tags',
        )

class OtnPathBulkEditForm(NetBoxModelBulkEditForm):
    model = OtnPath
    cable_type = forms.ChoiceField(
        choices=add_blank_choice(CableTypeChoices),
        required=False,
        label='光缆类型'
    )
    calculated_length = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='计算长度'
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea,
        label='描述'
    )
    comments = CommentField(
        label='评论'
    )

    fieldsets = (
        ('光缆路径', (
            'cable_type', 'calculated_length', 'description', 'comments',
        )),
    )
    nullable_fields = (
        'geometry', 'calculated_length', 'description', 'comments',
    )


class OtnPathFilterForm(NetBoxModelFilterSetForm):
    model = OtnPath
    tag = TagFilterField(OtnPath)
    groups = DynamicModelMultipleChoiceField(
        queryset=OtnPathGroup.objects.all(),
        required=False,
        label='所属路径组'
    )
    cable_type = forms.ChoiceField(
        choices=add_blank_choice(CableTypeChoices),
        required=False,
        label='光缆类型'
    )
    site_a = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='A端站点'
    )
    site_z = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='Z端站点'
    )


class OtnPathGroupForm(NetBoxModelForm):
    """路径组编辑表单"""
    paths = DynamicModelMultipleChoiceField(
        queryset=OtnPath.objects.all(),
        required=False,
        label='包含路径'
    )
    comments = CommentField(
        label='评论'
    )

    class Meta:
        model = OtnPathGroup
        fields = (
            'name', 'slug', 'description', 'paths', 'comments', 'tags',
        )


class OtnPathGroupFilterForm(NetBoxModelFilterSetForm):
    """路径组过滤表单"""
    model = OtnPathGroup
    tag = TagFilterField(OtnPathGroup)

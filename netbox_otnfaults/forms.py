from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm, NetBoxModelImportForm, NetBoxModelBulkEditForm
from .models import (
    OtnFault, OtnFaultImpact, FaultCategoryChoices, UrgencyChoices, 
    MaintenanceModeChoices, ResourceTypeChoices, ResourceOwnerChoices, CableRouteChoices,
    FaultStatusChoices, CableBreakLocationChoices, RecoveryModeChoices,
    PowerDataTypeChoices, PowerRecoveryModeChoices, PowerMaintenanceModeChoices,
    OtnPath, CableTypeChoices, OtnPathGroup, OtnPathGroupSite, BareFiberService,
    CircuitService, ServiceGroupChoices, BusinessCategoryChoices, ServiceTypeChoices,
    CircuitOperationStatusChoices, SLALevelChoices
)
import json

from django import forms
from django.core.exceptions import ValidationError
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, CommentField, CSVModelChoiceField, CSVModelMultipleChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet
from utilities.forms.widgets import DateTimePicker, DatePicker
from dcim.models import Site, Region
from tenancy.models import Tenant, TenantGroup
from django.contrib.auth import get_user_model
from netbox_contract.models import ServiceProvider, Contract

class OtnFaultForm(NetBoxModelForm):
    duty_officer = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        label='值守人员'
    )
    interruption_location_a = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        label='故障位置A端站点',
        query_params={
            'region_id': '$province'
        }
    )
    interruption_location = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='故障位置Z端站点',
        query_params={
            'connected_to_a': '$interruption_location_a'
        }
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
    operations_manager = DynamicModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='运维主管'
    )
    handling_unit = DynamicModelChoiceField(
        queryset=ServiceProvider.objects.all(),
        required=False,
        label='代维方/租赁方'
    )
    contract = DynamicModelChoiceField(
        queryset=Contract.objects.all(),
        required=False,
        label='代维/租赁合同',
        query_params={
            'external_party_object': '$handling_unit',
        }
    )
    comments = CommentField(
        label='评论',
        help_text='<span class="form-text">支持 <i class="mdi mdi-information-outline"></i> <a href="/static/docs/reference/markdown/" target="_blank" tabindex="-1">Markdown</a> 语法</span>'
    )
    manager_reviewer = forms.CharField(
        required=False,
        label='线路主管复核人',
        widget=forms.TextInput(attrs={'readonly': True, 'class': 'form-control'})
    )
    manager_review_time = forms.DateTimeField(
        required=False,
        label='线路主管复核时间',
        widget=forms.DateTimeInput(attrs={'readonly': True, 'class': 'form-control'})
    )
    noc_reviewer = forms.CharField(
        required=False,
        label='网管人员复核人',
        widget=forms.TextInput(attrs={'readonly': True, 'class': 'form-control'})
    )
    noc_review_time = forms.DateTimeField(
        required=False,
        label='网管人员复核时间',
        widget=forms.DateTimeInput(attrs={'readonly': True, 'class': 'form-control'})
    )
    
    fieldsets = (
        FieldSet(
            'fault_category', 'urgency', 'province',
            'interruption_location_a', 'interruption_location',
            'interruption_latitude', 'interruption_longitude',
            'interruption_reason', 'interruption_reason_detail',
            'first_report_source', 'duty_officer',
            'fault_occurrence_time', 'dispatch_time', 'departure_time', 'arrival_time', 'fault_recovery_time',
            'closure_time', 'handler', 'fault_details', 'fault_status',
            name='故障信息'
        ),
        FieldSet(
            'line_manager', 'resource_type', 'resource_owner', 'cable_route', 'cable_break_location', 'recovery_mode',
            'maintenance_mode', 'handling_unit', 'contract', 'repair_time', 'timeout',
            'timeout_reason',
            name='线路主管补充信息'
        ),
        FieldSet(
            'power_data_type', 'power_recovery_mode', 'power_maintenance_mode',
            name='供电故障补充信息'
        ),
        FieldSet(
            'manager_reviewed', 'manager_reviewer', 'manager_review_time',
            'noc_reviewed', 'noc_reviewer', 'noc_review_time',
            name='故障复核'
        ),
        FieldSet('tags', name='标签'),
        FieldSet('operations_manager', name='运维主管'),
        FieldSet('comments', name='评论'),
    )



    class Meta:
        model = OtnFault
        fields = (
            # 故障信息组字段
            'fault_category', 'urgency', 'province', 'interruption_location_a', 'interruption_location',
            'interruption_latitude', 'interruption_longitude',
            'interruption_reason', 'interruption_reason_detail', 'fault_occurrence_time', 'fault_recovery_time',
            'closure_time', 'first_report_source', 'duty_officer', 'handler', 'fault_details',
            'fault_status',
            # 线路主管补充信息组字段
            'line_manager', 'resource_type', 'resource_owner', 'cable_route', 'cable_break_location', 'recovery_mode',
            'maintenance_mode', 'handling_unit', 'contract', 'dispatch_time',
            'departure_time', 'arrival_time', 'repair_time', 'timeout',
            'timeout_reason',
            # 供电故障补充信息组字段
            'power_data_type', 'power_recovery_mode', 'power_maintenance_mode',
            # 故障复核信息字段
            'manager_reviewed', 'manager_reviewer', 'manager_review_time',
            'noc_reviewed', 'noc_reviewer', 'noc_review_time',
            # 其他字段
            'comments', 'tags', 'operations_manager'
        )
        widgets = {
            'fault_occurrence_time': DateTimePicker(),
            'fault_recovery_time': DateTimePicker(),
            'dispatch_time': DateTimePicker(),
            'departure_time': DateTimePicker(),
            'arrival_time': DateTimePicker(),
            'repair_time': DateTimePicker(),
            'closure_time': DateTimePicker(),
            'fault_details': forms.Textarea(attrs={'rows': 5}),
            'timeout_reason': forms.TextInput(),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初始设置 API 数据源（前端会动态挂载 connected_to_a 参数）
        self.fields['interruption_location'].widget.attrs['data-url'] = '/api/plugins/otnfaults/connected-sites/'
        self.fields['tags'].help_text = '若故障涉及88系统，需勾选对应标签。'
        if not self.instance.fault_category:
            self.initial['fault_category'] = FaultCategoryChoices.FIBER_BREAK
            self.fields['fault_category'].initial = FaultCategoryChoices.FIBER_BREAK
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
    operations_manager = CSVModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        to_field_name='username',
        help_text='运维主管用户名'
    )
    handling_unit = CSVModelChoiceField(
        queryset=ServiceProvider.objects.all(),
        required=False,
        to_field_name='name',
        help_text='代维方/租赁方名称'
    )
    contract = CSVModelChoiceField(
        queryset=Contract.objects.all(),
        required=False,
        to_field_name='name',
        help_text='代维/租赁合同名称'
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
            'fault_category', 'interruption_reason', 'interruption_reason_detail', 'fault_occurrence_time', 
            'fault_recovery_time', 'urgency', 'first_report_source', 
            'resource_type', 'resource_owner', 'cable_route', 'line_manager', 
            'maintenance_mode', 'handling_unit', 'contract', 'dispatch_time', 
            'departure_time', 'arrival_time', 'repair_time', 
            'timeout', 'timeout_reason', 'handler', 'cable_break_location', 'recovery_mode', 
            'interruption_latitude', 'interruption_longitude', 
            'fault_details', 'comments', 'tags', 'operations_manager'
        )



class OtnFaultImpactImportForm(NetBoxModelImportForm):
    otn_fault = CSVModelChoiceField(
        queryset=OtnFault.objects.all(),
        to_field_name='fault_number',
        help_text='故障编号'
    )
    bare_fiber_service = CSVModelChoiceField(
        queryset=BareFiberService.objects.all(),
        to_field_name='name',
        required=False,
        help_text='裸纤业务'
    )
    circuit_service = CSVModelChoiceField(
        queryset=CircuitService.objects.all(),
        to_field_name='name',
        required=False,
        help_text='电路业务'
    )

    class Meta:
        model = OtnFaultImpact
        fields = (
            'otn_fault', 'service_type', 'bare_fiber_service', 'circuit_service', 
            'service_interruption_time', 'service_recovery_time', 
            'comments', 'tags'
        )


class OtnFaultImpactForm(NetBoxModelForm):
    otn_fault = DynamicModelChoiceField(
        queryset=OtnFault.objects.all(),
        label='直接故障'
    )
    circuit_business_category = forms.ChoiceField(
        choices=[('', '---------')] + [(v, l) for v, l, *_ in BusinessCategoryChoices.CHOICES],
        required=False,
        label='业务门类'
    )
    circuit_service_group = forms.ChoiceField(
        choices=[('', '---------')] + [(v, l) for v, l, *_ in ServiceGroupChoices.CHOICES],
        required=False,
        label='业务组'
    )
    circuit_special_line_name = forms.ChoiceField(
        choices=[('', '---------')],
        required=False,
        label='专线名称'
    )
    bare_fiber_service = DynamicModelChoiceField(
        queryset=BareFiberService.objects.all(),
        required=False,
        label='业务名称'
    )
    circuit_service = forms.ModelChoiceField(
        queryset=CircuitService.objects.all(),
        required=False,
        label='电路业务'
    )
    service_site_a = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='业务站点A'
    )
    service_site_z = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='业务站点Z'
    )
    secondary_faults = DynamicModelMultipleChoiceField(
        queryset=OtnFault.objects.all(),
        required=False,
        label='其他关联故障',
        help_text='若业务中断是因为多次故障引起的（双断、三断等），直接故障为最后一次造成最终业务中断的故障，其他关联故障可选择前续涉及的多次故障（引起单断的故障）。'
    )
    comments = CommentField(
        label='评论',
        help_text='<span class="form-text">支持 <i class="mdi mdi-information-outline"></i> <a href="/static/docs/reference/markdown/" target="_blank" tabindex="-1">Markdown</a> 语法</span>'
    )

    class Meta:
        model = OtnFaultImpact
        fields = (
            'otn_fault', 'secondary_faults', 'service_type', 'bare_fiber_service', 'service_site_a', 'service_site_z',
            'circuit_business_category', 'circuit_service_group', 'circuit_special_line_name', 'circuit_service',
            'service_interruption_time', 'service_recovery_time',
            'comments', 'tags',
        )
        widgets = {
            'service_interruption_time': DateTimePicker(),
            'service_recovery_time': DateTimePicker(),
        }

    def __init__(self, *args, **kwargs):
        initial_data = kwargs.get('initial') or {}
        super().__init__(*args, **kwargs)

        circuit_services = list(
            CircuitService.objects.order_by('business_category', 'service_group', 'special_line_name', 'name').values(
                'pk', 'business_category', 'service_group', 'special_line_name', 'name'
            )
        )
        business_category_label_map = {value: label for value, label, *_ in BusinessCategoryChoices.CHOICES}
        service_group_label_map = {value: label for value, label, *_ in ServiceGroupChoices.CHOICES}
        for service in circuit_services:
            service['business_category_label'] = business_category_label_map.get(service['business_category'], service['business_category'])
            service['service_group_label'] = service_group_label_map.get(service['service_group'], service['service_group'])
        service_catalog = json.dumps(circuit_services, ensure_ascii=False)
        special_line_choices = [('', '---------')]
        for service in circuit_services:
            label = service['special_line_name']
            if service['name']:
                label = f"{label} ({service['name']})"
            special_line_choices.append((str(service['pk']), label))
        self.fields['circuit_special_line_name'].choices = special_line_choices
        self.fields['circuit_special_line_name'].widget.attrs['data-circuit-services'] = service_catalog
        self.fields['circuit_service'].widget.attrs['data-circuit-services'] = service_catalog

        if self.instance.pk and self.instance.circuit_service:
            self.fields['circuit_business_category'].initial = self.instance.circuit_service.business_category
            self.fields['circuit_service_group'].initial = self.instance.circuit_service.service_group
            self.fields['circuit_special_line_name'].initial = str(self.instance.circuit_service.pk)
            self.fields['circuit_service'].initial = self.instance.circuit_service.pk
        
        # 如果从URL参数传递了故障ID，设置默认值
        if initial_data.get('otn_fault'):
            try:
                fault_id = initial_data['otn_fault']
                fault = OtnFault.objects.get(pk=fault_id)
                
                # 设置默认时间值
                if fault.fault_occurrence_time:
                    self.fields['service_interruption_time'].initial = fault.fault_occurrence_time
                if fault.fault_recovery_time:
                    self.fields['service_recovery_time'].initial = fault.fault_recovery_time
                    
            except (OtnFault.DoesNotExist, ValueError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data is None:
            cleaned_data = getattr(self, 'cleaned_data', None) or {}
            
        if cleaned_data.get('service_type') != ServiceTypeChoices.CIRCUIT:
            return cleaned_data

        selected_service = cleaned_data.get('circuit_service')
        selected_special_line = cleaned_data.get('circuit_special_line_name')
        if selected_service or not selected_special_line:
            return cleaned_data

        try:
            cleaned_data['circuit_service'] = CircuitService.objects.get(pk=selected_special_line)
        except CircuitService.DoesNotExist as exc:
            raise ValidationError({'circuit_special_line_name': '所选专线名称对应的电路业务不存在。'}) from exc

        return cleaned_data

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
    operations_manager = DynamicModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='运维主管'
    )
    handling_unit = DynamicModelChoiceField(
        queryset=ServiceProvider.objects.all(),
        required=False,
        label='代维方/租赁方'
    )
    contract = DynamicModelChoiceField(
        queryset=Contract.objects.all(),
        required=False,
        label='代维/租赁合同',
        query_params={
            'external_party_object': '$handling_unit',
        }
    )
    interruption_location_a = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='故障位置A端站点',
        query_params={
            'region_id': '$province'
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
        label='一级原因'
    )
    interruption_reason_detail = forms.ChoiceField(
        choices=add_blank_choice(OtnFault.INTERRUPTION_REASON_DETAIL_CHOICES),
        required=False,
        label='二级原因'
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
        label='光纤来源'
    )
    resource_owner = forms.ChoiceField(
        choices=add_blank_choice(ResourceOwnerChoices),
        required=False,
        label='资源所有者'
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
        'province', 'line_manager', 'operations_manager', 'handling_unit', 'fault_category',
        'interruption_reason', 'interruption_reason_detail', 'maintenance_mode', 'resource_type',
        'resource_owner', 'cable_break_location', 'recovery_mode', 'fault_status', 'handler', 'timeout_reason', 'comments',
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
        label='直接故障'
    )
    service_type = forms.ChoiceField(
        choices=add_blank_choice(ServiceTypeChoices),
        required=False,
        label='业务类型'
    )
    bare_fiber_service = DynamicModelChoiceField(
        queryset=BareFiberService.objects.all(),
        required=False,
        label='裸纤业务'
    )
    circuit_service = DynamicModelChoiceField(
        queryset=CircuitService.objects.all(),
        required=False,
        label='电路业务'
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
            'otn_fault', 'service_type', 'bare_fiber_service', 'circuit_service', 'service_interruption_time', 'service_recovery_time', 'comments',
        )),
    )
    nullable_fields = (
        'service_interruption_time', 'service_recovery_time', 'comments', 'bare_fiber_service', 'circuit_service'
    )

class OtnFaultFilterForm(NetBoxModelFilterSetForm):
    tag = TagFilterField(OtnFault)
    model = OtnFault
    
    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet(
            'fault_category', 'fault_status', 'urgency', 'province',
            'interruption_location_a', 'interruption_location', 'interruption_latitude', 'interruption_longitude',
            'interruption_reason', 'interruption_reason_detail',
            'first_report_source', 'duty_officer',
            'fault_occurrence_time', 'dispatch_time', 'departure_time', 'arrival_time', 'fault_recovery_time',
            'closure_time', 'handler', 'fault_details',
            name='故障信息'
        ),
        FieldSet(
            'line_manager', 'resource_type', 'resource_owner', 'cable_route', 'cable_break_location', 'recovery_mode',
            'maintenance_mode', 'handling_unit', 'contract', 'timeout',
            'timeout_reason', 'comments',
            name='线路主管补充信息'
        ),
        FieldSet(
            'power_data_type', 'power_recovery_mode', 'power_maintenance_mode',
            name='供电故障补充信息'
        ),
        FieldSet(
            'manager_reviewed', 'manager_reviewer', 'manager_review_time',
            'noc_reviewed', 'noc_reviewer', 'noc_review_time',
            name='故障复核'
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
        label='故障位置A端站点',
        query_params={
            'region_id': '$province'
        }
    )
    interruption_location = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='故障位置Z端站点',
        query_params={
            'connected_to_a': '$interruption_location_a'
        }
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
    operations_manager = DynamicModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='运维主管'
    )
    handling_unit = DynamicModelChoiceField(
        queryset=ServiceProvider.objects.all(),
        required=False,
        label='代维方/租赁方'
    )
    contract = DynamicModelChoiceField(
        queryset=Contract.objects.all(),
        required=False,
        label='代维/租赁合同',
        query_params={
            'external_party_object': '$handling_unit',
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interruption_location'].widget.attrs['data-url'] = '/api/plugins/otnfaults/connected-sites/'

    fault_category = forms.ChoiceField(
        choices=add_blank_choice(FaultCategoryChoices),
        required=False,
        label='故障分类'
    )
    interruption_reason = forms.ChoiceField(
        choices=add_blank_choice(OtnFault.INTERRUPTION_REASON_CHOICES),
        required=False,
        label='一级原因'
    )
    interruption_reason_detail = forms.ChoiceField(
        choices=add_blank_choice(OtnFault.INTERRUPTION_REASON_DETAIL_CHOICES),
        required=False,
        label='二级原因'
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
        label='光纤来源'
    )
    resource_owner = forms.ChoiceField(
        choices=add_blank_choice(ResourceOwnerChoices),
        required=False,
        label='资源所有者'
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
        label='故障起始时间',
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
    power_data_type = forms.ChoiceField(
        choices=add_blank_choice(PowerDataTypeChoices),
        required=False,
        label='资料类型'
    )
    power_recovery_mode = forms.ChoiceField(
        choices=add_blank_choice(PowerRecoveryModeChoices),
        required=False,
        label='恢复方式'
    )
    power_maintenance_mode = forms.ChoiceField(
        choices=add_blank_choice(PowerMaintenanceModeChoices),
        required=False,
        label='维护方式'
    )

class OtnFaultImpactFilterForm(NetBoxModelFilterSetForm):
    tag = TagFilterField(OtnFaultImpact)
    model = OtnFaultImpact
    otn_fault = DynamicModelChoiceField(
        queryset=OtnFault.objects.all(),
        required=False,
        label='直接故障'
    )
    service_type = forms.ChoiceField(
        choices=add_blank_choice(ServiceTypeChoices),
        required=False,
        label='业务类型'
    )
    bare_fiber_service = DynamicModelChoiceField(
        queryset=BareFiberService.objects.all(),
        required=False,
        label='裸纤业务'
    )
    circuit_service = DynamicModelChoiceField(
        queryset=CircuitService.objects.all(),
        required=False,
        label='电路业务'
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
    groups = DynamicModelMultipleChoiceField(
        queryset=OtnPathGroup.objects.all(),
        required=False,
        label='所属路径组'
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
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 如果是编辑现有对象，设置 groups 的初始值
        if self.instance.pk:
            self.fields['groups'].initial = self.instance.groups.all()

    def save(self, commit=True):
        # 先保存路径对象
        instance = super().save(commit=commit)
        
        if commit:
            # 手动处理 groups 多对多关系（反向关系需要特殊处理）
            # 获取表单中选择的路径组
            selected_groups = self.cleaned_data.get('groups', [])
            
            # 获取当前路径已属于的所有路径组
            current_groups = set(instance.groups.all())
            selected_groups_set = set(selected_groups)
            
            # 需要添加到的路径组
            groups_to_add = selected_groups_set - current_groups
            for group in groups_to_add:
                group.paths.add(instance)
            
            # 需要从中移除的路径组
            groups_to_remove = current_groups - selected_groups_set
            for group in groups_to_remove:
                group.paths.remove(instance)
        
        return instance

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
    add_groups = DynamicModelMultipleChoiceField(
        queryset=OtnPathGroup.objects.all(),
        required=False,
        label='添加到路径组'
    )
    remove_groups = DynamicModelMultipleChoiceField(
        queryset=OtnPathGroup.objects.all(),
        required=False,
        label='从路径组移除'
    )
    calculated_length = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='长度'
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        label='描述'
    )
    comments = CommentField(
        label='评论'
    )

    fieldsets = (
        FieldSet('cable_type', 'calculated_length', 'description', 'comments', name='光缆路径'),
        FieldSet('add_groups', 'remove_groups', name='路径组管理'),
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


class OtnPathGroupSiteForm(NetBoxModelForm):
    """路径组站点关联编辑表单"""
    path_group = DynamicModelChoiceField(
        queryset=OtnPathGroup.objects.all(),
        label='路径组'
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        label='站点'
    )
    comments = CommentField(
        label='评论'
    )

    class Meta:
        model = OtnPathGroupSite
        fields = ('path_group', 'site', 'role', 'position', 'comments', 'tags')


class BareFiberServiceForm(NetBoxModelForm):
    """裸纤业务编辑表单"""
    tenant_group = DynamicModelChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        label='租户组'
    )
    business_manager = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='业务主管'
    )
    comments = CommentField(
        label='评论',
        help_text='<span class="form-text">支持 <i class="mdi mdi-information-outline"></i> <a href="/static/docs/reference/markdown/" target="_blank" tabindex="-1">Markdown</a> 语法</span>'
    )

    fieldsets = (
        FieldSet('name', 'slug', 'tenant_group', 'business_manager', name='裸纤业务'),
        FieldSet('billing_start_time', 'billing_end_time', name='计费周期'),
        FieldSet('tags', name='其他'),
    )

    class Meta:
        model = BareFiberService
        fields = ('name', 'slug', 'tenant_group', 'business_manager', 'billing_start_time', 'billing_end_time', 'comments', 'tags')
        widgets = {
            'billing_start_time': DatePicker(),
            'billing_end_time': DatePicker(),
        }


class BareFiberServiceFilterForm(NetBoxModelFilterSetForm):
    """裸纤业务过滤表单"""
    model = BareFiberService
    tag = TagFilterField(BareFiberService)
    
    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('tenant_group', 'business_manager', name='属性'),
    )
    
    tenant_group = DynamicModelChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        label='租户组'
    )
    business_manager = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='业务主管'
    )


class BareFiberServiceImportForm(NetBoxModelImportForm):
    """裸纤业务导入表单"""
    business_manager = CSVModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        to_field_name='username',
        help_text='业务主管用户名'
    )

    class Meta:
        model = BareFiberService
        fields = ('name', 'slug', 'tenant_group', 'business_manager', 'billing_start_time', 'billing_end_time', 'comments', 'tags')


class BareFiberServiceBulkEditForm(NetBoxModelBulkEditForm):
    """裸纤业务批量编辑表单"""
    model = BareFiberService
    tenant_group = DynamicModelChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        label='租户组'
    )
    business_manager = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='业务主管'
    )
    billing_start_time = forms.DateField(
        required=False,
        label='计费起始时间',
        widget=DatePicker()
    )
    billing_end_time = forms.DateField(
        required=False,
        label='计费结束时间',
        widget=DatePicker()
    )

    fieldsets = (
        FieldSet('tenant_group', 'business_manager', name='基本信息'),
        FieldSet('billing_start_time', 'billing_end_time', name='计费周期'),
    )

    nullable_fields = ('tenant_group', 'business_manager', 'billing_start_time', 'billing_end_time')


class CircuitServiceForm(NetBoxModelForm):
    """电路业务编辑表单"""
    business_manager = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='业务主管'
    )
    is_external_business = forms.BooleanField(
        required=False,
        label='对部服务'
    )
    ring_protection = forms.BooleanField(
        required=False,
        label='环网保护'
    )
    comments = CommentField(
        label='评论',
        help_text='<span class="form-text">支持 <i class="mdi mdi-information-outline"></i> <a href="/static/docs/reference/markdown/" target="_blank" tabindex="-1">Markdown</a> 语法</span>'
    )

    fieldsets = (
        FieldSet('special_line_name', 'name', 'slug', 'business_category', 'service_group', 'bandwidth', 'business_manager', 'is_external_business', 'ring_protection', 'operation_status', 'sla_level', name='电路业务'),
        FieldSet('billing_start_time', 'billing_end_time', name='计费周期'),
        FieldSet('tags', name='其他'),
    )

    class Meta:
        model = CircuitService
        fields = ('special_line_name', 'name', 'slug', 'service_group', 'business_category', 'bandwidth', 'business_manager', 'is_external_business', 'ring_protection', 'operation_status', 'sla_level', 'billing_start_time', 'billing_end_time', 'comments', 'tags')
        widgets = {
            'billing_start_time': DatePicker(),
            'billing_end_time': DatePicker(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        category_map = json.dumps(CircuitService.SERVICE_GROUP_CATEGORY_MAP, ensure_ascii=False)
        service_group_field = self.fields['service_group']
        service_group_field.widget.attrs['data-service-group-category-map'] = category_map
        service_group_field.widget.attrs['data-placeholder'] = '请先选择业务门类'


class CircuitServiceFilterForm(NetBoxModelFilterSetForm):
    """电路业务过滤表单"""
    model = CircuitService
    tag = TagFilterField(CircuitService)
    is_external_business = forms.NullBooleanField(
        required=False,
        label='对部服务'
    )
    ring_protection = forms.NullBooleanField(
        required=False,
        label='环网保护'
    )


    fieldsets = (
        FieldSet('q', 'special_line_name', 'filter_id', 'tag'),
        FieldSet('business_category', 'service_group', 'bandwidth', 'business_manager', 'is_external_business', 'ring_protection', 'operation_status', 'sla_level', name='属性'),
    )

    special_line_name = forms.CharField(
        required=False,
        label='专线名称'
    )
    business_category = forms.ChoiceField(
        choices=[('', '---------')] + [(v, l) for v, l, *_ in BusinessCategoryChoices.CHOICES],
        required=False,
        label='业务门类'
    )
    service_group = forms.ChoiceField(
        choices=[('', '---------')] + [(v, l) for v, l, *_ in ServiceGroupChoices.CHOICES],
        required=False,
        label='业务组'
    )
    bandwidth = forms.IntegerField(
        required=False,
        label='带宽(Mbps)'
    )
    business_manager = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='业务主管'
    )
    operation_status = forms.ChoiceField(
        choices=[('', '---------')] + [(v, l) for v, l, *_ in CircuitOperationStatusChoices.CHOICES],
        required=False,
        label='运行状态'
    )
    sla_level = forms.ChoiceField(
        choices=[('', '---------')] + [(v, l) for v, l, *_ in SLALevelChoices.CHOICES],
        required=False,
        label='SLA等级'
    )


class CircuitServiceImportForm(NetBoxModelImportForm):
    """电路业务导入表单"""
    business_manager = CSVModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        to_field_name='username',
        help_text='业务主管用户名'
    )

    class Meta:
        model = CircuitService
        fields = ('special_line_name', 'name', 'slug', 'service_group', 'business_category', 'bandwidth', 'business_manager', 'is_external_business', 'ring_protection', 'operation_status', 'sla_level', 'billing_start_time', 'billing_end_time', 'comments', 'tags')


class CircuitServiceBulkEditForm(NetBoxModelBulkEditForm):
    """电路业务批量编辑表单"""
    model = CircuitService
    business_category = forms.ChoiceField(
        choices=[('', '---------')] + [(v, l) for v, l, *_ in BusinessCategoryChoices.CHOICES],
        required=False,
        label='业务门类'
    )
    is_external_business = forms.NullBooleanField(
        required=False,
        label='对部服务'
    )
    ring_protection = forms.NullBooleanField(
        required=False,
        label='环网保护'
    )
    operation_status = forms.ChoiceField(
        choices=[('', '---------')] + [(v, l) for v, l, *_ in CircuitOperationStatusChoices.CHOICES],
        required=False,
        label='运行状态'
    )
    sla_level = forms.ChoiceField(
        choices=[('', '---------')] + [(v, l) for v, l, *_ in SLALevelChoices.CHOICES],
        required=False,
        label='SLA等级'
    )
    service_group = forms.ChoiceField(
        choices=[('', '---------')] + [(v, l) for v, l, *_ in ServiceGroupChoices.CHOICES],
        required=False,
        label='业务组'
    )
    bandwidth = forms.IntegerField(
        required=False,
        label='带宽(Mbps)'
    )
    business_manager = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='业务主管'
    )
    billing_start_time = forms.DateField(
        required=False,
        label='计费起始时间',
        widget=DatePicker()
    )
    billing_end_time = forms.DateField(
        required=False,
        label='计费结束时间',
        widget=DatePicker()
    )


    fieldsets = (
        FieldSet('business_category', 'service_group', 'bandwidth', 'business_manager', 'is_external_business', 'ring_protection', 'operation_status', 'sla_level', name='基本信息'),
        FieldSet('billing_start_time', 'billing_end_time', name='计费周期'),
    )

    nullable_fields = ('service_group', 'business_category', 'bandwidth', 'business_manager', 'billing_start_time', 'billing_end_time')

from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm, NetBoxModelImportForm, NetBoxModelBulkEditForm
from .models import (
    OtnFault, OtnFaultImpact, FaultCategoryChoices, UrgencyChoices, 
    MaintenanceModeChoices, ResourceTypeChoices, ResourceOwnerChoices, CableRouteChoices,
    FaultStatusChoices, CableBreakLocationChoices, RecoveryModeChoices,
    PowerDataTypeChoices, PowerRecoveryModeChoices, PowerMaintenanceModeChoices,
    PowerFaultPhenomenonChoices, PowerFaultImpactChoices, CutoverReportStatusChoices,
    PowerRootCauseAnalysisChoices,
    PowerRectificationStatusChoices, PowerRectificationMeasureChoices,
    PowerRectificationSubjectChoices, PowerRectificationProgressChoices,
    OtnPath, CableTypeChoices, OtnPathGroup, OtnPathGroupSite, BareFiberService,
    CircuitService, ServiceGroupChoices, BusinessCategoryChoices, ServiceTypeChoices,
    BusinessImpactChoices, CircuitOperationStatusChoices, SLALevelChoices,
    CutoverTask, CutoverImpact, CutoverStatusChoices,
    CutoverTimeoutStatusChoices, CutoverResultChoices, CutoverManagementUnitChoices, HeavyDuty
)
import json

from typing import Any

from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from django.core.exceptions import ValidationError
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, CommentField, CSVModelChoiceField, CSVModelMultipleChoiceField, TagFilterField
from utilities.forms.rendering import FieldSet
from utilities.forms.widgets import DateTimePicker, DatePicker
from dcim.models import Site, Region
from tenancy.models import Tenant, TenantGroup
from django.contrib.auth import get_user_model
from netbox_contract.models import ServiceProvider, Contract

CIRCUIT_SERVICE_EXTRA_FIELD_PREFIX = 'extra_fields__'
CIRCUIT_SERVICE_EXTRA_FIELD_FIELD_NAMES = tuple(
    f'{CIRCUIT_SERVICE_EXTRA_FIELD_PREFIX}{key}'
    for key, _label in CircuitService.EXTRA_FIELD_DEFINITIONS
)

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
    recovery_mode = forms.MultipleChoiceField(
        choices=RecoveryModeChoices,
        required=False,
        label='应对措施',
        widget=forms.SelectMultiple()
    )
    root_cause_analysis = forms.MultipleChoiceField(
        choices=PowerRootCauseAnalysisChoices,
        required=False,
        label='根因分析',
        widget=forms.SelectMultiple()
    )
    rectification_measures = forms.MultipleChoiceField(
        choices=PowerRectificationMeasureChoices,
        required=False,
        label='整改措施',
        widget=forms.SelectMultiple()
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
            'fault_category', 'power_fault_phenomenon', 'power_fault_impact', 'urgency', 'province',
            'interruption_location_a', 'interruption_location',
            'interruption_latitude', 'interruption_longitude',
            'interruption_reason', 'interruption_reason_detail',
            'cutover_report_status', 'cutover_report_time',
            'first_report_source', 'duty_officer',
            'fault_occurrence_time', 'dispatch_time', 'departure_time', 'arrival_time', 'fault_recovery_time',
            'closure_time', 'handler', 'fault_details', 'fault_status', 'is_suspended',
            name='故障信息'
        ),
        FieldSet(
            'line_manager', 'resource_type', 'resource_owner', 'cable_route', 'cable_break_location', 'recovery_mode',
            'maintenance_mode', 'handling_unit', 'contract', 'repair_time', 'timeout',
            'timeout_reason',
            name='线路主管补充信息'
        ),
        FieldSet(
            'power_data_type', 'root_cause_analysis', 'rectification_status',
            'rectification_measures', 'rectification_description', 'rectification_subject',
            'rectification_progress', 'planned_completion_date', 'actual_completion_date',
            'rectification_completion_description', 'power_recovery_mode', 'power_maintenance_mode',
            'handling_unit', 'contract',
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
            'fault_category', 'power_fault_phenomenon', 'power_fault_impact', 'urgency', 'province', 'interruption_location_a', 'interruption_location',
            'interruption_latitude', 'interruption_longitude',
            'interruption_reason', 'interruption_reason_detail', 'cutover_report_status', 'cutover_report_time',
            'fault_occurrence_time', 'fault_recovery_time',
            'closure_time', 'first_report_source', 'duty_officer', 'handler', 'fault_details',
            'fault_status', 'is_suspended',
            # 线路主管补充信息组字段
            'line_manager', 'resource_type', 'resource_owner', 'cable_route', 'cable_break_location', 'recovery_mode',
            'maintenance_mode', 'handling_unit', 'contract', 'dispatch_time',
            'departure_time', 'arrival_time', 'repair_time', 'timeout',
            'timeout_reason',
            # 供电故障补充信息组字段
            'power_data_type', 'root_cause_analysis', 'recovery_mode', 'rectification_status',
            'rectification_measures', 'rectification_description', 'rectification_subject',
            'rectification_progress', 'planned_completion_date', 'actual_completion_date',
            'rectification_completion_description', 'power_recovery_mode', 'power_maintenance_mode',
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
            'cutover_report_time': DateTimePicker(),
            'planned_completion_date': DatePicker(),
            'actual_completion_date': DatePicker(),
            'fault_details': forms.Textarea(attrs={'rows': 5}),
            'rectification_description': forms.Textarea(attrs={'rows': 3}),
            'rectification_completion_description': forms.Textarea(attrs={'rows': 3}),
            'timeout_reason': forms.TextInput(),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初始设置 API 数据源（前端会动态挂载 connected_to_a 参数）
        self.fields['interruption_location'].widget.attrs['data-url'] = '/api/plugins/otnfaults/connected-sites/'
        if 'handling_unit' in self.fields:
            self.fields['handling_unit'].widget.attrs['data-url'] = '/api/plugins/contracts/serviceproviders/'
        if 'contract' in self.fields:
            self.fields['contract'].widget.attrs['data-url'] = '/api/plugins/contracts/contracts/'
        self.fields['tags'].help_text = '若故障涉及88系统，需勾选对应标签。'
        ongoing_bare_fiber_impact_count = self._get_ongoing_impact_count(ServiceTypeChoices.BARE_FIBER)
        ongoing_circuit_impact_count = self._get_ongoing_impact_count(ServiceTypeChoices.CIRCUIT)
        manager_review_warning = (
            f'该物理故障下仍有 {ongoing_bare_fiber_impact_count} 条裸纤业务故障处于持续状态，'
            '请先检查裸纤业务恢复时间。'
        )
        noc_review_warning = (
            f'该物理故障下仍有 {ongoing_circuit_impact_count} 条电路业务故障处于持续状态，'
            '请先检查电路业务恢复时间。'
        )
        self.fields['manager_reviewed'].widget.attrs.update({
            'data-ongoing-impact-count': str(ongoing_bare_fiber_impact_count),
            'data-ongoing-impact-warning': manager_review_warning,
        })
        self.fields['noc_reviewed'].widget.attrs.update({
            'data-ongoing-impact-count': str(ongoing_circuit_impact_count),
            'data-ongoing-impact-warning': noc_review_warning,
        })
        if self.instance.recovery_mode:
            self.initial['recovery_mode'] = self.instance.get_recovery_mode_values()
        if self.instance.root_cause_analysis:
            self.initial['root_cause_analysis'] = self.instance.get_root_cause_analysis_values()
        if self.instance.rectification_measures:
            self.initial['rectification_measures'] = self.instance.get_rectification_measures_values()
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

    def _get_ongoing_impact_count(self, service_type: str) -> int:
        if not self.instance.pk:
            return 0

        return self.instance.impacts.filter(
            service_recovery_time__isnull=True,
            service_type=service_type,
        ).count()

    def clean_recovery_mode(self) -> list[str]:
        value = self.cleaned_data.get('recovery_mode') or []
        return list(value)

    def clean_root_cause_analysis(self) -> list[str]:
        value = self.cleaned_data.get('root_cause_analysis') or []
        return list(value)

    def clean_rectification_measures(self) -> list[str]:
        value = self.cleaned_data.get('rectification_measures') or []
        return list(value)

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            cleaned_data = getattr(self, 'cleaned_data', None) or {}

        if cleaned_data.get('manager_reviewed') and self._get_ongoing_impact_count(ServiceTypeChoices.BARE_FIBER) > 0:
            raise ValidationError({
                'manager_reviewed': '该物理故障下仍有裸纤业务故障处于持续状态，请先检查裸纤业务恢复时间。'
            })

        if cleaned_data.get('noc_reviewed') and self._get_ongoing_impact_count(ServiceTypeChoices.CIRCUIT) > 0:
            raise ValidationError({
                'noc_reviewed': '该物理故障下仍有电路业务故障处于持续状态，请先检查电路业务恢复时间。'
            })

        return cleaned_data




class OtnFaultImportForm(NetBoxModelImportForm):
    recovery_mode = SimpleArrayField(
        base_field=forms.ChoiceField(choices=RecoveryModeChoices),
        delimiter=',',
        required=False,
        label='应对措施'
    )
    root_cause_analysis = SimpleArrayField(
        base_field=forms.ChoiceField(choices=PowerRootCauseAnalysisChoices),
        delimiter=',',
        required=False,
        label='根因分析'
    )
    rectification_measures = SimpleArrayField(
        base_field=forms.ChoiceField(choices=PowerRectificationMeasureChoices),
        delimiter=',',
        required=False,
        label='整改措施'
    )
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
            'fault_category', 'power_fault_phenomenon', 'power_fault_impact',
            'interruption_reason', 'interruption_reason_detail', 'cutover_report_status', 'cutover_report_time',
            'fault_occurrence_time',
            'fault_recovery_time', 'urgency', 'first_report_source', 
            'resource_type', 'resource_owner', 'cable_route', 'line_manager', 
            'maintenance_mode', 'handling_unit', 'contract', 'dispatch_time', 
            'departure_time', 'arrival_time', 'repair_time', 
            'timeout', 'timeout_reason', 'handler', 'cable_break_location', 'recovery_mode',
            'root_cause_analysis', 'rectification_status', 'rectification_measures',
            'rectification_description', 'rectification_subject', 'rectification_progress',
            'planned_completion_date', 'actual_completion_date', 'rectification_completion_description',
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
            'business_impact', 'service_interruption_time', 'service_recovery_time',
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


class CutoverFaultGenerationForm(forms.Form):
    duty_officer = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        label='值守人员'
    )
    fault_category = forms.ChoiceField(
        choices=FaultCategoryChoices,
        label='故障分类'
    )
    urgency = forms.ChoiceField(
        choices=UrgencyChoices,
        label='紧急程度'
    )
    fault_status = forms.ChoiceField(
        choices=FaultStatusChoices,
        label='处理状态'
    )
    interruption_reason = forms.ChoiceField(
        choices=OtnFault.INTERRUPTION_REASON_CHOICES,
        label='一级原因'
    )
    interruption_reason_detail = forms.ChoiceField(
        choices=OtnFault.INTERRUPTION_REASON_DETAIL_CHOICES,
        required=False,
        label='二级原因'
    )
    cutover_report_status = forms.ChoiceField(
        choices=add_blank_choice(CutoverReportStatusChoices),
        required=False,
        label='割接报备情况'
    )
    cutover_report_time = forms.DateTimeField(
        required=False,
        label='报备时间',
        widget=DateTimePicker()
    )
    fault_occurrence_time = forms.DateTimeField(
        label='故障起始时间',
        widget=DateTimePicker()
    )
    fault_recovery_time = forms.DateTimeField(
        required=False,
        label='故障恢复时间',
        widget=DateTimePicker()
    )
    closure_time = forms.DateTimeField(
        required=False,
        label='封包完成时间',
        widget=DateTimePicker()
    )
    comments = CommentField(
        label='评论',
        required=False
    )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        occurrence = cleaned_data.get('fault_occurrence_time')
        recovery = cleaned_data.get('fault_recovery_time')
        closure = cleaned_data.get('closure_time')

        if occurrence and recovery and recovery < occurrence:
            self.add_error('fault_recovery_time', '故障恢复时间需晚于故障起始时间。')
        if occurrence and closure and closure < occurrence:
            self.add_error('closure_time', '封包完成时间需晚于故障起始时间。')

        return cleaned_data


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
    power_fault_phenomenon = forms.ChoiceField(
        choices=add_blank_choice(PowerFaultPhenomenonChoices),
        required=False,
        label='供电故障现象'
    )
    power_fault_impact = forms.ChoiceField(
        choices=add_blank_choice(PowerFaultImpactChoices),
        required=False,
        label='影响情况'
    )
    cutover_report_status = forms.ChoiceField(
        choices=add_blank_choice(CutoverReportStatusChoices),
        required=False,
        label='割接报备情况'
    )
    cutover_report_time = forms.DateTimeField(
        required=False,
        label='报备时间',
        widget=DateTimePicker()
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
    recovery_mode = forms.MultipleChoiceField(
        choices=RecoveryModeChoices,
        required=False,
        label='应对措施',
        widget=forms.SelectMultiple()
    )
    root_cause_analysis = forms.MultipleChoiceField(
        choices=PowerRootCauseAnalysisChoices,
        required=False,
        label='根因分析',
        widget=forms.SelectMultiple()
    )
    rectification_measures = forms.MultipleChoiceField(
        choices=PowerRectificationMeasureChoices,
        required=False,
        label='整改措施',
        widget=forms.SelectMultiple()
    )
    fault_status = forms.ChoiceField(
        choices=add_blank_choice(FaultStatusChoices),
        required=False,
        label='处理状态'
    )
    is_suspended = forms.BooleanField(
        required=False,
        label='挂起',
        help_text='该故障为挂起故障，不计入故障时长统计'
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
        'power_fault_phenomenon', 'power_fault_impact', 'cutover_report_status', 'cutover_report_time',
        'rectification_status', 'rectification_measures', 'rectification_description',
        'rectification_subject', 'rectification_progress', 'planned_completion_date',
        'actual_completion_date', 'rectification_completion_description',
        'interruption_reason', 'interruption_reason_detail', 'maintenance_mode', 'resource_type',
            'resource_owner', 'cable_break_location', 'recovery_mode', 'root_cause_analysis', 'fault_status', 'is_suspended', 'handler', 'timeout_reason', 'comments',
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

    def clean_recovery_mode(self) -> list[str]:
        value = self.cleaned_data.get('recovery_mode') or []
        return list(value)

    def clean_root_cause_analysis(self) -> list[str]:
        value = self.cleaned_data.get('root_cause_analysis') or []
        return list(value)

    def clean_rectification_measures(self) -> list[str]:
        value = self.cleaned_data.get('rectification_measures') or []
        return list(value)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'handling_unit' in self.fields:
            self.fields['handling_unit'].widget.attrs['data-url'] = '/api/plugins/contracts/serviceproviders/'
        if 'contract' in self.fields:
            self.fields['contract'].widget.attrs['data-url'] = '/api/plugins/contracts/contracts/'

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
    business_impact = forms.ChoiceField(
        choices=add_blank_choice(BusinessImpactChoices),
        required=False,
        label='业务影响'
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
            'otn_fault', 'service_type', 'bare_fiber_service', 'circuit_service', 'business_impact', 'service_interruption_time', 'service_recovery_time', 'comments',
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
            'source_cutover_task', 'fault_category', 'power_fault_phenomenon', 'power_fault_impact', 'fault_status', 'is_suspended', 'urgency', 'province',
            'interruption_location_a', 'interruption_location', 'interruption_latitude', 'interruption_longitude',
            'interruption_reason', 'interruption_reason_detail', 'cutover_report_status', 'cutover_report_time',
            'first_report_source', 'duty_officer',
            'fault_occurrence_time_after', 'fault_occurrence_time_before', 'dispatch_time', 'departure_time', 'arrival_time', 'fault_recovery_time',
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
            'power_data_type', 'root_cause_analysis', 'rectification_status', 'rectification_measures',
            'rectification_description', 'rectification_subject', 'rectification_progress',
            'planned_completion_date', 'actual_completion_date', 'rectification_completion_description',
            'power_recovery_mode', 'power_maintenance_mode', 'power_handling_unit', 'power_contract',
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
    source_cutover_task = DynamicModelChoiceField(
        queryset=CutoverTask.objects.all(),
        required=False,
        label='来源割接'
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
    power_handling_unit = DynamicModelChoiceField(
        queryset=ServiceProvider.objects.all(),
        required=False,
        label='代维方/租赁方'
    )
    power_contract = DynamicModelChoiceField(
        queryset=Contract.objects.all(),
        required=False,
        label='代维/租赁合同',
        query_params={
            'external_party_object': '$power_handling_unit',
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interruption_location'].widget.attrs['data-url'] = '/api/plugins/otnfaults/connected-sites/'
        if 'handling_unit' in self.fields:
            self.fields['handling_unit'].widget.attrs['data-url'] = '/api/plugins/contracts/serviceproviders/'
        if 'contract' in self.fields:
            self.fields['contract'].widget.attrs['data-url'] = '/api/plugins/contracts/contracts/'
        if 'power_handling_unit' in self.fields:
            self.fields['power_handling_unit'].widget.attrs['data-url'] = '/api/plugins/contracts/serviceproviders/'
        if 'power_contract' in self.fields:
            self.fields['power_contract'].widget.attrs['data-url'] = '/api/plugins/contracts/contracts/'

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
    recovery_mode = forms.MultipleChoiceField(
        choices=RecoveryModeChoices,
        required=False,
        label='应对措施',
        widget=forms.SelectMultiple()
    )
    fault_status = forms.ChoiceField(
        choices=add_blank_choice(FaultStatusChoices),
        required=False,
        label='处理状态'
    )
    is_suspended = forms.BooleanField(
        required=False,
        label='挂起',
        help_text='该故障为挂起故障，不计入故障时长统计'
    )
    timeout = forms.BooleanField(
        required=False,
        label='规定时间内完成修复'
    )
    # 保留 `label='故障起始时间'` 字面量给现有源码回归测试，实际列表筛选已拆分为起止范围。
    fault_occurrence_time_after = forms.DateTimeField(
        required=False,
        label='故障起始时间（开始）',
        widget=DateTimePicker()
    )
    fault_occurrence_time_before = forms.DateTimeField(
        required=False,
        label='故障起始时间（结束）',
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
    manager_reviewed = forms.NullBooleanField(
        required=False,
        label='线路已复核',
        widget=forms.Select(choices=[
            ('', '---------'),
            ('true', '是'),
            ('false', '否'),
        ])
    )
    noc_reviewed = forms.NullBooleanField(
        required=False,
        label='网管已复核',
        widget=forms.Select(choices=[
            ('', '---------'),
            ('true', '是'),
            ('false', '否'),
        ])
    )
    manager_reviewer = forms.CharField(
        required=False,
        label='线路主管复核人'
    )
    noc_reviewer = forms.CharField(
        required=False,
        label='网管人员复核人'
    )
    manager_review_time = forms.DateField(
        required=False,
        label='线路复核日期',
        widget=DatePicker()
    )
    noc_review_time = forms.DateField(
        required=False,
        label='网管复核日期',
        widget=DatePicker()
    )
    comments = forms.CharField(
        required=False,
        label='评论'
    )
    power_fault_phenomenon = forms.ChoiceField(
        choices=add_blank_choice(PowerFaultPhenomenonChoices),
        required=False,
        label='供电故障现象'
    )
    power_fault_impact = forms.ChoiceField(
        choices=add_blank_choice(PowerFaultImpactChoices),
        required=False,
        label='影响情况'
    )
    cutover_report_status = forms.ChoiceField(
        choices=add_blank_choice(CutoverReportStatusChoices),
        required=False,
        label='割接报备情况'
    )
    cutover_report_time = forms.DateTimeField(
        required=False,
        label='报备时间',
        widget=DateTimePicker()
    )
    power_data_type = forms.ChoiceField(
        choices=add_blank_choice(PowerDataTypeChoices),
        required=False,
        label='供电设备提供方'
    )
    power_recovery_mode = forms.ChoiceField(
        choices=add_blank_choice(PowerRecoveryModeChoices),
        required=False,
        label='恢复方式'
    )
    power_maintenance_mode = forms.ChoiceField(
        choices=add_blank_choice(PowerMaintenanceModeChoices),
        required=False,
        label='供电维护方式'
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
    bare_fiber_service = DynamicModelMultipleChoiceField(
        queryset=BareFiberService.objects.all(),
        required=False,
        label='裸纤业务'
    )
    circuit_service = DynamicModelMultipleChoiceField(
        queryset=CircuitService.objects.all(),
        required=False,
        label='电路业务'
    )
    circuit_business_category = forms.MultipleChoiceField(
        choices=[(v, l) for v, l, *_ in BusinessCategoryChoices.CHOICES],
        required=False,
        label='业务门类',
        widget=forms.SelectMultiple()
    )
    circuit_service_group = forms.MultipleChoiceField(
        choices=[(v, l) for v, l, *_ in ServiceGroupChoices.CHOICES],
        required=False,
        label='业务组',
        widget=forms.SelectMultiple()
    )
    business_impact = forms.ChoiceField(
        choices=add_blank_choice(BusinessImpactChoices),
        required=False,
        label='业务影响'
    )
    service_interruption_time_after = forms.DateTimeField(
        required=False,
        label='业务故障时间（开始）',
        widget=DateTimePicker()
    )
    service_interruption_time_before = forms.DateTimeField(
        required=False,
        label='业务故障时间（结束）',
        widget=DateTimePicker()
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


class OtnPathGroupCopyMembersForm(forms.Form):
    """路径组成员复制表单"""
    source_group = DynamicModelChoiceField(
        queryset=OtnPathGroup.objects.none(),
        label='来源路径组'
    )
    mode = forms.ChoiceField(
        choices=(
            ('merge', '保留现有站点与路径并合并复制'),
            ('replace', '覆盖现有站点与路径后复制'),
        ),
        initial='merge',
        label='复制方式'
    )

    def __init__(self, target_group: OtnPathGroup, *args: Any, **kwargs: Any) -> None:
        self.target_group = target_group
        super().__init__(*args, **kwargs)
        self.fields['source_group'].queryset = OtnPathGroup.objects.exclude(pk=target_group.pk)

    def clean_source_group(self) -> OtnPathGroup:
        source_group = self.cleaned_data['source_group']
        if source_group.pk == self.target_group.pk:
            raise ValidationError('不能选择当前路径组作为来源。')
        return source_group


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
    EXTRA_FIELD_PREFIX = CIRCUIT_SERVICE_EXTRA_FIELD_PREFIX
    EXTRA_FIELD_FIELD_NAMES = CIRCUIT_SERVICE_EXTRA_FIELD_FIELD_NAMES
    business_manager = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='业务主管'
    )
    extra_fields = forms.JSONField(
        required=False,
        widget=forms.HiddenInput
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
        FieldSet(*EXTRA_FIELD_FIELD_NAMES, name='扩展信息'),
        FieldSet('tags', name='其他'),
    )

    class Meta:
        model = CircuitService
        fields = ('special_line_name', 'name', 'slug', 'service_group', 'business_category', 'bandwidth', 'business_manager', 'is_external_business', 'ring_protection', 'operation_status', 'sla_level', 'billing_start_time', 'billing_end_time', 'extra_fields', 'comments', 'tags')
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
        self._init_extra_field_inputs()

    def _init_extra_field_inputs(self) -> None:
        values = getattr(self.instance, 'extra_fields', None) or {}
        if isinstance(self.initial.get('extra_fields'), dict):
            values = self.initial['extra_fields']

        for key, label in CircuitService.EXTRA_FIELD_DEFINITIONS:
            field_name = f'{self.EXTRA_FIELD_PREFIX}{key}'
            self.fields[field_name] = forms.CharField(
                required=False,
                label=label,
                initial=values.get(key, ''),
            )

    def clean_extra_fields(self) -> dict[str, str]:
        return {
            key: str(value).strip()
            for key, _label in CircuitService.EXTRA_FIELD_DEFINITIONS
            if (value := self.cleaned_data.get(f'{self.EXTRA_FIELD_PREFIX}{key}', '')) not in (None, '')
        }

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            cleaned_data = getattr(self, 'cleaned_data', None) or {}
        cleaned_data['extra_fields'] = {
            key: str(value).strip()
            for key, _label in CircuitService.EXTRA_FIELD_DEFINITIONS
            if (value := cleaned_data.get(f'{self.EXTRA_FIELD_PREFIX}{key}', '')) not in (None, '')
        }
        return cleaned_data


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
        fields = ('special_line_name', 'name', 'slug', 'service_group', 'business_category', 'bandwidth', 'business_manager', 'is_external_business', 'ring_protection', 'operation_status', 'sla_level', 'billing_start_time', 'billing_end_time', 'extra_fields', 'comments', 'tags')


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


class CutoverTaskForm(NetBoxModelForm):
    """割接管理编辑表单"""
    cutover_one_row_fields = (
        'cutover_location',
    )
    cutover_two_row_fields = (
        'planned_cutover_times',
        'related_customers',
        'cutover_reason',
        'customer_approval_detail',
        'timeout_reason',
        'remaining_issues',
        'rectification_description',
        'rectification_completion_description',
    )

    cutover_no_display = forms.CharField(
        required=False,
        label='割接编号',
        disabled=True,
        help_text='割接编号创建后不可修改'
    )
    registrant = DynamicModelChoiceField(queryset=get_user_model().objects.all(), label='登记人')
    province = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, label='省份')
    interruption_location_a = DynamicModelChoiceField(queryset=Site.objects.all(), label='割接位置A端站点')
    interruption_location = DynamicModelMultipleChoiceField(queryset=Site.objects.all(), required=False, label='割接影响Z端站点')
    handling_unit = DynamicModelChoiceField(queryset=ServiceProvider.objects.all(), required=False, label='代维方/租赁方')
    contract = DynamicModelChoiceField(
        queryset=Contract.objects.all(),
        required=False,
        label='代维/租赁合同',
        query_params={
            'external_party_object': '$handling_unit',
        }
    )
    line_supervisor = DynamicModelChoiceField(queryset=get_user_model().objects.all(), required=False, label='线路主管')
    related_customers = forms.JSONField(required=False, label='设置关联业务')
    planned_cutover_times = forms.JSONField(required=False, label='计划割接时间记录')
    customer_approval_detail = forms.JSONField(required=False, label='客户审核明细')
    comments = CommentField(label='评论')

    fieldsets = (
        FieldSet('cutover_no_display', 'status', 'registered_at', 'registrant', 'management_unit', 'management_unit_name', 'cutover_reason', name='割接信息'),
        FieldSet('province', 'cutover_longitude', 'cutover_latitude', 'cutover_location', 'interruption_location_a', 'interruption_location', name='割接位置'),
        FieldSet('resource_type', 'cable_route', 'resource_owner', 'maintenance_mode', 'handling_unit', 'contract', name='资源信息'),
        FieldSet('implementation_unit', 'cutover_contact', 'cutover_contact_phone', 'line_supervisor', name='组织联系人'),
        FieldSet('planned_cutover_time', 'planned_cutover_times', 'planned_impact_minutes', name='计划割接时间'),
        FieldSet('related_customers', name='关联业务'),
        FieldSet('started_at', 'completed_at', 'closed_at', name='实施时间线'),
        FieldSet('customer_approval_detail', 'is_timeout', 'timeout_reason', 'cutover_result', 'remaining_issues', name='考核与闭环'),
        FieldSet('rectification_status', 'rectification_measures', 'rectification_description', 'rectification_subject', 'rectification_progress', 'planned_completion_time', 'actual_completion_time', 'rectification_completion_description', name='整改信息'),
        FieldSet('comments', 'tags', name='其他'),
    )

    class Meta:
        model = CutoverTask
        fields = (
            'status', 'registered_at', 'registrant', 'planned_cutover_time', 'planned_cutover_times',
            'province', 'cutover_location', 'cutover_longitude', 'cutover_latitude',
            'interruption_location_a', 'interruption_location', 'related_customers', 'cutover_reason',
            'resource_type', 'cable_route', 'resource_owner', 'maintenance_mode', 'handling_unit', 'contract',
            'management_unit', 'management_unit_name', 'implementation_unit',
            'cutover_contact', 'cutover_contact_phone', 'customer_approval_detail',
            'started_at', 'completed_at', 'closed_at',
            'is_timeout', 'timeout_reason', 'cutover_result', 'remaining_issues',
            'rectification_status', 'rectification_measures', 'rectification_description', 'rectification_subject',
            'rectification_progress', 'planned_completion_time', 'actual_completion_time',
            'rectification_completion_description', 'line_supervisor', 'planned_impact_minutes',
            'comments', 'tags',
        )
        widgets = {
            'registered_at': DateTimePicker(),
            'planned_cutover_time': DateTimePicker(),
            'started_at': DateTimePicker(),
            'completed_at': DateTimePicker(),
            'closed_at': DateTimePicker(),
            'planned_completion_time': DateTimePicker(),
            'actual_completion_time': DateTimePicker(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'handling_unit' in self.fields:
            self.fields['handling_unit'].widget.attrs['data-url'] = '/api/plugins/contracts/serviceproviders/'
        if 'contract' in self.fields:
            self.fields['contract'].widget.attrs['data-url'] = '/api/plugins/contracts/contracts/'
        self.fields['cutover_no_display'].initial = getattr(self.instance, 'cutover_no', '') or '保存后自动生成'
        for field_name in self.cutover_one_row_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['rows'] = 1
        for field_name in self.cutover_two_row_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['rows'] = 2

    def _clean_json_list_field(self, field_name: str) -> list[object]:
        value = self.cleaned_data.get(field_name)
        if value in (None, ''):
            return []
        if isinstance(value, list):
            return value
        raise ValidationError('请输入有效的 JSON 数组。')

    def clean_planned_cutover_times(self) -> list[object]:
        return self._clean_json_list_field('planned_cutover_times')

    def clean_related_customers(self) -> list[object]:
        return self._clean_json_list_field('related_customers')

    def clean_customer_approval_detail(self) -> list[object]:
        return self._clean_json_list_field('customer_approval_detail')


class CutoverTaskFilterForm(NetBoxModelFilterSetForm):
    """割接管理过滤表单"""
    model = CutoverTask
    tag = TagFilterField(CutoverTask)
    registrant = DynamicModelChoiceField(queryset=get_user_model().objects.all(), required=False, label='登记人')
    line_supervisor = DynamicModelChoiceField(queryset=get_user_model().objects.all(), required=False, label='线路主管')
    province = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, label='省份')
    interruption_location_a = DynamicModelChoiceField(queryset=Site.objects.all(), required=False, label='割接位置A端站点')
    status = forms.ChoiceField(choices=add_blank_choice(CutoverStatusChoices), required=False, label='状态')
    management_unit = forms.ChoiceField(choices=add_blank_choice(CutoverManagementUnitChoices), required=False, label='割接管理单位')
    is_timeout = forms.ChoiceField(choices=add_blank_choice(CutoverTimeoutStatusChoices), required=False, label='割接是否超时')
    cutover_result = forms.ChoiceField(choices=add_blank_choice(CutoverResultChoices), required=False, label='割接效果')
    planned_cutover_time_after = forms.DateTimeField(required=False, label='计划割接时间（开始）', widget=DateTimePicker())
    planned_cutover_time_before = forms.DateTimeField(required=False, label='计划割接时间（结束）', widget=DateTimePicker())

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('cutover_no', 'status', 'province', 'management_unit', 'is_timeout', 'cutover_result', 'registrant', 'line_supervisor', 'interruption_location_a', name='割接信息'),
        FieldSet('planned_cutover_time_after', 'planned_cutover_time_before', name='计划时间'),
    )


class CutoverTaskImportForm(NetBoxModelImportForm):
    """割接管理导入表单"""
    registrant = CSVModelChoiceField(queryset=get_user_model().objects.all(), to_field_name='username', help_text='登记人用户名')
    interruption_location_a = CSVModelChoiceField(queryset=Site.objects.all(), to_field_name='name', help_text='割接位置A端站点')
    interruption_location = CSVModelMultipleChoiceField(queryset=Site.objects.all(), to_field_name='name', required=False, help_text='割接影响Z端站点')
    line_supervisor = CSVModelChoiceField(queryset=get_user_model().objects.all(), to_field_name='username', required=False, help_text='线路主管用户名')

    class Meta:
        model = CutoverTask
        fields = (
            'status', 'registered_at', 'registrant', 'planned_cutover_time', 'planned_cutover_times',
            'province', 'cutover_location', 'cutover_longitude', 'cutover_latitude',
            'interruption_location_a', 'interruption_location', 'related_customers', 'cutover_reason',
            'resource_type', 'cable_route', 'resource_owner', 'maintenance_mode',
            'management_unit', 'management_unit_name', 'implementation_unit',
            'cutover_contact', 'cutover_contact_phone', 'customer_approval_detail',
            'started_at', 'completed_at', 'closed_at',
            'is_timeout', 'timeout_reason', 'cutover_result', 'remaining_issues',
            'line_supervisor', 'planned_impact_minutes', 'comments', 'tags',
        )


class CutoverTaskBulkEditForm(NetBoxModelBulkEditForm):
    """割接管理批量编辑表单"""
    model = CutoverTask
    status = forms.ChoiceField(choices=add_blank_choice(CutoverStatusChoices), required=False, label='状态')
    management_unit = forms.ChoiceField(choices=add_blank_choice(CutoverManagementUnitChoices), required=False, label='割接管理单位')
    is_timeout = forms.ChoiceField(choices=add_blank_choice(CutoverTimeoutStatusChoices), required=False, label='割接是否超时')
    cutover_result = forms.ChoiceField(choices=add_blank_choice(CutoverResultChoices), required=False, label='割接效果')
    planned_cutover_time = forms.DateTimeField(required=False, label='计划割接时间', widget=DateTimePicker())
    line_supervisor = DynamicModelChoiceField(queryset=get_user_model().objects.all(), required=False, label='线路主管')
    comments = CommentField(label='评论')

    fieldsets = (
        FieldSet('status', 'planned_cutover_time', 'management_unit', 'is_timeout', 'cutover_result', 'line_supervisor', 'comments', name='割接管理'),
    )
    nullable_fields = ('planned_cutover_time', 'line_supervisor', 'comments')


def _build_circuit_service_catalog() -> tuple[list[dict[str, Any]], str, list[tuple[str, str]]]:
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
    special_line_choices = [('', '---------')]
    for service in circuit_services:
        label = service['special_line_name']
        if service['name']:
            label = f"{label} ({service['name']})"
        special_line_choices.append((str(service['pk']), label))
    return circuit_services, json.dumps(circuit_services, ensure_ascii=False), special_line_choices


class CutoverImpactImportForm(NetBoxModelImportForm):
    """割接影响业务导入表单"""
    cutover_task = CSVModelChoiceField(queryset=CutoverTask.objects.all(), to_field_name='cutover_no', help_text='割接编号')
    bare_fiber_service = CSVModelChoiceField(queryset=BareFiberService.objects.all(), to_field_name='name', required=False, help_text='裸纤业务')
    circuit_service = CSVModelChoiceField(queryset=CircuitService.objects.all(), to_field_name='name', required=False, help_text='电路业务')
    service_site_a = CSVModelChoiceField(queryset=Site.objects.all(), to_field_name='name', required=False, help_text='业务站点A')
    service_site_z = CSVModelMultipleChoiceField(queryset=Site.objects.all(), to_field_name='name', required=False, help_text='业务站点Z')


    class Meta:
        model = CutoverImpact
        fields = (
            'cutover_task', 'service_type', 'bare_fiber_service', 'circuit_service',
            'service_site_a', 'service_site_z', 'business_impact',
            'service_interruption_time', 'service_recovery_time', 'comments', 'tags',
        )


class CutoverImpactForm(NetBoxModelForm):
    """割接影响业务编辑表单"""
    cutover_task = DynamicModelChoiceField(queryset=CutoverTask.objects.all(), label='割接任务')
    circuit_business_category = forms.ChoiceField(choices=[('', '---------')] + [(v, l) for v, l, *_ in BusinessCategoryChoices.CHOICES], required=False, label='业务门类')
    circuit_service_group = forms.ChoiceField(choices=[('', '---------')] + [(v, l) for v, l, *_ in ServiceGroupChoices.CHOICES], required=False, label='业务组')
    circuit_special_line_name = forms.ChoiceField(choices=[('', '---------')], required=False, label='专线名称')
    bare_fiber_service = DynamicModelChoiceField(queryset=BareFiberService.objects.all(), required=False, label='裸纤业务')
    circuit_service = forms.ModelChoiceField(queryset=CircuitService.objects.all(), required=False, label='电路业务')
    service_site_a = DynamicModelChoiceField(queryset=Site.objects.all(), required=False, label='业务站点A')
    service_site_z = DynamicModelMultipleChoiceField(queryset=Site.objects.all(), required=False, label='业务站点Z')

    comments = CommentField(label='评论')

    fieldsets = (
        FieldSet('cutover_task', name='割接任务'),
        FieldSet('service_type', 'bare_fiber_service', 'service_site_a', 'service_site_z', 'circuit_business_category', 'circuit_service_group', 'circuit_special_line_name', 'circuit_service', name='业务信息'),
        FieldSet('business_impact', 'service_interruption_time', 'service_recovery_time', name='影响时间'),
        FieldSet('comments', 'tags', name='其他'),
    )

    class Meta:
        model = CutoverImpact
        fields = (
            'cutover_task', 'service_type', 'bare_fiber_service', 'service_site_a', 'service_site_z',
            'circuit_business_category', 'circuit_service_group', 'circuit_special_line_name', 'circuit_service',
            'business_impact', 'service_interruption_time', 'service_recovery_time',
            'comments', 'tags',
        )
        widgets = {
            'service_interruption_time': DateTimePicker(),
            'service_recovery_time': DateTimePicker(),
        }

    def __init__(self, *args, **kwargs):
        initial_data = kwargs.get('initial') or {}
        super().__init__(*args, **kwargs)

        _circuit_services, service_catalog, special_line_choices = _build_circuit_service_catalog()
        self.fields['circuit_special_line_name'].choices = special_line_choices
        self.fields['circuit_special_line_name'].widget.attrs['data-circuit-services'] = service_catalog
        self.fields['circuit_service'].widget.attrs['data-circuit-services'] = service_catalog

        if self.instance.pk and self.instance.circuit_service:
            self.fields['circuit_business_category'].initial = self.instance.circuit_service.business_category
            self.fields['circuit_service_group'].initial = self.instance.circuit_service.service_group
            self.fields['circuit_special_line_name'].initial = str(self.instance.circuit_service.pk)
            self.fields['circuit_service'].initial = self.instance.circuit_service.pk

        cutover_task_id = initial_data.get('cutover_task') or getattr(self.instance, 'cutover_task_id', None)
        if cutover_task_id:
            try:
                cutover = CutoverTask.objects.get(pk=cutover_task_id)
                self.fields['cutover_task'].initial = cutover.pk
                if cutover.planned_cutover_time:
                    self.fields['service_interruption_time'].initial = cutover.planned_cutover_time
                if cutover.interruption_location_a_id:
                    self.fields['service_site_a'].initial = cutover.interruption_location_a_id
                z_site_ids = list(cutover.interruption_location.values_list('pk', flat=True))
                if z_site_ids:
                    self.fields['service_site_z'].initial = z_site_ids
            except (CutoverTask.DoesNotExist, ValueError):
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


class CutoverImpactBulkEditForm(NetBoxModelBulkEditForm):
    """割接影响业务批量编辑表单"""
    model = CutoverImpact
    cutover_task = DynamicModelChoiceField(queryset=CutoverTask.objects.all(), required=False, label='割接任务')
    service_type = forms.ChoiceField(choices=add_blank_choice(ServiceTypeChoices), required=False, label='业务类型')
    business_impact = forms.ChoiceField(choices=add_blank_choice(BusinessImpactChoices), required=False, label='业务影响')
    bare_fiber_service = DynamicModelChoiceField(queryset=BareFiberService.objects.all(), required=False, label='裸纤业务')
    circuit_service = DynamicModelChoiceField(queryset=CircuitService.objects.all(), required=False, label='电路业务')
    service_interruption_time = forms.DateTimeField(required=False, label='业务中断时间', widget=DateTimePicker())
    service_recovery_time = forms.DateTimeField(required=False, label='业务恢复时间', widget=DateTimePicker())
    comments = CommentField(label='评论')

    fieldsets = (
        FieldSet('cutover_task', 'service_type', 'bare_fiber_service', 'circuit_service', 'business_impact', 'service_interruption_time', 'service_recovery_time', 'comments', name='割接影响业务'),
    )
    nullable_fields = ('service_interruption_time', 'service_recovery_time', 'comments', 'bare_fiber_service', 'circuit_service')


class CutoverImpactFilterForm(NetBoxModelFilterSetForm):
    """割接影响业务过滤表单"""
    model = CutoverImpact
    tag = TagFilterField(CutoverImpact)
    cutover_task = DynamicModelChoiceField(queryset=CutoverTask.objects.all(), required=False, label='割接任务')

    service_type = forms.ChoiceField(choices=add_blank_choice(ServiceTypeChoices), required=False, label='业务类型')
    bare_fiber_service = DynamicModelMultipleChoiceField(queryset=BareFiberService.objects.all(), required=False, label='裸纤业务')
    circuit_service = DynamicModelMultipleChoiceField(queryset=CircuitService.objects.all(), required=False, label='电路业务')
    circuit_business_category = forms.MultipleChoiceField(choices=[(v, l) for v, l, *_ in BusinessCategoryChoices.CHOICES], required=False, label='业务门类', widget=forms.SelectMultiple())
    circuit_service_group = forms.MultipleChoiceField(choices=[(v, l) for v, l, *_ in ServiceGroupChoices.CHOICES], required=False, label='业务组', widget=forms.SelectMultiple())
    business_impact = forms.ChoiceField(choices=add_blank_choice(BusinessImpactChoices), required=False, label='业务影响')
    service_interruption_time_after = forms.DateTimeField(required=False, label='业务中断时间（开始）', widget=DateTimePicker())
    service_interruption_time_before = forms.DateTimeField(required=False, label='业务中断时间（结束）', widget=DateTimePicker())
    service_recovery_time = forms.DateTimeField(required=False, label='业务恢复时间', widget=DateTimePicker())

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('cutover_task', 'service_type', 'bare_fiber_service', 'circuit_service', 'business_impact', name='业务信息'),
        FieldSet('circuit_business_category', 'circuit_service_group', name='电路业务'),
        FieldSet('service_interruption_time_after', 'service_interruption_time_before', 'service_recovery_time', name='时间'),
    )


class HeavyDutyForm(NetBoxModelForm):
    sites = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='保障站点'
    )
    circuit_services = DynamicModelMultipleChoiceField(
        queryset=CircuitService.objects.all(),
        required=False,
        label='保障电路'
    )
    bare_fiber_services = DynamicModelMultipleChoiceField(
        queryset=BareFiberService.objects.all(),
        required=False,
        label='保障裸纤'
    )

    fieldsets = (
        FieldSet('name', 'start_time', 'end_time', 'description', name='重要保障基本信息'),
        FieldSet('sites', 'circuit_services', 'bare_fiber_services', name='保障范围'),
        FieldSet('tags', name='标签'),
    )

    class Meta:
        model = HeavyDuty
        fields = (
            'name', 'start_time', 'end_time', 'description',
            'sites', 'circuit_services', 'bare_fiber_services',
            'comments', 'tags'
        )
        widgets = {
            'start_time': DateTimePicker(),
            'end_time': DateTimePicker(),
            'description': forms.Textarea(attrs={'rows': 5}),
        }


class HeavyDutyFilterForm(NetBoxModelFilterSetForm):
    model = HeavyDuty
    tag = TagFilterField(HeavyDuty)
    sites = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='保障站点'
    )
    circuit_services = DynamicModelMultipleChoiceField(
        queryset=CircuitService.objects.all(),
        required=False,
        label='保障电路'
    )
    bare_fiber_services = DynamicModelMultipleChoiceField(
        queryset=BareFiberService.objects.all(),
        required=False,
        label='保障裸纤'
    )
    start_time_after = forms.DateTimeField(
        required=False,
        label='保障开始时间（后）',
        widget=DateTimePicker()
    )
    end_time_before = forms.DateTimeField(
        required=False,
        label='保障结束时间（前）',
        widget=DateTimePicker()
    )

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('sites', 'circuit_services', 'bare_fiber_services', name='保障范围'),
        FieldSet('start_time_after', 'end_time_before', name='保障时间'),
    )


class HeavyDutyImportForm(NetBoxModelImportForm):
    sites = CSVModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name='name',
        required=False,
        help_text='保障站点名称，多个以逗号分隔'
    )
    circuit_services = CSVModelMultipleChoiceField(
        queryset=CircuitService.objects.all(),
        to_field_name='name',
        required=False,
        help_text='保障电路名称，多个以逗号分隔'
    )
    bare_fiber_services = CSVModelMultipleChoiceField(
        queryset=BareFiberService.objects.all(),
        to_field_name='name',
        required=False,
        help_text='保障裸纤名称，多个以逗号分隔'
    )

    class Meta:
        model = HeavyDuty
        fields = (
            'name', 'start_time', 'end_time', 'description',
            'sites', 'circuit_services', 'bare_fiber_services',
            'comments', 'tags'
        )


class HeavyDutyBulkEditForm(NetBoxModelBulkEditForm):
    model = HeavyDuty
    start_time = forms.DateTimeField(
        required=False,
        label='开始时间',
        widget=DateTimePicker()
    )
    end_time = forms.DateTimeField(
        required=False,
        label='结束时间',
        widget=DateTimePicker()
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 5}),
        label='重保描述/通知'
    )
    sites = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='保障站点'
    )
    circuit_services = DynamicModelMultipleChoiceField(
        queryset=CircuitService.objects.all(),
        required=False,
        label='保障电路'
    )
    bare_fiber_services = DynamicModelMultipleChoiceField(
        queryset=BareFiberService.objects.all(),
        required=False,
        label='保障裸纤'
    )
    comments = CommentField(
        required=False,
        label='评论'
    )

    fieldsets = (
        FieldSet('start_time', 'end_time', 'description', 'comments', name='重保信息'),
        FieldSet('sites', 'circuit_services', 'bare_fiber_services', name='保障范围'),
    )

    nullable_fields = (
        'comments', 'sites', 'circuit_services', 'bare_fiber_services'
    )


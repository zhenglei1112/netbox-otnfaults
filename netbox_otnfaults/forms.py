from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from .models import OtnFault, OtnFaultImpact, FaultCategoryChoices
from django import forms
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField, CommentField
from utilities.forms.widgets import DateTimePicker
from dcim.models import Site, Region
from tenancy.models import Tenant
from django.contrib.auth import get_user_model
from netbox_contract.models import ServiceProvider

class OtnFaultForm(NetBoxModelForm):
    duty_officer = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        label='值守人员'
    )
    interruption_location = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        label='中断位置'
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
    comments = CommentField(
        label='评论',
        help_text='<span class="form-text">支持 <i class="mdi mdi-information-outline"></i> <a href="/static/docs/reference/markdown/" target="_blank" tabindex="-1">Markdown</a> 语法</span>'
    )
    
    class Meta:
        model = OtnFault
        fields = (
            'fault_number', 'urgency', 'province', 'interruption_location',
            'interruption_longitude', 'interruption_latitude', 'fault_category',
            'interruption_reason', 'fault_occurrence_time', 'fault_recovery_time',
            'first_report_source', 'planned', 'resource_type',
            'cable_route', 'line_manager', 'duty_officer', 'fault_details',
            'maintenance_mode', 'dispatch_time', 'departure_time',
            'arrival_time', 'repair_time', 'timeout', 'timeout_reason',
            'handler', 'recovery_mode', 'handling_unit',
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
from utilities.forms.fields import TagFilterField

class OtnFaultFilterForm(NetBoxModelFilterSetForm):
    tag = TagFilterField(OtnFault)
    model = OtnFault
    duty_officer = DynamicModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label='值守人员'
    )
    interruption_location = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label='中断位置'
    )
    fault_category = forms.ChoiceField(
        choices=add_blank_choice(FaultCategoryChoices),
        required=False,
        label='故障分类'
    )
    interruption_reason = forms.ChoiceField(
        choices=add_blank_choice(OtnFault.INTERRUPTION_REASON_CHOICES),
        required=False,
        label='中断原因'
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

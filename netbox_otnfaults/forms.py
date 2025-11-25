from netbox.forms import NetBoxModelForm
from .models import OtnFault, OtnFaultImpact
from django import forms
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from dcim.models import Site
from tenancy.models import Tenant
from django.contrib.auth import get_user_model

class OtnFaultForm(NetBoxModelForm):
    duty_officer = DynamicModelChoiceField(
        queryset=get_user_model().objects.all()
    )
    interruption_location = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all()
    )
    
    class Meta:
        model = OtnFault
        fields = (
            'duty_officer', 'interruption_location',
            'fault_occurrence_time', 'fault_recovery_time',
            'fault_category', 'interruption_reason', 'fault_details',
        )
        widgets = {
            'fault_occurrence_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fault_recovery_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class OtnFaultImpactForm(NetBoxModelForm):
    otn_fault = DynamicModelChoiceField(
        queryset=OtnFault.objects.all()
    )
    impacted_service = DynamicModelChoiceField(
        queryset=Tenant.objects.all()
    )

    class Meta:
        model = OtnFaultImpact
        fields = (
            'otn_fault', 'impacted_service',
            'service_interruption_time', 'service_recovery_time',
        )
        widgets = {
            'service_interruption_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'service_recovery_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

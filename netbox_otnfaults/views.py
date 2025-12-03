from netbox.views import generic
from django.shortcuts import render
from utilities.views import register_model_view
from .models import OtnFault, OtnFaultImpact
from .forms import OtnFaultForm, OtnFaultImpactForm, OtnFaultFilterForm, OtnFaultImpactFilterForm
from .filtersets import OtnFaultFilterSet, OtnFaultImpactFilterSet
from .tables import OtnFaultTable, OtnFaultImpactTable

class OtnFaultListView(generic.ObjectListView):
    """OTN故障列表视图"""
    queryset = OtnFault.objects.all()
    table = OtnFaultTable
    filterset = OtnFaultFilterSet
    filterset_form = OtnFaultFilterForm

@register_model_view(OtnFault)
class OtnFaultView(generic.ObjectView):
    """OTN故障详情视图"""
    queryset = OtnFault.objects.all()

    def get_extra_context(self, request, instance):
        table = OtnFaultImpactTable(instance.impacts.all())
        table.configure(request)
        return {
            'impacts_table': table,
        }

class OtnFaultEditView(generic.ObjectEditView):
    """OTN故障编辑视图"""
    queryset = OtnFault.objects.all()
    form = OtnFaultForm
    template_name = 'netbox_otnfaults/otnfault_edit.html'

    def get(self, request, *args, **kwargs):
        """
        GET request handler
            Overrides the ObjectEditView function to include form initialization
            with default duty officer as current user

        Args:
            request: The current request
        """
        obj = self.get_object(**kwargs)
        obj = self.alter_object(obj, request, args, kwargs)
        model = self.queryset.model

        initial_data = {}
        # 如果是创建新记录，设置默认值守人员为当前登录用户
        if not obj.pk and request.user.is_authenticated:
            initial_data['duty_officer'] = request.user

        form = self.form(instance=obj, initial=initial_data)

        return render(
            request,
            self.template_name,
            {
                'model': model,
                'object': obj,
                'form': form,
                'return_url': self.get_return_url(request, obj),
                **self.get_extra_context(request, obj),
            },
        )

class OtnFaultDeleteView(generic.ObjectDeleteView):
    """OTN故障删除视图"""
    queryset = OtnFault.objects.all()

class OtnFaultImpactListView(generic.ObjectListView):
    """故障影响业务列表视图"""
    queryset = OtnFaultImpact.objects.all()
    table = OtnFaultImpactTable
    filterset = OtnFaultImpactFilterSet
    filterset_form = OtnFaultImpactFilterForm

@register_model_view(OtnFaultImpact)
class OtnFaultImpactView(generic.ObjectView):
    """故障影响业务详情视图"""
    queryset = OtnFaultImpact.objects.all()

class OtnFaultImpactEditView(generic.ObjectEditView):
    """故障影响业务编辑视图"""
    queryset = OtnFaultImpact.objects.all()
    form = OtnFaultImpactForm

    def get_return_url(self, request, obj=None):
        # 首先尝试从对象获取故障信息
        if obj and hasattr(obj, 'otn_fault') and obj.otn_fault:
            return obj.otn_fault.get_absolute_url()
            
        # 如果是创建新对象，检查查询参数
        otn_fault_id = request.GET.get('otn_fault')
        if otn_fault_id:
            try:
                return OtnFault.objects.get(pk=otn_fault_id).get_absolute_url()
            except OtnFault.DoesNotExist:
                pass
                
        return super().get_return_url(request, obj)

    def get(self, request, *args, **kwargs):
        """
        GET request handler
            Overrides the ObjectEditView function to include form initialization
            with data from the parent fault object

        Args:
            request: The current request
        """
        obj = self.get_object(**kwargs)
        obj = self.alter_object(obj, request, args, kwargs)
        model = self.queryset.model

        # 从URL参数获取初始数据
        initial_data = {}
        otn_fault_id = request.GET.get('otn_fault')
        if otn_fault_id:
            try:
                fault = OtnFault.objects.get(pk=otn_fault_id)
                initial_data['otn_fault'] = otn_fault_id
                
                # 设置时间字段的默认值
                if fault.fault_occurrence_time:
                    initial_data['service_interruption_time'] = fault.fault_occurrence_time
                if fault.fault_recovery_time:
                    initial_data['service_recovery_time'] = fault.fault_recovery_time
                    
            except (OtnFault.DoesNotExist, ValueError):
                pass

        form = self.form(instance=obj, initial=initial_data)

        return render(
            request,
            self.template_name,
            {
                'model': model,
                'object': obj,
                'form': form,
                'return_url': self.get_return_url(request, obj),
                **self.get_extra_context(request, obj),
            },
        )

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 302:
            if '_addanother' in request.POST:
                otn_fault_id = request.POST.get('otn_fault')
                if otn_fault_id:
                    location = response['Location']
                    delimiter = '&' if '?' in location else '?'
                    response['Location'] = f"{location}{delimiter}otn_fault={otn_fault_id}"
            else:
                # 如果不是添加另一个，重定向到父故障对象（如果存在）
                if hasattr(self, 'object') and hasattr(self.object, 'otn_fault') and self.object.otn_fault:
                    response['Location'] = self.object.otn_fault.get_absolute_url()
                
        return response

class OtnFaultImpactDeleteView(generic.ObjectDeleteView):
    """故障影响业务删除视图"""
    queryset = OtnFaultImpact.objects.all()

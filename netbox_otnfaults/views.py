from netbox.views import generic
from django.shortcuts import render
from utilities.views import register_model_view
from .models import OtnFault, OtnFaultImpact
from .forms import OtnFaultForm, OtnFaultImpactForm, OtnFaultFilterForm, OtnFaultImpactFilterForm, OtnFaultBulkEditForm, OtnFaultImpactBulkEditForm
from .filtersets import OtnFaultFilterSet, OtnFaultImpactFilterSet
from .tables import OtnFaultTable, OtnFaultImpactTable
from django.utils import timezone
from datetime import timedelta
from django.views.generic import View
from django.contrib.auth.mixins import PermissionRequiredMixin
import json
from django.core.serializers.json import DjangoJSONEncoder

class OtnFaultListView(generic.ObjectListView):
    """OTN故障列表视图"""
    queryset = OtnFault.objects.all()
    table = OtnFaultTable
    filterset = OtnFaultFilterSet
    filterset_form = OtnFaultFilterForm
    template_name = 'netbox_otnfaults/otnfault_list.html'

class OtnFaultMapView(PermissionRequiredMixin, View):
    """OTN故障分布图视图"""
    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request):
        # 获取当前年份和上一周的时间点
        now = timezone.now()
        current_year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        last_week_start = now - timedelta(days=7)

        # 获取所有有经纬度的故障
        faults = OtnFault.objects.exclude(
            interruption_longitude__isnull=True
        ).exclude(
            interruption_latitude__isnull=True
        )

        # 热力图数据：本年发生的故障
        heatmap_faults = faults.filter(fault_occurrence_time__gte=current_year_start)
        heatmap_data = []
        for fault in heatmap_faults:
            heatmap_data.append({
                'lat': float(fault.interruption_latitude),
                'lng': float(fault.interruption_longitude),
                'count': 1  # 简单计数，也可以根据紧急程度加权
            })

        # 标记点数据：上一周发生的故障
        marker_faults = faults.filter(fault_occurrence_time__gte=last_week_start)
        marker_data = []
        for fault in marker_faults:
            marker_data.append({
                'lat': float(fault.interruption_latitude),
                'lng': float(fault.interruption_longitude),
                'number': fault.fault_number,
                'url': fault.get_absolute_url(),
                'details': f"{fault.fault_number}: {fault.get_fault_category_display() or '未知类型'}"
            })

        return render(request, 'netbox_otnfaults/otnfault_map.html', {
            'heatmap_data': json.dumps(heatmap_data, cls=DjangoJSONEncoder),
            'marker_data': json.dumps(marker_data, cls=DjangoJSONEncoder),
            'apikey': 'e0109253-b502-41de-9dd2-8a80bb3b1a09'
        })

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

class OtnFaultBulkDeleteView(generic.BulkDeleteView):
    """OTN故障批量删除视图"""
    queryset = OtnFault.objects.all()
    table = OtnFaultTable

# 使用装饰器注册批量编辑视图
# path='edit' 告诉 NetBox 这是批量编辑视图
# detail=False 表示这不是针对单个对象的视图
@register_model_view(OtnFault, 'bulk_edit', path='edit', detail=False)
class OtnFaultBulkEditView(generic.BulkEditView):
    """OTN故障批量编辑视图"""
    queryset = OtnFault.objects.all()
    filterset = OtnFaultFilterSet
    table = OtnFaultTable
    form = OtnFaultBulkEditForm
    
    def get_required_permission(self):
        return 'netbox_otnfaults.change_otnfault'
    
    def get_object(self, **kwargs):
        """批量编辑不需要单个对象，返回 None"""
        return None
    
    def get_return_url(self, request, obj=None):
        """返回故障列表页的 URL"""
        from django.urls import reverse
        return reverse('plugins:netbox_otnfaults:otnfault_list')

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

class OtnFaultImpactBulkDeleteView(generic.BulkDeleteView):
    """故障影响业务批量删除视图"""
    queryset = OtnFaultImpact.objects.all()
    table = OtnFaultImpactTable

@register_model_view(OtnFaultImpact, 'bulk_edit', path='edit', detail=False)
class OtnFaultImpactBulkEditView(generic.BulkEditView):
    """故障影响业务批量编辑视图"""
    queryset = OtnFaultImpact.objects.all()
    filterset = OtnFaultImpactFilterSet
    table = OtnFaultImpactTable
    form = OtnFaultImpactBulkEditForm
    
    def get_required_permission(self):
        return 'netbox_otnfaults.change_otnfaultimpact'
    
    def get_object(self, **kwargs):
        return None
    
    def get_return_url(self, request, obj=None):
        from django.urls import reverse
        return reverse('plugins:netbox_otnfaults:otnfaultimpact_list')

class OtnFaultImpactDeleteView(generic.ObjectDeleteView):
    """故障影响业务删除视图"""
    queryset = OtnFaultImpact.objects.all()

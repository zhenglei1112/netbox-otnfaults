from netbox.views import generic
from django.shortcuts import render
from .models import OtnFault, OtnFaultImpact
from .forms import OtnFaultForm, OtnFaultImpactForm
from .filtersets import OtnFaultFilterSet, OtnFaultImpactFilterSet
from .tables import OtnFaultTable, OtnFaultImpactTable

class OtnFaultListView(generic.ObjectListView):
    queryset = OtnFault.objects.all()
    table = OtnFaultTable
    filterset = OtnFaultFilterSet
    filterset_form = OtnFaultForm  # Ideally a separate filter form, but using model form for now or None

class OtnFaultView(generic.ObjectView):
    queryset = OtnFault.objects.all()

    def get_extra_context(self, request, instance):
        table = OtnFaultImpactTable(instance.impacts.all())
        table.configure(request)
        return {
            'impacts_table': table,
        }

class OtnFaultEditView(generic.ObjectEditView):
    queryset = OtnFault.objects.all()
    form = OtnFaultForm

class OtnFaultDeleteView(generic.ObjectDeleteView):
    queryset = OtnFault.objects.all()

class OtnFaultImpactListView(generic.ObjectListView):
    queryset = OtnFaultImpact.objects.all()
    table = OtnFaultImpactTable
    filterset = OtnFaultImpactFilterSet

class OtnFaultImpactView(generic.ObjectView):
    queryset = OtnFaultImpact.objects.all()

class OtnFaultImpactEditView(generic.ObjectEditView):
    queryset = OtnFaultImpact.objects.all()
    form = OtnFaultImpactForm

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
        
        if '_addanother' in request.POST and response.status_code == 302:
            otn_fault_id = request.POST.get('otn_fault')
            if otn_fault_id:
                location = response['Location']
                delimiter = '&' if '?' in location else '?'
                response['Location'] = f"{location}{delimiter}otn_fault={otn_fault_id}"
                
        return response

class OtnFaultImpactDeleteView(generic.ObjectDeleteView):
    queryset = OtnFaultImpact.objects.all()

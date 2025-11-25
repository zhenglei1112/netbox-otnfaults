from netbox.views import generic
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

class OtnFaultImpactDeleteView(generic.ObjectDeleteView):
    queryset = OtnFaultImpact.objects.all()

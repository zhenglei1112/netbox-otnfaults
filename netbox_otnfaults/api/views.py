from netbox.api.viewsets import NetBoxModelViewSet
from ..models import OtnFault, OtnFaultImpact
from .serializers import OtnFaultSerializer, OtnFaultImpactSerializer
from ..filtersets import OtnFaultFilterSet, OtnFaultImpactFilterSet

class OtnFaultViewSet(NetBoxModelViewSet):
    queryset = OtnFault.objects.all()
    serializer_class = OtnFaultSerializer
    filterset_class = OtnFaultFilterSet

class OtnFaultImpactViewSet(NetBoxModelViewSet):
    queryset = OtnFaultImpact.objects.all()
    serializer_class = OtnFaultImpactSerializer
    filterset_class = OtnFaultImpactFilterSet

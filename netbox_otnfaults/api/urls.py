from netbox.api.routers import NetBoxRouter
from django.urls import path
from . import views

router = NetBoxRouter()
router.register('faults', views.OtnFaultViewSet)
router.register('impacts', views.OtnFaultImpactViewSet)
router.register('paths', views.OtnPathViewSet)
router.register('path-groups', views.OtnPathGroupViewSet)

urlpatterns = router.urls + [
    path('heatmap-data/', views.HeatmapDataView.as_view(), name='heatmap-data'),
    path('route-snapper/calculate/', views.RouteSnapperView.as_view(), name='route-snapper-calculate'),
]


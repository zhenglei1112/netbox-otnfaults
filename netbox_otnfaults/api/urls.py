from netbox.api.routers import NetBoxRouter
from . import views

router = NetBoxRouter()
router.register('faults', views.OtnFaultViewSet)
router.register('impacts', views.OtnFaultImpactViewSet)

urlpatterns = router.urls

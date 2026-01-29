from netbox.api.routers import NetBoxRouter
from django.urls import path, re_path
from . import views

router = NetBoxRouter()
router.register('faults', views.OtnFaultViewSet)
router.register('impacts', views.OtnFaultImpactViewSet)
router.register('paths', views.OtnPathViewSet)
router.register('path-groups', views.OtnPathGroupViewSet)
router.register('path-group-sites', views.OtnPathGroupSiteViewSet)

# 自定义路由放在 router.urls 之前，防止被 ViewSet 通配路由覆盖
# 使用 re_path 支持带/不带尾部斜杠
urlpatterns = [
    re_path(r'^path-groups/(?P<pk>\d+)/batch-add/?$', views.path_group_batch_add, name='path-group-batch-add'),
    re_path(r'^path-groups/(?P<pk>\d+)/clear-paths/?$', views.path_group_clear_paths, name='path-group-clear-paths'),
    re_path(r'^path-groups/(?P<pk>\d+)/clear-sites/?$', views.path_group_clear_sites, name='path-group-clear-sites'),
    path('heatmap-data/', views.HeatmapDataView.as_view(), name='heatmap-data'),
    path('route-snapper/calculate/', views.RouteSnapperView.as_view(), name='route-snapper-calculate'),
] + router.urls


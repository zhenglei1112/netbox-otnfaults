from django.urls import include, path
from utilities.urls import get_model_urls
from . import views

urlpatterns = [
    # OTN故障相关路由
    path('faults/', views.OtnFaultListView.as_view(), name='otnfault_list'),
    path('faults/add/', views.OtnFaultEditView.as_view(), name='otnfault_add'),
    path('faults/import/', views.OtnFaultBulkImportView.as_view(), name='otnfault_import'),
    # 批量编辑路由 - 必须手动配置
    path('faults/edit/', views.OtnFaultBulkEditView.as_view(), name='otnfault_bulk_edit'),
    path('faults/bulk-delete/', views.OtnFaultBulkDeleteView.as_view(), name='otnfault_bulk_delete'),
    path('faults/map/', views.OtnFaultMapView.as_view(), name='otnfault_map'),
    path('faults/<int:pk>/', include(get_model_urls('netbox_otnfaults', 'otnfault'))),
    path('faults/<int:pk>/edit/', views.OtnFaultEditView.as_view(), name='otnfault_edit'),
    path('faults/<int:pk>/delete/', views.OtnFaultDeleteView.as_view(), name='otnfault_delete'),

    # 故障影响业务相关路由
    path('impacts/', views.OtnFaultImpactListView.as_view(), name='otnfaultimpact_list'),
    path('impacts/add/', views.OtnFaultImpactEditView.as_view(), name='otnfaultimpact_add'),
    path('impacts/import/', views.OtnFaultImpactBulkImportView.as_view(), name='otnfaultimpact_import'),
    path('impacts/edit/', views.OtnFaultImpactBulkEditView.as_view(), name='otnfaultimpact_bulk_edit'),
    path('impacts/bulk-delete/', views.OtnFaultImpactBulkDeleteView.as_view(), name='otnfaultimpact_bulk_delete'),
    path('impacts/<int:pk>/', include(get_model_urls('netbox_otnfaults', 'otnfaultimpact'))),
    path('impacts/<int:pk>/edit/', views.OtnFaultImpactEditView.as_view(), name='otnfaultimpact_edit'),
    path('impacts/<int:pk>/delete/', views.OtnFaultImpactDeleteView.as_view(), name='otnfaultimpact_delete'),
]

from django.urls import include, path
from utilities.urls import get_model_urls
from netbox.views.generic import ObjectChangeLogView
from . import models, views

urlpatterns = [
    # OTN故障 (OtnFault)
    path('faults/', views.OtnFaultListView.as_view(), name='otnfault_list'),
    path('faults/add/', views.OtnFaultEditView.as_view(), name='otnfault_add'),
    path('faults/import/', views.OtnFaultBulkImportView.as_view(), name='otnfault_bulk_import'),
    path('faults/edit/', views.OtnFaultBulkEditView.as_view(), name='otnfault_bulk_edit'),
    path('faults/bulk-delete/', views.OtnFaultBulkDeleteView.as_view(), name='otnfault_bulk_delete'),
    path('faults/map-globe/', views.OtnFaultGlobeMapView.as_view(), name='otnfault_map_globe'),
    path('faults/map-data/', views.OtnFaultMapDataView.as_view(), name='otnfault_map_data'),
    path('map/location/', views.LocationMapView.as_view(), name='location_map'),
    path('faults/<int:pk>/', include(get_model_urls('netbox_otnfaults', 'otnfault'))),
    path('faults/<int:pk>/edit/', views.OtnFaultEditView.as_view(), name='otnfault_edit'),
    path('faults/<int:pk>/delete/', views.OtnFaultDeleteView.as_view(), name='otnfault_delete'),
    path('faults/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='otnfault_changelog', kwargs={'model': models.OtnFault}),

    # 故障影响业务 (OtnFaultImpact)
    path('impacts/', views.OtnFaultImpactListView.as_view(), name='otnfaultimpact_list'),
    path('impacts/add/', views.OtnFaultImpactEditView.as_view(), name='otnfaultimpact_add'),
    path('impacts/import/', views.OtnFaultImpactBulkImportView.as_view(), name='otnfaultimpact_bulk_import'),
    path('impacts/edit/', views.OtnFaultImpactBulkEditView.as_view(), name='otnfaultimpact_bulk_edit'),
    path('impacts/bulk-delete/', views.OtnFaultImpactBulkDeleteView.as_view(), name='otnfaultimpact_bulk_delete'),
    path('impacts/<int:pk>/', include(get_model_urls('netbox_otnfaults', 'otnfaultimpact'))),
    path('impacts/<int:pk>/edit/', views.OtnFaultImpactEditView.as_view(), name='otnfaultimpact_edit'),
    path('impacts/<int:pk>/delete/', views.OtnFaultImpactDeleteView.as_view(), name='otnfaultimpact_delete'),
    path('impacts/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='otnfaultimpact_changelog', kwargs={'model': models.OtnFaultImpact}),

    # 光缆路径 (OtnPath)
    path('paths/', views.OtnPathListView.as_view(), name='otnpath_list'),
    path('paths/add/', views.OtnPathEditView.as_view(), name='otnpath_add'),
    path('paths/import/', views.OtnPathBulkImportView.as_view(), name='otnpath_bulk_import'),
    path('paths/edit/', views.OtnPathBulkEditView.as_view(), name='otnpath_bulk_edit'),
    path('paths/bulk-delete/', views.OtnPathBulkDeleteView.as_view(), name='otnpath_bulk_delete'),
    path('paths/<int:pk>/', include(get_model_urls('netbox_otnfaults', 'otnpath'))),
    path('paths/<int:pk>/edit/', views.OtnPathEditView.as_view(), name='otnpath_edit'),
    path('paths/<int:pk>/delete/', views.OtnPathDeleteView.as_view(), name='otnpath_delete'),
    path('paths/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='otnpath_changelog', kwargs={'model': models.OtnPath}),

    # 路径组 (OtnPathGroup)
    path('path-groups/', views.OtnPathGroupListView.as_view(), name='otnpathgroup_list'),
    path('path-groups/add/', views.OtnPathGroupEditView.as_view(), name='otnpathgroup_add'),
    path('path-groups/bulk-delete/', views.OtnPathGroupBulkDeleteView.as_view(), name='otnpathgroup_bulk_delete'),
    path('path-groups/<int:pk>/', include(get_model_urls('netbox_otnfaults', 'otnpathgroup'))),
    path('path-groups/<int:pk>/edit/', views.OtnPathGroupEditView.as_view(), name='otnpathgroup_edit'),
    path('path-groups/<int:pk>/delete/', views.OtnPathGroupDeleteView.as_view(), name='otnpathgroup_delete'),
    path('path-groups/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='otnpathgroup_changelog', kwargs={'model': models.OtnPathGroup}),
]


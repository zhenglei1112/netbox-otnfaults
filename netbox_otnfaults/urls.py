from django.urls import include, path
from utilities.urls import get_model_urls
from netbox.views.generic import ObjectChangeLogView
from . import models, views
from . import dashboard_views
from . import weekly_report_views
from . import statistics_views
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

    # 路径组站点关联 (OtnPathGroupSite)
    path('path-group-sites/add/', views.OtnPathGroupSiteEditView.as_view(), name='otnpathgroupsite_add'),
    path('path-group-sites/<int:pk>/edit/', views.OtnPathGroupSiteEditView.as_view(), name='otnpathgroupsite_edit'),
    path('path-group-sites/<int:pk>/delete/', views.OtnPathGroupSiteDeleteView.as_view(), name='otnpathgroupsite_delete'),

    # 裸纤业务 (BareFiberService)
    path('bare-fiber-services/', views.BareFiberServiceListView.as_view(), name='barefiberservice_list'),
    path('bare-fiber-services/add/', views.BareFiberServiceEditView.as_view(), name='barefiberservice_add'),
    path('bare-fiber-services/import/', views.BareFiberServiceBulkImportView.as_view(), name='barefiberservice_bulk_import'),
    path('bare-fiber-services/edit/', views.BareFiberServiceBulkEditView.as_view(), name='barefiberservice_bulk_edit'),
    path('bare-fiber-services/bulk-delete/', views.BareFiberServiceBulkDeleteView.as_view(), name='barefiberservice_bulk_delete'),
    path('bare-fiber-services/<int:pk>/', include(get_model_urls('netbox_otnfaults', 'barefiberservice'))),
    path('bare-fiber-services/<int:pk>/edit/', views.BareFiberServiceEditView.as_view(), name='barefiberservice_edit'),
    path('bare-fiber-services/<int:pk>/delete/', views.BareFiberServiceDeleteView.as_view(), name='barefiberservice_delete'),
    path('bare-fiber-services/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='barefiberservice_changelog', kwargs={'model': models.BareFiberService}),

    # 电路业务 (CircuitService)
    path('circuit-services/', views.CircuitServiceListView.as_view(), name='circuitservice_list'),
    path('circuit-services/add/', views.CircuitServiceEditView.as_view(), name='circuitservice_add'),
    path('circuit-services/import/', views.CircuitServiceBulkImportView.as_view(), name='circuitservice_bulk_import'),
    path('circuit-services/edit/', views.CircuitServiceBulkEditView.as_view(), name='circuitservice_bulk_edit'),
    path('circuit-services/bulk-delete/', views.CircuitServiceBulkDeleteView.as_view(), name='circuitservice_bulk_delete'),
    path('circuit-services/<int:pk>/', include(get_model_urls('netbox_otnfaults', 'circuitservice'))),
    path('circuit-services/<int:pk>/edit/', views.CircuitServiceEditView.as_view(), name='circuitservice_edit'),
    path('circuit-services/<int:pk>/delete/', views.CircuitServiceDeleteView.as_view(), name='circuitservice_delete'),
    path('circuit-services/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='circuitservice_changelog', kwargs={'model': models.CircuitService}),


    # OTN线路设计器
    path('route-editor/', views.RouteEditorView.as_view(), name='route_editor'),

    # 大屏可视化系统
    path('dashboard/', dashboard_views.DashboardPageView.as_view(), name='dashboard'),
    path('dashboard/data/', dashboard_views.DashboardDataAPI.as_view(), name='dashboard_data'),

    # 每周通报大屏
    path('weekly-report/', weekly_report_views.WeeklyReportPageView.as_view(), name='weekly_report'),
    path('weekly-report/data/', weekly_report_views.WeeklyReportDataAPI.as_view(), name='weekly_report_data'),

    # 故障统计看板
    path('statistics/', statistics_views.FaultStatisticsPageView.as_view(), name='statistics'),
    path('statistics/data/', statistics_views.FaultStatisticsDataAPI.as_view(), name='statistics_data'),
]


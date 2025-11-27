from django.urls import path
from . import views
from netbox.views.generic import ObjectChangeLogView, ObjectJournalView

urlpatterns = [
    # OTN故障相关路由
    path('faults/', views.OtnFaultListView.as_view(), name='otnfault_list'),
    path('faults/add/', views.OtnFaultEditView.as_view(), name='otnfault_add'),
    path('faults/<int:pk>/', views.OtnFaultView.as_view(), name='otnfault'),
    path('faults/<int:pk>/edit/', views.OtnFaultEditView.as_view(), name='otnfault_edit'),
    path('faults/<int:pk>/delete/', views.OtnFaultDeleteView.as_view(), name='otnfault_delete'),
    path('faults/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='otnfault_changelog', kwargs={'model': views.OtnFault}),
    path('faults/<int:pk>/journal/', ObjectJournalView.as_view(), name='otnfault_journal', kwargs={'model': views.OtnFault}),

    # 故障影响业务相关路由
    path('impacts/', views.OtnFaultImpactListView.as_view(), name='otnfaultimpact_list'),
    path('impacts/add/', views.OtnFaultImpactEditView.as_view(), name='otnfaultimpact_add'),
    path('impacts/<int:pk>/', views.OtnFaultImpactView.as_view(), name='otnfaultimpact'),
    path('impacts/<int:pk>/edit/', views.OtnFaultImpactEditView.as_view(), name='otnfaultimpact_edit'),
    path('impacts/<int:pk>/delete/', views.OtnFaultImpactDeleteView.as_view(), name='otnfaultimpact_delete'),
    path('impacts/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='otnfaultimpact_changelog', kwargs={'model': views.OtnFaultImpact}),
    path('impacts/<int:pk>/journal/', ObjectJournalView.as_view(), name='otnfaultimpact_journal', kwargs={'model': views.OtnFaultImpact}),
]

from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def read_source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_cutover_task_model_defines_core_fields_and_helpers() -> None:
    source = read_source("netbox_otnfaults/models.py")

    assert "class CutoverStatusChoices(ChoiceSet):" in source
    assert "(APPLYING, '申请中', 'blue')" in source
    assert "(PENDING_IMPLEMENTATION, '待实施', 'orange')" in source
    assert "(COMPLETED, '已完成', 'green')" in source
    assert "(CANCELLED, '被取消', 'gray')" in source
    cutover_management_choices = source.split("class CutoverManagementUnitChoices(ChoiceSet):", 1)[1].split("class ResourceTypeChoices", 1)[0]
    assert "(HEADQUARTERS, '本部', 'blue')" in cutover_management_choices
    assert "(ZHEJIANG, '浙江子公司', 'green')" in cutover_management_choices
    assert "(SHAANXI, '陕西子公司', 'orange')" in cutover_management_choices
    assert "(SICHUAN, '四川子公司', 'purple')" in cutover_management_choices
    assert "(INNER_MONGOLIA, '内蒙古子公司', 'teal')" in cutover_management_choices
    assert "(JIANGXI, '江西子公司', 'yellow')" in cutover_management_choices
    assert "(SHANDONG, '山东子公司', 'cyan')" in cutover_management_choices
    assert "(THIRD_PARTY, '第三方', 'gray')" in cutover_management_choices
    assert "'各子公司'" not in cutover_management_choices
    assert "class CutoverTimeoutStatusChoices(ChoiceSet):" in source
    assert "class CutoverResultChoices(ChoiceSet):" in source
    assert "class CutoverTask(NetBoxModel, ImageAttachmentsMixin):" in source
    assert "cutover_no = models.CharField" in source
    assert "registered_at = models.DateTimeField" in source
    assert "registrant = models.ForeignKey" in source
    assert "planned_cutover_times = models.JSONField" in source
    assert "related_customers = models.JSONField" in source
    assert "interruption_location_a = models.ForeignKey" in source
    assert "interruption_location = models.ManyToManyField" in source
    assert "cutover_longitude = models.DecimalField" in source
    assert "cutover_latitude = models.DecimalField" in source
    cutover_task_model = source.split("class CutoverTask(NetBoxModel, ImageAttachmentsMixin):", 1)[1].split("class CutoverImpact", 1)[0]
    assert "customer_approval_result" not in cutover_task_model
    assert "CutoverApprovalResultChoices" not in source
    assert "maintenance_unit" not in cutover_task_model
    assert "service_interrupted_at" not in cutover_task_model
    assert "service_restored_at" not in cutover_task_model
    assert "actual_interrupt_minutes" not in cutover_task_model
    assert "def get_absolute_url(self) -> str:" in source
    assert "reverse('plugins:netbox_otnfaults:cutovertask'" in source


def test_cutover_task_number_is_system_generated_and_readonly() -> None:
    models = read_source("netbox_otnfaults/models.py")
    forms = read_source("netbox_otnfaults/forms.py")
    migration = read_source("netbox_otnfaults/migrations/0067_cutovertask.py")
    edit_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html")

    assert "help_text='系统自动生成，格式为CYYYYNNNN'" in models
    assert "blank=True" in models
    assert "def save(self, *args: Any, **kwargs: Any) -> None:" in models
    assert "year = timezone.localdate().strftime('%Y')" in models
    assert "prefix = f'C{year}'" in models
    assert ".filter(cutover_no__startswith=prefix)" in models
    assert "last_number = int(last_cutover.cutover_no[5:])" in models
    assert "self.cutover_no = f'{prefix}{new_number:04d}'" in models
    assert "'cutover_no'," in models

    assert "blank=True" in migration
    assert "help_text='系统自动生成，格式为CYYYYNNNN" in migration

    assert "'cutover_no'" not in forms.split("class CutoverTaskForm", 1)[1].split("class CutoverTaskFilterForm", 1)[0].split("fields = (", 1)[1].split(")", 1)[0]
    assert "cutover_no_display" in forms
    assert "disabled=True" in forms
    assert "割接编号创建后不可修改" in forms
    assert "{% render_field form.cutover_no %}" not in edit_template
    assert "{% render_field form.cutover_no_display %}" in edit_template


def test_cutover_task_ui_forms_tables_filters_and_views_are_registered() -> None:
    forms = read_source("netbox_otnfaults/forms.py")
    tables = read_source("netbox_otnfaults/tables.py")
    filters = read_source("netbox_otnfaults/filtersets.py")
    views = read_source("netbox_otnfaults/views.py")
    urls = read_source("netbox_otnfaults/urls.py")
    navigation = read_source("netbox_otnfaults/navigation.py")

    assert "class CutoverTaskForm(NetBoxModelForm):" in forms
    assert "class CutoverTaskFilterForm(NetBoxModelFilterSetForm):" in forms
    assert "class CutoverTaskImportForm(NetBoxModelImportForm):" in forms
    assert "class CutoverTaskBulkEditForm(NetBoxModelBulkEditForm):" in forms
    assert "FieldSet('cutover_no_display', 'status', 'registered_at', 'registrant'" in forms
    assert "widget=DateTimePicker()" in forms

    assert "class CutoverTaskTable(NetBoxTable):" in tables
    cutover_task_table = tables.split("class CutoverTaskTable", 1)[1].split("class CircuitServiceTable", 1)[0]
    assert "def render_status(self, value, record):" in cutover_task_table
    assert "record.get_status_color()" in cutover_task_table
    assert "record.get_status_display()" in cutover_task_table
    assert '<span class="badge bg-{} text-white">{}</span>' in cutover_task_table
    assert "'actions'," in tables
    assert "url_name='plugins:netbox_otnfaults:cutovertask_list'" in tables

    assert "class CutoverTaskFilterSet(NetBoxModelFilterSet):" in filters
    assert "planned_cutover_time_after = django_filters.DateTimeFilter" in filters
    assert "planned_cutover_time_before = django_filters.DateTimeFilter" in filters

    assert "class CutoverTaskListView(ExcelFriendlyCSVExportMixin, generic.ObjectListView):" in views
    assert "@register_model_view(CutoverTask)" in views
    assert "class CutoverTaskView(generic.ObjectView):" in views
    assert "class CutoverTaskEditView(generic.ObjectEditView):" in views
    assert "class CutoverTaskBulkImportView(generic.BulkImportView):" in views
    assert "class CutoverTaskBulkDeleteView(generic.BulkDeleteView):" in views
    assert "class CutoverTaskBulkEditView(generic.BulkEditView):" in views

    assert "path('cutovers/', views.CutoverTaskListView.as_view(), name='cutovertask_list')" in urls
    assert "path('cutovers/add/', views.CutoverTaskEditView.as_view(), name='cutovertask_add')" in urls
    assert "path('cutovers/<int:pk>/', include(get_model_urls('netbox_otnfaults', 'cutovertask')))" in urls

    assert "label='故障与割接'" in navigation
    assert "label='故障管理'" not in navigation
    assert "('故障', (" in navigation
    assert "('割接', (" in navigation
    assert "link='plugins:netbox_otnfaults:cutovertask_list'" in navigation
    assert "link_text='割接管理'" in navigation
    assert "permissions=['netbox_otnfaults.view_cutovertask']" in navigation
    cutover_group = navigation.split("('割接', (", 1)[1].split(")),", 1)[0]
    assert "link='plugins:netbox_otnfaults:cutovertask_list'" in cutover_group
    assert "link='plugins:netbox_otnfaults:cutoverimpact_list'" in cutover_group
    fault_group = navigation.split("('故障', (", 1)[1].split(")),", 1)[0]
    assert "link='plugins:netbox_otnfaults:cutovertask_list'" not in fault_group
    assert "link='plugins:netbox_otnfaults:cutoverimpact_list'" not in fault_group


def test_cutover_task_form_normalizes_empty_json_fields_to_lists() -> None:
    forms = read_source("netbox_otnfaults/forms.py")

    assert "def _clean_json_list_field(self, field_name: str) -> list[object]:" in forms
    assert "return []" in forms
    assert "def clean_planned_cutover_times(self) -> list[object]:" in forms
    assert "return self._clean_json_list_field('planned_cutover_times')" in forms
    assert "def clean_related_customers(self) -> list[object]:" in forms
    assert "return self._clean_json_list_field('related_customers')" in forms
    assert "def clean_customer_approval_detail(self) -> list[object]:" in forms
    assert "return self._clean_json_list_field('customer_approval_detail')" in forms


def test_cutover_task_model_normalizes_nullable_json_fields_before_validation() -> None:
    models = read_source("netbox_otnfaults/models.py")

    assert "def _normalize_json_list_fields(self) -> None:" in models
    assert "for field_name in ('planned_cutover_times', 'related_customers', 'customer_approval_detail'):" in models
    assert "if getattr(self, field_name) is None:" in models
    assert "setattr(self, field_name, [])" in models
    assert "self._normalize_json_list_fields()" in models


def test_cutover_task_api_serializer_viewset_router_and_templates_exist() -> None:
    serializers = read_source("netbox_otnfaults/api/serializers.py")
    api_views = read_source("netbox_otnfaults/api/views.py")
    api_urls = read_source("netbox_otnfaults/api/urls.py")

    assert "class CutoverTaskSerializer(NetBoxModelSerializer):" in serializers
    assert "model = CutoverTask" in serializers
    assert "'planned_cutover_times'" in serializers
    cutover_task_serializer = serializers.split("class CutoverTaskSerializer", 1)[1].split("class OtnMapPreferenceSerializer", 1)[0]
    assert "service_interrupted_at" not in cutover_task_serializer
    assert "service_restored_at" not in cutover_task_serializer
    assert "actual_interrupt_minutes" not in cutover_task_serializer
    assert "customer_approval_result" not in cutover_task_serializer
    assert "maintenance_unit" not in cutover_task_serializer

    assert "class CutoverTaskViewSet(NetBoxModelViewSet):" in api_views
    assert "queryset = CutoverTask.objects.all()" in api_views
    assert "serializer_class = CutoverTaskSerializer" in api_views
    assert "filterset_class = CutoverTaskFilterSet" in api_views

    assert "router.register('cutovers', views.CutoverTaskViewSet)" in api_urls

    detail_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html")
    edit_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html")

    assert "割接信息" in detail_template
    assert "计划割接时间" in detail_template
    assert "割接位置" in detail_template
    assert "实施时间线" in detail_template
    assert "{% render_field form.cutover_no_display %}" in edit_template
    assert "{% render_field form.cutover_longitude %}" in edit_template


def test_cutover_task_edit_inline_script_keeps_path_shortcuts_inside_iife() -> None:
    edit_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html")
    script_match = re.search(r"<script>\s*(.*?)\s*</script>", edit_template, re.DOTALL)

    assert script_match is not None
    assert "    // Z端快捷定位" in edit_template
    subprocess.run(
        ["node", "--check"],
        input=script_match.group(1),
        text=True,
        check=True,
        capture_output=True,
    )


def test_cutover_task_related_customers_use_bare_fiber_multi_select() -> None:
    forms = read_source("netbox_otnfaults/forms.py")
    views = read_source("netbox_otnfaults/views.py")
    urls = read_source("netbox_otnfaults/urls.py")
    edit_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html")
    detail_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html")

    assert "related_customers = forms.JSONField(required=False, label='设置关联用户')" in forms

    assert "def get_extra_context(self, request, instance):" in views
    assert "BareFiberService.objects.select_related('tenant_group')" in views
    assert "'bare_fiber_services': bare_fiber_services" in views

    assert '{% load form_helpers helpers %}' in edit_template
    assert "{{ bare_fiber_services|json_script:\"cutover-bare-fiber-services\" }}" in edit_template
    assert "const bareFiberServices = JSON.parse(" in edit_template
    assert "设置关联用户" in edit_template
    assert "bare-fiber-service-checkbox" in edit_template
    assert "service_id" in edit_template
    assert "已协调" in edit_template
    assert "是否协调" not in edit_template
    assert "customer-coordinated" in edit_template
    assert "customer-coordination-time" in edit_template
    assert "syncJsonInput();" in edit_template

    assert "class CutoverTaskRelatedCustomersView(PermissionRequiredMixin, View):" in views
    assert "permission_required = 'netbox_otnfaults.change_cutovertask'" in views
    assert "json.loads(request.POST.get('related_customers', '[]'))" in views
    assert "task.related_customers = related_customers" in views
    assert "task.save(update_fields=['related_customers', 'last_updated'])" in views
    assert "cutovers/<int:pk>/related-customers/" in urls

    assert "{{ bare_fiber_services|json_script:\"cutover-detail-bare-fiber-services\" }}" in detail_template
    assert "{{ object.related_customers|json_script:\"cutover-detail-related-customers\" }}" in detail_template
    assert "cutovertask_related_customers" in detail_template
    assert "cutover-related-customers-form" in detail_template
    assert "cutover-related-customers-json" in detail_template
    assert "btn-set-related-customers" in detail_template
    assert "保存协调信息" in detail_template
    assert "customer-coordinated" in detail_template
    assert "customer-coordination-time" in detail_template
    assert "function formatCurrentMinute()" in detail_template
    assert "String(value).padStart(2, '0')" in detail_template
    assert "this.checked && !relatedCustomers[index].time" in detail_template
    assert "timeInput.value = currentTime;" in detail_template
    assert "customerModal" in detail_template
    assert "bare-fiber-service-checkbox" in detail_template
    assert "btn-save-customers" in detail_template
    assert "modal-dialog modal-dialog-centered cutover-customer-dialog" in detail_template
    assert "width: min(760px, calc(100vw - 2rem));" in detail_template
    assert "max-height: 52vh;" in detail_template
    assert "cutover-customer-picker .table > :not(caption) > * > *" in detail_template
    assert "backdrop.style.backgroundColor = '#808080';" in detail_template
    assert "backdrop.style.opacity = '1';" in detail_template
    assert 'id="cutover-customer-picker"' not in detail_template
    assert 'class="btn btn-ghost-primary btn-sm" id="btn-set-related-customers"' in detail_template
    assert 'class="btn btn-primary generate-planned-time-btn" id="btn-save-customers"' in detail_template
    assert 'class="btn btn-secondary generate-planned-time-btn" id="btn-cancel-related-customers"' in detail_template
    assert "btn btn-outline-primary btn-sm" not in detail_template
    assert "btn btn-sm btn-primary" not in detail_template
    assert "btn btn-sm btn-outline-secondary" not in detail_template


def test_cutover_task_form_fieldsets_follow_detail_page_grouping_order() -> None:
    forms = read_source("netbox_otnfaults/forms.py")
    form_source = forms.split("class CutoverTaskForm(NetBoxModelForm):", 1)[1].split("class CutoverTaskFilterForm", 1)[0]
    fieldsets_source = form_source.split("fieldsets = (", 1)[1].split("\n    )", 1)[0]

    expected_order = [
        "割接信息",
        "割接位置",
        "资源信息",
        "组织联系人",
        "计划割接时间",
        "关联用户",
        "实施时间线",
        "考核与闭环",
        "整改信息",
        "其他",
    ]
    positions = [fieldsets_source.index(f"name='{name}'") for name in expected_order]
    assert positions == sorted(positions)

    assert "FieldSet('cutover_no_display', 'status', 'registered_at', 'registrant', 'management_unit', 'management_unit_name', 'cutover_reason', name='割接信息')" in fieldsets_source
    assert "FieldSet('province', 'cutover_longitude', 'cutover_latitude', 'cutover_location', 'interruption_location_a', 'interruption_location', name='割接位置')" in fieldsets_source
    assert "FieldSet('resource_type', 'cable_route', 'resource_owner', 'maintenance_mode', 'handling_unit', 'contract', name='资源信息')" in fieldsets_source
    assert "FieldSet('implementation_unit', 'cutover_contact', 'cutover_contact_phone', 'line_supervisor', name='组织联系人')" in fieldsets_source
    assert "FieldSet('related_customers', name='关联用户')" in fieldsets_source
    assert "FieldSet('customer_approval_detail', 'is_timeout', 'timeout_reason', 'cutover_result', 'remaining_issues', name='考核与闭环')" in fieldsets_source
    assert "customer_approval_result" not in form_source
    assert "maintenance_unit" not in form_source

    edit_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html")
    edit_titles = [
        "割接信息",
        "割接位置",
        "资源信息",
        "组织联系人",
        "计划割接时间",
        "关联用户",
        "实施时间线",
        "考核与闭环",
        "整改信息",
    ]
    edit_positions = [edit_template.index(f">{title}</h2>") for title in edit_titles]
    assert edit_positions == sorted(edit_positions)
    assert "计划与地点" not in edit_template
    assert "影响范围" not in edit_template
    assert "维护与组织" not in edit_template
    assert "审核与实施" not in edit_template


def test_cutover_task_detail_renders_planned_times_and_related_customers_as_readable_tables() -> None:
    detail_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html")

    assert '<pre class="mb-0">{{ object.planned_cutover_times|default:"[]" }}</pre>' not in detail_template
    assert '<pre class="mb-0">{{ object.related_customers|default:"[]" }}</pre>' not in detail_template
    assert "{% for time in object.planned_cutover_times reversed %}" in detail_template
    assert "第{{ forloop.revcounter }}次" in detail_template
    assert "最新" in detail_template
    assert "cutover-time-record" in detail_template
    assert "var(--bs-tertiary-bg)" in detail_template
    assert "border-color: transparent;" in detail_template
    assert '[data-bs-theme="dark"] .cutover-time-record' in detail_template
    assert "bg-success-subtle" not in detail_template
    assert "bg-light" not in detail_template
    assert "{{ object.related_customers|json_script:\"cutover-detail-related-customers\" }}" in detail_template
    assert "relatedCustomers.forEach((item, index) => {" in detail_template
    assert "item.tenant_group || item.tenant" in detail_template
    assert "item.name || item.business" in detail_template
    assert "item.time || item.coordination_time" in detail_template
    assert "租户组" in detail_template
    assert "业务名称" in detail_template
    assert "已协调" in detail_template
    assert "customer-coordinated" in detail_template
    assert "保存协调信息" in detail_template
    assert "协调时间" in detail_template
    assert "暂无关联用户记录" in detail_template


def test_cutover_task_detail_uses_standard_netbox_two_column_layout() -> None:
    detail_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html")

    assert "cutover-detail-summary" not in detail_template
    assert "cutover-summary-grid" not in detail_template
    assert "cutover-detail-grid" not in detail_template
    assert "col-12 col-xl-5" not in detail_template
    assert "col-12 col-xl-7" not in detail_template
    assert "割接概览" not in detail_template
    assert detail_template.count('<div class="col col-md-6">') >= 2
    assert "关联用户" in detail_template
    assert "割接信息</h5>" in detail_template
    assert 'class="badge bg-{{ object.get_status_color|default:\'secondary\' }} text-white"' in detail_template
    assert "{{ object.get_status_display|default:\"—\" }}" in detail_template
    assert "割接位置</h5>" in detail_template
    assert "影响范围</h5>" not in detail_template
    assert "地域地点</h5>" not in detail_template
    assert '<tr><th scope="row">关联用户</th>' not in detail_template
    assert "table-responsive cutover-related-customers-table" in detail_template

    left_column = detail_template.split('<div class="col col-md-6">', 1)[1].split('<div class="col col-md-6">', 1)[0]
    right_column = detail_template.split('<div class="col col-md-6">', 2)[2].split('</div>\n</div>\n\n{# 割接影响业务面板 #}', 1)[0]
    assert left_column.index("割接信息</h5>") < left_column.index("割接位置</h5>")
    assert left_column.index("割接位置</h5>") < left_column.index("计划割接时间</h5>")
    cutover_info_card = left_column.split("割接信息</h5>", 1)[1].split("割接位置</h5>", 1)[0]
    assert "割接原因" in cutover_info_card
    assert "A端站点" not in cutover_info_card
    assert "Z端站点" not in cutover_info_card
    cutover_location_card = left_column.split("割接位置</h5>", 1)[1].split("计划割接时间</h5>", 1)[0]
    assert "A端:" in cutover_location_card
    assert "Z端:" in cutover_location_card
    assert "省份与坐标" in cutover_location_card
    assert "GPS:" in cutover_location_card
    assert "mdi mdi-map-marker" in cutover_location_card
    assert "location_map_url" in cutover_location_card
    assert "a_site={{ object.interruption_location_a.pk }}" in cutover_location_card
    assert "z_sites=" in cutover_location_card
    assert "q={{ object.cutover_latitude|unlocalize }},{{ object.cutover_longitude|unlocalize }}" in cutover_location_card
    assert cutover_location_card.index("A端:") < cutover_location_card.index("省份与坐标")
    assert cutover_location_card.index("省份与坐标") < cutover_location_card.index("割接具体地点")
    assert "A端站点" not in cutover_location_card
    assert "Z端站点" not in cutover_location_card
    assert "<tr><th scope=\"row\">经度</th>" not in cutover_location_card
    assert "<tr><th scope=\"row\">纬度</th>" not in cutover_location_card
    assert left_column.index("计划割接时间</h5>") < left_column.index("cutover-related-customers-form")
    assert left_column.index("cutover-related-customers-form") < left_column.index("实施时间线</h5>")
    timeline_card = left_column.split("实施时间线</h5>", 1)[1].split("考核与闭环</h5>", 1)[0]
    assert timeline_card.index("割接完成时间") < timeline_card.index("割接历时")
    assert timeline_card.index("割接历时") < timeline_card.index("割接封包时间")
    assert "object.cutover_duration" in timeline_card
    assert "业务中断时间" not in timeline_card
    assert "业务恢复时间" not in timeline_card
    assert "实际中断时长" not in timeline_card
    assert "超时原因" not in timeline_card
    assert "遗留问题" not in timeline_card
    assert left_column.index("实施时间线</h5>") < left_column.index("考核与闭环</h5>")
    assert left_column.index("考核与闭环</h5>") < left_column.index("整改信息</h5>")
    assessment_card = left_column.split("考核与闭环</h5>", 1)[1].split("整改信息</h5>", 1)[0]
    assert "割接是否超时" in assessment_card
    assert "割接效果" in assessment_card
    assert "超时原因" in assessment_card
    assert "遗留问题" in assessment_card
    assert "考核与闭环</h5>" not in right_column
    assert "整改信息</h5>" not in right_column
    assert "标签" not in left_column
    assert "评论" not in left_column
    assert "割接位置</h5>" not in right_column
    assert "inc/panels/tags.html" in right_column
    assert "inc/panels/comments.html" in right_column


def test_cutover_task_exposes_cutover_duration_as_computed_property() -> None:
    model_source = read_source("netbox_otnfaults/models.py")

    assert "def cutover_duration(self) -> str | None:" in model_source
    assert "duration = end_time - self.started_at" in model_source
    assert "return f\"{duration_text}（{total_hours:.2f}小时）{ongoing_marker}\"" in model_source
    assert "cutover_duration = models." not in model_source


def test_cutover_task_detail_renders_all_model_field_groups() -> None:
    detail_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html")

    assert '<h5 class="card-header">客户审核</h5>' not in detail_template
    assert "客户审核明细" not in detail_template
    assert "object.customer_approval_detail" not in detail_template
    assert "客户审核结果" not in detail_template
    assert "维护单位" not in detail_template
    assert "object.maintenance_unit" not in detail_template

    expected_markers = {
        "资源信息": [
            "光纤来源",
            "光缆路由属性",
            "资源所有者",
            "维护方式",
            "代维方/租赁方",
            "代维/租赁合同",
            "object.get_resource_type_display",
            "object.get_cable_route_display",
            "object.get_resource_owner_display",
            "object.get_maintenance_mode_display",
            "object.handling_unit",
            "object.contract",
        ],
        "组织联系人": [
            "线路主管",
            "object.line_supervisor",
        ],
        "整改信息": [
            "是否整改",
            "整改措施",
            "措施描述",
            "整改主体",
            "整改进度",
            "计划完成时间",
            "实际完成时间",
            "整改完成情况描述",
            "object.get_rectification_status_display",
            "object.rectification_measures",
            "object.rectification_description",
            "object.get_rectification_subject_display",
            "object.get_rectification_progress_display",
            "object.planned_completion_time",
            "object.actual_completion_time",
            "object.rectification_completion_description",
        ],
    }
    for card_title, markers in expected_markers.items():
        assert f">{card_title}</h5>" in detail_template
        for marker in markers:
            assert marker in detail_template


def test_cutover_task_detail_keeps_attr_table_labels_on_one_line() -> None:
    detail_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html")

    assert "cutover-detail" in detail_template
    assert ".cutover-detail .attr-table th[scope=\"row\"]" in detail_template
    assert "width: clamp(7rem, 14%, 9rem);" in detail_template
    assert "min-width: 7rem;" in detail_template
    assert "width: 1%;" not in detail_template
    assert "min-width: 9.5rem;" not in detail_template
    assert "white-space: nowrap;" in detail_template
    assert "word-break: keep-all;" in detail_template
    assert ".cutover-detail .attr-table td" in detail_template
    assert "overflow-wrap: anywhere;" in detail_template


def test_cutover_task_regenerating_planned_time_requires_confirmation_and_resets_customer_approval() -> None:
    edit_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html")
    detail_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html")
    views = read_source("netbox_otnfaults/views.py")
    urls = read_source("netbox_otnfaults/urls.py")

    assert "生成新的割接时间，需要重新与每个关联用户确认（会清理掉已有的关联用户确认状态），确定要生成吗？" in edit_template
    assert "if (!confirm(regenerateConfirmMessage)) {" in edit_template
    assert "window.dispatchEvent(new CustomEvent('cutover:planned-time-regenerated'));" in edit_template
    assert "window.addEventListener('cutover:planned-time-regenerated'" in edit_template
    assert "item.is_coordinated = false;" in edit_template
    assert "item.time = '';" in edit_template

    assert "class CutoverTaskGeneratePlannedTimeView(PermissionRequiredMixin, View):" in views
    assert "permission_required = 'netbox_otnfaults.change_cutovertask'" in views
    assert "raw_time = request.POST.get('planned_cutover_time', '').strip()" in views
    assert "parse_datetime(raw_time)" in views
    assert "task.planned_cutover_time = parsed_time" in views
    assert "task.planned_cutover_times.append(new_time)" in views
    assert "customer['is_coordinated'] = False" in views
    assert "customer['time'] = ''" in views
    assert "customer['coordination_time'] = ''" in views
    assert "'planned_cutover_times', 'related_customers'" in views
    assert "cutovers/<int:pk>/generate-planned-time/" in urls

    assert "生成新的割接时间" in detail_template
    assert "cutovertask_generate_planned_time" in detail_template
    assert 'name="planned_cutover_time"' in detail_template
    assert 'type="datetime-local"' in detail_template
    assert '<button type="submit" class="btn btn-ghost-primary btn-sm">' in detail_template
    assert "{% csrf_token %}" in detail_template
    assert "生成新的割接时间，需要重新与每个关联用户确认，会清理掉已有的关联用户确认状态和协调时间，确定生成吗？" in detail_template
    assert "return confirm(" not in detail_template
    assert 'id="generatePlannedTimeModal"' in detail_template
    assert 'class="modal-dialog modal-dialog-centered generate-planned-time-dialog"' in detail_template
    assert 'class="modal-content"' in detail_template
    assert "width: min(560px, calc(100vw - 2rem));" in detail_template
    assert "aspect-ratio: 1.618 / 1;" not in detail_template
    assert 'class="modal-backdrop fade show"' in detail_template
    assert "background-color: #808080;" in detail_template
    assert "opacity: 1;" in detail_template
    assert 'class="seal-reason-text"' not in detail_template
    assert 'class="btn btn-primary generate-planned-time-btn"' in detail_template
    assert 'class="btn btn-secondary generate-planned-time-btn"' in detail_template
    assert "确认生成" in detail_template
    assert "取消" in detail_template
    assert "showGeneratePlannedTimeModal()" in detail_template
    assert "submitGeneratePlannedTimeForm()" in detail_template


def test_cutover_task_province_foreign_key_has_legacy_column_migration() -> None:
    migration = read_source("netbox_otnfaults/migrations/0068_cutovertask_province_fk.py")

    assert "legacy province text column" in migration
    assert "ALTER TABLE netbox_otnfaults_cutovertask RENAME COLUMN province TO province_text" in migration
    assert "ALTER TABLE netbox_otnfaults_cutovertask ADD COLUMN province_id bigint NULL" in migration
    assert "dcim_region" in migration
    assert "models.ForeignKey" in migration


def test_cutover_task_legacy_remarks_column_is_removed_safely() -> None:
    migration = read_source("netbox_otnfaults/migrations/0070_cutovertask_drop_legacy_remarks.py")

    assert "remarks" in migration
    assert "comments" in migration
    assert "information_schema.columns" in migration
    assert "ALTER TABLE netbox_otnfaults_cutovertask DROP COLUMN remarks" in migration


def test_cutover_task_legacy_maintenance_unit_column_is_removed_safely() -> None:
    migration = read_source("netbox_otnfaults/migrations/0074_drop_legacy_cutovertask_maintenance_unit.py")

    assert "maintenance_unit" in migration
    assert "information_schema.columns" in migration
    assert "ALTER TABLE netbox_otnfaults_cutovertask DROP COLUMN maintenance_unit" in migration
    assert "ADD COLUMN IF NOT EXISTS maintenance_unit" in migration


def test_cutover_impact_model_and_migration_are_defined() -> None:
    models = read_source("netbox_otnfaults/models.py")
    migration = read_source("netbox_otnfaults/migrations/0071_cutoverimpact.py")

    assert "class CutoverImpact(NetBoxModel, ImageAttachmentsMixin):" in models
    assert "cutover_task = models.ForeignKey" in models
    assert "related_name='impacts'" in models
    assert "related_name='cutover_impacts'" in models
    assert "related_name='cutover_impact_service_site_a'" in models
    assert "related_name='cutover_impact_service_site_z'" in models
    cutover_impact_model = models.split("class CutoverImpact", 1)[1].split("class Meta:", 1)[0]
    assert "secondary_cutovers" not in cutover_impact_model
    assert "secondary_impacts" not in cutover_impact_model
    assert "name='unique_cutover_bare_fiber'" in models
    assert "name='unique_cutover_circuit'" in models
    assert "def get_absolute_url(self) -> str:" in models
    assert "reverse('plugins:netbox_otnfaults:cutoverimpact'" in models
    assert "self.service_site_z.clear()" in models

    assert "name='CutoverImpact'" in migration
    assert "unique_cutover_bare_fiber" in migration
    assert "unique_cutover_circuit" in migration
    assert "service_site_z" in migration
    assert "secondary_cutovers" not in migration
    assert "secondary_impacts" not in migration


def test_cutover_impact_forms_are_defined_and_imported() -> None:
    forms = read_source("netbox_otnfaults/forms.py")
    views = read_source("netbox_otnfaults/views.py")

    assert "CutoverTask, CutoverImpact" in forms
    assert "class CutoverImpactImportForm(NetBoxModelImportForm):" in forms
    assert "class CutoverImpactForm(NetBoxModelForm):" in forms
    assert "class CutoverImpactBulkEditForm(NetBoxModelBulkEditForm):" in forms
    assert "class CutoverImpactFilterForm(NetBoxModelFilterSetForm):" in forms
    assert "cutover_task = DynamicModelChoiceField" in forms
    cutover_forms = forms.split("class CutoverImpactImportForm", 1)[1]
    assert "secondary_cutovers" not in cutover_forms
    assert "其他关联割接" not in cutover_forms
    assert "circuit_business_category = forms.ChoiceField" in forms
    assert "circuit_special_line_name = forms.ChoiceField" in forms
    assert "data-circuit-services" in forms
    cutover_task_forms = forms.split("class CutoverTaskForm", 1)[1].split("def _build_circuit_service_catalog", 1)[0]
    assert "service_interrupted_at" not in cutover_task_forms
    assert "service_restored_at" not in cutover_task_forms
    cutover_impact_form = forms.split("class CutoverImpactForm", 1)[1].split("class CutoverImpactBulkEditForm", 1)[0]
    assert "cutover.service_interrupted_at" not in cutover_impact_form
    assert "cutover.service_restored_at" not in cutover_impact_form
    assert "planned_cutover_time" in forms
    assert "CutoverImpactForm, CutoverImpactFilterForm, CutoverImpactImportForm, CutoverImpactBulkEditForm" in views


def test_cutover_impact_tables_filters_api_urls_and_templates_are_registered() -> None:
    tables = read_source("netbox_otnfaults/tables.py")
    filtersets = read_source("netbox_otnfaults/filtersets.py")
    serializers = read_source("netbox_otnfaults/api/serializers.py")
    api_views = read_source("netbox_otnfaults/api/views.py")
    api_urls = read_source("netbox_otnfaults/api/urls.py")
    urls = read_source("netbox_otnfaults/urls.py")
    detail_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html")
    impact_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutoverimpact.html")
    edit_template = read_source("netbox_otnfaults/templates/netbox_otnfaults/cutoverimpact_edit.html")

    assert "class CutoverImpactTable(NetBoxTable):" in tables
    assert "class CutoverImpactSummaryTable(CutoverImpactTable):" in tables
    impact_table = tables.split("class CutoverImpactTable", 1)[1].split("class CutoverImpactSummaryTable", 1)[0]
    fields_block = impact_table.split("fields = (", 1)[1].split(")", 1)[0]
    assert fields_block.rstrip().endswith("'actions',")
    summary_table = tables.split("class CutoverImpactSummaryTable", 1)[1]
    summary_fields_block = summary_table.split("fields = (", 1)[1].split(")", 1)[0]
    assert summary_fields_block.rstrip().endswith("'actions',")
    assert summary_fields_block.index("'service_site_a'") < summary_fields_block.index("'actions',")
    assert summary_fields_block.index("'service_site_z'") < summary_fields_block.index("'actions',")
    assert "secondary_cutovers" not in impact_table
    assert "其他关联割接" not in impact_table

    assert "class CutoverImpactFilterSet(NetBoxModelFilterSet):" in filtersets
    cutover_filterset = filtersets.split("class CutoverImpactFilterSet", 1)[1]
    assert "secondary_cutovers" not in cutover_filterset
    assert "其他关联割接" not in cutover_filterset
    assert "service_interruption_time_after" in filtersets
    assert "service_interruption_time_before" in filtersets
    assert "service_recovery_time" in filtersets

    assert "class CutoverImpactSerializer(NetBoxModelSerializer):" in serializers
    cutover_serializer = serializers.split("class CutoverImpactSerializer", 1)[1]
    assert "secondary_cutovers" not in cutover_serializer
    assert "class CutoverImpactViewSet(NetBoxModelViewSet):" in api_views
    assert "router.register('cutover-impacts', views.CutoverImpactViewSet)" in api_urls

    assert "path('cutover-impacts/', views.CutoverImpactListView.as_view(), name='cutoverimpact_list')" in urls
    assert "path('cutover-impacts/<int:pk>/changelog/', ObjectChangeLogView.as_view(), name='cutoverimpact_changelog'" in urls

    assert "{% load render_table from django_tables2 %}" in detail_template
    assert '<div class="row mb-3">' in detail_template
    assert '<div class="col col-md-12">' in detail_template
    assert "影响业务" in detail_template
    assert "card-actions" in detail_template
    assert "cutoverimpact_add" in detail_template
    assert 'class="btn btn-ghost-primary btn-sm"' in detail_template
    assert "增加一个影响的业务" in detail_template
    assert '<div class="impacts-table-container">' in detail_template
    assert "{% render_table impacts_table %}" in detail_template
    cutover_impact_panel = detail_template.split("{# 割接影响业务面板 #}", 1)[1].split("{% endblock %}", 1)[0]
    assert "impact-page" not in cutover_impact_panel
    assert "impact-per_page" not in cutover_impact_panel
    assert "card-footer" not in cutover_impact_panel
    assert "impacts_count" not in cutover_impact_panel
    assert "secondary_cutovers" not in impact_template
    assert "其他关联割接" not in impact_template
    assert "id_circuit_special_line_name" in edit_template
    assert "tomselect.settings.sortField = [{ field: '$order' }];" in edit_template
    assert ".filter((option) => option.value !== '')" in edit_template
    assert "if (!service.service_group || seen.has(service.service_group))" in edit_template

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "netbox_otnfaults"
EXTENSION_PATH = PACKAGE_ROOT / "template_content.py"
VIEWS_PATH = PACKAGE_ROOT / "views.py"
URLS_PATH = PACKAGE_ROOT / "urls.py"
TEMPLATE_PATH = (
    PACKAGE_ROOT
    / "templates"
    / "netbox_otnfaults"
    / "inc"
    / "contract_otn_faults.html"
)


def test_contract_fault_query_filters_occurrence_date_inclusively():
    source = EXTENSION_PATH.read_text(encoding="utf-8-sig")

    assert "parse_date(" in source
    assert "request.GET.get('fault_occurrence_time_after', '')" in source
    assert "request.GET.get('fault_occurrence_time_before', '')" in source
    assert "fault_occurrence_time__date__gte=fault_start_date" in source
    assert "fault_occurrence_time__date__lte=fault_end_date" in source
    assert "request.GET.getlist('fault_tag')" in source
    assert "faults_qs.filter(tags__pk__in=fault_tag_ids).distinct()" in source
    assert "'fault_start_date': fault_start_date" in source
    assert "'fault_end_date': fault_end_date" in source
    assert "'fault_tag_ids': fault_tag_ids" in source


def test_contract_fault_query_is_permission_scoped_and_avoids_unused_work():
    source = EXTENSION_PATH.read_text(encoding="utf-8-sig")

    assert "OtnFault.objects.restrict(request.user, 'view')" in source
    assert ".select_related('duty_officer')" in source
    assert ".prefetch_related('tags')" in source
    assert "faults_qs.count()" not in source
    assert "prefetch_related(\n            'interruption_location_a'" not in source


def test_lightweight_contract_fault_fragment_endpoint_is_registered():
    views = VIEWS_PATH.read_text(encoding="utf-8-sig")
    urls = URLS_PATH.read_text(encoding="utf-8-sig")

    assert "class ContractOtnFaultFragmentView(PermissionRequiredMixin, View):" in views
    assert "permission_required = 'netbox_otnfaults.view_otnfault'" in views
    assert "build_contract_fault_context(request, contract_id)" in views
    assert "'netbox_otnfaults/inc/contract_otn_faults.html'" in views
    assert "'contract-faults/<int:contract_id>/'" in urls
    assert "name='contract_faults_fragment'" in urls


def test_contract_fault_card_clears_filter_through_fragment_endpoint():
    template = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

    assert "fault_start_date or fault_end_date or fault_tag_ids" in template
    assert "fault_start_date|date:" in template
    assert "fault_tag_ids" in template
    assert "\u5339\u914d\u4ed8\u6b3e\u6807\u7b7e" in template
    assert "fault_end_date|date:" in template
    assert "contract_faults_fragment" in template
    assert 'hx-get="{{ contract_faults_url }}"' in template
    assert 'hx-target="#contract_otn_faults"' in template
    assert 'hx-select="#contract_otn_faults"' not in template
    assert 'hx-swap="outerHTML"' in template
    assert 'hx-push-url="false"' in template
    assert "request.path" not in template
    assert "mdi-filter-remove-outline" in template
    assert "\u6e05\u9664\u6545\u969c\u7b5b\u9009" in template

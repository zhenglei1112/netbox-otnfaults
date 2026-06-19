from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"


def test_service_statistics_sorts_bare_fiber_before_circuit_by_count_then_name() -> None:
    source = VIEWS_PATH.read_text(encoding="utf-8")

    assert "svc_sort_rank = 0" in source
    assert "svc_sort_rank = 1" in source
    assert "svc_sort_rank = 2" not in source
    assert "'sort_rank': svc_sort_rank" in source
    assert "services_result.sort(key=lambda x: (x['sort_rank'], -x['count'], x['name']))" in source
    assert "result.pop('sort_rank', None)" in source
    assert "services_result.sort(key=lambda x: x['count'], reverse=True)" not in source


def test_service_statistics_payload_exposes_group_label_for_bare_fiber_and_circuit() -> None:
    source = VIEWS_PATH.read_text(encoding="utf-8")

    assert "'bare_fiber_service__tenant_group'" in source
    assert "svc_group_label = imp.bare_fiber_service.tenant_group.name if imp.bare_fiber_service.tenant_group else '未分组'" in source
    assert "svc_group_label = imp.circuit_service.get_business_category_display() if imp.circuit_service.business_category else '未分组'" in source
    assert "'group_label': svc_group_label" in source
    assert "'group_label': stats['group_label']" in source


def test_service_statistics_initializes_all_bare_fiber_services_only_when_requested() -> None:
    source = VIEWS_PATH.read_text(encoding="utf-8")

    assert "BareFiberService" in source
    assert "dict(ServiceTypeChoices.CHOICES)" not in source
    assert "include_all_bare_fiber: bool = request.GET.get('include_all_bare_fiber') == '1'" in source
    conditional_block = source.split("if include_all_bare_fiber:", 1)[1].split(
        "# 遍历 impacts 填充受到故障影响的业务卡片",
        1,
    )[0]
    assert "BareFiberService.objects.select_related('tenant_group').order_by('name')" in source
    assert "for service in all_bare_fiber_services:" in conditional_block
    assert "statistics_bf_ids = affected_bf_ids | {service.pk for service in all_bare_fiber_services}" in source
    assert "bare_fiber_service_id__in=statistics_bf_ids" in source
    assert "circuit_service_id__in=affected_cs_ids" in source
    assert "svc_key = f'bf_{service.pk}'" in source
    assert "'has_current_period_faults': False" in source
    assert "stats['has_current_period_faults'] = True" in source
    assert "'has_current_period_faults': stats['has_current_period_faults']" in source

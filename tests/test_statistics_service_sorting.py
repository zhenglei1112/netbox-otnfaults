from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"


def test_service_statistics_sorts_bare_fiber_before_circuit_by_count_then_name() -> None:
    source = VIEWS_PATH.read_text(encoding="utf-8")

    assert "svc_sort_rank = 0" in source
    assert "svc_sort_rank = 1" in source
    assert "svc_sort_rank = 2" in source
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


def test_service_statistics_initializes_all_bare_fiber_services() -> None:
    source = VIEWS_PATH.read_text(encoding="utf-8")

    assert "BareFiberService" in source
    assert "dict(ServiceTypeChoices.CHOICES)" not in source
    assert "for service in BareFiberService.objects.select_related('tenant_group').order_by('name')" in source
    assert "svc_key = f'bf_{service.pk}'" in source
    assert "'has_current_period_faults': False" in source
    assert "stats['has_current_period_faults'] = True" in source
    assert "'has_current_period_faults': stats['has_current_period_faults']" in source

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

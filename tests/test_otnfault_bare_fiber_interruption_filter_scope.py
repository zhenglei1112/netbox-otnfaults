from pathlib import Path


FILTERSETS_PATH = (
    Path(__file__).resolve().parents[1] / "netbox_otnfaults" / "filtersets.py"
)


def test_bare_fiber_interruption_method_is_scoped_to_fault_filterset() -> None:
    source = FILTERSETS_PATH.read_text(encoding="utf-8-sig")

    assert source.count("def filter_caused_bare_fiber_interruption") == 1

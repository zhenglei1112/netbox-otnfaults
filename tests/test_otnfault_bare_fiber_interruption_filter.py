from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"


def _class_block(source: str, class_name: str, next_class_name: str) -> str:
    return source.split(f"class {class_name}", 1)[1].split(
        f"class {next_class_name}", 1
    )[0]


def test_fault_filterset_defines_bare_fiber_interruption_boolean_filter() -> None:
    source = FILTERSETS_PATH.read_text(encoding="utf-8-sig")
    filterset = _class_block(source, "OtnFaultFilterSet", "OtnFaultImpactFilterSet")

    assert "from django.db.models import Exists, OuterRef" in source
    assert "ServiceTypeChoices" in source
    assert "BusinessImpactChoices" in source
    assert "caused_bare_fiber_interruption = django_filters.BooleanFilter(" in filterset
    assert "method='filter_caused_bare_fiber_interruption'" in filterset
    assert "label='造成裸纤业务中断'" in filterset
    assert "'caused_bare_fiber_interruption'" in filterset


def test_fault_filterset_uses_exists_for_positive_and_negative_filtering() -> None:
    source = FILTERSETS_PATH.read_text(encoding="utf-8-sig")
    filterset = _class_block(source, "OtnFaultFilterSet", "OtnFaultImpactFilterSet")
    method = filterset.split(
        "def filter_caused_bare_fiber_interruption", 1
    )[1].split("\n    def ", 1)[0]

    assert "if value is None:" in method
    assert "return queryset" in method
    assert "OtnFaultImpact.objects.filter(" in method
    assert "otn_fault_id=OuterRef('pk')" in method
    assert "service_type=ServiceTypeChoices.BARE_FIBER" in method
    assert "business_impact=BusinessImpactChoices.INTERRUPTED" in method
    assert "if value:" in method
    assert "return queryset.filter(Exists(matching_impacts))" in method
    assert "return queryset.filter(~Exists(matching_impacts))" in method


def test_fault_filter_form_places_bare_fiber_interruption_between_times() -> None:
    source = FORMS_PATH.read_text(encoding="utf-8-sig")
    form = _class_block(source, "OtnFaultFilterForm", "OtnFaultImpactFilterForm")

    assert "caused_bare_fiber_interruption = forms.NullBooleanField(" in form
    assert "label='造成裸纤业务中断'" in form
    assert "(True, '是')" in form
    assert "(False, '否')" in form

    fieldset = form.split("fieldsets = (", 1)[1].split("duty_officer =", 1)[0]
    start_time_position = fieldset.index("'fault_occurrence_time_before'")
    interruption_position = fieldset.index("'caused_bare_fiber_interruption'")
    dispatch_time_position = fieldset.index("'dispatch_time'")

    assert start_time_position < interruption_position < dispatch_time_position

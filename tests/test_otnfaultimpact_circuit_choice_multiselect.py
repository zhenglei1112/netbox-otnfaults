from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"


class OtnFaultImpactCircuitChoiceMultiSelectSourceTestCase(unittest.TestCase):
    def test_filter_form_uses_multi_select_choice_fields(self) -> None:
        forms_text = FORMS_PATH.read_text(encoding="utf-8")
        filter_form_text = forms_text.split("class OtnFaultImpactFilterForm", 1)[1].split("class OtnPathForm", 1)[0]

        self.assertIn("circuit_business_category = forms.MultipleChoiceField(", filter_form_text)
        self.assertIn("label='业务门类'", filter_form_text)
        self.assertIn("circuit_service_group = forms.MultipleChoiceField(", filter_form_text)
        self.assertIn("label='业务组'", filter_form_text)
        self.assertIn("widget=forms.SelectMultiple", filter_form_text)

    def test_filterset_uses_multi_choice_filters_for_related_circuit_fields(self) -> None:
        filtersets_text = FILTERSETS_PATH.read_text(encoding="utf-8")

        self.assertIn("circuit_business_category = django_filters.MultipleChoiceFilter(", filtersets_text)
        self.assertIn("field_name='circuit_service__business_category'", filtersets_text)
        self.assertIn("circuit_service_group = django_filters.MultipleChoiceFilter(", filtersets_text)
        self.assertIn("field_name='circuit_service__service_group'", filtersets_text)
        self.assertIn("distinct=True", filtersets_text)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_list.html"
)


class OtnFaultListTimeFiltersSourceTestCase(unittest.TestCase):
    def test_filter_form_uses_start_end_occurrence_fields(self) -> None:
        forms_text = FORMS_PATH.read_text(encoding="utf-8")
        filter_form_text = forms_text.split("class OtnFaultFilterForm", 1)[1].split("class OtnFaultImpactFilterForm", 1)[0]

        self.assertIn("fault_occurrence_time_after = forms.DateTimeField(", filter_form_text)
        self.assertIn("label='故障起始时间（开始）'", filter_form_text)
        self.assertIn("fault_occurrence_time_before = forms.DateTimeField(", filter_form_text)
        self.assertIn("label='故障起始时间（结束）'", filter_form_text)
        self.assertNotIn("fault_occurrence_time = forms.DateTimeField(", filter_form_text)
        self.assertIn("'fault_occurrence_time_after', 'fault_occurrence_time_before',", filter_form_text)
        self.assertNotIn("'fault_occurrence_time', 'dispatch_time', 'departure_time', 'arrival_time', 'fault_recovery_time',", filter_form_text)

    def test_filterset_applies_occurrence_time_range(self) -> None:
        filtersets_text = FILTERSETS_PATH.read_text(encoding="utf-8")

        self.assertIn("fault_occurrence_time_after = django_filters.DateTimeFilter(", filtersets_text)
        self.assertIn("field_name='fault_occurrence_time', lookup_expr='gte'", filtersets_text)
        self.assertIn("fault_occurrence_time_before = django_filters.DateTimeFilter(", filtersets_text)
        self.assertIn("field_name='fault_occurrence_time', lookup_expr='lte'", filtersets_text)
        self.assertNotIn("'fault_occurrence_time', 'fault_recovery_time', 'fault_category',", filtersets_text)

    def test_list_template_contains_last_week_and_last_month_shortcuts(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("data-range=\"last-week\"", template_text)
        self.assertIn(">上周<", template_text)
        self.assertIn("data-range=\"last-month\"", template_text)
        self.assertIn(">上月<", template_text)
        self.assertIn("data-range=\"this-week\"", template_text)
        self.assertIn("data-range=\"this-month\"", template_text)
        self.assertIn("data-range=\"this-year\"", template_text)
        self.assertIn("data-range=\"last-7-days\"", template_text)
        self.assertIn("data-range=\"last-30-days\"", template_text)
        self.assertIn("name=\"fault_occurrence_time_after\"", template_text)
        self.assertIn("name=\"fault_occurrence_time_before\"", template_text)
        self.assertIn("otnfault-date-range-row", template_text)
        self.assertIn("otnfault-date-range-content", template_text)
        self.assertIn("otnfault-date-range-field", template_text)
        self.assertIn("otnfault-date-shortcuts-row", template_text)
        self.assertIn("otnfault-date-shortcuts-content", template_text)
        self.assertIn("btn-group btn-group-sm otnfault-date-shortcuts", template_text)
        self.assertIn("labelElement.textContent = '故障起始时间';", template_text)
        self.assertIn(".otnfault-date-shortcuts .btn:last-child {", template_text)
        self.assertIn("shortcutsContent.appendChild(shortcuts);", template_text)
        self.assertNotIn("form.submit();", template_text)
        self.assertIn("button.classList.remove('btn-primary', 'active');", template_text)
        self.assertIn("button.classList.add('btn-outline-primary');", template_text)
        self.assertIn("activeButton.classList.remove('btn-outline-primary');", template_text)
        self.assertIn("activeButton.classList.add('btn-primary', 'active');", template_text)


if __name__ == "__main__":
    unittest.main()

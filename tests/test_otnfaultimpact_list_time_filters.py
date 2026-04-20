from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfaultimpact_list.html"
)
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"


class OtnFaultImpactListTimeFiltersSourceTestCase(unittest.TestCase):
    def test_filter_form_uses_start_end_service_interruption_fields(self) -> None:
        forms_text = FORMS_PATH.read_text(encoding="utf-8")
        filter_form_text = forms_text.split("class OtnFaultImpactFilterForm", 1)[1].split("class OtnPathForm", 1)[0]

        self.assertIn("service_interruption_time_after = forms.DateTimeField(", filter_form_text)
        self.assertIn("label='业务故障时间（开始）'", filter_form_text)
        self.assertIn("service_interruption_time_before = forms.DateTimeField(", filter_form_text)
        self.assertIn("label='业务故障时间（结束）'", filter_form_text)
        self.assertNotIn("service_interruption_time = forms.DateTimeField(", filter_form_text)

    def test_filterset_applies_service_interruption_time_range(self) -> None:
        filtersets_text = FILTERSETS_PATH.read_text(encoding="utf-8")

        self.assertIn("service_interruption_time_after = django_filters.DateTimeFilter(", filtersets_text)
        self.assertIn("field_name='service_interruption_time', lookup_expr='gte'", filtersets_text)
        self.assertIn("service_interruption_time_before = django_filters.DateTimeFilter(", filtersets_text)
        self.assertIn("field_name='service_interruption_time', lookup_expr='lte'", filtersets_text)
        self.assertNotIn("'service_interruption_time',\n            'service_recovery_time',", filtersets_text)

    def test_list_view_uses_custom_template_for_shortcuts(self) -> None:
        views_text = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("class OtnFaultImpactListView(ExcelFriendlyCSVExportMixin, generic.ObjectListView):", views_text)
        self.assertIn("template_name = 'netbox_otnfaults/otnfaultimpact_list.html'", views_text)

    def test_list_template_contains_matching_shortcuts_ui(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("aria-label=\"业务故障时间快捷选择\"", template_text)
        self.assertIn("data-range=\"last-week\"", template_text)
        self.assertIn(">上周<", template_text)
        self.assertIn("data-range=\"last-month\"", template_text)
        self.assertIn(">上月<", template_text)
        self.assertIn("data-range=\"this-week\"", template_text)
        self.assertIn("data-range=\"this-month\"", template_text)
        self.assertIn("data-range=\"this-year\"", template_text)
        self.assertIn("data-range=\"last-7-days\"", template_text)
        self.assertIn("data-range=\"last-30-days\"", template_text)
        self.assertIn("name=\"service_interruption_time_after\"", template_text)
        self.assertIn("name=\"service_interruption_time_before\"", template_text)
        self.assertIn("labelElement.textContent = '业务故障时间';", template_text)
        self.assertIn("shortcutsContent.appendChild(shortcuts);", template_text)
        self.assertIn("button.classList.remove('btn-primary', 'active');", template_text)
        self.assertIn("activeButton.classList.add('btn-primary', 'active');", template_text)


if __name__ == "__main__":
    unittest.main()

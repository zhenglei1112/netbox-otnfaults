import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CUTOVER_EDIT_TEMPLATE = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "cutovertask_edit.html"
)
CUTOVER_FORMS = REPO_ROOT / "netbox_otnfaults" / "forms.py"


class CutoverEditTemplateTestCase(unittest.TestCase):
    def test_customer_approval_detail_is_hidden_not_rendered_as_json_field(self) -> None:
        template = CUTOVER_EDIT_TEMPLATE.read_text(encoding="utf-8")

        self.assertNotIn("{% render_field form.customer_approval_detail %}", template)
        self.assertIn("{{ form.customer_approval_detail.as_hidden }}", template)

    def test_cutover_task_multiline_fields_render_as_two_rows(self) -> None:
        forms = CUTOVER_FORMS.read_text(encoding="utf-8")
        form_source = forms.split("class CutoverTaskForm(NetBoxModelForm):", 1)[1].split(
            "class CutoverTaskFilterForm", 1
        )[0]

        expected_fields = (
            "planned_cutover_times",
            "related_customers",
            "cutover_reason",
            "customer_approval_detail",
            "timeout_reason",
            "remaining_issues",
            "rectification_description",
            "rectification_completion_description",
        )

        self.assertIn("cutover_two_row_fields = (", form_source)
        for field_name in expected_fields:
            self.assertIn(f"'{field_name}'", form_source)
        self.assertIn("cutover_one_row_fields = (", form_source)
        self.assertIn("'cutover_location'", form_source.split("cutover_one_row_fields = (", 1)[1].split(")", 1)[0])
        self.assertNotIn("'cutover_location'", form_source.split("cutover_two_row_fields = (", 1)[1].split(")", 1)[0])
        self.assertNotIn("'comments'", form_source.split("cutover_two_row_fields = (", 1)[1].split(")", 1)[0])
        self.assertIn("self.fields[field_name].widget.attrs['rows'] = 1", form_source)
        self.assertIn("self.fields[field_name].widget.attrs['rows'] = 2", form_source)

    def test_cutover_contract_is_filtered_by_handling_unit(self) -> None:
        forms = CUTOVER_FORMS.read_text(encoding="utf-8")
        form_source = forms.split("class CutoverTaskForm(NetBoxModelForm):", 1)[1].split(
            "class CutoverTaskFilterForm", 1
        )[0]
        contract_field = form_source.split("contract = DynamicModelChoiceField(", 1)[1].split(
            "line_supervisor = DynamicModelChoiceField", 1
        )[0]

        self.assertIn("query_params={", contract_field)
        self.assertIn("'external_party_object': '$handling_unit'", contract_field)


if __name__ == "__main__":
    unittest.main()

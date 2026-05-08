import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
SERIALIZERS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "serializers.py"
EDIT_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_edit.html"
DETAIL_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _parse(path: Path) -> ast.Module:
    return ast.parse(_read(path))


def _find_class(module: ast.Module, class_name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"Class {class_name} not found")


def _find_meta_tuple(class_node: ast.ClassDef, tuple_name: str) -> list[str]:
    meta_class = next(
        node for node in class_node.body if isinstance(node, ast.ClassDef) and node.name == "Meta"
    )
    for node in meta_class.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == tuple_name:
                    if not isinstance(node.value, (ast.Tuple, ast.List)):
                        raise AssertionError(f"Meta.{tuple_name} is not a tuple/list")
                    return [
                        elt.value
                        for elt in node.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    ]
    raise AssertionError(f"Meta.{tuple_name} not found in {class_node.name}")


class OtnFaultCutoverReportFieldsSourceTestCase(unittest.TestCase):
    def test_model_defines_cutover_report_choice_and_time_fields(self) -> None:
        models_text = _read(MODELS_PATH)

        self.assertIn("class CutoverReportStatusChoices(ChoiceSet):", models_text)
        self.assertIn("UNREPORTED = 'unreported'", models_text)
        self.assertIn("REPORTED = 'reported'", models_text)
        self.assertIn("(UNREPORTED, '未报备'", models_text)
        self.assertIn("(REPORTED, '已报备'", models_text)
        self.assertIn("cutover_report_status = models.CharField", models_text)
        self.assertIn("verbose_name='割接报备情况'", models_text)
        self.assertIn("cutover_report_time = models.DateTimeField", models_text)
        self.assertIn("verbose_name='报备时间'", models_text)

    def test_forms_tables_filtersets_and_serializer_expose_fields(self) -> None:
        field_names = ["cutover_report_status", "cutover_report_time"]

        forms_text = _read(FORMS_PATH)
        form_block = forms_text.split("class OtnFaultForm", 1)[1].split("class OtnFaultImportForm", 1)[0]
        filter_form_block = forms_text.split("class OtnFaultFilterForm", 1)[1].split("class OtnFaultImpactFilterForm", 1)[0]
        for field_name in field_names:
            self.assertIn(field_name, form_block)
            self.assertIn(field_name, filter_form_block)

        table_class = _find_class(_parse(TABLES_PATH), "OtnFaultTable")
        table_fields = _find_meta_tuple(table_class, "fields")
        detail_index = table_fields.index("interruption_reason_detail")
        self.assertEqual(table_fields[detail_index + 1:detail_index + 3], field_names)

        filterset_text = _read(FILTERSETS_PATH)
        serializer_text = _read(SERIALIZERS_PATH)
        for field_name in field_names:
            self.assertIn(field_name, filterset_text)
            self.assertIn(field_name, serializer_text)

    def test_edit_template_places_fields_after_detail_reason_and_toggles_conditionally(self) -> None:
        template_text = _read(EDIT_TEMPLATE_PATH)

        detail_marker = "{% render_field form.interruption_reason_detail %}"
        status_marker = "{% render_field form.cutover_report_status %}"
        time_marker = "{% render_field form.cutover_report_time %}"
        duty_marker = "{% render_field form.duty_officer %}"

        self.assertLess(template_text.index(detail_marker), template_text.index(status_marker))
        self.assertLess(template_text.index(status_marker), template_text.index(time_marker))
        self.assertLess(template_text.index(time_marker), template_text.index(duty_marker))
        self.assertIn("data-cutover-report-only", template_text)
        self.assertIn("POWER_RECTIFICATION_REASON = 'power_equipment_rectification'", template_text)
        self.assertIn("toggleCutoverReportFields", template_text)

    def test_detail_template_places_fields_after_fault_reason_and_toggles_conditionally(self) -> None:
        template_text = _read(DETAIL_TEMPLATE_PATH)

        reason_marker = "{{ object.get_interruption_reason_detail_display|default:"
        status_marker = "{{ object.get_cutover_report_status_display|default:"
        time_marker = "{{ object.cutover_report_time|date:"
        duty_marker = "值守人员"

        self.assertLess(template_text.index(reason_marker), template_text.index(status_marker))
        self.assertLess(template_text.index(status_marker), template_text.index(time_marker))
        self.assertLess(template_text.index(time_marker), template_text.index(duty_marker))
        self.assertIn("object.fault_category == 'power_fault'", template_text)
        self.assertIn("object.interruption_reason == 'power_equipment_rectification'", template_text)


if __name__ == "__main__":
    unittest.main()

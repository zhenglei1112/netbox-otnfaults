import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
SERIALIZERS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "serializers.py"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_edit.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _parse(path: Path) -> ast.Module:
    return ast.parse(_read(path))


def _find_class(module: ast.Module, class_name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"Class {class_name} not found")


def _string_tuple_items(node: ast.AST) -> list[str]:
    if not isinstance(node, (ast.Tuple, ast.List)):
        raise AssertionError("Expected tuple/list")
    return [
        elt.value
        for elt in node.elts
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
    ]


def _find_meta_tuple(class_node: ast.ClassDef, tuple_name: str) -> list[str]:
    meta_class = next(
        node for node in class_node.body if isinstance(node, ast.ClassDef) and node.name == "Meta"
    )
    for node in meta_class.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == tuple_name:
                    return _string_tuple_items(node.value)
    raise AssertionError(f"Meta.{tuple_name} not found in {class_node.name}")


class OtnFaultPowerFaultFieldsSourceTestCase(unittest.TestCase):
    def test_choice_sets_define_required_options(self) -> None:
        models_text = _read(MODELS_PATH)

        phenomenon_block = models_text.split("class PowerFaultPhenomenonChoices", 1)[1].split("class ", 1)[0]
        impact_block = models_text.split("class PowerFaultImpactChoices", 1)[1].split("class ", 1)[0]

        self.assertIn("ALL_INTERRUPTED = 'all_interrupted'", phenomenon_block)
        self.assertIn("PARTIAL_INTERRUPTED = 'partial_interrupted'", phenomenon_block)
        self.assertIn("(ALL_INTERRUPTED, '全中断'", phenomenon_block)
        self.assertIn("(PARTIAL_INTERRUPTED, '部分中断'", phenomenon_block)
        self.assertIn("HOSTED = 'hosted'", impact_block)
        self.assertIn("NOT_HOSTED = 'not_hosted'", impact_block)
        self.assertIn("(HOSTED, '设备托管'", impact_block)
        self.assertIn("(NOT_HOSTED, '设备未托管'", impact_block)

    def test_model_form_filter_table_and_serializer_include_fields(self) -> None:
        field_names = ["power_fault_phenomenon", "power_fault_impact"]

        models_text = _read(MODELS_PATH)
        for field_name in field_names:
            self.assertIn(f"{field_name} = models.CharField", models_text)

        forms_text = _read(FORMS_PATH)
        form_block = forms_text.split("class OtnFaultForm", 1)[1].split("class OtnFaultImportForm", 1)[0]
        filter_form_block = forms_text.split("class OtnFaultFilterForm", 1)[1].split("class OtnFaultImpactFilterForm", 1)[0]
        for field_name in field_names:
            self.assertIn(field_name, form_block)
            self.assertIn(field_name, filter_form_block)

        tables_module = _parse(TABLES_PATH)
        table_class = _find_class(tables_module, "OtnFaultTable")
        fields = _find_meta_tuple(table_class, "fields")
        fault_category_index = fields.index("fault_category")
        self.assertEqual(fields[fault_category_index + 1:fault_category_index + 3], field_names)

        filterset_text = _read(FILTERSETS_PATH)
        serializer_text = _read(SERIALIZERS_PATH)
        for field_name in field_names:
            self.assertIn(field_name, filterset_text)
            self.assertIn(field_name, serializer_text)

    def test_edit_template_places_fields_after_category_and_hides_with_power_group(self) -> None:
        template_text = _read(TEMPLATE_PATH)

        category_marker = "{% render_field form.fault_category %}"
        phenomenon_marker = "{% render_field form.power_fault_phenomenon %}"
        impact_marker = "{% render_field form.power_fault_impact %}"
        status_marker = "{% render_field form.fault_status %}"

        self.assertLess(template_text.index(category_marker), template_text.index(phenomenon_marker))
        self.assertLess(template_text.index(phenomenon_marker), template_text.index(impact_marker))
        self.assertLess(template_text.index(impact_marker), template_text.index(status_marker))
        self.assertIn("data-power-fault-only", template_text)
        self.assertIn("querySelectorAll('[data-power-fault-only]')", template_text)


if __name__ == "__main__":
    unittest.main()

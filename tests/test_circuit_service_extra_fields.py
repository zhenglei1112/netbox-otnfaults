import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
SERIALIZERS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "serializers.py"
DETAIL_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "circuitservice.html"


EXPECTED_EXTRA_KEYS = [
    "request_number",
    "request_attachment",
    "configuration_completed_date",
    "configuration_person",
    "service_test_start_date",
    "service_open_time",
    "opening_order_attachment",
    "service_test_end_time",
    "service_end_time",
    "resource_recycle_time",
    "resource_recycle_person",
    "change_number",
    "change_date",
    "change_person",
    "change_order_attachment",
    "interconnection_info",
    "carrier_system",
    "contracting_party",
    "customer_object",
    "customer_a_end",
    "trunk_a_site",
    "trunk_a_site_attribute",
    "trunk_a_ne",
    "trunk_a_board",
    "trunk_a_port",
    "customer_z_end",
    "trunk_z_site",
    "trunk_z_site_attribute",
    "trunk_z_ne",
    "trunk_z_board",
    "trunk_z_port",
    "charge_attribute",
    "sales_person",
    "contract_open_time",
    "contract_end_time",
    "contract_number",
    "contract_name",
    "project_approval_number",
    "project_name",
    "execution_exception",
    "execution_exception_reason",
]


def _parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"))


def _find_class(module: ast.Module, class_name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"Class {class_name} not found")


def _find_assignment(class_node: ast.ClassDef, target_name: str) -> ast.AST:
    for node in class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == target_name:
                    return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == target_name:
            return node.value
    raise AssertionError(f"Assignment {target_name} not found in {class_node.name}")


def _find_meta_tuple(class_node: ast.ClassDef, field_name: str) -> None:
    meta_class = _find_class(ast.Module(body=class_node.body, type_ignores=[]), "Meta")
    value = _find_assignment(meta_class, "fields")
    if not isinstance(value, (ast.Tuple, ast.List)):
        raise AssertionError(f"{class_node.name}.Meta.fields is not a tuple/list")
    items = [elt.value for elt in value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
    if field_name not in items:
        raise AssertionError(f"{field_name} not found in {class_node.name}.Meta.fields")


class CircuitServiceExtraFieldsSourceTestCase(unittest.TestCase):
    def test_model_declares_json_field_and_ordered_definitions(self) -> None:
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "CircuitService")

        definitions = _find_assignment(class_node, "EXTRA_FIELD_DEFINITIONS")
        self.assertIsInstance(definitions, (ast.Tuple, ast.List))
        keys = []
        for item in definitions.elts:
            self.assertIsInstance(item, (ast.Tuple, ast.List))
            self.assertEqual(len(item.elts), 2)
            key_node, label_node = item.elts
            self.assertIsInstance(key_node, ast.Constant)
            self.assertIsInstance(label_node, ast.Constant)
            self.assertIsInstance(key_node.value, str)
            self.assertIsInstance(label_node.value, str)
            keys.append(key_node.value)
        self.assertEqual(keys, EXPECTED_EXTRA_KEYS)

        value = _find_assignment(class_node, "extra_fields")
        self.assertIsInstance(value, ast.Call)
        self.assertIsInstance(value.func, ast.Attribute)
        self.assertEqual(value.func.attr, "JSONField")

        keyword_names = {kw.arg for kw in value.keywords}
        self.assertIn("default", keyword_names)
        self.assertIn("blank", keyword_names)
        self.assertIn("verbose_name", keyword_names)

    def test_forms_split_extra_fields_for_editing(self) -> None:
        forms_text = FORMS_PATH.read_text(encoding="utf-8-sig")
        circuit_form_text = forms_text[
            forms_text.index("class CircuitServiceForm"):
            forms_text.index("class CircuitServiceFilterForm")
        ]
        module = _parse_module(FORMS_PATH)
        form_class = _find_class(module, "CircuitServiceForm")

        _find_meta_tuple(form_class, "extra_fields")
        self.assertIn("EXTRA_FIELD_PREFIX", forms_text)
        self.assertIn("CircuitService.EXTRA_FIELD_DEFINITIONS", forms_text)
        self.assertIn("def _init_extra_field_inputs", circuit_form_text)
        self.assertIn("def clean_extra_fields", circuit_form_text)
        self.assertIn("def clean(self) -> dict[str, Any]", circuit_form_text)
        self.assertIn("cleaned_data = getattr(self, 'cleaned_data', None) or {}", circuit_form_text)
        self.assertIn("f'{self.EXTRA_FIELD_PREFIX}{key}'", circuit_form_text)
        self.assertNotIn("    EXTRA_FIELD_FIELD_NAMES = tuple(", forms_text)

    def test_serializer_and_detail_template_expose_extra_fields(self) -> None:
        serializers_module = _parse_module(SERIALIZERS_PATH)
        serializer_class = _find_class(serializers_module, "CircuitServiceSerializer")
        _find_meta_tuple(serializer_class, "extra_fields")

        template_text = DETAIL_TEMPLATE_PATH.read_text(encoding="utf-8-sig")
        self.assertIn("扩展信息", template_text)
        self.assertIn("object.extra_field_items", template_text)
        self.assertIn("extra_field.label", template_text)
        self.assertIn("extra_field.value", template_text)


if __name__ == "__main__":
    unittest.main()

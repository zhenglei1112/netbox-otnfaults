import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"
SERIALIZERS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "serializers.py"


def _parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


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


def _find_meta_tuple(class_node: ast.ClassDef, field_name: str, attr_name: str = "fields") -> None:
    meta_class = _find_class(ast.Module(body=class_node.body, type_ignores=[]), "Meta")
    value = _find_assignment(meta_class, attr_name)
    if not isinstance(value, (ast.Tuple, ast.List)):
        raise AssertionError(f"{class_node.name}.Meta.{attr_name} is not a tuple/list")
    items = [elt.value for elt in value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
    if field_name not in items:
        raise AssertionError(f"{field_name} not found in {class_node.name}.Meta.{attr_name}")


class CircuitServiceExternalBusinessSourceTestCase(unittest.TestCase):
    def test_model_declares_boolean_field_with_false_default(self) -> None:
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "CircuitService")
        value = _find_assignment(class_node, "is_external_business")

        self.assertIsInstance(value, ast.Call)
        self.assertIsInstance(value.func, ast.Attribute)
        self.assertEqual(value.func.attr, "BooleanField")

        keyword_names = {kw.arg for kw in value.keywords}
        self.assertIn("default", keyword_names)
        self.assertIn("verbose_name", keyword_names)

        default_kw = next(kw for kw in value.keywords if kw.arg == "default")
        verbose_kw = next(kw for kw in value.keywords if kw.arg == "verbose_name")
        self.assertIs(default_kw.value.value, False)
        self.assertEqual(verbose_kw.value.value, "对外业务")

    def test_forms_include_external_business_field(self) -> None:
        module = _parse_module(FORMS_PATH)

        for class_name in ("CircuitServiceForm", "CircuitServiceImportForm"):
            class_node = _find_class(module, class_name)
            _find_meta_tuple(class_node, "is_external_business")

        bulk_edit_class = _find_class(module, "CircuitServiceBulkEditForm")
        _find_assignment(bulk_edit_class, "is_external_business")

        filter_form_class = _find_class(module, "CircuitServiceFilterForm")
        _find_assignment(filter_form_class, "is_external_business")

    def test_filterset_serializer_and_table_include_external_business(self) -> None:
        filtersets_module = _parse_module(FILTERSETS_PATH)
        filterset_class = _find_class(filtersets_module, "CircuitServiceFilterSet")
        _find_meta_tuple(filterset_class, "is_external_business")

        serializers_module = _parse_module(SERIALIZERS_PATH)
        serializer_class = _find_class(serializers_module, "CircuitServiceSerializer")
        _find_meta_tuple(serializer_class, "is_external_business")

        tables_module = _parse_module(TABLES_PATH)
        table_class = _find_class(tables_module, "CircuitServiceTable")
        _find_meta_tuple(table_class, "is_external_business")
        _find_meta_tuple(table_class, "is_external_business", attr_name="default_columns")


if __name__ == "__main__":
    unittest.main()

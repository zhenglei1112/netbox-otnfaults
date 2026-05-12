import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"


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
    raise AssertionError(f"Assignment {target_name} not found in {class_node.name}")


def _tuple_items(value: ast.AST) -> list[str]:
    if not isinstance(value, (ast.Tuple, ast.List)):
        raise AssertionError("Expected tuple/list")
    return [elt.value for elt in value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]


class OtnFaultListColumnPreferencesSourceTestCase(unittest.TestCase):
    def test_fault_details_available_in_fault_list_column_settings(self) -> None:
        module = _parse_module(TABLES_PATH)
        table_class = _find_class(module, "OtnFaultTable")
        meta_class = _find_class(ast.Module(body=table_class.body, type_ignores=[]), "Meta")

        fields = _tuple_items(_find_assignment(meta_class, "fields"))

        self.assertIn("fault_details", fields)

    def test_power_data_type_available_in_fault_list_column_settings(self) -> None:
        module = _parse_module(TABLES_PATH)
        table_class = _find_class(module, "OtnFaultTable")
        meta_class = _find_class(ast.Module(body=table_class.body, type_ignores=[]), "Meta")

        fields = _tuple_items(_find_assignment(meta_class, "fields"))

        self.assertIn("power_data_type", fields)


if __name__ == "__main__":
    unittest.main()

import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"


def _parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"))


def _find_class(module: ast.Module, class_name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"Class {class_name} not found")


def _find_method(class_node: ast.ClassDef, method_name: str) -> ast.FunctionDef:
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    raise AssertionError(f"Method {method_name} not found in {class_node.name}")


class OtnFaultFaultNumberLocalDateSourceTestCase(unittest.TestCase):
    def test_save_generates_fault_number_from_local_creation_date(self) -> None:
        source = MODELS_PATH.read_text(encoding="utf-8-sig")
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "OtnFault")
        save_node = _find_method(class_node, "save")
        save_source = ast.get_source_segment(source, save_node)

        self.assertIsNotNone(save_source)
        assert save_source is not None

        self.assertIn("timezone.localdate().strftime('%Y%m%d')", save_source)
        self.assertNotIn("timezone.now().strftime('%Y%m%d')", save_source)

    def test_save_generates_fault_number_inside_transaction_with_row_lock(self) -> None:
        source = MODELS_PATH.read_text(encoding="utf-8-sig")
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "OtnFault")
        save_node = _find_method(class_node, "save")
        save_source = ast.get_source_segment(source, save_node)

        self.assertIsNotNone(save_source)
        assert save_source is not None

        self.assertIn("transaction.atomic()", save_source)
        self.assertIn("select_for_update()", save_source)
        self.assertIn("order_by('-fault_number')", save_source)
        self.assertIn(".first()", save_source)
        self.assertNotIn("order_by('fault_number').last()", save_source)

    def test_save_retries_generated_fault_number_after_unique_collision(self) -> None:
        source = MODELS_PATH.read_text(encoding="utf-8-sig")
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "OtnFault")
        save_node = _find_method(class_node, "save")
        save_source = ast.get_source_segment(source, save_node)

        self.assertIsNotNone(save_source)
        assert save_source is not None

        self.assertIn("except IntegrityError", save_source)
        self.assertIn("self.fault_number = ''", save_source)
        self.assertIn("raise", save_source)


if __name__ == "__main__":
    unittest.main()

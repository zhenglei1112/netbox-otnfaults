import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"


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


class OtnFaultFaultCategorySourceTestCase(unittest.TestCase):
    def test_fault_category_is_required_with_fiber_break_default(self) -> None:
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "OtnFault")
        value = _find_assignment(class_node, "fault_category")

        self.assertIsInstance(value, ast.Call)
        self.assertIsInstance(value.func, ast.Attribute)
        self.assertEqual(value.func.attr, "CharField")

        keyword_names = {kw.arg for kw in value.keywords}
        self.assertIn("choices", keyword_names)
        self.assertIn("default", keyword_names)
        self.assertNotIn("blank", keyword_names)
        self.assertNotIn("null", keyword_names)

        choices_kw = next(kw for kw in value.keywords if kw.arg == "choices")
        default_kw = next(kw for kw in value.keywords if kw.arg == "default")

        self.assertIsInstance(choices_kw.value, ast.Name)
        self.assertEqual(choices_kw.value.id, "FaultCategoryChoices")
        self.assertIsInstance(default_kw.value, ast.Attribute)
        self.assertEqual(default_kw.value.value.id, "FaultCategoryChoices")
        self.assertEqual(default_kw.value.attr, "FIBER_BREAK")

    def test_form_sets_create_default_selection_without_overwriting_existing_value(self) -> None:
        forms_text = FORMS_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("if not self.instance.fault_category:", forms_text)
        self.assertIn("self.initial['fault_category'] = FaultCategoryChoices.FIBER_BREAK", forms_text)
        self.assertIn("self.fields['fault_category'].initial = FaultCategoryChoices.FIBER_BREAK", forms_text)


if __name__ == "__main__":
    unittest.main()

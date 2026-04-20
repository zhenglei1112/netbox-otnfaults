import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"


def _parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"))


def _find_class(module: ast.Module, class_name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"Class {class_name} not found")


def _find_assignment(class_node: ast.ClassDef, target_name: str) -> ast.Call:
    for node in class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == target_name:
                    if not isinstance(node.value, ast.Call):
                        raise AssertionError(f"{target_name} is not assigned from a call")
                    return node.value
    raise AssertionError(f"Assignment {target_name} not found in {class_node.name}")


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    raise AssertionError("Unsupported call target")


class OtnFaultImpactFilterMultiSelectSourceTestCase(unittest.TestCase):
    def test_filter_form_uses_multi_select_service_fields(self) -> None:
        module = _parse_module(FORMS_PATH)
        class_node = _find_class(module, "OtnFaultImpactFilterForm")

        bare_fiber_service = _find_assignment(class_node, "bare_fiber_service")
        circuit_service = _find_assignment(class_node, "circuit_service")

        self.assertEqual(_call_name(bare_fiber_service), "DynamicModelMultipleChoiceField")
        self.assertEqual(_call_name(circuit_service), "DynamicModelMultipleChoiceField")

    def test_filterset_uses_multi_value_service_filters(self) -> None:
        module = _parse_module(FILTERSETS_PATH)
        class_node = _find_class(module, "OtnFaultImpactFilterSet")

        bare_fiber_service = _find_assignment(class_node, "bare_fiber_service")
        circuit_service = _find_assignment(class_node, "circuit_service")

        self.assertEqual(_call_name(bare_fiber_service), "ModelMultipleChoiceFilter")
        self.assertEqual(_call_name(circuit_service), "ModelMultipleChoiceFilter")


if __name__ == "__main__":
    unittest.main()

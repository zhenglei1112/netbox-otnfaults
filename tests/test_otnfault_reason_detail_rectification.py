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


def _find_assignment(class_node: ast.ClassDef, target_name: str) -> ast.AST:
    for node in class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == target_name:
                    return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == target_name:
            return node.value
    raise AssertionError(f"Assignment {target_name} not found in {class_node.name}")


class OtnFaultReasonDetailRectificationTestCase(unittest.TestCase):
    def test_cable_rectification_has_planned_and_unplanned_detail_reasons(self) -> None:
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "OtnFault")

        detail_choices = ast.literal_eval(_find_assignment(class_node, "INTERRUPTION_REASON_DETAIL_CHOICES"))
        reason_to_detail_map = ast.literal_eval(_find_assignment(class_node, "REASON_TO_DETAIL_MAP"))

        self.assertIn(("planned_reporting", "计划报备"), detail_choices)
        self.assertIn(("unplanned_reporting", "非报备"), detail_choices)
        self.assertEqual(
            reason_to_detail_map["cable_rectification"],
            ["planned_reporting", "unplanned_reporting"],
        )


if __name__ == "__main__":
    unittest.main()

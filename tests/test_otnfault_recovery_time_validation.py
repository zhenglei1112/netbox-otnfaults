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


class OtnFaultRecoveryTimeValidationSourceTestCase(unittest.TestCase):
    def test_clean_allows_recovery_time_before_dispatch_chain_after_fault_start(self) -> None:
        source = MODELS_PATH.read_text(encoding="utf-8-sig")
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "OtnFault")
        clean_node = _find_method(class_node, "clean")
        clean_source = ast.get_source_segment(source, clean_node)

        self.assertIsNotNone(clean_source)
        assert clean_source is not None

        self.assertIn("sequence_time_fields = [", clean_source)
        self.assertNotIn("('fault_recovery_time', '故障恢复时间')", clean_source)
        self.assertIn("if self.fault_recovery_time:", clean_source)
        self.assertIn("if self.fault_occurrence_time and time_j < self.fault_occurrence_time:", clean_source)
        self.assertIn("errors[field_name_j].append('故障恢复时间需晚于故障起始时间')", clean_source)
        self.assertNotIn("故障恢复时间需晚于处理派发时间", clean_source)
        self.assertNotIn("故障恢复时间需晚于维修出发时间", clean_source)
        self.assertNotIn("故障恢复时间需晚于到达现场时间", clean_source)


if __name__ == "__main__":
    unittest.main()

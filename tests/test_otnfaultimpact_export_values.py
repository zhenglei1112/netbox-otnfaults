import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"


def _find_class(module: ast.Module, name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"{name} class not found")


class OtnFaultImpactExportValuesSourceTestCase(unittest.TestCase):
    def test_secondary_faults_exports_plain_text_values(self) -> None:
        source = TABLES_PATH.read_text(encoding="utf-8-sig")
        module = ast.parse(source)
        class_node = _find_class(module, "OtnFaultImpactTable")
        method_names = {
            node.name for node in class_node.body if isinstance(node, ast.FunctionDef)
        }

        self.assertIn("value_secondary_faults", method_names)

        method_node = next(
            node
            for node in class_node.body
            if isinstance(node, ast.FunctionDef) and node.name == "value_secondary_faults"
        )
        method_source = ast.get_source_segment(source, method_node)
        self.assertIsNotNone(method_source)
        assert method_source is not None
        self.assertIn("record.secondary_faults.all()", method_source)
        self.assertIn("str(fault)", method_source)
        self.assertIn("join", method_source)
        self.assertNotIn("<a", method_source)
        self.assertNotIn("href", method_source)


if __name__ == "__main__":
    unittest.main()

import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"


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

    def test_fault_impact_business_counts_columns_are_available_by_default_before_actions(self) -> None:
        module = _parse_module(TABLES_PATH)
        table_class = _find_class(module, "OtnFaultTable")
        meta_class = _find_class(ast.Module(body=table_class.body, type_ignores=[]), "Meta")

        fields = _tuple_items(_find_assignment(meta_class, "fields"))
        default_columns = _tuple_items(_find_assignment(meta_class, "default_columns"))

        self.assertIn("bare_fiber_impact_counts", fields)
        self.assertIn("circuit_impact_counts", fields)
        self.assertIn("bare_fiber_impact_counts", default_columns)
        self.assertIn("circuit_impact_counts", default_columns)
        self.assertLess(fields.index("bare_fiber_impact_counts"), fields.index("circuit_impact_counts"))
        self.assertLess(fields.index("circuit_impact_counts"), fields.index("actions"))
        self.assertEqual("actions", fields[-1])

    def test_fault_impact_business_counts_columns_render_colored_counts_and_export_values(self) -> None:
        tables_source = TABLES_PATH.read_text(encoding="utf-8-sig")
        table_block = tables_source.split("class OtnFaultTable", 1)[1].split("class ContractOtnFaultTable", 1)[0]

        self.assertIn("bare_fiber_impact_counts = tables.Column(", table_block)
        self.assertIn("circuit_impact_counts = tables.Column(", table_block)
        self.assertIn("verbose_name='裸纤'", table_block)
        self.assertIn("verbose_name='电路'", table_block)
        self.assertIn("orderable=False", table_block)
        self.assertIn("def render_bare_fiber_impact_counts(self, record: OtnFault)", table_block)
        self.assertIn("def render_circuit_impact_counts(self, record: OtnFault)", table_block)
        self.assertIn("def _render_impact_count(count: int, color: str, title: str) -> object:", table_block)
        self.assertIn("if count == 0:", table_block)
        self.assertIn("return '-'", table_block)
        self.assertIn("#fd7e14", table_block)
        self.assertIn("#dc3545", table_block)
        self.assertIn("def value_bare_fiber_impact_counts(self, record: OtnFault) -> str:", table_block)
        self.assertIn("def value_circuit_impact_counts(self, record: OtnFault) -> str:", table_block)
        self.assertIn("bare_fiber_not_interrupted_count", table_block)
        self.assertIn("bare_fiber_interrupted_count", table_block)
        self.assertIn("circuit_not_interrupted_count", table_block)
        self.assertIn("circuit_interrupted_count", table_block)

    def test_fault_list_view_annotates_impact_business_counts(self) -> None:
        views_source = VIEWS_PATH.read_text(encoding="utf-8-sig")
        view_block = views_source.split("class OtnFaultListView", 1)[1].split("class OtnFaultBulkImportView", 1)[0]

        self.assertIn("Count(", view_block)
        self.assertIn("filter=Q(", view_block)
        self.assertIn("bare_fiber_not_interrupted_count=Count(", view_block)
        self.assertIn("bare_fiber_interrupted_count=Count(", view_block)
        self.assertIn("circuit_not_interrupted_count=Count(", view_block)
        self.assertIn("circuit_interrupted_count=Count(", view_block)
        self.assertIn("ServiceTypeChoices.BARE_FIBER", view_block)
        self.assertIn("ServiceTypeChoices.CIRCUIT", view_block)
        self.assertIn("BusinessImpactChoices.NOT_INTERRUPTED", view_block)
        self.assertIn("BusinessImpactChoices.INTERRUPTED", view_block)


if __name__ == "__main__":
    unittest.main()

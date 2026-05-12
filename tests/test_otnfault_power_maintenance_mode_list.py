import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"
DETAIL_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _find_class(module: ast.Module, class_name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"Class {class_name} not found")


def _find_meta_tuple(class_node: ast.ClassDef, tuple_name: str) -> list[str]:
    meta_class = next(
        node for node in class_node.body if isinstance(node, ast.ClassDef) and node.name == "Meta"
    )
    for node in meta_class.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == tuple_name:
                    if not isinstance(node.value, (ast.Tuple, ast.List)):
                        raise AssertionError(f"Meta.{tuple_name} is not a tuple/list")
                    return [
                        elt.value
                        for elt in node.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    ]
    raise AssertionError(f"Meta.{tuple_name} not found in {class_node.name}")


class OtnFaultPowerMaintenanceModeListSourceTestCase(unittest.TestCase):
    def test_power_maintenance_mode_uses_distinct_display_label(self) -> None:
        models_source = _read(MODELS_PATH)
        forms_source = _read(FORMS_PATH)
        detail_source = _read(DETAIL_TEMPLATE_PATH)

        self.assertIn(
            "power_maintenance_mode = models.CharField(\n"
            "        max_length=20,\n"
            "        choices=PowerMaintenanceModeChoices,\n"
            "        blank=True,\n"
            "        null=True,\n"
            "        verbose_name='供电维护方式'",
            models_source,
        )
        self.assertIn(
            "power_maintenance_mode = forms.ChoiceField(\n"
            "        choices=add_blank_choice(PowerMaintenanceModeChoices),\n"
            "        required=False,\n"
            "        label='供电维护方式'",
            forms_source,
        )
        self.assertIn("<th scope=\"row\">供电维护方式</th>", detail_source)
        self.assertIn("verbose_name='维护方式'", models_source)

    def test_fault_list_exposes_power_maintenance_mode_before_actions(self) -> None:
        tables_source = _read(TABLES_PATH)
        table_node = _find_class(ast.parse(tables_source), "OtnFaultTable")
        fields = _find_meta_tuple(table_node, "fields")

        self.assertIn(
            "power_maintenance_mode = columns.ChoiceFieldColumn(\n"
            "        verbose_name='供电维护方式'",
            tables_source,
        )
        self.assertIn("power_maintenance_mode", fields)
        self.assertLess(fields.index("power_maintenance_mode"), fields.index("actions"))
        self.assertEqual("actions", fields[-1])


if __name__ == "__main__":
    unittest.main()

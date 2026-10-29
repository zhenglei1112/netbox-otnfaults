"""Check related-object URL bindings without requiring a NetBox installation."""

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CutoverSiteRelatedFiltersTest(unittest.TestCase):
    def setUp(self) -> None:
        tree = ast.parse(
            (ROOT / 'netbox_otnfaults/filtersets.py').read_text(encoding='utf-8-sig')
        )
        self.filterset = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'CutoverTaskFilterSet'
        )

    def test_netbox_related_object_parameters_target_the_correct_site_relation(self) -> None:
        declarations = {
            node.targets[0].id: node.value
            for node in self.filterset.body
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        }
        for parameter, relation in (
            ('interruption_location_a_id', 'interruption_location_a'),
            ('interruption_location_id', 'interruption_location'),
        ):
            with self.subTest(parameter=parameter):
                declaration = declarations[parameter]
                self.assertIsInstance(declaration, ast.Call)
                self.assertEqual(ast.unparse(declaration.func), 'django_filters.NumberFilter')
                options = {
                    keyword.arg: ast.literal_eval(keyword.value)
                    for keyword in declaration.keywords
                }
                self.assertEqual(options['field_name'], relation)
                if parameter == 'interruption_location_id':
                    self.assertTrue(options['distinct'])

    def test_existing_a_site_filter_remains_available(self) -> None:
        meta = next(
            node for node in self.filterset.body
            if isinstance(node, ast.ClassDef) and node.name == 'Meta'
        )
        fields = next(
            ast.literal_eval(node.value) for node in meta.body
            if isinstance(node, ast.Assign) and node.targets[0].id == 'fields'
        )
        self.assertIn('interruption_location_a', fields)


if __name__ == '__main__':
    unittest.main()

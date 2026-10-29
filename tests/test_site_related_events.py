"""Exercise isolated site queries without a local NetBox installation."""

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Predicate:
    def __init__(self, **conditions: Any) -> None:
        self.conditions = conditions
        self.children: list[Predicate] = []

    def __or__(self, other: 'Predicate') -> 'Predicate':
        result = Predicate()
        result.children = [self, other]
        return result

    def matches(self, row: dict[str, Any]) -> bool:
        if self.children:
            return any(child.matches(row) for child in self.children)
        return all(
            row['a' if key in ('interruption_location_a', 'interruption_location_a_id', 'site_a', 'site_a_id') else 'z']
            == getattr(value, 'pk', value)
            for key, value in self.conditions.items()
        )


class Rows:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def restrict(self, user: str, action: str) -> 'Rows':
        assert user == 'viewer' and action == 'view'
        return Rows([row for row in self.rows if row['visible']])

    def filter(self, predicate: Predicate) -> 'Rows':
        return Rows([row for row in self.rows if predicate.matches(row)])

    def distinct(self) -> 'Rows':
        return Rows(list({row['pk']: row for row in self.rows}.values()))

    def count(self) -> int:
        return len(self.rows)


def load_method(path: str, class_name: str, method_name: str, namespace: dict[str, Any]) -> Any:
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name)
    exec(compile(ast.Module(body=[method], type_ignores=[]), path, 'exec'), namespace)
    return namespace[method_name]


class SiteRelatedEventsTest(unittest.TestCase):
    def test_site_parameters_are_bound_and_extensions_registered(self) -> None:
        tree = ast.parse((ROOT / 'netbox_otnfaults/filtersets.py').read_text(encoding='utf-8-sig'))
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name in ('OtnFaultFilterSet', 'CutoverTaskFilterSet', 'OtnPathFilterSet')):
            site = next(node.value for node in cls.body if isinstance(node, ast.Assign)
                        and node.targets[0].id == 'site')
            self.assertEqual(ast.unparse(site.func), 'django_filters.NumberFilter')
            self.assertIn("method='filter_site'", ast.unparse(site))
        extensions = ast.parse((ROOT / 'netbox_otnfaults/template_content.py').read_text(encoding='utf-8-sig'))
        registration = next(node.value for node in extensions.body if isinstance(node, ast.Assign)
                            and node.targets[0].id == 'template_extensions')
        registered = {node.id for node in registration.elts}
        self.assertTrue({'SiteOtnFaults', 'SiteCutoverTasks', 'SiteOtnPaths'} <= registered)

    def setUp(self) -> None:
        # Join fan-out: A match with multiple Z sites, Z-only match, both ends,
        # unrelated row, A-only row, and a record hidden from the viewer.
        self.rows = Rows([
            {'pk': pk, 'a': a, 'z': z, 'visible': visible}
            for pk, a, z, visible in (
                (1, 169, 3, True), (1, 169, 4, True),
                (2, 5, 169, True), (3, 169, 169, True),
                (4, 6, 7, True), (5, 169, None, True),
                (6, 169, 8, False),
            )
        ])

    def test_fault_and_cutover_filters_match_either_end_and_deduplicate(self) -> None:
        for cls in ('OtnFaultFilterSet', 'CutoverTaskFilterSet'):
            with self.subTest(filterset=cls):
                method = load_method('netbox_otnfaults/filtersets.py', cls, 'filter_site',
                                     {'Q': Predicate, 'QuerySet': Rows})
                visible = self.rows.restrict('viewer', 'view')
                result = method(None, visible, 'site', 169)
                self.assertEqual({row['pk'] for row in result.rows}, {1, 2, 3, 5})
                self.assertEqual(result.count(), 4)
                self.assertEqual(method(None, visible, 'site', 999).count(), 0)
                self.assertIs(method(None, visible, 'site', None), visible)

    def test_related_counts_match_visible_filtered_results(self) -> None:
        for cls, model, count_key in (
            ('SiteOtnFaults', 'OtnFault', 'faults_count'),
            ('SiteCutoverTasks', 'CutoverTask', 'cutovers_count'),
        ):
            with self.subTest(extension=cls):
                method = load_method('netbox_otnfaults/template_content.py', cls, 'right_page',
                                     {'Q': Predicate, model: SimpleNamespace(objects=self.rows)})
                extension = SimpleNamespace(
                    context={'object': SimpleNamespace(pk=169), 'request': SimpleNamespace(user='viewer')},
                    render=lambda template, extra_context: extra_context,
                )
                context = method(extension)
                self.assertEqual(context[count_key], 4)
                self.assertEqual(context['site_id'], 169)

    def test_path_count_matches_a_or_z_filtered_visible_paths(self) -> None:
        # Both path endpoints are foreign keys: a double match is one row.
        rows = Rows([
            {'pk': pk, 'a': a, 'z': z, 'visible': visible}
            for pk, a, z, visible in (
                (1, 169, 3, True), (2, 5, 169, True), (3, 169, 169, True),
                (4, 6, 7, True), (5, 169, 8, False),
            )
        ])
        method = load_method('netbox_otnfaults/filtersets.py', 'OtnPathFilterSet', 'filter_site', {'Q': Predicate})
        visible = rows.restrict('viewer', 'view')
        result = method(None, visible, 'site', 169)
        self.assertEqual([row['pk'] for row in result.rows], [1, 2, 3])
        self.assertEqual(method(None, visible, 'site', 999).count(), 0)
        self.assertIs(method(None, visible, 'site', None), visible)
        count = load_method('netbox_otnfaults/template_content.py', 'SiteOtnPaths', 'right_page',
                            {'Q': Predicate, 'OtnPath': SimpleNamespace(objects=rows)})
        extension = SimpleNamespace(
            context={'object': SimpleNamespace(pk=169), 'request': SimpleNamespace(user='viewer')},
            render=lambda template, extra_context: extra_context,
        )
        self.assertEqual(count(extension)['paths_count'], result.count())


if __name__ == '__main__':
    unittest.main()

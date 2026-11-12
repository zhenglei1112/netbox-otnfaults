import ast
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock


FORMS_PATH = Path(__file__).resolve().parents[1] / 'netbox_otnfaults' / 'forms.py'


class ImpactCircuitStatusChoicesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = ast.parse(FORMS_PATH.read_text(encoding='utf-8-sig'))
        helpers = [node for node in self.module.body if isinstance(node, ast.FunctionDef)
                   and node.name in ('_get_impact_circuit_service_queryset', '_build_circuit_service_catalog')]
        self.manager = Mock()
        self.namespace: dict[str, Any] = {
            'CircuitService': SimpleNamespace(objects=self.manager),
            'CircuitOperationStatusChoices': SimpleNamespace(PENDING='pending', CLOSED='closed'),
            'BusinessCategoryChoices': SimpleNamespace(CHOICES=[]),
            'ServiceGroupChoices': SimpleNamespace(CHOICES=[]),
            'json': json,
        }
        code = ast.Module(body=[ast.ImportFrom(module='__future__', names=[
            ast.alias(name='annotations')], level=0), *helpers], type_ignores=[])
        exec(compile(ast.fix_missing_locations(code), str(FORMS_PATH), 'exec'), self.namespace)

    def test_new_impact_excludes_pending_and_closed(self) -> None:
        queryset = self.namespace['_get_impact_circuit_service_queryset'](SimpleNamespace(pk=None))
        self.manager.all.return_value.exclude.assert_called_once_with(
            operation_status__in=('pending', 'closed'))
        self.assertIs(queryset, self.manager.all.return_value.exclude.return_value)

    def test_edit_keeps_historical_circuit_available(self) -> None:
        queryset = self.namespace['_get_impact_circuit_service_queryset'](SimpleNamespace(pk=42))
        self.manager.all.return_value.exclude.assert_not_called()
        self.assertIs(queryset, self.manager.all.return_value)

    def test_catalog_uses_supplied_queryset_for_options_and_json(self) -> None:
        queryset = Mock()
        services = [dict(pk=i, business_category='commercial', service_group='finance',
                         special_line_name=status, name=str(i))
                    for i, status in enumerate(('configured', 'operating', 'testing'), start=1)]
        queryset.order_by.return_value.values.return_value = services
        catalog, serialized, choices = self.namespace['_build_circuit_service_catalog'](queryset)
        queryset.order_by.assert_called_once_with(
            'business_category', 'service_group', 'special_line_name', 'name')
        self.assertEqual(json.loads(serialized), catalog)
        self.assertEqual([value for value, _ in choices], ['', '1', '2', '3'])

    def test_both_forms_share_queryset_for_catalog_and_validation(self) -> None:
        for name in ('OtnFaultImpactForm', 'CutoverImpactForm'):
            with self.subTest(form=name):
                form = next(node for node in self.module.body
                            if isinstance(node, ast.ClassDef) and node.name == name)
                source = ast.unparse(form)
                self.assertIn('circuit_queryset = _get_impact_circuit_service_queryset(self.instance)', source)
                self.assertIn("self.fields['circuit_service'].queryset = circuit_queryset", source)
                self.assertIn('_build_circuit_service_catalog(circuit_queryset)', source)
                self.assertIn("self.fields['circuit_service'].queryset.get(pk=selected_special_line)", source)


if __name__ == '__main__':
    unittest.main()

"""Execute serializer with a controlled queryset; NetBox integration is separate."""
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import unittest


class CutoverDataTests(unittest.TestCase):
    def test_widget_filter_permissions_colors_and_missing_coordinates(self) -> None:
        today = datetime(2026, 9, 8, tzinfo=timezone.utc)
        calls = {}
        def task(pk, delta, status, color):
            return SimpleNamespace(pk=pk, planned_cutover_time=today + timedelta(days=delta),
                cutover_no=f'C{pk}', status=status, province=None, interruption_location_a=None,
                interruption_location=SimpleNamespace(all=lambda: []), cutover_location='',
                line_supervisor=None, line_supervisor_id=None,
                get_absolute_url=lambda: f'/cutovers/{pk}/', get_cutover_type_display=lambda: '光缆割接',
                get_status_display=lambda: status, get_status_color=lambda: color)
        class Query:
            def restrict(self, user, action):
                calls['permission'] = (user, action)
                return self
            def filter(self, **kwargs):
                calls['filter'] = kwargs
                return self
            def select_related(self, *args): return self
            def prefetch_related(self, *args): return self
            def order_by(self, *args):
                calls['order'] = args
                return [task(1, 0, 'completed', 'green'), task(2, 1, 'cancelled', 'red')]
        source = Path('netbox_otnfaults/services/dashboard_v2.py').read_text(encoding='utf-8')
        function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'build_dashboard_cutovers')
        namespace = {'Any': Any, 'timedelta': timedelta,
            'timezone': SimpleNamespace(localdate=lambda: today.date(), localtime=lambda value: value),
            'CutoverTask': SimpleNamespace(objects=Query()), 'resolve_cutover_coordinates': lambda task: None}
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<cutovers>', 'exec'), namespace)
        user = SimpleNamespace(pk=5)
        result = namespace['build_dashboard_cutovers'](user)
        self.assertEqual(calls['permission'], (user, 'view'))
        self.assertEqual(calls['filter'], {'planned_cutover_time__date__in': [today.date(), (today + timedelta(days=1)).date()]})
        self.assertEqual(result['cutover_summary'], {'today': 1, 'tomorrow': 1, 'total': 2})
        self.assertEqual([item['status_color'] for item in result['cutovers']], ['green', 'red'])
        self.assertTrue(all(item['lat'] is None for item in result['cutovers']))
        self.assertEqual(namespace['build_dashboard_cutovers'](None)['cutovers'], [])

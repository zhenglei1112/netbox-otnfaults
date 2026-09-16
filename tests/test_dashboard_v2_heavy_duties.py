"""Exercise the serializer without requiring a local NetBox installation."""
import ast
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import unittest


class HeavyDutyDataTests(unittest.TestCase):
    def test_permissions_inclusive_window_order_and_payload(self) -> None:
        now = datetime(2026, 9, 13, tzinfo=timezone.utc)
        calls: dict[str, Any] = {}

        class Query:
            def restrict(self, user: Any, action: str) -> Any:
                calls['permission'] = (user, action)
                return self

            def filter(self, **kwargs: Any) -> Any:
                calls['filter'] = kwargs
                return self

            def order_by(self, *args: str) -> list[Any]:
                calls['order'] = args
                return [SimpleNamespace(
                    pk=i, name=kind, type=kind, description='<b>正文</b>',
                    start_time=now, end_time=now,
                    get_absolute_url=lambda: '/heavy/1/',
                    get_type_display=lambda: '类型', get_type_color=lambda: 'blue',
                ) for i, kind in enumerate(['important', 'notice', 'memo'])]

        source = Path('netbox_otnfaults/services/dashboard_v2.py').read_text(encoding='utf-8')
        function = next(node for node in ast.parse(source).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'build_dashboard_heavy_duties')
        namespace = {'Any': Any, 'datetime': datetime, 'HeavyDuty': SimpleNamespace(objects=Query()),
                     'timezone': SimpleNamespace(localtime=lambda value: value)}
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<heavy>', 'exec'), namespace)
        build = namespace['build_dashboard_heavy_duties']
        result = build('viewer', now)['heavy_duties']
        self.assertEqual(calls['permission'], ('viewer', 'view'))
        self.assertEqual(calls['filter'], {'start_time__lte': now, 'end_time__gte': now})
        self.assertEqual(calls['order'], ('-start_time', '-pk'))
        self.assertEqual([item['type'] for item in result], ['important', 'notice', 'memo'])
        self.assertEqual(result[0]['description'], '<b>正文</b>')
        self.assertEqual(result[0]['url'], '/heavy/1/')
        self.assertNotIn('lng', result[0])
        self.assertEqual(build(None, now), {'heavy_duties': []})

from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('statistics_diagnostics_test_module', ROOT / 'netbox_otnfaults/statistics_diagnostics.py')
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)


class Response(dict):
    def __init__(self, payload: dict) -> None:
        super().__init__({'Content-Type': 'application/json'})
        self.content = json.dumps(payload).encode()


class StatisticsDiagnosticsTests(unittest.TestCase):
    def request(self, debug: str = '1', staff: bool = True) -> SimpleNamespace:
        return SimpleNamespace(GET={'statistics_debug': debug}, user=SimpleNamespace(is_authenticated=True, is_staff=staff, is_superuser=False))

    def test_gates_are_all_required(self) -> None:
        settings = SimpleNamespace(DEBUG=False, PLUGINS_CONFIG={'netbox_otnfaults': {'statistics_diagnostics': True}})
        self.assertTrue(diag.diagnostics_allowed(self.request(), settings))
        self.assertFalse(diag.diagnostics_allowed(self.request('0'), settings))
        self.assertFalse(diag.diagnostics_allowed(self.request(staff=False), settings))
        self.assertFalse(diag.diagnostics_allowed(self.request(), SimpleNamespace(DEBUG=False)))

    def test_queries_are_aggregated_without_text_or_parameters(self) -> None:
        profile = diag.StatisticsProfile()
        with profile.stage('query'):
            for _ in range(3):
                result = profile.execute(lambda *args: 42, 'SELECT secret FROM private WHERE password=%s', ['never-export-me'], False, {})
                self.assertEqual(result, 42)
        report = profile.report()
        self.assertEqual(report['sql_count'], 3)
        self.assertEqual(report['sql_top'][0]['count'], 3)
        self.assertEqual(report['stages'][0]['sql_count'], 3)
        serialized = json.dumps(report)
        self.assertNotIn('password', serialized)
        self.assertNotIn('never-export-me', serialized)

    def test_netbox_user_without_is_staff(self) -> None:
        settings = SimpleNamespace(DEBUG=True)
        request = self.request()
        request.user = SimpleNamespace(is_authenticated=True, is_superuser=True)
        self.assertTrue(diag.diagnostics_allowed(request, settings))
        request.user.is_superuser = False
        self.assertFalse(diag.diagnostics_allowed(request, settings))
        request.user = SimpleNamespace(is_authenticated=False)
        self.assertFalse(diag.diagnostics_allowed(request, settings))

    def test_nested_spans_and_disabled_wrapper_preserve_results(self) -> None:
        @diag.statistics_stage('outer')
        def work() -> list[int]:
            with diag.statistics_span('inner'):
                return [1, 2]
        self.assertEqual(work(), [1, 2])
        profile = diag.StatisticsProfile()
        token = diag._current.set(profile)
        try:
            self.assertEqual(work(), [1, 2])
            self.assertEqual(set(profile.stages), {'outer', 'outer/inner'})
        finally:
            diag._current.reset(token)

    def test_sql_storage_is_bounded_and_failures_count(self) -> None:
        profile = diag.StatisticsProfile()
        for index in range(150):
            profile.execute(lambda *args: None, f'SELECT {index}', None, False, {})
        self.assertEqual(len(profile.sql_groups), 101)
        with self.assertRaises(ValueError):
            profile.execute(lambda *args: (_ for _ in ()).throw(ValueError()), 'error', None, False, {})
        self.assertEqual(profile.sql_count, 151)

    def test_self_time_excludes_nested_stage(self) -> None:
        with patch.object(diag, 'perf_counter', side_effect=[0, 1, 2, 3, 5]):
            profile = diag.StatisticsProfile()
            with profile.stage('outer'):
                with profile.stage('inner'):
                    pass
        self.assertEqual(profile.stages['outer']['ms'], 4000)
        self.assertEqual(profile.stages['outer']['self_ms'], 3000)
        self.assertEqual(profile.stages['outer/inner']['self_ms'], 1000)

    def test_export_analyzer_keeps_periods_and_caches_separate(self) -> None:
        spec = importlib.util.spec_from_file_location('analyze_statistics_performance', ROOT / 'scripts/analyze_statistics_performance.py')
        analyzer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analyzer)
        rows = []
        for elapsed in [10, 20, 30, 40, 50]:
            rows.append({'type': 'request', 'action': 'month', 'endpoint': '/statistics/data', 'parameters': {'month': ['1']}, 'complete_ms': elapsed, 'server': {'cache': 'hit', 'sql_count': 0}})
        rows.append({**rows[0], 'complete_ms': 999, 'error': 'network_error'})
        rows.append({**rows[0], 'parameters': {'month': ['2']}, 'complete_ms': 100})
        rows.append({**rows[0], 'server': {'cache': 'miss', 'sql_count': 25}, 'complete_ms': 200})
        text = analyzer.summarize([{'records': rows}])
        self.assertIn('| 6 | 5 | 30.00 | 50.00 | 0 |', text)
        self.assertIn('| 1 | 1 | 100.00 | 100.00 | 0 |', text)
        self.assertIn('| 1 | 1 | 200.00 | 200.00 | 25 |', text)

    def test_request_scope_cache_isolation_and_cleanup(self) -> None:
        settings = SimpleNamespace(DEBUG=False, PLUGINS_CONFIG={'netbox_otnfaults': {'statistics_diagnostics': True}})
        wrappers = []
        @contextmanager
        def execute_wrapper(wrapper: object):
            wrappers.append(wrapper)
            try:
                yield
            finally:
                wrappers.pop()
        connection = SimpleNamespace(execute_wrapper=execute_wrapper)
        modules = {'django.conf': SimpleNamespace(settings=settings), 'django.db': SimpleNamespace(connections={'default': connection})}
        cached = {'kpis': {'count': 5}}
        @diag.statistics_debug_request
        def get(self: object, request: object) -> Response:
            diag.statistics_cache('hit')
            self.assertEqual(len(wrappers), 1)
            return Response(cached)
        with patch.dict('sys.modules', modules):
            first = get(self, self.request())
            second = get(self, self.request())
        data = json.loads(first.content)
        self.assertEqual(data['kpis'], cached['kpis'])
        self.assertNotIn('_statistics_debug', cached)
        self.assertEqual(data['_statistics_debug']['cache'], 'hit')
        self.assertNotEqual(first['X-Statistics-Request-ID'], second['X-Statistics-Request-ID'])
        self.assertEqual(first['Cache-Control'], 'private, no-store')
        self.assertIsNone(diag._current.get())
        self.assertEqual(wrappers, [])

    def test_exception_resets_profile_and_bypass_requires_active_debug(self) -> None:
        req = self.request()
        req.GET['statistics_cache_bypass'] = '1'
        self.assertFalse(diag.statistics_cache_bypass(req))
        settings = SimpleNamespace(DEBUG=True)
        @diag.statistics_debug_request
        def fail(self: object, request: object) -> None:
            self.assertTrue(diag.statistics_cache_bypass(request))
            raise ValueError('test')
        with patch.dict('sys.modules', {'django.conf': SimpleNamespace(settings=settings), 'django.db': SimpleNamespace(connections={})}):
            with self.assertRaises(ValueError):
                fail(self, req)
        self.assertIsNone(diag._current.get())


if __name__ == '__main__':
    unittest.main()

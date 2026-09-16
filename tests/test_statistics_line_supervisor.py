"""Exercise statistics calculations without importing the unavailable NetBox runtime."""
from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from types import SimpleNamespace
import re
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'netbox_otnfaults/statistics_views.py').read_text(encoding='utf-8')


class Rows(list):
    def select_related(self, *args: str) -> Rows:
        return self

    def prefetch_related(self, *args: str) -> Rows:
        return self

    def filter(self, *args: object, **kwargs: object) -> Rows:
        if args:  # The suspended-history query in these fixtures has no matches.
            return Rows()
        return Rows(row for row in self if all(self.matches(row, key, value) for key, value in kwargs.items()))

    def exclude(self, **kwargs: object) -> Rows:
        return Rows(row for row in self if not all(self.matches(row, key, value) for key, value in kwargs.items()))

    @staticmethod
    def matches(row: object, key: str, expected: object) -> bool:
        parts = key.split('__')
        op = parts.pop() if parts[-1] in ('gte', 'lt', 'in') else 'eq'
        actual = row
        for part in parts:
            actual = getattr(actual, part)
        if op == 'gte':
            return actual >= expected
        if op == 'lt':
            return actual < expected
        if op == 'in':
            return actual in expected
        return actual == expected


def load_calculators() -> dict:
    names = {
        'BRANCH_PROVINCE_NAMES', 'BRANCH_PROVINCE_PATH_LENGTHS', 'BRANCH_PROVINCE_ALIASES',
        'EXCLUDED_HANDLING_UNITS', 'LINE_SUPERVISOR_PROVINCES', 'LINE_SUPERVISOR_PATH_LENGTHS',
        '_should_exclude_for_branch', '_is_branch_company_fault', '_normalize_branch_province_name',
        '_branch_province_for_fault', '_line_supervisor_for_fault', '_is_line_supervisor_fault',
        '_filter_line_supervisor_faults', '_build_branch_company_statistics',
        '_duration_hours_for_fault', '_per_1000km', '_percentile', '_calculate_boxplot_values',
        '_build_branch_week_ranges', '_build_recent_calendar_months', '_build_year_to_month_calendar_months',
        '_get_filtered_bare_fiber_interruption_impacts', '_compute_bare_fiber_interruption_overview',
    }
    nodes = []
    for node in ast.parse(SOURCE).body:
        name = node.name if isinstance(node, ast.FunctionDef) else node.target.id if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) else None
        if name in names:
            nodes.append(node)
    env = {'datetime': datetime, 'timedelta': timedelta}
    exec(compile('from __future__ import annotations\n' + ast.unparse(ast.Module(body=nodes, type_ignores=[])), '<statistics calculators>', 'exec'), env)
    return env


def fault(province: str | None, hours: float = 1, excluded: bool = False, pk: int = 1) -> SimpleNamespace:
    start = datetime(2026, 1, 5, tzinfo=dt_timezone.utc)
    return SimpleNamespace(
        id=pk, province=SimpleNamespace(name=province) if province else None,
        handling_unit_id=1, handling_unit=SimpleNamespace(name='北京京宽网络科技有限公司' if excluded else '普通维护单位'),
        fault_category='fiber', fault_occurrence_time=start, fault_recovery_time=start + timedelta(hours=hours),
        interruption_reason='', interruption_reason_detail='', is_suspended=False, fault_status='closed',
        line_supervisor='故意填写错误的主管',
    )


class LineSupervisorStatisticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = load_calculators()

    def test_every_mapped_province_and_six_province_exception(self) -> None:
        for manager, provinces in self.env['LINE_SUPERVISOR_PROVINCES'].items():
            for province in provinces:
                with self.subTest(province=province):
                    expected = None if province in self.env['BRANCH_PROVINCE_NAMES'] else manager
                    self.assertEqual(self.env['_line_supervisor_for_fault'](fault(province)), expected)
                    self.assertEqual(self.env['_line_supervisor_for_fault'](fault(province, excluded=True)), manager)
                    self.assertEqual(self.env['_is_branch_company_fault'](fault(province)), expected is None)

    def test_aliases_unknown_and_recorded_supervisor_are_handled(self) -> None:
        for province, expected in [('内蒙古自治区', '冯鑫源'), ('内蒙', '冯鑫源'), ('宁夏回族自治区', '冯鑫源'), ('广西壮族自治区', '李立彬'), ('新疆维吾尔自治区', '冯鑫源'), ('广东省', '姜川'), ('上海市', '孙振伟'), ('辽宁省', '李小涛'), (None, None), ('西藏自治区', None)]:
            self.assertEqual(self.env['_line_supervisor_for_fault'](fault(province, excluded=True)), expected)

    def test_detail_scope_filters_manager_without_leaking_six_province_faults(self) -> None:
        rows = [fault('浙江'), fault('浙江', excluded=True), fault('广东'), fault(None)]
        filter_rows = self.env['_filter_line_supervisor_faults']
        self.assertEqual(filter_rows(rows), rows[1:3])
        self.assertEqual(filter_rows(rows, '冯鑫源'), [rows[1]])
        self.assertEqual(filter_rows(rows, '姜川'), [rows[2]])
        self.assertEqual(filter_rows(rows, '不存在'), [])

    def configure_calculator(self, rows: list) -> None:
        tz = dt_timezone.utc
        self.env.update({
            'timezone': SimpleNamespace(datetime=datetime, get_current_timezone=lambda: tz, localtime=lambda value: value),
            'OtnFault': SimpleNamespace(objects=Rows(rows)),
            '_suspended_fault_q': lambda: object(),
            'OVERALL_EXCLUDED_TOTAL_CATEGORIES': (),
            'get_cable_break_base_queryset': lambda start, end: Rows(rows),
            '_build_fault_category_summary': lambda faults, now: [{'name': 'fiber', 'value': len(faults)}],
            '_build_other_fault_summary': lambda faults, count: {'suspended_faults': count},
            '_compute_cable_break_overview': lambda faults, now: {'total_count': len(faults)},
            '_count_repeat_fiber_faults': lambda *args, **kwargs: 0,
            '_compute_bare_fiber_interruption_overview': Mock(return_value={}),
            '_build_branch_company_performance_cards': Mock(return_value=[]),
        })

    def calculate(self, rows: list, supervisor: bool = True) -> dict:
        self.configure_calculator(rows)
        return self.env['_build_branch_company_statistics'](
            rows, rows, 0, datetime(2026, 1, 1, tzinfo=dt_timezone.utc),
            datetime(2026, 2, 1, tzinfo=dt_timezone.utc), datetime(2026, 9, 16, tzinfo=dt_timezone.utc),
            line_supervisor_scope=supervisor,
        )

    def test_aggregate_raw_samples_trends_and_normalization(self) -> None:
        rows = [fault('广东', 1), fault('广东', 3), fault('湖南', 8), fault('湖南', .5), fault('浙江', 20), fault('浙江', 2, True)]
        result = self.calculate(rows)
        bars = {bar['name']: bar for bar in result['province_bars']}
        self.assertEqual(list(bars), list(self.env['LINE_SUPERVISOR_PROVINCES']))
        self.assertEqual(result['overview']['total_count'], 5)
        self.assertEqual(bars['姜川']['count'], 4)
        self.assertEqual(bars['姜川']['duration'], 12.5)
        self.assertEqual(bars['姜川']['count_per_1000km'], round(4 * 1000 / 11660, 2))
        self.assertEqual(bars['姜川']['duration_per_1000km'], round(12.5 * 1000 / 11660, 2))
        self.assertEqual(result['path_lengths'], {'冯鑫源': 3972, '姜川': 11660, '李立彬': 10162, '孙振伟': 11724, '李小涛': 3811})
        self.assertEqual(bars['冯鑫源']['count'], 1)
        self.assertEqual(bars['李小涛']['count'], 0)
        average = next(item for item in result['valid_duration_bars'] if item['name'] == '姜川')
        self.assertEqual(average['valid_duration'], 4)  # (1 + 3 + 8) / 3, not a mean of province means.
        box = next(item for item in result['duration_boxplot'] if item['name'] == '姜川')
        self.assertEqual(box['value'], self.env['_calculate_boxplot_values']([1, 3, 8, .5]))
        for key in ('weekly_trends', 'monthly_trends'):
            series = next(item for item in result[key]['series'] if item['name'] == '姜川')
            self.assertEqual(sum(series['counts']), 4)
            self.assertEqual(sum(series['durations']), 12.5)
            self.assertEqual(sum(series['valid_durations']), 12)
        self.env['_build_branch_company_performance_cards'].assert_not_called()
        self.assertTrue(self.env['_compute_bare_fiber_interruption_overview'].call_args.kwargs['line_supervisor_scope'])

    def test_empty_groups_and_existing_branch_behavior(self) -> None:
        result = self.calculate([])
        self.assertEqual(len(result['province_bars']), 5)
        self.assertTrue(all(item['count'] == 0 for item in result['province_bars']))
        branch = self.calculate([fault('浙江'), fault('浙江', excluded=True), fault('广东')], supervisor=False)
        self.assertEqual(branch['overview']['total_count'], 1)
        self.assertEqual(branch['provinces'], self.env['BRANCH_PROVINCE_NAMES'])
        self.env['_build_branch_company_performance_cards'].assert_called_once()

    def test_bare_fiber_scope_and_distinct_fault_duration(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=dt_timezone.utc)
        end = datetime(2026, 2, 1, tzinfo=dt_timezone.utc)
        included = fault('浙江', excluded=True, pk=2)
        impacts = []
        for item, hours in [(fault('浙江', pk=1), 10), (included, 2), (included, 4), (fault('广东', pk=3), 3), (fault(None, pk=4), 20)]:
            impacts.append(SimpleNamespace(otn_fault=item, otn_fault_id=item.id, service_type='bare', business_impact='interrupted', coordination_status='', service_interruption_time=start, service_recovery_time=start + timedelta(hours=hours)))
        self.env.update({
            'OtnFaultImpact': SimpleNamespace(objects=Rows(impacts)),
            'ServiceTypeChoices': SimpleNamespace(BARE_FIBER='bare'),
            'FaultStatusChoices': SimpleNamespace(SUSPENDED='suspended'),
            'BusinessImpactChoices': SimpleNamespace(NOT_INTERRUPTED='not_interrupted'),
        })
        overview = self.env['_compute_bare_fiber_interruption_overview'](start, end, [], end, line_supervisor_scope=True)
        self.assertEqual(overview, {'total_count': 3, 'distinct_count': 2, 'total_duration': 9, 'distinct_duration': 7})
        details = self.env['_get_filtered_bare_fiber_interruption_impacts'](start, end, [], line_supervisor_scope=True)
        self.assertEqual({row.otn_fault_id for row in details}, {2, 3})

    def test_template_ids_tab_order_and_interface_wiring(self) -> None:
        template = (ROOT / 'netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html').read_text(encoding='utf-8')
        ids = re.findall(r'\bid="([^"]+)"', template)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertLess(template.index('id="tab-line-supervisor-btn"'), template.index('id="tab-branch-company-btn"'))
        self.assertNotIn('暂定里程', template)
        self.assertIn("'prev_line_supervisor':", SOURCE)
        self.assertIn("'yoy_line_supervisor':", SOURCE)
        self.assertIn('_filter_line_supervisor_faults(current_faults, supervisor)', SOURCE)
        self.assertIn('_filter_line_supervisor_faults(preceding_faults, supervisor)', SOURCE)


if __name__ == '__main__':
    unittest.main()

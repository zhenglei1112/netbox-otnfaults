import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"


class StatisticsCableBreakOverviewTestCase(unittest.TestCase):
    def test_backend_builds_cable_break_overview_with_required_scope_and_buckets(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("FaultStatusChoices", source)
        self.assertIn("cable_break_faults = [", source)
        self.assertIn("f.fault_category == FaultCategoryChoices.FIBER_BREAK", source)
        self.assertIn("f.fault_status != FaultStatusChoices.SUSPENDED", source)
        self.assertIn("def _compute_cable_break_overview(faults: list, now) -> dict:", source)
        self.assertIn("cable_break_overview = _compute_cable_break_overview(faults, now)", source)
        self.assertIn("'cable_break_overview': cable_break_overview", source)
        self.assertIn("'prev_cable_break_overview': prev_cable_break_overview", source)
        self.assertIn("'total_count': cb_count", source)
        self.assertIn("'total_duration': round(total_duration, 2)", source)
        self.assertIn("'avg_metrics': avg_metrics", source)
        self.assertIn("'6-8小时': 0", source)
        self.assertIn("'8-10小时': 0", source)
        self.assertIn("'10-12小时': 0", source)
        self.assertIn("'12小时以上': 0", source)

    def test_template_contains_cable_break_overview_section_and_cards(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("statistics-cable-break-overview", template)
        self.assertIn("光缆中断概览", template)
        self.assertIn('id="cable-break-total-count"', template)
        self.assertIn('id="cable-break-count-flex-list"', template)
        self.assertIn('id="cable-break-duration-flex-list"', template)
        self.assertIn('id="cable-break-long-total"', template)
        self.assertIn('id="cable-break-long-flex-list"', template)
        self.assertIn('id="cable-break-total-duration"', template)
        self.assertIn('id="cable-break-overall-avg"', template)
        self.assertIn('id="cable-break-valid-avg"', template)
        self.assertIn('id="cable-break-daytime-avg"', template)
        self.assertIn('id="cable-break-nighttime-avg"', template)
        self.assertIn('id="cable-break-construction-avg"', template)
        self.assertIn('id="cable-break-noncons-avg"', template)

    def test_dashboard_script_renders_cable_break_overview(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("renderCableBreakOverview(data.cable_break_overview, data.prev_cable_break_overview);", source)
        self.assertIn("function renderCableBreakOverview(overview, prevOverview)", source)
        self.assertIn("document.getElementById('cable-break-total-count')", source)
        self.assertIn("document.getElementById('cable-break-count-flex-list')", source)
        self.assertIn("buildFlexGroup(overview.reason_top3", source)
        self.assertIn("buildFlexGroup(overview.source_counts", source)
        self.assertIn("overview.long_duration_buckets || {}", source)
        self.assertIn("const orderedBuckets = ['6-8小时', '8-10小时', '10-12小时', '12小时以上'];", source)
        self.assertIn("longTotal += count;", source)
        self.assertIn("longTotalEl.textContent = longTotal;", source)


    def test_dashboard_script_preserves_metric_id_nodes_when_rendering_trends(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("function renderTrendBesideMetric(metricEl, currentValue, previousValue)", source)
        self.assertNotIn("totalArrowEl.innerHTML", source)
        self.assertNotIn("longArrowEl.innerHTML", source)
        self.assertNotIn("durArrowEl.innerHTML", source)
        self.assertNotIn("avgArrowEl.innerHTML", source)

    def test_dashboard_script_renders_trend_arrows_with_diff_values(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("function formatTrendDiff(currentVal, prevVal)", source)
        self.assertIn("const diff = cur - prev;", source)
        self.assertIn("return Number.isInteger(diff) ? String(diff) : diff.toFixed(2);", source)
        self.assertIn("${symbol}${formatTrendDiff(cur, prev)}", source)

    def test_submetric_numbers_use_larger_font_size(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn('<div class="fs-3 fw-bold ${colorClass} lh-1">', source)
        self.assertIn('class="fs-3 fw-bold text-primary lh-1" id="cable-break-valid-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-info lh-1" id="cable-break-daytime-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-purple lh-1" id="cable-break-nighttime-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-warning lh-1" id="cable-break-construction-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-success lh-1" id="cable-break-noncons-avg"', template)

    def test_duration_reason_group_label_uses_reason_top3(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn('buildFlexGroup(durReasonItems, "时", "原因TOP3", "text-teal", prevDurReasonItems)', source)
        self.assertNotIn('buildFlexGroup(durReasonItems, "时", "一级原因", "text-teal", prevDurReasonItems)', source)


if __name__ == "__main__":
    unittest.main()

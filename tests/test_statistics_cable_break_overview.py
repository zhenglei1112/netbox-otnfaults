import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"
CSS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "statistics_dashboard.css"


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
        self.assertIn("'long_duration_total': round(long_duration_total, 2)", source)
        self.assertIn("'long_duration_bucket_durations': long_duration_bucket_durations", source)
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
        self.assertIn('id="cable-break-long-duration-total"', template)
        self.assertIn('id="cable-break-long-duration-flex-list"', template)
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
        self.assertIn("overview.long_duration_buckets || {}", source)
        self.assertIn("overview.long_duration_bucket_durations || {}", source)
        self.assertIn("document.getElementById('cable-break-long-duration-total')", source)
        self.assertIn("document.getElementById('cable-break-long-duration-flex-list')", source)
        self.assertIn("const orderedBuckets = ['6-8小时', '8-10小时', '10-12小时', '12小时以上'];", source)
        self.assertIn("longTotal += count;", source)
        self.assertIn("longTotalEl.textContent = longTotal;", source)
        self.assertIn("longDurationTotalEl.textContent = longDurationTotal.toFixed(2);", source)

    def test_cable_break_group_layout_uses_bottom_labels_and_short_separators(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn('class="statistics-kpi-grouped-list', template)
        self.assertIn("function buildGroupedFlexLayout(groups)", source)
        self.assertIn('class="statistics-kpi-group"', source)
        self.assertIn("statistics-kpi-group-title", source)
        self.assertIn("statistics-kpi-group-separator", source)

    def test_cable_break_first_row_uses_asymmetric_two_card_layout(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")
        cable_break_section = template.split('<section class="statistics-cable-break-overview mb-4">', 1)[1].split("</section>", 1)[0]

        self.assertIn("statistics-cable-break-summary-grid", cable_break_section)
        self.assertIn("statistics-cable-break-summary-card", cable_break_section)
        self.assertIn("statistics-cable-break-summary-card-primary", cable_break_section)
        self.assertIn("statistics-cable-break-summary-card-secondary", cable_break_section)
        self.assertIn("statistics-cable-break-row", cable_break_section)
        self.assertIn("statistics-cable-break-main", cable_break_section)
        self.assertNotIn("overflow-auto", cable_break_section)
        self.assertIn(".statistics-cable-break-summary-grid", css)
        self.assertIn("grid-template-columns: minmax(0, 1.45fr) minmax(0, 1fr);", css)
        self.assertIn("gap: 1rem;", css)
        self.assertIn("flex: 0 0 148px;", css)

    def test_duration_and_long_duration_cards_share_one_row(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")
        duration_grid = template.split('statistics-cable-break-duration-grid', 1)[1].split('<div class="card p-0 shadow-sm statistics-cable-break-summary-card mb-4">', 1)[0]

        self.assertIn('id="cable-break-total-duration"', duration_grid)
        self.assertIn('id="cable-break-long-duration-total"', duration_grid)
        self.assertIn(".statistics-cable-break-duration-grid", css)
        self.assertIn(".statistics-cable-break-duration-grid .statistics-kpi-grouped-list", css)
        self.assertIn("flex-direction: column;", css)
        self.assertIn(".statistics-cable-break-duration-grid .statistics-kpi-group-separator", css)

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

    def test_trend_diff_renders_below_metrics_to_reduce_width(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn('class="statistics-kpi-trend-row', source)
        self.assertIn("metricTrendContainer", source)
        self.assertIn("metricTrendContainer.parentElement.insertBefore(trendEl, metricTrendContainer.nextSibling);", source)
        self.assertIn(".statistics-kpi-trend-row", css)

    def test_submetric_numbers_use_larger_font_size(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn('<div class="fs-3 fw-bold ${colorClass} lh-1">', source)
        self.assertIn('class="fs-3 fw-bold text-indigo lh-1" id="cable-break-valid-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-indigo lh-1" id="cable-break-daytime-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-indigo lh-1" id="cable-break-nighttime-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-indigo lh-1" id="cable-break-construction-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-indigo lh-1" id="cable-break-noncons-avg"', template)

    def test_duration_reason_group_label_uses_reason_top3(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        overview_source = source.split("function renderCharts")[0]

        self.assertIn("原因TOP3", overview_source)
        self.assertNotIn("一级原因", overview_source)


if __name__ == "__main__":
    unittest.main()

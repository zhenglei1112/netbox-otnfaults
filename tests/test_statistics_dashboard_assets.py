import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
LOCAL_ECHARTS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "lib" / "echarts.min.js"
CSS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "statistics_dashboard.css"
JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"


class StatisticsDashboardAssetsTestCase(unittest.TestCase):
    def test_statistics_dashboard_uses_local_echarts_before_dashboard_script(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        local_echarts = "{% static 'netbox_otnfaults/lib/echarts.min.js' %}"
        dashboard_script = "{% static 'netbox_otnfaults/js/statistics_dashboard.js' %}"

        self.assertNotIn("cdn.jsdelivr.net/npm/echarts", template)
        self.assertIn(local_echarts, template)
        self.assertIn(dashboard_script, template)
        self.assertLess(template.index(local_echarts), template.index(dashboard_script))
        self.assertTrue(LOCAL_ECHARTS_PATH.exists())

    def test_statistics_dashboard_loads_bumped_theme_assets(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("statistics_dashboard.css' %}?v=6", template)
        self.assertIn("statistics_dashboard.js' %}?v=12", template)

    def test_statistics_dashboard_css_covers_light_and_dark_theme_surfaces(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("--statistics-surface", css)
        self.assertIn('[data-bs-theme="dark"] .page-statistics', css)
        self.assertIn(".page-statistics .filter-controls .form-control", css)
        self.assertIn(".page-statistics .text-dark", css)
        self.assertIn(".page-statistics .table", css)

    def test_statistics_dashboard_filter_controls_group_period_controls_with_smaller_gap(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".statistics-period-control-group {", css)
        filter_controls_block = css.split(".filter-controls {", 1)[1].split("}", 1)[0]
        period_controls_block = css.split(".statistics-period-control-group {", 1)[1].split("}", 1)[0]

        self.assertIn("statistics-period-control-group", template)
        self.assertIn("gap: 0.75rem;", filter_controls_block)
        self.assertIn("gap: 0.25rem;", period_controls_block)
        self.assertNotIn('id="filterType" class="form-select mx-2"', template)
        self.assertNotIn('id="filterDate" class="form-control mx-2"', template)

    def test_statistics_dashboard_period_select_has_stable_width(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn('id="filterType" class="form-select statistics-period-type-select"', template)
        self.assertNotIn('id="filterType" class="form-select" style="width: auto;"', template)
        self.assertIn(".statistics-period-type-select,", css)
        self.assertIn(".statistics-period-control-group .ts-wrapper", css)
        self.assertIn("width: 8.5rem !important;", css)
        self.assertIn("flex: 0 0 8.5rem;", css)

    def test_statistics_dashboard_period_select_has_stable_tomselect_height(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".statistics-period-control-group .ts-control", css)
        self.assertIn("height: 2.75rem;", css)
        self.assertIn("min-height: 2.75rem;", css)
        self.assertIn("flex-wrap: nowrap;", css)
        self.assertIn(".statistics-period-control-group .ts-control > input", css)
        self.assertIn("min-width: 1px !important;", css)
        self.assertIn("width: 1px !important;", css)

    def test_statistics_dashboard_js_uses_theme_aware_chart_options(self) -> None:
        script = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("function getChartTheme()", script)
        self.assertIn("buildTooltipTheme(chartTheme)", script)
        self.assertIn("buildAxisTheme(chartTheme", script)
        self.assertIn("buildLegendTheme(chartTheme)", script)
        self.assertIn("new MutationObserver(refreshChartsForTheme)", script)

    def test_statistics_dashboard_exposes_metric_explanation_modal(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn('id="statistics-metric-help-btn"', template)
        self.assertIn('data-bs-target="#statisticsMetricHelpModal"', template)
        self.assertIn('id="statisticsMetricHelpModal"', template)
        self.assertIn('class="modal-dialog modal-xl modal-dialog-scrollable"', template)
        self.assertIn("指标说明", template)
        self.assertIn("统计周期", template)
        self.assertIn("不纳入总体故障总数", template)
        self.assertIn("光缆中断统计仅包含故障类型为“光缆中断”且未挂起的物理故障", template)
        self.assertIn("长时故障", template)
        self.assertIn("历时大于 0.5 小时", template)
        self.assertIn("P50修复时长", template)
        self.assertIn("P90修复时长", template)
        self.assertIn("超时率", template)
        self.assertIn("历时大于等于 4 小时", template)
        self.assertIn("同一 A 端站点与任一 Z 端站点", template)
        self.assertIn("SLA", template)
        self.assertIn("合并重叠不可用时段", template)


if __name__ == "__main__":
    unittest.main()

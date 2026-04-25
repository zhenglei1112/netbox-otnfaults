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

        self.assertIn("statistics_dashboard.css' %}?v=4", template)
        self.assertIn("statistics_dashboard.js' %}?v=7", template)

    def test_statistics_dashboard_css_covers_light_and_dark_theme_surfaces(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("--statistics-surface", css)
        self.assertIn('[data-bs-theme="dark"] .page-statistics', css)
        self.assertIn(".page-statistics .filter-controls .form-control", css)
        self.assertIn(".page-statistics .text-dark", css)
        self.assertIn(".page-statistics .table", css)

    def test_statistics_dashboard_js_uses_theme_aware_chart_options(self) -> None:
        script = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("function getChartTheme()", script)
        self.assertIn("buildTooltipTheme(chartTheme)", script)
        self.assertIn("buildAxisTheme(chartTheme", script)
        self.assertIn("buildLegendTheme(chartTheme)", script)
        self.assertIn("new MutationObserver(refreshChartsForTheme)", script)


if __name__ == "__main__":
    unittest.main()

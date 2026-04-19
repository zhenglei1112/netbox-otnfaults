import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
LOCAL_ECHARTS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "lib" / "echarts.min.js"


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


if __name__ == "__main__":
    unittest.main()

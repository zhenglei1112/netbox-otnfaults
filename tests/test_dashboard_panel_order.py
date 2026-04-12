import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "dashboard.html"
)


class DashboardPanelOrderTestCase(unittest.TestCase):
    def test_trend_panel_appears_before_category_panel(self) -> None:
        template = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")

        trend_index = template.index('<div class="panel-card" id="trend-card">')
        category_index = template.index('<div class="panel-card" id="category-card">')

        self.assertLess(trend_index, category_index)


if __name__ == "__main__":
    unittest.main()

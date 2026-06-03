import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "dashboard.html"
)


class DashboardPanelOrderTestCase(unittest.TestCase):
    def test_running_board_metrics_and_trend_appear_before_event_queue(self) -> None:
        template = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")

        metrics_index = template.index('<div class="panel-card" id="situation-metrics-card">')
        trend_index = template.index('<div class="panel-card" id="trend-card">')
        event_queue_index = template.index('<div class="panel-card" id="event-queue-card">')

        self.assertLess(metrics_index, trend_index)
        self.assertLess(trend_index, event_queue_index)
        self.assertNotIn('id="situation-scope-card"', template)
        self.assertNotIn('id="category-card"', template)


if __name__ == "__main__":
    unittest.main()

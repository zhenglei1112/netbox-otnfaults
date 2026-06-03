import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"
DASHBOARD_APP_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "dashboard" / "dashboard_app.js"
)


class DashboardHeatmapScopeTestCase(unittest.TestCase):
    def test_running_board_does_not_load_closed_fault_heatmap(self) -> None:
        source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")
        app_source = DASHBOARD_APP_PATH.read_text(encoding="utf-8")

        self.assertNotIn("closed_faults_qs = OtnFault.objects.filter(", source)
        self.assertNotIn("'closed_fault_points': closed_fault_points", source)
        self.assertNotIn("renderHeatmap(data.closed_fault_points || [])", app_source)


if __name__ == "__main__":
    unittest.main()

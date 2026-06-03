import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "dashboard.html"
)
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"


class DashboardProvinceScopeTestCase(unittest.TestCase):
    def test_dashboard_template_removes_province_fault_distribution_panel(self) -> None:
        template = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertNotIn('id="province-card"', template)
        self.assertNotIn('id="province-list"', template)

    def test_dashboard_views_no_longer_builds_province_stats_for_running_board(self) -> None:
        source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertNotIn("province_stats = list(", source)
        self.assertNotIn("all_faults.values('province__name')", source)
        self.assertNotIn("active_faults_qs.values('province__name')", source)


if __name__ == "__main__":
    unittest.main()

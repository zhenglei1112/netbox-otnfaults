import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "dashboard.html"
)
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"


class DashboardProvinceScopeTestCase(unittest.TestCase):
    def test_dashboard_template_labels_province_panel_as_annual_fault_distribution(self) -> None:
        template = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("故障分布", template)
        self.assertNotIn("活跃故障分布", template)

    def test_dashboard_views_builds_province_stats_from_annual_faults(self) -> None:
        source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("province_stats = list(", source)
        self.assertIn("all_faults.values('province__name')", source)
        self.assertNotIn("active_faults_qs.values('province__name')", source)


if __name__ == "__main__":
    unittest.main()

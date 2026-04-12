import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"


class DashboardHeatmapScopeTestCase(unittest.TestCase):
    def test_closed_fault_heatmap_uses_annual_scope(self) -> None:
        source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("closed_faults_qs = OtnFault.objects.filter(", source)
        self.assertIn("fault_occurrence_time__gte=year_start", source)
        self.assertNotIn("fault_occurrence_time__gte=one_month_ago", source)


if __name__ == "__main__":
    unittest.main()

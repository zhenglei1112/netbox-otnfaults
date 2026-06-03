import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"


class DashboardActiveFaultScopeTestCase(unittest.TestCase):
    def test_dashboard_views_show_processing_faults_only(self) -> None:
        source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("processing_faults_qs = OtnFault.objects.filter(", source)
        self.assertIn("active_faults_qs = processing_faults_qs.select_related(", source)
        self.assertIn("fault_status=FaultStatusChoices.PROCESSING", source)
        self.assertNotIn("Q(fault_status='processing') | Q(fault_occurrence_time__gte=twenty_four_hours_ago)", source)
        self.assertIn("active_count = processing_faults_qs.count()", source)
        self.assertNotIn("'closed_fault_points': closed_fault_points", source)


if __name__ == "__main__":
    unittest.main()

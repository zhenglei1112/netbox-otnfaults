import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"


class DashboardActiveFaultScopeTestCase(unittest.TestCase):
    def test_dashboard_views_expand_active_fault_payload_scope_but_keep_summary_processing_only(self) -> None:
        source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("processing_faults_qs = OtnFault.objects.filter(", source)
        self.assertIn("active_faults_qs = OtnFault.objects.filter(", source)
        self.assertIn("Q(fault_status='processing') | Q(fault_occurrence_time__gte=twenty_four_hours_ago)", source)
        self.assertIn("active_count = processing_faults_qs.count()", source)


if __name__ == "__main__":
    unittest.main()

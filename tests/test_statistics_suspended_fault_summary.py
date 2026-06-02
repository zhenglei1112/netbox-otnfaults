import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"


class StatisticsSuspendedFaultSummaryTestCase(unittest.TestCase):
    def test_backend_returns_open_and_total_suspended_counts(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("all_suspended_faults_total_count = qs_all.filter(_suspended_fault_q()).count()", source)
        self.assertIn("all_open_suspended_faults_count = qs_all.filter(_suspended_fault_q()).exclude(fault_status=FaultStatusChoices.CLOSED).count()", source)
        self.assertIn("'suspended_faults': suspended_faults_count", source)
        self.assertIn("'suspended_faults_total': suspended_faults_total_count", source)

    def test_dashboard_displays_open_suspended_count_with_total_as_ratio(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("const suspendedDisplayValue = `${otherOverview.suspended_faults || 0}/${otherOverview.suspended_faults_total || 0}`;", source)
        self.assertIn("name: '挂起的故障（未关闭/总数）'", source)
        self.assertIn("displayValue: suspendedDisplayValue", source)
        self.assertNotIn("infoTitle: '未关闭的挂起故障（总数）'", source)
        self.assertIn("const itemDisplayValue = item && item.displayValue !== undefined ? item.displayValue : undefined;", source)


if __name__ == "__main__":
    unittest.main()

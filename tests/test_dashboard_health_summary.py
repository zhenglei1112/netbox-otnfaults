import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "dashboard.html"
)
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"
PANELS_JS_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "dashboard" / "panels.js"
)


class DashboardHealthSummaryTestCase(unittest.TestCase):
    def test_health_card_template_contains_running_board_core_stats(self) -> None:
        template = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn('id="gauge-value"', template)
        self.assertIn('id="stat-active"', template)
        self.assertIn('id="stat-upcoming-cutovers"', template)
        self.assertIn('id="stat-active-heavy-duties"', template)
        self.assertNotIn('id="stat-temp-recovery"', template)
        self.assertNotIn('id="stat-suspended"', template)

    def test_dashboard_summary_includes_running_board_counts(self) -> None:
        source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("'active_faults': active_count", source)
        self.assertIn("'upcoming_cutovers': len(cutovers_data)", source)
        self.assertIn("'active_heavy_duties': len(heavy_duties_data)", source)
        self.assertIn("'health_score': max(0, 100 - active_count * 5)", source)

    def test_panels_render_running_board_counts(self) -> None:
        source = PANELS_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("stat-upcoming-cutovers", source)
        self.assertIn("summary.upcoming_cutovers", source)
        self.assertIn("stat-active-heavy-duties", source)
        self.assertIn("summary.active_heavy_duties", source)
        self.assertNotIn("summary.temporary_recovery_faults", source)
        self.assertNotIn("summary.suspended_faults", source)


if __name__ == "__main__":
    unittest.main()

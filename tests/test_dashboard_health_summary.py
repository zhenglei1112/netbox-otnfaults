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
    def test_health_card_template_contains_temporary_recovery_and_suspended_stats(self) -> None:
        template = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("id=\"stat-temp-recovery\"", template)
        self.assertIn("id=\"stat-suspended\"", template)

    def test_dashboard_summary_includes_temporary_recovery_and_suspended_counts(self) -> None:
        source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("'temporary_recovery_faults':", source)
        self.assertIn("'suspended_faults':", source)

    def test_panels_render_temporary_recovery_and_suspended_counts(self) -> None:
        source = PANELS_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("stat-temp-recovery", source)
        self.assertIn("summary.temporary_recovery_faults", source)
        self.assertIn("stat-suspended", source)
        self.assertIn("summary.suspended_faults", source)


if __name__ == "__main__":
    unittest.main()

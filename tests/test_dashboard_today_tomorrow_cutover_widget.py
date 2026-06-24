import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard.py"
WIDGET_TEMPLATE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "inc"
    / "dashboard_today_tomorrow_cutover_widget.html"
)


class DashboardTodayTomorrowCutoverWidgetTestCase(unittest.TestCase):
    def test_today_tomorrow_widget_queries_cutovers_with_prefetches(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("class OtnTodayTomorrowCutoverWidget(DashboardWidget):", source)
        self.assertIn(".select_related('province', 'line_supervisor', 'interruption_location_a')", source)
        self.assertIn(".prefetch_related('interruption_location')", source)

    def test_today_tomorrow_widget_prepares_site_information(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("site_a_name = cutover.interruption_location_a.name if cutover.interruption_location_a else '无'", source)
        self.assertIn("site_z_names = [site.name for site in cutover.interruption_location.all()]", source)
        self.assertIn("site_z_display = ', '.join(site_z_names) if site_z_names else '无'", source)
        self.assertIn("'site_a': site_a_name,", source)
        self.assertIn("'site_z': site_z_display,", source)

    def test_today_tomorrow_template_renders_site_information(self) -> None:
        template_source = WIDGET_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(".otn-cutover-sites", template_source)
        self.assertIn(".otn-cutover-site-tag", template_source)
        self.assertIn("{{ cutover.site_a }}", template_source)
        self.assertIn("{{ cutover.site_z }}", template_source)


if __name__ == "__main__":
    unittest.main()

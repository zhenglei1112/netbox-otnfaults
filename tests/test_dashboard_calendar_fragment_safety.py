import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard.py"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "calendar_widget_views.py"


class DashboardCalendarFragmentSafetyTestCase(unittest.TestCase):
    def test_normal_dashboard_render_does_not_consume_page_query_month(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("year_value: str | None = None", source)
        self.assertIn("month_value: str | None = None", source)
        self.assertIn(
            "resolve_requested_month(\n"
            "                year_value,\n"
            "                month_value,",
            source,
        )
        self.assertNotIn("request.GET.get('year')", source)
        self.assertNotIn("request.GET.get('month')", source)

    def test_fragment_views_explicitly_pass_month_and_propagate_errors(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertEqual(source.count("year_value=request.GET.get('year')"), 2)
        self.assertEqual(source.count("month_value=request.GET.get('month')"), 2)
        self.assertEqual(source.count("raise_errors=True"), 2)

    def test_calendar_widgets_hide_tracebacks_from_normal_dashboard_users(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")
        fault_block = source.split("class OtnFaultsCalendarWidget", 1)[1]
        fault_block = fault_block.split("class OtnCutoverCalendarWidget", 1)[0]
        cutover_block = source.split("class OtnCutoverCalendarWidget", 1)[1]
        cutover_block = cutover_block.split("class OtnFaultsPendingReviewWidget", 1)[0]

        for block in (fault_block, cutover_block):
            self.assertIn("if raise_errors:", block)
            self.assertIn("raise", block)
            self.assertIn("日历加载失败，请稍后重试。", block)
            self.assertNotIn("traceback.format_exc()", block)


if __name__ == "__main__":
    unittest.main()

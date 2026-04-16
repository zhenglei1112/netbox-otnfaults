import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard.py"
CALENDAR_TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "inc" / "dashboard_calendar_widget.html"
)


class DashboardCalendarWidgetTestCase(unittest.TestCase):
    def test_calendar_widget_does_not_truncate_daily_fault_dots_to_five(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertNotIn("day_dots[day] = day_dots[day][:5]", source)

    def test_calendar_widget_template_uses_compact_dot_grid_layout(self) -> None:
        template_source = CALENDAR_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(".otn-cal-dots {", template_source)
        self.assertIn("display: flex;", template_source)
        self.assertIn("flex-wrap: wrap;", template_source)
        self.assertIn("justify-content: center;", template_source)
        self.assertIn("max-width: 34px;", template_source)
        self.assertIn("min-height: 13px;", template_source)
        self.assertIn("width: 6px; height: 6px;", template_source)
        self.assertNotIn("display: grid;", template_source)


if __name__ == "__main__":
    unittest.main()

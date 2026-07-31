import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FAULT_TEMPLATE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "inc"
    / "dashboard_calendar_widget.html"
)
CUTOVER_TEMPLATE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "inc"
    / "dashboard_cutover_calendar_widget.html"
)


class DashboardCalendarStyleIsolationTestCase(unittest.TestCase):
    def test_each_calendar_keeps_its_own_minimum_height(self) -> None:
        fault_source = FAULT_TEMPLATE_PATH.read_text(encoding="utf-8")
        cutover_source = CUTOVER_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(".otn-calendar-widget--fault { min-height: 210px; }", fault_source)
        self.assertIn(
            'class="otn-calendar-widget otn-calendar-widget--fault"',
            fault_source,
        )
        self.assertIn(
            ".otn-calendar-widget--cutover { min-height: 320px; }",
            cutover_source,
        )
        self.assertIn(
            'class="otn-calendar-widget otn-calendar-widget--cutover"',
            cutover_source,
        )
        self.assertNotIn(
            ".otn-calendar-widget { position: relative; min-height:",
            fault_source + cutover_source,
        )


if __name__ == "__main__":
    unittest.main()

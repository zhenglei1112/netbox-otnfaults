import importlib.util
import unittest
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NAVIGATION_PATH = REPO_ROOT / "netbox_otnfaults" / "calendar_navigation.py"
SCRIPT_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "dashboard_calendar_navigation.js"
)


class DashboardCalendarNavigationEdgeCaseTestCase(unittest.TestCase):
    def test_out_of_range_year_falls_back_to_current_month(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "calendar_navigation_edge_case",
            NAVIGATION_PATH,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(
            module.resolve_requested_month(
                "0",
                "12",
                date(2026, 7, 31),
                max_future_months=0,
            ),
            (2026, 7),
        )

    def test_fragment_parser_selects_widget_instead_of_leading_style(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "template.content.querySelector('[data-calendar-widget]')",
            source,
        )
        self.assertNotIn("template.content.firstElementChild", source)


if __name__ == "__main__":
    unittest.main()

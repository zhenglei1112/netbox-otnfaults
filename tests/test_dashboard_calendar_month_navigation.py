import importlib.util
import unittest
from datetime import date
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[1]
NAVIGATION_PATH = REPO_ROOT / "netbox_otnfaults" / "calendar_navigation.py"
DASHBOARD_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard.py"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "calendar_widget_views.py"
URLS_PATH = REPO_ROOT / "netbox_otnfaults" / "urls.py"
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
SCRIPT_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "dashboard_calendar_navigation.js"
)


def load_navigation_module() -> ModuleType:
    if not NAVIGATION_PATH.exists():
        raise AssertionError("calendar_navigation.py must be implemented")
    spec = importlib.util.spec_from_file_location("calendar_navigation", NAVIGATION_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("calendar_navigation.py must be importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CalendarMonthNavigationTestCase(unittest.TestCase):
    def test_shift_month_crosses_year_boundaries(self) -> None:
        navigation = load_navigation_module()

        self.assertEqual(navigation.shift_month(2026, 1, -1), (2025, 12))
        self.assertEqual(navigation.shift_month(2026, 12, 1), (2027, 1))

    def test_invalid_requested_month_falls_back_to_current_month(self) -> None:
        navigation = load_navigation_module()
        today = date(2026, 7, 31)

        self.assertEqual(
            navigation.resolve_requested_month("bad", "7", today, max_future_months=0),
            (2026, 7),
        )
        self.assertEqual(
            navigation.resolve_requested_month("2026", "13", today, max_future_months=0),
            (2026, 7),
        )

    def test_fault_calendar_caps_requested_month_at_current_month(self) -> None:
        navigation = load_navigation_module()

        self.assertEqual(
            navigation.resolve_requested_month(
                "2026",
                "8",
                date(2026, 7, 31),
                max_future_months=0,
            ),
            (2026, 7),
        )

    def test_cutover_calendar_caps_requested_month_at_next_month(self) -> None:
        navigation = load_navigation_module()

        self.assertEqual(
            navigation.resolve_requested_month(
                "2027",
                "2",
                date(2026, 12, 20),
                max_future_months=1,
            ),
            (2027, 1),
        )

    def test_past_requested_month_has_no_lower_limit(self) -> None:
        navigation = load_navigation_module()

        self.assertEqual(
            navigation.resolve_requested_month(
                "2018",
                "3",
                date(2026, 7, 31),
                max_future_months=0,
            ),
            (2018, 3),
        )


class CalendarWidgetWiringTestCase(unittest.TestCase):
    def test_widgets_use_distinct_future_limits_and_requested_months(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("max_future_months=0", source)
        self.assertIn("max_future_months=1", source)
        self.assertIn("year_value: str | None = None", source)
        self.assertIn("month_value: str | None = None", source)
        self.assertIn("'can_navigate_next':", source)
        self.assertIn("'previous_month_url':", source)
        self.assertIn("'next_month_url':", source)

    def test_fragment_views_are_login_protected_read_only_get_endpoints(self) -> None:
        self.assertTrue(VIEWS_PATH.exists(), "calendar_widget_views.py must be implemented")
        source = VIEWS_PATH.read_text(encoding="utf-8")
        urls_source = URLS_PATH.read_text(encoding="utf-8")

        self.assertIn("@login_required", source)
        self.assertIn("@require_GET", source)
        self.assertIn("OtnFaultsCalendarWidget().render(", source)
        self.assertIn("OtnCutoverCalendarWidget().render(", source)
        self.assertIn("dashboard/calendar/faults/", urls_source)
        self.assertIn("dashboard/calendar/cutovers/", urls_source)

    def test_templates_render_side_navigation_hotspots(self) -> None:
        for template_path in (FAULT_TEMPLATE_PATH, CUTOVER_TEMPLATE_PATH):
            source = template_path.read_text(encoding="utf-8")

            self.assertIn('data-calendar-widget', source)
            self.assertIn('data-calendar-nav-url="{{ previous_month_url }}"', source)
            self.assertIn('data-calendar-nav-url="{{ next_month_url }}"', source)
            self.assertIn("otn-calendar-nav--previous", source)
            self.assertIn("otn-calendar-nav--next", source)
            self.assertIn("{% if can_navigate_next %}", source)

    def test_navigation_script_replaces_only_the_clicked_widget(self) -> None:
        self.assertTrue(SCRIPT_PATH.exists(), "calendar navigation script must be implemented")
        source = SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("button.closest('[data-calendar-widget]')", source)
        self.assertIn("fetch(button.dataset.calendarNavUrl", source)
        self.assertIn("credentials: 'same-origin'", source)
        self.assertIn("widget.replaceWith(replacement)", source)
        self.assertIn("button.disabled = true", source)

    def test_navigation_arrows_are_hidden_until_hover_or_focus(self) -> None:
        for template_path in (FAULT_TEMPLATE_PATH, CUTOVER_TEMPLATE_PATH):
            source = template_path.read_text(encoding="utf-8")

            self.assertIn("opacity: 0;", source)
            self.assertIn(".otn-calendar-nav:hover", source)
            self.assertIn(".otn-calendar-nav:focus-visible", source)
            self.assertIn("top: 50%;", source)
            self.assertIn("transform: translateY(-50%);", source)


if __name__ == "__main__":
    unittest.main()

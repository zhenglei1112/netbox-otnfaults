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

    def test_calendar_widget_builds_fault_list_links_for_each_day(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("reverse('plugins:netbox_otnfaults:otnfault_list')", source)
        self.assertIn("'fault_occurrence_time_after':", source)
        self.assertIn("'fault_occurrence_time_before':", source)
        self.assertIn("'fault_list_url':", source)

    def test_calendar_widget_includes_leading_previous_month_dates(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("from datetime import date, timedelta", source)
        self.assertIn("calendar_start = first_day - timedelta(days=first_weekday)", source)
        self.assertIn("fault_occurrence_time__date__gte=calendar_start", source)
        self.assertIn("day_dots: dict[date, list[str]] = {}", source)
        self.assertIn("fault_day = timezone.localtime(occ_time).date()", source)
        self.assertIn("for offset in range(first_weekday):", source)
        self.assertIn("day_date = calendar_start + timedelta(days=offset)", source)
        self.assertIn("'is_current_month': day_date.month == month", source)
        self.assertIn("'dots': day_dots.get(day_date, [])", source)
        self.assertNotIn("cal_cells: list[dict | None] = [None] * first_weekday", source)

    def test_calendar_widget_template_links_date_cells_to_fault_list(self) -> None:
        template_source = CALENDAR_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn('href="{{ cell.fault_list_url }}"', template_source)
        self.assertIn("otn-cal-cell-link", template_source)

    def test_calendar_widget_template_grays_previous_month_dates(self) -> None:
        template_source = CALENDAR_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(".otn-cal-outside-month .otn-cal-day", template_source)
        self.assertIn("color: #adb5bd;", template_source)
        self.assertIn("{% if not cell.is_current_month %}otn-cal-outside-month{% endif %}", template_source)


if __name__ == "__main__":
    unittest.main()

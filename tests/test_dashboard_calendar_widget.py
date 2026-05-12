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

    def test_calendar_widget_only_renders_four_visible_fault_categories(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("CALENDAR_VISIBLE_FAULT_CATEGORIES: tuple[str, ...] = (", source)
        self.assertIn("FaultCategoryChoices.AC_FAULT", source)
        self.assertIn("FaultCategoryChoices.FIBER_BREAK", source)
        self.assertIn("FaultCategoryChoices.POWER_FAULT", source)
        self.assertIn("FaultCategoryChoices.DEVICE_FAULT", source)
        visible_categories_block = source.split("CALENDAR_VISIBLE_FAULT_CATEGORIES: tuple[str, ...] = (", 1)[1]
        visible_categories_block = visible_categories_block.split(")", 1)[0]
        self.assertNotIn("FaultCategoryChoices.FIBER_DEGRADATION", visible_categories_block)
        self.assertNotIn("FaultCategoryChoices.FIBER_JITTER", visible_categories_block)
        self.assertIn("fault_category__in=CALENDAR_VISIBLE_FAULT_CATEGORIES", source)
        self.assertIn("if cat not in CALENDAR_VISIBLE_FAULT_CATEGORIES:", source)

    def test_calendar_widget_uses_reference_fault_category_colors(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("FaultCategoryChoices.AC_FAULT: '#F4C542'", source)
        self.assertIn("FaultCategoryChoices.FIBER_BREAK: '#E53935'", source)
        self.assertIn("FaultCategoryChoices.POWER_FAULT: '#2F6BFF'", source)
        self.assertIn("FaultCategoryChoices.DEVICE_FAULT: '#8B5CF6'", source)
        category_colors_block = source.split("CATEGORY_CSS_COLORS: dict[str, str] = {", 1)[1]
        category_colors_block = category_colors_block.split("}", 1)[0]
        self.assertNotIn("FaultCategoryChoices.FIBER_DEGRADATION", category_colors_block)
        self.assertNotIn("FaultCategoryChoices.FIBER_JITTER", category_colors_block)

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

    def test_calendar_widget_marks_2026_public_holidays_and_makeup_workdays(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("CHINA_PUBLIC_HOLIDAYS: set[date] = {", source)
        self.assertIn("date(2026, 5, 1)", source)
        self.assertIn("date(2026, 5, 5)", source)
        self.assertIn("CHINA_MAKEUP_WORKDAYS: set[date] = {", source)
        self.assertIn("date(2026, 5, 9)", source)
        self.assertIn("holiday_marker = _get_china_holiday_marker(day_date)", source)
        self.assertIn("'holiday_marker': holiday_marker", source)

    def test_calendar_widget_template_renders_holiday_marker_after_day(self) -> None:
        template_source = CALENDAR_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(".otn-cal-holiday-marker", template_source)
        self.assertIn(".otn-cal-holiday-marker--workday", template_source)
        self.assertIn("color: #0d6efd;", template_source)
        self.assertIn("{% if cell.holiday_marker %}", template_source)
        self.assertIn('{% if cell.holiday_marker == "班" %} otn-cal-holiday-marker--workday{% endif %}', template_source)
        self.assertIn('<span class="otn-cal-holiday-marker{% if cell.holiday_marker == "班" %} otn-cal-holiday-marker--workday{% endif %}">{{ cell.holiday_marker }}</span>', template_source)


if __name__ == "__main__":
    unittest.main()

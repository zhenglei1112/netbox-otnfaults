import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard.py"
CUTOVER_CALENDAR_TEMPLATE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "inc"
    / "dashboard_cutover_calendar_widget.html"
)


class DashboardCutoverCalendarWidgetTestCase(unittest.TestCase):
    def test_cutover_calendar_widget_queries_planned_cutovers_with_impact_counts(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("from django.db.models import Count", source)
        self.assertIn("CutoverTask", source)
        self.assertIn("CutoverStatusChoices", source)
        self.assertIn("class OtnCutoverCalendarWidget(DashboardWidget):", source)
        self.assertIn('default_title = "割接月历"', source)
        self.assertIn("CutoverTask.objects.restrict(request.user, 'view')", source)
        self.assertIn("planned_cutover_time__date__gte=calendar_start", source)
        self.assertIn("planned_cutover_time__date__lte=last_day", source)
        self.assertIn(".annotate(impact_count=Count('impacts', distinct=True))", source)
        self.assertIn("timezone.localtime(cutover.planned_cutover_time).date()", source)

    def test_cutover_calendar_widget_builds_list_links_and_compact_summaries(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("reverse('plugins:netbox_otnfaults:cutovertask_list')", source)
        self.assertIn("'planned_cutover_time_after':", source)
        self.assertIn("'planned_cutover_time_before':", source)
        self.assertIn("'cutover_list_url':", source)
        self.assertIn(".select_related('province')", source)
        self.assertIn("'province': str(cutover.province) if cutover.province else ''", source)
        self.assertIn("'visible_cutovers': day_cutovers.get(day_date, [])[:1]", source)
        self.assertIn("'hidden_cutover_count': max(len(day_cutovers.get(day_date, [])) - 1, 0)", source)
        self.assertIn("impact_count = getattr(cutover, 'impact_count', 0)", source)
        self.assertIn("'impact_count': impact_count", source)
        self.assertIn("'location_short': _truncate_cutover_location(cutover.cutover_location)", source)

    def test_cutover_calendar_template_renders_compact_status_colored_items(self) -> None:
        template_source = CUTOVER_CALENDAR_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(".otn-cutover-cal-item", template_source)
        self.assertIn(".otn-cutover-cal-item--applying", template_source)
        self.assertIn(".otn-cutover-cal-item--pending_implementation", template_source)
        self.assertIn(".otn-cutover-cal-item--completed", template_source)
        self.assertIn(".otn-cutover-cal-item--cancelled", template_source)
        self.assertIn("{% for cutover in cell.visible_cutovers %}", template_source)
        self.assertIn(".otn-cutover-cal-line--meta", template_source)
        self.assertIn(".otn-cutover-cal-line--location", template_source)
        self.assertIn(".otn-cutover-cal-line--impact", template_source)
        self.assertIn("{{ cutover.time }}", template_source)
        self.assertIn("{{ cutover.province }}", template_source)
        self.assertIn("{{ cutover.location_short }}", template_source)
        self.assertIn("{{ cutover.impact_count }}项", template_source)
        self.assertIn("{% if cell.hidden_cutover_count %}", template_source)
        self.assertIn("+{{ cell.hidden_cutover_count }}", template_source)
        self.assertNotIn("otn-cal-dot", template_source)


if __name__ == "__main__":
    unittest.main()

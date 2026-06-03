import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"
DASHBOARD_HTML_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "dashboard.html"
DASHBOARD_JS_APP_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "dashboard" / "dashboard_app.js"
)
DASHBOARD_JS_PANELS_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "dashboard" / "panels.js"
)
DASHBOARD_CSS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "dashboard.css"


class DashboardSituationBoardTestCase(unittest.TestCase):
    def test_dashboard_api_returns_cutovers_and_omits_closed_heatmap(self) -> None:
        source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("CutoverTask", source)
        self.assertIn("CutoverStatusChoices", source)
        self.assertIn("upcoming_cutovers_qs = CutoverTask.objects.filter(", source)
        self.assertIn("planned_cutover_time__gte=now", source)
        self.assertIn("planned_cutover_time__lte=cutover_window_end", source)
        self.assertIn("status__in=[CutoverStatusChoices.APPLYING, CutoverStatusChoices.PENDING_IMPLEMENTATION]", source)
        self.assertIn("'cutovers': cutovers_data", source)
        self.assertNotIn("closed_faults_qs = OtnFault.objects.filter(", source)
        self.assertNotIn("renderHeatmap(data.closed_fault_points || [])", (DASHBOARD_JS_APP_PATH).read_text(encoding="utf-8"))

    def test_dashboard_template_uses_situation_board_layout(self) -> None:
        source = DASHBOARD_HTML_PATH.read_text(encoding="utf-8")

        self.assertIn('id="situation-metrics-card"', source)
        self.assertIn('id="stat-upcoming-cutovers"', source)
        self.assertIn('id="stat-active-heavy-duties"', source)
        self.assertIn('id="trend-card"', source)
        self.assertIn('id="trend-canvas"', source)
        self.assertIn('id="event-queue-card"', source)
        self.assertIn('id="event-queue"', source)
        self.assertIn('id="event-focus-card"', source)
        self.assertNotIn('id="situation-scope-card"', source)
        self.assertNotIn('class="scope-list"', source)
        self.assertNotIn("展示口径", source)
        self.assertNotIn('id="category-card"', source)
        self.assertNotIn('id="province-card"', source)

    def test_dashboard_panels_render_three_event_types(self) -> None:
        source = DASHBOARD_JS_PANELS_PATH.read_text(encoding="utf-8")

        self.assertIn("updateSituationMetrics", source)
        self.assertIn("updateTrendChart", source)
        self.assertIn("updateEventQueue", source)
        self.assertIn("_buildDashboardEvents", source)
        self.assertIn("type: 'cutover'", source)
        self.assertIn("type: 'heavy_duty'", source)
        self.assertIn("type: 'fault'", source)
        self.assertIn("showEventFocus", source)
        self.assertIn("_renderCutoverFocus", source)
        self.assertIn("_renderHeavyDutyFocus", source)
        self.assertIn("_renderFaultFocus", source)

    def test_dashboard_app_wires_events_without_heavy_duty_map_layer(self) -> None:
        source = DASHBOARD_JS_APP_PATH.read_text(encoding="utf-8")

        self.assertIn("Panels.updateSituationMetrics(data.summary || {})", source)
        self.assertIn("Panels.updateTrendChart(data.trend_24h || [])", source)
        self.assertIn("Panels.updateEventQueue(data)", source)
        self.assertIn("Panels.updateTicker(Panels.buildDashboardEvents(data))", source)
        self.assertIn("Panels.updateHeavyDuty(data.heavy_duties || [])", source)
        self.assertNotIn("MapEngine.renderHeavy", source)
        self.assertNotIn("MapEngine.renderHeatmap", source)

    def test_dashboard_css_has_running_board_components(self) -> None:
        source = DASHBOARD_CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".situation-metrics", source)
        self.assertIn(".event-queue", source)
        self.assertIn(".event-item--cutover", source)
        self.assertIn(".event-item--heavy_duty", source)
        self.assertIn(".event-item--fault", source)


if __name__ == "__main__":
    unittest.main()

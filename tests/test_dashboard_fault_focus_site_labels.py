import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"
MAP_ENGINE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "dashboard"
    / "map_engine.js"
)
DASHBOARD_APP_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "dashboard"
    / "dashboard_app.js"
)


class DashboardFaultFocusSiteLabelsTestCase(unittest.TestCase):
    def test_active_fault_payload_exposes_related_site_ids(self) -> None:
        source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("'site_a_id': fault.interruption_location_a_id", source)
        self.assertIn("'site_z_ids': [s.pk for s in fault.interruption_location.all()]", source)

    def test_map_engine_has_fault_focus_site_label_layer(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("'sites-focus-label'", source)
        self.assertIn("'sites-focus-glow'", source)
        self.assertIn("'sites-focus-core'", source)
        self.assertIn("'text-allow-overlap': true", source)
        self.assertIn("'text-ignore-placement': true", source)
        self.assertIn("function focusFaultSites(fault)", source)
        self.assertIn("function clearFaultSiteFocus()", source)
        self.assertIn("map.setFilter('sites-focus-label'", source)
        self.assertIn("focusFaultSites,", source)
        self.assertIn("clearFaultSiteFocus,", source)

    def test_fault_focus_temporarily_disables_regular_site_label_collision(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("function _setRegularSiteLabelCollision(enabled)", source)
        self.assertIn("map.setLayoutProperty('sites-label', 'text-allow-overlap', !enabled);", source)
        self.assertIn("map.setLayoutProperty('sites-label', 'text-ignore-placement', !enabled);", source)
        self.assertIn("_setRegularSiteLabelCollision(false);", source)
        self.assertIn("_setRegularSiteLabelCollision(true);", source)

    def test_fault_focus_hides_focused_sites_from_regular_site_labels(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("function _applyRegularSiteLabelFilter()", source)
        self.assertIn("map.setFilter('sites-label', null);", source)
        self.assertIn("['!', ['in', ['get', 'id'], ['literal', focusedSiteIds]]]", source)
        self.assertGreaterEqual(source.count("_applyRegularSiteLabelFilter();"), 3)

    def test_fault_focus_filters_use_expression_syntax_consistently(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("const emptySiteFilter = ['in', ['get', 'id'], ['literal', []]];", source)
        self.assertIn("const focusedSiteFilter = ['in', ['get', 'id'], ['literal', focusedSiteIds]];", source)
        self.assertNotIn("['in', 'id', -1]", source)
        self.assertNotIn("['!in', 'id']", source)

    def test_fault_focus_only_emphasizes_related_site_points(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("'sites-focus-glow'", source)
        self.assertIn("'sites-focus-core'", source)
        self.assertIn("'circle-radius': 16", source)
        self.assertIn("'circle-radius': 7", source)
        self.assertIn("if (map.getLayer('sites-focus-core')) map.setFilter('sites-focus-core', focusedSiteFilter);", source)
        self.assertNotIn("function _setRegularSitePointFocus(enabled)", source)
        self.assertNotIn("map.setPaintProperty('sites-core', 'circle-radius'", source)
        self.assertNotIn("map.setPaintProperty('sites-glow', 'circle-radius'", source)

    def test_dashboard_focus_callbacks_sync_site_label_focus(self) -> None:
        source = DASHBOARD_APP_PATH.read_text(encoding="utf-8")

        self.assertIn("MapEngine.focusFaultSites(fault);", source)
        self.assertIn("MapEngine.clearFaultSiteFocus();", source)

    def test_layer_stack_keeps_focus_site_labels_above_heatmap(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")
        stack = source.split("const DASHBOARD_LAYER_STACK = [", 1)[1].split("];", 1)[0]

        self.assertLess(stack.index("'sites-label'"), stack.index("'sites-focus-label'"))
        self.assertLess(stack.index("'sites-core'"), stack.index("'sites-focus-glow'"))
        self.assertLess(stack.index("'sites-focus-glow'"), stack.index("'sites-focus-core'"))
        self.assertLess(stack.index("'sites-focus-core'"), stack.index("'sites-focus-label'"))
        self.assertLess(stack.index("'closed-heatmap-layer'"), stack.index("'sites-focus-glow'"))
        self.assertLess(stack.index("'sites-focus-label'"), stack.index("'paths-fault-glow'"))

    def test_site_ids_are_normalized_before_filtering(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("properties: { name: s.name, id: String(s.id) }", source)
        self.assertIn("ids.push(String(fault.site_a_id));", source)
        self.assertIn("ids.push(String(siteId));", source)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_MODES_PATH = REPO_ROOT / "netbox_otnfaults" / "map_modes.py"
API_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "views.py"
API_URLS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "urls.py"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "unified_map.html"
FAULT_MODE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "modes"
    / "fault_mode.js"
)
LAYER_TOGGLE_CONTROL_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "controls"
    / "LayerToggleControl.js"
)


class FaultMapPathGroupOverlayTestCase(unittest.TestCase):
    def test_api_exposes_path_group_map_overlays_endpoint(self) -> None:
        api_source = API_VIEWS_PATH.read_text(encoding="utf-8")
        urls_source = API_URLS_PATH.read_text(encoding="utf-8")

        self.assertIn("def path_group_map_overlays(request: Request) -> Response", api_source)
        self.assertIn("Prefetch(", api_source)
        self.assertIn("select_related('site')", api_source)
        self.assertIn("to_attr='overlay_paths'", api_source)
        self.assertIn("to_attr='overlay_group_sites'", api_source)
        self.assertIn("'paths': path_features", api_source)
        self.assertIn("'sites': site_features", api_source)
        self.assertIn("path('path-groups/map-overlays/'", urls_source)

    def test_fault_map_injects_path_group_overlay_url(self) -> None:
        view_source = VIEWS_PATH.read_text(encoding="utf-8")
        template_source = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("'path_group_overlays_url': reverse('plugins-api:netbox_otnfaults-api:path-group-map-overlays')", view_source)
        self.assertIn("pathGroupOverlaysUrl: '{{ path_group_overlays_url|escapejs }}'", template_source)

    def test_fault_mode_passes_overlay_url_to_layer_toggle(self) -> None:
        source = FAULT_MODE_PATH.read_text(encoding="utf-8")

        self.assertIn("pathGroupOverlaysUrl: this.config.pathGroupOverlaysUrl", source)
        self.assertIn("enablePathGroupOverlays: true", source)

    def test_map_modes_cache_bust_layer_toggle_control(self) -> None:
        source = MAP_MODES_PATH.read_text(encoding="utf-8")

        self.assertIn("'controls/LayerToggleControl.js?v=pathgroup-overlays-3'", source)

    def test_layer_toggle_renders_and_toggles_path_group_overlays(self) -> None:
        source = LAYER_TOGGLE_CONTROL_PATH.read_text(encoding="utf-8")

        self.assertIn("this.pathGroupOverlaysUrl = this.options.pathGroupOverlaysUrl", source)
        self.assertIn("this.selectedPathGroupIds = new Set()", source)
        self.assertIn("this.createPathGroupOverlaySelector(menu)", source)
        self.assertIn("fetch(this.pathGroupOverlaysUrl", source)
        self.assertIn("togglePathGroupOverlay(group.id, input.checked)", source)
        self.assertIn("path-group-overlay-${groupId}-paths", source)
        self.assertIn("path-group-overlay-${groupId}-sites", source)
        self.assertIn("path-group-overlay-${groupId}-site-labels", source)
        self.assertIn("line-color\": \"#FFD700\"", source)
        self.assertIn("circle-color\": [\"get\", \"color\"]", source)

    def test_path_group_overlays_are_inserted_above_fault_map_layers(self) -> None:
        source = LAYER_TOGGLE_CONTROL_PATH.read_text(encoding="utf-8")

        self.assertIn("getPathGroupOverlayBeforeLayerId()", source)
        self.assertIn("'fault-points-layer'", source)
        self.assertIn("this.map.moveLayer(id, beforeLayerId)", source)
        self.assertIn("this.raisePathGroupOverlayLayers(groupId)", source)

    def test_layer_toggle_exposes_overlay_debug_state(self) -> None:
        source = LAYER_TOGGLE_CONTROL_PATH.read_text(encoding="utf-8")

        self.assertIn("getPathGroupOverlayDebug()", source)
        self.assertIn("pathFeatureCount", source)
        self.assertIn("siteFeatureCount", source)
        self.assertIn("sourceExists", source)
        self.assertIn("visibility", source)

    def test_selected_path_group_overlays_fit_map_bounds(self) -> None:
        source = LAYER_TOGGLE_CONTROL_PATH.read_text(encoding="utf-8")

        self.assertIn("fitSelectedPathGroupOverlays()", source)
        self.assertIn("new maplibregl.LngLatBounds()", source)
        self.assertIn("this.map.fitBounds(bounds", source)
        self.assertIn("this._extendOverlayBoundsWithGeometry(bounds, feature.geometry)", source)

    def test_path_group_overlays_do_not_follow_all_topology_visibility(self) -> None:
        source = LAYER_TOGGLE_CONTROL_PATH.read_text(encoding="utf-8")
        update_arcgis_method = source.split("updateArcgisLayersVisibility() {", 1)[1].split("\n    }", 1)[0]

        self.assertIn("this.setPathGroupOverlayVisibility(groupId, checked);", source)
        self.assertNotIn("checked && this.arcgisVisible", source)
        self.assertNotIn("selectedPathGroupIds", update_arcgis_method)


if __name__ == "__main__":
    unittest.main()

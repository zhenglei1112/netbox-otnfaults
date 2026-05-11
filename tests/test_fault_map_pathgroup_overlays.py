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
        self.assertIn("path_count=Count('paths', distinct=True)", api_source)
        self.assertIn("site_count=Count('group_sites', distinct=True)", api_source)
        self.assertIn("'path_count': group.path_count", api_source)
        self.assertIn("'site_count': group.site_count", api_source)
        self.assertNotIn("'paths': path_features", api_source.split("def path_group_map_overlays", 1)[1].split("def path_group_map_overlay_detail", 1)[0])
        self.assertNotIn("'sites': site_features", api_source.split("def path_group_map_overlays", 1)[1].split("def path_group_map_overlay_detail", 1)[0])
        self.assertIn("path('path-groups/map-overlays/'", urls_source)

    def test_api_exposes_single_path_group_overlay_detail_endpoint(self) -> None:
        api_source = API_VIEWS_PATH.read_text(encoding="utf-8")
        urls_source = API_URLS_PATH.read_text(encoding="utf-8")

        self.assertIn("def path_group_map_overlay_detail(request: Request, pk: int) -> Response", api_source)
        self.assertNotIn("include_paths", api_source.split("def path_group_map_overlay_detail", 1)[1].split("@api_view", 1)[0])
        self.assertIn("'bbox': _path_group_overlay_bbox(path_features, site_features)", api_source)
        self.assertIn("path('path-groups/<int:pk>/map-overlay/'", urls_source)

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
        self.assertIn("this.pathGroupOverlayDetails = new Map()", source)
        self.assertIn("this.selectedPathGroupIds = new Set()", source)
        self.assertIn("this.createPathGroupOverlaySelector(menu)", source)
        self.assertIn("fetch(this.pathGroupOverlaysUrl", source)
        self.assertIn("togglePathGroupOverlay(group.id, input.checked)", source)
        self.assertIn("path-group-overlay-paths", source)
        self.assertIn("path-group-overlay-sites", source)
        self.assertIn("path-group-overlay-site-labels", source)
        self.assertIn("refreshPathGroupOverlaySources()", source)
        self.assertIn("line-color\": \"#FFD700\"", source)
        self.assertIn("circle-color\": [\"get\", \"color\"]", source)

    def test_path_group_overlays_are_inserted_above_fault_map_layers(self) -> None:
        source = LAYER_TOGGLE_CONTROL_PATH.read_text(encoding="utf-8")

        self.assertIn("getPathGroupOverlayBeforeLayerId()", source)
        self.assertIn("'fault-points-layer'", source)
        self.assertIn("this.map.moveLayer(id, beforeLayerId)", source)
        self.assertIn("this.raisePathGroupOverlayLayers()", source)

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
        self.assertIn("this._extendOverlayBoundsWithBbox(bounds, detail.bbox)", source)

    def test_path_group_overlays_do_not_follow_all_topology_visibility(self) -> None:
        source = LAYER_TOGGLE_CONTROL_PATH.read_text(encoding="utf-8")
        update_arcgis_method = source.split("updateArcgisLayersVisibility() {", 1)[1].split("\n    }", 1)[0]

        self.assertIn("this.setPathGroupOverlayVisibility(this.selectedPathGroupIds.size > 0);", source)
        self.assertNotIn("checked && this.arcgisVisible", source)
        self.assertNotIn("selectedPathGroupIds", update_arcgis_method)

    def test_path_group_overlays_do_not_use_pmtiles(self) -> None:
        source = LAYER_TOGGLE_CONTROL_PATH.read_text(encoding="utf-8")

        self.assertNotIn("canUsePathGroupPmtiles", source)
        self.assertNotIn("include_paths", source)
        self.assertNotIn("path-group-overlay-pmtiles-paths", source)
        self.assertNotIn("path_group_ids", source)
        self.assertNotIn("refreshPathGroupPmtilesFilter", source)

    def test_pmtiles_export_does_not_include_path_group_properties(self) -> None:
        export_source = (
            REPO_ROOT / "netbox_otnfaults" / "scripts" / "export_paths_geojson.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("prefetch_related('groups')", export_source)
        self.assertNotIn('"path_group_ids":', export_source)
        self.assertNotIn('"path_group_names":', export_source)
        self.assertNotIn("'|' + '|'.join", export_source)


if __name__ == "__main__":
    unittest.main()

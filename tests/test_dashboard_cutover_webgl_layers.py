import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_ENGINE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "dashboard"
    / "map_engine.js"
)
DASHBOARD_CSS_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "css"
    / "dashboard.css"
)
DASHBOARD_TEMPLATE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "dashboard.html"
)


class DashboardCutoverWebGLLayersTestCase(unittest.TestCase):
    def test_cutovers_use_geojson_webgl_layers(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")
        renderer = source.split("function renderCutoverMarkers", 1)[1].split(
            "function renderHeatmap", 1
        )[0]

        self.assertIn("map.addSource('cutovers'", renderer)
        self.assertIn("map.getSource('cutovers').setData(geojson)", renderer)
        for layer_id in ("cutovers-glow", "cutovers-core", "cutovers-icon"):
            self.assertIn(f"id: '{layer_id}'", renderer)
        self.assertNotIn("new maplibregl.Marker", renderer)
        self.assertNotIn("_cutoverMarkers", renderer)

    def test_cutover_wrench_is_registered_as_a_map_image(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")
        template = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("FAULT_SVG_ICONS.cutover", source)
        self.assertIn("map.addImage(CUTOVER_ICON_IMAGE_ID", source)
        self.assertIn("'icon-image': CUTOVER_ICON_IMAGE_ID", source)
        self.assertIn("js/utils/fault_icons.js", template)

    def test_cutover_layers_are_stacked_above_fault_layers(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")
        stack = source.split("const DASHBOARD_LAYER_STACK = [", 1)[1].split(
            "];", 1
        )[0]
        layer_ids = [
            "'faults-core'",
            "'cutovers-glow'",
            "'cutovers-core'",
            "'cutovers-icon'",
        ]
        for layer_id in layer_ids:
            self.assertIn(layer_id, stack)
        positions = [stack.index(layer_id) for layer_id in layer_ids]

        self.assertEqual(positions, sorted(positions))

    def test_html_marker_styles_are_removed(self) -> None:
        css = DASHBOARD_CSS_PATH.read_text(encoding="utf-8")

        for selector in (
            ".cutover-map-marker",
            ".cutover-marker-glow",
            ".cutover-marker-core",
        ):
            self.assertNotIn(selector, css)


if __name__ == "__main__":
    unittest.main()

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


class DashboardLayerOrderTestCase(unittest.TestCase):
    def test_dashboard_layer_stack_matches_requested_bottom_to_top_order(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        expected_order = [
            "'province-shadow'",
            "'province-extrusion'",
            "'province-border-glow-bottom'",
            "'province-border-top'",
            "'province-labels'",
            "'otn-paths-base-glow'",
            "'otn-paths-base-main'",
            "'sites-glow'",
            "'sites-core'",
            "'sites-label'",
            "'closed-heatmap-layer'",
            "'sites-focus-glow'",
            "'sites-focus-core'",
            "'sites-focus-label'",
            "'paths-fault-glow'",
            "'paths-fault-main'",
            "'paths-label'",
            "'paths-detail'",
            "'faults-pulse'",
            "'faults-glow'",
            "'faults-core'",
        ]

        stack = source.split("const DASHBOARD_LAYER_STACK = [", 1)[1].split("];", 1)[0]
        last_index = -1
        for layer_id in expected_order:
            current_index = stack.index(layer_id)
            self.assertGreater(current_index, last_index, layer_id)
            last_index = current_index

        self.assertIn("function _restackDashboardLayers()", source)
        self.assertIn("for (var i = DASHBOARD_LAYER_STACK.length - 1; i >= 0; i--)", source)
        self.assertIn("map.moveLayer(layerId, beforeLayerId);", source)

    def test_dashboard_renderers_restack_after_each_dynamic_layer_group(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertGreaterEqual(source.count("_restackDashboardLayers();"), 6)
        self.assertNotIn("var candidateLayers = ['sites-glow', 'paths-glow', 'paths-main'];", source)
        self.assertNotIn("function _restackTopologyLayer()", source)


if __name__ == "__main__":
    unittest.main()

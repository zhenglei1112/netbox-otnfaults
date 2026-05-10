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


class DashboardGreenNetworkLayersTestCase(unittest.TestCase):
    def test_sites_and_base_paths_render_with_green_palette(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("'line-color': 'rgba(16, 185, 129, 0.16)'", source)
        self.assertIn("'line-color': 'rgba(16, 185, 129, 0.48)'", source)
        self.assertIn("'circle-color': 'rgba(16, 185, 129, 0.14)'", source)
        self.assertIn("'circle-color': '#10B981'", source)
        self.assertIn("'circle-stroke-color': 'rgba(16, 185, 129, 0.65)'", source)
        self.assertIn("'text-color': 'rgba(167, 243, 208, 0.82)'", source)

        self.assertNotIn("'circle-color': '#00D2FF'", source)

    def test_fault_related_paths_keep_red_alert_palette(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("const FAULT_PATH_COLOR = '#FF1E1E';", source)
        self.assertIn("'line-color': 'rgba(255, 30, 30, 0.25)'", source)
        self.assertIn("['==', ['get', 'has_fault'], 1], '#FF6B6B'", source)

        self.assertNotIn("const FAULT_PATH_COLOR = '#22C55E';", source)
        self.assertNotIn("'line-color': 'rgba(34, 197, 94, 0.28)'", source)
        self.assertNotIn("['==', ['get', 'has_fault'], 1], '#86EFAC'", source)


if __name__ == "__main__":
    unittest.main()

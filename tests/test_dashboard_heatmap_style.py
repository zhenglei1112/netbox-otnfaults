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


class DashboardHeatmapStyleTestCase(unittest.TestCase):
    def test_dashboard_heatmap_uses_tempered_yearly_density_style(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("'heatmap-intensity': ['interpolate', ['linear'], ['zoom'],", source)
        self.assertIn("3, 1.0,", source)
        self.assertIn("6, 0.9,", source)
        self.assertIn("10, 1.2", source)
        self.assertIn("'heatmap-radius': ['interpolate', ['linear'], ['zoom'],", source)
        self.assertIn("3, 28,", source)
        self.assertIn("5, 22,", source)
        self.assertIn("7, 16,", source)
        self.assertIn("10, 10", source)
        self.assertIn("0.82, 'rgba(255, 138, 0, 0.65)'", source)
        self.assertIn("1.0,  'rgba(255, 50, 30, 0.72)'", source)
        self.assertIn("'heatmap-opacity': ['interpolate', ['linear'], ['zoom'],", source)
        self.assertIn("3, 0.45,", source)
        self.assertIn("7, 0.38,", source)
        self.assertIn("10, 0.3", source)

        self.assertNotIn("3, 3.0,", source)
        self.assertNotIn("3, 50,", source)
        self.assertNotIn("0.8,  'rgba(255, 138, 0, 0.8)'", source)


if __name__ == "__main__":
    unittest.main()

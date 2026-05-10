import re
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
DIRECTING_ENGINE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "dashboard"
    / "directing_engine.js"
)


class DashboardFaultFocusZoomTestCase(unittest.TestCase):
    def test_map_engine_exports_site_label_min_zoom(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("const SITE_LABEL_MIN_ZOOM = 6", source)
        self.assertIn("minzoom: SITE_LABEL_MIN_ZOOM", source)
        self.assertIn("getSiteLabelMinZoom,", source)

    def test_fault_focus_zoom_is_above_site_label_threshold(self) -> None:
        source = DIRECTING_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("const FAULT_FOCUS_SITE_LABEL_ZOOM_MARGIN = 2.5", source)
        self.assertIn("MapEngine.getSiteLabelMinZoom()", source)
        self.assertIn("faultFocusZoom", source)
        self.assertIn("MapEngine.flyTo(currentFault.lng, currentFault.lat, faultFocusZoom", source)
        self.assertNotIn("MapEngine.flyTo(currentFault.lng, currentFault.lat, 8,", source)

        margin = float(
            re.search(r"FAULT_FOCUS_SITE_LABEL_ZOOM_MARGIN = ([0-9.]+)", source).group(1)
        )
        self.assertGreaterEqual(margin, 2.0)


if __name__ == "__main__":
    unittest.main()

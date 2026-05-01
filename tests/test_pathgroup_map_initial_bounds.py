import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCATION_MODE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "modes"
    / "location_mode.js"
)


class PathGroupMapInitialBoundsTestCase(unittest.TestCase):
    def test_pathgroup_initial_view_uses_combined_path_and_site_bounds(self) -> None:
        source = LOCATION_MODE_PATH.read_text(encoding="utf-8")

        self.assertIn("this._fitPathGroupBounds(", source)
        self.assertIn("_fitPathGroupBounds(highlightPathData, sitesData) {", source)
        self.assertIn("this._extendBoundsWithGeometry(bounds, feature.geometry);", source)
        self.assertIn("bounds.extend([site.lng, site.lat]);", source)
        self.assertIn('if (this.config.mode !== "pathgroup") return;', source)
        self.assertIn("map.fitBounds(bounds, { padding: 80, maxZoom: 12 });", source)
        self.assertIn("this.mapBase.setHomeBounds(bounds);", source)


if __name__ == "__main__":
    unittest.main()

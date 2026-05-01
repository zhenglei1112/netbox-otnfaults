from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"
LOCATION_MODE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "modes"
    / "location_mode.js"
)


class LocationMapFaultSitesViewTestCase(unittest.TestCase):
    def test_fault_location_map_includes_a_and_all_z_sites_in_view_bounds(self) -> None:
        views_source = VIEWS_PATH.read_text(encoding="utf-8")
        location_source = LOCATION_MODE_PATH.read_text(encoding="utf-8")

        self.assertIn("if location_site_ids:", views_source)
        self.assertIn("role_display = 'A端' if site.pk == a_site_pk else 'Z端'", views_source)
        self.assertIn("highlight_sites_data.append({", views_source)
        self.assertIn("_fitHighlightedSitesBounds(sitesData)", location_source)
        self.assertIn("bounds.extend([site.lng, site.lat]);", location_source)
        self.assertIn("map.fitBounds(bounds, { padding: 80, maxZoom: 12 });", location_source)


if __name__ == "__main__":
    unittest.main()

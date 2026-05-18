from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
COORDS_PATH = REPO_ROOT / "netbox_otnfaults" / "services" / "fault_coordinates.py"
MAP_DATA_PATH = REPO_ROOT / "netbox_otnfaults" / "services" / "fault_map_data.py"
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"


class FaultCoordinateResolutionTestCase(unittest.TestCase):
    def test_shared_resolver_documents_the_unified_fallback_order(self) -> None:
        self.assertTrue(COORDS_PATH.exists(), "shared fault coordinate resolver should exist")
        source = COORDS_PATH.read_text(encoding="utf-8")

        self.assertIn("class FaultCoordinate", source)
        self.assertIn("def resolve_fault_coordinates(fault: OtnFault) -> FaultCoordinate | None:", source)
        self.assertIn("fault.interruption_latitude is not None", source)
        self.assertIn("source='fault'", source)
        self.assertIn("z_sites = list(fault.interruption_location.all())", source)
        self.assertIn("if len(z_sites) == 0:", source)
        self.assertIn("if len(z_sites) == 1:", source)
        self.assertIn("_find_path_between_sites", source)
        self.assertIn("_geometry_midpoint", source)
        self.assertIn("return _site_coordinate(a_site, source='a_site')", source)
        self.assertIn("return None", source)

    def test_path_midpoint_uses_coordinate_array_middle_index(self) -> None:
        source = COORDS_PATH.read_text(encoding="utf-8")

        self.assertIn("def _geometry_midpoint(geometry: Any) -> tuple[float, float] | None:", source)
        self.assertIn("coords = geometry.get('coordinates')", source)
        self.assertIn("midpoint = coords[len(coords) // 2]", source)

    def test_map_payload_serializers_delegate_to_shared_resolver_and_keep_imprecision_flags(self) -> None:
        source = MAP_DATA_PATH.read_text(encoding="utf-8")

        self.assertIn("from .fault_coordinates import resolve_fault_coordinates", source)
        self.assertIn("resolved = resolve_fault_coordinates(fault)", source)
        self.assertIn("'coords_from_site': resolved.coords_from_site", source)
        self.assertIn("'coords_source': resolved.source", source)
        self.assertNotIn("for site in fault.interruption_location.all():\n            if site.latitude is not None", source)

    def test_dashboard_and_location_views_reuse_shared_resolver(self) -> None:
        dashboard_source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")
        views_source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("from .services.fault_coordinates import resolve_fault_coordinates", dashboard_source)
        self.assertIn("resolved = resolve_fault_coordinates(fault)", dashboard_source)
        self.assertNotIn("def _get_fault_coords(self, fault) -> tuple:", dashboard_source)

        self.assertIn("from .services.fault_coordinates import resolve_fault_coordinates", views_source)
        self.assertIn("resolved = resolve_fault_coordinates(fault)", views_source)


if __name__ == "__main__":
    unittest.main()

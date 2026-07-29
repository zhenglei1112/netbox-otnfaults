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
        self.assertIn("def resolve_cutover_coordinates(cutover: CutoverTask) -> FaultCoordinate | None:", source)
        self.assertIn("def resolve_location_coordinates(", source)
        self.assertIn("getattr(obj, 'interruption_latitude', None) is not None", source)
        self.assertIn("getattr(obj, 'cutover_latitude', None) is not None", source)
        self.assertIn("source='fault'", source)
        self.assertIn("source='cutover'", source)
        self.assertIn("len(z_sites) == 1", source)
        self.assertIn("_find_path_between_sites", source)
        self.assertIn("_geometry_midpoint", source)
        self.assertIn("return _calculate_sites_center", source)

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

    def test_dashboard_and_location_views_reuse_shared_resolver(self) -> None:
        dashboard_source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8")
        views_source = VIEWS_PATH.read_text(encoding="utf-8")
        cutover_html_source = (REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "cutovertask.html").read_text(encoding="utf-8")

        self.assertIn("from .services.fault_coordinates import resolve_fault_coordinates", dashboard_source)
        self.assertIn("resolved = resolve_fault_coordinates(fault)", dashboard_source)
        self.assertIn("resolve_cutover_coordinates", dashboard_source)
        self.assertIn("resolved = resolve_cutover_coordinates(cutover)", dashboard_source)
        self.assertIn("'lat': resolved.lat if resolved is not None else None", dashboard_source)
        self.assertIn("'lng': resolved.lng if resolved is not None else None", dashboard_source)
        self.assertIn("'site_a_id': cutover.interruption_location_a_id", dashboard_source)
        self.assertIn("'site_z_ids': [site.pk for site in z_site_objects]", dashboard_source)

        self.assertIn("resolve_cutover_coordinates", views_source)
        self.assertIn("resolve_location_coordinates", views_source)
        self.assertIn("cutover_id = request.GET.get('cutover', '')", views_source)
        self.assertIn("resolved = resolve_cutover_coordinates(cutover)", views_source)

        self.assertIn("location_map_url }}?cutover={{ object.pk }}&", cutover_html_source)


if __name__ == "__main__":
    unittest.main()

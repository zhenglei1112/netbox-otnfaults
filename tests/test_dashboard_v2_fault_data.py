import unittest
from pathlib import Path


VIEW_PATH = (
    Path(__file__).resolve().parents[1]
    / "netbox_otnfaults"
    / "services"
    / "dashboard_v2.py"
)


class DashboardV2FaultDataTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.source = VIEW_PATH.read_text(encoding="utf-8")

    def test_summary_uses_confirmed_fault_scopes(self) -> None:
        self.assertIn("from django.utils import timezone", self.source)
        self.assertIn("fault_occurrence_time__gte=year_start", self.source)
        self.assertIn("fault_occurrence_time__gte=today_start", self.source)
        self.assertIn("fault_occurrence_time__lt=tomorrow_start", self.source)
        self.assertIn("fault_status=FaultStatusChoices.PROCESSING", self.source)
        self.assertIn("business_impact=BusinessImpactChoices.INTERRUPTED", self.source)
        self.assertIn("service_recovery_time__isnull=True", self.source)

    def test_processing_faults_prefetch_all_card_relations(self) -> None:
        self.assertIn(
            '.select_related("province", "interruption_location_a", "handling_unit")',
            self.source,
        )
        self.assertIn('Prefetch(', self.source)
        self.assertIn('to_attr="dashboard_impacts"', self.source)
        self.assertNotIn("interruption_latitude__isnull=False", self.source)
        self.assertNotIn("interruption_longitude__isnull=False", self.source)

    def test_processing_fault_payload_has_full_card_fields_and_priority_sort(self) -> None:
        for field in (
            '"url": fault.get_absolute_url()',
            '"fault_number"',
            '"category_display"',
            '"urgency_display"',
            '"priority_score"',
            '"lng"',
            '"lat"',
            '"coords_source"',
            '"coords_from_site"',
            '"province"',
            '"site_a"',
            '"sites_z"',
            '"occurrence_time_display"',
            '"duration"',
            '"handling_unit"',
            '"handler"',
            '"interrupted_business_count"',
            '"interrupted_business_names"',
            '"reason"',
            '"details"',
        ):
            self.assertIn(field, self.source)
        self.assertIn("processing_faults.sort(", self.source)
        self.assertIn("reverse=True", self.source)

    def test_processing_faults_reuse_shared_coordinate_resolution(self) -> None:
        self.assertIn(
            "from .fault_coordinates import load_fault_path_midpoints, resolve_fault_coordinates",
            self.source,
        )
        self.assertIn("resolved_coordinates = resolve_fault_coordinates(fault, path_midpoints=path_midpoints)", self.source)
        self.assertIn("resolved_coordinates.lng", self.source)
        self.assertIn("resolved_coordinates.lat", self.source)
        self.assertIn("resolved_coordinates.source", self.source)
        self.assertIn("resolved_coordinates.coords_from_site", self.source)


if __name__ == "__main__":
    unittest.main()

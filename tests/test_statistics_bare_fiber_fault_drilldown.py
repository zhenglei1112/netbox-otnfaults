import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
JS_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "statistics_dashboard.js"
)


class StatisticsBareFiberFaultDrilldownTestCase(unittest.TestCase):
    def test_fault_details_reuse_bare_fiber_interruption_scope(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        helper_source = source.split(
            "def _get_filtered_bare_fiber_interruption_impacts(", 1
        )[1].split("\n\n\ndef _compute_bare_fiber_interruption_overview", 1)[0]
        self.assertIn("'otn_fault__handling_unit'", helper_source)
        self.assertIn(
            "business_impact=BusinessImpactChoices.NOT_INTERRUPTED", helper_source
        )
        self.assertIn("def _get_filtered_bare_fiber_interruption_impacts(", source)
        details_source = source.split("class FaultStatisticsDetailsAPI", 1)[1].split(
            "\n\nclass FaultStatisticsServiceDetailsAPI", 1
        )[0]
        self.assertIn("if bare_fiber_interruption != 'true':", details_source)
        self.assertIn("_get_filtered_bare_fiber_interruption_impacts(", details_source)
        self.assertIn("queryset.filter(pk__in=bare_fiber_fault_ids)", details_source)
        self.assertIn("branch_company_scope=scope == 'branch_company'", details_source)

    def test_four_cards_configure_bare_fiber_fault_drilldown(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("const bareFiberMetricElements = [", source)
        self.assertIn(
            "totalCountEl, distinctCountEl, totalDurationEl, distinctDurationEl",
            source,
        )
        self.assertIn("metric.dataset.filterField = 'bare_fiber_interruption';", source)
        self.assertIn("metric.dataset.filterValue = 'true';", source)
        self.assertIn("metric.dataset.detailScope = 'bare_fiber_interruption';", source)
        self.assertIn("metric.dataset.filterLabel = '裸纤业务中断';", source)


if __name__ == "__main__":
    unittest.main()

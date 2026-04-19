import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"


class StatisticsCableBreakOverviewTestCase(unittest.TestCase):
    def test_backend_builds_cable_break_overview_with_required_scope_and_buckets(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("FaultStatusChoices", source)
        self.assertIn("cable_break_faults = [", source)
        self.assertIn("fault.fault_category == FaultCategoryChoices.FIBER_BREAK", source)
        self.assertIn("fault.fault_status != FaultStatusChoices.SUSPENDED", source)
        self.assertIn("'cable_break_overview': {", source)
        self.assertIn("'total_count': len(cable_break_faults)", source)
        self.assertIn("'reason_top3': _sorted_count_items(cable_break_reason_counts)[:3]", source)
        self.assertIn("'source_counts': _sorted_count_items(cable_break_source_counts)", source)
        self.assertIn("'long_duration_buckets': cable_break_long_duration_buckets", source)
        self.assertIn("'6-8小时': 0", source)
        self.assertIn("'8-10小时': 0", source)
        self.assertIn("'10-12小时': 0", source)
        self.assertIn("'12小时以上': 0", source)

    def test_template_contains_cable_break_overview_section_and_cards(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("statistics-cable-break-overview", template)
        self.assertIn("光缆中断概览", template)
        self.assertIn('id="cable-break-total-count"', template)
        self.assertIn('id="cable-break-reason-top3"', template)
        self.assertIn('id="cable-break-source-counts"', template)
        self.assertIn('id="cable-break-long-total"', template)
        self.assertIn('data-cable-break-duration-bucket="6-8小时"', template)
        self.assertIn('data-cable-break-duration-bucket="8-10小时"', template)
        self.assertIn('data-cable-break-duration-bucket="10-12小时"', template)
        self.assertIn('data-cable-break-duration-bucket="12小时以上"', template)

    def test_dashboard_script_renders_cable_break_overview(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("renderCableBreakOverview(data.cable_break_overview);", source)
        self.assertIn("function renderCableBreakOverview(overview)", source)
        self.assertIn("document.getElementById('cable-break-total-count')", source)
        self.assertIn("renderCountList('cable-break-reason-top3', overview.reason_top3)", source)
        self.assertIn("renderCountList('cable-break-source-counts', overview.source_counts)", source)
        self.assertIn("overview.long_duration_buckets || {}", source)
        self.assertIn("document.querySelectorAll('[data-cable-break-duration-bucket]')", source)
        self.assertIn("longTotal += count;", source)
        self.assertIn("longTotalEl.textContent = longTotal;", source)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STATISTICS_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"
STATISTICS_JS_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "statistics_dashboard.js"
)


class SLAPrecisionTestCase(unittest.TestCase):
    def test_backend_sla_fields_use_two_decimal_truncation(self) -> None:
        statistics_source = STATISTICS_VIEWS_PATH.read_text(encoding="utf-8")
        views_source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("def truncate_sla(value: float) -> float:", statistics_source)
        self.assertIn("math.trunc(value * 100.0) / 100.0", statistics_source)
        self.assertIn("'sla': truncate_sla(monthly_sla),", statistics_source)
        self.assertIn("'sla': truncate_sla(annual_sla),", statistics_source)
        self.assertIn("'sla': truncate_sla(sla),", statistics_source)
        self.assertIn("'sla_this_month': truncate_sla(sla_this_month),", views_source)
        self.assertNotIn("round(monthly_sla, 4)", statistics_source)
        self.assertNotIn("round(annual_sla, 4)", statistics_source)
        self.assertNotIn("round(sla, 4)", statistics_source)
        self.assertNotIn("round(sla_this_month, 4)", views_source)

    def test_frontend_sla_display_uses_two_decimal_truncation(self) -> None:
        source = STATISTICS_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("function formatSlaValue(value)", source)
        self.assertIn("return (Math.trunc(number * 100) / 100).toFixed(2);", source)
        self.assertIn("${formatSlaValue(annualSummary.sla)}%", source)
        self.assertIn("${showSla ? formatSlaValue(itemSla) : '-'}", source)
        self.assertNotIn("${formatCardMetricValue(annualSummary.sla)}%", source)
        self.assertNotIn("${formatCardMetricValue(itemSla)}%", source)
        self.assertNotIn("${formatSlaValue(itemSla)}%", source)


if __name__ == "__main__":
    unittest.main()

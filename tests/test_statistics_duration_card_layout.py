import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
CSS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "statistics_dashboard.css"


class StatisticsDurationCardLayoutTestCase(unittest.TestCase):
    def test_duration_summary_cards_use_four_column_layout(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn('id="cable-break-duration-total-list"', template)
        self.assertIn('id="branch-company-cable-break-duration-total-list"', template)
        physical_card = template.split('id="cable-break-duration-total-list"', 1)[0][-500:]
        branch_card = template.split('id="branch-company-cable-break-duration-total-list"', 1)[0][-500:]
        self.assertNotIn("statistics-cable-break-duration-summary-card", physical_card)
        self.assertNotIn("statistics-cable-break-duration-summary-card", branch_card)
        self.assertIn("statistics-cable-break-four-card", physical_card)
        self.assertIn("statistics-cable-break-four-card", branch_card)
        self.assertNotIn(".statistics-cable-break-duration-summary-card .statistics-kpi-group-items", css)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", css)


if __name__ == "__main__":
    unittest.main()

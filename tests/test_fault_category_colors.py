import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"

class FaultCategoryColorsSourceTestCase(unittest.TestCase):
    def test_fault_category_choice_colors_do_not_reuse_fault_status_colors(self) -> None:
        source = MODELS_PATH.read_text(encoding="utf-8-sig")

        for color in ("purple", "teal", "orange", "cyan", "pink", "indigo"):
            self.assertIn(color, source)

        for status_color in ("'red'", "'blue'", "'yellow'", "'green'"):
            fault_category_block = source.split("class FaultCategoryChoices(ChoiceSet):", 1)[1]
            fault_category_block = fault_category_block.split("class UrgencyChoices(ChoiceSet):", 1)[0]
            self.assertNotIn(status_color, fault_category_block)

    def test_dashboard_category_hex_colors_do_not_reuse_status_hex_colors(self) -> None:
        source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8-sig")
        category_block = source.split("CATEGORY_COLORS = {", 1)[1].split("}\n\nCATEGORY_NAMES", 1)[0]
        status_block = source.split("STATUS_COLORS = {", 1)[1].split("}\n\nSTATUS_NAMES", 1)[0]

        for category_color in ("#6F42C1", "#6610F2", "#FF8A00", "#0DCAF0", "#20C997"):
            self.assertIn(category_color, category_block)

        for status_color in ("#FF1E1E", "#3B82F6", "#FADB14", "#10B981"):
            self.assertNotIn(status_color, category_block)
            self.assertIn(status_color, status_block)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROL_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "controls"
    / "LayerToggleControl.js"
)


class FaultMapDefaultCategoriesTestCase(unittest.TestCase):
    def test_fault_map_defaults_to_three_primary_categories(self) -> None:
        source = CONTROL_PATH.read_text(encoding="utf-8")
        constructor_source = source.split("constructor(options) {", 1)[1].split("\n    onAdd(map) {", 1)[0]

        self.assertIn(
            "this.selectedCategories = ['fiber_break', 'device_fault', 'power_fault'];",
            constructor_source,
        )
        self.assertNotIn(
            "this.selectedCategories = ['fiber_break', 'ac_fault', 'fiber_degradation', 'fiber_jitter', 'device_fault', 'power_fault', 'other'];",
            constructor_source,
        )

    def test_all_checkbox_is_not_checked_for_default_subset(self) -> None:
        source = CONTROL_PATH.read_text(encoding="utf-8")

        self.assertIn("allCheckbox.checked = this.areAllCategoriesSelected(categories);", source)
        self.assertIn("areAllCategoriesSelected(categories)", source)
        self.assertNotIn("allCheckbox.checked = this.selectedCategories.length >= 7;", source)


if __name__ == "__main__":
    unittest.main()

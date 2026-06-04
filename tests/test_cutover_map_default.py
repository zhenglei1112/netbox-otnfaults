from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
LAYER_TOGGLE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "controls"
    / "LayerToggleControl.js"
)
MAP_MODES_PATH = REPO_ROOT / "netbox_otnfaults" / "map_modes.py"


class CutoverMapDefaultTest(unittest.TestCase):
    def test_one_map_shows_cutover_plans_by_default(self) -> None:
        source = LAYER_TOGGLE_PATH.read_text(encoding="utf-8")

        self.assertIn("this.showCutover = true;", source)

    def test_one_map_layer_toggle_asset_version_marks_cutover_default_change(self) -> None:
        source = MAP_MODES_PATH.read_text(encoding="utf-8")

        self.assertIn("controls/LayerToggleControl.js?v=cutover-default-1", source)


if __name__ == "__main__":
    unittest.main()

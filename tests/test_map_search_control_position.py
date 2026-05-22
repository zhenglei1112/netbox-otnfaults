import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_BASE = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "maplibregl_base.js"
FAULT_MODE = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "modes" / "fault_mode.js"
LOCATION_MODE = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "modes" / "location_mode.js"
GLOBE_CSS = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "otnfault_map_globe.css"


class MapSearchControlPositionTestCase(unittest.TestCase):
    def test_map_base_supports_top_center_control_slot(self) -> None:
        source = MAP_BASE.read_text(encoding="utf-8")

        self.assertIn('position === "top-center"', source)
        self.assertIn('"maplibregl-ctrl-top-center"', source)
        self.assertIn("control.onAdd(this.map)", source)

    def test_search_control_is_added_to_top_center_slot(self) -> None:
        fault_source = FAULT_MODE.read_text(encoding="utf-8")
        location_source = LOCATION_MODE.read_text(encoding="utf-8")

        self.assertIn('this.mapBase.addControl(this.searchControl, "top-center")', fault_source)
        self.assertIn("this.mapBase.addControl(this.searchControl, 'top-center')", location_source)
        self.assertNotIn('this.mapBase.addControl(this.searchControl, "top-left")', fault_source)
        self.assertNotIn("this.mapBase.addControl(this.searchControl, 'top-left')", location_source)

    def test_top_center_slot_is_centered_over_map_window(self) -> None:
        source = GLOBE_CSS.read_text(encoding="utf-8")

        self.assertIn(".maplibregl-ctrl-top-center", source)
        self.assertIn("left: 50%;", source)
        self.assertIn("transform: translateX(-50%);", source)
        self.assertIn(".maplibregl-ctrl-top-center > .maplibregl-ctrl", source)


if __name__ == "__main__":
    unittest.main()

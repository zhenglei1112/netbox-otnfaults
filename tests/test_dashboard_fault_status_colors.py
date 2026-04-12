import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_ENGINE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "dashboard" / "map_engine.js"
)
PANELS_JS_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "dashboard" / "panels.js"
)


class DashboardFaultStatusColorsTestCase(unittest.TestCase):
    def test_map_fault_markers_use_status_colors(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn("var status = fault.status || 'processing';", source)
        self.assertIn("colors.status_colors", source)
        self.assertNotIn("colors.alert_colors[severity]", source)

    def test_fault_queue_uses_status_colors(self) -> None:
        source = PANELS_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("_getStatusColor(f.status)", source)


if __name__ == "__main__":
    unittest.main()

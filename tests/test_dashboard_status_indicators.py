import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PANELS_JS_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "dashboard" / "panels.js"
)


class DashboardStatusIndicatorsTestCase(unittest.TestCase):
    def test_focus_card_and_queue_use_fault_status_visuals(self) -> None:
        source = PANELS_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("function _getStatusColor(status)", source)
        self.assertIn("_getStatusColor(f.status)", source)
        self.assertIn("f.status_display", source)
        self.assertIn("_getStatusColor(fault.status)", source)
        self.assertIn("fault.status_display", source)


if __name__ == "__main__":
    unittest.main()

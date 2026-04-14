import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FAULT_STATS_CONTROL_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "controls"
    / "FaultStatisticsControl.js"
)
FAULT_MODE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "modes"
    / "fault_mode.js"
)


class FaultStatisticsControlPerformanceTestCase(unittest.TestCase):
    def test_fault_statistics_control_lazy_renders_expanded_details(self) -> None:
        source = FAULT_STATS_CONTROL_PATH.read_text(encoding="utf-8")

        self.assertIn("this.detailsHydrated = false;", source)
        self.assertIn("requestAnimationFrame(() => {", source)
        self.assertIn("this.ensureExpandedContentHydrated();", source)
        self.assertIn("window.setFaultMapAnimationSuspended?.(!this.minimized);", source)

    def test_fault_mode_exposes_animation_suspend_hook(self) -> None:
        source = FAULT_MODE_PATH.read_text(encoding="utf-8")

        self.assertIn("window.setFaultMapAnimationSuspended = this.setAnimationSuspended.bind(this);", source)
        self.assertIn("setAnimationSuspended(suspended) {", source)
        self.assertIn("if (this.animationSuspended === suspended) {", source)
        self.assertIn("this._stopIconAnimation();", source)

    def test_fault_mode_disables_dynamic_fault_marker_effects(self) -> None:
        source = FAULT_MODE_PATH.read_text(encoding="utf-8")

        self.assertNotIn("this._startIconAnimation();", source)
        self.assertNotIn('map.setLayoutProperty("fault-points-pulse", "visibility", "visible");', source)
        self.assertNotIn('map.setLayoutProperty("fault-points-glow", "visibility", "visible");', source)


if __name__ == "__main__":
    unittest.main()

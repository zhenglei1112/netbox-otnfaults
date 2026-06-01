import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FAULT_ICONS_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "utils"
    / "fault_icons.js"
)


class CutoverMapIconTestCase(unittest.TestCase):
    def test_cutover_icon_uses_wrench_without_clock_or_scissors(self) -> None:
        source = FAULT_ICONS_PATH.read_text(encoding="utf-8")
        cutover_icon = source.split("cutover:", 1)[1].split("};", 1)[0]

        self.assertIn('stroke="white"', cutover_icon)
        self.assertIn("M21.2 6.1a6.2 6.2 0 0 1-7.6 7.6", cutover_icon)
        self.assertIn("L7.1 20.2a2.8 2.8 0 0 1-4-4", cutover_icon)
        self.assertNotIn("M19,3A2,2", cutover_icon)
        self.assertNotIn("A1.5,1.5", cutover_icon)


if __name__ == "__main__":
    unittest.main()

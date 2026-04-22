from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
NAVIGATION_PATH = REPO_ROOT / "netbox_otnfaults" / "navigation.py"


class NavigationMenuTestCase(unittest.TestCase):
    def test_weekly_report_is_not_exposed_in_plugin_menu(self) -> None:
        source = NAVIGATION_PATH.read_text(encoding="utf-8")

        self.assertNotIn("plugins:netbox_otnfaults:weekly_report", source)


if __name__ == "__main__":
    unittest.main()

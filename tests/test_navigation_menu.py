from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
NAVIGATION_PATH = REPO_ROOT / "netbox_otnfaults" / "navigation.py"


class NavigationMenuTestCase(unittest.TestCase):
    def test_weekly_report_is_not_exposed_in_plugin_menu(self) -> None:
        source = NAVIGATION_PATH.read_text(encoding="utf-8")

        self.assertNotIn("plugins:netbox_otnfaults:weekly_report", source)

    def test_fault_statistics_is_exposed_under_fault_group(self) -> None:
        source = NAVIGATION_PATH.read_text(encoding="utf-8")
        fault_group = source.split("('故障', (", maxsplit=1)[1].split("('割接', (", maxsplit=1)[0]
        map_group = source.split("('地图', (", maxsplit=1)[1].split(")),", maxsplit=1)[0]

        self.assertIn("link='plugins:netbox_otnfaults:statistics'", fault_group)
        self.assertIn("link_text='故障统计'", fault_group)
        self.assertNotIn("link='plugins:netbox_otnfaults:statistics'", map_group)


if __name__ == "__main__":
    unittest.main()

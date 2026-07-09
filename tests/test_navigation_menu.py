from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
NAVIGATION_PATH = REPO_ROOT / "netbox_otnfaults" / "navigation.py"


class NavigationMenuTestCase(unittest.TestCase):
    def test_weekly_report_is_not_exposed_in_plugin_menu(self) -> None:
        source = NAVIGATION_PATH.read_text(encoding="utf-8")

        self.assertNotIn("plugins:netbox_otnfaults:weekly_report", source)

    def _group_block(self, source: str, group_name: str) -> str:
        start_marker = f"('{group_name}', ("
        start = source.index(start_marker)
        next_group = source.find("\n        ('", start + len(start_marker))
        if next_group == -1:
            next_group = source.index("\n    ),", start)
        return source[start:next_group]

    def test_menu_uses_scheme_a_group_order_and_entries(self) -> None:
        source = NAVIGATION_PATH.read_text(encoding="utf-8")

        expected_groups = [
            "运行态势",
            "故障处置",
            "割接管理",
            "保障任务",
            "业务资源",
            "网络资源",
        ]
        group_positions: list[int] = []
        for group_name in expected_groups:
            position = source.find(f"('{group_name}', (")
            self.assertNotEqual(position, -1, group_name)
            group_positions.append(position)

        self.assertEqual(group_positions, sorted(group_positions))
        self.assertNotIn("('故障', (", source)
        self.assertNotIn("('地图', (", source)

        expected_links_by_group = {
            "运行态势": [
                "dashboard",
                "otnfault_map_globe",
                "statistics",
            ],
            "故障处置": [
                "otnfault_list",
                "otnfaultimpact_list",
            ],
            "割接管理": [
                "cutovertask_list",
                "cutoverimpact_list",
            ],
            "保障任务": [
                "heavyduty_list",
            ],
            "业务资源": [
                "circuitservice_list",
                "barefiberservice_list",
            ],
            "网络资源": [
                "otnpathgroup_list",
                "otnpath_list",
                "route_editor",
            ],
        }

        for group_name, link_names in expected_links_by_group.items():
            group_block = self._group_block(source, group_name)
            link_positions = [
                group_block.index(f"plugins:netbox_otnfaults:{link_name}")
                for link_name in link_names
            ]
            self.assertEqual(link_positions, sorted(link_positions), group_name)

        running_group = self._group_block(source, "运行态势")
        self.assertIn("link_text='态势大屏'", running_group)
        self.assertIn("link_text='一张图'", running_group)
        self.assertIn("link_text='故障统计'", running_group)


if __name__ == "__main__":
    unittest.main()

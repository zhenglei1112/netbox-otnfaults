import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class FaultMapDisplayNameTestCase(unittest.TestCase):
    def test_fault_map_visible_name_is_one_map(self) -> None:
        display_sources = [
            REPO_ROOT / "netbox_otnfaults" / "map_modes.py",
            REPO_ROOT / "netbox_otnfaults" / "navigation.py",
            REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_list.html",
        ]
        combined_source = "\n".join(path.read_text(encoding="utf-8") for path in display_sources)

        self.assertIn("'title': '一张图'", combined_source)
        self.assertIn("link_text='一张图'", combined_source)
        self.assertIn("查看一张图", combined_source)
        self.assertNotIn("故障分布图", combined_source)

    def test_fault_map_old_name_is_absent_from_code_comments(self) -> None:
        code_paths = [
            path
            for path in (REPO_ROOT / "netbox_otnfaults").rglob("*")
            if path.suffix in {".py", ".js", ".html"}
        ]
        source_chunks = []
        for path in code_paths:
            try:
                source_chunks.append(path.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                continue
        combined_source = "\n".join(source_chunks)

        self.assertNotIn("故障分布图", combined_source)


if __name__ == "__main__":
    unittest.main()

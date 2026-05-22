import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_BASE = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "maplibregl_base.js"


class MapFaultControlIconTestCase(unittest.TestCase):
    def test_map_base_exposes_fault_meaning_icon(self) -> None:
        source = MAP_BASE.read_text(encoding="utf-8")
        icon_block = source.split("fault:", 1)[1].split("filter:", 1)[0]

        self.assertIn("viewBox=\"0 0 24 24\"", icon_block)
        self.assertIn("<path d=\"M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z\"", icon_block)
        self.assertIn("<line x1=\"12\" y1=\"9\" x2=\"12\" y2=\"13\"", icon_block)
        self.assertIn("<line x1=\"12\" y1=\"17\" x2=\"12.01\" y2=\"17\"", icon_block)


if __name__ == "__main__":
    unittest.main()

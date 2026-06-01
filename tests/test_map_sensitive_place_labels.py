import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_BASE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "maplibregl_base.js"
)


class MapSensitivePlaceLabelsTestCase(unittest.TestCase):
    def test_base_map_hides_taiwan_and_taipei_place_text(self) -> None:
        source = MAP_BASE_PATH.read_text(encoding="utf-8")

        self.assertIn("HIDDEN_PLACE_LABEL_NAMES", source)
        for name in ["台湾", "台北", "Taiwan", "Taipei"]:
            self.assertIn(f'"{name}"', source)
        self.assertIn("getHiddenPlaceLabelExpression", source)
        self.assertIn('this.getHiddenPlaceLabelExpression(["get", "name"])', source)
        self.assertIn('this.getHiddenPlaceLabelExpression([', source)
        self.assertIn('["get", "name:zh"]', source)
        self.assertIn('["get", "name"]', source)

    def test_base_map_hides_taipei_place_icons(self) -> None:
        source = MAP_BASE_PATH.read_text(encoding="utf-8")

        self.assertIn("getHiddenPlaceIconOpacityExpression", source)
        self.assertIn('layer.layout["icon-image"]', source)
        self.assertIn('layer.paint?.["icon-opacity"] || 1', source)
        self.assertIn('"icon-opacity"', source)

    def test_remote_style_is_sanitized_before_map_initial_render(self) -> None:
        source = MAP_BASE_PATH.read_text(encoding="utf-8")
        load_remote_style = source.split("async _loadRemoteBasemapStyle(theme) {", 1)[1]

        self.assertIn("applyHiddenPlaceRulesToStyle(styleConfig)", source)
        self.assertIn("this.applyHiddenPlaceRulesToStyle(styleConfig);", source)
        self.assertLess(
            load_remote_style.index("this.applyHiddenPlaceRulesToStyle(styleConfig);"),
            load_remote_style.index("return styleConfig;"),
        )


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_MODES_PATH = REPO_ROOT / "netbox_otnfaults" / "map_modes.py"
LOCATION_MODE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "modes"
    / "location_mode.js"
)
LAYER_TOGGLE_CONTROL_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "controls"
    / "LayerToggleControl.js"
)


class PathGroupTopologyToggleTestCase(unittest.TestCase):
    def test_pathgroup_mode_loads_layer_toggle_control(self) -> None:
        source = MAP_MODES_PATH.read_text(encoding="utf-8")
        mode_block = source.split("'pathgroup': {", 1)[1].split("'route_editor': {", 1)[0]

        self.assertIn("'controls/SpatialSelectControl.js'", mode_block)
        self.assertIn("'controls/LayerToggleControl.js?v=pathgroup-overlays-3'", mode_block)

    def test_location_mode_initializes_pathgroup_topology_toggle_only(self) -> None:
        source = LOCATION_MODE_PATH.read_text(encoding="utf-8")

        self.assertIn("layerToggleControl: null", source)
        self.assertIn("this._initPathGroupTopologyToggle();", source)
        self.assertIn("_initPathGroupTopologyToggle() {", source)
        self.assertIn("if (this.config.mode !== 'pathgroup') return;", source)
        self.assertIn("new LayerToggleControl({", source)
        self.assertIn("viewMode: false", source)
        self.assertIn("timeRange: false", source)
        self.assertIn("categories: false", source)
        self.assertIn("topology: true", source)
        self.assertNotIn("this._initPathGroupTopologyToggle();\n    }\n\n    // 1. 处理高亮路径", source)

    def test_layer_toggle_control_supports_topology_only_menu(self) -> None:
        source = LAYER_TOGGLE_CONTROL_PATH.read_text(encoding="utf-8")

        self.assertIn("this.sections = Object.assign", source)
        self.assertIn("viewMode: true", source)
        self.assertIn("timeRange: true", source)
        self.assertIn("categories: true", source)
        self.assertIn("topology: true", source)
        self.assertIn("this.sections.viewMode", source)
        self.assertIn("this.sections.timeRange", source)
        self.assertIn("this.sections.categories", source)
        self.assertIn("this.sections.topology", source)
        self.assertIn("this.options.title || '故障视图与时间设置'", source)
        self.assertIn("this.options.buttonIcon || window.mapBase.svgIcons.fault", source)
        self.assertNotIn("this.options.buttonIcon || window.mapBase.svgIcons.filter", source)
        self.assertIn("this.addHeader(menu, '故障视图模式')", source)
        self.assertIn("this.addHeader(menu, '故障时间范围')", source)
        self.assertNotIn("this.addHeader(menu, '视图模式')", source)
        self.assertNotIn("this.addHeader(menu, '时间范围')", source)


    def test_layer_toggle_floating_menu_opens_to_button_left(self) -> None:
        source = LAYER_TOGGLE_CONTROL_PATH.read_text(encoding="utf-8")

        self.assertIn("const rightOfMenu = viewportWidth - buttonRect.left + 8;", source)
        self.assertIn("let left = viewportWidth - rightOfMenu - menuWidth", source)
        self.assertNotIn("let left = buttonRect.right + 8;", source)

    def test_layer_toggle_inline_menu_opens_to_button_right(self) -> None:
        source = LAYER_TOGGLE_CONTROL_PATH.read_text(encoding="utf-8")

        self.assertIn("menu.style.top = '0';", source)
        self.assertIn("menu.style.left = '48px';", source)
        self.assertNotIn("menu.style.top = '40px';", source)
        self.assertNotIn("menu.style.left = '0';", source)


if __name__ == "__main__":
    unittest.main()

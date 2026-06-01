import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROL_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "controls"
    / "LayerToggleControl.js"
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


class FaultMapCutoverControlTestCase(unittest.TestCase):
    def test_cutover_is_its_own_left_side_control(self) -> None:
        source = FAULT_MODE_PATH.read_text(encoding="utf-8")
        fault_add_index = source.index('this.mapBase.addControl(this.layerToggleControl, "top-left")')
        cutover_add_index = source.index('this.mapBase.addControl(this.cutoverToggleControl, "top-left")')

        self.assertIn("cutoverToggleControl: null", source)
        self.assertIn("this.cutoverToggleControl = new LayerToggleControl({", source)
        self.assertIn("cutoverOnly: true", source)
        self.assertIn('controlClass: "cutover-toggle-control"', source)
        self.assertIn("this.mapBase.addControl(this.cutoverToggleControl, \"top-left\")", source)
        self.assertLess(fault_add_index, cutover_add_index)
        self.assertIn("showCutover = this.cutoverToggleControl.showCutover || false", source)

    def test_layer_display_control_does_not_include_cutover_toggle(self) -> None:
        source = CONTROL_PATH.read_text(encoding="utf-8")

        topology_block = source.split("if (this.sections.topology) {", 1)[1].split(
            "if (this.sections.cutover) {", 1
        )[0]

        self.assertNotIn("显示割接计划", topology_block)
        self.assertNotIn("createCutoverFilterPanel", topology_block)
        self.assertIn("cutover: false", source)
        self.assertIn("this.options.cutoverOnly === true", source)

    def test_cutover_source_updates_even_when_fault_filters_are_cached(self) -> None:
        source = FAULT_MODE_PATH.read_text(encoding="utf-8")
        data_sources_method = source.split("_updateDataSources() {", 1)[1].split("\n  },", 1)[0]
        cache_hit_block = data_sources_method.split("if (this.cachedFilterKey === filterKey && this.cachedFilteredFeatures) {", 1)[1].split("}", 1)[0]

        self.assertIn("this._updateCutoverDataSource();", cache_hit_block)
        self.assertLess(
            data_sources_method.index("this._updateCutoverDataSource();"),
            data_sources_method.index("return;", data_sources_method.index("this.cachedFilterKey === filterKey")),
        )

    def test_cutover_visibility_updates_even_when_fault_display_mode_is_unchanged(self) -> None:
        source = FAULT_MODE_PATH.read_text(encoding="utf-8")
        visibility_method = source.split("_updateLayerVisibility() {", 1)[1].split("\n  },", 1)[0]

        self.assertLess(
            visibility_method.index("this._updateCutoverLayerVisibility();"),
            visibility_method.index("return;", visibility_method.index("this.currentDisplayMode === mode")),
        )
        self.assertIn("_updateCutoverLayerVisibility() {", source)

    def test_cutover_points_do_not_use_breathing_glow_layer(self) -> None:
        source = FAULT_MODE_PATH.read_text(encoding="utf-8")

        self.assertNotIn("cutover-points-glow", source)
        self.assertNotIn("_startCutoverGlowAnimation", source)
        self.assertNotIn("_stopCutoverGlowAnimation", source)

    def test_cutover_card_icon_uses_light_static_shadow(self) -> None:
        source = FAULT_MODE_PATH.read_text(encoding="utf-8")
        card_icon_method = source.split("_createCutoverCardIcon(item) {", 1)[1].split("\n  },", 1)[0]

        self.assertIn("ctx.shadowColor = 'rgba(0, 0, 0, 0.16)'", card_icon_method)
        self.assertIn("ctx.shadowBlur = 5", card_icon_method)
        self.assertIn("ctx.shadowOffsetY = 2", card_icon_method)


if __name__ == "__main__":
    unittest.main()

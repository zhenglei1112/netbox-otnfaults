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

VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"


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


    def test_cutover_filter_uses_lightweight_abortable_request(self) -> None:
        source = CONTROL_PATH.read_text(encoding="utf-8")
        fetch_method = source.split("fetchCutoverDataAndRefresh() {", 1)[1].split(
            "\n    }", 1
        )[0]

        self.assertIn("url.searchParams.set('cutover_only', '1')", fetch_method)
        self.assertIn("this.cutoverRequestController.abort()", fetch_method)
        self.assertIn("this.cutoverRequestController = new AbortController()", fetch_method)
        self.assertIn("signal: requestController.signal", fetch_method)
        self.assertIn("if (requestController !== this.cutoverRequestController) return", fetch_method)
        self.assertIn("if (err.name === 'AbortError') return", fetch_method)

    def test_cutover_only_response_skips_full_map_payload_builders(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")
        view_method = source.split("class OtnFaultMapDataView", 1)[1].split(
            "\n\nclass MapPreferenceView", 1
        )[0]

        cutover_only_index = view_method.index("if request.GET.get('cutover_only') == '1':")
        sites_index = view_method.index("sites_data = get_sites_data()")
        faults_index = view_method.index("payload = build_fault_map_payload()")
        self.assertLess(cutover_only_index, sites_index)
        self.assertLess(cutover_only_index, faults_index)
        self.assertIn("return JsonResponse({'cutover_data': cutover_data})", view_method)
if __name__ == "__main__":
    unittest.main()

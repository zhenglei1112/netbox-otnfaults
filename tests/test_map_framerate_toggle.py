from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults"
UNIFIED_MAP_TEMPLATE = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "unified_map.html"
)
DASHBOARD_TEMPLATE = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "dashboard.html"
)
UNIFIED_MAP_CORE = STATIC_ROOT / "js" / "unified_map_core.js"
DASHBOARD_MAP_ENGINE = STATIC_ROOT / "js" / "dashboard" / "map_engine.js"
FRAMERATE_TOGGLE_JS = STATIC_ROOT / "js" / "map_framerate_toggle.js"
FRAMERATE_VENDOR_JS = STATIC_ROOT / "lib" / "mapbox-gl-framerate.js"
FRAMERATE_LICENSE = STATIC_ROOT / "lib" / "mapbox-gl-framerate.LICENCE"


class MapFrameRateToggleTestCase(unittest.TestCase):
    def test_framerate_vendor_assets_are_local_and_licensed(self) -> None:
        vendor_source = FRAMERATE_VENDOR_JS.read_text(encoding="utf-8")
        license_text = FRAMERATE_LICENSE.read_text(encoding="utf-8")

        self.assertIn("FrameRateControl", vendor_source)
        self.assertIn("global.FrameRateControl = factory()", vendor_source)
        self.assertIn("Copyright (c) 2019, Mapbox", license_text)

    def test_unified_map_loads_framerate_assets_before_core(self) -> None:
        template = UNIFIED_MAP_TEMPLATE.read_text(encoding="utf-8")

        vendor_include = "netbox_otnfaults/lib/mapbox-gl-framerate.js"
        toggle_include = "netbox_otnfaults/js/map_framerate_toggle.js"
        core_include = "netbox_otnfaults/js/unified_map_core.js"

        self.assertIn(vendor_include, template)
        self.assertIn(toggle_include, template)
        self.assertLess(template.index(vendor_include), template.index(toggle_include))
        self.assertLess(template.index(toggle_include), template.index(core_include))
        self.assertIn("window.mapboxgl = window.maplibregl", template)

    def test_dashboard_map_loads_framerate_assets_before_engine(self) -> None:
        template = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")

        vendor_include = "netbox_otnfaults/lib/mapbox-gl-framerate.js"
        toggle_include = "netbox_otnfaults/js/map_framerate_toggle.js"
        engine_include = "netbox_otnfaults/js/dashboard/map_engine.js"

        self.assertIn(vendor_include, template)
        self.assertIn(toggle_include, template)
        self.assertLess(template.index(vendor_include), template.index(toggle_include))
        self.assertLess(template.index(toggle_include), template.index(engine_include))
        self.assertIn("window.mapboxgl = window.maplibregl", template)

    def test_framerate_toggle_defaults_off_and_uses_complex_hotkey(self) -> None:
        source = FRAMERATE_TOGGLE_JS.read_text(encoding="utf-8")

        self.assertIn("ctrlKey && event.altKey && event.shiftKey", source)
        self.assertIn('event.code === "KeyF"', source)
        self.assertIn("new ControlClass", source)
        self.assertIn("map.addControl", source)
        self.assertIn("map.removeControl", source)
        self.assertIn("register(map", source)
        self.assertNotIn("showOnLoad", source)

    def test_all_map_entrypoints_register_framerate_toggle(self) -> None:
        unified_core = UNIFIED_MAP_CORE.read_text(encoding="utf-8")
        dashboard_engine = DASHBOARD_MAP_ENGINE.read_text(encoding="utf-8")

        self.assertIn("window.OTNMapFrameRateToggle.register(this.map", unified_core)
        self.assertIn("window.OTNMapFrameRateToggle.register(map", dashboard_engine)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_topology.py"
DASHBOARD_TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "dashboard.html"
)
DASHBOARD_APP_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "dashboard"
    / "dashboard_app.js"
)


class _DummyPath:
    def __init__(
        self,
        pk: int,
        name: str,
        geometry,
        site_a_id: int | None,
        site_z_id: int | None,
        cable_type: str = "96",
        cable_type_display: str = "96芯",
        site_a_name: str = "A站",
        site_z_name: str = "Z站",
        groups: list[str] | None = None,
        calculated_length: float | None = None,
    ) -> None:
        self.pk = pk
        self.name = name
        self.geometry = geometry
        self.site_a_id = site_a_id
        self.site_z_id = site_z_id
        self.cable_type = cable_type
        self.site_a = type("SiteRef", (), {"name": site_a_name})() if site_a_name else None
        self.site_z = type("SiteRef", (), {"name": site_z_name})() if site_z_name else None
        self.calculated_length = calculated_length
        self._groups = [type("GroupRef", (), {"name": group_name})() for group_name in (groups or [])]
        self._cable_type_display = cable_type_display

    def get_cable_type_display(self) -> str:
        return self._cable_type_display

    @property
    def groups(self):
        return type("GroupManager", (), {"all": lambda _self: self._groups})()


class DashboardPmtilesTopologyTestCase(unittest.TestCase):
    def _load_topology_module(self):
        spec = importlib.util.spec_from_file_location(
            "test_dashboard_topology_module",
            MODULE_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_build_fault_path_overlays_only_returns_fault_related_paths(self) -> None:
        module = self._load_topology_module()

        paths = [
            _DummyPath(
                pk=1,
                name="故障路径",
                geometry={"type": "LineString", "coordinates": [[110, 30], [111, 31]]},
                site_a_id=10,
                site_z_id=11,
                groups=["骨干环"],
                calculated_length=12.34,
            ),
            _DummyPath(
                pk=2,
                name="普通路径",
                geometry={"type": "LineString", "coordinates": [[112, 32], [113, 33]]},
                site_a_id=20,
                site_z_id=21,
                groups=["接入环"],
                calculated_length=45.67,
            ),
        ]

        overlays = module.build_fault_path_overlays(paths, active_fault_site_ids={10, 99})

        self.assertEqual(
            overlays,
            [
                {
                    "id": 1,
                    "name": "故障路径",
                    "geometry": {"type": "LineString", "coordinates": [[110, 30], [111, 31]]},
                    "cable_type": "96",
                    "cable_type_display": "96芯",
                    "site_a_name": "A站",
                    "site_z_name": "Z站",
                    "groups": ["骨干环"],
                    "length_km": "12.3km",
                    "has_fault": True,
                }
            ],
        )

    def test_dashboard_assets_switch_to_pmtiles_base_topology_and_fault_path_payload(self) -> None:
        dashboard_template = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")
        dashboard_app = DASHBOARD_APP_PATH.read_text(encoding="utf-8")

        self.assertIn("pmtiles.js", dashboard_template)
        self.assertIn("otnPathsPmtilesUrl", dashboard_template)
        self.assertIn("fault_paths", dashboard_app)
        self.assertNotIn("renderPaths(data.paths || [])", dashboard_app)

    def test_map_engine_preserves_maplibre_glyph_template_tokens(self) -> None:
        map_engine = (
            REPO_ROOT
            / "netbox_otnfaults"
            / "static"
            / "netbox_otnfaults"
            / "js"
            / "dashboard"
            / "map_engine.js"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "var glyphsUrl = CONFIG.localGlyphsUrl || '/maps/fonts/{fontstack}/{range}.pbf';",
            map_engine,
        )

    def test_map_engine_reorders_base_topology_after_province_layers_load(self) -> None:
        map_engine = (
            REPO_ROOT
            / "netbox_otnfaults"
            / "static"
            / "netbox_otnfaults"
            / "js"
            / "dashboard"
            / "map_engine.js"
        ).read_text(encoding="utf-8")

        self.assertIn("_restackTopologyLayer();", map_engine)


if __name__ == "__main__":
    unittest.main()

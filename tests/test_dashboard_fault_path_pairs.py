import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_topology.py"


class _DummyPath:
    def __init__(
        self,
        pk: int,
        name: str,
        geometry: dict,
        site_a_id: int | None,
        site_z_id: int | None,
        calculated_length: float | None = None,
    ) -> None:
        self.pk = pk
        self.name = name
        self.geometry = geometry
        self.site_a_id = site_a_id
        self.site_z_id = site_z_id
        self.cable_type = "96"
        self.site_a = type("SiteRef", (), {"name": "A-site"})()
        self.site_z = type("SiteRef", (), {"name": "Z-site"})()
        self.calculated_length = calculated_length
        self._groups = [type("GroupRef", (), {"name": "backbone"})()]

    def get_cable_type_display(self) -> str:
        return "96-fiber"

    @property
    def groups(self):
        return type("GroupManager", (), {"all": lambda _self: self._groups})()


class DashboardFaultPathPairsTestCase(unittest.TestCase):
    def _load_topology_module(self):
        spec = importlib.util.spec_from_file_location(
            "test_dashboard_topology_module",
            MODULE_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_build_fault_path_overlays_matches_complete_az_pairs_only(self) -> None:
        module = self._load_topology_module()
        paths = [
            _DummyPath(
                pk=1,
                name="matched-path",
                geometry={"type": "LineString", "coordinates": [[110, 30], [111, 31]]},
                site_a_id=10,
                site_z_id=11,
                calculated_length=12.34,
            ),
            _DummyPath(
                pk=2,
                name="single-end-match-path",
                geometry={"type": "LineString", "coordinates": [[112, 32], [113, 33]]},
                site_a_id=10,
                site_z_id=99,
                calculated_length=45.67,
            ),
            _DummyPath(
                pk=3,
                name="reverse-matched-path",
                geometry={"type": "LineString", "coordinates": [[114, 34], [115, 35]]},
                site_a_id=11,
                site_z_id=10,
                calculated_length=10.0,
            ),
        ]

        overlays = module.build_fault_path_overlays(paths, fault_site_pairs={(10, 11)})

        self.assertEqual([overlay["id"] for overlay in overlays], [1, 3])


if __name__ == "__main__":
    unittest.main()

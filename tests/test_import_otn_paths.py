import importlib.util
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "netbox_otnfaults" / "scripts" / "import_otn_paths.py"


class _Q:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    def __or__(self, other):
        return self


class _Var:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs


class _FakeSite:
    DoesNotExist = type("DoesNotExist", (Exception,), {})
    MultipleObjectsReturned = type("MultipleObjectsReturned", (Exception,), {})

    def __init__(self, name: str, slug: str, latitude=None, longitude=None, status: str = "active") -> None:
        self.name = name
        self.slug = slug
        self.latitude = latitude
        self.longitude = longitude
        self.status = status


class _FakeSiteQuerySet:
    def __init__(self, sites):
        self._sites = list(sites)

    def exclude(self, **kwargs):
        sites = self._sites
        for key, value in kwargs.items():
            if key == "latitude__isnull":
                sites = [site for site in sites if (site.latitude is None) != value]
            elif key == "longitude__isnull":
                sites = [site for site in sites if (site.longitude is None) != value]
            else:
                raise AssertionError(f"Unsupported exclude lookup: {key}")
        return _FakeSiteQuerySet(sites)

    def __iter__(self):
        return iter(self._sites)


class _FakeSiteManager:
    def __init__(self, sites):
        self._sites = list(sites)

    def get_or_create(self, slug: str, defaults: dict):
        for site in self._sites:
            if site.slug == slug:
                return site, False
        site = _FakeSite(
            name=defaults["name"],
            slug=slug,
            status=defaults.get("status", "active"),
        )
        self._sites.append(site)
        return site, True

    def get(self, name: str):
        matches = [site for site in self._sites if site.name == name]
        if not matches:
            raise _FakeSite.DoesNotExist()
        if len(matches) > 1:
            raise _FakeSite.MultipleObjectsReturned()
        return matches[0]

    def exclude(self, **kwargs):
        return _FakeSiteQuerySet(self._sites).exclude(**kwargs)


class _FakeFilterResult:
    def first(self):
        return None


class _FakeOtnPathManager:
    def filter(self, *args, **kwargs):
        return _FakeFilterResult()


class _FakeOtnPath:
    objects = _FakeOtnPathManager()
    created = []
    save_calls = 0

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        _FakeOtnPath.created.append(kwargs)

    def full_clean(self) -> None:
        return None

    def save(self) -> None:
        _FakeOtnPath.save_calls += 1
        return None


def _install_import_stubs(fake_site_class, fake_otn_path_class) -> None:
    extras_module = types.ModuleType("extras")
    extras_scripts_module = types.ModuleType("extras.scripts")

    class _Script:
        pass

    extras_scripts_module.Script = _Script
    extras_scripts_module.IntegerVar = _Var
    extras_scripts_module.BooleanVar = _Var
    sys.modules["extras"] = extras_module
    sys.modules["extras.scripts"] = extras_scripts_module

    django_module = types.ModuleType("django")
    django_db_module = types.ModuleType("django.db")
    django_db_models_module = types.ModuleType("django.db.models")
    django_db_models_module.Q = _Q
    django_core_module = types.ModuleType("django.core")
    django_core_exceptions_module = types.ModuleType("django.core.exceptions")
    django_core_exceptions_module.ObjectDoesNotExist = Exception
    sys.modules["django"] = django_module
    sys.modules["django.db"] = django_db_module
    sys.modules["django.db.models"] = django_db_models_module
    sys.modules["django.core"] = django_core_module
    sys.modules["django.core.exceptions"] = django_core_exceptions_module

    dcim_module = types.ModuleType("dcim")
    dcim_models_module = types.ModuleType("dcim.models")
    dcim_models_module.Site = fake_site_class
    sys.modules["dcim"] = dcim_module
    sys.modules["dcim.models"] = dcim_models_module

    plugin_module = types.ModuleType("netbox_otnfaults")
    plugin_models_module = types.ModuleType("netbox_otnfaults.models")
    plugin_models_module.OtnPath = fake_otn_path_class
    plugin_models_module.CableTypeChoices = type(
        "CableTypeChoices",
        (),
        {
            "SELF_BUILT": "self_built",
            "COORDINATED": "coordinated",
            "LEASED": "leased",
        },
    )
    sys.modules["netbox_otnfaults"] = plugin_module
    sys.modules["netbox_otnfaults.models"] = plugin_models_module

    requests_module = types.ModuleType("requests")
    requests_module.get = lambda *args, **kwargs: None
    sys.modules["requests"] = requests_module


def _load_script_module(fake_site_class, fake_otn_path_class):
    _install_import_stubs(fake_site_class, fake_otn_path_class)
    spec = importlib.util.spec_from_file_location("test_import_otn_paths_module", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ImportOtnPathsNetBoxMatchingTestCase(unittest.TestCase):
    def test_run_matches_line_endpoints_against_netbox_sites_when_arcgis_points_are_empty(self) -> None:
        site_a = _FakeSite(name="Alpha", slug="alpha", latitude=25.0, longitude=118.0)
        site_z = _FakeSite(name="Beta", slug="beta", latitude=25.001, longitude=118.001)
        _FakeSite.objects = _FakeSiteManager([site_a, site_z])
        _FakeOtnPath.created = []

        module = _load_script_module(_FakeSite, _FakeOtnPath)
        script = module.ImportOtnPaths()
        script.log_info = lambda message: None
        script.log_warning = lambda message: None
        script.log_success = lambda message: None
        script.log_failure = lambda message: None

        def _fake_fetch(url):
            if url.endswith("/0"):
                return {"features": []}
            if url.endswith("/1"):
                return {
                    "features": [
                        {
                            "geometry": {
                                "paths": [
                                    [
                                        [118.0, 25.0],
                                        [118.001, 25.001],
                                    ]
                                ]
                            },
                            "attributes": {
                                "O_NAME": "UnhelpfulName",
                                "O_COM": "demo",
                            },
                        }
                    ]
                }
            raise AssertionError(f"Unexpected URL {url}")

        script.fetch_arcgis_data = _fake_fetch
        script.run({"distance_threshold": 200}, commit=False)

        self.assertEqual(len(_FakeOtnPath.created), 1)
        created_path = _FakeOtnPath.created[0]
        self.assertEqual(created_path["site_a"].name, "Alpha")
        self.assertEqual(created_path["site_z"].name, "Beta")
        self.assertEqual(created_path["name"], "Alpha-Beta")

    def test_dry_run_skips_save_even_when_commit_is_true(self) -> None:
        site_a = _FakeSite(name="Alpha", slug="alpha", latitude=25.0, longitude=118.0)
        site_z = _FakeSite(name="Beta", slug="beta", latitude=25.001, longitude=118.001)
        _FakeSite.objects = _FakeSiteManager([site_a, site_z])
        _FakeOtnPath.created = []
        _FakeOtnPath.save_calls = 0

        module = _load_script_module(_FakeSite, _FakeOtnPath)
        script = module.ImportOtnPaths()
        script.log_info = lambda message: None
        script.log_warning = lambda message: None
        script.log_success = lambda message: None
        script.log_failure = lambda message: None

        def _fake_fetch(url):
            if url.endswith("/1"):
                return {
                    "features": [
                        {
                            "geometry": {
                                "paths": [
                                    [
                                        [118.0, 25.0],
                                        [118.001, 25.001],
                                    ]
                                ]
                            },
                            "attributes": {
                                "O_NAME": "Alpha-Beta",
                                "O_COM": "demo",
                            },
                        }
                    ]
                }
            return {"features": []}

        script.fetch_arcgis_data = _fake_fetch
        script.run({"distance_threshold": 200, "dry_run": True}, commit=True)

        self.assertEqual(len(_FakeOtnPath.created), 1)
        self.assertEqual(_FakeOtnPath.save_calls, 0)

    def test_report_includes_detailed_unspecified_path_names(self) -> None:
        nearby_site = _FakeSite(name="Nearby Station", slug="nearby-station", latitude=25.0012, longitude=118.0012)
        _FakeSite.objects = _FakeSiteManager([nearby_site])
        _FakeOtnPath.created = []
        _FakeOtnPath.save_calls = 0

        module = _load_script_module(_FakeSite, _FakeOtnPath)
        script = module.ImportOtnPaths()
        script.log_info = lambda message: None
        script.log_warning = lambda message: None
        script.log_success = lambda message: None
        script.log_failure = lambda message: None

        def _fake_fetch(url):
            if url.endswith("/1"):
                return {
                    "features": [
                        {
                            "geometry": {
                                "paths": [
                                    [
                                        [118.0, 25.0],
                                        [118.001, 25.001],
                                    ]
                                ]
                            },
                            "attributes": {
                                "O_NAME": "ArcPath-001",
                                "O_COM": "demo",
                            },
                        }
                    ]
                }
            return {"features": []}

        script.fetch_arcgis_data = _fake_fetch
        report = script.run({"distance_threshold": 50, "dry_run": True}, commit=False)

        self.assertIn("原始路径名: ArcPath-001", report)
        self.assertIn("导入路径名:", report)
        self.assertIn("模糊匹配后仍未匹配", report)
        self.assertIn("仍保持【未指定】", report)
        self.assertIn("待匹配端站点名称: ArcPath", report)
        self.assertIn("最近候选站点: Nearby Station", report)
        self.assertIn("最近距离:", report)
        self.assertIn("最佳相似候选: Nearby Station", report)
        self.assertNotIn("Z端 最近候选站点", report)

    def test_fuzzy_fallback_rescues_unspecified_endpoint_and_reports_details(self) -> None:
        site_a = _FakeSite(name="Alpha", slug="alpha", latitude=25.0, longitude=118.0)
        site_z = _FakeSite(name="Beta Hub Main", slug="beta-hub-main", latitude=25.0012, longitude=118.0012)
        far_site = _FakeSite(name="Gamma Remote", slug="gamma-remote", latitude=27.0, longitude=120.0)
        _FakeSite.objects = _FakeSiteManager([site_a, site_z, far_site])
        _FakeOtnPath.created = []
        _FakeOtnPath.save_calls = 0

        module = _load_script_module(_FakeSite, _FakeOtnPath)
        script = module.ImportOtnPaths()
        script.log_info = lambda message: None
        script.log_warning = lambda message: None
        script.log_success = lambda message: None
        script.log_failure = lambda message: None

        def _fake_fetch(url):
            if url.endswith("/1"):
                return {
                    "features": [
                        {
                            "geometry": {
                                "paths": [
                                    [
                                        [118.0, 25.0],
                                        [118.001, 25.001],
                                    ]
                                ]
                            },
                            "attributes": {
                                "O_NAME": "Alpha-Beta Hub",
                                "O_COM": "demo",
                            },
                        }
                    ]
                }
            return {"features": []}

        script.fetch_arcgis_data = _fake_fetch
        report = script.run({"distance_threshold": 10, "dry_run": True}, commit=False)

        self.assertEqual(len(_FakeOtnPath.created), 1)
        created_path = _FakeOtnPath.created[0]
        self.assertEqual(created_path["site_a"].name, "Alpha")
        self.assertEqual(created_path["site_z"].name, "Beta Hub Main")
        self.assertIn("模糊匹配修正成功", report)
        self.assertIn("Alpha-Beta Hub", report)
        self.assertIn("Beta Hub Main", report)

    def test_bidirectional_name_matching_handles_za_order(self) -> None:
        site_a = _FakeSite(name="Alpha", slug="alpha", latitude=25.0002, longitude=118.0002)
        site_z = _FakeSite(name="Beta Hub Main", slug="beta-hub-main", latitude=25.0012, longitude=118.0012)
        _FakeSite.objects = _FakeSiteManager([site_a, site_z])
        _FakeOtnPath.created = []
        _FakeOtnPath.save_calls = 0

        module = _load_script_module(_FakeSite, _FakeOtnPath)
        script = module.ImportOtnPaths()
        script.log_info = lambda message: None
        script.log_warning = lambda message: None
        script.log_success = lambda message: None
        script.log_failure = lambda message: None

        def _fake_fetch(url):
            if url.endswith("/1"):
                return {
                    "features": [
                        {
                            "geometry": {
                                "paths": [
                                    [
                                        [118.0, 25.0],
                                        [118.001, 25.001],
                                    ]
                                ]
                            },
                            "attributes": {
                                "O_NAME": "Beta Hub Main-Alpha",
                                "O_COM": "demo",
                            },
                        }
                    ]
                }
            return {"features": []}

        script.fetch_arcgis_data = _fake_fetch
        script.run({"distance_threshold": 10, "dry_run": True}, commit=False)

        self.assertEqual(len(_FakeOtnPath.created), 1)
        created_path = _FakeOtnPath.created[0]
        self.assertEqual(created_path["site_a"].name, "Alpha")
        self.assertEqual(created_path["site_z"].name, "Beta Hub Main")
        self.assertEqual(created_path["name"], "Alpha-Beta Hub Main")

    def test_low_quality_successful_match_is_reported(self) -> None:
        site_a = _FakeSite(name="Alpha Data Center", slug="alpha-data-center", latitude=25.0, longitude=118.0)
        site_z = _FakeSite(name="Beta Switching Hub", slug="beta-switching-hub", latitude=25.001, longitude=118.001)
        _FakeSite.objects = _FakeSiteManager([site_a, site_z])
        _FakeOtnPath.created = []
        _FakeOtnPath.save_calls = 0

        module = _load_script_module(_FakeSite, _FakeOtnPath)
        script = module.ImportOtnPaths()
        script.log_info = lambda message: None
        script.log_warning = lambda message: None
        script.log_success = lambda message: None
        script.log_failure = lambda message: None

        def _fake_fetch(url):
            if url.endswith("/1"):
                return {
                    "features": [
                        {
                            "geometry": {
                                "paths": [
                                    [
                                        [118.0, 25.0],
                                        [118.001, 25.001],
                                    ]
                                ]
                            },
                            "attributes": {
                                "O_NAME": "Node-12",
                                "O_COM": "demo",
                            },
                        }
                    ]
                }
            return {"features": []}

        script.fetch_arcgis_data = _fake_fetch
        report = script.run({"distance_threshold": 500, "dry_run": True}, commit=False)

        self.assertIn("低匹配度路径汇总", report)
        self.assertIn("Node-12", report)
        self.assertIn("Alpha Data Center-Beta Switching Hub", report)
        self.assertIn("综合得分", report)


class ImportOtnPathsProxyHandlingTestCase(unittest.TestCase):
    def test_fetch_arcgis_data_uses_session_without_environment_proxies(self) -> None:
        _FakeSite.objects = _FakeSiteManager([])
        _FakeOtnPath.created = []
        module = _load_script_module(_FakeSite, _FakeOtnPath)

        class _FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {"features": []}

        class _FakeSession:
            def __init__(self) -> None:
                self.trust_env = True
                self.calls = []

            def get(self, url, params=None, timeout=None):
                self.calls.append((url, params, timeout))
                return _FakeResponse()

        fake_session = _FakeSession()
        module.requests.get = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("fetch_arcgis_data() should not call requests.get directly")
        )
        module.requests.Session = lambda: fake_session

        script = module.ImportOtnPaths()
        script.log_failure = lambda message: None

        result = script.fetch_arcgis_data("http://example.test/layer")

        self.assertEqual(result, {"features": []})
        self.assertIs(fake_session.trust_env, False)
        self.assertEqual(len(fake_session.calls), 1)
        self.assertEqual(fake_session.calls[0][0], "http://example.test/layer/query")


if __name__ == "__main__":
    unittest.main()

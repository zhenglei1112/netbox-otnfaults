import importlib.util
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "netbox_otnfaults" / "scripts" / "import_arcgis_sites.py"


def _install_import_stubs() -> None:
    if "django.utils.text" not in sys.modules:
        django_module = types.ModuleType("django")
        utils_module = types.ModuleType("django.utils")
        text_module = types.ModuleType("django.utils.text")
        text_module.slugify = lambda value: str(value).lower().replace(" ", "-")
        sys.modules["django"] = django_module
        sys.modules["django.utils"] = utils_module
        sys.modules["django.utils.text"] = text_module

    if "dcim.models" not in sys.modules:
        dcim_module = types.ModuleType("dcim")
        dcim_models_module = types.ModuleType("dcim.models")
        dcim_models_module.Site = type("Site", (), {"objects": None})
        dcim_choices_module = types.ModuleType("dcim.choices")
        dcim_choices_module.SiteStatusChoices = type(
            "SiteStatusChoices",
            (),
            {"STATUS_ACTIVE": "active"},
        )
        sys.modules["dcim"] = dcim_module
        sys.modules["dcim.models"] = dcim_models_module
        sys.modules["dcim.choices"] = dcim_choices_module

    if "extras.scripts" not in sys.modules:
        extras_module = types.ModuleType("extras")
        extras_scripts_module = types.ModuleType("extras.scripts")

        class _Script:
            pass

        class _Var:
            def __init__(self, *args, **kwargs) -> None:
                self.args = args
                self.kwargs = kwargs

        extras_scripts_module.Script = _Script
        extras_scripts_module.StringVar = _Var
        extras_scripts_module.BooleanVar = _Var
        sys.modules["extras"] = extras_module
        sys.modules["extras.scripts"] = extras_scripts_module

    if "requests" not in sys.modules:
        requests_module = types.ModuleType("requests")
        requests_module.get = lambda *args, **kwargs: None
        sys.modules["requests"] = requests_module


def _load_script_module():
    _install_import_stubs()
    spec = importlib.util.spec_from_file_location("test_import_arcgis_sites_module", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _DummyScript:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def log_info(self, message: str) -> None:
        self.messages.append(("info", message))

    def log_warning(self, message: str) -> None:
        self.messages.append(("warning", message))

    def log_success(self, message: str) -> None:
        self.messages.append(("success", message))

    def log_failure(self, message: str) -> None:
        self.messages.append(("failure", message))


class ImportArcGISSitesHelperTestCase(unittest.TestCase):
    def test_find_nearby_duplicate_pairs_returns_pairs_within_threshold(self) -> None:
        module = _load_script_module()

        pairs = module._find_nearby_duplicate_pairs(
            [
                ("site-a", 25.0, 118.0),
                ("site-b", 25.0003, 118.0003),
                ("site-c", 26.0, 119.0),
            ],
            threshold_m=100.0,
        )

        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0], "site-a")
        self.assertEqual(pairs[0][1], "site-b")
        self.assertLess(pairs[0][2], 100.0)

    def test_classify_nearby_duplicate_prefers_existing_sites_over_batch_sites(self) -> None:
        module = _load_script_module()

        duplicate = module._classify_nearby_duplicate(
            name="incoming-site",
            latitude=25.0,
            longitude=118.0,
            existing_site_coords=[("existing-site", 25.0003, 118.0003)],
            batch_site_coords=[("batch-site", 25.0002, 118.0002)],
            threshold_m=100.0,
        )

        self.assertEqual(duplicate[0], "existing")
        self.assertEqual(duplicate[1], "existing-site")
        self.assertLess(duplicate[2], 100.0)

    def test_classify_nearby_duplicate_detects_batch_duplicates(self) -> None:
        module = _load_script_module()

        duplicate = module._classify_nearby_duplicate(
            name="incoming-site",
            latitude=25.0,
            longitude=118.0,
            existing_site_coords=[],
            batch_site_coords=[("batch-site", 25.0003, 118.0003)],
            threshold_m=100.0,
        )

        self.assertEqual(duplicate[0], "batch")
        self.assertEqual(duplicate[1], "batch-site")
        self.assertLess(duplicate[2], 100.0)


class ImportArcGISSitesLoggingTestCase(unittest.TestCase):
    def test_log_existing_nearby_duplicates_logs_warning_details(self) -> None:
        module = _load_script_module()
        script = _DummyScript()

        module._log_existing_nearby_duplicates(
            script,
            [
                ("site-a", 25.0, 118.0),
                ("site-b", 25.0003, 118.0003),
            ],
            threshold_m=100.0,
        )

        self.assertTrue(any(level == "warning" for level, _ in script.messages))
        self.assertTrue(any("100m" in message for _, message in script.messages))


if __name__ == "__main__":
    unittest.main()

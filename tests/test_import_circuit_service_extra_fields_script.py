import importlib.util
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "netbox_otnfaults" / "scripts" / "import_circuit_service_extra_fields.py"


class _Var:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs


class _BaseScript:
    def __init__(self) -> None:
        self.info_logs: list[str] = []
        self.warning_logs: list[str] = []
        self.success_logs: list[str] = []

    def log_info(self, message: str) -> None:
        self.info_logs.append(message)

    def log_warning(self, message: str) -> None:
        self.warning_logs.append(message)

    def log_success(self, message: str) -> None:
        self.success_logs.append(message)


class _FakeCircuitServiceDoesNotExist(Exception):
    pass


class _FakeCircuitService:
    DoesNotExist = _FakeCircuitServiceDoesNotExist
    objects = None

    def __init__(self, special_line_name: str, name: str, extra_fields: dict[str, str] | None = None) -> None:
        self.special_line_name = special_line_name
        self.name = name
        self.extra_fields = extra_fields or {}
        self.save_calls: list[list[str] | None] = []

    def save(self, update_fields=None) -> None:
        self.save_calls.append(update_fields)


class _FakeCircuitServiceManager:
    def __init__(self, services: list[_FakeCircuitService]) -> None:
        self.services = services

    def get(self, special_line_name: str, name: str) -> _FakeCircuitService:
        for service in self.services:
            if service.special_line_name == special_line_name and service.name == name:
                return service
        raise _FakeCircuitService.DoesNotExist()


class _FakeRow:
    def __init__(
        self,
        row_number: int,
        special_line_name: str,
        circuit_number: str,
        extra_fields: dict[str, str] | None,
    ) -> None:
        self.row_number = row_number
        self.special_line_name = special_line_name
        self.circuit_number = circuit_number
        self.extra_fields = extra_fields


def _install_import_stubs() -> types.ModuleType:
    extras_module = types.ModuleType("extras")
    extras_scripts_module = types.ModuleType("extras.scripts")
    extras_scripts_module.Script = _BaseScript
    extras_scripts_module.StringVar = _Var
    extras_scripts_module.FileVar = _Var
    sys.modules["extras"] = extras_module
    sys.modules["extras.scripts"] = extras_scripts_module

    plugin_module = types.ModuleType("netbox_otnfaults")
    plugin_module.__path__ = []
    plugin_models_module = types.ModuleType("netbox_otnfaults.models")
    plugin_models_module.CircuitService = _FakeCircuitService
    sys.modules["netbox_otnfaults"] = plugin_module
    sys.modules["netbox_otnfaults.models"] = plugin_models_module

    services_module = types.ModuleType("netbox_otnfaults.services")
    excel_module = types.ModuleType("netbox_otnfaults.services.circuit_service_excel_import")
    excel_module.read_circuit_service_excel_rows = lambda path, sheet_name="最终数据": []
    sys.modules["netbox_otnfaults.services"] = services_module
    sys.modules["netbox_otnfaults.services.circuit_service_excel_import"] = excel_module
    return excel_module


def _load_script_module():
    excel_module = _install_import_stubs()
    spec = importlib.util.spec_from_file_location("test_import_circuit_extra_fields", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, excel_module


class ImportCircuitServiceExtraFieldsScriptTestCase(unittest.TestCase):
    def test_updates_existing_service_extra_fields_and_preserves_unmentioned_values(self) -> None:
        module, excel_module = _load_script_module()
        self.assertIs(module.ImportCircuitServiceExtraFields.excel_file.__class__, _Var)
        self.assertFalse(hasattr(module.ImportCircuitServiceExtraFields, "excel_path"))
        service = _FakeCircuitService(
            special_line_name="行业专网-江苏",
            name="221132200N9001JT",
            extra_fields={"request_number": "OLD", "manual_note": "keep"},
        )
        _FakeCircuitService.objects = _FakeCircuitServiceManager([service])
        module.read_circuit_service_excel_rows = lambda path, sheet_name="最终数据": [
            _FakeRow(
                3,
                "行业专网-江苏",
                "221132200N9001JT",
                {"request_number": "REQ-001", "contract_number": "HT-001"},
            )
        ]

        script = module.ImportCircuitServiceExtraFields()
        script.run({"excel_file": object(), "sheet_name": "最终数据"}, commit=True)

        self.assertEqual(
            service.extra_fields,
            {"request_number": "REQ-001", "manual_note": "keep", "contract_number": "HT-001"},
        )
        self.assertEqual(service.save_calls, [["extra_fields"]])
        self.assertTrue(any("更新 1 条" in message for message in script.success_logs))

    def test_commit_false_previews_without_saving(self) -> None:
        module, excel_module = _load_script_module()
        service = _FakeCircuitService("行业专网-江苏", "221132200N9001JT", {})
        _FakeCircuitService.objects = _FakeCircuitServiceManager([service])
        module.read_circuit_service_excel_rows = lambda path, sheet_name="最终数据": [
            _FakeRow(3, "行业专网-江苏", "221132200N9001JT", {"request_number": "REQ-001"})
        ]

        script = module.ImportCircuitServiceExtraFields()
        script.run({"excel_file": object(), "sheet_name": "最终数据"}, commit=False)

        self.assertEqual(service.extra_fields, {})
        self.assertEqual(service.save_calls, [])
        self.assertTrue(any("模拟运行" in message for message in script.warning_logs))

    def test_logs_unmatched_rows(self) -> None:
        module, excel_module = _load_script_module()
        _FakeCircuitService.objects = _FakeCircuitServiceManager([])
        module.read_circuit_service_excel_rows = lambda path, sheet_name="最终数据": [
            _FakeRow(3, "不存在专线", "NO-001", {"request_number": "REQ-001"})
        ]

        script = module.ImportCircuitServiceExtraFields()
        script.run({"excel_file": object(), "sheet_name": "最终数据"}, commit=True)

        self.assertTrue(any("未找到" in message for message in script.warning_logs))
        self.assertTrue(any("未匹配 1 条" in message for message in script.success_logs))


if __name__ == "__main__":
    unittest.main()

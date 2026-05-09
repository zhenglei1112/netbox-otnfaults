import datetime as dt
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "netbox_otnfaults" / "scripts" / "ministry_weekly_fault_report.py"
TZ = ZoneInfo("Asia/Shanghai")


def aware(year: int, month: int, day: int, hour: int, minute: int = 0, second: int = 0) -> dt.datetime:
    return dt.datetime(year, month, day, hour, minute, second, tzinfo=TZ)


class _Var:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs


class _BaseScript:
    def __init__(self) -> None:
        self.info_logs: list[str] = []
        self.success_logs: list[str] = []

    def log_info(self, message: str) -> None:
        self.info_logs.append(message)

    def log_success(self, message: str) -> None:
        self.success_logs.append(message)

    def get_job_data(self) -> dict[str, object]:
        return {
            "log": self.info_logs + self.success_logs,
            "output": "",
            "tests": {},
        }


class _FakeSite:
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name


class _FakeUser:
    def __init__(self, name: str) -> None:
        self.name = name

    def get_full_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return "fallback"


class _FakeManyToMany:
    def __init__(self, values: list[_FakeSite]) -> None:
        self.values = values

    def all(self) -> list[_FakeSite]:
        return self.values


class _FakeFault:
    def __init__(self) -> None:
        self.fault_number = "F20260424001"
        self.fault_category = "fiber_break"
        self.duty_officer = _FakeUser("郑帆")
        self.interruption_location_a = _FakeSite("混池")
        self.interruption_location = _FakeManyToMany([_FakeSite("孟津")])
        self.fault_occurrence_time = dt.datetime(2026, 4, 24, 0, 0, tzinfo=TZ)
        self.fault_recovery_time = dt.datetime(2026, 4, 24, 1, 43, 28, tzinfo=TZ)
        self.interruption_reason = "cable_rectification"
        self.interruption_reason_detail = "planned_reporting"

    def get_fault_category_display(self) -> str:
        return "光缆中断"

    def get_interruption_reason_display(self) -> str:
        return "光缆整改"

    def get_interruption_reason_detail_display(self) -> str:
        return "计划报备"


class _FakeQuerySet:
    def __init__(self, faults: list[_FakeFault]) -> None:
        self.faults = faults
        self.filter_kwargs: dict[str, object] = {}

    def filter(self, **kwargs):
        self.filter_kwargs.update(kwargs)
        return self

    def select_related(self, *args):
        return self

    def prefetch_related(self, *args):
        return self

    def order_by(self, *args):
        return self

    def distinct(self):
        return self

    def __iter__(self):
        return iter(self.faults)


class _FakeOtnFault:
    objects = _FakeQuerySet([_FakeFault()])


def _install_import_stubs() -> None:
    extras_module = types.ModuleType("extras")
    extras_scripts_module = types.ModuleType("extras.scripts")
    extras_scripts_module.Script = _BaseScript
    extras_scripts_module.DateVar = _Var
    sys.modules["extras"] = extras_module
    sys.modules["extras.scripts"] = extras_scripts_module

    django_module = types.ModuleType("django")
    django_utils_module = types.ModuleType("django.utils")
    django_timezone_module = types.ModuleType("django.utils.timezone")
    django_timezone_module.get_current_timezone = lambda: TZ
    django_timezone_module.localtime = lambda value=None: value
    django_timezone_module.localdate = lambda: dt.date(2026, 4, 24)
    sys.modules["django"] = django_module
    sys.modules["django.utils"] = django_utils_module
    sys.modules["django.utils.timezone"] = django_timezone_module

    plugin_module = types.ModuleType("netbox_otnfaults")
    plugin_module.__path__ = [str(REPO_ROOT / "netbox_otnfaults")]
    models_module = types.ModuleType("netbox_otnfaults.models")
    models_module.OtnFault = _FakeOtnFault
    sys.modules["netbox_otnfaults"] = plugin_module
    sys.modules["netbox_otnfaults.models"] = models_module


def _load_script_module():
    _install_import_stubs()
    spec = importlib.util.spec_from_file_location("test_ministry_weekly_fault_report_script_module", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_script_module_without_service_package():
    _install_import_stubs()
    service_module_names = [
        name
        for name in sys.modules
        if name == "netbox_otnfaults.services"
        or name.startswith("netbox_otnfaults.services.")
    ]
    for name in service_module_names:
        sys.modules.pop(name, None)

    package = sys.modules["netbox_otnfaults"]
    package.__path__ = []

    spec = importlib.util.spec_from_file_location("test_ministry_weekly_fault_report_script_no_service", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MinistryWeeklyFaultReportScriptTestCase(unittest.TestCase):
    def test_module_loads_even_when_service_package_is_unavailable(self) -> None:
        module = _load_script_module_without_service_package()

        self.assertTrue(hasattr(module, "MinistryWeeklyFaultReport"))

    def test_script_source_does_not_import_ministry_weekly_report_service(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertNotIn("netbox_otnfaults.services import ministry_weekly_fault_report", source)
        self.assertNotIn('"services" / "ministry_weekly_fault_report.py"', source)

    def test_load_report_service_uses_script_local_implementation(self) -> None:
        module = _load_script_module()
        sys.modules.pop("netbox_otnfaults.services.ministry_weekly_fault_report", None)
        services_module = types.ModuleType("netbox_otnfaults.services")
        services_module.__path__ = []
        sys.modules["netbox_otnfaults.services"] = services_module
        if hasattr(module, "__file__"):
            delattr(module, "__file__")

        service = module._load_report_service()

        self.assertTrue(hasattr(service, "FaultReportRecord"))
        self.assertTrue(hasattr(service, "build_week_range"))
        self.assertTrue(hasattr(service, "build_weekly_report_rows"))
        self.assertTrue(hasattr(service, "render_csv"))

    def test_build_week_range_uses_monday_to_next_monday_for_input_date(self) -> None:
        module = _load_script_module()
        service = module._load_report_service()

        start, end = service.build_week_range(dt.date(2026, 4, 24), timezone=TZ)

        self.assertEqual(start, aware(2026, 4, 20, 0, 0))
        self.assertEqual(end, aware(2026, 4, 27, 0, 0))

    def test_merges_same_day_same_scope_and_prefers_first_fiber_break_as_carrier(self) -> None:
        module = _load_script_module()
        service = module._load_report_service()
        record_class = service.FaultReportRecord
        records = [
            record_class(
                fault_number="F20260424009",
                fault_category="fiber_jitter",
                fault_category_label="光缆抖动",
                duty_officer="王宝梁",
                site_a="洋中",
                site_z=("延平",),
                occurrence_time=aware(2026, 4, 24, 11, 54),
                duration_seconds=313,
                primary_reason="unknown",
                primary_reason_label="无法查明",
                secondary_reason_label="",
            ),
            record_class(
                fault_number="F20260424010",
                fault_category="fiber_degradation",
                fault_category_label="光缆劣化",
                duty_officer="王宝梁",
                site_a="洋中",
                site_z=("延平",),
                occurrence_time=aware(2026, 4, 24, 12, 10),
                duration_seconds=600,
                primary_reason="unknown",
                primary_reason_label="无法查明",
                secondary_reason_label="",
            ),
            record_class(
                fault_number="F20260424011",
                fault_category="fiber_break",
                fault_category_label="光缆中断",
                duty_officer="王宝梁",
                site_a="洋中",
                site_z=("延平",),
                occurrence_time=aware(2026, 4, 24, 12, 20),
                duration_seconds=3600,
                primary_reason="unknown",
                primary_reason_label="无法查明",
                secondary_reason_label="",
            ),
        ]

        rows = service.build_weekly_report_rows(records)

        self.assertEqual([row["故障编号"] for row in rows], ["F20260424011"])
        self.assertEqual(rows[0]["故障历时"], "1小时15分13秒")
        self.assertEqual(rows[0]["对部周报"], "合并了F20260424009、F20260424010")

    def test_cable_rectification_rows_are_marked_without_merge_note_when_single(self) -> None:
        module = _load_script_module()
        service = module._load_report_service()
        record_class = service.FaultReportRecord

        rows = service.build_weekly_report_rows([
            record_class(
                fault_number="F20260424001",
                fault_category="fiber_break",
                fault_category_label="光缆中断",
                duty_officer="郑帆",
                site_a="混池",
                site_z=("孟津",),
                occurrence_time=aware(2026, 4, 24, 0, 0),
                duration_seconds=6208,
                primary_reason="cable_rectification",
                primary_reason_label="光缆整改",
                secondary_reason_label="计划报备",
            )
        ])

        self.assertEqual(rows[0]["对部周报"], "否，整改")

    def test_render_csv_keeps_weekly_report_as_last_column_and_adds_bom(self) -> None:
        module = _load_script_module()
        service = module._load_report_service()

        csv_text = service.render_csv([
            {
                "故障编号": "F20260424001",
                "故障分类": "光缆中断",
                "值守人员": "郑帆",
                "A端": "混池",
                "Z端": "孟津",
                "起始时间": "2026/4/24 0:00",
                "故障历时": "1小时43分28秒",
                "一级原因": "光缆整改",
                "二级原因": "计划报备",
                "对部周报": "否，整改",
            }
        ])

        self.assertTrue(csv_text.startswith("\ufeff"))
        header = csv_text.splitlines()[0].lstrip("\ufeff")
        self.assertTrue(header.endswith(",对部周报"))

    def test_run_queries_88_tag_faults_for_input_week_and_returns_csv(self) -> None:
        module = _load_script_module()

        script = module.MinistryWeeklyFaultReport()
        csv_text = script.run({"report_date": dt.date(2026, 4, 24)}, commit=False)

        filter_kwargs = _FakeOtnFault.objects.filter_kwargs
        self.assertEqual(filter_kwargs["fault_occurrence_time__gte"], dt.datetime(2026, 4, 20, 0, 0, tzinfo=TZ))
        self.assertEqual(filter_kwargs["fault_occurrence_time__lt"], dt.datetime(2026, 4, 27, 0, 0, tzinfo=TZ))
        self.assertEqual(filter_kwargs["tags__name__icontains"], "涉及88系统")
        self.assertIn("F20260424001", csv_text)
        self.assertIn("否，整改", csv_text)
        self.assertEqual(script.output_mime_type, "text/csv; charset=utf-8")
        self.assertEqual(script.output_extension, "csv")
        self.assertEqual(script.output_filename, "ministry_weekly_fault_report_20260424.csv")
        job_data = script.get_job_data()
        self.assertEqual(job_data["output_mime_type"], "text/csv; charset=utf-8")
        self.assertEqual(job_data["output_extension"], "csv")
        self.assertEqual(job_data["output_filename"], "ministry_weekly_fault_report_20260424.csv")
        self.assertTrue(any("生成 1 条" in message for message in script.success_logs))


if __name__ == "__main__":
    unittest.main()

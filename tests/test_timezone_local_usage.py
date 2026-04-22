import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8-sig")


class TimezoneLocalUsageSourceTestCase(unittest.TestCase):
    def test_business_views_use_localtime_for_current_period_boundaries(self) -> None:
        risky_view_files = [
            "netbox_otnfaults/api/views.py",
            "netbox_otnfaults/dashboard_views.py",
            "netbox_otnfaults/views.py",
            "netbox_otnfaults/statistics_views.py",
        ]

        for relative_path in risky_view_files:
            with self.subTest(path=relative_path):
                source = _read(relative_path)
                self.assertNotIn("timezone.now().year", source)
                self.assertNotIn("now = timezone.now()", source)

    def test_plugin_runtime_code_does_not_read_utc_now_directly(self) -> None:
        runtime_files = [
            path for path in (REPO_ROOT / "netbox_otnfaults").rglob("*.py")
            if "__pycache__" not in path.parts and "migrations" not in path.parts
        ]

        for path in runtime_files:
            with self.subTest(path=str(path.relative_to(REPO_ROOT))):
                source = path.read_text(encoding="utf-8-sig")
                self.assertNotIn("timezone.now(", source)

    def test_scripts_use_local_current_dates_when_formatting_or_extracting_dates(self) -> None:
        risky_script_files = [
            "netbox_otnfaults/scripts/generate_fault_data.py",
            "netbox_otnfaults/scripts/weekly_fault_report.py",
        ]

        for relative_path in risky_script_files:
            with self.subTest(path=relative_path):
                source = _read(relative_path)
                self.assertNotIn("timezone.now().date()", source)
                self.assertNotIn("timezone.now().strftime(", source)

    def test_statistics_dashboard_uses_local_date_arithmetic(self) -> None:
        source = _read("netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js")

        self.assertNotIn("Date.UTC", source)
        self.assertNotIn("getUTC", source)
        self.assertNotIn("setUTC", source)
        self.assertNotIn("todayUtc", source)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "netbox_otnfaults" / "weekly_report_summary.py"
SPEC = importlib.util.spec_from_file_location("test_weekly_report_summary_module", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
build_bare_fiber_summary = MODULE.build_bare_fiber_summary


class BuildBareFiberSummaryTestCase(unittest.TestCase):
    def test_build_bare_fiber_summary_counts_interruption_jitter_and_normal_services(self) -> None:
        services = [
            {"name": "专线-1", "status": "interruption"},
            {"name": "专线-2", "status": "interruption"},
            {"name": "专线-3", "status": "jitter"},
            {"name": "专线-4", "status": "jitter"},
            {"name": "专线-5", "status": "jitter"},
        ]

        summary = build_bare_fiber_summary(total_services=20, impacted_services=services)

        self.assertEqual(
            summary,
            {
                "interruption": 2,
                "jitter": 3,
                "normal": 15,
            },
        )


if __name__ == "__main__":
    unittest.main()

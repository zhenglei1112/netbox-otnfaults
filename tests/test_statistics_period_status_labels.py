import importlib.util
import unittest
from datetime import datetime
from pathlib import Path


PERIOD_HELPER_PATH = Path(__file__).resolve().parents[1] / "netbox_otnfaults" / "statistics_period.py"


def load_period_helper_module():
    spec = importlib.util.spec_from_file_location("test_statistics_period_status_module", PERIOD_HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class StatisticsPeriodStatusLabelsTestCase(unittest.TestCase):
    def test_current_period_uses_current_label(self) -> None:
        module = load_period_helper_module()

        period = module.build_period_display(
            start_date=datetime(2026, 4, 14, 0, 0, 0),
            end_date=datetime(2026, 4, 21, 0, 0, 0),
            now=datetime(2026, 4, 15, 9, 30, 0),
        )

        self.assertEqual(period, {"start": "2026-04-14", "end": "当前", "is_future": False})

    def test_future_period_uses_not_arrived_label(self) -> None:
        module = load_period_helper_module()

        period = module.build_period_display(
            start_date=datetime(2026, 4, 20, 0, 0, 0),
            end_date=datetime(2026, 4, 27, 0, 0, 0),
            now=datetime(2026, 4, 15, 9, 30, 0),
        )

        self.assertEqual(period, {"start": "2026-04-20", "end": "未到日期", "is_future": True})


if __name__ == "__main__":
    unittest.main()

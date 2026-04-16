import importlib.util
import unittest
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STATISTICS_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
PERIOD_HELPER_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_period.py"


def load_period_helper_module():
    assert PERIOD_HELPER_PATH.exists(), f"Missing helper module: {PERIOD_HELPER_PATH}"
    spec = importlib.util.spec_from_file_location("test_statistics_period_module", PERIOD_HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class StatisticsPeriodDisplayTestCase(unittest.TestCase):
    def test_build_period_display_uses_current_label_when_display_end_is_after_today(self) -> None:
        module = load_period_helper_module()

        period = module.build_period_display(
            start_date=datetime(2026, 4, 14, 0, 0, 0),
            end_date=datetime(2026, 4, 21, 0, 0, 0),
            now=datetime(2026, 4, 15, 9, 30, 0),
        )

        self.assertEqual(period, {"start": "2026-04-14", "end": "当前", "is_future": False})

    def test_build_period_display_keeps_actual_date_when_display_end_is_not_in_future(self) -> None:
        module = load_period_helper_module()

        period = module.build_period_display(
            start_date=datetime(2026, 4, 1, 0, 0, 0),
            end_date=datetime(2026, 4, 16, 0, 0, 0),
            now=datetime(2026, 4, 15, 9, 30, 0),
        )

        self.assertEqual(period, {"start": "2026-04-01", "end": "2026-04-15", "is_future": False})

    def test_statistics_views_use_shared_period_display_helper(self) -> None:
        source = STATISTICS_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("from .statistics_period import build_period_display", source)
        self.assertGreaterEqual(source.count("build_period_display(start_date, end_date, now)"), 2)


if __name__ == "__main__":
    unittest.main()


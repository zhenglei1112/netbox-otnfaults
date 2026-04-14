import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"


class OtnFaultTimelineDateFormatSourceTestCase(unittest.TestCase):
    def test_cross_day_timeline_uses_chinese_date_without_parentheses(self) -> None:
        models_source = MODELS_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("time_str = dt_local.strftime('%H:%M:%S') if dt_local else ''", models_source)
        self.assertIn("date_str = f\"{dt_local.month}月{dt_local.day}日\"", models_source)
        self.assertIn("time_str = f\"{date_str}\\n{time_str}\"", models_source)
        self.assertNotIn("time_str += f\"\\n({dt_local.strftime('%m-%d')})\"", models_source)


if __name__ == "__main__":
    unittest.main()

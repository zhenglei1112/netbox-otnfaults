import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"


class OtnFaultTimelineSameDayPlaceholderSourceTestCase(unittest.TestCase):
    def test_same_day_highlight_uses_invisible_placeholder_first_line(self) -> None:
        models_source = MODELS_PATH.read_text(encoding="utf-8-sig")

        self.assertIn('date_str = f"{dt_local.month}月{dt_local.day}日"', models_source)
        self.assertIn('time_str = f"{date_str}\\n{time_str}"', models_source)
        self.assertIn("elif i in (0, 4):", models_source)
        self.assertIn('time_str = f"　\\n{time_str}"', models_source)
        self.assertNotIn('time_str = f"\\n{time_str}"', models_source)


if __name__ == "__main__":
    unittest.main()

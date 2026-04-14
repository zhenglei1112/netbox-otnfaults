import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"
MODEL_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"


class OtnFaultDetailFaultNumberDisplaySourceTestCase(unittest.TestCase):
    def test_template_uses_raw_fault_number(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("{{ object.fault_number|default:", template_text)
        self.assertNotIn("{{ object.formatted_fault_number|default:", template_text)

    def test_model_contains_formatted_fault_number_property(self) -> None:
        model_text = MODEL_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("def formatted_fault_number(self)", model_text)
        self.assertIn("fault_number[1:5]", model_text)
        self.assertIn("fault_number[5:7]", model_text)
        self.assertIn("fault_number[7:9]", model_text)
        self.assertIn('return f"{fault_number}（{year}年{month}月{day}日）"', model_text)


if __name__ == "__main__":
    unittest.main()

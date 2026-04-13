import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"


class OtnFaultTagsHelpTextSourceTestCase(unittest.TestCase):
    def test_otnfault_form_sets_tags_help_text_for_88_system_faults(self) -> None:
        forms_text = FORMS_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("self.fields['tags'].help_text", forms_text)
        self.assertIn("若故障涉及88系统，需勾选对应标签。", forms_text)


if __name__ == "__main__":
    unittest.main()

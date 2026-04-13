import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_edit.html"


class OtnFaultEditFieldOrderSourceTestCase(unittest.TestCase):
    def test_first_report_source_and_tags_follow_urgency(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        urgency_marker = "{% render_field form.urgency %}"
        first_report_source_marker = "{% render_field form.first_report_source %}"
        tags_marker = "{% render_field form.tags %}"
        province_marker = "{% render_field form.province %}"

        urgency_index = template_text.index(urgency_marker)
        first_report_source_index = template_text.index(first_report_source_marker)
        tags_index = template_text.index(tags_marker)
        province_index = template_text.index(province_marker)

        self.assertLess(urgency_index, first_report_source_index)
        self.assertLess(first_report_source_index, tags_index)
        self.assertLess(tags_index, province_index)


if __name__ == "__main__":
    unittest.main()

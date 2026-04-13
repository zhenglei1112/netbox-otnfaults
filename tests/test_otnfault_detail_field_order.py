import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"


class OtnFaultDetailFieldOrderSourceTestCase(unittest.TestCase):
    def test_first_report_source_row_uses_valid_default_filter_syntax(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn(
            '{{ object.get_first_report_source_display|default:"—" }}',
            template_text,
        )

    def test_first_report_source_is_between_basic_info_and_location(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        basic_info_marker = "{{ object.fault_number|default:"
        first_report_source_marker = "{{ object.get_first_report_source_display|default:"
        location_marker = "{% if object.interruption_location_a %}"

        basic_info_index = template_text.index(basic_info_marker)
        first_report_source_index = template_text.index(first_report_source_marker)
        location_index = template_text.index(location_marker)

        self.assertLess(basic_info_index, first_report_source_index)
        self.assertLess(first_report_source_index, location_index)


if __name__ == "__main__":
    unittest.main()

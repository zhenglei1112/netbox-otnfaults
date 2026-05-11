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

    def test_power_fault_fields_follow_fault_type_as_plain_text(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        fault_type_marker = "{% badge object.get_fault_category_display bg_color=object.get_fault_category_color %}"
        phenomenon_marker = "{{ object.get_power_fault_phenomenon_display|default:"
        impact_marker = "{{ object.get_power_fault_impact_display|default:"
        status_marker = "{% badge object.get_fault_status_display bg_color=object.get_fault_status_color %}"
        supplemental_marker = '<h5 class="card-header">供电故障补充信息</h5>'

        self.assertLess(template_text.index(fault_type_marker), template_text.index(phenomenon_marker))
        self.assertLess(template_text.index(phenomenon_marker), template_text.index(impact_marker))
        self.assertLess(template_text.index(impact_marker), template_text.index(status_marker))

        basic_info_block = template_text.split('<h5 class="card-header">故障信息</h5>', 1)[1].split(
            '<h5 class="card-header">时间轴</h5>', 1
        )[0]
        self.assertNotIn("get_power_fault_phenomenon_color", basic_info_block)
        self.assertNotIn("get_power_fault_impact_color", basic_info_block)

        supplemental_block = template_text.split(supplemental_marker, 1)[1].split("</table>", 1)[0]
        self.assertNotIn("power_fault_phenomenon", supplemental_block)
        self.assertNotIn("power_fault_impact", supplemental_block)

    def test_blank_power_fault_fields_render_dash_in_detail(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn('{{ object.get_power_fault_phenomenon_display|default:"—" }}', template_text)
        self.assertIn('{{ object.get_power_fault_impact_display|default:"—" }}', template_text)


if __name__ == "__main__":
    unittest.main()

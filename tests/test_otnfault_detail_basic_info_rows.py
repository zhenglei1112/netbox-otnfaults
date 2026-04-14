import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"


class OtnFaultDetailBasicInfoRowsSourceTestCase(unittest.TestCase):
    def test_basic_info_fields_render_as_independent_rows(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertNotIn('<th scope="row">故障基本信息</th>', template_text)
        self.assertIn('<th scope="row"><span style="white-space: nowrap; word-break: keep-all;">故障编号</span></th>', template_text)
        self.assertIn('<th scope="row"><span style="white-space: nowrap; word-break: keep-all;">故障类型</span></th>', template_text)
        self.assertIn('<th scope="row"><span style="white-space: nowrap; word-break: keep-all;">处理状态</span></th>', template_text)
        self.assertIn('<th scope="row"><span style="white-space: nowrap; word-break: keep-all;">紧急程度</span></th>', template_text)

        fault_number_index = template_text.index('{{ object.formatted_fault_number|default:')
        fault_category_index = template_text.index('{% badge object.get_fault_category_display bg_color=object.get_fault_category_color %}')
        fault_status_index = template_text.index('{% badge object.get_fault_status_display bg_color=object.get_fault_status_color %}')
        urgency_index = template_text.index('{% badge object.get_urgency_display bg_color=object.get_urgency_color %}')

        self.assertLess(fault_number_index, fault_category_index)
        self.assertLess(fault_category_index, fault_status_index)
        self.assertLess(fault_status_index, urgency_index)


if __name__ == "__main__":
    unittest.main()

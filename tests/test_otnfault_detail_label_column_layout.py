import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"


class OtnFaultDetailLabelColumnLayoutSourceTestCase(unittest.TestCase):
    def test_basic_info_table_keeps_label_column_stable_for_long_content(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn('<table class="table table-hover attr-table" style="table-layout: fixed; width: 100%;">', template_text)
        self.assertIn('<colgroup>', template_text)
        self.assertIn('<col style="width: 10rem;">', template_text)
        self.assertIn('<col>', template_text)
        self.assertIn('<span style="white-space: nowrap; word-break: keep-all;">故障编号</span>', template_text)
        self.assertIn('<span style="white-space: nowrap; word-break: keep-all;">故障详情和处理过程</span>', template_text)
        self.assertIn('style="overflow-wrap: break-word; word-break: break-word;"', template_text)


if __name__ == "__main__":
    unittest.main()

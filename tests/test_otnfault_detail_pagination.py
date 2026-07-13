import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"

class OtnFaultDetailPaginationTestCase(unittest.TestCase):
    def test_otnfault_template_pagination_rules(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        # 1. 验证是否隐藏了默认的 django_tables2 分页
        self.assertIn('.impacts-table-container ul.pagination,', template_text)
        self.assertIn('.site-faults-table-container ul.pagination {', template_text)
        self.assertIn('display: none !important;', template_text)

        # 2. 验证影响业务列表的分页组件和参数
        self.assertIn('{% if impacts_table.page %}', template_text)
        self.assertIn('aria-label="影响业务分页"', template_text)
        self.assertIn('impacts_page={{ impacts_table.page.previous_page_number }}', template_text)
        self.assertIn('impacts_page={{ num }}', template_text)
        self.assertIn('per_page={{ per_page }}', template_text)

        # 3. 验证站点历史故障的分页组件、参数和锚点
        self.assertIn('{% if site_faults_table.page %}', template_text)
        self.assertIn('aria-label="站点历史故障分页"', template_text)
        self.assertIn('site_page={{ site_faults_table.page.previous_page_number }}', template_text)
        self.assertIn('site_page={{ num }}', template_text)
        self.assertIn('#site-history', template_text)

    def test_otnfault_views_pagination_handling(self) -> None:
        views_text = VIEWS_PATH.read_text(encoding="utf-8-sig")

        # 验证后端处理了 impacts_page 和 site_page 分页
        self.assertIn("request.GET.get('impacts_page', 1)", views_text)
        self.assertIn("request.GET.get('site_page', 1)", views_text)
        self.assertIn("table.paginate(page=impacts_page, per_page=per_page)", views_text)
        self.assertIn("site_faults_table.paginate(page=site_page, per_page=per_page)", views_text)

if __name__ == "__main__":
    unittest.main()

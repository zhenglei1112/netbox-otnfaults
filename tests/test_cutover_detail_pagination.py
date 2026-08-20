import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "cutovertask.html"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"

class CutoverTaskDetailPaginationTestCase(unittest.TestCase):
    def test_cutover_template_pagination_rules(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        # 1. 验证样式通过 NetBox 支持的 head 块加载并隐藏默认分页
        self.assertIn('{% block head %}', template_text)
        self.assertIn('{{ block.super }}', template_text)
        self.assertNotIn('{% block extra_styles %}', template_text)
        self.assertIn('.impacts-table-container ul.pagination,', template_text)
        self.assertIn('.impacts-table-container .pagination {', template_text)
        self.assertIn('display: none !important;', template_text)

        # 2. 验证影响业务列表的分页组件和参数
        self.assertIn('{% if impacts_table.page %}', template_text)
        self.assertIn('page={{ impacts_table.page.previous_page_number }}', template_text)
        self.assertIn('page={{ num }}', template_text)
        self.assertIn('per_page={{ per_page }}', template_text)

    def test_cutover_views_pagination_handling(self) -> None:
        views_text = VIEWS_PATH.read_text(encoding="utf-8-sig")

        # 验证后端处理了割接分页
        self.assertIn("request.GET.get('page', request.GET.get('impact-page', 1))", views_text)
        self.assertIn("impacts_table.paginate(page=impacts_page, per_page=per_page)", views_text)

if __name__ == "__main__":
    unittest.main()

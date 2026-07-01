import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"
CSS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "statistics_dashboard.css"


class StatisticsBareFiberInterruptionTestCase(unittest.TestCase):
    def test_backend_contains_bare_fiber_interruption_logic(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("def _compute_bare_fiber_interruption_overview(", source)
        self.assertIn("service_type=ServiceTypeChoices.BARE_FIBER", source)
        self.assertIn("otn_fault__is_suspended=False", source)
        self.assertIn("business_impact == BusinessImpactChoices.NOT_INTERRUPTED", source)
        self.assertIn("fault.interruption_reason == 'cable_rectification'", source)
        self.assertIn("fault.interruption_reason_detail == 'planned_reporting'", source)
        self.assertIn("coordination_status == 'approved'", source)
        self.assertIn("distinct_fault_ids = {imp.otn_fault_id for imp in filtered_impacts if imp.otn_fault_id}", source)
        self.assertIn("bare_fiber_interruption = _compute_bare_fiber_interruption_overview(", source)
        self.assertIn("'bare_fiber_interruption': bare_fiber_interruption", source)
        self.assertIn("'prev_bare_fiber_interruption': prev_bare_fiber_interruption", source)

    def test_template_contains_bare_fiber_interruption_section(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("statistics-barefiber-overview", template)
        self.assertIn("裸纤业务中断情况", template)
        self.assertIn('id="barefiber-total-count"', template)
        self.assertIn('id="barefiber-distinct-count"', template)
        self.assertIn('id="barefiber-total-duration"', template)
        self.assertIn('id="barefiber-distinct-duration"', template)
        self.assertIn("statistics-barefiber-grid", template)

    def test_css_defines_bare_fiber_grid_style(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".statistics-barefiber-grid", css)
        self.assertIn("grid-template-columns: repeat(4, minmax(0, 1fr)) !important;", css)
        self.assertIn("@media (max-width: 991.98px)", css)
        self.assertIn("@media (max-width: 575.98px)", css)

    def test_js_renders_bare_fiber_interruption_data(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("let currentBareFiberInterruption = null;", source)
        self.assertIn("let currentPrevBareFiberInterruption = null;", source)
        self.assertIn("function renderBareFiberInterruption(overview, prevOverview, yoyOverview, idPrefix = 'barefiber')", source)
        self.assertIn("document.getElementById(`${idPrefix}-total-count`)", source)
        self.assertIn("document.getElementById(`${idPrefix}-distinct-count`)", source)
        self.assertIn("document.getElementById(`${idPrefix}-total-duration`)", source)
        self.assertIn("document.getElementById(`${idPrefix}-distinct-duration`)", source)
        self.assertIn("renderBareFiberInterruption(data.bare_fiber_interruption, data.prev_bare_fiber_interruption, data.yoy_bare_fiber_interruption);", source)
        self.assertIn("renderBareFiberInterruption(currentBareFiberInterruption, currentPrevBareFiberInterruption || {}, currentYoyBareFiberInterruption || {});", source)

    def test_bare_fiber_fault_detail_columns(self) -> None:
        import re
        source_views = VIEWS_PATH.read_text(encoding="utf-8")
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        source_js = JS_PATH.read_text(encoding="utf-8")

        # 校验后端 API 查询及返回字段
        self.assertIn("'otn_fault__province'", source_views)
        self.assertIn("'fault_province':", source_views)
        self.assertIn("'fault_reason_level1':", source_views)
        self.assertIn("'fault_reason_level2':", source_views)

        # 校验模板表头和 colspan，且“分类”必须在“故障省份”之后，且在“一级原因”之前
        self.assertIn("<th>故障省份</th>", template)
        self.assertIn("<th>一级原因</th>", template)
        self.assertIn("<th>二级原因</th>", template)
        self.assertIn('<td colspan="11" class="text-center text-muted py-4">数据加载中...</td>', template)
        self.assertTrue(re.search(r"<th>故障省份</th>\s*<th>分类</th>\s*<th>一级原因</th>\s*<th>二级原因</th>", template))

        # 校验 JS 渲染
        self.assertIn("tbodyId === 'service-details-tbody' ? 11 : 8", source_js)
        self.assertIn("item.fault_province", source_js)
        self.assertIn("item.fault_reason_level1", source_js)
        self.assertIn("item.fault_reason_level2", source_js)
        
        # 校验渲染时的列顺序
        js_row_pattern = r"<td>\$\{escapeHtml\(item\.fault_province\s*\|\|\s*'-'\)\}<\/td>\s*<td>\$\{escapeHtml\(item\.fault_category\s*\|\|\s*'-'\)\}<\/td>\s*<td>\$\{escapeHtml\(item\.fault_reason_level1\s*\|\|\s*'-'\)\}<\/td>\s*<td>\$\{escapeHtml\(item\.fault_reason_level2\s*\|\|\s*'-'\)\}<\/td>"
        self.assertTrue(re.search(js_row_pattern, source_js))


if __name__ == "__main__":
    unittest.main()

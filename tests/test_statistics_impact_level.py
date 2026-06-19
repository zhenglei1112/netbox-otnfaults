import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
SERIALIZERS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "serializers.py"
STATISTICS_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
DASHBOARD_HTML_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
DASHBOARD_JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _class_block(source: str, class_name: str) -> str:
    start = source.index(f"class {class_name}(")
    next_class = source.find("\nclass ", start + 1)
    return source[start:] if next_class == -1 else source[start:next_class]

class StatisticsImpactLevelTestCase(unittest.TestCase):

    def test_new_fields_in_models(self) -> None:
        source = _read(MODELS_PATH)
        # 校验新判定字段的添加
        self.assertIn("ac_fault_is_class_i = models.BooleanField", source)
        self.assertIn("device_fault_is_class_i = models.BooleanField", source)
        self.assertIn("is_important = models.BooleanField", source)

    def test_fields_in_forms(self) -> None:
        source = _read(FORMS_PATH)
        self.assertIn("ac_fault_is_class_i", source)
        self.assertIn("device_fault_is_class_i", source)
        self.assertIn("is_important", source)

    def test_tables_rules(self) -> None:
        source = _read(TABLES_PATH)
        class_source = _class_block(source, "CircuitServiceTable")
        self.assertIn("is_important = tables.BooleanColumn", class_source)
        
        # 确保 actions 永远保持为最后一列，且 is_important 在它前面
        normalized_source = class_source.replace(" ", "").replace("\n", "").replace("\r", "").replace('"', "'")
        self.assertTrue(normalized_source.index("'is_important'") < normalized_source.index("'actions'"))
        self.assertIn(".keys(),'actions'", normalized_source)

    def test_filtersets_and_serializers(self) -> None:
        filter_source = _read(FILTERSETS_PATH)
        self.assertIn("ac_fault_is_class_i", filter_source)
        self.assertIn("device_fault_is_class_i", filter_source)
        self.assertIn("is_important", filter_source)

        serializers_source = _read(SERIALIZERS_PATH)
        self.assertIn("ac_fault_is_class_i", serializers_source)
        self.assertIn("device_fault_is_class_i", serializers_source)
        self.assertIn("is_important", serializers_source)

    def test_backend_aggregates_and_filters(self) -> None:
        views_source = _read(STATISTICS_VIEWS_PATH)
        # 校验 Q_CLASS 宏的定义与过滤
        self.assertIn("Q_CLASS_I = ", views_source)
        self.assertIn("Q_CLASS_II = ", views_source)
        self.assertIn("Q_CLASS_III = ", views_source)
        self.assertIn("Q_CLASS_IV = ", views_source)
        self.assertIn("Q_CLASS_V = ", views_source)
        self.assertIn("Q_CLASS_TOTAL = ", views_source)
        
        # 校验 FaultStatisticsDetailsAPI 中对 impact_level 参数的下钻过滤
        self.assertIn("impact_level = request.GET.get('impact_level')", views_source)
        self.assertIn("impact_filters: dict[str, Q] = {", views_source)
        self.assertIn("'class_i': Q_CLASS_I", views_source)
        self.assertIn("queryset = queryset.filter(impact_filters[impact_level])", views_source)

    def test_frontend_dashboard_and_js(self) -> None:
        html_source = _read(DASHBOARD_HTML_PATH)
        # 校验 8 个等级指标卡片
        self.assertIn('id="kpi-level-total"', html_source)
        self.assertIn('id="kpi-level-class-i-ii"', html_source)
        self.assertIn('id="kpi-level-class-i"', html_source)
        self.assertIn('id="kpi-level-class-ii"', html_source)
        self.assertIn('id="kpi-level-class-iii"', html_source)
        self.assertRegex(
            html_source,
            r'class="impact-level-block-item statistics-drill-metric"[^>]+data-filter-value="class_iii"',
        )
        self.assertIn('id="kpi-level-class-iv"', html_source)
        self.assertIn('id="kpi-level-class-v"', html_source)
        self.assertIn('id="card-cutover-implemented"', html_source)
        self.assertIn("<th>故障等级</th>", html_source)
        
        # 校验 3 个等级占比环形图 DOM ID
        self.assertIn('id="chart-ring-fiber"', html_source)
        self.assertIn('id="chart-ring-power"', html_source)
        self.assertIn('id="chart-ring-environment"', html_source)

        js_source = _read(DASHBOARD_JS_PATH)
        # 校验前端数据填充和事件绑定
        self.assertIn("renderImpactLevelOverview", js_source)
        self.assertIn("card-cutover-implemented", js_source)
        self.assertIn("impact_level", js_source)
        self.assertIn("getImpactLevelBadge", js_source)
        
        # 校验前端环形图初始化与渲染函数
        self.assertIn("chartRingFiber", js_source)
        self.assertIn("chartRingPower", js_source)
        self.assertIn("chartRingEnvironment", js_source)
        self.assertIn("renderRingCharts", js_source)

    def test_ring_charts_support_sector_and_center_drill_down(self) -> None:
        js_source = _read(DASHBOARD_JS_PATH)
        views_source = _read(STATISTICS_VIEWS_PATH)

        self.assertIn("function handleImpactRingSectorClick(params, faultGroup)", js_source)
        self.assertIn("function handleImpactRingCenterClick(chart, faultGroup, event)", js_source)
        self.assertIn("chartRingFiber.on('click', params => handleImpactRingSectorClick(params, 'fiber'));", js_source)
        self.assertIn("chartRingPower.on('click', params => handleImpactRingSectorClick(params, 'power'));", js_source)
        self.assertIn("chartRingEnvironment.on('click', params => handleImpactRingSectorClick(params, 'environment'));", js_source)
        self.assertIn("handleImpactRingCenterClick(chartRingFiber, 'fiber', event)", js_source)
        self.assertIn("handleImpactRingCenterClick(chartRingPower, 'power', event)", js_source)
        self.assertIn("handleImpactRingCenterClick(chartRingEnvironment, 'environment', event)", js_source)
        self.assertIn("'I类': 'class_i'", js_source)
        self.assertIn("'II类': 'class_ii'", js_source)
        self.assertIn("'III类': 'class_iii'", js_source)
        self.assertIn("'挂起': 'class_v'", js_source)
        self.assertIn("activeFilterField = 'fault_group';", js_source)
        self.assertIn("activeFilterExtraField = impactLevel ? 'impact_level' : null;", js_source)

        self.assertIn("fault_group = request.GET.get('fault_group')", views_source)
        self.assertIn("if fault_group == 'fiber':", views_source)
        self.assertIn("elif fault_group == 'power':", views_source)
        self.assertIn("elif fault_group == 'environment':", views_source)
        self.assertIn("FaultCategoryChoices.AC_FAULT,", views_source)
        self.assertIn("FaultCategoryChoices.DEVICE_FAULT,", views_source)

if __name__ == "__main__":
    unittest.main()

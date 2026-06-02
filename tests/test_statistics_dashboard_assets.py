import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
LOCAL_ECHARTS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "lib" / "echarts.min.js"
CSS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "statistics_dashboard.css"
JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"


class StatisticsDashboardAssetsTestCase(unittest.TestCase):
    def test_statistics_dashboard_uses_local_echarts_before_dashboard_script(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        local_echarts = "{% static 'netbox_otnfaults/lib/echarts.min.js' %}"
        dashboard_script = "{% static 'netbox_otnfaults/js/statistics_dashboard.js' %}"

        self.assertNotIn("cdn.jsdelivr.net/npm/echarts", template)
        self.assertIn(local_echarts, template)
        self.assertIn(dashboard_script, template)
        self.assertLess(template.index(local_echarts), template.index(dashboard_script))
        self.assertTrue(LOCAL_ECHARTS_PATH.exists())

    def test_statistics_dashboard_loads_bumped_theme_assets(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("statistics_dashboard.css' %}?v=33", template)
        self.assertIn("statistics_dashboard.js' %}?v=39", template)

    def test_statistics_dashboard_css_covers_light_and_dark_theme_surfaces(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("--statistics-surface", css)
        self.assertIn('[data-bs-theme="dark"] .page-statistics', css)
        self.assertIn(".page-statistics .filter-controls .form-control", css)
        self.assertIn(".page-statistics .text-dark", css)
        self.assertIn(".page-statistics .table", css)

    def test_statistics_dashboard_reserves_scrollbar_space_for_modal_opening(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertRegex(css, r"html\s*\{[^}]*scrollbar-gutter:\s*stable;")
        self.assertRegex(css, r"body\.modal-open\s*\{[^}]*overflow-y:\s*scroll\s*!important;")
        self.assertRegex(css, r"body\.modal-open\s*\{[^}]*padding-right:\s*0\s*!important;")

    def test_statistics_dashboard_filter_controls_group_period_controls_with_smaller_gap(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".statistics-period-control-group {", css)
        filter_controls_block = css.split(".filter-controls {", 1)[1].split("}", 1)[0]
        period_controls_block = css.split(".statistics-period-control-group {", 1)[1].split("}", 1)[0]

        self.assertIn("statistics-period-control-group", template)
        self.assertIn("gap: 0.75rem;", filter_controls_block)
        self.assertIn("gap: 0.25rem;", period_controls_block)
        self.assertNotIn('id="filterType" class="form-select mx-2"', template)
        self.assertNotIn('id="filterDate" class="form-control mx-2"', template)

    def test_statistics_dashboard_period_select_has_stable_width(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn('id="filterType" class="form-select statistics-period-type-select"', template)
        self.assertNotIn('id="filterType" class="form-select" style="width: auto;"', template)
        self.assertIn(".statistics-period-type-select,", css)
        self.assertIn(".statistics-period-control-group .ts-wrapper", css)
        self.assertIn("width: 8.5rem !important;", css)
        self.assertIn("flex: 0 0 8.5rem;", css)

    def test_statistics_dashboard_period_select_has_stable_tomselect_height(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".statistics-period-control-group .ts-control", css)
        self.assertIn("height: 2.75rem;", css)
        self.assertIn("min-height: 2.75rem;", css)
        self.assertIn("flex-wrap: nowrap;", css)
        self.assertIn(".statistics-period-control-group .ts-control > input", css)
        self.assertIn("min-width: 1px !important;", css)
        self.assertIn("width: 1px !important;", css)

    def test_statistics_dashboard_js_uses_theme_aware_chart_options(self) -> None:
        script = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("function getChartTheme()", script)
        self.assertIn("buildTooltipTheme(chartTheme)", script)
        self.assertIn("buildAxisTheme(chartTheme", script)
        self.assertIn("buildLegendTheme(chartTheme)", script)
        self.assertIn("new MutationObserver(refreshChartsForTheme)", script)

    def test_statistics_dashboard_chart_grid_lines_are_not_dashed(self) -> None:
        script = JS_PATH.read_text(encoding="utf-8")

        split_line_fragments = [
            fragment.split("}", 1)[0]
            for fragment in script.split("splitLine:")[1:]
        ]

        self.assertGreater(len(split_line_fragments), 0)
        for fragment in split_line_fragments:
            self.assertNotIn("type: 'dashed'", fragment)

    def test_statistics_dashboard_exposes_metric_explanation_modal(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn('id="statistics-metric-help-btn"', template)
        self.assertIn('data-bs-target="#statisticsMetricHelpModal"', template)
        self.assertIn('id="statisticsMetricHelpModal"', template)
        self.assertIn('class="modal-dialog modal-xl modal-dialog-scrollable"', template)
        self.assertIn("指标说明", template)
        self.assertIn("统计周期", template)
        self.assertIn("不纳入总体故障总数", template)
        self.assertIn("挂起的故障显示未关闭的挂起故障数量，括号内为系统内总挂起故障数量，不随当前统计周期变化", template)
        self.assertIn("分类统计仅展示起数", template)
        self.assertIn("每日中断图固定展示当前自然年内未挂起光缆中断", template)
        self.assertIn("中断时长箱线图跟随当前统计周期", template)
        self.assertIn("光缆中断统计仅包含故障类型为“光缆中断”且未挂起的物理故障", template)
        self.assertIn("长时故障", template)
        self.assertIn("历时大于 0.5 小时", template)
        self.assertIn("P50修复时长", template)
        self.assertIn("P90修复时长", template)
        self.assertIn("超时率", template)
        self.assertIn("历时大于等于 4 小时", template)
        self.assertIn("同一 A 端站点与任一 Z 端站点", template)
        self.assertIn("光缆属性指标卡按汇总口径展示", template)
        self.assertIn("光缆属性分布图按原始资源属性展示", template)
        self.assertIn("业务卡片展示年度累计、本期间、运行月历和近六个月中断日历", template)
        self.assertIn("年度累计按所选年份统计 SLA、中断时长和中断起数", template)
        self.assertIn("运行月历按所选年份逐月展示故障数与故障时长", template)
        self.assertIn("裸纤业务和电路业务均仅统计影响为“中断”的故障影响记录", template)
        self.assertIn("裸纤业务不再限定故障类型为“光缆中断”", template)
        self.assertIn("电路业务同样不再限定故障类型为“光缆中断”", template)
        self.assertIn("本期间按故障分类汇总故障总数和故障时长，分类明细仅显示非零项", template)
        self.assertIn("SLA 按两位小数向下截取展示", template)
        self.assertIn("运行月历的 SLA 单元格只显示数字，不显示百分号", template)
        self.assertIn("中断日历默认展示近六个月，可展开查看所选年份截至当前月份", template)
        self.assertIn("SLA", template)
        self.assertIn("合并重叠不可用时段", template)
        self.assertNotIn("本期间按故障分类全量列示故障总数和故障时长", template)
        self.assertNotIn("平均时长为累计时长除以影响次数", template)
        self.assertNotIn("业务长时故障指单次业务影响历时大于等于 6 小时", template)
        self.assertNotIn("业务重复故障指同一业务相邻两次影响时间间隔不超过 60 天", template)

    def test_statistics_metric_help_modal_uses_compact_card_layout(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("statistics-metric-help-modal", template)
        self.assertIn("statistics-metric-help-grid", template)
        self.assertEqual(template.count('class="statistics-metric-help-card"'), 4)
        self.assertIn("statistics-metric-help-card-title", template)
        self.assertIn("statistics-metric-help-footer", template)
        self.assertIn("statistics-metric-help-confirm", template)

        self.assertIn(".statistics-metric-help-modal .modal-content", css)
        self.assertIn(".statistics-metric-help-grid", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", css)
        self.assertIn(".statistics-metric-help-card-title", css)
        self.assertIn(".statistics-metric-help-confirm", css)
        self.assertIn("background: #008a7a;", css)
        self.assertIn("background: var(--statistics-surface, #ffffff);", css)
        self.assertIn("border: 1px solid var(--statistics-border, #d7dee8);", css)

    def test_statistics_dashboard_exposes_content_fullscreen_control(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")
        script = JS_PATH.read_text(encoding="utf-8")

        self.assertIn('id="statistics-fullscreen-btn"', template)
        self.assertIn('aria-label="最大化故障统计页面"', template)
        self.assertIn('mdi-fullscreen', template)
        self.assertIn(".page-statistics:fullscreen", css)
        self.assertIn(".page-statistics.is-statistics-fullscreen", css)
        self.assertIn("const btnStatisticsFullscreen = document.getElementById('statistics-fullscreen-btn');", script)
        self.assertIn("statisticsPage.requestFullscreen()", script)
        self.assertIn("document.exitFullscreen()", script)
        self.assertIn("document.addEventListener('fullscreenchange', syncStatisticsFullscreenState);", script)
        self.assertIn("setTimeout(resizeStatisticsCharts, 150);", script)

    def test_statistics_dashboard_fullscreen_keeps_period_header_visible(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".page-statistics:fullscreen header", css)
        self.assertIn(".page-statistics.is-statistics-fullscreen header", css)
        fullscreen_header_block = css.split(".page-statistics:fullscreen header", 1)[1].split("}", 1)[0]
        self.assertIn("position: sticky;", fullscreen_header_block)
        self.assertIn("top: 0;", fullscreen_header_block)
        self.assertIn("z-index: 30;", fullscreen_header_block)
        self.assertIn(".page-statistics:fullscreen #statisticsTab", css)
        self.assertIn(".page-statistics.is-statistics-fullscreen #statisticsTab", css)
        fullscreen_tab_block = css.split(".page-statistics:fullscreen #statisticsTab", 1)[1].split("}", 1)[0]
        self.assertIn("padding-top: 0.25rem;", fullscreen_tab_block)

    def test_statistics_dashboard_does_not_render_parent_fullscreen_period_overlay(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")
        script = JS_PATH.read_text(encoding="utf-8")

        self.assertNotIn('id="statistics-fullscreen-period-display"', template)
        self.assertNotIn(".statistics-fullscreen-period-display", css)
        self.assertNotIn("fullscreenPeriodDisplay", script)
        self.assertNotIn("syncFullscreenPeriodDisplay", script)


if __name__ == "__main__":
    unittest.main()

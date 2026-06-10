import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"
CSS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "statistics_dashboard.css"


class StatisticsBranchCompanyTestCase(unittest.TestCase):
    def test_backend_builds_branch_company_payload_for_fixed_six_provinces(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("BRANCH_PROVINCE_NAMES: list[str] = ['浙江', '山东', '内蒙', '陕西', '四川', '江西']", source)
        self.assertIn("'江西': 3545.0", source)
        self.assertIn("'浙江': 2804.0", source)
        self.assertIn("'陕西': 2182.0", source)
        self.assertIn("'山东': 1464.0", source)
        self.assertIn("'四川': 985.0", source)
        self.assertIn("'内蒙': 972.0", source)
        self.assertIn("def _normalize_branch_province_name(name: str | None) -> str | None:", source)
        self.assertIn("def _build_branch_company_statistics(", source)
        self.assertIn("calendar_year: int | None = None", source)
        self.assertIn("calendar_month: int | None = None", source)
        self.assertIn("path_lengths = BRANCH_PROVINCE_PATH_LENGTHS.copy()", source)
        self.assertNotIn("def _build_branch_company_path_lengths() -> dict[str, float]:", source)
        self.assertNotIn("OtnPath.objects.select_related('site_a__region', 'site_z__region')", source)
        self.assertIn("branch_company_stats = _build_branch_company_statistics(", source)
        self.assertIn("'branch_company': branch_company_stats", source)
        self.assertIn("prev_branch_company_stats = {}", source)
        self.assertIn("'prev_branch_company': prev_branch_company_stats", source)

    def test_backend_branch_company_payload_contains_all_chart_datasets(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")
        branch_source = source.split("def _build_branch_company_statistics(", 1)[1].split("\n\n\ndef _parse_time_range", 1)[0]

        for province in ("浙江", "山东", "内蒙", "陕西", "四川", "江西"):
            self.assertIn(province, source)

        for key in (
            "'overview'",
            "'cable_break_overview'",
            "'province_bars'",
            "'duration_boxplot'",
            "'valid_duration_bars'",
            "'weekly_trends'",
            "'monthly_trends'",
            "'path_lengths'",
            "'per_1000km'",
        ):
            self.assertIn(key, branch_source)

        self.assertIn("'count_per_1000km'", branch_source)
        self.assertIn("'count': count", branch_source)
        self.assertIn("'duration_per_1000km'", branch_source)
        self.assertIn("valid_duration_avg = valid_duration / valid_count if valid_count > 0 else 0.0", branch_source)
        self.assertIn("'valid_duration': round(valid_duration_avg, 2)", branch_source)
        self.assertIn("'valid_duration_total': round(valid_duration, 2)", branch_source)
        self.assertIn("'valid_count': valid_count", branch_source)
        self.assertIn("'valid_duration_per_1000km'", branch_source)
        self.assertIn("'week_count_per_1000km'", branch_source)
        self.assertIn("'week_duration_per_1000km'", branch_source)
        self.assertIn("'week_valid_duration_per_1000km'", branch_source)
        self.assertIn("monthly_by_province = {", branch_source)
        self.assertIn("'month_count_per_1000km'", branch_source)
        self.assertIn("'month_duration_per_1000km'", branch_source)
        self.assertIn("'month_valid_duration_per_1000km'", branch_source)
        self.assertIn("selected_calendar_year = calendar_year or selected_year", branch_source)
        self.assertIn("selected_calendar_month = calendar_month or timezone.localtime(start_date).month", branch_source)
        self.assertIn("calendar_months = _build_recent_calendar_months(selected_calendar_year, selected_calendar_month, tz)", branch_source)
        self.assertIn("_calculate_boxplot_values(province_samples[province])", branch_source)
        self.assertIn("branch_cable_break_overview['repeat_faults_count']", branch_source)
        self.assertIn("'performance_cards'", branch_source)

    def test_backend_branch_company_payload_contains_performance_cards(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("BRANCH_PERFORMANCE_DEDUCTION_LABELS: dict[str, str]", source)
        self.assertIn("def _classify_branch_fault_responsibility(fault) -> dict[str, object]:", source)
        self.assertIn("def _calculate_branch_performance_score(metrics: dict[str, float]) -> dict[str, object]:", source)
        self.assertIn("def _build_branch_company_performance_cards(", source)
        self.assertIn("performance_cards = _build_branch_company_performance_cards(", source)
        self.assertIn("'performance_cards': performance_cards", source)

        performance_source = source.split("def _build_branch_company_performance_cards(", 1)[1].split("\n\n\ndef _build_branch_company_statistics", 1)[0]
        for province in ("娴欐睙", "灞变笢", "鍐呰挋", "闄曡タ", "鍥涘窛", "姹熻タ"):
            self.assertIn("for province in BRANCH_PROVINCE_NAMES:", performance_source)
        for key in (
            "'responsibility_score'",
            "'overall_score'",
            "'grade'",
            "'status'",
            "'deductions'",
            "'responsibility_metrics'",
            "'overall_metrics'",
            "'responsibility_reason_top3'",
            "'overall_reason_top3'",
            "'weekly_trend'",
            "'responsibility_basis'",
            "'monthly_stats'",
            "'interrupt_calendar'",
            "'interrupt_calendar_full'",
        ):
            self.assertIn(key, performance_source)

    def test_backend_branch_company_score_uses_double_scope_and_deductions(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")
        score_source = source.split("def _calculate_branch_performance_score(", 1)[1].split("\n\n\ndef _build_branch_company_performance_cards", 1)[0]
        classify_source = source.split("def _classify_branch_fault_responsibility(", 1)[1].split("\n\n\ndef _calculate_branch_performance_score", 1)[0]
        performance_source = source.split("def _build_branch_company_performance_cards(", 1)[1].split("\n\n\ndef _build_branch_company_statistics", 1)[0]

        for key in (
            "'frequency'",
            "'duration'",
            "'valid_duration'",
            "'severity'",
            "'repeat'",
            "'trend'",
        ):
            self.assertIn(key, score_source)
        self.assertIn("max(0.0, round(100.0 - total_deduction, 2))", score_source)
        self.assertIn("ResourceTypeChoices.LEASED", classify_source)
        self.assertIn("fault.interruption_reason == 'natural_disaster'", classify_source)
        self.assertIn("fault.interruption_reason_detail == 'planned_reporting'", classify_source)
        self.assertIn("responsibility_reason_counts: dict[str, float]", performance_source)
        self.assertIn("responsibility_reason_counts[reason] = responsibility_reason_counts.get(reason, 0.0) + weight", performance_source)

    def test_template_places_branch_company_tab_after_circuit_service(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        circuit_index = template.index('id="tab-circuit-service-btn"')
        branch_index = template.index('id="tab-branch-company-btn"')
        performance_index = template.index('id="tab-branch-performance-btn"')
        self.assertLess(circuit_index, branch_index)
        self.assertLess(branch_index, performance_index)
        self.assertIn('data-bs-target="#tab-branch-company"', template)
        self.assertIn('data-bs-target="#tab-branch-performance"', template)
        self.assertIn('子公司（省份）故障', template)
        self.assertIn('子公司绩效评分', template)
        self.assertIn('id="branch-company-overall-total"', template)
        self.assertIn('id="branch-company-cable-break-total-count"', template)
        self.assertIn('id="branch-company-kpi-repeat-faults"', template)
        self.assertIn('data-filter-label="重复起数"', template)
        self.assertIn('id="chart-branch-company-count"', template)
        self.assertIn('id="chart-branch-company-duration"', template)
        self.assertIn('id="chart-branch-company-boxplot"', template)
        self.assertIn('id="chart-branch-company-valid-duration"', template)
        self.assertIn('id="chart-branch-company-weekly"', template)
        self.assertIn('id="chart-branch-company-monthly"', template)
        self.assertIn('年初至今月趋势', template)
        self.assertIn('id="branch-company-drill-down-filter-badge"', template)
        self.assertIn('id="branch-company-btn-clear-filter"', template)
        self.assertIn('id="branch-company-filtered-kpi-summary"', template)
        self.assertIn('id="branch-company-details-tbody"', template)
        self.assertIn('id="branch-company-performance-cards"', template)
        branch_tab = template.split('id="tab-branch-company"', 1)[1].split('id="tab-branch-performance"', 1)[0]
        performance_tab = template.split('id="tab-branch-performance"', 1)[1]
        self.assertNotIn('id="branch-company-performance-cards"', branch_tab)
        self.assertIn('id="branch-company-performance-cards"', performance_tab)

    def test_template_exposes_branch_company_metric_switches(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        for group_name in (
            "branchCompanyCountMetric",
            "branchCompanyDurationMetric",
            "branchCompanyWeeklyMetric",
            "branchCompanyWeeklyScale",
        ):
            self.assertIn(f'name="{group_name}"', template)
        boxplot_header = template.split('id="chart-branch-company-boxplot"', 1)[0].split('中断时长箱线图', 1)[-1]
        self.assertNotIn('name="branchCompanyBoxplotMetric"', boxplot_header)
        self.assertNotIn('id="branch-company-boxplot-normalized"', boxplot_header)
        self.assertNotIn('千公里平均', boxplot_header)
        valid_chart_header = template.split('id="chart-branch-company-valid-duration"', 1)[0].split('有效平均历时', 1)[-1]
        self.assertNotIn('name="branchCompanyValidMetric"', valid_chart_header)
        self.assertNotIn('id="branch-company-valid-normalized"', valid_chart_header)
        self.assertNotIn('千公里平均', valid_chart_header)

    def test_dashboard_script_renders_branch_company_charts(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("const chartBranchCompanyCountElement = document.getElementById('chart-branch-company-count');", source)
        self.assertIn("let chartBranchCompanyCount = chartBranchCompanyCountElement ? echarts.init(chartBranchCompanyCountElement) : null;", source)
        self.assertIn("let currentPrevBranchCompanyData = null;", source)
        self.assertIn("function renderBranchCompanySection(branchData, prevBranchData = currentPrevBranchCompanyData)", source)
        self.assertIn("function renderBranchCompanyPerformanceCards(cards)", source)
        self.assertIn("renderBranchCompanyPerformanceCards(branchData.performance_cards || []);", source)
        self.assertIn("function renderBranchCompanyPerformanceCard(card)", source)
        self.assertIn("function formatBranchPerformanceDeductionValue(value)", source)
        self.assertIn("function handleBranchCompanyPerformanceCardClick(card)", source)
        self.assertIn("function handleBranchCompanyPerformanceDeductionClick(card, deduction)", source)
        self.assertIn("branch-performance-company-icon", source)
        self.assertIn("mdi-office-building", source)
        self.assertIn("branch-performance-score-total", source)
        self.assertNotIn("branch-performance-score-denominator", source)
        self.assertNotIn("/100", source)
        self.assertIn("branch-performance-grade-pill", source)
        self.assertIn("mdi-medal", source)
        self.assertIn("branch-performance-metric-icon", source)
        self.assertIn("branch-performance-deduction-icon", source)
        self.assertIn("branch-performance-impact-line", source)
        self.assertIn("mdi-pulse", source)
        self.assertIn("function renderBranchPerformanceRuntimeCalendar(card)", source)
        self.assertIn("branch-performance-runtime-calendar", source)
        self.assertIn("branch-performance-runtime-calendar-chart", source)
        self.assertIn("function initBranchPerformanceRuntimeCalendarCharts(container, cardsByProvince)", source)
        self.assertIn("function renderBranchPerformanceInterruptCalendar(card, interruptCalendarMaxCount)", source)
        self.assertIn("branch-performance-interrupt-calendar", source)
        self.assertIn("initBranchPerformanceInterruptCalendarToggles(container)", source)
        self.assertIn("${renderBranchPerformanceRuntimeCalendar(card)}", source)
        self.assertIn("${renderBranchPerformanceInterruptCalendar(card, card.interruptCalendarMaxCount)}", source)
        performance_card_source = source.split("function renderBranchCompanyPerformanceCard(card)", 1)[1].split("function renderBranchCompanyPerformanceCards", 1)[0]
        self.assertNotIn("renderServiceRuntimeCalendarSlaTable", performance_card_source)
        self.assertNotIn("service-runtime-calendar-sla-grid", performance_card_source)
        self.assertIn("<span>责任得分 ${formatBranchPerformanceValue(card.responsibility_score || 0)}</span>", source)
        self.assertNotIn("责任得分 <strong>${formatBranchPerformanceValue(card.responsibility_score || 0)}</strong>", source)
        self.assertIn("<span>全量得分 ${formatBranchPerformanceValue(card.overall_score || 0)}</span>", source)
        self.assertIn("branch-company-performance-cards", source)
        self.assertIn("branch-performance-score-value", source)
        self.assertIn("branch-performance-deduction", source)
        self.assertIn("branch-performance-deduction-heading", source)
        self.assertIn("责任扣分", source)
        self.assertIn("全量影响", source)
        self.assertNotIn("<strong>-${formatBranchPerformanceValue(item.value || 0)}</strong>", source)
        self.assertIn("function renderBranchCompanyOverview(branchData, prevBranchData = currentPrevBranchCompanyData)", source)
        self.assertIn("renderTrendBesideMetric(totalEl, overview.total_count || 0, prevOverview.total_count, true);", source)
        self.assertIn("renderTrendBesideMetric(cableBreakTotalEl, cableBreak.total_count || 0, prevCableBreak.total_count, true);", source)
        self.assertIn("const repeatEl = document.getElementById('branch-company-kpi-repeat-faults');", source)
        self.assertIn("renderTrendBesideMetric(repeatEl, cableBreak.repeat_faults_count || 0, prevCableBreak.repeat_faults_count, true);", source)
        self.assertIn("id: 'branch-company-timeout-rate'", source)
        self.assertIn("function renderBranchCompanyBarCharts(branchData)", source)
        self.assertIn("function renderBranchCompanyBoxplot(branchData)", source)
        self.assertIn("function renderBranchCompanyValidDurationChart(branchData)", source)
        self.assertIn("function renderBranchCompanyWeeklyChart(branchData)", source)
        self.assertIn("const chartBranchCompanyMonthlyElement = document.getElementById('chart-branch-company-monthly');", source)
        self.assertIn("let chartBranchCompanyMonthly = chartBranchCompanyMonthlyElement ? echarts.init(chartBranchCompanyMonthlyElement) : null;", source)
        self.assertIn("if (chartBranchCompanyMonthly) chartBranchCompanyMonthly.resize();", source)
        self.assertIn("renderBranchCompanyMonthlyChart(branchData);", source)
        self.assertIn("function renderBranchCompanyMonthlyChart(branchData)", source)
        self.assertIn("const monthlyData = branchData.monthly_trends || {};", source)
        self.assertIn("month_count_per_1000km", source)
        self.assertIn("month_duration_per_1000km", source)
        self.assertIn("month_valid_duration_per_1000km", source)
        self.assertIn("type: 'bar'", source)
        self.assertIn("function syncBranchCompanyWeeklyScaleAvailability()", source)
        self.assertIn("weeklyScaleNormalized.disabled = isValidDuration;", source)
        self.assertIn("if (isValidDuration && weeklyScaleNormalized.checked)", source)
        self.assertIn("weeklyScaleRaw.checked = true;", source)
        self.assertIn("function getBranchCompanyProvinceColor(name, chartTheme)", source)
        self.assertIn("'浙江': '#4E79A7'", source)
        self.assertIn("'山东': '#F28E2B'", source)
        self.assertIn("'内蒙': '#59A14F'", source)
        self.assertIn("'陕西': '#B07AA1'", source)
        self.assertIn("'四川': '#EDC948'", source)
        self.assertIn("'江西': '#9C755F'", source)
        self.assertIn("itemStyle: { color: getBranchCompanyProvinceColor(item.name, chartTheme), borderRadius: [4, 4, 0, 0] }", source)
        self.assertIn("const lineColor = getBranchCompanyProvinceColor(item.name, chartTheme);", source)
        self.assertIn("itemStyle: { color: lineColor },", source)
        self.assertIn("lineStyle: { width: 2, color: lineColor },", source)
        self.assertIn("function formatBranchCompanyWeekMonthTick(value, index, labels)", source)
        self.assertIn("'一月', '二月', '三月', '四月', '五月', '六月'", source)
        self.assertIn("boundaryGap: false,", source)
        self.assertIn("formatter: (value, index) => formatBranchCompanyWeekMonthTick(value, index, labels)", source)
        self.assertNotIn("interval: Math.max(0, Math.floor(labels.length / 12))", source)
        self.assertIn("function buildBranchCompanyGrid(isWeekly = false)", source)
        self.assertIn("const selectedDateParts = inputDate.value.split('-').map(Number);", source)
        self.assertIn("&calendar_year=${selectedDateParts[0]}&calendar_month=${selectedDateParts[1]}", source)
        self.assertIn("top: isWeekly ? 76 : 52", source)
        self.assertIn("function buildBranchCompanyYAxis(unit, chartTheme)", source)
        self.assertIn("nameGap: 16", source)
        self.assertIn("nameTextStyle", source)
        boxplot_chart_source = source.split("function renderBranchCompanyBoxplot(branchData)", 1)[1].split("function renderBranchCompanyValidDurationChart", 1)[0]
        self.assertIn("const metric = 'duration';", boxplot_chart_source)
        self.assertIn("value: item.value || [],", boxplot_chart_source)
        self.assertIn("yAxis: buildBranchCompanyYAxis('小时', chartTheme)", boxplot_chart_source)
        self.assertNotIn("getCheckedValue('branchCompanyBoxplotMetric'", boxplot_chart_source)
        self.assertNotIn("per_1000km", boxplot_chart_source)
        self.assertIn("tooltipFormatter = null", source)
        self.assertIn("_validDurationTotal: item.valid_duration_total || 0", source)
        self.assertIn("_validCount: item.valid_count || 0", source)
        valid_chart_source = source.split("function renderBranchCompanyValidDurationChart(branchData)", 1)[1].split("function renderBranchCompanyWeeklyChart(branchData)", 1)[0]
        self.assertIn("const metric = 'valid_duration';", valid_chart_source)
        self.assertNotIn("getCheckedValue('branchCompanyValidMetric'", valid_chart_source)
        self.assertNotIn("valid_duration_per_1000km", valid_chart_source)
        self.assertNotIn("千公里有效平均历时", valid_chart_source)
        self.assertIn("function renderBranchCompanyDetailsTable()", source)
        self.assertIn("function handleBranchCompanyChartClick(params, fieldName)", source)
        self.assertIn("function handleBranchCompanyMetricFilterClick(metric)", source)
        self.assertIn("currentBranchCompanyDetails = currentAllDetails.filter", source)
        self.assertIn("branchCompanyProvinceSet.has(item.province)", source)
        self.assertIn("chartBranchCompanyCount.on('click', params => handleBranchCompanyChartClick(params, 'province'));", source)
        self.assertIn("branch-company-details-tbody", source)
        self.assertIn("有效平均历时", source)
        self.assertIn("currentPrevBranchCompanyData = data.prev_branch_company || null;", source)
        self.assertIn("renderBranchCompanySection(data.branch_company, data.prev_branch_company);", source)
        self.assertIn("if (chartBranchCompanyCount) chartBranchCompanyCount.resize();", source)
        self.assertIn("renderBranchCompanySection(currentBranchCompanyData, currentPrevBranchCompanyData);", source)
        self.assertIn("activeTab.id === 'tab-branch-company-btn'", source)
        self.assertIn("activeTab.id === 'tab-branch-performance-btn'", source)
        self.assertIn("event.target.id === 'tab-branch-performance-btn'", source)

    def test_backend_filters_out_specific_maintenance_companies_in_branch_statistics(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("EXCLUDED_HANDLING_UNITS: set[str] = {", source)
        self.assertIn("'山东瑞阳云技术有限公司'", source)
        self.assertIn("'嘉兴广信信息科技有限公司'", source)
        self.assertIn("'杭州骏云科技有限公司'", source)
        self.assertIn("'上海信智通网络技术有限公司'", source)

        self.assertIn("def _should_exclude_for_branch(fault) -> bool:", source)
        self.assertIn("fault.handling_unit.name in EXCLUDED_HANDLING_UNITS", source)

        branch_stats_source = source.split("def _build_branch_company_statistics(", 1)[1].split("\n\n\ndef _parse_time_range", 1)[0]
        self.assertIn("not _should_exclude_for_branch(fault)", branch_stats_source)

    def test_css_defines_branch_company_chart_layout(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".statistics-branch-performance-section", css)
        self.assertIn(".statistics-branch-performance-grid", css)
        self.assertIn(".statistics-branch-performance-card", css)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", css)
        self.assertIn("@media (max-width: 1199.98px)", css)
        self.assertIn(".branch-performance-card-top", css)
        self.assertIn(".branch-performance-company-icon", css)
        self.assertIn(".branch-performance-score-total", css)
        self.assertNotIn(".branch-performance-score-denominator", css)
        self.assertIn(".branch-performance-grade-pill", css)
        self.assertIn(".branch-performance-score-subline", css)
        self.assertIn(".statistics-branch-performance-card--good .branch-performance-score-total", css)
        self.assertIn(".statistics-branch-performance-card--stable .branch-performance-score-total", css)
        self.assertIn(".statistics-branch-performance-card--warning .branch-performance-score-total", css)
        self.assertIn(".statistics-branch-performance-card--danger .branch-performance-score-total", css)
        self.assertIn(".branch-performance-metric-icon", css)
        self.assertIn("flex-direction: row;", css)
        self.assertIn("justify-content: center;", css)
        self.assertIn("text-align: left;", css)
        self.assertIn(".branch-performance-metric--orange", css)
        self.assertIn(".branch-performance-deduction-icon", css)
        self.assertIn(".branch-performance-reasons-panel", css)
        self.assertIn(".branch-performance-impact-line", css)
        self.assertIn(".branch-performance-runtime-calendar", css)
        self.assertIn(".branch-performance-runtime-calendar-chart", css)
        self.assertIn(".branch-performance-interrupt-calendar", css)
        self.assertIn("font-weight: 400;", css)
        self.assertIn("color: #667085;", css)
        self.assertIn(".branch-performance-score-value", css)
        self.assertIn(".branch-performance-deduction", css)
        self.assertIn(".statistics-branch-company-chart-grid", css)
        self.assertIn(".statistics-branch-company-chart", css)
        self.assertIn(".statistics-branch-company-weekly-chart", css)
        self.assertIn(".statistics-branch-company-monthly-chart", css)


if __name__ == "__main__":
    unittest.main()

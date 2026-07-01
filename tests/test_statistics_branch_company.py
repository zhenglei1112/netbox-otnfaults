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
            "'bare_fiber_interruption'",
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
        self.assertIn("branch_bare_fiber_interruption = _compute_bare_fiber_interruption_overview(", branch_source)
        self.assertIn("branch_company_scope=True", branch_source)
        self.assertIn("'performance_cards'", branch_source)

    def test_backend_bare_fiber_interruption_supports_branch_company_scope(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")
        compute_source = source.split("def _compute_bare_fiber_interruption_overview(", 1)[1].split("\n\n\ndef _build_physical_province_chart_stats", 1)[0]

        self.assertIn("branch_company_scope: bool = False", compute_source)
        self.assertIn("if branch_company_scope:", compute_source)
        self.assertIn("_branch_province_for_fault(fault) not in BRANCH_PROVINCE_NAMES", compute_source)
        self.assertIn("_should_exclude_for_branch(fault)", compute_source)

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
            "'annual_stats'",
        ):
            self.assertIn(key, performance_source)
        self.assertIn("'count_per_1000km': _per_1000km(", performance_source)
        self.assertIn("'duration_per_1000km': _per_1000km(", performance_source)
        self.assertIn("def _build_branch_performance_bare_fiber_annual_stats(", source)
        self.assertIn("year_all_faults = [", source)
        self.assertIn("PowerFaultImpactChoices.HOSTED", source)
        self.assertIn("'bare_fiber': bare_fiber_annual_stats.get(province", performance_source)
        self.assertIn("'cable_break': {", performance_source)
        self.assertIn("'power': {", performance_source)
        self.assertIn("'hosted_count': power_hosted_count", performance_source)
        self.assertIn("cards.sort(key=lambda card: card['annual_stats']['cable_break']['count_per_1000km'], reverse=True)", performance_source)

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
        self.assertIn('子公司绩效', template)
        self.assertNotIn('子公司绩效评分', template)
        self.assertIn('<span>子公司绩效</span>', template)
        self.assertNotIn('<span>六省绩效考核</span>', template)
        self.assertIn('name="branchPerformanceRuntimeScale"', template)
        self.assertIn('id="branch-performance-runtime-scale-normalized"', template)
        self.assertIn('value="per_1000km" autocomplete="off" checked', template)
        self.assertIn('id="branch-performance-runtime-scale-raw"', template)
        self.assertIn('id="branch-company-overall-total"', template)
        self.assertIn('id="branch-company-cable-break-total-count"', template)
        self.assertIn('id="branch-company-kpi-repeat-faults"', template)
        self.assertIn('id="branch-barefiber-total-count"', template)
        self.assertIn('id="branch-barefiber-distinct-count"', template)
        self.assertIn('id="branch-barefiber-total-duration"', template)
        self.assertIn('id="branch-barefiber-distinct-duration"', template)
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
        self.assertIn('name="branchCompanyDetailSortMode"', template)
        self.assertIn('id="branch-company-detail-sort-time"', template)
        self.assertIn('id="branch-company-detail-sort-repeat"', template)
        self.assertIn('for="branch-company-detail-sort-time">按时间排序</label>', template)
        self.assertIn('for="branch-company-detail-sort-repeat">按重复排序</label>', template)
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
        self.assertIn("function renderBranchCompanySection(branchData, prevBranchData = currentPrevBranchCompanyData, yoyBranchData = currentYoyBranchCompanyData)", source)
        self.assertIn("function renderBranchCompanyPerformanceCards(cards)", source)
        self.assertIn("renderBranchCompanyPerformanceCards(branchData.performance_cards || []);", source)
        self.assertIn("function renderBranchCompanyPerformanceCard(card)", source)
        self.assertIn("function renderBranchPerformanceAnnualStats(card)", source)
        self.assertIn("function renderBranchPerformanceMetricItem(label, value, unit = '', emphasized = false)", source)
        self.assertIn("const annualYear = (card.annual_stats && card.annual_stats.year) || new Date().getFullYear();", source)
        self.assertIn("年度累计（${annualYear}年）", source)
        self.assertIn("service-annual-summary-value--emphasis", source)
        self.assertIn("service-annual-summary-value", source)
        annual_stats_source = source.split("function renderBranchPerformanceAnnualStats(card)", 1)[1].split("function renderBranchPerformanceRuntimeCalendar", 1)[0]
        annual_section_source = source.split("function renderBranchPerformanceAnnualSection(", 1)[1].split("function renderBranchPerformanceAnnualStats", 1)[0]
        performance_card_source = source.split("function renderBranchCompanyPerformanceCard(card)", 1)[1].split("function renderBranchCompanyPerformanceCards", 1)[0]
        self.assertNotIn("annualYear = new Date().getFullYear()", annual_section_source)
        self.assertNotIn("年度累计（${annualYear}年）", annual_section_source)
        self.assertNotIn("service-annual-header", annual_stats_source)
        self.assertNotIn("年度累计（${annualYear}年）", annual_stats_source)
        self.assertEqual(performance_card_source.count("年度累计（${annualYear}年）"), 1)
        self.assertIn("branch-performance-title-name", performance_card_source)
        self.assertIn("branch-performance-title-annual", performance_card_source)
        self.assertIn("branch-performance-title-annual-icon", performance_card_source)
        self.assertIn("mdi-calendar-range-outline", performance_card_source)
        self.assertEqual(annual_stats_source.count(", true)"), 6)
        self.assertIn("branch-performance-annual-stats", source)
        self.assertIn("branch-performance-annual-section", source)
        self.assertIn("branch-performance-annual-grid", source)
        self.assertIn("annual.bare_fiber", source)
        self.assertIn("annual.cable_break", source)
        self.assertIn("annual.power", source)
        self.assertIn("function formatBranchPerformanceDeductionValue(value)", source)
        self.assertIn("function handleBranchCompanyPerformanceCardClick(card)", source)
        self.assertIn("function handleBranchCompanyPerformanceDeductionClick(card, deduction)", source)
        self.assertNotIn("branch-performance-score-denominator", source)
        self.assertNotIn("/100", source)
        self.assertIn("function renderBranchPerformanceRuntimeCalendar(card)", source)
        self.assertIn("branch-performance-runtime-calendar", source)
        self.assertIn("branch-performance-runtime-calendar-chart", source)
        self.assertIn("service-runtime-calendar branch-performance-runtime-calendar", source)
        self.assertIn("service-runtime-calendar-heading", source)
        self.assertIn("service-runtime-calendar-chart branch-performance-runtime-calendar-chart", source)
        self.assertIn("function initBranchPerformanceRuntimeCalendarCharts(container, cardsByProvince)", source)
        self.assertIn("const branchPerformanceRuntimeScaleInputs = Array.from(document.querySelectorAll('input[name=\"branchPerformanceRuntimeScale\"]'));", source)
        self.assertIn("branchPerformanceRuntimeScaleInputs.forEach(input => input.addEventListener('change'", source)
        self.assertIn("function getBranchPerformanceRuntimeScale()", source)
        self.assertIn("const runtimeScale = getBranchPerformanceRuntimeScale();", source)
        self.assertIn("runtimeScale === 'per_1000km'", source)
        self.assertIn("monthlyStats[index].count_per_1000km", source)
        self.assertIn("monthlyStats[index].duration_per_1000km", source)
        runtime_chart_source = source.split("function initBranchPerformanceRuntimeCalendarCharts(container, cardsByProvince)", 1)[1].split("function initBranchPerformanceInterruptCalendarToggles", 1)[0]
        runtime_bar_source = runtime_chart_source.split("type: 'bar'", 1)[1]
        self.assertIn("const countAxisUnit = runtimeScale === 'per_1000km' ? '次/千公里' : '次';", runtime_chart_source)
        self.assertIn("name: countAxisUnit", runtime_chart_source)
        count_axis_source = runtime_chart_source.split("name: countAxisUnit", 1)[1].split("minInterval: 1", 1)[0]
        self.assertIn("nameLocation: 'middle'", count_axis_source)
        self.assertIn("nameRotate: 0", count_axis_source)
        self.assertNotIn("offset:", count_axis_source)
        self.assertNotIn("nameLocation: 'start'", count_axis_source)
        self.assertIn("padding: [78, 0, 0, 0]", count_axis_source)
        self.assertIn("return value > 0 ? formatCardMetricValue(value) : '';", runtime_bar_source)
        self.assertNotIn("${formatCardMetricValue(value)}${countUnit}", runtime_bar_source)
        self.assertIn("function renderBranchPerformanceInterruptCalendar(card, interruptCalendarMaxCount)", source)
        self.assertIn("branch-performance-interrupt-calendar", source)
        self.assertIn("initBranchPerformanceInterruptCalendarToggles(container)", source)
        self.assertIn("${renderBranchPerformanceRuntimeCalendar(card)}", source)
        self.assertIn("${renderBranchPerformanceInterruptCalendar(card, card.interruptCalendarMaxCount)}", source)
        self.assertIn("service-strip-card-title", performance_card_source)
        self.assertIn("${renderBranchPerformanceAnnualStats(card)}", performance_card_source)
        self.assertIn("${renderBranchPerformanceRuntimeCalendar(card)}", performance_card_source)
        self.assertIn("${renderBranchPerformanceInterruptCalendar(card, card.interruptCalendarMaxCount)}", performance_card_source)
        self.assertNotIn("responsibilityMetrics", performance_card_source)
        self.assertNotIn("overallMetrics", performance_card_source)
        self.assertNotIn("deductions", performance_card_source)
        self.assertNotIn("branch-performance-score-subline", performance_card_source)
        self.assertNotIn("branch-performance-score-panel", performance_card_source)
        self.assertNotIn("branch-performance-score-total", performance_card_source)
        self.assertNotIn("branch-performance-grade-pill", performance_card_source)
        self.assertNotIn("branch-performance-kpi-grid", performance_card_source)
        self.assertNotIn("branch-performance-impact-line", performance_card_source)
        self.assertNotIn("branch-performance-deduction", performance_card_source)
        self.assertNotIn("branch-performance-reasons", performance_card_source)
        self.assertNotIn("renderBranchPerformanceReasonList", performance_card_source)
        self.assertNotIn("renderServiceRuntimeCalendarSlaTable", performance_card_source)
        self.assertNotIn("service-runtime-calendar-sla-grid", performance_card_source)
        self.assertIn("branch-company-performance-cards", source)
        self.assertIn("function renderBranchCompanyOverview(branchData, prevBranchData = currentPrevBranchCompanyData, yoyBranchData = currentYoyBranchCompanyData)", source)
        self.assertIn("const bareFiber = branchData.bare_fiber_interruption || {};", source)
        self.assertIn("const prevBareFiber = (prevBranchData && prevBranchData.bare_fiber_interruption) || {};", source)
        self.assertIn("renderBareFiberInterruption(bareFiber, prevBareFiber, yoyBareFiber, 'branch-barefiber');", source)
        self.assertIn("function renderBareFiberInterruption(overview, prevOverview, yoyOverview, idPrefix = 'barefiber')", source)
        self.assertIn("document.getElementById(`${idPrefix}-total-count`)", source)
        self.assertIn("renderTrendBesideMetric(totalEl, overview.total_count || 0, prevOverview.total_count, yoyOverview.total_count, true);", source)
        self.assertIn("renderTrendBesideMetric(cableBreakTotalEl, cableBreak.total_count || 0, prevCableBreak.total_count, yoyCableBreak.total_count, true);", source)
        self.assertIn("const repeatEl = document.getElementById('branch-company-kpi-repeat-faults');", source)
        self.assertIn("renderTrendBesideMetric(repeatEl, cableBreak.repeat_faults_count || 0, prevCableBreak.repeat_faults_count, yoyCableBreak.repeat_faults_count, true);", source)
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
        self.assertIn("renderBranchCompanySection(currentBranchCompanyData, currentPrevBranchCompanyData, currentYoyBranchCompanyData);", source)
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

    def test_branch_company_details_filter_valid_duration_on_server(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")
        details_source = source.split(
            "class FaultStatisticsDetailsAPI",
            1,
        )[1].split(
            "class FaultRepeatsAPI",
            1,
        )[0]

        self.assertIn("is_valid_duration = request.GET.get('is_valid_duration')", details_source)
        self.assertIn("if is_valid_duration == 'true':", details_source)
        self.assertIn("Coalesce(F('fault_recovery_time'), now) - F('fault_occurrence_time')", details_source)
        self.assertIn("duration__gt=timedelta(minutes=30)", details_source)
        self.assertIn("currentBranchCompanyDetails = data.results || [];", JS_PATH.read_text(encoding="utf-8"))
        self.assertIn("filteredDetails = sortDetailRows(filteredDetails, sortMode);", JS_PATH.read_text(encoding="utf-8"))

    def test_branch_company_details_use_normalized_scope_instead_of_exact_region_names(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")
        details_source = source.split(
            "class FaultStatisticsDetailsAPI",
            1,
        )[1].split(
            "class FaultRepeatsAPI",
            1,
        )[0]

        self.assertIn(
            "current_faults = [fault for fault in current_faults if _is_branch_company_fault(fault)]",
            details_source,
        )
        self.assertIn(
            "preceding_faults = [fault for fault in preceding_faults if _is_branch_company_fault(fault)]",
            details_source,
        )
        self.assertNotIn(
            "queryset = queryset.filter(province__name__in=BRANCH_PROVINCE_NAMES)",
            details_source,
        )
    def test_css_defines_branch_company_chart_layout(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".statistics-branch-performance-section", css)
        self.assertIn(".statistics-branch-performance-grid", css)
        self.assertIn(".statistics-branch-performance-card", css)
        self.assertIn("grid-template-columns: repeat(auto-fill, minmax(21rem, 22.5rem));", css)
        self.assertIn("@media (max-width: 1199.98px)", css)
        self.assertNotIn(".branch-performance-card-top", css)
        self.assertNotIn(".branch-performance-company-icon", css)
        self.assertIn(".statistics-branch-performance-card .service-strip-card-title", css)
        self.assertIn(".statistics-branch-performance-card .branch-performance-title-name", css)
        self.assertIn(".statistics-branch-performance-card .branch-performance-title-annual", css)
        self.assertIn(".statistics-branch-performance-card .branch-performance-title-annual-icon", css)
        self.assertIn("color: rgba(255, 255, 255, 0.84)", css)
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
        self.assertIn(".statistics-branch-performance-card .service-runtime-calendar", css)
        self.assertIn(".service-runtime-calendar-chart", css)
        self.assertIn(".branch-performance-annual-stats", css)
        self.assertIn(".branch-performance-annual-section", css)
        self.assertIn(".service-annual-summary-grid", css)
        self.assertIn(".service-annual-summary-item", css)
        self.assertIn(".service-annual-summary-value--emphasis", css)
        self.assertIn("font-weight: 500;", css)
        self.assertIn("font-weight: 850;", css)
        self.assertIn(".statistics-branch-performance-card .service-interrupt-calendar", css)
        self.assertIn("font-weight: 400;", css)
        self.assertIn("color: #667085;", css)
        self.assertIn(".branch-performance-score-value", css)
        self.assertIn(".branch-performance-deduction", css)
        self.assertIn(".statistics-branch-company-chart-grid", css)
        self.assertIn(".statistics-branch-company-chart", css)
        self.assertIn(".statistics-branch-company-weekly-chart", css)
        self.assertIn(".statistics-branch-company-monthly-chart", css)

    def test_branch_performance_card_css_reuses_service_card_system(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertNotIn("grid-templat/*", css)
        performance_grid_source = css.split(".statistics-branch-performance-grid {", 1)[1].split("}", 1)[0]
        self.assertNotIn("grid-template-columns: repeat(6, minmax(0, 1fr))", performance_grid_source)
        self.assertNotIn("grid-template-columns: repeat(3, minmax(0, 1fr))", performance_grid_source)
        self.assertIn("grid-template-columns: repeat(auto-fill, minmax(21rem, 22.5rem));", performance_grid_source)
        self.assertIn(".statistics-branch-performance-grid {\n    display: grid;\n    grid-template-columns: repeat(auto-fill, minmax(21rem, 22.5rem));", css)
        self.assertIn(".statistics-branch-performance-card.service-strip-card", css)
        self.assertIn(".statistics-branch-performance-card .service-strip-card-title", css)
        self.assertIn(".statistics-branch-performance-card .service-runtime-calendar", css)
        self.assertIn(".statistics-branch-performance-card .service-interrupt-calendar", css)
        self.assertIn(".branch-performance-annual-section--bare-fiber .service-annual-summary-grid", css)
        self.assertIn(".branch-performance-annual-section--cable-break .service-annual-summary-grid", css)
        self.assertIn(".branch-performance-annual-section--power .service-annual-summary-grid", css)


if __name__ == "__main__":
    unittest.main()

/**
 * 故障统计交互脚本
 */
document.addEventListener("DOMContentLoaded", function() {
    // ---------------- 图表实例初始化 ----------------
    let chartResource = echarts.init(document.getElementById('chart-resource'));
    let chartProvince = echarts.init(document.getElementById('chart-province'));
    let chartReason = echarts.init(document.getElementById('chart-reason'));
    let chartRingFiber = echarts.init(document.getElementById('chart-ring-fiber'));
    let chartRingPower = echarts.init(document.getElementById('chart-ring-power'));
    let chartRingEnvironment = echarts.init(document.getElementById('chart-ring-environment'));
    const chartHistogramElement = document.getElementById('chart-cable-break-histogram');
    let chartHistogram = chartHistogramElement ? echarts.init(chartHistogramElement) : null;
    const chartPhysicalDailyElement = document.getElementById('chart-physical-daily-faults');
    let chartPhysicalDaily = chartPhysicalDailyElement ? echarts.init(chartPhysicalDailyElement) : null;
    const chartPhysicalDurationBoxplotElement = document.getElementById('chart-physical-duration-boxplot');
    let chartPhysicalDurationBoxplot = chartPhysicalDurationBoxplotElement ? echarts.init(chartPhysicalDurationBoxplotElement) : null;
    const chartBranchCompanyCountElement = document.getElementById('chart-branch-company-count');
    let chartBranchCompanyCount = chartBranchCompanyCountElement ? echarts.init(chartBranchCompanyCountElement) : null;
    const chartBranchCompanyDurationElement = document.getElementById('chart-branch-company-duration');
    let chartBranchCompanyDuration = chartBranchCompanyDurationElement ? echarts.init(chartBranchCompanyDurationElement) : null;
    const chartBranchCompanyBoxplotElement = document.getElementById('chart-branch-company-boxplot');
    let chartBranchCompanyBoxplot = chartBranchCompanyBoxplotElement ? echarts.init(chartBranchCompanyBoxplotElement) : null;
    const chartBranchCompanyValidDurationElement = document.getElementById('chart-branch-company-valid-duration');
    let chartBranchCompanyValidDuration = chartBranchCompanyValidDurationElement ? echarts.init(chartBranchCompanyValidDurationElement) : null;
    const chartBranchCompanyWeeklyElement = document.getElementById('chart-branch-company-weekly');
    let chartBranchCompanyWeekly = chartBranchCompanyWeeklyElement ? echarts.init(chartBranchCompanyWeeklyElement) : null;
    const chartBranchCompanyMonthlyElement = document.getElementById('chart-branch-company-monthly');
    let chartBranchCompanyMonthly = chartBranchCompanyMonthlyElement ? echarts.init(chartBranchCompanyMonthlyElement) : null;
    const physicalDailyMetricInputs = Array.from(document.querySelectorAll('input[name="physicalDailyMetric"]'));
    const physicalDailyGranularityInputs = Array.from(document.querySelectorAll('input[name="physicalDailyGranularity"]'));
    const branchPerformanceRuntimeScaleInputs = Array.from(document.querySelectorAll('input[name="branchPerformanceRuntimeScale"]'));
    const branchCompanyMetricInputs = Array.from(document.querySelectorAll(
        'input[name="branchCompanyCountMetric"], input[name="branchCompanyDurationMetric"], input[name="branchCompanyWeeklyMetric"], input[name="branchCompanyWeeklyScale"]'
    ));
    const physicalBoxplotFilterShort = document.getElementById('physical-boxplot-filter-short');
    const physicalBoxplotFilterRectification = document.getElementById('physical-boxplot-filter-rectification');
    const physicalBoxplotLogScale = document.getElementById('physical-boxplot-log-scale');
    const cableBreakMetricsToggle = document.getElementById('cable-break-metrics-toggle');
    const cableBreakDeferredMetrics = document.getElementById('cable-break-deferred-metrics');
    const statisticsPage = document.querySelector('.page-statistics');
    const btnStatisticsFullscreen = document.getElementById('statistics-fullscreen-btn');
    

    const metricReasonInputs = Array.from(document.querySelectorAll('input[name="metricReason"]'));
    const metricResourceInputs = Array.from(document.querySelectorAll('input[name="metricResource"]'));
    const metricProvinceInputs = Array.from(document.querySelectorAll('input[name="metricProvince"]'));

    let currentMetricReason = 'count';
    let currentMetricResource = 'count';
    let currentMetricProvince = 'count';

    metricReasonInputs.forEach(input => input.addEventListener('change', (e) => {
        currentMetricReason = e.target.value;
        if (currentChartsData) renderCharts(currentChartsData);
    }));
    metricResourceInputs.forEach(input => input.addEventListener('change', (e) => {
        currentMetricResource = e.target.value;
        if (currentChartsData) renderCharts(currentChartsData);
    }));
    metricProvinceInputs.forEach(input => input.addEventListener('change', (e) => {
        currentMetricProvince = e.target.value;
        if (currentChartsData) renderCharts(currentChartsData);
    }));

    const detailSortModeInputs = Array.from(document.querySelectorAll('input[name="detailSortMode"]'));
    detailSortModeInputs.forEach(input => input.addEventListener('change', () => {
        renderDetailsTable();
    }));
    const branchCompanyDetailSortModeInputs = Array.from(document.querySelectorAll('input[name="branchCompanyDetailSortMode"]'));
    branchCompanyDetailSortModeInputs.forEach(input => input.addEventListener('change', () => {
        renderBranchCompanyDetailsTable();
    }));

    let excludedCategories = {
        resource_type: new Set(),
        province: new Set(),
        reason: new Set()
    };

    function updateExcludedSet(field, selectedObj) {
        excludedCategories[field].clear();
        for (let key in selectedObj) {
            if (!selectedObj[key]) {
                excludedCategories[field].add(key);
            }
        }
    }

    function resizeStatisticsCharts() {
        chartResource.resize();
        chartProvince.resize();
        chartReason.resize();
        chartRingFiber.resize();
        chartRingPower.resize();
        chartRingEnvironment.resize();
        if (chartHistogram) chartHistogram.resize();
        if (chartPhysicalDaily) chartPhysicalDaily.resize();
        if (chartPhysicalDurationBoxplot) chartPhysicalDurationBoxplot.resize();
        if (chartBranchCompanyCount) chartBranchCompanyCount.resize();
        if (chartBranchCompanyDuration) chartBranchCompanyDuration.resize();
        if (chartBranchCompanyBoxplot) chartBranchCompanyBoxplot.resize();
        if (chartBranchCompanyValidDuration) chartBranchCompanyValidDuration.resize();
        if (chartBranchCompanyWeekly) chartBranchCompanyWeekly.resize();
        if (chartBranchCompanyMonthly) chartBranchCompanyMonthly.resize();
        resizeBranchPerformanceCalendarCharts();
        resizeServiceCalendarCharts();
    }

    function isStatisticsFullscreen() {
        return document.fullscreenElement === statisticsPage;
    }

    function syncStatisticsFullscreenState() {
        const active = isStatisticsFullscreen();
        if (statisticsPage) {
            statisticsPage.classList.toggle('is-statistics-fullscreen', active);
        }
        if (btnStatisticsFullscreen) {
            const icon = btnStatisticsFullscreen.querySelector('.mdi');
            const label = active ? '退出故障统计全屏' : '最大化故障统计页面';
            btnStatisticsFullscreen.setAttribute('aria-pressed', active ? 'true' : 'false');
            btnStatisticsFullscreen.setAttribute('aria-label', label);
            btnStatisticsFullscreen.setAttribute('title', label);
            if (icon) {
                icon.classList.toggle('mdi-fullscreen', !active);
                icon.classList.toggle('mdi-fullscreen-exit', active);
            }
        }
        setTimeout(resizeStatisticsCharts, 150);
    }

    function toggleStatisticsFullscreen() {
        if (!statisticsPage || !document.fullscreenEnabled) return;
        if (isStatisticsFullscreen()) {
            document.exitFullscreen();
            return;
        }
        statisticsPage.requestFullscreen().catch(() => {});
    }

    window.addEventListener('resize', resizeStatisticsCharts);
    document.addEventListener('fullscreenchange', syncStatisticsFullscreenState);
    if (btnStatisticsFullscreen) {
        btnStatisticsFullscreen.addEventListener('click', toggleStatisticsFullscreen);
    }

    // ---------------- 统一事件绑定 ----------------
    // 点击下钻
    chartResource.on('click', params => handleChartClick(params, 'resource_type'));
    chartProvince.on('click', params => handleChartClick(params, 'province'));
    chartReason.on('click', params => handleChartClick(params, 'reason'));
    if (chartHistogram) chartHistogram.on('click', params => handleChartClick(params, 'duration_histogram_bucket'));
    if (chartBranchCompanyCount) chartBranchCompanyCount.on('click', params => handleBranchCompanyChartClick(params, 'province'));
    if (chartBranchCompanyDuration) chartBranchCompanyDuration.on('click', params => handleBranchCompanyChartClick(params, 'province'));
    if (chartBranchCompanyBoxplot) chartBranchCompanyBoxplot.on('click', params => handleBranchCompanyChartClick(params, 'province'));
    if (chartBranchCompanyValidDuration) chartBranchCompanyValidDuration.on('click', params => handleBranchCompanyChartClick(params, 'province'));
    if (chartBranchCompanyWeekly) chartBranchCompanyWeekly.on('click', params => handleBranchCompanyChartClick({ name: params.seriesName }, 'province'));
    
    // 图例切换（过滤剔除）
    chartResource.on('legendselectchanged', params => { updateExcludedSet('resource_type', params.selected); renderDetailsTable(); });
    chartProvince.on('legendselectchanged', params => { updateExcludedSet('province', params.selected); renderDetailsTable(); });
    chartReason.on('legendselectchanged', params => { updateExcludedSet('reason', params.selected); renderDetailsTable(); });

    document.addEventListener('click', function(event) {
        const metric = event.target.closest('.statistics-drill-metric');
        if (!metric) return;
        if (metric.closest('#tab-branch-company')) {
            handleBranchCompanyMetricFilterClick(metric);
            return;
        }
        handleMetricFilterClick(metric);
    });

    let currentAllDetails = []; // 保存后端返回的全部详情数据
    let currentChartsData = null;
    let currentCableBreakOverview = null;
    let currentPrevCableBreakOverview = null;
    let currentBareFiberInterruption = null;
    let currentPrevBareFiberInterruption = null;
    let currentBranchCompanyData = null;
    let currentPrevBranchCompanyData = null;
    let currentBranchCompanyDetails = [];
    let branchCompanyProvinceSet = new Set();
    let activeFilterField = null; // 'resource_type', 'province', 'reason'
    let activeFilterValue = null;
    let activeFilterExtraField = null;
    let activeFilterExtraValue = null;
    let activeFilterLabel = null;
    let activeBranchCompanyFilterField = null;
    let activeBranchCompanyFilterValue = null;
    let activeBranchCompanyFilterExtraField = null;
    let activeBranchCompanyFilterExtraValue = null;
    let activeBranchCompanyFilterLabel = null;
    let branchPerformanceCalendarCharts = [];

    if (physicalBoxplotFilterShort) {
        physicalBoxplotFilterShort.addEventListener('change', () => renderPhysicalDurationBoxplot(currentChartsData && currentChartsData.physical_duration_boxplot, selFilterType.value));
    }
    if (physicalBoxplotFilterRectification) {
        physicalBoxplotFilterRectification.addEventListener('change', () => renderPhysicalDurationBoxplot(currentChartsData && currentChartsData.physical_duration_boxplot, selFilterType.value));
    }
    if (physicalBoxplotLogScale) {
        physicalBoxplotLogScale.addEventListener('change', () => renderPhysicalDurationBoxplot(currentChartsData && currentChartsData.physical_duration_boxplot, selFilterType.value));
    }
    physicalDailyMetricInputs.forEach(input => input.addEventListener('change', () => renderOverallDailyFaultChart(currentChartsData && currentChartsData.physical_daily)));
    physicalDailyGranularityInputs.forEach(input => input.addEventListener('change', () => renderOverallDailyFaultChart(currentChartsData && currentChartsData.physical_daily)));
    branchCompanyMetricInputs.forEach(input => input.addEventListener('change', () => {
        syncBranchCompanyWeeklyScaleAvailability();
        renderBranchCompanySection(currentBranchCompanyData, currentPrevBranchCompanyData);
    }));
    branchPerformanceRuntimeScaleInputs.forEach(input => input.addEventListener('change', () => {
        if (input.checked && currentBranchCompanyData) {
            renderBranchCompanyPerformanceCards(currentBranchCompanyData.performance_cards || []);
        }
    }));

    if (cableBreakMetricsToggle && cableBreakDeferredMetrics) {
        cableBreakMetricsToggle.addEventListener('click', () => {
            const expanded = cableBreakMetricsToggle.getAttribute('aria-expanded') !== 'true';
            cableBreakDeferredMetrics.classList.toggle('d-none', !expanded);
            cableBreakMetricsToggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
            cableBreakMetricsToggle.textContent = expanded
                ? cableBreakMetricsToggle.dataset.expandedLabel
                : cableBreakMetricsToggle.dataset.collapsedLabel;
        });
    }
    // ---------------- DOM 元素 ----------------
    const selFilterType = document.getElementById('filterType');
    const inputDate = document.getElementById('filterDate');
    const btnPrevPeriod = document.getElementById('btn-prev-period');
    const btnNextPeriod = document.getElementById('btn-next-period');
    const btnCableBreakMap = document.getElementById('statistics-cable-break-map-btn');
    const cableBreakMapModal = document.getElementById('statisticsCableBreakMapModal');
    const cableBreakMapCloseBtn = document.getElementById('statisticsCableBreakMapCloseBtn');
    const cableBreakMapIframe = document.getElementById('statistics-cable-break-map-iframe');
    const cableBreakMapLoading = document.getElementById('statistics-cable-break-map-loading');
    const cableBreakMapPeriod = document.getElementById('statistics-cable-break-map-period');
    const scopeToggle = document.getElementById('bare-fiber-service-card-scope-toggle');
    const physicalProvinceFilterGroup = document.getElementById('physical-province-filter-group');
    const physicalProvinceFilter = document.getElementById('physical-province-filter');
    const bareFiberServiceCardScopeInputs = Array.from(document.querySelectorAll('input[name="bareFiberServiceCardScope"]'));
    let cableBreakMapManualBackdrop = null;

    const badgeFilter = document.getElementById('drill-down-filter-badge');
    const btnClearFilter = document.getElementById('btn-clear-filter');

    function isDarkTheme() {
        return document.documentElement.getAttribute('data-bs-theme') === 'dark';
    }

    function getStatisticsPageStyle() {
        const page = document.querySelector('.page-statistics') || document.documentElement;
        return getComputedStyle(page);
    }

    function getCssColor(style, name, fallback) {
        const value = style.getPropertyValue(name).trim();
        return value || fallback;
    }

    function getChartTheme() {
        const style = getStatisticsPageStyle();
        const dark = isDarkTheme();
        return {
            dark,
            text: getCssColor(style, '--statistics-text', dark ? '#dce3ee' : '#182433'),
            muted: getCssColor(style, '--statistics-muted', dark ? '#aeb8c7' : '#667085'),
            heading: getCssColor(style, '--statistics-heading', dark ? '#f2f6fb' : '#111827'),
            border: getCssColor(style, '--statistics-border', dark ? '#3d4656' : '#d9dee7'),
            surface: getCssColor(style, '--statistics-surface', dark ? '#1f2632' : '#ffffff'),
            primary: getCssColor(style, '--statistics-primary', dark ? '#6ea8fe' : '#206bc4'),
            axisLine: dark ? '#4f5d73' : '#c8d0dc',
            tooltipBg: dark ? 'rgba(31, 38, 50, 0.96)' : 'rgba(255, 255, 255, 0.98)',
            tooltipBorder: dark ? '#4f5d73' : '#d9dee7',
            chartPalette: dark
                ? ['#6ea8fe', '#20c997', '#ffd43b', '#ff8787', '#b197fc', '#63e6be', '#adb5bd']
                : ['#206bc4', '#2fb344', '#f59f00', '#d63939', '#ae3ec9', '#0ca678', '#667085']
        };
    }

    function buildTooltipTheme(theme) {
        return {
            backgroundColor: theme.tooltipBg,
            borderColor: theme.tooltipBorder,
            textStyle: { color: theme.text },
            extraCssText: 'box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);'
        };
    }

    function buildAxisTheme(theme, axisLabelOverrides = {}) {
        return {
            axisLine: { lineStyle: { color: theme.axisLine } },
            axisTick: { lineStyle: { color: theme.axisLine } },
            axisLabel: Object.assign({ color: theme.muted }, axisLabelOverrides),
            nameTextStyle: { color: theme.muted },
            splitLine: { show: false }
        };
    }

    function buildLegendTheme(theme) {
        return {
            textStyle: { color: theme.muted },
            inactiveColor: theme.dark ? '#697386' : '#b8c0cc',
            pageIconColor: theme.muted,
            pageIconInactiveColor: theme.border,
            pageTextStyle: { color: theme.muted }
        };
    }

    function buildPhysicalDailyChartGrid() {
        return { top: 58, left: 64, right: 64, bottom: 36, containLabel: false };
    }

    function buildPieLabelTheme(theme) {
        return {
            color: theme.text,
            fontWeight: 600
        };
    }

    function refreshChartsForTheme() {
        if (currentCableBreakOverview) {
            renderCableBreakOverview(currentCableBreakOverview, currentPrevCableBreakOverview || {});
        }
        if (currentBareFiberInterruption) {
            renderBareFiberInterruption(currentBareFiberInterruption, currentPrevBareFiberInterruption || {});
        }
        if (currentChartsData) {
            renderCharts(currentChartsData);
            renderRingCharts(currentChartsData);
            renderOverallDailyFaultChart(currentChartsData.physical_daily);
            renderPhysicalDurationBoxplot(currentChartsData.physical_duration_boxplot, selFilterType.value);
        }
        if (currentBranchCompanyData) {
            renderBranchCompanySection(currentBranchCompanyData, currentPrevBranchCompanyData);
        }
    }

    const themeObserver = new MutationObserver(refreshChartsForTheme);
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-bs-theme'] });

    function setCableBreakMapLoading(visible) {
        if (!cableBreakMapLoading) return;
        cableBreakMapLoading.classList.toggle('d-none', !visible);
    }

    function openCableBreakMapModal() {
        if (!cableBreakMapModal || !cableBreakMapIframe || !window.STATISTICS_CABLE_BREAK_MAP_URL) return;
        refreshCableBreakMapFrame();
        showCableBreakMapModalFallback();
    }

    function refreshCableBreakMapFrame() {
        if (!cableBreakMapIframe || !window.STATISTICS_CABLE_BREAK_MAP_URL) return;
        setCableBreakMapLoading(true);
        if (cableBreakMapPeriod) {
            cableBreakMapPeriod.innerHTML = formatStatisticsPeriodLabel(selFilterType.value, inputDate.value, buildLocalPeriodForDate(selFilterType.value, inputDate.value));
            updatePeriodLabelState(cableBreakMapPeriod, buildLocalPeriodForDate(selFilterType.value, inputDate.value));
        }
        cableBreakMapIframe.src = `${window.STATISTICS_CABLE_BREAK_MAP_URL}?modal=true&${buildTimeParams()}${buildPhysicalProvinceParams()}`;
    }

    function closeCableBreakMapModal() {
        if (!cableBreakMapIframe) return;
        cableBreakMapIframe.src = 'about:blank';
        setCableBreakMapLoading(false);
        hideCableBreakMapModalFallback();
    }

    function showCableBreakMapModalFallback() {
        if (!cableBreakMapManualBackdrop) {
            cableBreakMapManualBackdrop = document.createElement('div');
            cableBreakMapManualBackdrop.className = 'modal-backdrop fade show';
            cableBreakMapManualBackdrop.style.opacity = '0.85';
            cableBreakMapManualBackdrop.addEventListener('click', closeCableBreakMapModal);
            document.body.appendChild(cableBreakMapManualBackdrop);
        }

        cableBreakMapModal.style.display = 'block';
        cableBreakMapModal.classList.add('show');
        cableBreakMapModal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('modal-open');
    }

    function hideCableBreakMapModalFallback() {
        if (!cableBreakMapModal) return;
        cableBreakMapModal.classList.remove('show');
        cableBreakMapModal.style.display = 'none';
        cableBreakMapModal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('modal-open');

        if (cableBreakMapManualBackdrop) {
            cableBreakMapManualBackdrop.remove();
            cableBreakMapManualBackdrop = null;
        }
    }

    if (btnCableBreakMap) {
        btnCableBreakMap.addEventListener('click', openCableBreakMapModal);
    }
    const cardCutover = document.getElementById('card-cutover-implemented');
    if (cardCutover) {
        cardCutover.addEventListener('click', function(e) {
            e.preventDefault();
            let url = '/plugins/netbox-otnfaults/cutovers/';
            const type = selFilterType.value;
            const dateVal = inputDate.value;
            const period = buildLocalPeriodForDate(type, dateVal);
            if (period && period.start) {
                url += `?planned_cutover_time_after=${period.start}T00:00:00`;
                if (period.end && period.end !== '当前') {
                    url += `&planned_cutover_time_before=${period.end}T23:59:59`;
                } else {
                    const today = new Date();
                    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
                    url += `&planned_cutover_time_before=${todayStr}T23:59:59`;
                }
            }
            const provinces = getSelectedPhysicalProvinces();
            if (provinces.length > 0) {
                provinces.forEach(p => {
                    url += `&province=${encodeURIComponent(p)}`;
                });
            }
            window.open(url, '_blank');
        });
    }
    if (cableBreakMapIframe) {
        cableBreakMapIframe.addEventListener('load', () => {
            if (cableBreakMapIframe.src !== 'about:blank') {
                setCableBreakMapLoading(false);
            }
        });
    }
    if (cableBreakMapCloseBtn) {
        cableBreakMapCloseBtn.addEventListener('click', closeCableBreakMapModal);
    }
    if (cableBreakMapModal) {
        cableBreakMapModal.addEventListener('click', function(event) {
            if (event.target === cableBreakMapModal) closeCableBreakMapModal();
        });
    }

    // ---------------- UI 联动逻辑 ----------------
    function updateDateSelectors() {
        inputDate.title = '选择日期后，将按当前统计类型取该日期所在的年、月或 ISO 周';
    }

    selFilterType.addEventListener('change', () => {
        updateDateSelectors();
        loadActiveTab();
    });
    
    [inputDate].forEach(el => {
        el.addEventListener('change', loadActiveTab);
    });

    btnPrevPeriod.addEventListener('click', () => shiftSelectedPeriod(-1));
    btnNextPeriod.addEventListener('click', () => shiftSelectedPeriod(1));

    // ---------------- 构建时间参数 URL ----------------
    function getIsoWeekParts(dateValue) {
        const parts = dateValue.split('-').map(Number);
        const date = new Date(parts[0], parts[1] - 1, parts[2]);
        const dayNumber = date.getDay() || 7;
        date.setDate(date.getDate() + 4 - dayNumber);
        const isoYear = date.getFullYear();
        const yearStart = new Date(isoYear, 0, 1);
        const isoWeek = Math.ceil((((date - yearStart) / 86400000) + 1) / 7);
        return { year: isoYear, week: isoWeek };
    }

    function parseDateValue(dateValue) {
        const parts = dateValue.split('-').map(Number);
        return new Date(parts[0], parts[1] - 1, parts[2]);
    }

    function getHalfYearPart(month) {
        return month <= 6 ? 1 : 2;
    }

    function getQuarterPart(month) {
        return Math.floor((month - 1) / 3) + 1;
    }

    function getHalfYearLabel(half) {
        return half === 1 ? '上半年' : '下半年';
    }

    function padDatePart(value) {
        return String(value).padStart(2, '0');
    }

    function formatDotDate(date) {
        return `${date.getFullYear()}.${padDatePart(date.getMonth() + 1)}.${padDatePart(date.getDate())}`;
    }

    function formatInputDate(date) {
        return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())}`;
    }

    function formatApiDate(dateValue) {
        const parts = dateValue.split('-');
        return `${parts[0]}.${parts[1]}.${parts[2]}`;
    }

    function formatPeriodStartDate(period, fallbackDate) {
        if (period && period.start) {
            return formatApiDate(period.start);
        }
        return formatDotDate(fallbackDate);
    }

    function formatPeriodEndDate(periodEnd, fallbackDate) {
        if (!periodEnd) {
            return formatDotDate(fallbackDate);
        }
        if (/^\d{4}-\d{2}-\d{2}$/.test(periodEnd)) {
            return formatApiDate(periodEnd);
        }
        return periodEnd;
    }

    function getIsoWeekRange(dateValue) {
        const date = parseDateValue(dateValue);
        const dayNumber = date.getDay() || 7;
        const weekStart = new Date(date);
        weekStart.setDate(date.getDate() - dayNumber + 1);
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + 6);
        return { weekStart, weekEnd };
    }

    function getMonthWeekOrdinal(weekStart, monthDate) {
        const firstDay = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
        const firstDayNumber = firstDay.getDay() || 7;
        const firstWeekStart = new Date(firstDay);
        firstWeekStart.setDate(firstDay.getDate() - firstDayNumber + 1);
        return Math.floor((weekStart - firstWeekStart) / (7 * 86400000)) + 1;
    }

    function getYearEndDate(date) {
        return new Date(date.getFullYear(), 11, 31);
    }

    function getHalfYearRange(date) {
        const year = date.getFullYear();
        const half = getHalfYearPart(date.getMonth() + 1);
        const startMonth = half === 1 ? 0 : 6;
        const endMonth = half === 1 ? 5 : 11;
        return {
            half,
            start: new Date(year, startMonth, 1),
            end: new Date(year, endMonth + 1, 0)
        };
    }

    function getQuarterRange(date) {
        const year = date.getFullYear();
        const quarter = getQuarterPart(date.getMonth() + 1);
        const startMonth = (quarter - 1) * 3;
        return {
            quarter,
            start: new Date(year, startMonth, 1),
            end: new Date(year, startMonth + 3, 0)
        };
    }

    function getMonthEndDate(date) {
        return new Date(date.getFullYear(), date.getMonth() + 1, 0);
    }

    function shiftPeriodDate(dateValue, type, direction) {
        const date = parseDateValue(dateValue);

        if (type === 'year') {
            date.setFullYear(date.getFullYear() + direction);
        }
        if (type === 'half') {
            date.setMonth(date.getMonth() + (direction * 6));
        }
        if (type === 'quarter') {
            date.setMonth(date.getMonth() + (direction * 3));
        }
        if (type === 'month') {
            date.setMonth(date.getMonth() + direction);
        }
        if (type === 'week') {
            date.setDate(date.getDate() + (direction * 7));
        }

        return formatInputDate(date);
    }

    function shiftSelectedPeriod(direction) {
        inputDate.value = shiftPeriodDate(inputDate.value, selFilterType.value, direction);
        loadActiveTab();
    }

    function buildLocalPeriodForDate(type, dateValue) {
        const date = parseDateValue(dateValue);
        const today = new Date();
        const todayLocal = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        let start = date;
        let end = date;

        if (type === 'year') {
            start = new Date(date.getFullYear(), 0, 1);
            end = getYearEndDate(date);
        } else if (type === 'half') {
            const range = getHalfYearRange(date);
            start = range.start;
            end = range.end;
        } else if (type === 'quarter') {
            const range = getQuarterRange(date);
            start = range.start;
            end = range.end;
        } else if (type === 'month') {
            start = new Date(date.getFullYear(), date.getMonth(), 1);
            end = getMonthEndDate(date);
        } else if (type === 'week') {
            const range = getIsoWeekRange(dateValue);
            start = range.weekStart;
            end = range.weekEnd;
        }

        return {
            start: formatInputDate(start),
            end: todayLocal >= start && todayLocal <= end ? '当前' : formatInputDate(end),
            is_future: start > todayLocal,
        };
    }

    function updatePeriodLabelState(periodEl, period) {
        periodEl.classList.remove('statistics-period-label--current');
        periodEl.classList.remove('statistics-period-label--future');
        if (period && period.end === '当前') {
            periodEl.classList.add('statistics-period-label--current');
        } else if (period && period.is_future) {
            periodEl.classList.add('statistics-period-label--future');
        }
    }

    function formatPeriodFlag(label) {
        return `<span class="statistics-period-flag">${label}</span>`;
    }

    function formatStatisticsPeriodLabel(type, dateValue, period) {
        const date = parseDateValue(dateValue);
        const year = date.getFullYear();
        const month = date.getMonth() + 1;

        if (type === 'year') {
            const rangeStart = formatPeriodStartDate(period, date);
            const rangeEnd = formatPeriodEndDate(period && period.end, getYearEndDate(date));
            return `${formatPeriodFlag('年统计')} ${year}年（${rangeStart}至${rangeEnd}）`;
        }
        if (type === 'half') {
            const { half, start, end } = getHalfYearRange(date);
            const rangeStart = formatPeriodStartDate(period, start);
            const rangeEnd = formatPeriodEndDate(period && period.end, end);
            return `${formatPeriodFlag('半年统计')} ${year}年${getHalfYearLabel(half)}（${rangeStart}至${rangeEnd}）`;
        }
        if (type === 'quarter') {
            const { quarter, start, end } = getQuarterRange(date);
            const rangeStart = formatPeriodStartDate(period, start);
            const rangeEnd = formatPeriodEndDate(period && period.end, end);
            return `${formatPeriodFlag('季度统计')} ${year}年第${quarter}季度（${rangeStart}至${rangeEnd}）`;
        }
        if (type === 'month') {
            const rangeStart = formatPeriodStartDate(period, date);
            const rangeEnd = formatPeriodEndDate(period && period.end, getMonthEndDate(date));
            return `${formatPeriodFlag('月统计')} ${year}年${month}月（${rangeStart}至${rangeEnd}）`;
        }
        if (type === 'week') {
            const { weekStart, weekEnd } = getIsoWeekRange(dateValue);
            const weekLabelDate = weekEnd;
            const weekYear = weekLabelDate.getFullYear();
            const weekMonth = weekLabelDate.getMonth() + 1;
            const weekOrdinalLabels = ['第一周', '第二周', '第三周', '第四周', '第五周', '第六周'];
            const weekOrdinalNumber = getMonthWeekOrdinal(weekStart, weekLabelDate);
            const weekOrdinalLabel = weekOrdinalLabels[weekOrdinalNumber - 1] || `${weekOrdinalNumber}周`;
            const rangeStart = formatPeriodStartDate(period, weekStart);
            const rangeEnd = formatPeriodEndDate(period && period.end, weekEnd);
            return `${formatPeriodFlag('周统计')} ${weekYear}年${weekMonth}月${weekOrdinalLabel}（${rangeStart}至${rangeEnd}）`;
        }
        const rangeStart = formatPeriodStartDate(period, date);
        const rangeEnd = formatPeriodEndDate(period && period.end, getYearEndDate(date));
        return `年统计 ${year}年（${rangeStart}至${rangeEnd}）`;
    }

    function buildTimeParams(dateValue = inputDate.value) {
        const type = selFilterType.value;
        const selectedDate = dateValue;
        const parts = selectedDate.split('-').map(Number);
        const year = parts[0];
        const month = parts[1];

        if (type === 'year') {
            return `filter_type=year&year=${year}`;
        }
        if (type === 'half') {
            return `filter_type=half&year=${year}&half=${getHalfYearPart(month)}`;
        }
        if (type === 'quarter') {
            return `filter_type=quarter&year=${year}&quarter=${getQuarterPart(month)}`;
        }
        if (type === 'month') {
            return `filter_type=month&year=${year}&month=${month}`;
        }
        if (type === 'week') {
            const iso = getIsoWeekParts(selectedDate);
            return `filter_type=week&year=${iso.year}&week=${iso.week}`;
        }
        return `filter_type=year&year=${year}`;
    }

    function getSelectedPhysicalProvinces() {
        if (!physicalProvinceFilter) return [];
        return Array.from(physicalProvinceFilter.selectedOptions || [])
            .map(option => option.value)
            .filter(Boolean);
    }

    function buildPhysicalProvinceParams() {
        const activeTab = document.querySelector('#statisticsTab .nav-link.active');
        if (activeTab && activeTab.id !== 'tab-physical-btn') return '';
        const params = new URLSearchParams();
        getSelectedPhysicalProvinces().forEach(province => {
            params.append('provinces', province);
        });
        const encoded = params.toString();
        return encoded ? `&${encoded}` : '';
    }

    function syncPhysicalProvinceFilterVisibility() {
        if (!physicalProvinceFilterGroup) return;
        const activeTab = document.querySelector('#statisticsTab .nav-link.active');
        const activeTabId = activeTab ? activeTab.id : '';
        physicalProvinceFilterGroup.classList.toggle('d-none', activeTabId !== 'tab-physical-btn');
    }

    // ---------------- 详情请求状态变量 ----------------
    let faultOrdering = '-fault_occurrence_time';
    let branchOrdering = '-fault_occurrence_time';
    let serviceOrdering = '-service_interruption_time';
    let circuitOrdering = '-service_interruption_time';

    // 弹窗拉取重复故障
    async function showFaultRepeatsModal(faultId) {
        const modalEl = document.getElementById('faultRepeatsModal');
        if (!modalEl) return;
        const bootstrapModal = new bootstrap.Modal(modalEl);
        const tbody = document.getElementById('fault-repeats-tbody');
        tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">加载中...</td></tr>';
        bootstrapModal.show();

        try {
            const response = await fetch(`${window.FAULT_REPEATS_API}?fault_id=${faultId}`);
            if (!response.ok) throw new Error('Network response error');
            const data = await response.json();
            const results = data.results || [];
            
            if (results.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">未找到关联的重复故障</td></tr>';
                return;
            }

            tbody.innerHTML = results.map(item => {
                let note = '';
                if (String(item.id) === String(faultId)) {
                    note = '<span class="badge bg-secondary text-white">当前故障</span>';
                } else if (item.in_period) {
                    note = '<span class="badge bg-info text-white">同周期重复</span>';
                } else {
                    note = '<span class="badge bg-purple text-white">前序重复</span>';
                }

                return `<tr>
                    <td><a href="${item.url}" target="_blank">${item.fault_number}</a></td>
                    <td>${item.fault_occurrence_time}</td>
                    <td>${item.fault_recovery_time}</td>
                    <td><strong>${item.duration}</strong></td>
                    <td>${item.category}</td>
                    <td>${item.province}</td>
                    <td>${item.reason}</td>
                    <td><small>${item.site_a}${item.site_z ? ' &rarr; ' + item.site_z : ''}</small></td>
                    <td>${note}</td>
                </tr>`;
            }).join('');
        } catch (error) {
            console.error('Fetch repeats error:', error);
            tbody.innerHTML = '<tr><td colspan="9" class="text-danger text-center py-4">数据加载失败，请重试</td></tr>';
        }
    }

    // ---------------- 获取物理故障数据 ----------------
    async function loadData() {
        const selectedDateParts = inputDate.value.split('-').map(Number);
        let url = `${window.STATISTICS_DATA_API}?${buildTimeParams()}&calendar_year=${selectedDateParts[0]}&calendar_month=${selectedDateParts[1]}`;
        url += buildPhysicalProvinceParams();

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Network response error');
            const data = await response.json();
            
            if (data.period && data.period.start) {
                const periodEl = document.getElementById('period-display');
                periodEl.innerHTML = formatStatisticsPeriodLabel(selFilterType.value, inputDate.value, data.period);
                updatePeriodLabelState(periodEl, data.period);
            } else {
                document.getElementById('period-display').innerHTML = '';
            }

            renderKPIs(data.kpis, data.prev_kpis, selFilterType.value);
            renderImpactLevelOverview(data.impact_level_summary, data.prev_impact_level_summary, selFilterType.value);
            renderOverallSummary(data.kpis, data.charts, data.prev_charts);
            renderOverallOtherSummary(data.other_overview, data.prev_other_overview);
            renderOverallDailyFaultChart(data.charts && data.charts.physical_daily);
            renderPhysicalDurationBoxplot(data.charts && data.charts.physical_duration_boxplot, selFilterType.value);
            currentCableBreakOverview = data.cable_break_overview || null;
            currentPrevCableBreakOverview = data.prev_cable_break_overview || null;
            currentBareFiberInterruption = data.bare_fiber_interruption || null;
            currentPrevBareFiberInterruption = data.prev_bare_fiber_interruption || null;
            currentChartsData = data.charts || null;
            currentBranchCompanyData = data.branch_company || null;
            currentPrevBranchCompanyData = data.prev_branch_company || null;
            branchCompanyProvinceSet = new Set(((currentBranchCompanyData && currentBranchCompanyData.provinces) || []).map(normalizeBranchCompanyProvince));
            renderCableBreakOverview(data.cable_break_overview, data.prev_cable_break_overview);
            renderBranchCompanySection(data.branch_company, data.prev_branch_company);
            renderCharts(data.charts);
            renderRingCharts(data.charts);
            renderBareFiberInterruption(data.bare_fiber_interruption, data.prev_bare_fiber_interruption);

            // 异步加载明细分页
            loadFaultDetails();
            loadBranchDetails();
        } catch (error) {
            console.error('Fetch error:', error);
            document.getElementById('details-tbody').innerHTML = '<tr><td colspan="10" class="text-danger text-center py-4">数据加载失败，请检查网络或刷新重试</td></tr>';
        }
    }

    // ---------------- 渲染部分 ----------------
    function renderKPIs(kpis, prevKpis, type) {
        let repeatEl = document.getElementById('kpi-repeat-faults');
        if (repeatEl) repeatEl.textContent = formatCardCountValue(kpis.repeat_faults_count);
        if (repeatEl) renderTrendBesideMetric(repeatEl, kpis.repeat_faults_count, prevKpis && prevKpis.repeat_faults_count, true);
        
        const periodStrMap = { 'year': '上年', 'half': '上半年', 'quarter': '上季度', 'month': '上月', 'week': '上周' };
        const label = periodStrMap[type] || '上期';
        
        function renderDiff(elId, current, prev, unit) {
            const el = document.getElementById(elId);
            if (!el) return;
            if (!prevKpis) { el.innerHTML = ''; return; }
            let diff = current - prev;
            diff = parseFloat(diff.toFixed(1));
            
            let style = 'background-color: #f1f3f8; color: #6e7687; border: 1px solid #e6e8eb; border-radius: 20px;';
            let symbol = '';
            if (diff > 0) {
                style = 'background-color: #fee2e2; color: #dc2626; border: 1px solid #fecaca; border-radius: 20px;';
                symbol = '+';
            } else if (diff < 0) {
                style = 'background-color: #dcfce7; color: #16a34a; border: 1px solid #bbf7d0; border-radius: 20px;';
            }
            
            el.innerHTML = `<span class="badge fw-normal" style="${style} padding: 4px 10px; font-size:12px;">较${label} ${symbol}${diff} ${unit}</span>`;
        }

        function renderCompactMetricDiff(elId, current, prev) {
            const el = document.getElementById(elId);
            if (!el) return;
            if (!prevKpis) { el.innerHTML = ''; return; }

            let diff = current - prev;
            diff = parseFloat(diff.toFixed(1));

            if (diff > 0) {
                el.innerHTML = `<span class="text-danger fw-bold">⬆${diff}</span>`;
            } else if (diff < 0) {
                el.innerHTML = `<span class="text-success fw-bold">⬇${Math.abs(diff)}</span>`;
            } else {
                el.innerHTML = '';
            }
        }
        
    }

    function renderImpactLevelOverview(summary, prevSummary, type) {
        summary = summary || {};
        prevSummary = prevSummary || {};

        const fields = [
            { id: 'kpi-level-total', key: 'total' },
            { id: 'kpi-level-class-i-ii', key: 'class_i_ii' },
            { id: 'kpi-level-class-i', key: 'class_i' },
            { id: 'kpi-level-class-ii', key: 'class_ii' },
            { id: 'kpi-level-class-iii', key: 'class_iii' },
            { id: 'kpi-level-class-iv', key: 'class_iv' },
            { id: 'kpi-level-class-v', key: 'class_v' },
            { id: 'kpi-level-cutover', key: 'cutover_implemented' }
        ];

        fields.forEach(field => {
            const el = document.getElementById(field.id);
            if (!el) return;
            const currentVal = summary[field.key] !== undefined ? summary[field.key] : 0;
            const prevVal = prevSummary[field.key];
            
            el.textContent = formatCardCountValue(currentVal);
            if (prevVal !== undefined) {
                renderTrendBesideMetric(el, currentVal, prevVal, true);
            } else {
                const trendEl = el.parentElement.parentElement.querySelector('.statistics-metric-trend');
                if (trendEl) trendEl.innerHTML = '';
            }
        });
    }

    function renderOverallSummary(kpis, chartsData, prevChartsData) {
        const overallTotal = document.getElementById('kpi-overall-total');
        const categoriesList = document.getElementById('kpi-overall-categories-flex-list');
        if (!overallTotal || !categoriesList) return;

        overallTotal.textContent = formatCardCountValue(kpis.total_count);

        let categories = (chartsData && chartsData.category) || [];
        if (categories.length === 0) {
            categories = [{name: '--', value: 0}];
        }

        const prevCategories = (prevChartsData && prevChartsData.category) || [];
        const prevOverallTotal = prevCategories.length > 0
            ? prevCategories.reduce((sum, c) => sum + (c.value || 0), 0)
            : undefined;
        renderTrendBesideMetric(overallTotal, kpis.total_count, prevOverallTotal, true);

        let htmlContent = buildFlexGroup(categories, "起", "", "text-indigo", prevCategories, "category");
        categoriesList.innerHTML = htmlContent;
    }

    function renderOverallOtherSummary(otherOverview, prevOtherOverview) {
        const otherList = document.getElementById('kpi-overall-other-flex-list');
        if (!otherList) return;

        otherOverview = otherOverview || {};
        prevOtherOverview = prevOtherOverview || {};
        const suspendedDisplayValue = `${otherOverview.suspended_faults || 0}/${otherOverview.suspended_faults_total || 0}`;
        const prevSuspendedDisplayValue = `${prevOtherOverview.suspended_faults || 0}/${prevOtherOverview.suspended_faults_total || 0}`;

        const items = [
            { name: '光缆劣化', value: otherOverview.fiber_degradation || 0, filterField: 'category' },
            { name: '光缆抖动', value: otherOverview.fiber_jitter || 0, filterField: 'category' },
            {
                name: '挂起的故障（未关闭/总数）',
                value: otherOverview.suspended_faults || 0,
                displayValue: suspendedDisplayValue
            },
        ];
        const prevItems = [
            { name: '光缆劣化', value: prevOtherOverview.fiber_degradation || 0 },
            { name: '光缆抖动', value: prevOtherOverview.fiber_jitter || 0 },
            { name: '挂起的故障（未关闭/总数）', value: prevOtherOverview.suspended_faults || 0, displayValue: prevSuspendedDisplayValue },
        ];

        otherList.innerHTML = buildFlexGroup(items, "起", "", "text-indigo", prevItems);
    }

    function parsePhysicalDailyLabelDate(value) {
        const parts = String(value).split('-').map(Number);
        if (parts.length !== 3 || parts.some(Number.isNaN)) return null;
        return { month: parts[1], day: parts[2] };
    }

    function formatPhysicalWeeklyAxisLabel(value) {
        return String(value).split('第', 1)[0];
    }

    function formatPhysicalDailyAxisLabel(value, filterType) {
        if (filterType === 'week') return formatPhysicalWeeklyAxisLabel(value);
        const dateParts = parsePhysicalDailyLabelDate(value);
        if (!dateParts) return value;
        const { month, day } = dateParts;
        if (filterType === 'month') {
            return `${month}/${day}`;
        }
        if (filterType === 'quarter') {
            return day === 1 ? `${month}月` : `${month}/${day}`;
        }
        return day === 1 ? `${month}月` : '';
    }

    function shouldShowPhysicalDailyAxisLabel(index, value, filterType) {
        if (filterType === 'week') return String(value).includes('第1周');
        const dateParts = parsePhysicalDailyLabelDate(value);
        if (!dateParts) return true;
        const day = dateParts.day;
        if (filterType === 'month') return index === 0 || day === 1 || day % 3 === 0;
        if (filterType === 'quarter') return index === 0 || day === 1 || day % 10 === 0;
        return day === 1;
    }

    function getPhysicalDurationBoxWidth(filterType) {
        if (filterType === 'week') return ['18%', '55%'];
        if (filterType === 'month') return ['10%', '42%'];
        if (filterType === 'quarter') return ['6%', '30%'];
        return ['4%', '18%'];
    }

    function getSelectedPhysicalDailyMetric() {
        const checked = physicalDailyMetricInputs.find(input => input.checked);
        return checked ? checked.value : 'count';
    }

    function getSelectedPhysicalDailyGranularity() {
        const checked = physicalDailyGranularityInputs.find(input => input.checked);
        return checked ? checked.value : 'day';
    }

    function getSelectedPhysicalDailySeriesData(dailyData) {
        const selectedMetric = getSelectedPhysicalDailyMetric();
        const selectedGranularity = getSelectedPhysicalDailyGranularity();
        const labels = selectedGranularity === 'week' ? (dailyData.week_labels || []) : (dailyData.day_labels || dailyData.labels || []);
        const values = selectedMetric === 'duration'
            ? (selectedGranularity === 'week' ? (dailyData.week_durations || []) : (dailyData.day_durations || dailyData.durations || []))
            : (selectedGranularity === 'week' ? (dailyData.week_counts || []) : (dailyData.day_counts || ((dailyData.series || [])[0] || {}).data || []));
        return { labels, values };
    }

    function renderOverallDailyFaultChart(dailyData) {
        if (!chartPhysicalDaily || !dailyData) return;

        const chartTheme = getChartTheme();
        const selectedMetric = getSelectedPhysicalDailyMetric();
        const selectedGranularity = getSelectedPhysicalDailyGranularity();
        const selectedData = getSelectedPhysicalDailySeriesData(dailyData);
        const isCountMetric = selectedMetric === 'count';
        const isWeekGranularity = selectedGranularity === 'week';
        const seriesName = isCountMetric ? '中断数量' : '中断时长';
        const seriesColor = isCountMetric ? '#dc3545' : chartTheme.muted;
        const series = [{
            name: seriesName,
            type: isCountMetric ? 'bar' : 'line',
            yAxisIndex: isCountMetric ? 0 : 1,
            smooth: !isCountMetric,
            showSymbol: false,
            barWidth: isCountMetric ? (isWeekGranularity ? '65%' : 2) : undefined,
            barMaxWidth: isCountMetric ? (isWeekGranularity ? 18 : 2) : undefined,
            emphasis: { focus: 'series' },
            lineStyle: { width: isCountMetric ? 1.5 : 2, color: seriesColor, type: 'solid' },
            itemStyle: { color: seriesColor },
            data: selectedData.values || [],
        }];

        chartPhysicalDaily.setOption({
            textStyle: { color: chartTheme.text },
            color: [seriesColor],
            tooltip: {
                ...buildTooltipTheme(chartTheme),
                trigger: 'axis',
                axisPointer: { type: isCountMetric && isWeekGranularity ? 'shadow' : 'line', lineStyle: { color: chartTheme.axisLine } },
                formatter: function(params) {
                    const item = Array.isArray(params) ? params[0] : params;
                    const value = Number(item.value || 0);
                    const unit = isCountMetric ? '次' : '小时';
                    const displayValue = isCountMetric ? String(Math.round(value)) : value.toFixed(2);
                    return `${item.axisValue}<br/>${item.marker}${item.seriesName}: ${displayValue}${unit}`;
                }
            },
            legend: { show: false },
            grid: buildPhysicalDailyChartGrid(),
            xAxis: {
                type: 'category',
                data: selectedData.labels || [],
                axisLabel: {
                    color: chartTheme.muted,
                    formatter: function(value) {
                        return formatPhysicalDailyAxisLabel(value, selectedGranularity);
                    },
                    interval: function(index, value) {
                        return shouldShowPhysicalDailyAxisLabel(index, value, selectedGranularity);
                    },
                },
                axisLine: { lineStyle: { color: chartTheme.axisLine } },
                axisTick: { show: false },
            },
            yAxis: [
                {
                    type: 'value',
                    name: '次数',
                    minInterval: 1,
                    ...buildAxisTheme(chartTheme),
                    splitLine: { show: false },
                },
                {
                    type: 'value',
                    name: '中断时长(小时)',
                    min: 0,
                    ...buildAxisTheme(chartTheme),
                    splitLine: { show: false },
                }
            ],
            series
        }, true);
    }

    function getBoxplotTooltipValues(params) {
        const rawValue = Array.isArray(params.data && params.data.rawValue) ? params.data.rawValue : (Array.isArray(params.value) ? params.value : (params.data || []));
        return rawValue.length >= 6 ? rawValue.slice(1, 6) : rawValue.slice(0, 5);
    }

    function getBoxplotOutlierTooltipValues(params) {
        const rawValue = Array.isArray(params.data && params.data.rawValue) ? params.data.rawValue : (Array.isArray(params.value) ? params.value : (params.data || []));
        return rawValue.length >= 2 ? rawValue[1] : null;
    }

    const LOG_SCALE_MIN_VALUE = 0.01;

    function clampDurationForLogScale(value) {
        const number = Number(value);
        return Number.isFinite(number) && number > 0 ? number : LOG_SCALE_MIN_VALUE;
    }

    function isEmptyBoxplotSample(item) {
        return Array.isArray(item) && item.every(value => Number(value) <= 0);
    }

    function normalizeBoxplotDataForLogScale(boxplotData) {
        return (boxplotData || []).map(item => {
            if (!Array.isArray(item)) return item;
            if (isEmptyBoxplotSample(item)) return { value: [null, null, null, null, null], rawValue: item };
            return {
                value: item.map(clampDurationForLogScale),
                rawValue: item,
            };
        });
    }

    function normalizeOutlierDataForLogScale(outlierData) {
        return (outlierData || []).map(item => {
            if (!Array.isArray(item)) return item;
            return {
                value: [item[0], clampDurationForLogScale(item[1])],
                rawValue: item,
            };
        });
    }

    function getSelectedPhysicalBoxplotData(dailyData) {
        const shortChecked = Boolean(physicalBoxplotFilterShort && physicalBoxplotFilterShort.checked);
        const rectificationChecked = Boolean(physicalBoxplotFilterRectification && physicalBoxplotFilterRectification.checked);
        const key = shortChecked && rectificationChecked ? 'exclude_short_rectification' : shortChecked ? 'exclude_short' : rectificationChecked ? 'exclude_rectification' : 'all';
        const options = dailyData.boxplot_options || {};
        return options[key] || dailyData.boxplot || [];
    }

    function getSelectedPhysicalBoxplotOutliers(dailyData) {
        const shortChecked = Boolean(physicalBoxplotFilterShort && physicalBoxplotFilterShort.checked);
        const rectificationChecked = Boolean(physicalBoxplotFilterRectification && physicalBoxplotFilterRectification.checked);
        const key = shortChecked && rectificationChecked ? 'exclude_short_rectification' : shortChecked ? 'exclude_short' : rectificationChecked ? 'exclude_rectification' : 'all';
        const options = dailyData.boxplot_outlier_options || {};
        return options[key] || dailyData.boxplot_outliers || [];
    }

    function renderPhysicalDurationBoxplot(dailyData, filterType) {
        if (!chartPhysicalDurationBoxplot || !dailyData) return;

        const chartTheme = getChartTheme();
        const labels = dailyData.labels || [];
        const boxplotData = getSelectedPhysicalBoxplotData(dailyData);
        const outlierData = getSelectedPhysicalBoxplotOutliers(dailyData);
        const useLogScale = Boolean(physicalBoxplotLogScale && physicalBoxplotLogScale.checked);
        const renderedBoxplotData = useLogScale ? normalizeBoxplotDataForLogScale(boxplotData) : boxplotData;
        const renderedOutlierData = useLogScale ? normalizeOutlierDataForLogScale(outlierData) : outlierData;

        chartPhysicalDurationBoxplot.setOption({
            textStyle: { color: chartTheme.text },
            tooltip: {
                ...buildTooltipTheme(chartTheme),
                trigger: 'axis',
                axisPointer: { type: 'shadow', shadowStyle: { color: chartTheme.dark ? 'rgba(110, 168, 254, 0.14)' : 'rgba(32, 107, 196, 0.1)' } },
                formatter: function(params) {
                    const axisParams = Array.isArray(params) ? params : [params];
                    const boxplotParam = axisParams.find(item => item.seriesType === 'boxplot') || axisParams[0] || { value: [] };
                    const outlierParams = axisParams.filter(item => item.seriesType === 'scatter');
                    const value = getBoxplotTooltipValues(boxplotParam);
                    const outlierValues = outlierParams.map(getBoxplotOutlierTooltipValues).filter(value => value !== null);
                    const outlierHtml = outlierValues.length > 0
                        ? `<br/><span style="margin-left:14px;">超出上须: ${outlierValues.join('、')}小时</span>`
                        : '';
                    return `${boxplotParam.axisValue || boxplotParam.name || ''}<br/>` +
                        `<span style="margin-left:14px;">最大值: ${value[4] || 0}小时</span><br/>` +
                        `<span style="margin-left:14px;">Q3: ${value[3] || 0}小时</span><br/>` +
                        `<span style="margin-left:14px;">中位数: ${value[2] || 0}小时</span><br/>` +
                        `<span style="margin-left:14px;">Q1: ${value[1] || 0}小时</span><br/>` +
                        `<span style="margin-left:14px;">最小值: ${value[0] || 0}小时</span>` +
                        outlierHtml;
                }
            },
            grid: buildPhysicalDailyChartGrid(),
            xAxis: {
                type: 'category',
                data: labels,
                axisLabel: {
                    color: chartTheme.muted,
                    formatter: function(value) {
                        return formatPhysicalDailyAxisLabel(value, filterType);
                    },
                    interval: function(index, value) {
                        return shouldShowPhysicalDailyAxisLabel(index, value, filterType);
                    },
                },
                axisLine: { lineStyle: { color: chartTheme.axisLine } },
                axisTick: { show: false },
            },
            yAxis: {
                type: useLogScale ? 'log' : 'value',
                name: '中断时长分布(小时)',
                nameGap: 12,
                nameLocation: 'end',
                min: useLogScale ? 0.01 : 0,
                ...buildAxisTheme(chartTheme),
                axisLabel: {
                    color: chartTheme.muted,
                    formatter: function(value) {
                        if (useLogScale && Math.abs(Number(value) - LOG_SCALE_MIN_VALUE) < 0.000001) return '0.01';
                        return String(value);
                    },
                },
                splitLine: { show: false },
            },
            series: [{
                name: '中断时长分布',
                type: 'boxplot',
                boxWidth: getPhysicalDurationBoxWidth(filterType),
                data: renderedBoxplotData,
                itemStyle: {
                    color: chartTheme.dark ? 'rgba(110, 168, 254, 0.22)' : 'rgba(32, 107, 196, 0.16)',
                    borderColor: chartTheme.primary,
                    borderWidth: 1.2,
                },
                emphasis: { itemStyle: { borderWidth: 2 } },
            }, {
                name: '超出上须',
                type: 'scatter',
                symbol: 'circle',
                symbolSize: 5,
                data: renderedOutlierData,
                itemStyle: {
                    color: chartTheme.dark ? '#ff8787' : '#d63939',
                    opacity: 0.86,
                },
                emphasis: { scale: 1.4 },
            }]
        }, true);
    }

    function formatTrendDiff(currentVal, prevVal, integer = false) {
        const cur = parseFloat(currentVal);
        const prev = parseFloat(prevVal);
        const diff = cur - prev;
        return integer ? String(Math.round(diff)) : diff.toFixed(1);
    }

    function formatCardMetricValue(value) {
        const number = Number(value);
        if (!Number.isFinite(number)) return value === undefined || value === null ? '--' : String(value);
        return number.toFixed(1);
    }

    function formatSlaValue(value) {
        const number = Number(value);
        if (!Number.isFinite(number)) return value === undefined || value === null ? '--' : String(value);
        return (Math.trunc(number * 100) / 100).toFixed(2);
    }

    function formatCardCountValue(value) {
        const number = Number(value);
        if (!Number.isFinite(number)) return value === undefined || value === null ? '--' : String(value);
        return String(Math.round(number));
    }

    function isCountUnit(unit) {
        return unit === '起' || unit === '次';
    }

    function getTrendValueClass(currentVal, prevVal) {
        if (prevVal === undefined || prevVal === null) return 'text-dark';
        const cur = parseFloat(currentVal);
        const prev = parseFloat(prevVal);
        if (isNaN(cur) || isNaN(prev)) return 'text-dark';
        if (cur > prev) return 'text-danger';
        if (cur < prev) return 'text-success';
        return 'text-dark';
    }

    function applyTrendValueColor(metricEl, currentValue, previousValue) {
        if (!metricEl) return;
        const trendValueClass = getTrendValueClass(currentValue, previousValue);
        metricEl.classList.remove('text-danger', 'text-success', 'text-dark', 'text-indigo', 'text-primary', 'text-purple');
        if (trendValueClass) {
            metricEl.classList.add(trendValueClass);
        }
    }

    function buildTrendArrow(currentVal, prevVal, integer = false) {
        if (prevVal === undefined || prevVal === null) return '';
        const cur = parseFloat(currentVal);
        const prev = parseFloat(prevVal);
        if (isNaN(cur) || isNaN(prev) || cur === prev) return '';
        const symbol = cur > prev ? '+' : '';
        const diffText = `${symbol}${formatTrendDiff(cur, prev, integer)}`;
        if (cur > prev) {
            return `<span class="statistics-trend-diff text-danger">${diffText}</span>`;
        } else {
            return `<span class="statistics-trend-diff text-success">${diffText}</span>`;
        }
    }

    function renderTrendBesideMetric(metricEl, currentValue, previousValue, integer = false) {
        if (!metricEl) return;
        applyTrendValueColor(metricEl, currentValue, previousValue);
        const metricTrendContainer = metricEl.parentElement;
        if (!metricTrendContainer || !metricTrendContainer.parentElement) return;

        let trendEl = metricTrendContainer.parentElement.querySelector('.statistics-metric-trend');
        if (!trendEl) {
            trendEl = document.createElement('span');
            trendEl.className = 'statistics-metric-trend statistics-kpi-trend-row';
            metricTrendContainer.appendChild(trendEl);
        }
        trendEl.innerHTML = buildTrendArrow(currentValue, previousValue, integer);
    }

    function buildFlexItemCore(value, unit, title, colorClass = "text-primary", prevValue, filterField, filterValue, filterLabel, valueId, filterExtraField, filterExtraValue, infoTitle, infoLabel, displayValueOverride) {
        const countUnit = isCountUnit(unit);
        const arrow = buildTrendArrow(value, prevValue, countUnit);
        const displayValue = displayValueOverride !== undefined
            ? displayValueOverride
            : (isCountUnit(unit) ? formatCardCountValue(value) : formatCardMetricValue(value));
        const effectiveColorClass = getTrendValueClass(value, prevValue);
        const infoHtml = infoTitle
            ? `<span class="statistics-info-button statistics-inline-info" title="${infoTitle}" aria-label="${infoLabel || title + '说明'}"><i class="mdi mdi-information-outline" aria-hidden="true"></i></span>`
            : "";
        const filterClass = filterField ? " statistics-drill-metric" : "";
        const filterAttrs = filterField
            ? ` data-filter-field="${filterField}" data-filter-value="${filterValue}"${filterExtraField ? ` data-filter-extra-field="${filterExtraField}" data-filter-extra-value="${filterExtraValue}"` : ""} data-filter-label="${filterLabel || title}"`
            : "";
        const valueIdAttr = valueId ? ` id="${valueId}"` : "";
        return `
            <div class="text-center${filterClass}"${filterAttrs}>
                <div class="statistics-overall-kpi-value fs-3 fw-bold ${effectiveColorClass} lh-1"${valueIdAttr}>${displayValue}<span class="statistics-overall-kpi-unit ms-1 text-muted fw-normal" style="font-size: 13px;">${unit}</span>${arrow ? `<span class="statistics-metric-trend statistics-kpi-trend-row">${arrow}</span>` : ''}</div>
                <div class="statistics-overall-kpi-label text-muted mt-1" style="font-size: 12px;">${title}${infoHtml}</div>
            </div>
        `;
    }

    function buildFlexGroup(items, unit, groupTitle, colorClass, prevItems, filterField) {
        if (!items || items.length === 0) return "";
        const compactClass = items.length >= 4 ? " statistics-kpi-group--compact" : "";
        let groupHtml = `<div class="statistics-kpi-group${compactClass}">`;
        groupHtml += `<div class="statistics-kpi-group-items">`;
        items.forEach((item) => {
            let val = (item && item.value !== undefined) ? item.value : item;
            let name = (item && (item.name !== undefined || item.title !== undefined)) ? (item.name || item.title) : item;
            // 按名称在上周期数据中查找对应值
            let prevVal = undefined;
            if (prevItems && prevItems.length > 0) {
                const match = prevItems.find(p => (p.name || p.title) === name);
                if (match) prevVal = match.value;
            }
            if (item && item.prevValue !== undefined) prevVal = item.prevValue;
            const itemFilterField = item && item.filterField !== undefined ? item.filterField : filterField;
            const itemFilterValue = item && item.filterValue !== undefined ? item.filterValue : name;
            const itemFilterLabel = item && item.filterLabel !== undefined ? item.filterLabel : name;
            const itemValueId = item && item.id !== undefined ? item.id : undefined;
            const itemFilterExtraField = item && item.filterExtraField !== undefined ? item.filterExtraField : undefined;
            const itemFilterExtraValue = item && item.filterExtraValue !== undefined ? item.filterExtraValue : undefined;
            const itemInfoTitle = item && item.infoTitle !== undefined ? item.infoTitle : undefined;
            const itemInfoLabel = item && item.infoLabel !== undefined ? item.infoLabel : undefined;
            const itemDisplayValue = item && item.displayValue !== undefined ? item.displayValue : undefined;
            const itemUnit = item && item.unit !== undefined ? item.unit : unit;
            groupHtml += buildFlexItemCore(val, itemUnit, name, colorClass, prevVal, itemFilterField, itemFilterValue, itemFilterLabel, itemValueId, itemFilterExtraField, itemFilterExtraValue, itemInfoTitle, itemInfoLabel, itemDisplayValue);
        });
        groupHtml += `</div>`;
        if (groupTitle) {
            groupHtml += `<span class="statistics-kpi-group-title">${groupTitle}</span>`;
        }
        groupHtml += `</div>`;
        return groupHtml;
    }

    function normalizeTopItems(items, size) {
        const normalized = items.slice(0, size).map(item => ({
            name: item.name || item.title || '--',
            value: item.value !== undefined ? item.value : 0,
        }));
        while (normalized.length < size) {
            normalized.push({name: '--', value: 0});
        }
        return normalized;
    }

    function normalizeNamedItems(items, names) {
        return names.map(name => {
            const match = items.find(item => item.name === name || item.title === name);
            return {
                name,
                value: match && match.value !== undefined ? match.value : 0,
            };
        });
    }

    function buildGroupedFlexLayout(groups) {
        const validGroups = (groups || []).filter(group => group);
        if (validGroups.length === 0) return "";

        let html = "";
        validGroups.forEach((groupHtml, index) => {
            if (index > 0) {
                html += `<div class="statistics-kpi-group-separator" aria-hidden="true"></div>`;
            }
            html += groupHtml;
        });
        return html;
    }

    function renderCableBreakOverview(overview, prevOverview) {
        const totalEl = document.getElementById('cable-break-total-count');
        if (!totalEl) return;

        overview = overview || {};
        prevOverview = prevOverview || {};
        totalEl.textContent = formatCardCountValue(overview.total_count || 0);

        renderTrendBesideMetric(totalEl, overview.total_count || 0, prevOverview.total_count, true);

        // 卡片1-3: 中断起数、原因TOP3、光缆属性
        const prevReasonTop3 = prevOverview.reason_top3 || [];
        const prevSourceCounts = prevOverview.source_counts || [];
        const reasonTop3 = normalizeTopItems(overview.reason_top3 || [], 3);
        const reasonList = document.getElementById('cable-break-reason-top3-flex-list');
        if (reasonList) reasonList.innerHTML = buildFlexGroup(reasonTop3, "起", "", "text-indigo", prevReasonTop3, "reason");

        const sourceCounts = normalizeNamedItems(overview.source_counts || [], ["自控", "第三方", "其他/未填"]);
        const sourceList = document.getElementById('cable-break-source-flex-list');
        if (sourceList) sourceList.innerHTML = buildFlexGroup(sourceCounts, "起", "", "text-indigo", prevSourceCounts, "source_group");

        // 卡片2: 长时中断起数
        let htmlLong = "";
        const buckets = overview.long_duration_buckets || {};
        const prevBuckets = prevOverview.long_duration_buckets || {};
        const orderedBuckets = ['6-8小时', '8-10小时', '10-12小时', '12小时以上'];
        let longTotal = 0;
        let prevLongTotal = 0;
        let longItems = orderedBuckets.map(b => {
            let count = buckets[b] || 0;
            longTotal += count;
            return { value: count, name: b };
        });
        let prevLongItems = orderedBuckets.map(b => {
            let count = prevBuckets[b] || 0;
            prevLongTotal += count;
            return { value: count, name: b };
        });
        longItems = [
            {
                name: "起数",
                value: longTotal,
                prevValue: prevLongTotal,
                filterField: "is_long",
                filterValue: "true",
                filterLabel: "长时起数",
                id: "cable-break-long-total",
            },
            ...longItems.map((item) => ({
                ...item,
                filterField: "duration_bucket",
                filterValue: item.name,
                filterLabel: item.name,
            })),
        ];
        prevLongItems = [
            {name: "起数", value: prevLongTotal},
            ...prevLongItems,
        ];
        htmlLong += buildFlexGroup(longItems, "起", "", "text-indigo", prevLongItems);
        
        const longList = document.getElementById('cable-break-long-flex-list');
        if (longList) longList.innerHTML = htmlLong;

        // 长时历时
        let htmlLongDuration = "";
        const longDurationBuckets = overview.long_duration_bucket_durations || {};
        const prevLongDurationBuckets = prevOverview.long_duration_bucket_durations || {};
        let longDurationTotal = Number(overview.long_duration_total || 0);
        let prevLongDurationTotal = Number(prevOverview.long_duration_total || 0);
        let longDurationItems = orderedBuckets.map(b => {
            const duration = Number(longDurationBuckets[b] || 0);
            return { value: duration, name: b };
        });
        let prevLongDurationItems = orderedBuckets.map(b => {
            const duration = Number(prevLongDurationBuckets[b] || 0);
            return { value: duration, name: b };
        });
        longDurationItems = [
            {
                name: "总历时",
                value: longDurationTotal,
                prevValue: prevLongDurationTotal,
                filterField: "is_long",
                filterValue: "true",
                filterLabel: "长时历时",
                id: "cable-break-long-duration-total",
            },
            ...longDurationItems.map((item) => ({
                ...item,
                filterField: "duration_bucket",
                filterValue: item.name,
                filterLabel: item.name,
            })),
        ];
        prevLongDurationItems = [
            {name: "总历时", value: prevLongDurationTotal},
            ...prevLongDurationItems,
        ];
        htmlLongDuration += buildFlexGroup(longDurationItems, "时", "", "text-indigo", prevLongDurationItems);
        
        const longDurationList = document.getElementById('cable-break-long-duration-flex-list');
        if (longDurationList) longDurationList.innerHTML = htmlLongDuration;

        // 中断历时、原因TOP3、光缆属性
        const prevDurReasonTop3 = prevOverview.reason_duration_top3 || [];
        const prevDurSourceCounts = prevOverview.source_duration_counts || [];
        const currentDuration = Number(overview.total_duration || 0);
        const prevDuration = Number(prevOverview.total_duration || 0);
        const durationTotalList = document.getElementById('cable-break-duration-total-list');

        const durReasonItems = normalizeTopItems((overview.reason_duration_top3 || []).map(i => ({
            name: i.name || i.title,
            value: Number(i.value || 0),
        })), 3);
        const prevDurReasonItems = prevDurReasonTop3.map(i => ({...i, value: Number(i.value || 0)}));
        const durationReasonList = document.getElementById('cable-break-duration-reason-flex-list');
        if (durationReasonList) {
            durationReasonList.innerHTML = buildFlexGroup(durReasonItems, "时", "", "text-indigo", prevDurReasonItems, "reason");
        }

        const durSourceItems = normalizeNamedItems((overview.source_duration_counts || []).map(i => ({
            name: i.name || i.title,
            value: Number(i.value || 0),
        })), ["自控", "第三方", "其他/未填"]);
        const prevDurSourceItems = prevDurSourceCounts.map(i => ({...i, value: Number(i.value || 0)}));
        const durationSourceList = document.getElementById('cable-break-duration-source-flex-list');
        if (durationSourceList) {
            durationSourceList.innerHTML = buildFlexGroup(durSourceItems, "时", "", "text-indigo", prevDurSourceItems, "source_group");
        }

        // 平均历时
        const prevMetrics = prevOverview.avg_metrics || {};
        const durationMetricsList = document.getElementById('cable-break-duration-metrics-flex-list');
        const filteredAverageList = document.getElementById('cable-break-filtered-average-flex-list');
        if (overview.avg_metrics) {
            const m = overview.avg_metrics;
            const overallAverageItems = [
                {
                    name: "全口径平均",
                    value: Number(m.overall_avg || 0),
                    prevValue: prevMetrics.overall_avg,
                    filterField: "category",
                    filterValue: "光缆中断",
                    filterLabel: "全口径平均",
                    id: "cable-break-overall-avg",
                },
            ];
            const durationMetricItems = [
                {
                    name: "P50修复时长",
                    value: Number(m.p50_repair_duration || 0),
                    prevValue: prevMetrics.p50_repair_duration,
                    unit: "时",
                    filterField: "duration_max",
                    filterValue: m.p50_repair_duration,
                    filterLabel: "P50修复时长",
                    id: "cable-break-p50-repair-duration",
                },
                {
                    name: "P90修复时长",
                    value: Number(m.p90_repair_duration || 0),
                    prevValue: prevMetrics.p90_repair_duration,
                    unit: "时",
                    filterField: "duration_min",
                    filterValue: m.p90_repair_duration,
                    filterLabel: "P90修复时长",
                    id: "cable-break-p90-repair-duration",
                },
                {
                    name: "超时率",
                    value: Number(m.timeout_rate || 0),
                    prevValue: prevMetrics.timeout_rate,
                    unit: "%",
                    filterField: "duration_min",
                    filterValue: "4",
                    filterLabel: "超时率",
                    id: "cable-break-timeout-rate",
                },
            ];
            const filteredAverageItems = [
                {
                    name: "有效平均",
                    value: Number(m.valid_avg || 0),
                    prevValue: prevMetrics.valid_avg,
                    filterField: "is_valid_duration",
                    filterValue: "true",
                    filterLabel: "有效平均",
                    id: "cable-break-valid-avg",
                },
                {
                    name: "日间平均",
                    value: Number(m.daytime_avg || 0),
                    prevValue: prevMetrics.daytime_avg,
                    filterField: "occurrence_period",
                    filterValue: "日间",
                    filterExtraField: "is_valid_duration",
                    filterExtraValue: "true",
                    filterLabel: "日间平均",
                    id: "cable-break-daytime-avg",
                },
                {
                    name: "夜间平均",
                    value: Number(m.nighttime_avg || 0),
                    prevValue: prevMetrics.nighttime_avg,
                    filterField: "occurrence_period",
                    filterValue: "夜间",
                    filterExtraField: "is_valid_duration",
                    filterExtraValue: "true",
                    filterLabel: "夜间平均",
                    id: "cable-break-nighttime-avg",
                },
                {
                    name: "施工类",
                    value: Number(m.construction_avg || 0),
                    prevValue: prevMetrics.construction_avg,
                    filterField: "cause_group",
                    filterValue: "施工类",
                    filterExtraField: "is_valid_duration",
                    filterExtraValue: "true",
                    filterLabel: "施工类",
                    id: "cable-break-construction-avg",
                },
                {
                    name: "非施工类",
                    value: Number(m.non_construction_avg || 0),
                    prevValue: prevMetrics.non_construction_avg,
                    filterField: "cause_group",
                    filterValue: "非施工类",
                    filterExtraField: "is_valid_duration",
                    filterExtraValue: "true",
                    filterLabel: "非施工类",
                    id: "cable-break-noncons-avg",
                },
            ];
            const prevOverallAverageItems = overallAverageItems.map(item => ({name: item.name, value: item.prevValue}));
            const prevDurationMetricItems = durationMetricItems.map(item => ({name: item.name, value: item.prevValue}));
            const prevFilteredAverageItems = filteredAverageItems.map(item => ({name: item.name, value: item.prevValue}));
            const durationSummaryItems = [
                {
                    name: "总历时",
                    value: currentDuration,
                    prevValue: prevDuration,
                    unit: "时",
                    filterField: "category",
                    filterValue: "光缆中断",
                    filterLabel: "中断历时",
                    id: "cable-break-total-duration",
                },
                ...overallAverageItems,
                ...filteredAverageItems.slice(0, 1),
                ...durationMetricItems.slice(2),
            ];
            const prevDurationSummaryItems = durationSummaryItems.map(item => ({name: item.name, value: item.prevValue}));
            const remainingFilteredAverageItems = filteredAverageItems.slice(1);
            const prevRemainingFilteredAverageItems = prevFilteredAverageItems.slice(1);
            const repairPercentileItems = durationMetricItems.slice(0, 2);
            const prevRepairPercentileItems = prevDurationMetricItems.slice(0, 2);
            if (durationTotalList) {
                durationTotalList.innerHTML = buildFlexGroup(durationSummaryItems, "", "", "text-indigo", prevDurationSummaryItems);
            }
            if (durationMetricsList) {
                durationMetricsList.innerHTML = buildFlexGroup(repairPercentileItems, "", "", "text-indigo", prevRepairPercentileItems);
            }
            if (filteredAverageList) {
                filteredAverageList.innerHTML = buildFlexGroup(remainingFilteredAverageItems, "时", "", "text-indigo", prevRemainingFilteredAverageItems);
            }
        }
        
        if (overview.histogram && chartHistogram) {
            let histLabels = overview.histogram.map(item => item.label);
            let histValues = overview.histogram.map(item => ({value: item.value, _percent: item.percent}));
            const histogramMaxValue = Math.max(...overview.histogram.map(item => item.value), 0);
            const chartTheme = getChartTheme();
            
            chartHistogram.setOption({
                tooltip: {
                    ...buildTooltipTheme(chartTheme),
                    trigger: 'axis',
                    axisPointer: { type: 'shadow', shadowStyle: { color: chartTheme.dark ? 'rgba(110, 168, 254, 0.14)' : 'rgba(32, 107, 196, 0.1)' } },
                    formatter: function(params) {
                        let p = params[0];
                        return `${p.name} 小时<br/>数量：${p.value}起 (${p.data._percent}%)`;
                    }
                },
                grid: { top: 32, left: 12, right: 12, bottom: 30, containLabel: true },
                xAxis: { 
                    type: 'category', 
                    data: histLabels,
                    name: '历时(小时)',
                    nameLocation: 'middle',
                    nameGap: 24,
                    ...buildAxisTheme(chartTheme, { interval: 0, fontSize: 11 })
                },
                yAxis: {
                    type: 'value',
                    name: '起数',
                    minInterval: 1,
                    max: histogramMaxValue > 0 ? Math.ceil(histogramMaxValue * 1.25) : 1,
                    ...buildAxisTheme(chartTheme),
                    splitLine: { show: false }
                },
                series: [{
                    type: 'bar',
                    barCategoryGap: '0%',
                    barGap: '0%',
                    itemStyle: { color: chartTheme.primary, borderRadius: [0, 0, 0, 0] },
                    label: {
                        show: true,
                        position: 'top',
                        formatter: function(params) {
                            if(params.value === 0) return '';
                            return `${params.value}起\n${params.data._percent}%`;
                        },
                        color: chartTheme.heading,
                        fontSize: 10,
                        lineHeight: 14,
                        align: 'center'
                    },
                    data: histValues
                }]
            });
        }
    }

    function renderBareFiberInterruption(overview, prevOverview, idPrefix = 'barefiber') {
        overview = overview || {};
        prevOverview = prevOverview || {};

        const totalCountEl = document.getElementById(`${idPrefix}-total-count`);
        const distinctCountEl = document.getElementById(`${idPrefix}-distinct-count`);
        const totalDurationEl = document.getElementById(`${idPrefix}-total-duration`);
        const distinctDurationEl = document.getElementById(`${idPrefix}-distinct-duration`);

        if (totalCountEl) {
            totalCountEl.textContent = formatCardCountValue(overview.total_count);
            renderTrendBesideMetric(totalCountEl, overview.total_count, prevOverview.total_count, true);
        }
        if (distinctCountEl) {
            distinctCountEl.textContent = formatCardCountValue(overview.distinct_count);
            renderTrendBesideMetric(distinctCountEl, overview.distinct_count, prevOverview.distinct_count, true);
        }
        if (totalDurationEl) {
            totalDurationEl.textContent = formatCardMetricValue(overview.total_duration);
            renderTrendBesideMetric(totalDurationEl, overview.total_duration, prevOverview.total_duration, false);
        }
        if (distinctDurationEl) {
            distinctDurationEl.textContent = formatCardMetricValue(overview.distinct_duration);
            renderTrendBesideMetric(distinctDurationEl, overview.distinct_duration, prevOverview.distinct_duration, false);
        }
    }

    function renderCharts(chartsData) {
        if (!chartsData) return;
        const chartTheme = getChartTheme();
        // 1. 光缆属性 (Pie)
        const resourceColorMap = {
            '自建光缆': chartTheme.chartPalette[0],
            '协调资源': chartTheme.chartPalette[1],
            '租赁纤芯': chartTheme.chartPalette[2],
            '未填写': chartTheme.dark ? '#697386' : '#cbd5e1'
        };
        const resourceTypeOrder = ['自建光缆', '协调资源', '租赁纤芯', '未填写'];
        const resourceTypeRank = new Map(resourceTypeOrder.map((name, index) => [name, index]));
        const isResourceCount = currentMetricResource === 'count';
        const resourceData = chartsData.resource
            .map(item => ({name: item.name, value: isResourceCount ? item.value : item.duration, _duration: item.duration, _count: item.value}))
            .sort((a, b) => (resourceTypeRank.get(a.name) ?? resourceTypeOrder.length) - (resourceTypeRank.get(b.name) ?? resourceTypeOrder.length));
        const resourceTotal = resourceData.reduce((sum, item) => sum + item.value, 0);
        function formatResourceMetricLabel(params) {
            const item = resourceData.find(resourceItem => resourceItem.name === params.name);
            if (!item) return params.name;
            const percent = resourceTotal > 0 ? ((item.value / resourceTotal) * 100).toFixed(2) : "0.00";
            return isResourceCount ? `${params.name}\n${item._count}次 ${percent}%` : `${params.name}\n${item._duration.toFixed(2)}小时 ${percent}%`;
        }
        chartResource.setOption({
            textStyle: { color: chartTheme.text },
            tooltip: { 
                ...buildTooltipTheme(chartTheme),
                trigger: 'axis',
                axisPointer: { type: 'shadow', shadowStyle: { color: chartTheme.dark ? 'rgba(110, 168, 254, 0.14)' : 'rgba(32, 107, 196, 0.1)' } },
                formatter: params => {
                    let p = params[0];
                    let percent = resourceTotal > 0 ? ((p.value / resourceTotal) * 100).toFixed(2) : "0.00";
                    let avg = p.data._count > 0 ? (p.data._duration / p.data._count).toFixed(2) : "0.00";
                    return `${p.marker || ''}${p.name}: ${p.data._count}次 (${isResourceCount ? percent + '%' : '-'})<br/>` +
                           `<span style="margin-left:14px;">总历时: ${p.data._duration} 小时 (${!isResourceCount ? percent + '%' : '-'})</span><br/>` +
                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;
                }
            },
            grid: { top: 12, left: 16, right: 16, bottom: 12, containLabel: false },
            xAxis: {
                type: 'value',
                minInterval: 1,
                axisLabel: { show: false },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { show: false },
            },
            yAxis: {
                type: 'category',
                data: resourceData.map(item => item.name),
                inverse: true,
                axisLabel: { show: false },
                axisLine: { show: false },
                axisTick: { show: false },
            },
            series: [{
                type: 'bar',
                barMaxWidth: 16,
                label: {
                    show: true,
                    position: 'top',
                    align: 'left',
                    distance: 8,
                    formatter: formatResourceMetricLabel,
                    color: chartTheme.heading,
                    fontSize: 11,
                    lineHeight: 15
                },
                labelLayout: params => ({
                    x: params.rect.x,
                    y: params.rect.y - 4,
                    verticalAlign: 'bottom',
                    align: 'left',
                }),
                itemStyle: { borderRadius: [0, 4, 4, 0] },
                data: resourceData.map(item => ({value: item.value, _duration: item._duration, _count: item._count, itemStyle: { color: resourceColorMap[item.name] || chartTheme.primary }}))
            }]
        });

        // 2. 省份 (Bar 全部)
        const isProvinceCount = currentMetricProvince === 'count';
        let provData = chartsData.province.slice().sort((a, b) => {
            return isProvinceCount ? b.value - a.value : b.duration - a.duration;
        });
        chartProvince.setOption({
            textStyle: { color: chartTheme.text },
            tooltip: { 
                ...buildTooltipTheme(chartTheme),
                trigger: 'axis', 
                axisPointer: { type: 'shadow', shadowStyle: { color: chartTheme.dark ? 'rgba(110, 168, 254, 0.14)' : 'rgba(32, 107, 196, 0.1)' } },
                formatter: params => {
                    let p = params[0];
                    let avg = p.data._count > 0 ? (p.data._duration / p.data._count).toFixed(2) : "0.00";
                    return `${p.marker || ''}${p.name}: ${p.data._count}次<br/>` +
                           `<span style="margin-left:14px;">总历时: ${p.data._duration} 小时</span><br/>` +
                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;
                }
            },
            grid: { top: 18, left: 12, right: 12, bottom: 42, containLabel: true },
            xAxis: { 
                type: 'category', 
                data: provData.map(item => item.name),
                ...buildAxisTheme(chartTheme, { interval: 0, rotate: 30 })
            },
            yAxis: { type: 'value', ...buildAxisTheme(chartTheme) },
            series: [{
                type: 'bar',
                label: { 
                    show: true, position: 'top', color: chartTheme.heading, fontWeight: 600,
                    formatter: function(params) { return isProvinceCount ? (params.value > 0 ? params.value : '') : (params.value > 0 ? params.value.toFixed(1) : ''); }
                },
                itemStyle: { color: chartTheme.primary, borderRadius: [4, 4, 0, 0] },
                data: provData.map(item => ({value: isProvinceCount ? item.value : item.duration, _duration: item.duration, _count: item.value}))
            }]
        });

        // 3. 一级原因 (Pie)
        const isReasonCount = currentMetricReason === 'count';
        const reasonData = chartsData.reason.map(item => ({name: item.name, value: isReasonCount ? item.value : item.duration, _duration: item.duration, _count: item.value}));
        const reasonTotal = reasonData.reduce((sum, item) => sum + item.value, 0);
        const reasonLegendByName = new Map(reasonData.map(item => [item.name, item]));
        const reasonColorPalette = [
            '#2563eb',
            '#16a34a',
            '#f97316',
            '#dc2626',
            '#9333ea',
            '#0891b2',
            '#64748b',
            '#eab308'
        ];
        chartReason.setOption({
            textStyle: { color: chartTheme.text },
            color: reasonColorPalette,
            tooltip: { 
                ...buildTooltipTheme(chartTheme),
                trigger: 'item', 
                formatter: params => {
                    let avg = params.data._count > 0 ? (params.data._duration / params.data._count).toFixed(2) : "0.00";
                    return `${params.marker}${params.name}: ${params.data._count}次 (${isReasonCount ? params.percent + '%' : '-'})<br/>` +
                           `<span style="margin-left:14px;">总历时: ${params.data._duration} 小时 (${!isReasonCount ? params.percent + '%' : '-'})</span><br/>` +
                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;
                }
            },
            legend: {
                bottom: 0,
                left: 'center',
                formatter: name => {
                    const item = reasonLegendByName.get(name);
                    if (!item) return name;
                    const percent = reasonTotal > 0 ? ((item.value / reasonTotal) * 100).toFixed(2) : "0.00";
                    return isReasonCount ? `${name}  ${item._count}次 ${percent}%` : `${name}  ${item._duration.toFixed(2)}时 ${percent}%`;
                },
                ...buildLegendTheme(chartTheme)
            },
            series: [{
                type: 'pie',
                radius: ['38%', '62%'],
                center: ['50%', '34%'],
                label: { show: false },
                labelLine: { show: false },
                itemStyle: { borderColor: chartTheme.surface, borderWidth: 2 },
                data: reasonData,
                emphasis: {
                    itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: chartTheme.dark ? 'rgba(0, 0, 0, 0.75)' : 'rgba(0, 0, 0, 0.3)' }
                }
            }]
        });

    }

    function renderRingCharts(chartsData) {
        if (!chartsData) return;
        const theme = getChartTheme();

        const buildRingOption = (titleText, dataList) => {
            const total = dataList.reduce((sum, item) => sum + (item.value || 0), 0);
            
            const colorMap = {
                'I类': '#ef4444',
                'II类': theme.chartPalette[0],
                'III类': theme.chartPalette[0],
                '挂起': '#94a3b8'
            };
            const colors = dataList.map(item => colorMap[item.name] || theme.primary);

            return {
                textStyle: { color: theme.text },
                color: colors,
                tooltip: {
                    ...buildTooltipTheme(theme),
                    trigger: 'item',
                    formatter: function(params) {
                        const percent = total > 0 ? ((params.value / total) * 100).toFixed(2) : "0.00";
                        return `${params.marker}${params.name}: ${params.value}起 (${percent}%)`;
                    }
                },
                title: {
                    text: total + '起',
                    subtext: '总数',
                    left: 'center',
                    top: '32%',
                    textStyle: {
                        fontSize: 20,
                        fontWeight: 'bold',
                        color: theme.heading
                    },
                    subtextStyle: {
                        fontSize: 11,
                        color: theme.muted
                    }
                },
                legend: {
                    bottom: 5,
                    left: 'center',
                    itemWidth: 10,
                    itemHeight: 10,
                    formatter: function(name) {
                        const item = dataList.find(d => d.name === name);
                        if (!item) return name;
                        const val = item.value || 0;
                        const pct = total > 0 ? ((val / total) * 100).toFixed(1) : "0.0";
                        return `${name} ${val}起 (${pct}%)`;
                    },
                    ...buildLegendTheme(theme)
                },
                series: [{
                    type: 'pie',
                    radius: ['48%', '66%'],
                    center: ['50%', '42%'],
                    label: { show: false },
                    labelLine: { show: false },
                    itemStyle: {
                        borderColor: theme.surface,
                        borderWidth: 2
                    },
                    data: dataList,
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowOffsetX: 0,
                            shadowColor: theme.dark ? 'rgba(0, 0, 0, 0.5)' : 'rgba(0, 0, 0, 0.2)'
                        }
                    }
                }]
            };
        };

        if (chartsData.ring_fiber) {
            chartRingFiber.setOption(buildRingOption('光缆中断', chartsData.ring_fiber));
        }
        if (chartsData.ring_power) {
            chartRingPower.setOption(buildRingOption('供电故障', chartsData.ring_power));
        }
        if (chartsData.ring_environment) {
            chartRingEnvironment.setOption(buildRingOption('空调与设备', chartsData.ring_environment));
        }
    }

    function getCheckedValue(name, fallback) {
        const checked = document.querySelector(`input[name="${name}"]:checked`);
        return checked ? checked.value : fallback;
    }

    function normalizeBranchCompanyProvince(name) {
        const value = String(name || '').trim();
        if (!value) return '';
        if (value.startsWith('内蒙古')) return '内蒙';
        return value
            .replace('维吾尔自治区', '')
            .replace('壮族自治区', '')
            .replace('回族自治区', '')
            .replace('自治区', '')
            .replace('省', '')
            .replace('市', '');
    }

    function renderBranchCompanySection(branchData, prevBranchData = currentPrevBranchCompanyData) {
        if (!branchData) return;
        renderBranchCompanyPerformanceCards(branchData.performance_cards || []);
        renderBranchCompanyOverview(branchData, prevBranchData);
        renderBranchCompanyBarCharts(branchData);
        renderBranchCompanyBoxplot(branchData);
        renderBranchCompanyValidDurationChart(branchData);
        renderBranchCompanyWeeklyChart(branchData);
        renderBranchCompanyMonthlyChart(branchData);
    }

    function formatBranchPerformanceValue(value, digits = 1) {
        const numeric = Number(value || 0);
        return numeric.toFixed(digits).replace(/\.0$/, '');
    }

    function formatBranchPerformanceDeductionValue(value) {
        const numeric = Number(value || 0);
        if (numeric <= 0) {
            return '0';
        }
        return `-${formatBranchPerformanceValue(numeric)}`;
    }

    function renderBranchPerformanceReasonList(items, type = 'responsibility') {
        const source = Array.isArray(items) ? items : [];
        if (source.length === 0) {
            return '<span class="branch-performance-empty">暂无</span>';
        }
        const pillClass = type === 'responsibility' ? 'branch-performance-reason-pill--responsibility' : 'branch-performance-reason-pill--overall';
        return source.map(item => {
            const name = item.name || item.label || '-';
            const value = Number(item.value || item.count || 0);
            return `<span class="branch-performance-reason-pill ${pillClass}">${escapeHtml(name)} ${formatBranchPerformanceValue(value)}</span>`;
        }).join('');
    }

    function renderBranchPerformanceMetricItem(label, value, unit = '', emphasized = false) {
        const emphasisClass = emphasized ? ' service-annual-summary-value--emphasis' : '';
        return `
            <div class="service-annual-summary-item branch-performance-annual-metric-v2">
                <div class="service-annual-summary-value${emphasisClass}">
                    ${formatCardMetricValue(value)}${unit ? `<small class="branch-performance-annual-unit">${escapeHtml(unit)}</small>` : ''}
                </div>
                <div class="service-annual-summary-label">${escapeHtml(label)}</div>
            </div>`;
    }

    function renderBranchPerformanceAnnualSection(title, items, modifier = '') {
        let iconClass = 'mdi-server-network';
        if (modifier.includes('bare-fiber')) {
            iconClass = 'mdi-server-network';
        } else if (modifier.includes('cable-break')) {
            iconClass = 'mdi-transit-connection-horizontal';
        } else if (modifier.includes('power')) {
            iconClass = 'mdi-flash';
        }
        return `
            <div class="branch-performance-annual-section ${modifier}">
                <div class="branch-performance-annual-heading">
                    <span class="service-annual-icon"><i class="mdi ${iconClass}"></i></span>
                    <div class="branch-performance-annual-title">${escapeHtml(title)}</div>
                </div>
                <div class="service-annual-summary-grid branch-performance-annual-grid-v2">
                    ${items.join('')}
                </div>
            </div>`;
    }

    function renderBranchPerformanceAnnualStats(card) {
        const annual = card.annual_stats || {};
        const bareFiber = annual.bare_fiber || {};
        const cableBreak = annual.cable_break || {};
        const power = annual.power || {};
        return `
            <div class="service-annual-summary branch-performance-annual-stats">
                ${renderBranchPerformanceAnnualSection('\u88f8\u7ea4\u4e1a\u52a1', [
                    renderBranchPerformanceMetricItem('\u603b\u6b21\u6570', bareFiber.total_count, '\u8d77', true),
                    renderBranchPerformanceMetricItem('\u53bb\u9664\u540c\u6e90', bareFiber.distinct_count, '\u8d77', true),
                    renderBranchPerformanceMetricItem('\u603b\u5386\u65f6', bareFiber.total_duration, '\u65f6', true),
                    renderBranchPerformanceMetricItem('\u53bb\u9664\u540c\u6e90\u5386\u65f6', bareFiber.distinct_duration, '\u65f6', true),
                ], 'branch-performance-annual-section--bare-fiber')}
                ${renderBranchPerformanceAnnualSection('\u5149\u7f06\u4e2d\u65ad\uff08\u4e0d\u542b\u6302\u8d77\uff09', [
                    renderBranchPerformanceMetricItem('\u603b\u6b21\u6570', cableBreak.total_count, '\u8d77'),
                    renderBranchPerformanceMetricItem('\u5343\u516c\u91cc\u6b21\u6570', cableBreak.count_per_1000km, '\u8d77', true),
                    renderBranchPerformanceMetricItem('\u603b\u5386\u65f6', cableBreak.total_duration, '\u65f6'),
                    renderBranchPerformanceMetricItem('\u5343\u516c\u91cc\u5386\u65f6', cableBreak.duration_per_1000km, '\u65f6', true),
                    renderBranchPerformanceMetricItem('\u6709\u6548\u5e73\u5747\u5386\u65f6', cableBreak.valid_avg_duration, '\u65f6'),
                    renderBranchPerformanceMetricItem('\u957f\u65f6\u22656h', cableBreak.long_count, '\u8d77'),
                    renderBranchPerformanceMetricItem('\u91cd\u590d\u6545\u969c', cableBreak.repeat_count, '\u8d77'),
                ], 'branch-performance-annual-section--cable-break')}
                ${renderBranchPerformanceAnnualSection('\u4f9b\u7535\u6545\u969c', [
                    renderBranchPerformanceMetricItem('\u603b\u6b21\u6570', power.total_count, '\u8d77'),
                    renderBranchPerformanceMetricItem('\u8bbe\u5907\u8131\u7ba1', power.hosted_count, '\u8d77'),
                ], 'branch-performance-annual-section--power')}
            </div>`;
    }

    function renderBranchPerformanceRuntimeCalendar(card) {
        return `
                <div class="service-runtime-calendar branch-performance-runtime-calendar">
                    <div class="service-runtime-calendar-heading">
                        <span class="service-runtime-calendar-icon"><i class="mdi mdi-calendar-month-outline"></i></span>
                        <div class="service-runtime-calendar-title">运行月历</div>
                    </div>
                    <div class="service-runtime-calendar-chart branch-performance-runtime-calendar-chart" aria-label="本年子公司故障月度统计"></div>
                </div>`;
    }

    function renderBranchPerformanceInterruptCalendar(card, interruptCalendarMaxCount) {
        const months = Array.isArray(card.interrupt_calendar) ? card.interrupt_calendar.slice(-3) : [];
        const expandedMonths = Array.isArray(card.interrupt_calendar_full) ? card.interrupt_calendar_full : months;
        const maxCount = Number(interruptCalendarMaxCount || 0);
        return `
                <div class="branch-performance-interrupt-calendar service-interrupt-calendar" aria-label="近三个月子公司中断日历">
                    <div class="service-interrupt-calendar-months service-interrupt-calendar-months--default">${renderServiceInterruptCalendarMonthGrid(months, maxCount)}</div>
                    <div class="service-interrupt-calendar-months service-interrupt-calendar-months--expanded d-none">${renderServiceInterruptCalendarMonthGrid(expandedMonths, maxCount)}</div>
                    <button type="button" class="branch-performance-interrupt-calendar-toggle service-interrupt-calendar-toggle" aria-label="展开本年中断日历" title="展开本年中断日历">
                        <i class="mdi mdi-arrow-expand-all"></i>
                    </button>
                </div>`;
    }

    function disposeBranchPerformanceCalendarCharts() {
        branchPerformanceCalendarCharts.forEach(chart => chart.dispose());
        branchPerformanceCalendarCharts = [];
    }

    function resizeBranchPerformanceCalendarCharts() {
        branchPerformanceCalendarCharts.forEach(chart => chart.resize());
    }

    function getBranchPerformanceRuntimeScale() {
        const checked = branchPerformanceRuntimeScaleInputs.find(input => input.checked);
        return checked && checked.value === 'raw' ? 'raw' : 'per_1000km';
    }

    function initBranchPerformanceRuntimeCalendarCharts(container, cardsByProvince) {
        container.querySelectorAll('.branch-performance-runtime-calendar-chart').forEach(element => {
            const cardEl = element.closest('.statistics-branch-performance-card[data-province]');
            const card = cardEl ? cardsByProvince.get(cardEl.dataset.province) || {} : {};
            const monthlyStats = Array.isArray(card.monthly_stats) ? card.monthly_stats : [];
            const runtimeScale = getBranchPerformanceRuntimeScale();
            const countAxisUnit = runtimeScale === 'per_1000km' ? '次/千公里' : '次';
            const durationUnit = runtimeScale === 'per_1000km' ? '时/千公里' : '时';
            const monthLabels = Array.from({ length: 12 }, (_item, index) => `${index + 1}月`);
            const selectedDateParts = inputDate.value.split('-').map(Number);
            const annualYear = (card.annual_stats && card.annual_stats.year) || (selectedDateParts && selectedDateParts[0]) || new Date().getFullYear();
            const currentDate = new Date();
            const currentYear = currentDate.getFullYear();
            const currentMonth = currentDate.getMonth() + 1;
            const isCurrentYear = annualYear === currentYear;
            const countValues = monthLabels.map((_label, index) => Number(
                monthlyStats[index] && (runtimeScale === 'per_1000km' ? monthlyStats[index].count_per_1000km : monthlyStats[index].count) || 0
            ));
            const durationValues = monthLabels.map((_label, index) => Number(
                monthlyStats[index] && (runtimeScale === 'per_1000km' ? monthlyStats[index].duration_per_1000km : monthlyStats[index].duration) || 0
            ));
            const durationValuesPast = Array(12).fill(null);
            const durationValuesFuture = Array(12).fill(null);
            if (isCurrentYear) {
                for (let i = 0; i < 12; i++) {
                    if (i < currentMonth) {
                        durationValuesPast[i] = durationValues[i];
                    }
                    if (i >= currentMonth - 1) {
                        durationValuesFuture[i] = durationValues[i];
                    }
                }
            } else if (annualYear < currentYear) {
                for (let i = 0; i < 12; i++) {
                    durationValuesPast[i] = durationValues[i];
                }
            } else {
                for (let i = 0; i < 12; i++) {
                    durationValuesFuture[i] = durationValues[i];
                }
            }
            const maxCount = Math.max(...countValues, 0);
            const maxDuration = Math.max(...durationValues, 0);
            const countAxisMax = Math.max(1, Math.ceil(maxCount * 2.6));
            let durationAxisMin, durationAxisMax;
            if (maxDuration > 0) {
                durationAxisMin = -Math.max(1, Math.ceil(maxDuration * 1.5));
                durationAxisMax = Math.max(1, Math.ceil(maxDuration * 1.15));
            } else {
                durationAxisMin = -1.3;
                durationAxisMax = 1.0;
            }
            const theme = getChartTheme();
            const chart = echarts.init(element);
            const chartOptions = {
                animation: false,
                backgroundColor: 'transparent',
                grid: { top: 16, left: 4, right: runtimeScale === 'per_1000km' ? 42 : 24, bottom: 20, containLabel: false },
                tooltip: Object.assign({
                    trigger: 'axis',
                    confine: true,
                    formatter(params) {
                        const label = params && params[0] ? params[0].axisValue : '';
                        const labelIndex = monthLabels.indexOf(label);
                        const count = countValues[labelIndex] || 0;
                        const duration = durationValues[labelIndex] || 0;
                        return `${label}<br/>故障数：${formatCardMetricValue(count)}${countAxisUnit}<br/>故障时长：${formatCardMetricValue(duration)}${durationUnit}`;
                    }
                }, buildTooltipTheme(theme)),
                xAxis: {
                    type: 'category',
                    data: monthLabels,
                    axisLine: { show: true, lineStyle: { color: 'rgba(154, 168, 186, 0.45)', width: 1 } },
                    axisTick: { show: false },
                    axisLabel: { color: theme.muted, fontSize: 10, interval: 0, margin: 8, hideOverlap: false },
                    splitLine: { show: false }
                },
                yAxis: [
                    {
                        name: countAxisUnit,
                        type: 'value',
                        position: 'right',
                        nameLocation: 'middle',
                        nameRotate: 0,
                        nameGap: runtimeScale === 'per_1000km' ? 18 : 0,
                        nameTextStyle: { color: '#078087', fontSize: 10, fontWeight: 600, align: 'center', verticalAlign: 'middle', padding: [78, 0, 0, 0] },
                        minInterval: 1,
                        min: 0,
                        max: countAxisMax,
                        axisLine: { show: false },
                        axisTick: { show: false },
                        axisLabel: { show: false },
                        splitLine: { show: false }
                    },
                    {
                        name: '时',
                        type: 'value',
                        position: 'right',
                        nameLocation: 'end',
                        nameGap: 2,
                        nameTextStyle: { color: '#078087', fontSize: 10, fontWeight: 600 },
                        min: durationAxisMin,
                        max: durationAxisMax,
                        axisLine: { show: false },
                        axisTick: { show: false },
                        axisLabel: { show: false },
                        splitLine: { show: false }
                    }
                ],
                series: [
                    {
                        name: '故障时长',
                        type: 'line',
                        yAxisIndex: 1,
                        data: durationValuesPast,
                        smooth: true,
                        symbol: 'circle',
                        symbolSize: 4,
                        label: {
                            show: true,
                            position: 'top',
                            distance: 4,
                            color: '#078087',
                            fontSize: 9,
                            formatter(params) {
                                const value = Number(params.value || 0);
                                return value > 0 ? formatCardMetricValue(value) : '';
                            }
                        },
                        lineStyle: { width: 1.8, color: '#078087' },
                        itemStyle: { color: '#078087' },
                        areaStyle: { color: '#078087', opacity: 0.08 }
                    },
                    {
                        name: '故障时长',
                        type: 'line',
                        yAxisIndex: 1,
                        data: durationValuesFuture,
                        smooth: true,
                        symbol: 'circle',
                        symbolSize: 4,
                        label: {
                            show: true,
                            position: 'top',
                            distance: 4,
                            color: '#cbd5e1',
                            fontSize: 9,
                            formatter(params) {
                                const value = Number(params.value || 0);
                                return value > 0 ? formatCardMetricValue(value) : '';
                            }
                        },
                        lineStyle: { width: 1.8, color: '#cbd5e1' },
                        itemStyle: { color: '#cbd5e1' },
                        areaStyle: { color: '#cbd5e1', opacity: 0.08 }
                    },
                    {
                        name: '故障数',
                        type: 'bar',
                        yAxisIndex: 0,
                        data: countValues,
                        barWidth: 8,
                        label: {
                            show: true,
                            position: 'top',
                            distance: 2,
                            color: theme.muted,
                            fontSize: 9,
                            formatter(params) {
                                const value = Number(params.value || 0);
                                return value > 0 ? formatCardMetricValue(value) : '';
                            }
                        },
                        itemStyle: {
                            color: 'rgba(32, 107, 196, 0.55)',
                            borderRadius: [3, 3, 0, 0]
                        }
                    }
                ]
            };
            chart.setOption(chartOptions);
            branchPerformanceCalendarCharts.push(chart);
        });
    }

    function initBranchPerformanceInterruptCalendarToggles(container) {
        container.querySelectorAll('.branch-performance-interrupt-calendar-toggle').forEach(button => {
            button.addEventListener('click', event => {
                event.preventDefault();
                event.stopPropagation();
                const calendar = button.closest('.branch-performance-interrupt-calendar');
                if (!calendar) return;
                const defaultMonths = calendar.querySelector('.service-interrupt-calendar-months--default');
                const expandedMonths = calendar.querySelector('.service-interrupt-calendar-months--expanded');
                const icon = button.querySelector('.mdi');
                const expanded = !calendar.classList.contains('service-interrupt-calendar--expanded');
                calendar.classList.toggle('service-interrupt-calendar--expanded', expanded);
                if (defaultMonths) defaultMonths.classList.toggle('d-none', expanded);
                if (expandedMonths) expandedMonths.classList.toggle('d-none', !expanded);
                button.setAttribute('aria-label', expanded ? '收回中断日历' : '展开本年中断日历');
                button.setAttribute('title', expanded ? '收回中断日历' : '展开本年中断日历');
                if (icon) icon.className = expanded ? 'mdi mdi-arrow-collapse-all' : 'mdi mdi-arrow-expand-all';
            });
        });
    }

    function renderBranchCompanyPerformanceCard(card) {
        const title = card.label || card.province || '-';
        const annualYear = (card.annual_stats && card.annual_stats.year) || new Date().getFullYear();
        const annualLabel = `年度累计（${annualYear}年）`;
        return `
            <div class="statistics-strip-card service-strip-card statistics-branch-performance-card" data-province="${escapeHtml(card.province || '')}">
                <div class="service-strip-card-title" title="${escapeHtml(`${title} ${annualLabel}`)}" role="button" tabindex="0">
                    <span class="branch-performance-title-name">${escapeHtml(title)}</span>
                    <span class="branch-performance-title-annual">
                        <span class="branch-performance-title-annual-icon"><i class="mdi mdi-calendar-range-outline"></i></span>
                        <span>${escapeHtml(annualLabel)}</span>
                    </span>
                </div>
                <div class="statistics-strip-card-body">
                    ${renderBranchPerformanceAnnualStats(card)}
                    ${renderBranchPerformanceRuntimeCalendar(card)}
                    ${renderBranchPerformanceInterruptCalendar(card, card.interruptCalendarMaxCount)}
                </div>
            </div>`;
    }

    function renderBranchCompanyPerformanceCards(cards) {
        const container = document.getElementById('branch-company-performance-cards');
        if (!container) return;
        const source = Array.isArray(cards) ? cards : [];
        disposeBranchPerformanceCalendarCharts();
        if (source.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-4">暂无子公司绩效考核数据</div>';
            return;
        }
        const interruptCalendarMaxCount = getMaxServiceInterruptCalendarCount(source);
        const cardsWithCalendar = source.map(card => Object.assign({}, card, { interruptCalendarMaxCount }));
        const cardsByProvince = new Map(cardsWithCalendar.map(card => [card.province, card]));
        container.innerHTML = cardsWithCalendar.map(renderBranchCompanyPerformanceCard).join('');
        initBranchPerformanceRuntimeCalendarCharts(container, cardsByProvince);
        initBranchPerformanceInterruptCalendarToggles(container);
        container.querySelectorAll('.statistics-branch-performance-card').forEach(cardEl => {
            const province = cardEl.dataset.province || '';
            const card = cardsWithCalendar.find(item => item.province === province);
            const title = cardEl.querySelector('.service-strip-card-title');
            if (title && card) {
                title.addEventListener('click', () => handleBranchCompanyPerformanceCardClick(card));
            }
            cardEl.querySelectorAll('.branch-performance-deduction').forEach(button => {
                const deduction = (card && Array.isArray(card.deductions))
                    ? card.deductions.find(item => item.key === button.dataset.deductionKey)
                    : null;
                if (card && deduction) {
                    button.addEventListener('click', event => {
                        event.stopPropagation();
                        handleBranchCompanyPerformanceDeductionClick(card, deduction);
                    });
                }
            });
        });
    }

    function handleBranchCompanyPerformanceCardClick(card) {
        handleBranchCompanyChartClick({ name: card.province }, 'province');
    }

    function handleBranchCompanyPerformanceDeductionClick(card, deduction) {
        activeBranchCompanyFilterField = 'province';
        activeBranchCompanyFilterValue = normalizeFilterValue('province', card.province);
        activeBranchCompanyFilterExtraField = null;
        activeBranchCompanyFilterExtraValue = null;
        activeBranchCompanyFilterLabel = `${card.province} ${deduction.label || ''}`;
        if (deduction.key === 'repeat') {
            activeBranchCompanyFilterExtraField = 'is_repeat';
            activeBranchCompanyFilterExtraValue = true;
        } else if (deduction.key === 'severity') {
            activeBranchCompanyFilterExtraField = 'is_long';
            activeBranchCompanyFilterExtraValue = true;
        } else if (deduction.key === 'valid_duration') {
            activeBranchCompanyFilterExtraField = 'is_valid_duration';
            activeBranchCompanyFilterExtraValue = true;
        }
        const tbl = document.getElementById('branch-company-details-tbody');
        if (tbl) {
            tbl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        loadBranchDetails();
    }

    function renderBranchCompanyOverview(branchData, prevBranchData = currentPrevBranchCompanyData) {
        const overview = branchData.overview || {};
        const bareFiber = branchData.bare_fiber_interruption || {};
        const cableBreak = branchData.cable_break_overview || {};
        const prevOverview = (prevBranchData && prevBranchData.overview) || {};
        const prevBareFiber = (prevBranchData && prevBranchData.bare_fiber_interruption) || {};
        const prevCableBreak = (prevBranchData && prevBranchData.cable_break_overview) || {};
        const totalEl = document.getElementById('branch-company-overall-total');
        if (totalEl) totalEl.textContent = formatCardCountValue(overview.total_count || 0);
        renderTrendBesideMetric(totalEl, overview.total_count || 0, prevOverview.total_count, true);
        renderBareFiberInterruption(bareFiber, prevBareFiber, 'branch-barefiber');

        const categoryEl = document.getElementById('branch-company-overall-categories-flex-list');
        if (categoryEl) {
            const categories = (overview.categories || []).map(item => ({
                id: `branch-company-overall-${item.name}`,
                name: item.name,
                value: item.value || 0,
                filterField: 'category',
                filterValue: item.name,
                filterLabel: item.name,
            }));
            categoryEl.innerHTML = buildFlexGroup(categories, '起', '', 'text-indigo', prevOverview.categories || []);
        }

        const otherEl = document.getElementById('branch-company-overall-other-flex-list');
        if (otherEl) {
            const other = overview.other || {};
            const prevOther = prevOverview.other || {};
            const otherItems = [
                { id: 'branch-company-fiber-degradation', name: '光缆劣化', value: other.fiber_degradation || 0, filterField: 'category', filterValue: '光缆劣化', filterLabel: '光缆劣化' },
                { id: 'branch-company-fiber-jitter', name: '光缆抖动', value: other.fiber_jitter || 0, filterField: 'category', filterValue: '光缆抖动', filterLabel: '光缆抖动' },
                { id: 'branch-company-suspended', name: '挂起', value: other.suspended_faults || 0 },
            ];
            const prevOtherItems = [
                { name: '光缆劣化', value: prevOther.fiber_degradation || 0 },
                { name: '光缆抖动', value: prevOther.fiber_jitter || 0 },
                { name: '挂起', value: prevOther.suspended_faults || 0 },
            ];
            otherEl.innerHTML = buildFlexGroup(otherItems, '起', '', 'text-indigo', prevOtherItems);
        }

        const cableBreakTotalEl = document.getElementById('branch-company-cable-break-total-count');
        if (cableBreakTotalEl) cableBreakTotalEl.textContent = formatCardCountValue(cableBreak.total_count || 0);
        renderTrendBesideMetric(cableBreakTotalEl, cableBreak.total_count || 0, prevCableBreak.total_count, true);

        const reasonEl = document.getElementById('branch-company-cable-break-reason-top3-flex-list');
        if (reasonEl) {
            reasonEl.innerHTML = buildFlexGroup((cableBreak.reason_top3 || []).map(item => ({
                ...item,
                filterField: 'reason',
                filterValue: item.name,
                filterLabel: item.name,
            })), '起', '', 'text-indigo', prevCableBreak.reason_top3 || []);
        }

        const durationEl = document.getElementById('branch-company-cable-break-duration-total-list');
        if (durationEl) {
            const metrics = cableBreak.avg_metrics || {};
            const prevMetrics = prevCableBreak.avg_metrics || {};
            const durationItems = [
                { id: 'branch-company-total-duration', name: '总历时', value: cableBreak.total_duration || 0, prevValue: prevCableBreak.total_duration, unit: '小时', filterField: 'category', filterValue: '光缆中断', filterLabel: '中断历时' },
                { id: 'branch-company-overall-avg', name: '全口径平均', value: metrics.overall_avg || 0, prevValue: prevMetrics.overall_avg, unit: '小时', filterField: 'category', filterValue: '光缆中断', filterLabel: '全口径平均' },
                { id: 'branch-company-valid-avg', name: '有效平均', value: metrics.valid_avg || 0, prevValue: prevMetrics.valid_avg, unit: '小时', filterField: 'is_valid_duration', filterValue: 'true', filterLabel: '有效平均' },
                { id: 'branch-company-timeout-rate', name: '超时率', value: metrics.timeout_rate || 0, prevValue: prevMetrics.timeout_rate, unit: '%', filterField: 'duration_min', filterValue: '4', filterLabel: '超时率' },
            ];
            durationEl.innerHTML = buildFlexGroup(durationItems, '', '', 'text-indigo');
        }

        const repeatEl = document.getElementById('branch-company-kpi-repeat-faults');
        if (repeatEl) repeatEl.textContent = formatCardCountValue(cableBreak.repeat_faults_count || 0);
        renderTrendBesideMetric(repeatEl, cableBreak.repeat_faults_count || 0, prevCableBreak.repeat_faults_count, true);
    }

    function getSortedBranchBars(data, metric) {
        return (data || []).slice().sort((a, b) => Number(b[metric] || 0) - Number(a[metric] || 0));
    }

    function buildBranchCompanyGrid(isWeekly = false) {
        return {
            top: isWeekly ? 76 : 52,
            left: 64,
            right: 28,
            bottom: 42,
            containLabel: true
        };
    }

    function buildBranchCompanyYAxis(unit, chartTheme) {
        return {
            type: 'value',
            name: unit,
            nameGap: 16,
            nameLocation: 'end',
            nameTextStyle: {
                color: chartTheme.muted,
                fontWeight: 600,
                align: 'right',
                padding: [0, 0, 4, 0]
            },
            ...buildAxisTheme(chartTheme)
        };
    }

    function getBranchCompanyProvinceColor(name, chartTheme) {
        const colors = {
            '浙江': '#4E79A7',
            '山东': '#F28E2B',
            '内蒙': '#59A14F',
            '陕西': '#B07AA1',
            '四川': '#EDC948',
            '江西': '#9C755F',
        };
        return colors[name] || chartTheme.primary;
    }

    function renderBranchBarChart(chart, data, metric, title, unit, tooltipFormatter = null) {
        if (!chart) return;
        const chartTheme = getChartTheme();
        const sortedData = getSortedBranchBars(data, metric);
        chart.setOption({
            textStyle: { color: chartTheme.text },
            tooltip: {
                ...buildTooltipTheme(chartTheme),
                trigger: 'axis',
                axisPointer: { type: 'shadow', shadowStyle: { color: chartTheme.dark ? 'rgba(110, 168, 254, 0.14)' : 'rgba(32, 107, 196, 0.1)' } },
                formatter: params => {
                    const p = params[0];
                    const raw = p.data || {};
                    if (typeof tooltipFormatter === 'function') {
                        return tooltipFormatter(p, raw);
                    }
                    return `${p.marker || ''}${p.name}<br/>故障数: ${raw._count || 0} 起<br/>故障历时: ${formatCardMetricValue(raw._duration || 0)} 小时<br/>光缆长度: ${formatCardMetricValue(raw._pathLength || 0)} 公里`;
                }
            },
            grid: buildBranchCompanyGrid(),
            xAxis: {
                type: 'category',
                data: sortedData.map(item => item.name),
                ...buildAxisTheme(chartTheme, { interval: 0 })
            },
            yAxis: buildBranchCompanyYAxis(unit, chartTheme),
            series: [{
                name: title,
                type: 'bar',
                barMaxWidth: 34,
                label: {
                    show: true,
                    position: 'top',
                    color: chartTheme.heading,
                    fontWeight: 600,
                    formatter: params => Number(params.value || 0) > 0 ? formatCardMetricValue(params.value) : ''
                },
                data: sortedData.map(item => ({
                    value: Number(item[metric] || 0),
                    _count: item.value || 0,
                    _duration: item.duration || 0,
                    _validDurationTotal: item.valid_duration_total || 0,
                    _validCount: item.valid_count || 0,
                    _pathLength: item.path_length || 0,
                    itemStyle: { color: getBranchCompanyProvinceColor(item.name, chartTheme), borderRadius: [4, 4, 0, 0] },
                }))
            }]
        });
    }

    function renderBranchCompanyBarCharts(branchData) {
        const countMetric = getCheckedValue('branchCompanyCountMetric', 'count');
        const durationMetric = getCheckedValue('branchCompanyDurationMetric', 'duration');
        renderBranchBarChart(
            chartBranchCompanyCount,
            branchData.province_bars || [],
            countMetric,
            countMetric === 'count' ? '故障数' : '千公里故障数',
            countMetric === 'count' ? '起' : '起/千公里'
        );
        renderBranchBarChart(
            chartBranchCompanyDuration,
            branchData.province_bars || [],
            durationMetric,
            durationMetric === 'duration' ? '故障历时' : '千公里故障历时',
            durationMetric === 'duration' ? '小时' : '小时/千公里'
        );
    }

    function renderBranchCompanyBoxplot(branchData) {
        if (!chartBranchCompanyBoxplot) return;
        const chartTheme = getChartTheme();
        const metric = 'duration';
        const boxplotData = (branchData.duration_boxplot || []).map(item => ({
            name: item.name,
            value: item.value || [],
        }));
        chartBranchCompanyBoxplot.setOption({
            textStyle: { color: chartTheme.text },
            tooltip: {
                ...buildTooltipTheme(chartTheme),
                trigger: 'axis',
                axisPointer: { type: 'shadow', shadowStyle: { color: chartTheme.dark ? 'rgba(110, 168, 254, 0.14)' : 'rgba(32, 107, 196, 0.1)' } },
                formatter: params => {
                    const p = Array.isArray(params) ? params[0] : params;
                    const value = Array.isArray(p.data) ? p.data : (p.data && p.data.value) || [];
                    return `${p.name}<br/>最小: ${formatCardMetricValue(value[0] || 0)}<br/>Q1: ${formatCardMetricValue(value[1] || 0)}<br/>中位: ${formatCardMetricValue(value[2] || 0)}<br/>Q3: ${formatCardMetricValue(value[3] || 0)}<br/>上须: ${formatCardMetricValue(value[4] || 0)}`;
                }
            },
            grid: buildBranchCompanyGrid(),
            xAxis: {
                type: 'category',
                data: boxplotData.map(item => item.name),
                ...buildAxisTheme(chartTheme, { interval: 0 })
            },
            yAxis: buildBranchCompanyYAxis('小时', chartTheme),
            series: [{
                name: '中断时长分布',
                type: 'boxplot',
                boxWidth: ['22%', '58%'],
                itemStyle: { color: chartTheme.surface, borderColor: chartTheme.primary },
                data: boxplotData.map(item => item.value)
            }]
        });
    }

    function renderBranchCompanyValidDurationChart(branchData) {
        const metric = 'valid_duration';
        renderBranchBarChart(
            chartBranchCompanyValidDuration,
            branchData.valid_duration_bars || [],
            metric,
            '有效平均历时',
            '小时',
            (p, raw) => `${p.marker || ''}${p.name}<br/>有效平均历时: ${formatCardMetricValue(p.value || 0)} 小时<br/>有效故障数: ${raw._validCount || 0} 起<br/>有效总历时: ${formatCardMetricValue(raw._validDurationTotal || 0)} 小时<br/>光缆长度: ${formatCardMetricValue(raw._pathLength || 0)} 公里`
        );
    }

    function syncBranchCompanyWeeklyScaleAvailability() {
        const weeklyScaleRaw = document.getElementById('branch-company-weekly-scale-raw');
        const weeklyScaleNormalized = document.getElementById('branch-company-weekly-scale-normalized');
        const weeklyScaleNormalizedLabel = document.querySelector('label[for="branch-company-weekly-scale-normalized"]');
        if (!weeklyScaleRaw || !weeklyScaleNormalized) return;

        const isValidDuration = getCheckedValue('branchCompanyWeeklyMetric', 'count') === 'valid_duration';
        if (isValidDuration && weeklyScaleNormalized.checked) {
            weeklyScaleRaw.checked = true;
        }
        weeklyScaleNormalized.disabled = isValidDuration;
        weeklyScaleNormalized.setAttribute('aria-disabled', isValidDuration ? 'true' : 'false');
        if (weeklyScaleNormalizedLabel) {
            weeklyScaleNormalizedLabel.classList.toggle('disabled', isValidDuration);
            weeklyScaleNormalizedLabel.setAttribute(
                'title',
                isValidDuration ? '有效时长不支持千公里统计' : ''
            );
        }
    }

    function formatBranchCompanyWeekMonthTick(value, index, labels) {
        const monthNames = [
            '一月', '二月', '三月', '四月', '五月', '六月',
            '七月', '八月', '九月', '十月', '十一月', '十二月'
        ];
        const match = String(value || '').match(/^(\d{1,2})\//);
        if (!match) return index === 0 ? value : '';

        const currentMonth = Number(match[1]);
        const previousValue = index > 0 ? labels[index - 1] : '';
        const previousMatch = String(previousValue || '').match(/^(\d{1,2})\//);
        const previousMonth = previousMatch ? Number(previousMatch[1]) : null;
        if (index === 0 || currentMonth !== previousMonth) {
            return monthNames[currentMonth - 1] || value;
        }
        return '';
    }

    function renderBranchCompanyWeeklyChart(branchData) {
        if (!chartBranchCompanyWeekly) return;
        const chartTheme = getChartTheme();
        syncBranchCompanyWeeklyScaleAvailability();
        const metric = getCheckedValue('branchCompanyWeeklyMetric', 'count');
        const scale = getCheckedValue('branchCompanyWeeklyScale', 'raw');
        const weeklyData = branchData.weekly_trends || {};
        const labels = weeklyData.labels || [];
        const metricKey = scale === 'per_1000km'
            ? (metric === 'count' ? 'week_count_per_1000km' : metric === 'duration' ? 'week_duration_per_1000km' : 'week_valid_duration_per_1000km')
            : (metric === 'count' ? 'counts' : metric === 'duration' ? 'durations' : 'valid_durations');
        const unit = scale === 'per_1000km'
            ? (metric === 'count' ? '起/千公里' : '小时/千公里')
            : (metric === 'count' ? '起' : '小时');
        chartBranchCompanyWeekly.setOption({
            textStyle: { color: chartTheme.text },
            tooltip: {
                ...buildTooltipTheme(chartTheme),
                trigger: 'axis'
            },
            legend: {
                top: 8,
                left: 'center',
                ...buildLegendTheme(chartTheme)
            },
            grid: buildBranchCompanyGrid(true),
            xAxis: {
                type: 'category',
                data: labels,
                boundaryGap: false,
                ...buildAxisTheme(chartTheme, {
                    interval: 0,
                    rotate: 0,
                    formatter: (value, index) => formatBranchCompanyWeekMonthTick(value, index, labels)
                })
            },
            yAxis: buildBranchCompanyYAxis(unit, chartTheme),
            series: (weeklyData.series || []).map(item => {
                const lineColor = getBranchCompanyProvinceColor(item.name, chartTheme);
                return {
                    name: item.name,
                    type: 'line',
                    smooth: true,
                    symbol: 'circle',
                    symbolSize: 4,
                    itemStyle: { color: lineColor },
                    lineStyle: { width: 2, color: lineColor },
                    data: item[metricKey] || []
                };
            })
        });
    }

    function renderBranchCompanyMonthlyChart(branchData) {
        if (!chartBranchCompanyMonthly) return;
        const chartTheme = getChartTheme();
        syncBranchCompanyWeeklyScaleAvailability();
        const metric = getCheckedValue('branchCompanyWeeklyMetric', 'count');
        const scale = getCheckedValue('branchCompanyWeeklyScale', 'raw');
        const monthlyData = branchData.monthly_trends || {};
        const labels = monthlyData.labels || [];
        const metricKey = scale === 'per_1000km'
            ? (metric === 'count' ? 'month_count_per_1000km' : metric === 'duration' ? 'month_duration_per_1000km' : 'month_valid_duration_per_1000km')
            : (metric === 'count' ? 'counts' : metric === 'duration' ? 'durations' : 'valid_durations');
        const unit = scale === 'per_1000km'
            ? (metric === 'count' ? '起/千公里' : '小时/千公里')
            : (metric === 'count' ? '起' : '小时');
        chartBranchCompanyMonthly.setOption({
            textStyle: { color: chartTheme.text },
            tooltip: {
                ...buildTooltipTheme(chartTheme),
                trigger: 'axis',
                axisPointer: { type: 'shadow', shadowStyle: { color: chartTheme.dark ? 'rgba(110, 168, 254, 0.14)' : 'rgba(32, 107, 196, 0.1)' } }
            },
            legend: {
                top: 8,
                left: 'center',
                ...buildLegendTheme(chartTheme)
            },
            grid: buildBranchCompanyGrid(true),
            xAxis: {
                type: 'category',
                data: labels,
                ...buildAxisTheme(chartTheme, {
                    interval: 0,
                    rotate: 0
                })
            },
            yAxis: buildBranchCompanyYAxis(unit, chartTheme),
            series: (monthlyData.series || []).map(item => {
                const barColor = getBranchCompanyProvinceColor(item.name, chartTheme);
                return {
                    name: item.name,
                    type: 'bar',
                    barMaxWidth: 18,
                    itemStyle: { color: barColor, borderRadius: [3, 3, 0, 0] },
                    data: item[metricKey] || []
                };
            })
        });
    }

    // ---------------- 渲染下钻表格 ----------------
    function normalizeFilterValue(fieldName, value) {
        if (value === 'true') return true;
        if (value === 'false') return false;
        return value;
    }

    function applyDetailFilter(item, fieldName, value) {
        if (fieldName === 'province') {
            return item[fieldName] === value || normalizeBranchCompanyProvince(item[fieldName]) === normalizeBranchCompanyProvince(value);
        }
        if (fieldName === 'duration_min') {
            return Number(item.duration || 0) >= Number(value || 0);
        }
        if (fieldName === 'duration_max') {
            return Number(item.duration || 0) <= Number(value || 0);
        }
        return item[fieldName] === value;
    }

    function assignRepeatGroupColors(items) {
        const parseTime = (str) => new Date(str.replace(/-/g, '/'));
        items.forEach(item => { item.repeatGroupClass = ''; });
        
        let repeatItems = items.filter(item => item.is_repeat);
        if (repeatItems.length === 0) return;
        
        const isRepeatMatch = (a, b) => {
            if (a.site_a !== b.site_a) return false;
            const zA = a.site_z.split(',').map(s => s.trim()).filter(Boolean);
            const zB = b.site_z.split(',').map(s => s.trim()).filter(Boolean);
            const hasOverlap = zA.some(z => zB.includes(z));
            if (!hasOverlap) return false;
            const diffMs = Math.abs(parseTime(a.fault_occurrence_time) - parseTime(b.fault_occurrence_time));
            return diffMs <= 60 * 24 * 60 * 60 * 1000;
        };
        
        let groups = [];
        for (let item of repeatItems) {
            let foundGroup = null;
            for (let g of groups) {
                if (g.some(member => isRepeatMatch(member, item))) {
                    foundGroup = g;
                    break;
                }
            }
            if (foundGroup) {
                foundGroup.push(item);
            } else {
                groups.push([item]);
            }
        }
        
        let colorIndex = 0;
        for (let g of groups) {
            if (g.length > 1) {
                const colorClass = `repeat-group-color-${colorIndex % 6}`;
                colorIndex++;
                g.forEach(item => {
                    item.repeatGroupClass = colorClass;
                });
            }
        }
    }

    function sortDetailRows(details, sortMode) {
        const parseTime = (str) => new Date(str.replace(/-/g, '/'));
        if (sortMode === 'time') {
            return details
                .filter(item => item.in_period !== false)
                .sort((a, b) => parseTime(b.fault_occurrence_time) - parseTime(a.fault_occurrence_time));
        }
        if (sortMode !== 'repeat') {
            return details;
        }

        const itemsForSort = [...details];
        itemsForSort.sort((a, b) => parseTime(b.fault_occurrence_time) - parseTime(a.fault_occurrence_time));

        const isRepeatMatch = (a, b) => {
            if (a.site_a !== b.site_a) return false;
            const zA = a.site_z.split(',').map(s => s.trim()).filter(Boolean);
            const zB = b.site_z.split(',').map(s => s.trim()).filter(Boolean);
            const hasOverlap = zA.some(z => zB.includes(z));
            if (!hasOverlap) return false;
            const diffMs = Math.abs(parseTime(a.fault_occurrence_time) - parseTime(b.fault_occurrence_time));
            return diffMs <= 60 * 24 * 60 * 60 * 1000;
        };

        const groups = [];
        for (const item of itemsForSort) {
            if (item.is_repeat) {
                let foundGroup = null;
                for (const group of groups) {
                    if (group.some(member => isRepeatMatch(member, item))) {
                        foundGroup = group;
                        break;
                    }
                }
                if (foundGroup) {
                    foundGroup.push(item);
                } else {
                    groups.push([item]);
                }
            } else {
                groups.push([item]);
            }
        }

        groups.forEach(group => {
            group.sort((a, b) => parseTime(b.fault_occurrence_time) - parseTime(a.fault_occurrence_time));
        });
        groups.sort((g1, g2) => parseTime(g2[0].fault_occurrence_time) - parseTime(g1[0].fault_occurrence_time));
        return groups.flat();
    }

    async function loadFaultDetails() {
        let url = `${window.STATISTICS_DETAILS_API}?${buildTimeParams()}&ordering=${faultOrdering}`;
        url += buildPhysicalProvinceParams();

        if (activeFilterField && activeFilterValue !== null) {
            url += `&${activeFilterField}=${encodeURIComponent(activeFilterValue)}`;
            if (activeFilterExtraField && activeFilterExtraValue !== null) {
                url += `&${activeFilterExtraField}=${encodeURIComponent(activeFilterExtraValue)}`;
            }
        }
        const tbody = document.getElementById('details-tbody');
        tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4">加载中...</td></tr>';

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Network response error');
            const data = await response.json();
            currentAllDetails = data.results || [];
            renderDetailsTable();
        } catch (error) {
            console.error('Fetch details error:', error);
            tbody.innerHTML = '<tr><td colspan="10" class="text-danger text-center py-4">数据加载失败，请检查网络或刷新重试</td></tr>';
        }
    }

    function updateFaultFilterBadgeAndSummary(filteredDetails) {
        let activeConditions = [];
        if (excludedCategories.resource_type.size > 0) {
            activeConditions.push(`排除光缆属性[${Array.from(excludedCategories.resource_type).join(', ')}]`);
        }
        if (excludedCategories.province.size > 0) {
            activeConditions.push(`排除省份[${Array.from(excludedCategories.province).join(', ')}]`);
        }
        if (excludedCategories.reason.size > 0) {
            activeConditions.push(`排除原因[${Array.from(excludedCategories.reason).join(', ')}]`);
        }

        if (activeFilterField && activeFilterValue !== null) {
            let filterName = '';
            let filterValueDisp = activeFilterLabel || activeFilterValue;
            if (activeFilterField === 'resource_type') filterName = '光缆属性';
            else if (activeFilterField === 'source_group') filterName = '光缆属性';
            else if (activeFilterField === 'province') filterName = '省份';
            else if (activeFilterField === 'reason') filterName = '原因';
            else if (activeFilterField === 'duration_bucket') filterName = '历时分布';
            else if (activeFilterField === 'duration_max') { filterName = '历时指标'; filterValueDisp = `<=${formatCardMetricValue(activeFilterValue)}小时`; }
            else if (activeFilterField === 'duration_min') { filterName = '历时指标'; filterValueDisp = `>=${formatCardMetricValue(activeFilterValue)}小时`; }
            else if (activeFilterField === 'duration_histogram_bucket') filterName = '故障历时频数';
            else if (activeFilterField === 'category') filterName = '分类';
            else if (activeFilterField === 'occurrence_period') filterName = '发生时段';
            else if (activeFilterField === 'cause_group') filterName = '成因';
            else if (activeFilterField === 'is_valid_duration') { filterName = '特殊标签'; filterValueDisp = '有效平均'; }
            else if (activeFilterField === 'is_long') { filterName = '特殊标签'; filterValueDisp = '长时故障(≥6h)'; }
            else if (activeFilterField === 'is_repeat') { filterName = '特殊标签'; filterValueDisp = '历史重复故障'; }
            else if (activeFilterField === 'impact_level') {
                filterName = '影响程度';
                if (activeFilterValue === 'total') filterValueDisp = '总次数';
                else if (activeFilterValue === 'class_i_ii') filterValueDisp = 'I类和II类';
                else if (activeFilterValue === 'class_i') filterValueDisp = 'I类';
                else if (activeFilterValue === 'class_ii') filterValueDisp = 'II类';
                else if (activeFilterValue === 'class_iii') filterValueDisp = 'III类';
                else if (activeFilterValue === 'class_iv') filterValueDisp = 'IV类';
                else if (activeFilterValue === 'class_v') filterValueDisp = 'V类';
            }

            activeConditions.push(`下钻：${filterName}=${filterValueDisp}`);
            if (activeFilterExtraField === 'is_valid_duration' && activeFilterExtraValue === true) {
                activeConditions.push('附加：有效历时>30分钟');
            }
        }

        const summaryDiv = document.getElementById('filtered-kpi-summary');
        if (activeConditions.length > 0) {
            const conditionsText = activeConditions.join(' | ');
            badgeFilter.textContent = conditionsText;
            badgeFilter.className = 'badge bg-primary text-white ms-2';
            badgeFilter.style.display = 'inline-block';
            btnClearFilter.style.display = 'inline-block';
            const inPeriodDetails = filteredDetails.filter(item => item.in_period !== false);
            const totalDuration = inPeriodDetails.reduce((sum, item) => sum + Number(item.duration || 0), 0);
            const averageDuration = inPeriodDetails.length > 0 ? totalDuration / inPeriodDetails.length : 0;
            const longCount = inPeriodDetails.filter(item => item.is_long).length;
            const repeatCount = inPeriodDetails.filter(item => item.is_repeat).length;
            summaryDiv.innerHTML = `<div><i class="mdi mdi-filter-outline me-1"></i> <strong>当期过滤条件：${conditionsText}</strong> 的局部统计：共发生故障 <strong class="text-primary">${inPeriodDetails.length}</strong> 次，累计时长 <strong class="text-primary">${totalDuration.toFixed(2)}</strong> 小时，平均故障时长 <strong class="text-primary">${averageDuration.toFixed(2)}</strong> 小时。其中长时故障（≥6h） <strong class="text-warning text-dark">${longCount}</strong> 条，涉及历史重复故障 <strong class="text-purple">${repeatCount}</strong> 条。</div>`;
            summaryDiv.classList.remove('d-none');
        } else {
            badgeFilter.style.display = 'none';
            btnClearFilter.style.display = 'none';
            summaryDiv.classList.add('d-none');
        }
    }

    function getImpactLevelBadge(level) {
        if (!level) return '—';
        return `<span class="badge bg-indigo text-white" style="color: #fff !important;">${level}</span>`;
    }

    function renderDetailsTableHtml(results) {
        const tbody = document.getElementById('details-tbody');
        if (results.length === 0) {
            tbody.innerHTML = `<tr><td colspan="11" class="text-center py-4 text-muted">包含过滤条件下，无可展示的故障数据</td></tr>`;
            return;
        }

        assignRepeatGroupColors(results);

        const html = results.map(item => {
            let badges = '';
            if (item.is_repeat) {
                badges += `<span class="badge bg-purple text-white ms-1 show-repeats-btn" data-fault-id="${item.id}" style="cursor:pointer;" title="点击查看关联重复故障">重复</span>`;
            }
            if (item.is_long) badges += '<span class="badge bg-warning text-dark ms-1">≥6h</span>';
            
            const trClassList = [];
            if (item.in_period === false) trClassList.push('statistics-preceding-fault-row');
            if (item.repeatGroupClass) trClassList.push(item.repeatGroupClass);
            const trClass = trClassList.length > 0 ? `class="${trClassList.join(' ')}"` : '';

            return `<tr ${trClass}>
                <td><a href="${item.url}" target="_blank">${item.fault_number}</a></td>
                <td>${item.fault_occurrence_time}</td>
                <td>${item.fault_recovery_time}</td>
                <td><strong class="${item.is_long ? 'text-danger' : ''}">${item.duration}</strong></td>
                <td>${item.category}</td>
                <td>${getImpactLevelBadge(item.impact_level)}</td>
                <td>${item.resource_type}</td>
                <td>${item.province}</td>
                <td>${item.reason}</td>
                <td><small>${item.site_a}${item.site_z ? ' &rarr; ' + item.site_z : ''}</small></td>
                <td>${badges}</td>
            </tr>`;
        }).join('');
        tbody.innerHTML = html;

        tbody.querySelectorAll('.show-repeats-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                showFaultRepeatsModal(btn.dataset.faultId);
            });
        });
    }

    function renderDetailsTable() {
        let filteredDetails = currentAllDetails.slice();
        if (excludedCategories.resource_type.size > 0) {
            filteredDetails = filteredDetails.filter(item => !excludedCategories.resource_type.has(item.resource_type));
        }
        if (excludedCategories.province.size > 0) {
            filteredDetails = filteredDetails.filter(item => !excludedCategories.province.has(item.province));
        }
        if (excludedCategories.reason.size > 0) {
            filteredDetails = filteredDetails.filter(item => !excludedCategories.reason.has(item.reason));
        }
        const sortMode = document.querySelector('input[name="detailSortMode"]:checked')?.value || 'time';
        assignRepeatGroupColors(filteredDetails);
        filteredDetails = sortDetailRows(filteredDetails, sortMode);
        updateFaultFilterBadgeAndSummary(filteredDetails);
        renderDetailsTableHtml(filteredDetails);
    }

    function renderDetailRows(details, emptyText) {
        if (details.length === 0) {
            return `<tr><td colspan="11" class="text-center py-4 text-muted">${emptyText}</td></tr>`;
        }

        assignRepeatGroupColors(details);

        return details.map(item => {
            let badges = '';
            if (item.is_repeat) {
                badges += `<span class="badge bg-purple text-white ms-1 show-repeats-btn" data-fault-id="${item.id}" style="cursor:pointer;" title="点击查看关联重复故障">重复</span>`;
            }
            if (item.is_long) badges += '<span class="badge bg-warning text-dark ms-1">≥6h</span>';
            
            const trClassList = [];
            if (item.in_period === false) trClassList.push('statistics-preceding-fault-row');
            if (item.repeatGroupClass) trClassList.push(item.repeatGroupClass);
            const trClass = trClassList.length > 0 ? `class="${trClassList.join(' ')}"` : '';

            return `<tr ${trClass}>
                <td><a href="${item.url}" target="_blank">${item.fault_number}</a></td>
                <td>${item.fault_occurrence_time}</td>
                <td>${item.fault_recovery_time}</td>
                <td><strong class="${item.is_long ? 'text-danger' : ''}">${item.duration}</strong></td>
                <td>${item.category}</td>
                <td>${getImpactLevelBadge(item.impact_level)}</td>
                <td>${item.resource_type}</td>
                <td>${item.province}</td>
                <td>${item.reason}</td>
                <td><small>${item.site_a}${item.site_z ? ' &rarr; ' + item.site_z : ''}</small></td>
                <td>${badges}</td>
            </tr>`;
        }).join('');
    }

    async function loadBranchDetails() {
        let url = `${window.STATISTICS_DETAILS_API}?${buildTimeParams()}&ordering=${branchOrdering}&scope=branch_company`;

        if (activeBranchCompanyFilterField && activeBranchCompanyFilterValue !== null) {
            url += `&${activeBranchCompanyFilterField}=${encodeURIComponent(activeBranchCompanyFilterValue)}`;
            if (activeBranchCompanyFilterExtraField && activeBranchCompanyFilterExtraValue !== null) {
                url += `&${activeBranchCompanyFilterExtraField}=${encodeURIComponent(activeBranchCompanyFilterExtraValue)}`;
            }
        }

        const tbody = document.getElementById('branch-company-details-tbody');
        tbody.innerHTML = '<tr><td colspan="11" class="text-center py-4">加载中...</td></tr>';

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Network response error');
            const data = await response.json();
            currentBranchCompanyDetails = data.results || [];
            renderBranchCompanyDetailsTable();
        } catch (error) {
            console.error('Fetch branch details error:', error);
            tbody.innerHTML = '<tr><td colspan="11" class="text-danger text-center py-4">数据加载失败，请检查网络或刷新重试</td></tr>';
        }
    }

    function updateBranchFilterBadgeAndSummary(filteredDetails) {
        let activeConditions = [];
        const badge = document.getElementById('branch-company-drill-down-filter-badge');
        const clearButton = document.getElementById('branch-company-btn-clear-filter');
        const summaryDiv = document.getElementById('branch-company-filtered-kpi-summary');

        if (activeBranchCompanyFilterField && activeBranchCompanyFilterValue !== null) {
            let filterName = '';
            let filterValueDisp = activeBranchCompanyFilterLabel || activeBranchCompanyFilterValue;
            if (activeBranchCompanyFilterField === 'province') filterName = '省份';
            else if (activeBranchCompanyFilterField === 'category') filterName = '分类';
            else if (activeBranchCompanyFilterField === 'reason') filterName = '原因';
            else if (activeBranchCompanyFilterField === 'is_valid_duration') { filterName = '特殊标签'; filterValueDisp = '有效平均'; }
            else if (activeBranchCompanyFilterField === 'is_long') { filterName = '特殊标签'; filterValueDisp = '长时故障(≥6h)'; }
            else filterName = activeBranchCompanyFilterField;
            activeConditions.push(`下钻：${filterName}=${filterValueDisp}`);
        }

        if (activeConditions.length > 0) {
            const conditionsText = activeConditions.join(' | ');
            if (badge) {
                badge.textContent = conditionsText;
                badge.className = 'badge bg-primary text-white ms-2';
                badge.style.display = 'inline-block';
            }
            if (clearButton) clearButton.style.display = 'inline-block';
            if (summaryDiv) {
                const inPeriodDetails = filteredDetails.filter(item => item.in_period !== false);
                const totalDuration = inPeriodDetails.reduce((sum, item) => sum + Number(item.duration || 0), 0);
                const averageDuration = inPeriodDetails.length > 0 ? totalDuration / inPeriodDetails.length : 0;
                const longCount = inPeriodDetails.filter(item => item.is_long).length;
                const repeatCount = inPeriodDetails.filter(item => item.is_repeat).length;
                summaryDiv.innerHTML = `<div><i class="mdi mdi-filter-outline me-1"></i> <strong>当前过滤条件：${conditionsText}</strong> 的局部统计：共发生故障 <strong class="text-primary">${inPeriodDetails.length}</strong> 次，累计时长 <strong class="text-primary">${totalDuration.toFixed(2)}</strong> 小时，平均故障时长 <strong class="text-primary">${averageDuration.toFixed(2)}</strong> 小时。其中长时故障（≥6h） <strong class="text-warning text-dark">${longCount}</strong> 条，涉及历史重复故障 <strong class="text-purple">${repeatCount}</strong> 条。</div>`;
                summaryDiv.classList.remove('d-none');
            }
        } else {
            if (badge) badge.style.display = 'none';
            if (clearButton) clearButton.style.display = 'none';
            if (summaryDiv) summaryDiv.classList.add('d-none');
        }
    }

    function renderBranchDetailsTableHtml(results) {
        const tbody = document.getElementById('branch-company-details-tbody');
        tbody.innerHTML = renderDetailRows(results, '当前子公司范围及过滤条件下，无可展示的故障数据');
        
        tbody.querySelectorAll('.show-repeats-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                showFaultRepeatsModal(btn.dataset.faultId);
            });
        });
    }

    function renderBranchCompanyDetailsTable() {
        let filteredDetails = currentBranchCompanyDetails.slice();
        const sortMode = document.querySelector('input[name="branchCompanyDetailSortMode"]:checked')?.value || 'time';
        assignRepeatGroupColors(filteredDetails);
        filteredDetails = sortDetailRows(filteredDetails, sortMode);
        updateBranchFilterBadgeAndSummary(filteredDetails);
        renderBranchDetailsTableHtml(filteredDetails);
    }

    function formatPieSliceLabel(params) {
        if (!params.value) return params.name;
        return `${params.name}\n${params.value}次 ${params.percent}%`;
    }

    function formatLegendMetricLabel(name, dataByName, total) {
        const item = dataByName.get(name);
        if (!item) return name;
        const percent = total > 0 ? ((item.value / total) * 100).toFixed(2) : "0.00";
        return `${name}  ${item.value}次 ${percent}%`;
    }

    // ---------------- 下钻事件处理 ----------------
    function handleChartClick(params, fieldName) {
        if (!params.name) return;
        activeFilterField = fieldName;
        activeFilterValue = params.name;
        activeFilterExtraField = null;
        activeFilterExtraValue = null;
        activeFilterLabel = null;
        
        const timeRadio = document.getElementById('detail-sort-time');
        if (timeRadio) {
            timeRadio.checked = true;
        }

        // 滚动到下方的表格
        const tbl = document.getElementById('details-tbody');
        if (tbl) {
            tbl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        loadFaultDetails();
    }

    function handleMetricFilterClick(metric) {
        const fieldName = metric.dataset.filterField;
        if (!fieldName) return;

        activeFilterField = fieldName;
        activeFilterValue = normalizeFilterValue(fieldName, metric.dataset.filterValue);
        activeFilterExtraField = metric.dataset.filterExtraField || null;
        activeFilterExtraValue = activeFilterExtraField
            ? normalizeFilterValue(activeFilterExtraField, metric.dataset.filterExtraValue)
            : null;
        activeFilterLabel = metric.dataset.filterLabel || metric.dataset.filterValue;

        const timeRadio = document.getElementById('detail-sort-time');
        if (timeRadio) {
            timeRadio.checked = true;
        }

        const tbl = document.getElementById('details-tbody');
        if (tbl) {
            tbl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        loadFaultDetails();
    }

    function handleBranchCompanyChartClick(params, fieldName) {
        const name = params && params.name ? params.name : null;
        if (!name) return;
        activeBranchCompanyFilterField = fieldName;
        activeBranchCompanyFilterValue = name;
        activeBranchCompanyFilterExtraField = null;
        activeBranchCompanyFilterExtraValue = null;
        activeBranchCompanyFilterLabel = null;
        const timeRadio = document.getElementById('branch-company-detail-sort-time');
        if (timeRadio) {
            timeRadio.checked = true;
        }
        const tbl = document.getElementById('branch-company-details-tbody');
        if (tbl) {
            tbl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        loadBranchDetails();
    }

    function handleBranchCompanyMetricFilterClick(metric) {
        const fieldName = metric.dataset.filterField;
        if (!fieldName) return;

        activeBranchCompanyFilterField = fieldName;
        activeBranchCompanyFilterValue = normalizeFilterValue(fieldName, metric.dataset.filterValue);
        activeBranchCompanyFilterExtraField = metric.dataset.filterExtraField || null;
        activeBranchCompanyFilterExtraValue = activeBranchCompanyFilterExtraField
            ? normalizeFilterValue(activeBranchCompanyFilterExtraField, metric.dataset.filterExtraValue)
            : null;
        activeBranchCompanyFilterLabel = metric.dataset.filterLabel || metric.dataset.filterValue;
        const timeRadio = document.getElementById('branch-company-detail-sort-time');
        if (timeRadio) {
            timeRadio.checked = true;
        }

        const tbl = document.getElementById('branch-company-details-tbody');
        if (tbl) {
            tbl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        loadBranchDetails();
    }

    // ---------------- 清除过滤 ----------------
    btnClearFilter.addEventListener('click', () => {
        activeFilterField = null;
        activeFilterValue = null;
        activeFilterExtraField = null;
        activeFilterExtraValue = null;
        activeFilterLabel = null;
        
        excludedCategories.resource_type.clear();
        excludedCategories.province.clear();
        excludedCategories.reason.clear();
        
        chartResource.dispatchAction({ type: 'legendAllSelect' });
        chartReason.dispatchAction({ type: 'legendAllSelect' });
        
        loadFaultDetails();
    });

    const btnClearBranchCompanyFilter = document.getElementById('branch-company-btn-clear-filter');
    if (btnClearBranchCompanyFilter) {
        btnClearBranchCompanyFilter.addEventListener('click', () => {
            activeBranchCompanyFilterField = null;
            activeBranchCompanyFilterValue = null;
            activeBranchCompanyFilterExtraField = null;
            activeBranchCompanyFilterExtraValue = null;
            activeBranchCompanyFilterLabel = null;
            loadBranchDetails();
        });
    }

    // ---------------- 业务故障统计 ----------------
    let serviceDataLoaded = false;
    let currentServiceDetails = [];
    let activeServiceDetailFilterKey = null;
    let activeServiceDetailFilterName = null;
    let activeServiceDetailFilterType = null;
    let serviceCalendarCharts = [];
    let currentBareFiberServices = [];
    let bareFiberServiceCardScope = 'faulted';
    let bareFiberAllServicesLoaded = false;
    let serviceDataRequestSequence = 0;

    async function loadServiceData({ includeAllBareFiber = false } = {}) {
        const requestSequence = ++serviceDataRequestSequence;
        const preserveExistingCards = includeAllBareFiber && currentBareFiberServices.length > 0;
        if (!preserveExistingCards) {
            disposeServiceCalendarCharts();
            setServiceCardsLoading('service-cards-container');
            setServiceCardsLoading('circuit-service-cards-container');
            setServiceDetailsLoading('service-details-tbody');
            setServiceDetailsLoading('circuit-service-details-tbody');
        }

        const selectedDateParts = inputDate.value.split('-').map(Number);
        let url = `${window.SERVICE_STATISTICS_DATA_API}?${buildTimeParams()}&calendar_year=${selectedDateParts[0]}&calendar_month=${selectedDateParts[1]}`;
        if (includeAllBareFiber) url += '&include_all_bare_fiber=1';

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Network response error');
            const data = await response.json();
            if (requestSequence !== serviceDataRequestSequence) return;

            if (data.period && data.period.start) {
                const periodEl = document.getElementById('period-display');
                periodEl.innerHTML = formatStatisticsPeriodLabel(selFilterType.value, inputDate.value, data.period);
                updatePeriodLabelState(periodEl, data.period);
            }

            const services = data.services || [];
            activeServiceDetailFilterKey = null;
            activeServiceDetailFilterName = null;
            activeServiceDetailFilterType = null;
            currentBareFiberServices = getServicesByType(services, '裸纤业务');
            bareFiberAllServicesLoaded = includeAllBareFiber;
            renderBareFiberServiceCards();
            renderServiceCards(getServicesByType(services, '电路业务'), 'circuit-service-cards-container', '电路业务');

            loadServiceDetails('裸纤业务', serviceOrdering, 'service-details-tbody', 'service-detail-filter-badge', 'btn-clear-service-detail-filter');
            loadServiceDetails('电路业务', circuitOrdering, 'circuit-service-details-tbody', 'circuit-service-detail-filter-badge', 'btn-clear-circuit-service-detail-filter');

            serviceDataLoaded = true;
        } catch (error) {
            if (requestSequence !== serviceDataRequestSequence) return;
            console.error('Service data fetch error:', error);
            if (!preserveExistingCards) {
                setServiceCardsError('service-cards-container');
                setServiceCardsError('circuit-service-cards-container');
                setServiceDetailsError('service-details-tbody');
                setServiceDetailsError('circuit-service-details-tbody');
            }
        }
    }

    function setServiceCardsLoading(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = '<div class="col-12 text-center text-muted py-5"><i class="mdi mdi-loading mdi-spin me-1"></i> 数据加载中...</div>';
    }

    function setServiceCardsError(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = '<div class="col-12 text-center text-danger py-5">数据加载失败，请检查网络或刷新重试</div>';
    }

    function setServiceDetailsLoading(tbodyId) {
        const tbody = document.getElementById(tbodyId);
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">数据加载中...</td></tr>';
    }

    function setServiceDetailsError(tbodyId) {
        const tbody = document.getElementById(tbodyId);
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="8" class="text-danger text-center py-4">数据加载失败，请检查网络或刷新重试</td></tr>';
    }

    function getServicesByType(services, serviceType) {
        return services.filter(svc => svc.type === serviceType);
    }

    function serviceHasCurrentPeriodFaults(svc) {
        return Number(svc && svc.count || 0) > 0;
    }

    function getVisibleBareFiberServices() {
        if (bareFiberServiceCardScope === 'all') {
            return currentBareFiberServices;
        }
        return currentBareFiberServices.filter(serviceHasCurrentPeriodFaults);
    }

    function renderBareFiberServiceCards() {
        disposeServiceCalendarCharts();
        renderServiceCards(getVisibleBareFiberServices(), 'service-cards-container', '裸纤业务');
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function renderStripMetric(metric) {
        const valueClass = metric.valueClass || 'text-indigo';
        const valueText = isCountUnit(metric.unit) ? formatCardCountValue(metric.value) : formatCardMetricValue(metric.value);
        const valueStyle = metric.color ? ` style="color:${metric.color};"` : '';
        const unitHtml = metric.unit ? `<span class="statistics-strip-card-unit">${metric.unit}</span>` : '';
        const detailHtml = metric.detail ? `<div class="statistics-strip-card-detail">${metric.detail}</div>` : '';
        return `
            <div class="statistics-strip-card-metric">
                <div class="statistics-strip-card-label">${metric.label}</div>
                <div class="statistics-strip-card-value-row">
                    <span class="statistics-strip-card-value ${valueClass}"${valueStyle}>${valueText}</span>
                    ${unitHtml}
                </div>
                ${detailHtml}
            </div>`;
    }

    function renderServiceAnnualSummary(svc) {
        const annualSummary = svc && svc.annual_summary ? svc.annual_summary : {};
        const annualYear = annualSummary.year || new Date().getFullYear();
        return `
                    <div class="service-annual-summary">
                        <div class="service-annual-header">
                            <div class="service-annual-title-group">
                                <span class="service-annual-icon"><i class="mdi mdi-calendar-range-outline"></i></span>
                                <div class="service-annual-summary-title">年度累计（${annualYear}年）</div>
                            </div>
                            <span class="service-status-pill"><span class="service-status-dot"></span>正常</span>
                        </div>
                        <div class="service-annual-summary-grid">
                            <div class="service-annual-summary-item">
                                <div class="service-annual-summary-value">${formatSlaValue(annualSummary.sla)}%</div>
                                <div class="service-annual-summary-label">SLA</div>
                            </div>
                            <div class="service-annual-summary-item">
                                <div class="service-annual-summary-value">${formatCardMetricValue(annualSummary.total_duration)}时</div>
                                <div class="service-annual-summary-label">中断时长</div>
                            </div>
                            <div class="service-annual-summary-item">
                                <div class="service-annual-summary-value">${formatCardCountValue(annualSummary.count)}起</div>
                                <div class="service-annual-summary-label">中断起数</div>
                            </div>
                        </div>
                    </div>`;
    }

    function renderServiceCurrentPeriodTable(categoryStats) {
        categoryStats = Array.isArray(categoryStats) ? categoryStats : [];
        const totalCount = categoryStats.reduce((sum, item) => sum + Number(item.count || 0), 0);
        const totalDuration = categoryStats.reduce((sum, item) => sum + Number(item.duration || 0), 0);
        return `
                        <div class="service-period-summary-list" aria-label="本期间业务故障分类统计">
                            ${renderServicePeriodSummaryMetric('故障总数', totalCount, '次', categoryStats, 'count')}
                            ${renderServicePeriodSummaryMetric('故障时长', totalDuration, '时', categoryStats, 'duration')}
                        </div>`;
    }

    function renderServicePeriodSummaryMetric(title, total, unit, categoryStats, field) {
        const totalValue = field === 'count'
            ? formatCardCountValue(total)
            : formatCardMetricValue(total);
        const parts = Array.isArray(categoryStats)
            ? categoryStats
                .map(item => {
                    const rawValue = Number(item[field] || 0);
                    if (rawValue <= 0) {
                        return '';
                    }
                    const value = field === 'count'
                        ? formatCardCountValue(rawValue)
                        : formatCardMetricValue(rawValue);
                    return `<span class="service-period-detail-item">${escapeHtml(item.label || '-')} ${value}</span>`;
                })
                .filter(Boolean)
            : [];
        const detail = parts.length > 0
            ? parts.join('<span class="service-period-detail-separator">|</span>')
            : '<span class="service-period-detail-empty">暂无</span>';
        return `
                            <div class="service-period-summary-card">
                                <div class="service-period-summary-main">
                                    <span class="service-period-summary-title">${title}</span>
                                    <span class="service-period-summary-total">
                                        <span class="service-period-summary-number">${totalValue}</span>
                                        <span class="service-period-summary-unit">${unit}</span>
                                    </span>
                                </div>
                                <div class="service-period-summary-detail">${detail}</div>
                            </div>`;
    }

    function renderServiceCurrentPeriod(svc) {
        return `
                    <div class="service-current-period">
                        <div class="service-current-period-heading">
                            <span class="service-current-period-icon"><i class="mdi mdi-chart-bar"></i></span>
                            <div class="service-current-period-title">本期间</div>
                        </div>
                        ${renderServiceCurrentPeriodTable(svc.category_stats)}
                    </div>`;
    }

    function renderServiceRuntimeCalendar(svc) {
        return `
                    <div class="service-runtime-calendar">
                        <div class="service-runtime-calendar-heading">
                            <span class="service-runtime-calendar-icon"><i class="mdi mdi-calendar-month-outline"></i></span>
                            <div class="service-runtime-calendar-title">运行月历</div>
                        </div>
                        ${renderServiceRuntimeCalendarSlaTable(svc)}
                        <div class="service-runtime-calendar-chart" aria-label="本年业务故障月度统计"></div>
                    </div>`;
    }

    function renderServiceRuntimeCalendarSlaRow(monthlyStats, annualYear, currentYear, currentMonth) {
        return monthlyStats.map((item, index) => {
            const itemLabel = item && item.label ? item.label : `${index + 1}月`;
            const itemSla = item && item.sla !== undefined ? item.sla : 100;
            const monthNumber = Number(item && item.month || index + 1);
            const showSla = annualYear < currentYear || (annualYear === currentYear && monthNumber <= currentMonth);
            return `
                            <div class="service-runtime-calendar-sla-cell">
                                <span class="service-runtime-calendar-sla-month">${escapeHtml(itemLabel)}</span>
                                <span class="service-runtime-calendar-sla-value">${showSla ? formatSlaValue(itemSla) : '-'}</span>
                            </div>`;
        }).join('');
    }

    function renderServiceRuntimeCalendarSlaTable(svc) {
        const annualYear = Number(svc.annual_summary && svc.annual_summary.year || new Date().getFullYear());
        const currentYear = new Date().getFullYear();
        const currentMonth = new Date().getMonth() + 1;
        const sourceStats = Array.isArray(svc.monthly_stats) ? svc.monthly_stats : [];
        const monthlyStats = Array.from({ length: 12 }, (_item, index) => {
            return sourceStats[index] || { month: index + 1, label: `${index + 1}月`, sla: 100 };
        });
        const firstHalf = monthlyStats.slice(0, 6);
        const secondHalf = monthlyStats.slice(6, 12);
        return `
                    <div class="service-runtime-calendar-sla-grid" aria-label="本年各月SLA情况">
                        ${renderServiceRuntimeCalendarSlaRow(firstHalf, annualYear, currentYear, currentMonth)}
                        ${renderServiceRuntimeCalendarSlaRow(secondHalf, annualYear, currentYear, currentMonth)}
                    </div>`;
    }

    function getInterruptCalendarLevel(count) {
        if (count <= 0) return 0;
        return Math.min(4, count);
    }

    function renderServiceInterruptCalendarMonthGrid(months, maxCount) {
        const monthHtml = months.map(month => {
            const days = Array.isArray(month.days) ? month.days : [];
            const leadingBlanks = Array.from({ length: Number(month.weekday_offset || 0) }, () => '<span class="service-interrupt-calendar-day service-interrupt-calendar-day--blank"></span>').join('');
            const dayHtml = days.map(day => {
                const count = Number(day.count || 0);
                const level = getInterruptCalendarLevel(count);
                const title = `${escapeHtml(month.label || '')}${escapeHtml(day.day || '')}日：${count}次`;
                return `<span class="service-interrupt-calendar-day service-interrupt-calendar-day--level-${level}" title="${title}"></span>`;
            }).join('');
            return `
                            <div class="service-interrupt-calendar-month">
                                <div class="service-interrupt-calendar-month-label">${escapeHtml(month.label || '-')}</div>
                                <div class="service-interrupt-calendar-days">${leadingBlanks}${dayHtml}</div>
                            </div>`;
        }).join('');
        return monthHtml;
    }

    function renderServiceInterruptCalendar(svc, interruptCalendarMaxCount) {
        const months = Array.isArray(svc.interrupt_calendar) ? svc.interrupt_calendar : [];
        const expandedMonths = Array.isArray(svc.interrupt_calendar_full) ? svc.interrupt_calendar_full : months;
        const maxCount = Number(interruptCalendarMaxCount || 0);
        return `
                    <div class="service-interrupt-calendar" aria-label="近三个月业务中断日历">
                        <div class="service-interrupt-calendar-months service-interrupt-calendar-months--default">${renderServiceInterruptCalendarMonthGrid(months, maxCount)}</div>
                        <div class="service-interrupt-calendar-months service-interrupt-calendar-months--expanded d-none">${renderServiceInterruptCalendarMonthGrid(expandedMonths, maxCount)}</div>
                        <button type="button" class="service-interrupt-calendar-toggle" aria-label="展开本年中断日历" title="展开本年中断日历">
                            <i class="mdi mdi-arrow-expand-all"></i>
                        </button>
                    </div>`;
    }

    function disposeServiceCalendarCharts() {
        serviceCalendarCharts.forEach(chart => chart.dispose());
        serviceCalendarCharts = [];
    }

    function resizeServiceCalendarCharts() {
        serviceCalendarCharts.forEach(chart => chart.resize());
    }

    function initServiceRuntimeCalendarCharts(container, servicesByKey) {
        container.querySelectorAll('.service-runtime-calendar-chart').forEach(element => {
            const card = element.closest('.service-strip-card[data-service-key]');
            const svc = card ? servicesByKey.get(card.dataset.serviceKey) || {} : {};
            const monthlyStats = Array.isArray(svc.monthly_stats) ? svc.monthly_stats : [];
            const monthLabels = Array.from({ length: 12 }, (_item, index) => `${index + 1}月`);
            const selectedDateParts = inputDate.value.split('-').map(Number);
            const annualYear = Number((svc.annual_summary && svc.annual_summary.year) || (selectedDateParts && selectedDateParts[0]) || new Date().getFullYear());
            const currentDate = new Date();
            const currentYear = currentDate.getFullYear();
            const currentMonth = currentDate.getMonth() + 1;
            const isCurrentYear = annualYear === currentYear;
            const countValues = monthLabels.map((_label, index) => Number(monthlyStats[index] && monthlyStats[index].count || 0));
            const durationValues = monthLabels.map((_label, index) => Number(monthlyStats[index] && monthlyStats[index].duration || 0));
            const durationValuesPast = Array(12).fill(null);
            const durationValuesFuture = Array(12).fill(null);
            if (isCurrentYear) {
                for (let i = 0; i < 12; i++) {
                    if (i < currentMonth) {
                        durationValuesPast[i] = durationValues[i];
                    }
                    if (i >= currentMonth - 1) {
                        durationValuesFuture[i] = durationValues[i];
                    }
                }
            } else if (annualYear < currentYear) {
                for (let i = 0; i < 12; i++) {
                    durationValuesPast[i] = durationValues[i];
                }
            } else {
                for (let i = 0; i < 12; i++) {
                    durationValuesFuture[i] = durationValues[i];
                }
            }
            const maxCount = Math.max(...countValues, 0);
            const maxDuration = Math.max(...durationValues, 0);
            const countAxisMax = Math.max(1, Math.ceil(maxCount * 2.6));
            let durationAxisMin, durationAxisMax;
            if (maxDuration > 0) {
                durationAxisMin = -Math.max(1, Math.ceil(maxDuration * 1.5));
                durationAxisMax = Math.max(1, Math.ceil(maxDuration * 1.15));
            } else {
                durationAxisMin = -1.3;
                durationAxisMax = 1.0;
            }
            const theme = getChartTheme();
            const chart = echarts.init(element);
            const chartOptions = {
                animation: false,
                backgroundColor: 'transparent',
                grid: { top: 16, left: 4, right: 18, bottom: 20, containLabel: false },
                tooltip: Object.assign({
                    trigger: 'axis',
                    confine: true,
                    formatter(params) {
                        const label = params && params[0] ? params[0].axisValue : '';
                        const labelIndex = monthLabels.indexOf(label);
                        const count = countValues[labelIndex] || 0;
                        const duration = durationValues[labelIndex] || 0;
                        return `${label}<br/>故障数：${count}次<br/>故障时长：${formatCardMetricValue(duration)}时`;
                    }
                }, buildTooltipTheme(theme)),
                xAxis: {
                    type: 'category',
                    data: monthLabels,
                    axisLine: { show: true, lineStyle: { color: 'rgba(154, 168, 186, 0.45)', width: 1 } },
                    axisTick: { show: false },
                    axisLabel: {
                        color: theme.muted,
                        fontSize: 10,
                        interval: 0,
                        margin: 8,
                        hideOverlap: false
                    },
                    splitLine: { show: false }
                },
                yAxis: [
                    {
                        type: 'value',
                        minInterval: 1,
                        min: 0,
                        max: countAxisMax,
                        axisLine: { show: false },
                        axisTick: { show: false },
                        axisLabel: { show: false },
                        splitLine: { show: false }
                    },
                    {
                        name: '时',
                        type: 'value',
                        position: 'right',
                        nameLocation: 'end',
                        nameGap: 2,
                        nameTextStyle: { color: '#078087', fontSize: 10, fontWeight: 600 },
                        min: durationAxisMin,
                        max: durationAxisMax,
                        axisLine: { show: false },
                        axisTick: { show: false },
                        axisLabel: { show: false },
                        splitLine: { show: false }
                    }
                ],
                series: [
                    {
                        name: '故障时长',
                        type: 'line',
                        yAxisIndex: 1,
                        data: durationValuesPast,
                        smooth: true,
                        symbol: 'circle',
                        symbolSize: 4,
                        label: {
                            show: true,
                            position: 'top',
                            distance: 4,
                            color: '#078087',
                            fontSize: 9,
                            formatter(params) {
                                const value = Number(params.value || 0);
                                return value > 0 ? formatCardMetricValue(value) : '';
                            }
                        },
                        lineStyle: { width: 1.8, color: '#078087' },
                        itemStyle: { color: '#078087' },
                        areaStyle: { color: '#078087', opacity: 0.08 }
                    },
                    {
                        name: '故障时长',
                        type: 'line',
                        yAxisIndex: 1,
                        data: durationValuesFuture,
                        smooth: true,
                        symbol: 'circle',
                        symbolSize: 4,
                        label: {
                            show: true,
                            position: 'top',
                            distance: 4,
                            color: '#cbd5e1',
                            fontSize: 9,
                            formatter(params) {
                                const value = Number(params.value || 0);
                                return value > 0 ? formatCardMetricValue(value) : '';
                            }
                        },
                        lineStyle: { width: 1.8, color: '#cbd5e1' },
                        itemStyle: { color: '#cbd5e1' },
                        areaStyle: { color: '#cbd5e1', opacity: 0.08 }
                    },
                    {
                        name: '故障数',
                        type: 'bar',
                        yAxisIndex: 0,
                        data: countValues,
                        barWidth: 8,
                        label: {
                            show: true,
                            position: 'top',
                            distance: 2,
                            color: theme.muted,
                            fontSize: 9,
                            formatter(params) {
                                const value = Number(params.value || 0);
                                return value > 0 ? `${formatCardCountValue(value)}次` : '';
                            }
                        },
                        itemStyle: {
                            color: 'rgba(32, 107, 196, 0.55)',
                            borderRadius: [3, 3, 0, 0]
                        }
                    }
                ]
            };
            chart.setOption(chartOptions);
            serviceCalendarCharts.push(chart);
        });
    }

    function initServiceInterruptCalendarToggles(container) {
        container.querySelectorAll('.service-interrupt-calendar-toggle').forEach(button => {
            button.addEventListener('click', event => {
                event.preventDefault();
                event.stopPropagation();
                const calendar = button.closest('.service-interrupt-calendar');
                if (!calendar) return;
                const defaultMonths = calendar.querySelector('.service-interrupt-calendar-months--default');
                const expandedMonths = calendar.querySelector('.service-interrupt-calendar-months--expanded');
                const icon = button.querySelector('.mdi');
                const expanded = !calendar.classList.contains('service-interrupt-calendar--expanded');
                calendar.classList.toggle('service-interrupt-calendar--expanded', expanded);
                if (defaultMonths) defaultMonths.classList.toggle('d-none', expanded);
                if (expandedMonths) expandedMonths.classList.toggle('d-none', !expanded);
                button.setAttribute('aria-label', expanded ? '收回中断日历' : '展开本年中断日历');
                button.setAttribute('title', expanded ? '收回中断日历' : '展开本年中断日历');
                if (icon) icon.className = expanded ? 'mdi mdi-arrow-collapse-all' : 'mdi mdi-arrow-expand-all';
            });
        });
    }

    function renderStripCard(card) {
        const title = escapeHtml(card.footer);
        const svc = card.service || {};
        const hasCurrentPeriodFaults = card.service ? card.service.has_current_period_faults !== false : true;
        const quietTitleClass = hasCurrentPeriodFaults ? '' : ' service-strip-card-title--quiet';
        const serviceAttrs = card.serviceKey
            ? ` data-service-key="${escapeHtml(card.serviceKey)}" data-service-name="${title}" data-service-type="${escapeHtml(card.serviceType || '')}" role="button" tabindex="0"`
            : '';
        return `
            <div class="statistics-strip-card service-strip-card"${serviceAttrs}>
                <div class="service-strip-card-title${quietTitleClass}" title="${title}">${title}</div>
                <div class="statistics-strip-card-body">
                    ${renderServiceAnnualSummary(card.service)}
                    ${renderServiceCurrentPeriod(card.service)}
                    ${renderServiceRuntimeCalendar(svc)}
                    ${renderServiceInterruptCalendar(svc, card.interruptCalendarMaxCount)}
                </div>
            </div>`;
    }

    function getMaxServiceInterruptCalendarCount(services) {
        return Math.max(
            ...services.flatMap(svc => {
                const calendars = [svc.interrupt_calendar, svc.interrupt_calendar_full].filter(Array.isArray);
                return calendars.flatMap(calendar =>
                    calendar.flatMap(month => Array.isArray(month.days) ? month.days.map(day => Number(day.count || 0)) : [])
                );
            }),
            0
        );
    }

    function groupServicesByLabel(services) {
        const groups = [];
        const groupMap = new Map();
        services.forEach(svc => {
            const groupLabel = svc.group_label || '未分组';
            if (!groupMap.has(groupLabel)) {
                const group = { label: groupLabel, services: [] };
                groupMap.set(groupLabel, group);
                groups.push(group);
            }
            groupMap.get(groupLabel).services.push(svc);
        });
        return groups;
    }

    function renderServiceCards(services, containerId, emptyServiceType) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (services.length === 0) {
            container.innerHTML = `<div class="col-12 text-center text-muted py-5"><i class="mdi mdi-information-outline me-1"></i> 当前时间范围内无${emptyServiceType}故障记录</div>`;
            return;
        }

        const interruptCalendarMaxCount = getMaxServiceInterruptCalendarCount(services);
        const servicesByKey = new Map(services.map(svc => [svc.key, svc]));
        const groupedServices = groupServicesByLabel(services);
        const html = groupedServices.map(group => {
            const cardsHtml = group.services.map(svc => {
                return renderStripCard({
                    serviceKey: svc.key,
                    serviceType: emptyServiceType,
                    footer: svc.name,
                    service: svc,
                    interruptCalendarMaxCount,
                });
            }).join('');
            return `
                <section class="service-group-section">
                    <div class="service-group-title">${escapeHtml(group.label)}</div>
                    <div class="service-group-card-grid">${cardsHtml}</div>
                </section>`;
        }).join('');

        container.innerHTML = html;
        initServiceRuntimeCalendarCharts(container, servicesByKey);
        initServiceInterruptCalendarToggles(container);
        container.querySelectorAll('.service-strip-card[data-service-key]').forEach(card => {
            card.addEventListener('click', () => handleServiceCardClick(card.dataset.serviceKey, card.dataset.serviceName, card.dataset.serviceType));
            card.addEventListener('keydown', event => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    handleServiceCardClick(card.dataset.serviceKey, card.dataset.serviceName, card.dataset.serviceType);
                }
            });
        });
    }

    function getServiceTypeValue(serviceType) {
        return serviceType === '裸纤业务' ? 'bare_fiber' : 'circuit';
    }

    async function loadServiceDetails(serviceType, ordering, tbodyId, badgeId, clearButtonId) {
        let url = `${window.SERVICE_STATISTICS_DETAILS_API}?${buildTimeParams()}&service_type=${encodeURIComponent(getServiceTypeValue(serviceType))}&ordering=${ordering}`;

        if (activeServiceDetailFilterKey && activeServiceDetailFilterType === serviceType) {
            url += `&service_key=${encodeURIComponent(activeServiceDetailFilterKey)}`;
        }

        const tbody = document.getElementById(tbodyId);
        tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4">加载中...</td></tr>';

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Network response error');
            const data = await response.json();
            const results = data.results || [];
            renderServiceDetailsTableHtml(results, serviceType, tbodyId, badgeId, clearButtonId);
        } catch (error) {
            console.error(`Fetch ${serviceType} details error:`, error);
            tbody.innerHTML = '<tr><td colspan="8" class="text-danger text-center py-4">数据加载失败，请检查网络或刷新重试</td></tr>';
        }
    }

    function renderServiceDetailsTableHtml(results, serviceType, tbodyId, badgeId, clearButtonId) {
        const tbody = document.getElementById(tbodyId);
        const badge = document.getElementById(badgeId);
        const clearButton = document.getElementById(clearButtonId);
        if (!tbody) return;

        if (activeServiceDetailFilterKey && activeServiceDetailFilterType === serviceType) {
            if (badge) {
                badge.textContent = activeServiceDetailFilterName || activeServiceDetailFilterKey;
                badge.className = 'badge bg-success text-white ms-2';
                badge.style.display = 'inline-block';
            }
            if (clearButton) clearButton.style.display = 'inline-block';
        } else {
            if (badge) badge.style.display = 'none';
            if (clearButton) clearButton.style.display = 'none';
        }

        if (clearButton) {
            clearButton.onclick = () => {
                activeServiceDetailFilterKey = null;
                activeServiceDetailFilterName = null;
                activeServiceDetailFilterType = null;
                if (serviceType === '裸纤业务') {
                    loadServiceDetails('裸纤业务', serviceOrdering, 'service-details-tbody', 'service-detail-filter-badge', 'btn-clear-service-detail-filter');
                } else {
                    loadServiceDetails('电路业务', circuitOrdering, 'circuit-service-details-tbody', 'circuit-service-detail-filter-badge', 'btn-clear-circuit-service-detail-filter');
                }
            };
        }

        if (results.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">当前条件下无可展示的业务故障明细</td></tr>';
            return;
        }

        tbody.innerHTML = results.map(item => {
            const badges = item.is_long ? '<span class="badge bg-warning text-dark ms-1">≥6h</span>' : '';
            const faultLink = item.fault_url
                ? `<a href="${escapeHtml(item.fault_url)}" target="_blank">${escapeHtml(item.fault_number)}</a>`
                : escapeHtml(item.fault_number || '-');
            const impactLink = item.impact_url
                ? `<a href="${escapeHtml(item.impact_url)}" target="_blank">查看</a>`
                : '-';
            return `<tr>
                <td>${faultLink}</td>
                <td>${escapeHtml(item.service_name || '-')}</td>
                <td>${escapeHtml(item.service_interruption_time || '-')}</td>
                <td>${escapeHtml(item.service_recovery_time || '-')}</td>
                <td><strong class="${item.is_long ? 'text-danger' : ''}">${escapeHtml(item.duration || 0)}</strong></td>
                <td>${escapeHtml(item.fault_category || '-')}</td>
                <td>${impactLink}</td>
                <td>${badges}</td>
            </tr>`;
        }).join('');
    }

    function handleServiceCardClick(serviceKey, serviceName, serviceType) {
        if (!serviceKey) return;
        activeServiceDetailFilterKey = serviceKey;
        activeServiceDetailFilterName = serviceName;
        activeServiceDetailFilterType = serviceType;

        if (serviceType === '裸纤业务') {
            loadServiceDetails('裸纤业务', serviceOrdering, 'service-details-tbody', 'service-detail-filter-badge', 'btn-clear-service-detail-filter');
            const tbody = document.getElementById('service-details-tbody');
            if (tbody) tbody.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            loadServiceDetails('电路业务', circuitOrdering, 'circuit-service-details-tbody', 'circuit-service-detail-filter-badge', 'btn-clear-circuit-service-detail-filter');
            const tbody = document.getElementById('circuit-service-details-tbody');
            if (tbody) tbody.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    function syncBareFiberServiceCardScopeToggle() {
        if (!scopeToggle) return;
        const activeTab = document.querySelector('#statisticsTab .nav-link.active');
        const activeTabId = activeTab ? activeTab.id : '';
        scopeToggle.classList.toggle('d-none', activeTabId !== 'tab-service-btn');
    }

    bareFiberServiceCardScopeInputs.forEach(input => {
        input.addEventListener('change', () => {
            if (!input.checked) return;
            bareFiberServiceCardScope = input.value === 'all' ? 'all' : 'faulted';
            if (bareFiberServiceCardScope === 'all' && !bareFiberAllServicesLoaded) {
                loadServiceData({ includeAllBareFiber: true });
                return;
            }
            renderBareFiberServiceCards();
        });
    });

    if (physicalProvinceFilter) {
        physicalProvinceFilter.addEventListener('change', () => {
            const activeTab = document.querySelector('#statisticsTab .nav-link.active');
            if (activeTab && activeTab.id === 'tab-physical-btn') loadData();
        });
    }

    // ---------------- Tab 切换联动 ----------------
    function loadActiveTab() {
        syncBareFiberServiceCardScopeToggle();
        syncPhysicalProvinceFilterVisibility();
        const activeTab = document.querySelector('#statisticsTab .nav-link.active');
        if (activeTab && (activeTab.id === 'tab-service-btn' || activeTab.id === 'tab-circuit-service-btn')) {
            loadServiceData({
                includeAllBareFiber: activeTab.id === 'tab-service-btn' && bareFiberServiceCardScope === 'all',
            });
        } else if (activeTab && (activeTab.id === 'tab-branch-company-btn' || activeTab.id === 'tab-branch-performance-btn')) {
            loadData();
        } else {
            loadData();
        }
    }

    // Tab 切换时加载对应数据
    const tabEl = document.getElementById('statisticsTab');
    if (tabEl) {
        tabEl.addEventListener('shown.bs.tab', function(event) {
            syncBareFiberServiceCardScopeToggle();
            syncPhysicalProvinceFilterVisibility();
            if (event.target.id === 'tab-service-btn' || event.target.id === 'tab-circuit-service-btn') {
                loadServiceData({
                    includeAllBareFiber: event.target.id === 'tab-service-btn' && bareFiberServiceCardScope === 'all',
                });
            } else if (event.target.id === 'tab-branch-company-btn' || event.target.id === 'tab-branch-performance-btn') {
                loadData();
                setTimeout(() => {
                    resizeStatisticsCharts();
                }, 100);
            } else if (event.target.id === 'tab-physical-btn') {
                loadData();
                setTimeout(() => {
                    resizeStatisticsCharts();
                }, 100);
            }
        });
    }

    // ---------------- 初始化启动 ----------------
    syncBareFiberServiceCardScopeToggle();
    syncPhysicalProvinceFilterVisibility();
    updateDateSelectors();
    loadData();
});


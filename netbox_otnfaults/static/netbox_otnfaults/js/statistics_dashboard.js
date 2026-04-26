/**
 * 故障统计交互脚本
 */
document.addEventListener("DOMContentLoaded", function() {
    // ---------------- 图表实例初始化 ----------------
    let chartResource = echarts.init(document.getElementById('chart-resource'));
    let chartProvince = echarts.init(document.getElementById('chart-province'));
    let chartReason = echarts.init(document.getElementById('chart-reason'));
    const chartHistogramElement = document.getElementById('chart-cable-break-histogram');
    let chartHistogram = chartHistogramElement ? echarts.init(chartHistogramElement) : null;
    const chartPhysicalDailyElement = document.getElementById('chart-physical-daily-faults');
    let chartPhysicalDaily = chartPhysicalDailyElement ? echarts.init(chartPhysicalDailyElement) : null;
    const chartPhysicalDurationBoxplotElement = document.getElementById('chart-physical-duration-boxplot');
    let chartPhysicalDurationBoxplot = chartPhysicalDurationBoxplotElement ? echarts.init(chartPhysicalDurationBoxplotElement) : null;
    const physicalBoxplotFilterShort = document.getElementById('physical-boxplot-filter-short');
    const physicalBoxplotFilterRectification = document.getElementById('physical-boxplot-filter-rectification');
    
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
        if (chartHistogram) chartHistogram.resize();
        if (chartPhysicalDaily) chartPhysicalDaily.resize();
        if (chartPhysicalDurationBoxplot) chartPhysicalDurationBoxplot.resize();
    }

    window.addEventListener('resize', resizeStatisticsCharts);

    // ---------------- 统一事件绑定 ----------------
    // 点击下钻
    chartResource.on('click', params => handleChartClick(params, 'resource_type'));
    chartProvince.on('click', params => handleChartClick(params, 'province'));
    chartReason.on('click', params => handleChartClick(params, 'reason'));
    if (chartHistogram) chartHistogram.on('click', params => handleChartClick(params, 'duration_histogram_bucket'));
    
    // 图例切换（过滤剔除）
    chartResource.on('legendselectchanged', params => { updateExcludedSet('resource_type', params.selected); renderDetailsTable(); });
    chartProvince.on('legendselectchanged', params => { updateExcludedSet('province', params.selected); renderDetailsTable(); });
    chartReason.on('legendselectchanged', params => { updateExcludedSet('reason', params.selected); renderDetailsTable(); });

    document.addEventListener('click', function(event) {
        const metric = event.target.closest('.statistics-drill-metric');
        if (!metric) return;
        handleMetricFilterClick(metric);
    });

    let currentAllDetails = []; // 保存后端返回的全部详情数据
    let currentChartsData = null;
    let currentCableBreakOverview = null;
    let currentPrevCableBreakOverview = null;
    let activeFilterField = null; // 'resource_type', 'province', 'reason'
    let activeFilterValue = null;
    let activeFilterExtraField = null;
    let activeFilterExtraValue = null;
    let activeFilterLabel = null;

    if (physicalBoxplotFilterShort) {
        physicalBoxplotFilterShort.addEventListener('change', () => renderPhysicalDurationBoxplot(currentChartsData && currentChartsData.physical_daily, selFilterType.value));
    }
    if (physicalBoxplotFilterRectification) {
        physicalBoxplotFilterRectification.addEventListener('change', () => renderPhysicalDurationBoxplot(currentChartsData && currentChartsData.physical_daily, selFilterType.value));
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
            splitLine: { lineStyle: { color: theme.border, type: 'dashed' } }
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
        if (currentChartsData) {
            renderCharts(currentChartsData);
            renderOverallDailyFaultChart(currentChartsData.physical_daily, selFilterType.value);
            renderPhysicalDurationBoxplot(currentChartsData.physical_daily, selFilterType.value);
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
        cableBreakMapIframe.src = `${window.STATISTICS_CABLE_BREAK_MAP_URL}?modal=true&${buildTimeParams()}`;
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

    // ---------------- 获取物理故障数据 ----------------
    async function loadData() {
        let url = `${window.STATISTICS_DATA_API}?${buildTimeParams()}`;

        try {
            document.getElementById('details-tbody').innerHTML = '<tr><td colspan="10" class="text-center py-4">加载中...</td></tr>';
            const response = await fetch(url);
            if (!response.ok) throw new Error('Network response error');
            const data = await response.json();
            
            currentAllDetails = data.details || [];
            if (activeFilterField && activeFilterValue) {
                // 如果当前正在下钻状态，不清除过滤条件，继续应用
                renderDetailsTable();
            } else {
                renderDetailsTable();
            }

            if (data.period && data.period.start) {
                const periodEl = document.getElementById('period-display');
                periodEl.innerHTML = formatStatisticsPeriodLabel(selFilterType.value, inputDate.value, data.period);
                updatePeriodLabelState(periodEl, data.period);
            } else {
                document.getElementById('period-display').innerHTML = '';
            }

            renderKPIs(data.kpis, data.prev_kpis, selFilterType.value);
            renderOverallSummary(data.kpis, data.charts, data.prev_charts);
            renderOverallOtherSummary(data.other_overview, data.prev_other_overview);
            renderOverallDailyFaultChart(data.charts && data.charts.physical_daily, selFilterType.value);
            renderPhysicalDurationBoxplot(data.charts && data.charts.physical_daily, selFilterType.value);
            currentCableBreakOverview = data.cable_break_overview || null;
            currentPrevCableBreakOverview = data.prev_cable_break_overview || null;
            currentChartsData = data.charts || null;
            renderCableBreakOverview(data.cable_break_overview, data.prev_cable_break_overview);
            renderCharts(data.charts);
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

        let htmlContent = buildFlexGroup(categories, "起", "", "text-indigo", prevCategories);
        categoriesList.innerHTML = htmlContent;
    }

    function renderOverallOtherSummary(otherOverview, prevOtherOverview) {
        const otherList = document.getElementById('kpi-overall-other-flex-list');
        if (!otherList) return;

        otherOverview = otherOverview || {};
        prevOtherOverview = prevOtherOverview || {};

        const items = [
            { name: '光缆劣化', value: otherOverview.fiber_degradation || 0 },
            { name: '光缆抖动', value: otherOverview.fiber_jitter || 0 },
            { name: '挂起的故障', value: otherOverview.suspended_faults || 0 },
        ];
        const prevItems = [
            { name: '光缆劣化', value: prevOtherOverview.fiber_degradation || 0 },
            { name: '光缆抖动', value: prevOtherOverview.fiber_jitter || 0 },
            { name: '挂起的故障', value: prevOtherOverview.suspended_faults || 0 },
        ];

        otherList.innerHTML = buildFlexGroup(items, "起", "", "text-indigo", prevItems);
    }

    function isPhysicalDailyLineMode(filterType) {
        return filterType === 'half' || filterType === 'year';
    }

    function parsePhysicalDailyLabelDate(value) {
        const parts = String(value).split('-').map(Number);
        if (parts.length !== 3 || parts.some(Number.isNaN)) return null;
        return { month: parts[1], day: parts[2] };
    }

    function formatPhysicalDailyAxisLabel(value, filterType) {
        const dateParts = parsePhysicalDailyLabelDate(value);
        if (!dateParts) return value;
        const { month, day } = dateParts;
        if (filterType === 'week' || filterType === 'month') {
            return `${month}/${day}`;
        }
        if (filterType === 'quarter') {
            return day === 1 ? `${month}月` : `${month}/${day}`;
        }
        return day === 1 ? `${month}月` : '';
    }

    function shouldShowPhysicalDailyAxisLabel(index, value, filterType) {
        const dateParts = parsePhysicalDailyLabelDate(value);
        if (!dateParts) return true;
        const day = dateParts.day;
        if (filterType === 'week') return true;
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

    function renderOverallDailyFaultChart(dailyData, filterType) {
        if (!chartPhysicalDaily || !dailyData) return;

        const chartTheme = getChartTheme();
        const labels = dailyData.labels || [];
        const durations = dailyData.durations || [];
        const useLineBars = isPhysicalDailyLineMode(filterType);
        const fallbackColors = {
            '光缆中断': '#dc3545',
            '供电故障': '#6f42c1',
            '空调故障': '#0d6efd',
            '设备故障': '#fd7e14',
        };
        const series = (dailyData.series || []).map(item => ({
            name: item.name,
            type: 'bar',
            stack: 'physical_faults',
            barWidth: useLineBars ? 2 : '65%',
            barMaxWidth: useLineBars ? 2 : 14,
            emphasis: { focus: 'series' },
            itemStyle: { color: item.color || fallbackColors[item.name] || chartTheme.primary },
            data: item.data || [],
        })).concat([{
            name: '中断时长',
            type: 'line',
            yAxisIndex: 1,
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 2, color: chartTheme.muted, type: 'dashed' },
            itemStyle: { color: chartTheme.muted },
            data: durations,
        }]);

        chartPhysicalDaily.setOption({
            textStyle: { color: chartTheme.text },
            color: (dailyData.series || []).map(item => item.color || fallbackColors[item.name] || chartTheme.primary).concat([chartTheme.muted]),
            tooltip: {
                ...buildTooltipTheme(chartTheme),
                trigger: 'axis',
                axisPointer: { type: useLineBars ? 'line' : 'shadow', lineStyle: { color: chartTheme.axisLine } },
                formatter: function(params) {
                    const countParams = params.filter(item => item.seriesType === 'bar');
                    const durationParam = params.find(item => item.seriesName === '中断时长');
                    const total = countParams.reduce((sum, item) => sum + Number(item.value || 0), 0);
                    const rows = params
                        .filter(item => item.seriesType === 'bar' && Number(item.value || 0) > 0)
                        .map(item => {
                            return `${item.marker}${item.seriesName}: ${item.value}起`;
                        })
                        .join('<br/>');
                    const durationText = durationParam ? `<br/><span style="margin-left:14px;">中断时长合计: ${Number(durationParam.value || 0).toFixed(2)}小时</span>` : '';
                    return `${params[0].axisValue}<br/>${rows || '无物理故障'}<br/><span style="margin-left:14px;">故障合计: ${total}起</span>${durationText}`;
                }
            },
            legend: {
                top: 8,
                left: 'center',
                type: 'scroll',
                ...buildLegendTheme(chartTheme)
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
            yAxis: [
                {
                    type: 'value',
                    name: '物理故障数',
                    minInterval: 1,
                    ...buildAxisTheme(chartTheme),
                    splitLine: { show: true, lineStyle: { color: chartTheme.border, type: 'dashed' } },
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
        const rawValue = Array.isArray(params.value) ? params.value : (params.data || []);
        return rawValue.length >= 6 ? rawValue.slice(1, 6) : rawValue.slice(0, 5);
    }

    function getSelectedPhysicalBoxplotData(dailyData) {
        const shortChecked = Boolean(physicalBoxplotFilterShort && physicalBoxplotFilterShort.checked);
        const rectificationChecked = Boolean(physicalBoxplotFilterRectification && physicalBoxplotFilterRectification.checked);
        const key = shortChecked && rectificationChecked ? 'exclude_short_rectification' : shortChecked ? 'exclude_short' : rectificationChecked ? 'exclude_rectification' : 'all';
        const options = dailyData.boxplot_options || {};
        return options[key] || dailyData.boxplot || [];
    }

    function renderPhysicalDurationBoxplot(dailyData, filterType) {
        if (!chartPhysicalDurationBoxplot || !dailyData) return;

        const chartTheme = getChartTheme();
        const labels = dailyData.labels || [];
        const boxplotData = getSelectedPhysicalBoxplotData(dailyData);

        chartPhysicalDurationBoxplot.setOption({
            textStyle: { color: chartTheme.text },
            tooltip: {
                ...buildTooltipTheme(chartTheme),
                trigger: 'item',
                formatter: function(params) {
                    const value = getBoxplotTooltipValues(params);
                    return `${params.name}<br/>` +
                        `<span style="margin-left:14px;">最大值: ${value[4] || 0}小时</span><br/>` +
                        `<span style="margin-left:14px;">Q3: ${value[3] || 0}小时</span><br/>` +
                        `<span style="margin-left:14px;">中位数: ${value[2] || 0}小时</span><br/>` +
                        `<span style="margin-left:14px;">Q1: ${value[1] || 0}小时</span><br/>` +
                        `<span style="margin-left:14px;">最小值: ${value[0] || 0}小时</span>`;
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
                type: 'value',
                name: '中断时长分布(小时)',
                nameGap: 12,
                nameLocation: 'end',
                min: 0,
                ...buildAxisTheme(chartTheme),
                splitLine: { show: true, lineStyle: { color: chartTheme.border, type: 'dashed' } },
            },
            series: [{
                name: '中断时长分布',
                type: 'boxplot',
                boxWidth: getPhysicalDurationBoxWidth(filterType),
                data: boxplotData,
                itemStyle: {
                    color: chartTheme.dark ? 'rgba(110, 168, 254, 0.22)' : 'rgba(32, 107, 196, 0.16)',
                    borderColor: chartTheme.primary,
                    borderWidth: 1.2,
                },
                emphasis: { itemStyle: { borderWidth: 2 } },
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

    function formatCardCountValue(value) {
        const number = Number(value);
        if (!Number.isFinite(number)) return value === undefined || value === null ? '--' : String(value);
        return String(Math.round(number));
    }

    function isCountUnit(unit) {
        return unit === '起' || unit === '次';
    }

    function buildTrendArrow(currentVal, prevVal, integer = false) {
        if (prevVal === undefined || prevVal === null) return '';
        const cur = parseFloat(currentVal);
        const prev = parseFloat(prevVal);
        if (isNaN(cur) || isNaN(prev) || cur === prev) return '';
        const symbol = cur > prev ? '+' : '';
        const diffText = `${symbol}${formatTrendDiff(cur, prev, integer)}`;
        if (cur > prev) {
            return `<span class="statistics-trend-diff text-danger">⬆ ${diffText}</span>`;
        } else {
            return `<span class="statistics-trend-diff text-success">⬇ ${diffText}</span>`;
        }
    }

    function renderTrendBesideMetric(metricEl, currentValue, previousValue, integer = false) {
        if (!metricEl) return;
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

    function buildFlexItemCore(value, unit, title, colorClass = "text-primary", prevValue, filterField, filterValue, filterLabel, valueId, filterExtraField, filterExtraValue, infoTitle, infoLabel) {
        const countUnit = isCountUnit(unit);
        const arrow = buildTrendArrow(value, prevValue, countUnit);
        const displayValue = isCountUnit(unit) ? formatCardCountValue(value) : formatCardMetricValue(value);
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
                <div class="statistics-overall-kpi-value fs-3 fw-bold ${colorClass} lh-1"${valueIdAttr}>${displayValue}<span class="statistics-overall-kpi-unit ms-1 text-muted fw-normal" style="font-size: 13px;">${unit}</span>${arrow ? `<span class="statistics-metric-trend statistics-kpi-trend-row">${arrow}</span>` : ''}</div>
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
            groupHtml += buildFlexItemCore(val, unit, name, colorClass, prevVal, itemFilterField, itemFilterValue, itemFilterLabel, itemValueId, itemFilterExtraField, itemFilterExtraValue, itemInfoTitle, itemInfoLabel);
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
        if (durationTotalList) {
            durationTotalList.innerHTML = buildFlexGroup([{
                name: "总历时",
                value: currentDuration,
                prevValue: prevDuration,
                filterField: "category",
                filterValue: "光缆中断",
                filterLabel: "中断历时",
                id: "cable-break-total-duration",
            }], "时", "", "text-indigo", [{name: "总历时", value: prevDuration}]);
        }

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
        const overallAverageList = document.getElementById('cable-break-average-overall-list');
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
            const prevFilteredAverageItems = filteredAverageItems.map(item => ({name: item.name, value: item.prevValue}));
            if (overallAverageList) {
                overallAverageList.innerHTML = buildFlexGroup(overallAverageItems, "时", "", "text-indigo", prevOverallAverageItems);
            }
            if (filteredAverageList) {
                filteredAverageList.innerHTML = buildFlexGroup(filteredAverageItems, "时", "", "text-indigo", prevFilteredAverageItems);
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
                grid: { top: 62, left: '3%', right: '4%', bottom: 42, containLabel: true },
                xAxis: { 
                    type: 'category', 
                    data: histLabels,
                    name: '历时(小时)',
                    nameLocation: 'middle',
                    nameGap: 30,
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

    function renderCharts(chartsData) {
        if (!chartsData) return;
        const chartTheme = getChartTheme();
        // 1. 光缆属性 (Pie)
        const resourceColorMap = {
            '自建': chartTheme.chartPalette[0],
            '协调': chartTheme.chartPalette[1],
            '租赁': chartTheme.chartPalette[2],
            '未指定': chartTheme.dark ? '#697386' : '#cbd5e1'
        };
        chartResource.setOption({
            textStyle: { color: chartTheme.text },
            tooltip: { 
                ...buildTooltipTheme(chartTheme),
                trigger: 'item', 
                formatter: params => {
                    let avg = params.value > 0 ? (params.data._duration / params.value).toFixed(2) : "0.00";
                    return `${params.marker}${params.name}: ${params.value}次 (${params.percent}%)<br/>` +
                           `<span style="margin-left:14px;">总历时: ${params.data._duration} 小时</span><br/>` +
                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;
                }
            },
            legend: { bottom: 0, type: 'scroll', ...buildLegendTheme(chartTheme) },
            series: [{
                type: 'pie',
                radius: ['45%', '75%'],
                center: ['50%', '45%'],
                label: {
                    show: true,
                    ...buildPieLabelTheme(chartTheme),
                    formatter: formatPieSliceLabel,
                    alignTo: 'edge',
                    edgeDistance: 10,
                    lineHeight: 15,
                    fontSize: 11
                },
                labelLine: { lineStyle: { color: chartTheme.border } },
                itemStyle: {
                    color: function(params) { return resourceColorMap[params.name] || '#5470c6'; },
                    borderRadius: 5, borderColor: chartTheme.surface, borderWidth: 2
                },
                data: chartsData.resource.map(item => ({name: item.name, value: item.value, _duration: item.duration}))
            }]
        });

        // 2. 省份 (Bar 全部)
        let provData = chartsData.province;
        chartProvince.setOption({
            textStyle: { color: chartTheme.text },
            tooltip: { 
                ...buildTooltipTheme(chartTheme),
                trigger: 'axis', 
                axisPointer: { type: 'shadow', shadowStyle: { color: chartTheme.dark ? 'rgba(110, 168, 254, 0.14)' : 'rgba(32, 107, 196, 0.1)' } },
                formatter: params => {
                    let p = params[0];
                    let avg = p.value > 0 ? (p.data._duration / p.value).toFixed(2) : "0.00";
                    return `${p.marker || ''}${p.name}: ${p.value}次<br/>` +
                           `<span style="margin-left:14px;">总历时: ${p.data._duration} 小时</span><br/>` +
                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;
                }
            },
            grid: { top: 30, left: '3%', right: '4%', bottom: '15%', containLabel: true },
            xAxis: { 
                type: 'category', 
                data: provData.map(item => item.name),
                ...buildAxisTheme(chartTheme, { interval: 0, rotate: 30 })
            },
            yAxis: { type: 'value', ...buildAxisTheme(chartTheme) },
            series: [{
                type: 'bar',
                label: { show: true, position: 'top', color: chartTheme.heading, fontWeight: 600 },
                itemStyle: { color: chartTheme.primary, borderRadius: [4, 4, 0, 0] },
                data: provData.map(item => ({value: item.value, _duration: item.duration}))
            }]
        });

        // 3. 一级原因 (Pie)
        chartReason.setOption({
            textStyle: { color: chartTheme.text },
            color: chartTheme.chartPalette,
            tooltip: { 
                ...buildTooltipTheme(chartTheme),
                trigger: 'item', 
                formatter: params => {
                    let avg = params.value > 0 ? (params.data._duration / params.value).toFixed(2) : "0.00";
                    return `${params.marker}${params.name}: ${params.value}次 (${params.percent}%)<br/>` +
                           `<span style="margin-left:14px;">总历时: ${params.data._duration} 小时</span><br/>` +
                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;
                }
            },
            legend: { bottom: 0, type: 'scroll', ...buildLegendTheme(chartTheme) },
            series: [{
                type: 'pie',
                radius: '65%',
                center: ['50%', '45%'],
                label: {
                    show: true,
                    ...buildPieLabelTheme(chartTheme),
                    formatter: formatPieSliceLabel,
                    alignTo: 'edge',
                    edgeDistance: 10,
                    lineHeight: 15,
                    fontSize: 11
                },
                labelLine: { lineStyle: { color: chartTheme.border } },
                itemStyle: { borderColor: chartTheme.surface, borderWidth: 2 },
                data: chartsData.reason.map(item => ({name: item.name, value: item.value, _duration: item.duration})),
                emphasis: {
                    itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: chartTheme.dark ? 'rgba(0, 0, 0, 0.75)' : 'rgba(0, 0, 0, 0.3)' }
                }
            }]
        });

    }

    // ---------------- 渲染下钻表格 ----------------
    function normalizeFilterValue(fieldName, value) {
        if (value === 'true') return true;
        if (value === 'false') return false;
        return value;
    }

    function applyDetailFilter(item, fieldName, value) {
        return item[fieldName] === value;
    }

    function renderDetailsTable() {
        let filteredDetails = currentAllDetails;
        let activeConditions = []; // 存入文本用于展示当前所有生效的过滤状态

        // 1. 应用图例剔除过滤 (点击图例取消显示的项目)
        if (excludedCategories.resource_type.size > 0) {
            filteredDetails = filteredDetails.filter(item => !excludedCategories.resource_type.has(item.resource_type));
            activeConditions.push(`排除光缆属性[${Array.from(excludedCategories.resource_type).join(', ')}]`);
        }
        if (excludedCategories.province.size > 0) {
            filteredDetails = filteredDetails.filter(item => !excludedCategories.province.has(item.province));
            activeConditions.push(`排除省份[${Array.from(excludedCategories.province).join(', ')}]`);
        }
        if (excludedCategories.reason.size > 0) {
            filteredDetails = filteredDetails.filter(item => !excludedCategories.reason.has(item.reason));
            activeConditions.push(`排除原因[${Array.from(excludedCategories.reason).join(', ')}]`);
        }
        
        const summaryDiv = document.getElementById('filtered-kpi-summary');

        // 2. 应用单点下钻过滤
        if (activeFilterField && activeFilterValue !== null) {
            filteredDetails = filteredDetails.filter(item => {
                if (!applyDetailFilter(item, activeFilterField, activeFilterValue)) return false;
                if (activeFilterExtraField && activeFilterExtraValue !== null) {
                    return applyDetailFilter(item, activeFilterExtraField, activeFilterExtraValue);
                }
                return true;
            });
            
            let filterName = '';
            let filterValueDisp = activeFilterLabel || activeFilterValue;
            if (activeFilterField === 'resource_type') filterName = '光缆属性';
            else if (activeFilterField === 'source_group') filterName = '光缆属性';
            else if (activeFilterField === 'province') filterName = '省份';
            else if (activeFilterField === 'reason') filterName = '原因';
            else if (activeFilterField === 'duration_bucket') filterName = '历时分布';
            else if (activeFilterField === 'duration_histogram_bucket') filterName = '故障历时频数';
            else if (activeFilterField === 'category') filterName = '分类';
            else if (activeFilterField === 'occurrence_period') filterName = '发生时段';
            else if (activeFilterField === 'cause_group') filterName = '成因';
            else if (activeFilterField === 'is_valid_duration') { filterName = '特殊标签'; filterValueDisp = '有效平均'; }
            else if (activeFilterField === 'is_long') { filterName = '特殊标签'; filterValueDisp = '长时故障(≥6h)'; }
            else if (activeFilterField === 'is_repeat') { filterName = '特殊标签'; filterValueDisp = '历史重复故障'; }
            
            activeConditions.push(`下钻：${filterName}=${filterValueDisp}`);
            if (activeFilterExtraField === 'is_valid_duration' && activeFilterExtraValue === true) {
                activeConditions.push('附加：有效历时>30分钟');
            }
        }

        if (activeConditions.length > 0) {
            let conditionsText = activeConditions.join(' | ');
            badgeFilter.textContent = conditionsText;
            badgeFilter.className = 'badge bg-primary text-white ms-2';
            badgeFilter.style.display = 'inline-block';
            btnClearFilter.style.display = 'inline-block';
            
            // 计算局部 KPI
            let fCount = filteredDetails.length;
            let fDur = 0.0;
            let fLong = 0;
            let fRepeat = 0;
            filteredDetails.forEach(item => {
                fDur += item.duration;
                if (item.is_long) fLong++;
                if (item.is_repeat) fRepeat++;
            });
            let fAvg = fCount > 0 ? (fDur / fCount).toFixed(2) : "0.00";
            
            summaryDiv.innerHTML = `<div><i class="mdi mdi-filter-outline me-1"></i> <strong>当期过滤条件：${conditionsText}</strong> 的局部统计：共发生故障 <strong class="text-primary">${fCount}</strong> 次，累计时长 <strong class="text-primary">${fDur.toFixed(2)}</strong> 小时，平均故障时长 <strong class="text-primary">${fAvg}</strong> 小时。其中长时故障（≥6h） <strong class="text-warning text-dark">${fLong}</strong> 条，涉及历史重复故障 <strong class="text-purple">${fRepeat}</strong> 条。</div>`;
            summaryDiv.classList.remove('d-none');
            
        } else {
            badgeFilter.style.display = 'none';
            btnClearFilter.style.display = 'none';
            summaryDiv.classList.add('d-none');
        }

        const tbody = document.getElementById('details-tbody');
        if (filteredDetails.length === 0) {
            tbody.innerHTML = `<tr><td colspan="10" class="text-center py-4 text-muted">包含过滤条件下，无可展示的故障数据</td></tr>`;
            return;
        }

        const html = filteredDetails.map(item => {
            let badges = '';
            if (item.is_repeat) badges += '<span class="badge bg-purple text-white ms-1">重复</span>';
            if (item.is_long) badges += '<span class="badge bg-warning text-dark ms-1">≥6h</span>';

            return `<tr>
                <td><a href="${item.url}" target="_blank">${item.fault_number}</a></td>
                <td>${item.fault_occurrence_time}</td>
                <td>${item.fault_recovery_time}</td>
                <td><strong class="${item.is_long ? 'text-danger' : ''}">${item.duration}</strong></td>
                <td>${item.category}</td>
                <td>${item.resource_type}</td>
                <td>${item.province}</td>
                <td>${item.reason}</td>
                <td><small>${item.site_a}${item.site_z ? ' &rarr; ' + item.site_z : ''}</small></td>
                <td>${badges}</td>
            </tr>`;
        }).join('');
        tbody.innerHTML = html;
    }

    function formatPieSliceLabel(params) {
        if (!params.value) return params.name;
        return `${params.name}\n${params.value}次 ${params.percent}%`;
    }

    // ---------------- 下钻事件处理 ----------------
    function handleChartClick(params, fieldName) {
        if (!params.name) return;
        activeFilterField = fieldName;
        activeFilterValue = params.name;
        activeFilterExtraField = null;
        activeFilterExtraValue = null;
        activeFilterLabel = null;
        // 滚动到下方的表格
        const tbl = document.getElementById('details-tbody');
        if (tbl) {
            tbl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        renderDetailsTable();
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

        const tbl = document.getElementById('details-tbody');
        if (tbl) {
            tbl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        renderDetailsTable();
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
        
        renderDetailsTable();
    });

    // ---------------- 业务故障统计 ----------------
    let serviceDataLoaded = false;

    async function loadServiceData() {
        setServiceCardsLoading('service-cards-container');
        setServiceCardsLoading('circuit-service-cards-container');

        let url = `${window.SERVICE_STATISTICS_DATA_API}?${buildTimeParams()}`;

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Network response error');
            const data = await response.json();

            if (data.period && data.period.start) {
                const periodEl = document.getElementById('period-display');
                periodEl.innerHTML = formatStatisticsPeriodLabel(selFilterType.value, inputDate.value, data.period);
                updatePeriodLabelState(periodEl, data.period);
            }

            const services = data.services || [];
            renderServiceCards(getServicesByType(services, '裸纤业务'), 'service-cards-container', '裸纤业务');
            renderServiceCards(getServicesByType(services, '电路业务'), 'circuit-service-cards-container', '电路业务');
            serviceDataLoaded = true;
        } catch (error) {
            console.error('Service data fetch error:', error);
            setServiceCardsError('service-cards-container');
            setServiceCardsError('circuit-service-cards-container');
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

    function getServicesByType(services, serviceType) {
        return services.filter(svc => svc.type === serviceType);
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
        const unitHtml = metric.unit ? `<span class="statistics-strip-card-unit">${metric.unit}</span>` : '';
        const detailHtml = metric.detail ? `<div class="statistics-strip-card-detail">${metric.detail}</div>` : '';
        return `
            <div class="statistics-strip-card-metric">
                <div class="statistics-strip-card-value-row">
                    <span class="statistics-strip-card-value ${valueClass}">${valueText}</span>
                    ${unitHtml}
                </div>
                ${detailHtml}
                <div class="statistics-strip-card-label">${metric.label}</div>
            </div>`;
    }

    function renderStripCard(card) {
        const footer = escapeHtml(card.footer);
        return `
            <div class="statistics-strip-card service-strip-card">
                <div class="statistics-strip-card-body">
                    <div class="statistics-strip-card-metrics">
                        ${card.metrics.map(renderStripMetric).join('')}
                    </div>
                </div>
                <div class="statistics-strip-card-footer" title="${footer}">${footer}</div>
            </div>`;
    }

    function renderServiceCards(services, containerId, emptyServiceType) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (services.length === 0) {
            container.innerHTML = `<div class="col-12 text-center text-muted py-5"><i class="mdi mdi-information-outline me-1"></i> 当前时间范围内无${emptyServiceType}故障记录</div>`;
            return;
        }

        const html = services.map(svc => {
            let slaColor = '#16a34a'; // green
            if (svc.sla < 99) {
                slaColor = '#dc2626';
            } else if (svc.sla < 99.9) {
                slaColor = '#ea580c';
            } else if (svc.sla < 99.99) {
                slaColor = '#ca8a04';
            }

            let catParts = [];
            if (svc.break_count > 0) catParts.push(`中断 ${formatCardCountValue(svc.break_count)}`);
            if (svc.jitter_count > 0) catParts.push(`抖动 ${formatCardCountValue(svc.jitter_count)}`);
            if (svc.degrade_count > 0) catParts.push(`劣化 ${formatCardCountValue(svc.degrade_count)}`);
            if (svc.other_count > 0) catParts.push(`其他 ${formatCardCountValue(svc.other_count)}`);
            let catDetail = catParts.length > 0 ? catParts.join(' | ') : svc.type;

            return renderStripCard({
                footer: svc.name,
                metrics: [
                    { label: '故障总数', value: svc.count, unit: '次', detail: catDetail },
                    { label: '累计时长', value: svc.total_duration, unit: '小时' },
                    { label: '平均时长', value: svc.avg_duration, unit: '小时' },
                    { label: '长时故障', value: svc.long_count, unit: '次', valueClass: svc.long_count > 0 ? 'text-danger' : 'text-indigo' },
                    { label: '重复故障', value: svc.repeat_count, unit: '次', valueClass: svc.repeat_count > 0 ? 'text-purple' : 'text-indigo' },
                    { label: 'SLA', value: svc.sla, unit: '%', valueClass: '', detail: `<span style="color:${slaColor};">可用率</span>` },
                ],
            });
        }).join('');

        container.innerHTML = html;
    }

    // ---------------- Tab 切换联动 ----------------
    function loadActiveTab() {
        const activeTab = document.querySelector('#statisticsTab .nav-link.active');
        if (activeTab && (activeTab.id === 'tab-service-btn' || activeTab.id === 'tab-circuit-service-btn')) {
            loadServiceData();
        } else {
            loadData();
        }
    }

    // Tab 切换时加载对应数据
    const tabEl = document.getElementById('statisticsTab');
    if (tabEl) {
        tabEl.addEventListener('shown.bs.tab', function(event) {
            if (event.target.id === 'tab-service-btn' || event.target.id === 'tab-circuit-service-btn') {
                loadServiceData();
            } else if (event.target.id === 'tab-physical-btn') {
                loadData();
                setTimeout(() => {
                    resizeStatisticsCharts();
                }, 100);
            }
        });
    }

    // ---------------- 初始化启动 ----------------
    updateDateSelectors();
    loadData();
});

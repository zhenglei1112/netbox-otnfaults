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

    window.addEventListener('resize', () => {
        chartResource.resize();
        chartProvince.resize();
        chartReason.resize();
        if (chartHistogram) chartHistogram.resize();
    });

    // ---------------- 统一事件绑定 ----------------
    // 点击下钻
    chartResource.on('click', params => handleChartClick(params, 'resource_type'));
    chartProvince.on('click', params => handleChartClick(params, 'province'));
    chartReason.on('click', params => handleChartClick(params, 'reason'));
    
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
    let activeFilterField = null; // 'resource_type', 'province', 'reason'
    let activeFilterValue = null;
    let activeFilterLabel = null;

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
    let cableBreakMapManualBackdrop = null;

    const badgeFilter = document.getElementById('drill-down-filter-badge');
    const btnClearFilter = document.getElementById('btn-clear-filter');

    function setCableBreakMapLoading(visible) {
        if (!cableBreakMapLoading) return;
        cableBreakMapLoading.classList.toggle('d-none', !visible);
    }

    function openCableBreakMapModal() {
        if (!cableBreakMapModal || !cableBreakMapIframe || !window.STATISTICS_CABLE_BREAK_MAP_URL) return;
        setCableBreakMapLoading(true);
        cableBreakMapIframe.src = `${window.STATISTICS_CABLE_BREAK_MAP_URL}?modal=true&${buildTimeParams()}`;
        showCableBreakMapModalFallback();
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
        const date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
        const dayNumber = date.getUTCDay() || 7;
        date.setUTCDate(date.getUTCDate() + 4 - dayNumber);
        const isoYear = date.getUTCFullYear();
        const yearStart = new Date(Date.UTC(isoYear, 0, 1));
        const isoWeek = Math.ceil((((date - yearStart) / 86400000) + 1) / 7);
        return { year: isoYear, week: isoWeek };
    }

    function parseDateValue(dateValue) {
        const parts = dateValue.split('-').map(Number);
        return new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
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
        return `${date.getUTCFullYear()}.${padDatePart(date.getUTCMonth() + 1)}.${padDatePart(date.getUTCDate())}`;
    }

    function formatInputDate(date) {
        return `${date.getUTCFullYear()}-${padDatePart(date.getUTCMonth() + 1)}-${padDatePart(date.getUTCDate())}`;
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
        const dayNumber = date.getUTCDay() || 7;
        const weekStart = new Date(date);
        weekStart.setUTCDate(date.getUTCDate() - dayNumber + 1);
        const weekEnd = new Date(weekStart);
        weekEnd.setUTCDate(weekStart.getUTCDate() + 6);
        return { weekStart, weekEnd };
    }

    function getMonthWeekOrdinal(weekStart, monthDate) {
        const firstDay = new Date(Date.UTC(monthDate.getUTCFullYear(), monthDate.getUTCMonth(), 1));
        const firstDayNumber = firstDay.getUTCDay() || 7;
        const firstWeekStart = new Date(firstDay);
        firstWeekStart.setUTCDate(firstDay.getUTCDate() - firstDayNumber + 1);
        return Math.floor((weekStart - firstWeekStart) / (7 * 86400000)) + 1;
    }

    function getYearEndDate(date) {
        return new Date(Date.UTC(date.getUTCFullYear(), 11, 31));
    }

    function getHalfYearRange(date) {
        const year = date.getUTCFullYear();
        const half = getHalfYearPart(date.getUTCMonth() + 1);
        const startMonth = half === 1 ? 0 : 6;
        const endMonth = half === 1 ? 5 : 11;
        return {
            half,
            start: new Date(Date.UTC(year, startMonth, 1)),
            end: new Date(Date.UTC(year, endMonth + 1, 0))
        };
    }

    function getQuarterRange(date) {
        const year = date.getUTCFullYear();
        const quarter = getQuarterPart(date.getUTCMonth() + 1);
        const startMonth = (quarter - 1) * 3;
        return {
            quarter,
            start: new Date(Date.UTC(year, startMonth, 1)),
            end: new Date(Date.UTC(year, startMonth + 3, 0))
        };
    }

    function getMonthEndDate(date) {
        return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0));
    }

    function shiftSelectedPeriod(direction) {
        const type = selFilterType.value;
        const date = parseDateValue(inputDate.value);

        if (type === 'year') {
            date.setUTCFullYear(date.getUTCFullYear() + direction);
        }
        if (type === 'half') {
            date.setUTCMonth(date.getUTCMonth() + (direction * 6));
        }
        if (type === 'quarter') {
            date.setUTCMonth(date.getUTCMonth() + (direction * 3));
        }
        if (type === 'month') {
            date.setUTCMonth(date.getUTCMonth() + direction);
        }
        if (type === 'week') {
            date.setUTCDate(date.getUTCDate() + (direction * 7));
        }

        inputDate.value = formatInputDate(date);
        loadActiveTab();
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
        const year = date.getUTCFullYear();
        const month = date.getUTCMonth() + 1;

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
            const weekYear = weekLabelDate.getUTCFullYear();
            const weekMonth = weekLabelDate.getUTCMonth() + 1;
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

    function buildTimeParams() {
        const type = selFilterType.value;
        const selectedDate = inputDate.value;
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
        if (repeatEl) repeatEl.textContent = kpis.repeat_faults_count;
        
        const periodStrMap = { 'year': '上年', 'half': '上半年', 'quarter': '上季度', 'month': '上月', 'week': '上周' };
        const label = periodStrMap[type] || '上期';
        
        function renderDiff(elId, current, prev, unit) {
            const el = document.getElementById(elId);
            if (!el) return;
            if (!prevKpis) { el.innerHTML = ''; return; }
            let diff = current - prev;
            if (!Number.isInteger(diff)) diff = parseFloat(diff.toFixed(2));
            
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
            if (!Number.isInteger(diff)) diff = parseFloat(diff.toFixed(2));

            if (diff > 0) {
                el.innerHTML = `<span class="text-danger fw-bold">⬆${diff}</span>`;
            } else if (diff < 0) {
                el.innerHTML = `<span class="text-success fw-bold">⬇${Math.abs(diff)}</span>`;
            } else {
                el.innerHTML = '';
            }
        }
        
        renderCompactMetricDiff('kpi-repeat-faults-diff', kpis.repeat_faults_count, prevKpis.repeat_faults_count);
    }

    function renderOverallSummary(kpis, chartsData, prevChartsData) {
        const overallTotal = document.getElementById('kpi-overall-total');
        const categoriesList = document.getElementById('kpi-overall-categories-flex-list');
        if (!overallTotal || !categoriesList) return;

        overallTotal.textContent = kpis.total_count;

        let categories = (chartsData && chartsData.category) || [];
        if (categories.length === 0) {
            categories = [{name: '--', value: 0}];
        }

        const prevCategories = (prevChartsData && prevChartsData.category) || [];
        let htmlContent = buildFlexGroup(categories, "起", "故障分类", "text-indigo", prevCategories);
        categoriesList.innerHTML = htmlContent;
    }

    function formatTrendDiff(currentVal, prevVal) {
        const cur = parseFloat(currentVal);
        const prev = parseFloat(prevVal);
        const diff = cur - prev;
        return Number.isInteger(diff) ? String(diff) : diff.toFixed(2);
    }

    function buildTrendArrow(currentVal, prevVal) {
        if (prevVal === undefined || prevVal === null) return '';
        const cur = parseFloat(currentVal);
        const prev = parseFloat(prevVal);
        if (isNaN(cur) || isNaN(prev) || cur === prev) return '';
        const symbol = cur > prev ? '+' : '';
        const diffText = `${symbol}${formatTrendDiff(cur, prev)}`;
        if (cur > prev) {
            return `<span class="statistics-trend-diff text-danger">⬆ ${diffText}</span>`;
        } else {
            return `<span class="statistics-trend-diff text-success">⬇ ${diffText}</span>`;
        }
    }

    function renderTrendBesideMetric(metricEl, currentValue, previousValue) {
        if (!metricEl) return;
        const metricTrendContainer = metricEl.parentElement;
        if (!metricTrendContainer || !metricTrendContainer.parentElement) return;

        let trendEl = metricTrendContainer.parentElement.querySelector('.statistics-metric-trend');
        if (!trendEl) {
            trendEl = document.createElement('span');
            trendEl.className = 'statistics-metric-trend statistics-kpi-trend-row';
            metricTrendContainer.parentElement.insertBefore(trendEl, metricTrendContainer.nextSibling);
        }
        trendEl.innerHTML = buildTrendArrow(currentValue, previousValue);
    }

    function buildFlexItemCore(value, unit, title, colorClass = "text-primary", prevValue, filterField, filterValue) {
        const arrow = buildTrendArrow(value, prevValue);
        const filterClass = filterField ? " statistics-drill-metric" : "";
        const filterAttrs = filterField
            ? ` data-filter-field="${filterField}" data-filter-value="${filterValue}" data-filter-label="${title}"`
            : "";
        return `
            <div class="text-center${filterClass}"${filterAttrs}>
                <div class="fs-3 fw-bold ${colorClass} lh-1">${value}<span class="ms-1 text-muted fw-normal" style="font-size: 13px;">${unit}</span></div>
                <div class="text-muted mt-1" style="font-size: 12px;">${title}</div>
                ${arrow ? `<div class="statistics-kpi-trend-row">${arrow}</div>` : ''}
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
            groupHtml += buildFlexItemCore(val, unit, name, colorClass, prevVal, filterField, name);
        });
        groupHtml += `</div>`;
        if (groupTitle) {
            groupHtml += `<span class="statistics-kpi-group-title">${groupTitle}</span>`;
        }
        groupHtml += `</div>`;
        return groupHtml;
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
        const durationTotalEl = document.getElementById('cable-break-total-duration');
        const longTotalEl = document.getElementById('cable-break-long-total');
        const longDurationTotalEl = document.getElementById('cable-break-long-duration-total');
        if (!totalEl || !longTotalEl) return;

        overview = overview || {};
        prevOverview = prevOverview || {};
        totalEl.textContent = overview.total_count || 0;
        if (durationTotalEl) durationTotalEl.textContent = overview.total_duration ? overview.total_duration.toFixed(2) : "0.00";

        renderTrendBesideMetric(totalEl, overview.total_count || 0, prevOverview.total_count);

        // 卡片1: 中断起数
        let htmlCount = "";
        const prevReasonTop3 = prevOverview.reason_top3 || [];
        const prevSourceCounts = prevOverview.source_counts || [];
        let reasonTop3 = overview.reason_top3 || [];
        if (reasonTop3.length === 0) reasonTop3 = [{name: '--', value: 0}];
        htmlCount += buildFlexGroup(reasonTop3, "起", "原因TOP3", "text-indigo", prevReasonTop3, "reason");

        let sourceCounts = overview.source_counts || [];
        if (sourceCounts.length === 0) sourceCounts = [{name: '--', value: 0}];
        htmlCount += buildFlexGroup(sourceCounts, "起", "光缆属性", "text-indigo", prevSourceCounts, "source_group");

        const countList = document.getElementById('cable-break-count-flex-list');
        if (countList) countList.innerHTML = htmlCount;

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
        longTotalEl.textContent = longTotal;

        renderTrendBesideMetric(longTotalEl, longTotal, prevLongTotal);

        if (longItems.length === 0) longItems = [{name: '--', value: 0}];
        htmlLong += buildFlexGroup(longItems, "起", "历时分布", "text-indigo", prevLongItems, "duration_bucket");
        
        const longList = document.getElementById('cable-break-long-flex-list');
        if (longList) longList.innerHTML = htmlLong;

        // 卡片3: 长时中断历时
        let htmlLongDuration = "";
        const longDurationBuckets = overview.long_duration_bucket_durations || {};
        const prevLongDurationBuckets = prevOverview.long_duration_bucket_durations || {};
        let longDurationTotal = Number(overview.long_duration_total || 0);
        let prevLongDurationTotal = Number(prevOverview.long_duration_total || 0);
        let longDurationItems = orderedBuckets.map(b => {
            const duration = Number(longDurationBuckets[b] || 0);
            return { value: duration.toFixed(2), name: b };
        });
        let prevLongDurationItems = orderedBuckets.map(b => {
            const duration = Number(prevLongDurationBuckets[b] || 0);
            return { value: duration.toFixed(2), name: b };
        });

        if (longDurationTotalEl) {
            longDurationTotalEl.textContent = longDurationTotal.toFixed(2);
            renderTrendBesideMetric(longDurationTotalEl, longDurationTotal, prevLongDurationTotal);
        }

        if (longDurationItems.length === 0) longDurationItems = [{name: '--', value: "0.00"}];
        htmlLongDuration += buildFlexGroup(longDurationItems, "时", "历时分布", "text-indigo", prevLongDurationItems, "duration_bucket");
        
        const longDurationList = document.getElementById('cable-break-long-duration-flex-list');
        if (longDurationList) longDurationList.innerHTML = htmlLongDuration;

        // 卡片4: 中断总历时
        let htmlDur = "";
        const prevDurReasonTop3 = prevOverview.reason_duration_top3 || [];
        const prevDurSourceCounts = prevOverview.source_duration_counts || [];
        let durReasonItems = (overview.reason_duration_top3 || []).map(i => ({...i, value: parseFloat(i.value).toFixed(2)}));
        if (durReasonItems.length === 0) durReasonItems = [{name: '--', value: "0.00"}];
        
        let durSourceItems = (overview.source_duration_counts || []).map(i => ({...i, value: parseFloat(i.value).toFixed(2)}));
        if (durSourceItems.length === 0) durSourceItems = [{name: '--', value: "0.00"}];
        
        let prevDurReasonItems = prevDurReasonTop3.map(i => ({...i, value: parseFloat(i.value).toFixed(2)}));
        let prevDurSourceItems = prevDurSourceCounts.map(i => ({...i, value: parseFloat(i.value).toFixed(2)}));

        if (durationTotalEl) {
            const currentDuration = overview.total_duration || 0;
            durationTotalEl.textContent = currentDuration.toFixed(2);
            renderTrendBesideMetric(durationTotalEl, currentDuration, prevOverview.total_duration);
        }

        htmlDur += buildFlexGroup(durReasonItems, "时", "原因TOP3", "text-indigo", prevDurReasonItems, "reason");
        htmlDur += buildFlexGroup(durSourceItems, "时", "光缆属性", "text-indigo", prevDurSourceItems, "source_group");
        
        const durList = document.getElementById('cable-break-duration-flex-list');
        if (durList) durList.innerHTML = htmlDur;

        // 卡片5: 平均历时深度分析
        const oAvgEl = document.getElementById('cable-break-overall-avg');
        const prevMetrics = prevOverview.avg_metrics || {};
        if (oAvgEl && overview.avg_metrics) {
            const m = overview.avg_metrics;
            oAvgEl.textContent = m.overall_avg.toFixed(2);
            renderTrendBesideMetric(oAvgEl, m.overall_avg, prevMetrics.overall_avg);
            // 子指标（静态 HTML 节点直接填值 + 箭头）
            const avgFields = [
                {id: 'cable-break-valid-avg', key: 'valid_avg'},
                {id: 'cable-break-daytime-avg', key: 'daytime_avg'},
                {id: 'cable-break-nighttime-avg', key: 'nighttime_avg'},
                {id: 'cable-break-construction-avg', key: 'construction_avg'},
                {id: 'cable-break-noncons-avg', key: 'non_construction_avg'},
            ];
            avgFields.forEach(f => {
                const el = document.getElementById(f.id);
                if (el) {
                    const curV = m[f.key];
                    const prevV = prevMetrics[f.key];
                    const arrow = buildTrendArrow(curV, prevV);
                    el.innerHTML = `${curV.toFixed(2)}`;
                    
                    const parentCenter = el.closest('.text-center');
                    if (parentCenter) {
                        let trendEl = parentCenter.querySelector('.statistics-kpi-trend-row');
                        if (!trendEl) {
                            trendEl = document.createElement('div');
                            trendEl.className = 'statistics-kpi-trend-row';
                            parentCenter.appendChild(trendEl);
                        }
                        trendEl.innerHTML = arrow;
                    }
                }
            });
        }
        
        if (overview.histogram && chartHistogram) {
            let histLabels = overview.histogram.map(item => item.label);
            let histValues = overview.histogram.map(item => ({value: item.value, _percent: item.percent}));
            const histogramMaxValue = Math.max(...overview.histogram.map(item => item.value), 0);
            
            chartHistogram.setOption({
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'shadow' },
                    formatter: function(params) {
                        let p = params[0];
                        return `${p.name} 小时<br/>数量：${p.value}起 (${p.data._percent}%)`;
                    }
                },
                grid: { top: 62, left: '3%', right: '4%', bottom: '10%', containLabel: true },
                xAxis: { 
                    type: 'category', 
                    data: histLabels,
                    name: '历时(小时)',
                    axisLabel: { interval: 0, fontSize: 11 }
                },
                yAxis: {
                    type: 'value',
                    name: '起数',
                    minInterval: 1,
                    max: histogramMaxValue > 0 ? Math.ceil(histogramMaxValue * 1.25) : 1
                },
                series: [{
                    type: 'bar',
                    barWidth: '60%',
                    itemStyle: { color: '#206bc4', borderRadius: [2, 2, 0, 0] },
                    label: {
                        show: true,
                        position: 'top',
                        formatter: function(params) {
                            if(params.value === 0) return '';
                            return `${params.value}起\n${params.data._percent}%`;
                        },
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
        // 1. 光缆属性 (Pie)
        const resourceColorMap = { '自建': '#206bc4', '协调': '#4299e1', '租赁': '#66b2ff', '未指定': '#cbd5e1' };
        chartResource.setOption({
            tooltip: { 
                trigger: 'item', 
                formatter: params => {
                    let avg = params.value > 0 ? (params.data._duration / params.value).toFixed(2) : "0.00";
                    return `${params.marker}${params.name}: ${params.value}次 (${params.percent}%)<br/>` +
                           `<span style="margin-left:14px;">总历时: ${params.data._duration} 小时</span><br/>` +
                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;
                }
            },
            legend: { bottom: 0, type: 'scroll' },
            series: [{
                type: 'pie',
                radius: ['45%', '75%'],
                center: ['50%', '45%'],
                label: {
                    show: true,
                    formatter: formatPieSliceLabel,
                    alignTo: 'edge',
                    edgeDistance: 10,
                    lineHeight: 15,
                    fontSize: 11
                },
                itemStyle: {
                    color: function(params) { return resourceColorMap[params.name] || '#5470c6'; },
                    borderRadius: 5, borderColor: '#fff', borderWidth: 2
                },
                data: chartsData.resource.map(item => ({name: item.name, value: item.value, _duration: item.duration}))
            }]
        });

        // 2. 省份 (Bar 全部)
        let provData = chartsData.province;
        chartProvince.setOption({
            tooltip: { 
                trigger: 'axis', 
                axisPointer: { type: 'shadow' },
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
                axisLabel: { interval: 0, rotate: 30 }
            },
            yAxis: { type: 'value' },
            series: [{
                type: 'bar',
                label: { show: true, position: 'top' },
                itemStyle: { color: '#206bc4', borderRadius: [4, 4, 0, 0] },
                data: provData.map(item => ({value: item.value, _duration: item.duration}))
            }]
        });

        // 3. 一级原因 (Pie)
        chartReason.setOption({
            color: ['#206bc4', '#4299e1', '#66b2ff', '#99ccff', '#b3d4ff', '#cbd5e1'],
            tooltip: { 
                trigger: 'item', 
                formatter: params => {
                    let avg = params.value > 0 ? (params.data._duration / params.value).toFixed(2) : "0.00";
                    return `${params.marker}${params.name}: ${params.value}次 (${params.percent}%)<br/>` +
                           `<span style="margin-left:14px;">总历时: ${params.data._duration} 小时</span><br/>` +
                           `<span style="margin-left:14px;">平均历时: ${avg} 小时</span>`;
                }
            },
            legend: { bottom: 0, type: 'scroll' },
            series: [{
                type: 'pie',
                radius: '65%',
                center: ['50%', '45%'],
                label: {
                    show: true,
                    formatter: formatPieSliceLabel,
                    alignTo: 'edge',
                    edgeDistance: 10,
                    lineHeight: 15,
                    fontSize: 11
                },
                data: chartsData.reason.map(item => ({name: item.name, value: item.value, _duration: item.duration})),
                emphasis: {
                    itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
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
            filteredDetails = filteredDetails.filter(item => applyDetailFilter(item, activeFilterField, activeFilterValue));
            
            let filterName = '';
            let filterValueDisp = activeFilterLabel || activeFilterValue;
            if (activeFilterField === 'resource_type') filterName = '光缆属性';
            else if (activeFilterField === 'source_group') filterName = '光缆属性';
            else if (activeFilterField === 'province') filterName = '省份';
            else if (activeFilterField === 'reason') filterName = '原因';
            else if (activeFilterField === 'duration_bucket') filterName = '历时分布';
            else if (activeFilterField === 'category') filterName = '分类';
            else if (activeFilterField === 'occurrence_period') filterName = '发生时段';
            else if (activeFilterField === 'cause_group') filterName = '成因';
            else if (activeFilterField === 'is_valid_duration') { filterName = '特殊标签'; filterValueDisp = '有效平均'; }
            else if (activeFilterField === 'is_long') { filterName = '特殊标签'; filterValueDisp = '长时故障(≥6h)'; }
            else if (activeFilterField === 'is_repeat') { filterName = '特殊标签'; filterValueDisp = '历史重复故障'; }
            
            activeConditions.push(`下钻：${filterName}=${filterValueDisp}`);
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
        const container = document.getElementById('service-cards-container');
        container.innerHTML = '<div class="col-12 text-center text-muted py-5"><i class="mdi mdi-loading mdi-spin me-1"></i> 数据加载中...</div>';

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

            renderServiceCards(data.services || [], data.period_total_hours || 0);
            serviceDataLoaded = true;
        } catch (error) {
            console.error('Service data fetch error:', error);
            container.innerHTML = '<div class="col-12 text-center text-danger py-5">数据加载失败，请检查网络或刷新重试</div>';
        }
    }

    function renderServiceCards(services, periodTotalHours) {
        const container = document.getElementById('service-cards-container');

        if (services.length === 0) {
            container.innerHTML = '<div class="col-12 text-center text-muted py-5"><i class="mdi mdi-information-outline me-1"></i> 当前时间范围内无业务故障记录</div>';
            return;
        }

        const html = services.map(svc => {
            // SLA 颜色
            let slaColor = '#16a34a'; // green
            let slaBg = '#dcfce7';
            if (svc.sla < 99) {
                slaColor = '#dc2626'; slaBg = '#fee2e2';
            } else if (svc.sla < 99.9) {
                slaColor = '#ea580c'; slaBg = '#fff7ed';
            } else if (svc.sla < 99.99) {
                slaColor = '#ca8a04'; slaBg = '#fefce8';
            }
            let slaPercent = Math.min(100, svc.sla);

            // 分类明细
            let catParts = [];
            if (svc.break_count > 0) catParts.push(`中断 <strong class="text-danger">${svc.break_count}</strong>`);
            if (svc.jitter_count > 0) catParts.push(`抖动 <strong class="text-info">${svc.jitter_count}</strong>`);
            if (svc.degrade_count > 0) catParts.push(`劣化 <strong class="text-warning">${svc.degrade_count}</strong>`);
            if (svc.other_count > 0) catParts.push(`其他 <strong>${svc.other_count}</strong>`);
            let catDetail = catParts.length > 0 ? `（${catParts.join(' | ')}）` : '';

            // 类型 badge
            let typeBadge = svc.type === '裸纤业务'
                ? '<span class="badge bg-blue text-white">裸纤</span>'
                : '<span class="badge bg-green text-white">电路</span>';

            return `<div class="col">
                <div class="card svc-card shadow-sm h-100">
                    <div class="card-body p-3">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <div class="d-flex align-items-center" style="min-width: 0;">
                                ${typeBadge}
                                <strong class="ms-2 text-truncate" title="${svc.name}">${svc.name}</strong>
                            </div>
                            <div class="sla-badge text-nowrap" style="background:${slaBg}; color:${slaColor}; border: 1px solid ${slaColor}30; border-radius:20px; padding: 4px 12px; font-size:13px; font-weight:600;">
                                SLA ${svc.sla.toFixed(2)}%
                            </div>
                        </div>

                        <div class="row g-2 mb-3">
                            <div class="col-12">
                                <div class="svc-stat-row">
                                    <span class="text-muted">故障总数</span>
                                    <span><strong class="text-primary fs-5">${svc.count}</strong> 次 ${catDetail}</span>
                                </div>
                            </div>
                        </div>

                        <div class="row g-2 mb-3">
                            <div class="col-6">
                                <div class="svc-stat-row">
                                    <span class="text-muted">累计时长</span>
                                    <span><strong>${svc.total_duration}</strong> 小时</span>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="svc-stat-row">
                                    <span class="text-muted">平均时长</span>
                                    <span><strong>${svc.avg_duration}</strong> 小时</span>
                                </div>
                            </div>
                        </div>

                        <div class="row g-2 mb-3">
                            <div class="col-6">
                                <div class="svc-stat-row">
                                    <span class="text-muted">长时故障(≥6h)</span>
                                    <span><strong class="${svc.long_count > 0 ? 'text-danger' : ''}">${svc.long_count}</strong></span>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="svc-stat-row">
                                    <span class="text-muted">重复故障</span>
                                    <span><strong class="${svc.repeat_count > 0 ? 'text-purple' : ''}">${svc.repeat_count}</strong></span>
                                </div>
                            </div>
                        </div>

                        <div class="svc-sla-bar">
                            <div class="d-flex justify-content-between mb-1">
                                <small class="text-muted">可用率</small>
                                <small style="color:${slaColor}; font-weight:600;">${svc.sla.toFixed(2)}%</small>
                            </div>
                            <div class="progress" style="height: 6px; border-radius: 3px;">
                                <div class="progress-bar" role="progressbar" style="width: ${slaPercent}%; background-color: ${slaColor}; border-radius: 3px;" aria-valuenow="${slaPercent}" aria-valuemin="0" aria-valuemax="100"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
        }).join('');

        container.innerHTML = html;
    }

    // ---------------- Tab 切换联动 ----------------
    function loadActiveTab() {
        const activeTab = document.querySelector('#statisticsTab .nav-link.active');
        if (activeTab && activeTab.id === 'tab-service-btn') {
            loadServiceData();
        } else {
            loadData();
        }
    }

    // Tab 切换时加载对应数据
    const tabEl = document.getElementById('statisticsTab');
    if (tabEl) {
        tabEl.addEventListener('shown.bs.tab', function(event) {
            if (event.target.id === 'tab-service-btn') {
                loadServiceData();
            } else if (event.target.id === 'tab-physical-btn') {
                loadData();
                // 切回时需要 resize echarts
                setTimeout(() => {
                    chartResource.resize();
                    chartProvince.resize();
                    chartReason.resize();
                }, 100);
            }
        });
    }

    // ---------------- 初始化启动 ----------------
    updateDateSelectors();
    loadData();
});

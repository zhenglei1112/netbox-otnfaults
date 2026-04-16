/**
 * 故障统计交互脚本
 */
document.addEventListener("DOMContentLoaded", function() {
    // ---------------- 图表实例初始化 ----------------
    let chartResource = echarts.init(document.getElementById('chart-resource'));
    let chartProvince = echarts.init(document.getElementById('chart-province'));
    let chartReason = echarts.init(document.getElementById('chart-reason'));
    let chartCategory = echarts.init(document.getElementById('chart-category'));
    
    let excludedCategories = {
        resource_type: new Set(),
        province: new Set(),
        reason: new Set(),
        category: new Set()
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
        chartCategory.resize();
    });

    // ---------------- 统一事件绑定 ----------------
    // 点击下钻
    chartResource.on('click', params => handleChartClick(params, 'resource_type'));
    chartProvince.on('click', params => handleChartClick(params, 'province'));
    chartReason.on('click', params => handleChartClick(params, 'reason'));
    chartCategory.on('click', params => handleChartClick(params, 'category'));
    
    // 图例切换（过滤剔除）
    chartResource.on('legendselectchanged', params => { updateExcludedSet('resource_type', params.selected); renderDetailsTable(); });
    chartProvince.on('legendselectchanged', params => { updateExcludedSet('province', params.selected); renderDetailsTable(); });
    chartReason.on('legendselectchanged', params => { updateExcludedSet('reason', params.selected); renderDetailsTable(); });
    chartCategory.on('legendselectchanged', params => { updateExcludedSet('category', params.selected); renderDetailsTable(); });

    // KPI 卡片点击下钻
    document.getElementById('card-long-faults').addEventListener('click', () => handleChartClick({name: true}, 'is_long'));
    document.getElementById('card-repeat-faults').addEventListener('click', () => handleChartClick({name: true}, 'is_repeat'));

    let currentAllDetails = []; // 保存后端返回的全部详情数据
    let activeFilterField = null; // 'resource_type', 'province', 'reason', 'category'
    let activeFilterValue = null;

    // ---------------- DOM 元素 ----------------
    const selFilterType = document.getElementById('filterType');
    const inputDate = document.getElementById('filterDate');

    const badgeFilter = document.getElementById('drill-down-filter-badge');
    const btnClearFilter = document.getElementById('btn-clear-filter');

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

    function padDatePart(value) {
        return String(value).padStart(2, '0');
    }

    function formatDotDate(date) {
        return `${date.getUTCFullYear()}.${padDatePart(date.getUTCMonth() + 1)}.${padDatePart(date.getUTCDate())}`;
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

    function getMonthEndDate(date) {
        return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0));
    }

    function updatePeriodLabelState(periodEl, period) {
        periodEl.classList.remove('text-success');
        periodEl.classList.remove('text-warning');
        if (period && period.end === '当前') {
            periodEl.classList.add('text-success');
        } else if (period && period.is_future) {
            periodEl.classList.add('text-warning');
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
            return `年统计 ${year}年（${rangeStart}至${rangeEnd}）`;
        }
        if (type === 'month') {
            const rangeStart = formatPeriodStartDate(period, date);
            const rangeEnd = formatPeriodEndDate(period && period.end, getMonthEndDate(date));
            return `月统计 ${year}年${month}月（${rangeStart}至${rangeEnd}）`;
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
            renderCharts(data.charts);
        } catch (error) {
            console.error('Fetch error:', error);
            document.getElementById('details-tbody').innerHTML = '<tr><td colspan="10" class="text-danger text-center py-4">数据加载失败，请检查网络或刷新重试</td></tr>';
        }
    }

    // ---------------- 渲染部分 ----------------
    function renderKPIs(kpis, prevKpis, type) {
        document.getElementById('kpi-total-cnt').textContent = kpis.total_count;
        document.getElementById('kpi-total-dur').textContent = kpis.total_duration;
        document.getElementById('kpi-avg-dur').textContent = kpis.avg_duration;
        document.getElementById('kpi-long-faults').textContent = kpis.long_faults_count;
        document.getElementById('kpi-repeat-faults').textContent = kpis.repeat_faults_count;
        
        const periodStrMap = { 'year': '上年', 'month': '上月', 'week': '上周' };
        const label = periodStrMap[type] || '上期';
        
        function renderDiff(elId, current, prev, unit) {
            const el = document.getElementById(elId);
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
        
        renderDiff('kpi-total-cnt-diff', kpis.total_count, prevKpis.total_count, '条');
        renderDiff('kpi-total-dur-diff', kpis.total_duration, prevKpis.total_duration, '小时');
        renderDiff('kpi-avg-dur-diff', kpis.avg_duration, prevKpis.avg_duration, '小时');
        renderDiff('kpi-long-faults-diff', kpis.long_faults_count, prevKpis.long_faults_count, '条');
        renderDiff('kpi-repeat-faults-diff', kpis.repeat_faults_count, prevKpis.repeat_faults_count, '条');
    }

    function renderCharts(chartsData) {
        // 1. 光缆属性 (Pie)
        const resourceColorMap = { '自建': '#10B981', '协调': '#3B82F6', '租赁': '#8B5CF6', '未指定': '#9CA3AF' };
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
                itemStyle: { color: '#3B82F6', borderRadius: [4, 4, 0, 0] },
                data: provData.map(item => ({value: item.value, _duration: item.duration}))
            }]
        });

        // 3. 一级原因 (Pie)
        chartReason.setOption({
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
                data: chartsData.reason.map(item => ({name: item.name, value: item.value, _duration: item.duration})),
                emphasis: {
                    itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
                }
            }]
        });

        // 4. 故障类型 (Pie)
        const categoryColorMap = {
            '光缆中断': '#8B5CF6',
            '空调故障': '#14B8A6',
            '光缆劣化': '#F97316',
            '光缆抖动': '#06B6D4',
            '设备故障': '#EC4899',
            '供电故障': '#6366F1'
        };
        chartCategory.setOption({
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
                itemStyle: {
                    color: function(params) { return categoryColorMap[params.name] || undefined; },
                    borderRadius: 5, borderColor: '#fff', borderWidth: 2
                },
                data: chartsData.category.map(item => ({name: item.name, value: item.value, _duration: item.duration})),
                emphasis: {
                    itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
                }
            }]
        });
    }

    // ---------------- 渲染下钻表格 ----------------
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
        if (excludedCategories.category.size > 0) {
            filteredDetails = filteredDetails.filter(item => !excludedCategories.category.has(item.category));
            activeConditions.push(`排除故障类型[${Array.from(excludedCategories.category).join(', ')}]`);
        }
        
        const summaryDiv = document.getElementById('filtered-kpi-summary');

        // 2. 应用单点下钻过滤
        if (activeFilterField && activeFilterValue !== null) {
            filteredDetails = filteredDetails.filter(item => item[activeFilterField] === activeFilterValue);
            
            let filterName = '';
            let filterValueDisp = activeFilterValue;
            if (activeFilterField === 'resource_type') filterName = '光缆属性';
            else if (activeFilterField === 'province') filterName = '省份';
            else if (activeFilterField === 'reason') filterName = '原因';
            else if (activeFilterField === 'category') filterName = '故障类型';
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

    // ---------------- 下钻事件处理 ----------------
    function handleChartClick(params, fieldName) {
        if (!params.name) return;
        activeFilterField = fieldName;
        activeFilterValue = params.name;
        // 滚动到下方的表格
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
        
        excludedCategories.resource_type.clear();
        excludedCategories.province.clear();
        excludedCategories.reason.clear();
        excludedCategories.category.clear();
        
        chartResource.dispatchAction({ type: 'legendAllSelect' });
        chartReason.dispatchAction({ type: 'legendAllSelect' });
        chartCategory.dispatchAction({ type: 'legendAllSelect' });
        
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
                    chartCategory.resize();
                }, 100);
            }
        });
    }

    // ---------------- 初始化启动 ----------------
    updateDateSelectors();
    loadData();
});

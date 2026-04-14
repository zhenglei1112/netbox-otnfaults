/**
 * 故障统计看板交互脚本
 */
document.addEventListener("DOMContentLoaded", function() {
    // ---------------- 图表实例初始化 ----------------
    let chartResource = null;
    let chartProvince = null;
    let chartReason = null;
    
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

    // 初始化只执行一次
    chartResource = echarts.init(document.getElementById('chart-resource'));
    chartProvince = echarts.init(document.getElementById('chart-province'));
    chartReason = echarts.init(document.getElementById('chart-reason'));

    window.addEventListener('resize', () => {
        chartResource.resize();
        chartProvince.resize();
        chartReason.resize();
    });

    // 绑定点击事件 (下钻)
    chartResource.on('click', params => handleChartClick(params, 'resource_type'));
    chartProvince.on('click', params => handleChartClick(params, 'province'));
    chartReason.on('click', params => handleChartClick(params, 'reason'));
    
    // 绑定图例切换事件 (过滤剔除)
    chartResource.on('legendselectchanged', params => { updateExcludedSet('resource_type', params.selected); renderDetailsTable(); });
    chartProvince.on('legendselectchanged', params => { updateExcludedSet('province', params.selected); renderDetailsTable(); });
    chartReason.on('legendselectchanged', params => { updateExcludedSet('reason', params.selected); renderDetailsTable(); });

    document.getElementById('card-long-faults').addEventListener('click', () => handleChartClick({name: true}, 'is_long'));
    document.getElementById('card-repeat-faults').addEventListener('click', () => handleChartClick({name: true}, 'is_repeat'));

    let currentAllDetails = []; // 保存后端返回的全部详情数据
    let activeFilterField = null; // 'resource_type', 'province', 'reason'
    let activeFilterValue = null;

    // ---------------- DOM 元素 ----------------
    const selFilterType = document.getElementById('filterType');
    const selYear = document.getElementById('filterYear');
    const selMonth = document.getElementById('filterMonth');
    const containerWeek = document.getElementById('filterWeekContainer');
    const inputWeek = document.getElementById('filterWeek');

    const badgeFilter = document.getElementById('drill-down-filter-badge');
    const btnClearFilter = document.getElementById('btn-clear-filter');

    // ---------------- UI 联动逻辑 ----------------
    function updateDateSelectors() {
        const type = selFilterType.value;
        selYear.style.display = 'inline-block';
        selMonth.style.display = type === 'month' ? 'inline-block' : 'none';
        containerWeek.style.display = type === 'week' ? 'inline-block' : 'none';
    }

    selFilterType.addEventListener('change', () => {
        updateDateSelectors();
        loadData();
    });
    
    [selYear, selMonth, inputWeek].forEach(el => {
        el.addEventListener('change', loadData);
    });

    // ---------------- 获取数据 ----------------
    async function loadData() {
        const type = selFilterType.value;
        const year = selYear.value;
        const month = selMonth.value;
        const week = inputWeek.value;

        let url = `${window.STATISTICS_DATA_API}?filter_type=${type}&year=${year}`;
        if (type === 'month') url += `&month=${month}`;
        if (type === 'week') url += `&week=${week}`;

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
                const periodText = `数据范围: ${data.period.start} 至 ${data.period.end || '今'}`;
                document.getElementById('period-display').textContent = periodText;
            } else {
                document.getElementById('period-display').textContent = '';
            }

            renderKPIs(data.kpis, data.prev_kpis, type);
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
            tooltip: { trigger: 'item', formatter: '{b}: {c}次 ({d}%)<br/>总历时: {c|duration}时' },
            legend: { top: 'bottom' },
            series: [{
                type: 'pie',
                radius: ['40%', '70%'],
                itemStyle: {
                    color: function(params) { return resourceColorMap[params.name] || '#5470c6'; },
                    borderRadius: 5, borderColor: '#fff', borderWidth: 2
                },
                data: chartsData.resource.map(item => ({name: item.name, value: item.value, _duration: item.duration}))
            }]
        });

        // 2. 省份 (Bar Top 10)
        let provData = chartsData.province.slice(0, 10);
        chartProvince.setOption({
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
            grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: { type: 'value' },
            yAxis: { type: 'category', data: provData.map(item => item.name).reverse() },
            series: [{
                type: 'bar',
                label: { show: true, position: 'right' },
                itemStyle: { color: '#3B82F6', borderRadius: [0, 4, 4, 0] },
                data: provData.map(item => item.value).reverse()
            }]
        });

        // 3. 一级原因 (Pie)
        chartReason.setOption({
            tooltip: { trigger: 'item', formatter: '{b}: {c}次 ({d}%)' },
            legend: { top: '5%', type: 'scroll' },
            series: [{
                type: 'pie',
                radius: '50%',
                center: ['50%', '55%'],
                data: chartsData.reason.map(item => ({name: item.name, value: item.value})),
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
        
        const summaryDiv = document.getElementById('filtered-kpi-summary');

        // 2. 应用单点下钻过滤
        if (activeFilterField && activeFilterValue !== null) {
            filteredDetails = filteredDetails.filter(item => item[activeFilterField] === activeFilterValue);
            
            let filterName = '';
            let filterValueDisp = activeFilterValue;
            if (activeFilterField === 'resource_type') filterName = '光缆属性';
            else if (activeFilterField === 'province') filterName = '省份';
            else if (activeFilterField === 'reason') filterName = '原因';
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
                <td><small>${item.site_a} &rarr; ${item.site_z}</small></td>
                <td>${badges}</td>
            </tr>`;
        }).join('');
        tbody.innerHTML = html;
    }

    // ---------------- 下钻事件绑定 ----------------
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

    chartResource.on('click', params => handleChartClick(params, 'resource_type'));
    chartProvince.on('click', params => handleChartClick(params, 'province'));
    chartReason.on('click', params => handleChartClick(params, 'reason'));

    document.getElementById('card-long-faults').addEventListener('click', () => {
        handleChartClick({name: true}, 'is_long');
    });

    document.getElementById('card-repeat-faults').addEventListener('click', () => {
        handleChartClick({name: true}, 'is_repeat');
    });

    btnClearFilter.addEventListener('click', () => {
        activeFilterField = null;
        activeFilterValue = null;
        
        excludedCategories.resource_type.clear();
        excludedCategories.province.clear();
        excludedCategories.reason.clear();
        
        chartResource.dispatchAction({ type: 'legendAllSelect' });
        chartReason.dispatchAction({ type: 'legendAllSelect' });
        // province chart relies on clicking bars rather than legends so no interaction needed here for unselecting them, but clear works on our internal variable
        
        renderDetailsTable();
    });

    // ---------------- 初始化启动 ----------------
    updateDateSelectors();
    loadData();
});

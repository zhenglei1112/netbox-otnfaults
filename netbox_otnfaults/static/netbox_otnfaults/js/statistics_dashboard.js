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
        loadActiveTab();
    });
    
    [selYear, selMonth, inputWeek].forEach(el => {
        el.addEventListener('change', loadActiveTab);
    });

    // ---------------- 构建时间参数 URL ----------------
    function buildTimeParams() {
        const type = selFilterType.value;
        const year = selYear.value;
        const month = selMonth.value;
        const week = inputWeek.value;
        let params = `filter_type=${type}&year=${year}`;
        if (type === 'month') params += `&month=${month}`;
        if (type === 'week') params += `&week=${week}`;
        return params;
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
                if (data.period.is_future) {
                    periodEl.textContent = `数据范围: ${data.period.start} 至 ${data.period.end}`;
                    periodEl.classList.remove('bg-light', 'text-dark');
                    periodEl.classList.add('bg-warning', 'text-dark');
                } else {
                    const periodText = `数据范围: ${data.period.start} 至 ${data.period.end || '今'}`;
                    periodEl.textContent = periodText;
                    periodEl.classList.remove('bg-warning');
                    periodEl.classList.add('bg-light', 'text-dark');
                }
            } else {
                document.getElementById('period-display').textContent = '';
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
            grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: { type: 'value' },
            yAxis: { type: 'category', data: provData.map(item => item.name).reverse() },
            series: [{
                type: 'bar',
                label: { show: true, position: 'right' },
                itemStyle: { color: '#3B82F6', borderRadius: [0, 4, 4, 0] },
                data: provData.map(item => ({value: item.value, _duration: item.duration})).reverse()
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
                radius: '50%',
                center: ['50%', '45%'],
                data: chartsData.reason.map(item => ({name: item.name, value: item.value, _duration: item.duration})),
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
                <td><small>${item.site_a}${item.site_z ? ' &rarr; ' + item.site_z : ''}</small></td>
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
                if (data.period.is_future) {
                    periodEl.textContent = `数据范围: ${data.period.start} 至 ${data.period.end}`;
                    periodEl.classList.remove('bg-light', 'text-dark');
                    periodEl.classList.add('bg-warning', 'text-dark');
                } else {
                    periodEl.textContent = `数据范围: ${data.period.start} 至 ${data.period.end || '今'}`;
                    periodEl.classList.remove('bg-warning');
                    periodEl.classList.add('bg-light', 'text-dark');
                }
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

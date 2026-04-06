/**
 * 每周通报大屏 - 业务逻辑
 */

document.addEventListener('DOMContentLoaded', () => {
    // 自动触发数据加载
    fetchReportData();
});

function fetchReportData() {
    const api_url = window.WEEKLY_REPORT_API;
    
    fetch(api_url)
        .then(res => res.json())
        .then(data => {
            renderKPIs(data);
            renderChart(data.reasons_analysis);
            renderProvinces(data.top_provinces);
            renderMajorEvents(data.major_events, data.summary.no_const_duration);
            renderBareFiberTable(data.bare_fiber);
        })
        .catch(err => {
            console.error('API Fetch error:', err);
        });
}

function getTrendHTML(diff, suffix='') {
    if (diff > 0) {
        return `<span class="kpi-trend trend-up">↑ +${diff}${suffix}</span>`;
    } else if (diff < 0) {
        return `<span class="kpi-trend trend-down">↓ ${diff}${suffix}</span>`;
    } else {
        return `<span class="kpi-trend" style="color:#64748b">- 0${suffix}</span>`;
    }
}

function renderKPIs(data) {
    document.getElementById('period-display').innerText = `${data.period.start} - ${data.period.end}`;
    
    // KPI 1
    document.getElementById('kpi-total-cnt').innerText = data.summary.total_count;
    document.getElementById('kpi-total-diff').outerHTML = getTrendHTML(data.summary.diff_count, '次');
    
    // KPI 2
    document.getElementById('kpi-total-dur').innerText = data.summary.total_duration;
    document.getElementById('kpi-total-dur-diff').outerHTML = getTrendHTML(data.summary.diff_duration, '小时');
    
    // KPI 3 & 4
    document.getElementById('kpi-self-built').innerText = `${data.summary.self_built.count}次 / ${data.summary.self_built.duration}h`;
    document.getElementById('kpi-leased').innerText = `${data.summary.leased.count}次 / ${data.summary.leased.duration}h`;
}

function renderChart(dataList) {
    const chartDom = document.getElementById('reasonsChart');
    if (!chartDom || !window.echarts) return;
    
    const myChart = echarts.init(chartDom);
    
    const xData = dataList.map(item => item.name);
    const yData = dataList.map(item => item.value);

    const option = {
        grid: {
            top: '15%',
            left: '3%',
            right: '4%',
            bottom: '5%',
            containLabel: true
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        xAxis: {
            type: 'category',
            data: xData,
            axisLabel: {
                color: '#64748b',
                interval: 0,
                formatter: function (value) {
                    return value.length > 4 ? value.slice(0, 4) + '\n' + value.slice(4) : value;
                }
            },
            axisLine: { lineStyle: { color: '#e2e8f0' } }
        },
        yAxis: {
            type: 'value',
            minInterval: 1,
            splitLine: {
                lineStyle: { color: '#f1f5f9', type: 'dashed' }
            },
            axisLabel: { color: '#64748b' }
        },
        series: [
            {
                name: '中断次数',
                type: 'bar',
                barWidth: '40%',
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#8b5cf6' },
                        { offset: 1, color: '#3b82f6' }
                    ]),
                    borderRadius: [6, 6, 0, 0]
                },
                label: {
                    show: true,
                    position: 'top',
                    color: '#1e293b',
                    fontWeight: 600,
                    formatter: '{c}次'
                },
                data: yData
            }
        ]
    };

    myChart.setOption(option);
    
    window.addEventListener('resize', () => {
        myChart.resize();
    });
}

function renderProvinces(provinces) {
    const container = document.getElementById('provinces-container');
    container.innerHTML = '';
    
    if (!provinces || provinces.length === 0) {
        container.innerHTML = '<div class="loading-text">本周暂无省份数据</div>';
        return;
    }
    
    provinces.forEach(p => {
        const html = `
            <div class="province-card">
                <div class="prov-name">${p.province}</div>
                <div class="prov-stats">
                    <div>次数: ${p.count}次</div>
                    <div>时长: 累计${p.duration}h</div>
                    <div style="color: #64748b; margin-top:2px;">主因: ${p.main_reason}</div>
                    <div class="prov-path">${p.paths}</div>
                </div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);
    });
}

function renderMajorEvents(events, noConstDur) {
    const container = document.getElementById('major-events-container');
    container.innerHTML = '';
    
    if (events.length === 0) {
        container.innerHTML = `
            <div class="event-item" style="text-align:center; padding: 20px;">
                <span class="event-num" style="font-size:24px;">0</span> 无
            </div>
        `;
    } else {
        events.forEach(ev => {
            const html = `
                <div class="event-item">
                    <div><span class="event-num">${ev.loc}</span></div>
                    <div style="color: #64748b; margin-top:5px;">
                        ${ev.prov}，中断${ev.duration}小时，${ev.reason}导致，${ev.details}
                    </div>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', html);
        });
    }
    
    document.getElementById('no-const-dur-info').innerText = `* 不含道路施工中断总时长：${noConstDur}小时`;
}

function renderBareFiberTable(services) {
    const tbody = document.getElementById('bare-fiber-tbody');
    tbody.innerHTML = '';
    
    const interruptedServices = [];
    const noInterruptedServices = [];
    
    services.forEach(s => {
        if (s.status === 'no_interruption') {
            noInterruptedServices.push(s);
        } else {
            interruptedServices.push(s);
        }
    });
    
    interruptedServices.forEach(s => {
        let statusHtml = '';
        let infoHtml = '';
        
        switch (s.status) {
            case 'jitter':
                statusHtml = '<span class="status-tag status-yellow">!</span>线路抖动';
                infoHtml = `
                    <td>-</td>
                    <td>抖动${s.jitter_cnt}次</td>
                    <td>-</td>
                    <td style="color:#cbd5e1;">（抖动${s.jitter_cnt}次，${s.segments}）</td>
                `;
                break;
            case 'interruption':
                statusHtml = '<span class="status-tag status-red">X</span>光缆中断';
                const jitterText = s.jitter_cnt > 0 ? ` / 抖动${s.jitter_cnt}次` : '';
                infoHtml = `
                    <td>光缆中断${s.break_cnt}次${jitterText}</td>
                    <td>造成业务阻断${s.block_cnt}次</td>
                    <td style="color:#ef4444; font-weight:bold;">阻断${s.duration}h</td>
                    <td style="color:#64748b; font-size:12px;">重点：${s.segments}</td>
                `;
                break;
        }
        
        const rowHTML = `
            <tr>
                <td class="col-service" width="20%">${s.name}</td>
                <td width="15%">${statusHtml}</td>
                ${infoHtml}
            </tr>
        `;
        tbody.insertAdjacentHTML('beforeend', rowHTML);
    });
    
    if (noInterruptedServices.length > 0) {
        const names = noInterruptedServices.map(s => s.name).join('、');
        const rowHTML = `
            <tr>
                <td colspan="6" style="color:#64748b; font-size: 13px; line-height: 1.6;">
                    <span class="status-tag status-green" style="margin-right: 10px;">✓ 没有中断</span>
                    <strong>正常业务：</strong> ${names}
                </td>
            </tr>
        `;
        tbody.insertAdjacentHTML('beforeend', rowHTML);
    }
}

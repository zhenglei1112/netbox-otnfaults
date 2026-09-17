/** Opt-in statistics timings. No interception of requests outside this page. */
(function (global) {
    'use strict';
    const enabled = new URLSearchParams(global.location.search).get('statistics_debug') === '1';
    const nativeFetch = global.fetch.bind(global);
    const records = [];
    let sequence = 0;
    let action = { id: 0, name: 'initial_load', started: performance.now() };
    let panel;
    let observer;
    const parameterNames = [
        'filter_type', 'year', 'half', 'quarter', 'month', 'week', 'date', 'calendar_year', 'calendar_month',
        'scope', 'detail_scope', 'service_type', 'service_key', 'include_all_bare_fiber', 'fault_id',
        'province', 'provinces', 'line_supervisor', 'category', 'reason', 'resource_type', 'source_group',
        'bare_fiber_interruption', 'impact_level', 'fault_group', 'is_long', 'is_repeat', 'is_valid_duration',
        'duration_min', 'duration_max', 'duration_bucket', 'duration_histogram_bucket', 'cause_group', 'occurrence_period', 'ordering',
    ];
    function add(record) {
        records.push(record);
        if (records.length > 1000) records.shift();
        if (panel && record.type !== 'render') panel.textContent = `已采集 ${records.length} 条；请求 ${records.filter(row => row.type === 'request').length} 次。详情和瓶颈见导出 JSON。`;
    }
    function begin(name) {
        if (!enabled) return;
        action = { id: ++sequence, name, started: performance.now() };
        add({ type: 'action', action_id: action.id, name, started: action.started });
    }
    function wrap(name, fn) {
        if (!enabled) return fn;
        return function (...args) {
            const started = performance.now();
            const owner = action;
            try { return fn.apply(this, args); }
            finally {
                add({ type: 'render', name, action_id: owner.id, ms: performance.now() - started, started });
            }
        };
    }
    async function measuredFetch(input, options) {
        if (!enabled) return nativeFetch(input, options);
        const owner = action;
        const started = performance.now();
        const url = new URL(input, global.location.href);
        url.searchParams.set('statistics_debug', '1');
        if (new URLSearchParams(global.location.search).get('statistics_cache_bypass') === '1') {
            url.searchParams.set('statistics_cache_bypass', '1');
        }
        const row = {
            type: 'request', action_id: owner.id, action: owner.name, started,
            endpoint: url.pathname,
            // Whitelist diagnostic dimensions, never export arbitrary query parameters.
            parameters: Object.fromEntries(parameterNames.map(key => [key, url.searchParams.getAll(key)]).filter(([, value]) => value.length)),
        };
        add(row);
        try {
            const response = await nativeFetch(url.href, options);
            row.headers_ms = performance.now() - started;
            row.status = response.status;
            if (response.status >= 400) {
                row.error = 'http_error';
                row.complete_ms = performance.now() - started;
            }
            const json = response.json.bind(response);
            response.json = async function () {
                const jsonStarted = performance.now();
                try {
                    const data = await json();
                    row.body_and_json_ms = performance.now() - jsonStarted;
                    row.complete_ms = performance.now() - started;
                    row.action_elapsed_ms = performance.now() - owner.started;
                    row.rows = Array.isArray(data.results) ? data.results.length : undefined;
                    row.server = data._statistics_debug || null;
                    row.backend_diagnostics = row.server ? 'enabled' : 'unavailable';
                    return data;
                } catch (error) {
                    row.error = 'body_or_json_error';
                    row.complete_ms = performance.now() - started;
                    throw error;
                }
            };
            return response;
        } catch (error) {
            row.error = 'network_error';
            row.complete_ms = performance.now() - started;
            throw error;
        }
    }
    function report() {
        const requests = records.filter(row => row.type === 'request');
        const findings = [];
        const repeated = new Map();
        for (const row of requests) {
            const key = JSON.stringify([row.action_id, row.endpoint, row.parameters]);
            repeated.set(key, (repeated.get(key) || 0) + 1);
            if (row.complete_ms >= 2000 || (row.server && row.server.total_ms >= 2000)) {
                findings.push({ request_id: row.server ? row.server.request_id : row.action_id, reason: `请求耗时过长(≥2.0s: ${(row.complete_ms || 0).toFixed(0)}ms)，需排查重计算或阻塞`, value: row.complete_ms });
            }
            if (row.server) {
                if (row.server.sql_count >= 100) findings.push({ request_id: row.server.request_id, reason: 'SQL 次数≥100，检查重复查询/N+1', value: row.server.sql_count });
                if (row.server.sql_ms > row.server.total_ms * .5) findings.push({ request_id: row.server.request_id, reason: '数据库执行占后端耗时超过50%', value: row.server.sql_ms });
                if (row.server.response_bytes > 1024 * 1024) findings.push({ request_id: row.server.request_id, reason: '原始响应超过1MiB', value: row.server.response_bytes });
                const externalDelay = row.complete_ms - row.server.total_ms;
                if (externalDelay >= 3000) {
                    findings.push({ request_id: row.server.request_id, reason: `视图外等待严重(≥3.0s: ${externalDelay.toFixed(0)}ms)，检查Worker并发排队或网络`, value: externalDelay });
                }
            }
        }
        for (const [key, count] of repeated) if (count > 1) findings.push({ reason: '同一交互重复请求', request: JSON.parse(key), count });
        return {
            version: 1, captured_at: new Date().toISOString(),
            navigation: performance.getEntriesByType('navigation').map(entry => ({ response_start_ms: entry.responseStart, dom_ready_ms: entry.domContentLoadedEventEnd, load_ms: entry.loadEventEnd })),
            records: records.slice(), findings,
            slow_render: records.filter(row => row.type === 'render' && row.ms >= 50).sort((a, b) => b.ms - a.ms),
            note: '阶段和渲染耗时含子调用，不能相加；headers_ms 含网络/排队/服务端，body_and_json_ms 含响应体传输与解析。长任务为页面级观察，跨交互时仅供关联。',
        };
    }
    function download() {
        const url = URL.createObjectURL(new Blob([JSON.stringify(report(), null, 2)], { type: 'application/json' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = `statistics-performance-${Date.now()}.json`;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    global.StatisticsDiagnostics = { enabled, fetch: measuredFetch, wrap, begin, report, download };
    if (!enabled) return;
    document.addEventListener('DOMContentLoaded', () => {
        const box = document.createElement('details');
        box.className = 'card p-2 m-2';
        box.innerHTML = '<summary>故障统计性能诊断（仅当前页面启用）</summary><p class="small mb-1">依次测试进入、日期、省份、Tab、下钻和排序，每种操作等待全部请求完成后重复 5 次，再导出。后端数据需管理员及插件诊断开关。</p><div class="small" data-diagnostic-status></div><div><button type="button" data-analyze class="btn btn-sm btn-outline-secondary mt-2 me-2">分析当前记录</button><button type="button" data-export class="btn btn-sm btn-outline-primary mt-2">导出诊断 JSON</button></div><pre class="small mt-2" style="max-height:320px;overflow:auto;white-space:pre-wrap" data-diagnostic-summary></pre>';
        const page = document.querySelector('.page-statistics');
        if (page) page.prepend(box);
        panel = box.querySelector('[data-diagnostic-status]');
        box.querySelector('[data-export]').addEventListener('click', download);
        box.querySelector('[data-analyze]').addEventListener('click', () => {
            const data = report();
            const requests = data.records.filter(row => row.type === 'request');
            const slow = requests.slice().sort((a, b) => (b.complete_ms || 0) - (a.complete_ms || 0)).slice(0, 10);
            const lines = slow.map(row => `${row.action} ${row.endpoint}: ${(row.complete_ms || 0).toFixed(1)}ms；后端 ${row.server ? row.server.total_ms + 'ms / SQL ' + row.server.sql_count + '次 / 缓存 ' + row.server.cache : '未启用或未完成'}`);
            box.querySelector('[data-diagnostic-summary]').textContent = ['请求耗时 Top 10（未完成请求耗时暂为0）', ...lines, '', '自动排查提示', ...data.findings.map(row => row.reason), '', '慢渲染', ...data.slow_render.slice(0, 10).map(row => `${row.name}: ${row.ms.toFixed(1)}ms`)].join('\n');
        });
        document.addEventListener('change', event => {
            if (event.target.closest('.page-statistics') && !event.target.closest('details')) begin(`change:${event.target.id || event.target.name || 'control'}`);
        }, true);
        document.addEventListener('click', event => {
            const target = event.target.closest('#statisticsTab button, .statistics-drill-metric, #btn-prev-period, #btn-next-period');
            if (target) begin(`click:${target.id || target.dataset.filterField || 'metric'}`);
        }, true);
        document.addEventListener('shown.bs.tab', event => {
            if (event.target.closest('#statisticsTab')) begin(`tab:${event.target.id}`);
        }, true);
        if (global.PerformanceObserver) {
            try {
                observer = new PerformanceObserver(list => list.getEntries().forEach(entry => add({ type: 'long_task', action_id: action.id, started: entry.startTime, ms: entry.duration })));
                observer.observe({ type: 'longtask', buffered: true });
            } catch (_) { /* Unsupported in some browsers. */ }
        }
    });
})(window);

// Run with: node tests/test_statistics_line_supervisor_frontend.js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js'), 'utf8');

function functionSource(name) {
    const match = source.match(new RegExp(`    (?:async )?function ${name}\\(.*?\\n    }`, 's'));
    assert.ok(match, name);
    return match[0];
}

function context(names, additions = {}) {
    const elements = new Map();
    const element = id => {
        if (!elements.has(id)) elements.set(id, {
            innerHTML: '', textContent: '', checked: false, disabled: false,
            style: {}, classList: { add() {}, remove() {}, toggle() {} },
            setAttribute() {}, scrollIntoView() {}, querySelectorAll: () => [],
        });
        return elements.get(id);
    };
    const ctx = vm.createContext({
        console, encodeURIComponent, Set, Date, elements,
        document: { getElementById: element, querySelector: element },
        activeLineSupervisorFilterField: null, activeLineSupervisorFilterValue: null,
        activeLineSupervisorFilterExtraField: null, activeLineSupervisorFilterExtraValue: null,
        activeLineSupervisorFilterLabel: null, activeLineSupervisorDetailScope: null,
        currentLineSupervisorDetails: [], supervisorDetailsRequest: 0,
        supervisorOrdering: '-fault_occurrence_time',
        currentPrevLineSupervisorData: null, currentYoyLineSupervisorData: null,
        window: { STATISTICS_DETAILS_API: '/statistics/details/' },
        buildTimeParams: () => 'year=2026', renderLineSupervisorDetailsTable() {},
        ...additions,
    });
    vm.runInContext(names.map(functionSource).join('\n'), ctx);
    return ctx;
}

test('chart and metric drilldowns keep manager scope separate from physical filters', async () => {
    const urls = [];
    const ctx = context(['loadSupervisorDetails', 'handleLineSupervisorChartClick', 'handleLineSupervisorMetricFilterClick', 'normalizeFilterValue'], {
        fetch: async url => { urls.push(url); return { ok: true, json: async () => ({ results: [{ province: '广东省' }] }) }; },
    });
    ctx.handleLineSupervisorChartClick({ name: '姜川' }, 'province');
    await new Promise(resolve => setImmediate(resolve));
    let url = new URL(urls[0], 'http://localhost');
    assert.equal(url.searchParams.get('scope'), 'line_supervisor');
    assert.equal(url.searchParams.get('line_supervisor'), '姜川');
    assert.equal(url.searchParams.get('detail_scope'), 'cable_break');
    assert.equal(url.searchParams.has('province'), false);
    assert.equal(ctx.currentLineSupervisorDetails[0].province, '广东省');
    ctx.handleLineSupervisorMetricFilterClick({ dataset: { filterField: 'bare_fiber_interruption', filterValue: 'true' }, closest: () => null });
    await new Promise(resolve => setImmediate(resolve));
    url = new URL(urls[1], 'http://localhost');
    assert.equal(url.searchParams.get('bare_fiber_interruption'), 'true');
    assert.equal(url.searchParams.has('detail_scope'), false);
    assert.equal(url.searchParams.has('line_supervisor'), false);
});

test('late detail responses cannot overwrite a newer selection', async () => {
    const pending = [];
    const ctx = context(['loadSupervisorDetails'], { fetch: () => new Promise(resolve => pending.push(resolve)) });
    const older = ctx.loadSupervisorDetails();
    const newer = ctx.loadSupervisorDetails();
    pending[1]({ ok: true, json: async () => ({ results: [{ id: 2 }] }) });
    await newer;
    pending[0]({ ok: true, json: async () => ({ results: [{ id: 1 }] }) });
    await older;
    assert.equal(ctx.currentLineSupervisorDetails[0].id, 2);
});

test('time and repeat sorting use independent supervisor inputs and original provinces', () => {
    let rendered;
    const ctx = context(['renderLineSupervisorDetailsTable', 'sortDetailRows', 'assignRepeatGroupColors'], {
        renderSupervisorDetailsTableHtml: rows => { rendered = rows; },
        updateSupervisorFilterBadgeAndSummary() {},
    });
    const row = (id, time, inPeriod) => ({ id, fault_occurrence_time: time, in_period: inPeriod, is_repeat: true, site_a: 'A', site_z: 'Z', province: '广东省' });
    ctx.currentLineSupervisorDetails = [row(1, '2026-01-05 12:00:00', true), row(2, '2025-12-30 12:00:00', false)];
    const sort = ctx.document.querySelector('input[name="lineSupervisorDetailSortMode"]:checked');
    sort.value = 'time';
    ctx.renderLineSupervisorDetailsTable();
    assert.equal(rendered.length, 1);
    sort.value = 'repeat';
    ctx.renderLineSupervisorDetailsTable();
    assert.equal(rendered.length, 2);
    assert.ok(rendered.every(row => row.province === '广东省'));
});

test('chart controls use independent metrics and disable normalized valid duration', () => {
    const calls = [];
    const ctx = context(['renderLineSupervisorBarCharts', 'syncLineSupervisorWeeklyScaleAvailability'], {
        getCheckedValue: name => ({ lineSupervisorCountMetric: 'count_per_1000km', lineSupervisorDurationMetric: 'duration_per_1000km', lineSupervisorWeeklyMetric: 'valid_duration' })[name],
        chartLineSupervisorCount: 'count-chart', chartLineSupervisorDuration: 'duration-chart',
        renderBranchBarChart: (...args) => calls.push(args),
    });
    ctx.renderLineSupervisorBarCharts({ province_bars: [] });
    assert.equal(calls[0][2], 'count_per_1000km');
    assert.equal(calls[1][2], 'duration_per_1000km');
    const normalized = ctx.document.getElementById('line-supervisor-weekly-scale-normalized');
    normalized.checked = true;
    ctx.syncLineSupervisorWeeklyScaleAvailability();
    assert.equal(normalized.disabled, true);
    assert.equal(ctx.document.getElementById('line-supervisor-weekly-scale-raw').checked, true);
});

test('clearing supervisor filters resets only its own state', () => {
    const ctx = context([], { loadSupervisorDetails() {}, activeBranchCompanyFilterValue: '浙江' });
    const button = ctx.document.getElementById('line-supervisor-btn-clear-filter');
    button.addEventListener = (type, handler) => { button.handler = handler; };
    vm.runInContext(source.match(/    const btnClearLineSupervisorFilter.*?\n    }/s)[0], ctx);
    ctx.activeLineSupervisorFilterValue = '姜川';
    ctx.activeLineSupervisorDetailScope = 'cable_break';
    button.handler();
    assert.equal(ctx.activeLineSupervisorFilterValue, null);
    assert.equal(ctx.activeLineSupervisorDetailScope, null);
    assert.equal(ctx.activeBranchCompanyFilterValue, '浙江');
});

test('all six charts render with shared helpers and independent supervisor instances', () => {
    const options = {};
    const mocks = {
        supervisorNames: ['冯鑫源', '姜川', '李立彬', '孙振伟', '李小涛'],
        getChartTheme: () => ({}), buildTooltipTheme: () => ({}), buildAxisTheme: () => ({}), buildLegendTheme: () => ({}),
        getCheckedValue: (name, fallback) => fallback,
        formatCardMetricValue: String, formatCardCountValue: String,
        renderTrendBesideMetric() {}, renderBareFiberInterruption() {}, buildFlexGroup: () => '',
    };
    for (const suffix of ['Count', 'Duration', 'Boxplot', 'ValidDuration', 'Weekly', 'Monthly']) {
        mocks[`chartLineSupervisor${suffix}`] = { setOption: value => { options[suffix] = value; } };
    }
    const ctx = context([
        'renderLineSupervisorSection', 'renderLineSupervisorOverview', 'renderLineSupervisorBarCharts',
        'renderLineSupervisorBoxplot', 'renderLineSupervisorValidDurationChart', 'renderLineSupervisorWeeklyChart',
        'renderLineSupervisorMonthlyChart', 'syncLineSupervisorWeeklyScaleAvailability',
        'renderBranchBarChart', 'getSortedBranchBars', 'getBranchCompanyProvinceColor',
        'buildBranchCompanyGrid', 'buildBranchCompanyYAxis', 'formatBranchCompanyWeekMonthTick',
    ], mocks);
    const names = mocks.supervisorNames;
    ctx.renderLineSupervisorSection({
        groups: [{ name: '冯鑫源', provinces: ['甘肃', '宁夏', '青海', '新疆'] }], path_lengths: { '冯鑫源': 3972 },
        province_bars: names.map((name, index) => ({ name, count: index, duration: index })),
        duration_boxplot: names.map(name => ({ name, value: [0, 0, 0, 0, 0] })),
        valid_duration_bars: names.map(name => ({ name, valid_duration: 0 })),
        weekly_trends: { labels: ['1/1'], series: names.map(name => ({ name, counts: [0] })) },
        monthly_trends: { labels: ['1月'], series: names.map(name => ({ name, counts: [0] })) },
    });
    assert.equal(Object.keys(options).length, 6);
    assert.deepEqual(Array.from(options.Count.xAxis.data), names);
    assert.equal(options.Weekly.series.length, 5);
    assert.equal(options.Monthly.series.length, 5);
});

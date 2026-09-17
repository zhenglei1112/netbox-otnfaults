const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../netbox_otnfaults/static/netbox_otnfaults/js/statistics_diagnostics.js'), 'utf8');
function setup(search = '?statistics_debug=1') {
    let time = 0;
    const calls = [];
    const window = {
        location: { search, href: `https://example.test/statistics/${search}` },
        fetch: async url => { calls.push(url); return { status: 200, json: async () => ({ results: [1], _statistics_debug: { request_id: 'test', sql_count: 120, sql_ms: 80, total_ms: 100, response_bytes: 20 } }) }; },
    };
    vm.runInNewContext(source, { window, URL, URLSearchParams, performance: { now: () => ++time, getEntriesByType: () => [] }, document: { addEventListener() {} }, console });
    return { api: window.StatisticsDiagnostics, calls };
}
test('disabled profiling preserves fetch URL and function identity', async () => {
    const { api, calls } = setup('');
    const fn = () => 7;
    assert.equal(api.wrap('render', fn), fn);
    await api.fetch('/api/test');
    assert.equal(calls[0], '/api/test');
    assert.equal(api.report().records.length, 0);
});
test('debug records requests, parsing and server findings without response bodies', async () => {
    const { api, calls } = setup();
    api.begin('date');
    const response = await api.fetch('/api/test?scope=line_supervisor&token=secret');
    const data = await response.json();
    assert.equal(data.results.length, 1);
    assert.ok(calls[0].includes('statistics_debug=1'));
    const report = api.report();
    assert.equal(report.records[1].server.sql_count, 120);
    assert.equal(report.findings.length, 2);
    assert.equal(JSON.stringify(report).includes('secret'), false);
    assert.equal(report.records[1].rows, 1);
});
test('render wrapper preserves this, return and exception; record storage bounded', () => {
    const { api } = setup();
    const obj = { value: 5, render: api.wrap('render', function () { return this.value; }) };
    assert.equal(obj.render(), 5);
    assert.throws(api.wrap('error', () => { throw Error('expected'); }));
    for (let i = 0; i < 1100; i++) obj.render();
    assert.equal(api.report().records.length, 1000);
});
test('bypass is explicit and repeated requests are flagged per action', async () => {
    const { api, calls } = setup('?statistics_debug=1&statistics_cache_bypass=1');
    await api.fetch('/api/test');
    await api.fetch('/api/test');
    assert.ok(calls[0].includes('statistics_cache_bypass=1'));
    assert.equal(api.report().findings.some(row => row.reason === '同一交互重复请求'), true);
});

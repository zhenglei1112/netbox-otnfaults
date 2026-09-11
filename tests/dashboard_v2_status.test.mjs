import test from 'node:test';
import assert from 'node:assert/strict';
import { updateDashboardStatus } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/status.js';

test('shared status follows V1 online/offline and keeps map failures and simulation visible', () => {
  const previous = globalThis.document;
  const text = { textContent: '' };
  let error = false;
  const dot = { classList: { toggle: (_, value) => { error = value; } } };
  globalThis.document = { getElementById: (id) => id.endsWith('-text') ? text : dot };
  try {
    updateDashboardStatus({ mapState: 'ready' });
    assert.equal(text.textContent, '数据加载中...');
    updateDashboardStatus({ dataState: 'online' });
    assert.equal(text.textContent, '数据在线');
    updateDashboardStatus({ dataState: 'error', dataError: 'HTTP 500' });
    assert.equal(text.textContent, '数据断联'); assert.equal(error, true);
    assert.match(text.title, /HTTP 500/);
    updateDashboardStatus({ mapState: 'ready' });
    assert.equal(text.textContent, '数据断联');
    updateDashboardStatus({ dataState: 'online', dataError: '' });
    assert.equal(error, false);
    updateDashboardStatus({ mapState: 'error', mapMessage: '瓦片加载失败' });
    updateDashboardStatus({ dataState: 'online', simulated: true });
    assert.equal(text.textContent, '瓦片加载失败 · 数据在线 · 模拟数据');
    assert.equal(error, true);
  } finally { globalThis.document = previous; }
});

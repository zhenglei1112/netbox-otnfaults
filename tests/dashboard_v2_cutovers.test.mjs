import test from 'node:test';
import assert from 'node:assert/strict';
import { presentationCutoverData, cutoverMapItems } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/cutovers.js';

test('presentation uses pending tasks only, chronological order, numeric ID tie-break and matching totals', () => {
  const task = (id, planned_time, day = 'today', status = 'pending_implementation') => ({ id, planned_time, day, status });
  const data = { cutovers: [task(10, '2026-09-11T02:00:00+08:00', 'tomorrow'),
    task(4, '2026-09-10T01:00:00+08:00', 'today', 'completed'),
    task(3, '2026-09-10T02:00:00+08:00'), task(2, '2026-09-10T02:00:00+08:00')],
    cutover_summary: { today: 3, tomorrow: 1 } };
  const before = JSON.stringify(data);
  const result = presentationCutoverData(data);
  assert.deepEqual(result.cutovers.map((item) => item.id), [2, 3, 10]);
  assert.deepEqual(result.cutover_summary, { today: 2, tomorrow: 1 });
  assert.deepEqual(cutoverMapItems(result.cutovers).map((item) => item.id), ['cutover-2', 'cutover-3', 'cutover-10']);
  assert.equal(JSON.stringify(data), before, 'desktop source data is untouched');
});

test('missing data and no pending tasks are safe', () => {
  assert.equal(presentationCutoverData(null), null);
  assert.deepEqual(presentationCutoverData({}).cutovers, []);
  assert.deepEqual(presentationCutoverData({ cutovers: [{ status: 'cancelled' }] }).cutover_summary, { today: 0, tomorrow: 0 });
});

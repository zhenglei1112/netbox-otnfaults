import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createDashboardV2MockFaultData,
} from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/mock_fault_data.js';


test('mock data builds five complete processing faults while preserving map sites', () => {
  const now = new Date('2026-09-02T06:00:00.000Z');
  const sites = [{ id: 1, name: '真实站点' }];
  const data = createDashboardV2MockFaultData({
    summary: { total_faults: 72, today_faults: 2 },
    sites,
  }, now);

  assert.equal(data.simulated, true);
  assert.equal(data.timestamp, now.toISOString());
  assert.equal(data.processing_faults.length, 5);
  assert.equal(data.summary.total_faults, 72);
  assert.equal(data.summary.processing_faults, 5);
  assert.equal(data.summary.today_faults, 5);
  assert.equal(data.summary.active_business_interruptions, 4);
  assert.equal(data.sites, sites);
  assert.equal(data.cutovers.length, 4);
  assert.deepEqual(data.cutover_summary, { today: 2, tomorrow: 2, total: 4 });
  assert.deepEqual(data.cutovers.map((task) => task.status_color), ['blue', 'orange', 'green', 'red']);
  for (const task of data.cutovers) {
    assert.equal(task.url, '');
    assert.ok(Number.isFinite(task.lng) && Number.isFinite(task.lat));
    const expected = new Date(now);
    expected.setDate(expected.getDate() + Number(task.day === 'tomorrow'));
    assert.equal(new Date(task.planned_time).toDateString(), expected.toDateString());
  }
  assert.deepEqual(
    new Set(data.processing_faults.map((fault) => fault.severity)),
    new Set(['critical', 'major', 'minor']),
  );
  for (const fault of data.processing_faults) {
    for (const field of [
      'fault_number',
      'category_display',
      'urgency_display',
      'lng',
      'lat',
      'province',
      'site_a',
      'occurrence_time',
      'occurrence_time_display',
      'duration',
      'handling_unit',
      'handler',
      'reason',
      'details',
    ]) {
      assert.ok(fault[field]);
    }
    assert.equal(fault.url, '');
  }
});

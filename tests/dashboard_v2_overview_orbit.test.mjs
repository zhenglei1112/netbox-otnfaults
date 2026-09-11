import test from 'node:test';
import assert from 'node:assert/strict';
import { createOverviewOrbit, orbitLongitude } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/overview_orbit.js';

test('longitude completes a smooth east/west cycle at the original center', () => {
  assert.equal(orbitLongitude(103, 8, 0), 103);
  assert.equal(orbitLongitude(103, 8, .25), 111);
  assert.equal(orbitLongitude(103, 8, .75), 95);
  assert.equal(orbitLongitude(103, 8, 1), 103);
});

test('overview locks layout, preserves camera axes, stops stale frames and honors reduced motion', () => {
  let callback;
  let reduced = false;
  const cameras = [];
  const map = { getCenter: () => ({ lng: 103, lat: 34 }), getZoom: () => 4,
    easeTo: (camera) => cameras.push(camera), __dashboardOverviewMargin: 100,
    on: (_, fn) => { callback = fn; }, off: () => { callback = null; }, stop() {} };
  const orbit = createOverviewOrbit({ map, reduced: () => reduced });
  orbit.start(); assert.equal(map.__dashboardOverviewLayoutLocked, true);
  assert.ok(cameras.at(-1).center[0] > 103 && cameras.at(-1).center[0] < 111);
  assert.equal(cameras.at(-1).center[1], 34);
  assert.equal(cameras.at(-1).zoom, 4);
  assert.equal(cameras.at(-1).bearing, 0); assert.equal(cameras.at(-1).pitch, 0);
  assert.equal(cameras.at(-1).duration, 11250);
  callback(); assert.equal(cameras.at(-1).duration, 22500);
  callback(); assert.equal(cameras.at(-1).center[0], 103);
  const stale = callback; const count = cameras.length;
  orbit.stop(); stale(22000);
  assert.equal(cameras.length, count); assert.equal(map.__dashboardOverviewLayoutLocked, undefined);
  reduced = true; orbit.start();
  assert.equal(callback, null); assert.equal(map.__dashboardOverviewLayoutLocked, true);
  assert.equal(map.__dashboardOverviewOrbit.state, 'reduced-motion');
  reduced = false; map.__dashboardOverviewMargin = 0; orbit.start();
  assert.equal(map.__dashboardOverviewOrbit.state, 'insufficient-space');
  map.__dashboardOverviewMargin = 100; orbit.start();
  assert.equal(map.__dashboardOverviewOrbit.state, 'running');
  assert.equal(map.__dashboardOverviewOrbit.round, 4);
  orbit.stop();
});

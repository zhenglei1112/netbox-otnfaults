import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createDayNightLayer,
  dayNightStrengths,
  initializeDashboardV2DayNight,
  solarSubpoint,
  surfaceIllumination,
} from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/day_night_layer.js';


test('places the subsolar point near the equator and Greenwich at the March equinox', () => {
  const sun = solarSubpoint(new Date('2024-03-20T12:00:00.000Z'));
  assert.ok(Math.abs(sun.latitude) < 0.5, `latitude=${sun.latitude}`);
  assert.ok(Math.abs(sun.longitude) < 3, `longitude=${sun.longitude}`);
});


test('enables and disables rendering without rebuilding the custom layer', () => {
  const addedLayers = [];
  let repaints = 0;
  const map = {
    loaded: () => true,
    getLayer: () => null,
    addLayer: (layer) => addedLayers.push(layer),
    triggerRepaint: () => { repaints += 1; },
  };
  const controller = initializeDashboardV2DayNight(map);

  assert.equal(addedLayers.length, 1);
  assert.equal(controller.getEnabled(), true);
  assert.equal(controller.setEnabled(false), false);
  assert.equal(addedLayers[0].enabled, false);
  assert.equal(controller.setEnabled(true), true);
  assert.equal(addedLayers[0].enabled, true);
  assert.equal(repaints, 2);
});


test('brightens daylight and darkens night with a neutral twilight band', () => {
  assert.deepEqual(dayNightStrengths(1), { day: 1, night: 0 });
  assert.deepEqual(dayNightStrengths(-1), { day: 0, night: 1 });
  const twilight = dayNightStrengths(0);
  assert.equal(twilight.day, 0);
  assert.ok(twilight.night > 0 && twilight.night < 1);
});


test('computes full illumination at the subsolar point and darkness at its antipode', () => {
  const sun = { longitude: 35, latitude: 20 };
  assert.ok(Math.abs(surfaceIllumination(35, 20, sun) - 1) < 1e-12);
  assert.ok(Math.abs(surfaceIllumination(-145, -20, sun) + 1) < 1e-12);
});


test('creates a globe-compatible custom day-night layer', () => {
  const layer = createDayNightLayer();
  assert.equal(layer.id, 'dashboard-v2-day-night');
  assert.equal(layer.type, 'custom');
  assert.equal(layer.renderingMode, '2d');
  assert.equal(typeof layer.onAdd, 'function');
  assert.equal(typeof layer.render, 'function');
  assert.equal(typeof layer.onRemove, 'function');
  assert.equal(layer.enabled, true);
});

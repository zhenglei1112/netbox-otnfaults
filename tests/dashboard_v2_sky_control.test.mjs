import assert from 'node:assert/strict';
import test from 'node:test';

import { initializeDashboardV2SkyControl } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/sky_control.js';


test('cycles full, primary, and off sky modes', () => {
  const button = {
    dataset: {},
    attributes: {},
    listeners: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    addEventListener(name, callback) { this.listeners[name] = callback; },
  };
  const status = { textContent: '' };
  globalThis.document = {
    getElementById(id) {
      if (id === 'dashboard-v2-map-sky') return button;
      if (id === 'dashboard-v2-sky-status') return status;
      return null;
    },
  };
  const galaxyValues = [];
  const starfieldValues = [];
  const controller = initializeDashboardV2SkyControl(
    { setVisible: (value) => galaxyValues.push(value) },
    { setMode: (value) => starfieldValues.push(value) },
  );

  assert.equal(controller.getMode(), 'full');
  assert.equal(button.dataset.skyMode, 'full');
  assert.equal(status.textContent, '天空 开启');
  button.listeners.click();
  assert.equal(controller.getMode(), 'primary');
  assert.equal(button.dataset.skyMode, 'primary');
  assert.equal(status.textContent, '天空 主星');
  button.listeners.click();
  assert.equal(controller.getMode(), 'off');
  assert.equal(status.textContent, '天空 关闭');
  button.listeners.click();
  assert.equal(controller.getMode(), 'full');
  assert.deepEqual(galaxyValues, [true, false, false, true]);
  assert.deepEqual(starfieldValues, ['full', 'primary', 'off', 'full']);
});

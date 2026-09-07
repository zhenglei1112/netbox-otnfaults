import assert from 'node:assert/strict';
import test from 'node:test';

import { initializeDashboardV2DayNightControl } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/day_night_control.js';


test('toggles day-night rendering and updates button state', () => {
  const button = {
    attributes: {},
    listeners: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    addEventListener(name, callback) { this.listeners[name] = callback; },
  };
  const status = { textContent: '' };
  globalThis.document = {
    getElementById(id) {
      if (id === 'dashboard-v2-map-day-night') return button;
      if (id === 'dashboard-v2-day-night-status') return status;
      return null;
    },
  };
  const values = [];
  const controller = initializeDashboardV2DayNightControl({
    getEnabled: () => true,
    setEnabled: (value) => values.push(value),
  });

  assert.equal(controller.getEnabled(), true);
  assert.equal(button.attributes['aria-pressed'], 'true');
  assert.equal(status.textContent, '昼夜 开启');
  button.listeners.click();
  assert.equal(controller.getEnabled(), false);
  assert.equal(button.attributes['aria-pressed'], 'false');
  assert.equal(status.textContent, '昼夜 关闭');
  button.listeners.click();
  assert.equal(controller.getEnabled(), true);
  assert.deepEqual(values, [true, false, true]);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { initializeDisplaySettings } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/display_settings.js';

test('icon buttons cycle independently without replacing their icons', () => {
  const elements = {};
  for (const kind of ['fault', 'cutover']) {
    elements[`dashboard-v2-${kind}-display`] = {
      dataset: {}, textContent: 'svg-placeholder', handlers: {},
      setAttribute() {}, addEventListener(type, handler) { this.handlers[type] = handler; },
      removeEventListener(type) { delete this.handlers[type]; },
    };
    elements[`dashboard-v2-${kind}-display-status`] = {};
  }
  globalThis.document = { getElementById: (id) => elements[id] };
  const updates = [];
  const control = initializeDisplaySettings((value) => updates.push(value));
  const button = elements['dashboard-v2-fault-display'];
  button.handlers.click();
  assert.deepEqual(updates.at(-1), { fault: 'points', cutover: 'full' });
  assert.match(elements['dashboard-v2-fault-display-status'].textContent, /只显示故障点/);
  button.handlers.click();
  assert.equal(button.dataset.mode, 'hidden');
  button.handlers.click();
  assert.equal(button.dataset.mode, 'full');
  assert.equal(button.textContent, 'svg-placeholder');
  control.destroy();
  assert.equal(button.handlers.click, undefined);
});

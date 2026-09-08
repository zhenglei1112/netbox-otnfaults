import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';


const MODULE_PATH = new URL(
  '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/debug_panel.js',
  import.meta.url,
);
const MODULE_SOURCE = await readFile(MODULE_PATH, 'utf8');


async function loadDebugPanel(tag) {
  const encoded = Buffer.from(MODULE_SOURCE).toString('base64');
  return import(`data:text/javascript;base64,${encoded}#${tag}`);
}


function installDom() {
  const ids = [
    'dashboard-v2-debug-panel',
    'dashboard-v2-debug-toggle',
    'dashboard-v2-debug-content',
    'dashboard-v2-debug-longitude',
    'dashboard-v2-debug-latitude',
    'dashboard-v2-debug-zoom',
    'dashboard-v2-debug-pitch',
    'dashboard-v2-debug-bearing',
    'dashboard-v2-debug-apply',
    'dashboard-v2-debug-reset',
    'dashboard-v2-debug-message',
    'dashboard-v2-debug-fps-current',
    'dashboard-v2-debug-fps-average',
    'dashboard-v2-debug-fps-minimum',
    'dashboard-v2-debug-data-simulation',
  ];
  const elements = new Map(ids.map((id) => [id, {
    id,
    hidden: id === 'dashboard-v2-debug-panel',
    value: '',
    checked: false,
    textContent: '',
    listeners: {},
    addEventListener(name, callback) {
      this.listeners[name] = callback;
    },
    setAttribute(name, value) {
      this[name] = value;
    },
  }]));
  globalThis.document = {
    getElementById(id) {
      return elements.get(id) || null;
    },
  };
  return elements;
}


function fakeMap() {
  const state = {
    center: { lng: 103, lat: 34.3 },
    zoom: 3.8,
    pitch: 35,
    bearing: 0,
    jumps: [],
    handlers: {},
    enabled: [],
    disabledRotations: [],
  };
  const map = {
    getCenter: () => state.center,
    getZoom: () => state.zoom,
    getPitch: () => state.pitch,
    getBearing: () => state.bearing,
    on(name, callback) {
      state.handlers[name] = callback;
    },
    jumpTo(camera) {
      state.jumps.push(camera);
      state.center = { lng: camera.center[0], lat: camera.center[1] };
      state.zoom = camera.zoom;
      state.pitch = camera.pitch;
      state.bearing = camera.bearing;
      state.handlers.moveend?.();
    },
  };
  for (const name of ['dragPan', 'scrollZoom', 'doubleClickZoom', 'dragRotate', 'touchZoomRotate']) {
    map[name] = { enable: () => state.enabled.push(name) };
  }
  map.touchZoomRotate.disableRotation = () => state.disabledRotations.push('touch');
  map.keyboard = { disableRotation: () => state.disabledRotations.push('keyboard') };
  return { map, state };
}


test('debug query accepts the requested ture value and the standard true spelling', async () => {
  const { isDashboardV2DebugEnabled } = await loadDebugPanel('query-option');

  assert.equal(isDashboardV2DebugEnabled('?debug=ture'), true);
  assert.equal(isDashboardV2DebugEnabled('?debug=true'), true);
  assert.equal(isDashboardV2DebugEnabled('?debug=TRUE'), true);
  assert.equal(isDashboardV2DebugEnabled('?debug=false'), false);
  assert.equal(isDashboardV2DebugEnabled(''), false);
});


test('debug panel remains hidden when the V2 debug option is disabled', async () => {
  const elements = installDom();
  const { map, state } = fakeMap();
  const { initializeDashboardV2DebugPanel } = await loadDebugPanel('disabled');

  const controller = initializeDashboardV2DebugPanel(map, { debugEnabled: false });

  assert.equal(controller, null);
  assert.equal(elements.get('dashboard-v2-debug-panel').hidden, true);
  assert.deepEqual(state.enabled, []);
});


test('FPS monitor reports current, average and minimum rates and can be stopped', async () => {
  const { createDashboardV2FpsMonitor } = await loadDebugPanel('fps-monitor');
  const outputs = {
    current: { textContent: '' },
    average: { textContent: '' },
    minimum: { textContent: '' },
  };
  const pendingFrames = new Map();
  let nextFrameId = 1;
  const scheduler = {
    requestAnimationFrame(callback) {
      const id = nextFrameId;
      nextFrameId += 1;
      pendingFrames.set(id, callback);
      return id;
    },
    cancelAnimationFrame(id) {
      pendingFrames.delete(id);
    },
  };
  const runFrame = (timestamp) => {
    const entry = pendingFrames.entries().next().value;
    assert.ok(entry);
    const [id, callback] = entry;
    pendingFrames.delete(id);
    callback(timestamp);
  };

  const monitor = createDashboardV2FpsMonitor(outputs, scheduler);
  monitor.start();
  assert.equal(monitor.running, true);
  assert.deepEqual(outputs, {
    current: { textContent: '--' },
    average: { textContent: '--' },
    minimum: { textContent: '--' },
  });

  runFrame(0);
  for (let timestamp = 20; timestamp <= 500; timestamp += 20) runFrame(timestamp);
  assert.equal(outputs.current.textContent, '50');
  assert.equal(outputs.average.textContent, '50');
  assert.equal(outputs.minimum.textContent, '50');

  for (let timestamp = 600; timestamp <= 1000; timestamp += 100) runFrame(timestamp);
  assert.equal(outputs.current.textContent, '10');
  assert.equal(outputs.average.textContent, '30');
  assert.equal(outputs.minimum.textContent, '10');

  monitor.stop();
  assert.equal(monitor.running, false);
  assert.equal(pendingFrames.size, 0);
});


test('debug panel applies camera options while keeping pitch and fixed bearing locked', async () => {
  const elements = installDom();
  const { map, state } = fakeMap();
  const { initializeDashboardV2DebugPanel } = await loadDebugPanel('enabled');
  const initialConfig = {
    debugEnabled: true,
    mapCenter: [103, 34.3],
    mapZoom: 3.8,
    mapPitch: 35,
    mapBearing: -5,
    simulationChanges: [],
  };
  initialConfig.onDataSimulationChange = (enabled) => {
    initialConfig.simulationChanges.push(enabled);
  };

  initializeDashboardV2DebugPanel(map, initialConfig);

  assert.equal(elements.get('dashboard-v2-debug-panel').hidden, false);
  assert.equal(elements.get('dashboard-v2-debug-content').hidden, false);
  assert.equal(elements.get('dashboard-v2-debug-longitude').value, '103');
  assert.equal(elements.get('dashboard-v2-debug-latitude').value, '34.3');
  assert.deepEqual(
    state.enabled,
    ['dragPan', 'scrollZoom', 'doubleClickZoom', 'touchZoomRotate'],
  );
  assert.deepEqual(state.disabledRotations, ['touch', 'keyboard']);

  const simulationToggle = elements.get('dashboard-v2-debug-data-simulation');
  simulationToggle.checked = true;
  simulationToggle.listeners.change();
  assert.deepEqual(initialConfig.simulationChanges, [true]);
  assert.match(elements.get('dashboard-v2-debug-message').textContent, /数据模拟/);
  simulationToggle.checked = false;
  simulationToggle.listeners.change();
  assert.deepEqual(initialConfig.simulationChanges, [true, false]);
  assert.match(elements.get('dashboard-v2-debug-message').textContent, /已恢复实时数据/);

  elements.get('dashboard-v2-debug-toggle').listeners.click();
  assert.equal(elements.get('dashboard-v2-debug-content').hidden, true);
  assert.equal(elements.get('dashboard-v2-debug-toggle').textContent, '展开');
  assert.equal(elements.get('dashboard-v2-debug-toggle')['aria-expanded'], 'false');
  elements.get('dashboard-v2-debug-toggle').listeners.click();
  assert.equal(elements.get('dashboard-v2-debug-content').hidden, false);
  assert.equal(elements.get('dashboard-v2-debug-toggle').textContent, '收起');

  elements.get('dashboard-v2-debug-longitude').value = '105.25';
  elements.get('dashboard-v2-debug-latitude').value = '35.5';
  elements.get('dashboard-v2-debug-zoom').value = '5.25';
  elements.get('dashboard-v2-debug-pitch').value = '40';
  elements.get('dashboard-v2-debug-bearing').value = '-12';
  elements.get('dashboard-v2-debug-apply').listeners.click();

  assert.deepEqual(state.jumps.at(-1), {
    center: [105.25, 35.5],
    zoom: 5.25,
    pitch: 0,
    bearing: 0,
  });
  assert.match(elements.get('dashboard-v2-debug-message').textContent, /已应用/);

  const jumpCount = state.jumps.length;
  elements.get('dashboard-v2-debug-longitude').value = '200';
  elements.get('dashboard-v2-debug-apply').listeners.click();
  assert.equal(state.jumps.length, jumpCount);
  assert.match(elements.get('dashboard-v2-debug-message').textContent, /经度/);

  elements.get('dashboard-v2-debug-longitude').value = '105';
  elements.get('dashboard-v2-debug-zoom').value = '';
  elements.get('dashboard-v2-debug-apply').listeners.click();
  assert.equal(state.jumps.length, jumpCount);
  assert.match(elements.get('dashboard-v2-debug-message').textContent, /缩放等级/);

  elements.get('dashboard-v2-debug-reset').listeners.click();
  assert.deepEqual(state.jumps.at(-1), {
    center: [103, 34.3],
    zoom: 3.8,
    pitch: 0,
    bearing: 0,
  });

  state.center = { lng: 100.125, lat: 30.25 };
  state.zoom = 6.5;
  state.pitch = 45;
  state.bearing = 8;
  state.handlers.moveend();
  assert.equal(elements.get('dashboard-v2-debug-longitude').value, '100.125');
  assert.equal(elements.get('dashboard-v2-debug-zoom').value, '6.5');
  assert.equal(elements.get('dashboard-v2-debug-pitch').value, '0');
  assert.equal(elements.get('dashboard-v2-debug-bearing').value, '0');

});

import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { createMockWeather, weatherDetails, initializeWeatherLayers, unexpiredWeather } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/weather_layers.js';

test('indicator CSS scopes event dots and lets weather state colors override the base', () => {
  const css = readFileSync(new URL('../netbox_otnfaults/static/netbox_otnfaults/css/dashboard_v2.css', import.meta.url), 'utf8');
  assert.ok(!css.includes('button:not(#dashboard-v2-presentation-mode):not([data-mode="hidden"])::after'));
  assert.ok(css.includes('button:is([data-mode="full"], [data-mode="points"])::after'));
  assert.ok(css.includes('.dashboard-v2-map-tool-button:where([data-weather-state]:not([data-weather-state="off"]))::after'));
  assert.match(css, /\[data-weather-state="ready"\]::after\s*\{ background: #19d978;/);
  assert.match(css, /\[data-weather-state="error"\]::after\s*\{ background: #ff5964;/);
});

test('weather simulation covers four hazards and separate track geometries', () => {
  const data = createMockWeather(new Date('2026-09-14T00:00:00Z'));
  assert.equal(data.weather.features.length, 5);
  assert.equal(data.weather.features[4].properties.risks.length, 2);
  assert.deepEqual(new Set(data.weather.features.flatMap((f) => f.properties.risks.map((r) => r.kind))), new Set(['rain', 'wind', 'heat', 'cold']));
  assert.equal(data.typhoon.features.filter((f) => f.geometry.type === 'LineString').length, 2);
  assert.ok(!JSON.stringify(data).includes('radius'));
  assert.match(weatherDetails(data.weather.features[0].properties), /非官方预警/);
  assert.match(weatherDetails(data.typhoon.features[0].properties), /香港天文台/);
});

test('cached geometry is removed after expiry even if the server is unreachable', () => {
  const now = new Date('2026-09-14T00:00:00Z');
  const data = createMockWeather(now);
  assert.equal(unexpiredWeather(data, +now).weather, data.weather);
  assert.equal(unexpiredWeather(data, +now + 25 * 3600000).weather.features.length, 0);
  assert.equal(unexpiredWeather(data, +now + 25 * 3600000).typhoon.features.length, 0);
});

test('layers persist switches, reuse unchanged geometry, isolate simulation and clean up', async () => {
  const keys = ['document', 'maplibregl', 'localStorage', 'fetch', 'setInterval', 'clearInterval', 'matchMedia'];
  const previous = Object.fromEntries(keys.map((key) => [key, globalThis[key]]));
  const listeners = new Map(), sources = new Map(), layers = new Map(), images = new Map(), timers = new Set();
  let writes = 0, screen = false, removed = 0;
  const buttons = new Map();
  const makeElement = () => ({ textContent: '', style: {}, attributes: {}, classList: { toggle() {} }, setAttribute(key, value) { this.attributes[key] = value; }, addEventListener(type, fn) { this[type] = fn; }, removeEventListener(type) { delete this[type]; } });
  const ctx = new Proxy({}, { get: (_, key) => key === 'getImageData' ? () => ({ width: 48, height: 48, data: [] }) : () => {}, set: () => true });
  const storage = new Map([['dashboard-v2-weather', 'off']]);
  const data = createMockWeather();
  const messages = [];
  const canvas = makeElement();
  const map = {
    on(name, handler) { listeners.set(name, handler); }, off(name) { listeners.delete(name); },
    getSource: (id) => sources.get(id), getLayer: (id) => layers.get(id),
    addSource(id, options) { sources.set(id, { ...options, setData(value) { this.data = value; writes++; } }); }, removeSource(id) { sources.delete(id); },
    addLayer(layer) { layers.set(layer.id, layer); }, removeLayer(id) { layers.delete(id); },
    setLayoutProperty(id, key, value) { const layer = layers.get(id); layer.layout = { ...layer.layout, [key]: value }; },
    setPaintProperty(id, key, value) { const layer = layers.get(id); layer.paint = { ...layer.paint, [key]: value }; },
    addImage(id, image) { images.set(id, image); }, hasImage: (id) => images.has(id), removeImage(id) { images.delete(id); },
    isStyleLoaded: () => true, getCanvas: () => canvas, addControl() {}, removeControl() { removed++; },
    queryRenderedFeatures: () => [],
  };
  try {
    globalThis.document = { hidden: false, documentElement: { classList: { contains: () => screen } },
      getElementById(id) { if (!buttons.has(id)) buttons.set(id, makeElement()); return buttons.get(id); },
      createElement: (tag) => tag === 'canvas' ? { getContext: () => ctx } : makeElement() };
    globalThis.localStorage = { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value) };
    globalThis.matchMedia = () => ({ matches: true });
    globalThis.setInterval = (fn) => { timers.add(fn); return fn; }; globalThis.clearInterval = (fn) => timers.delete(fn);
    globalThis.maplibregl = { AttributionControl: class {}, Popup: class {
      remove() { return this; } setDOMContent(node) { return this; } setLngLat() { return this; } addTo() { return this; }
    } };
    globalThis.fetch = async () => ({ ok: true, json: async () => data });
    const control = initializeWeatherLayers(map, { url: '/weather', onStatus: (value) => messages.push(value) });
    assert.equal(sources.get('v2-weather').cluster, false);
    assert.notEqual(sources.get('v2-typhoon').cluster, true);
    assert.equal(layers.has('weather-clusters'), false);
    const state = (kind) => buttons.get(`dashboard-v2-${kind}-toggle`).attributes['data-weather-state'];
    assert.equal(state('weather'), 'off');
    assert.equal(state('typhoon'), 'loading');
    await new Promise((resolve) => setTimeout(resolve, 0));
    assert.equal(state('typhoon'), 'ready');
    assert.equal(layers.get('weather-icons').layout.visibility, 'none');
    buttons.get('dashboard-v2-weather-toggle').click();
    assert.equal(storage.get('dashboard-v2-weather'), 'on');
    assert.equal(state('weather'), 'ready');
    const oldWrites = writes;
    for (const fn of [...timers]) await fn();
    assert.equal(writes, oldWrites);
    data.sources.weather.state = 'stale';
    for (const fn of [...timers]) await fn();
    assert.equal(state('weather'), 'error');
    assert.equal(state('typhoon'), 'ready');
    globalThis.fetch = async () => { throw new Error('offline'); };
    for (const fn of [...timers]) await fn();
    assert.equal(state('typhoon'), 'error');
    control.setSimulation(true);
    assert.equal(state('weather'), 'ready');
    assert.equal(state('typhoon'), 'ready');
    assert.notEqual(sources.get('v2-weather').data, data.weather);
    control.setSimulation(false);
    assert.equal(state('typhoon'), 'error');
    data.sources.weather.state = 'ready';
    globalThis.fetch = async () => ({ ok: true, json: async () => data });
    for (const fn of [...timers]) await fn();
    assert.equal(state('weather'), 'ready');
    assert.equal(state('typhoon'), 'ready');
    buttons.get('dashboard-v2-typhoon-toggle').click();
    assert.equal(state('typhoon'), 'off');
    assert.equal(sources.get('v2-weather').data, data.weather);
    screen = true; map.__dashboardPresentationScale = 2; listeners.get('resize')();
    assert.equal(layers.get('weather-icons').layout['icon-size'], 2);
    control.destroy();
    assert.equal(timers.size, 0); assert.equal(sources.size, 0); assert.equal(layers.size, 0);
    assert.equal(images.size, 0); assert.equal(listeners.size, 0); assert.equal(removed, 1);
  } finally { keys.forEach((key) => { globalThis[key] = previous[key]; }); }
});

import assert from 'node:assert/strict';
import test from 'node:test';
import { createPresentationTour, validPosition } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/presentation_tour.js';
import { scaleMapValue, initializePresentationMode, presentationFocusZoom } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/presentation_mode.js';

test('event focus zoom enlarges local view and preserves extent across display sizes', () => {
  assert.equal(presentationFocusZoom(1), 6.5);
  assert.equal(presentationFocusZoom(2), 7.5);
  assert.equal(presentationFocusZoom(.5), 5.5);
  for (const scale of [.5, 1, 1.5, 2]) {
    assert.ok(Math.abs(scale / 2 ** presentationFocusZoom(scale) - 1 / 2 ** 6.5) < 1e-10);
  }
  for (const scale of [NaN, Infinity, 0, -1]) assert.equal(presentationFocusZoom(scale), 6.5);
});

function harness() {
  let timer = null;
  const events = [];
  const tour = createPresentationTour({
    overview: (items, duration) => events.push(['overview', items.length, duration]),
    focus: (item, duration) => events.push(['focus', item.id, duration]),
    clearFocus() {}, cancelMotion() {},
    setTimer: (fn, ms) => { timer = { fn, ms }; return timer; },
    clearTimer: () => { timer = null; },
  });
  return { tour, events, timer: () => timer, async tick() { const next = timer; timer = null; next.fn(); await Promise.resolve(); } };
}

test('overview 45 seconds, each event 12 seconds, then repeat; refresh does not reset', async () => {
  const h = harness();
  h.tour.setItems([{ id: 'f1' }, { id: 'cutover-1' }]);
  h.tour.start(); await Promise.resolve();
  assert.equal(h.timer().ms, 45000);
  const timer = h.timer();
  h.tour.setItems([{ id: 'f1', duration: 'new' }, { id: 'cutover-1' }]);
  assert.equal(h.timer(), timer);
  await h.tick();
  assert.deepEqual(h.events.at(-1), ['focus', 'f1', 2000]);
  assert.equal(h.timer().ms, 12000);
  await h.tick();
  assert.equal(h.tour.currentId(), 'cutover-1');
  await h.tick();
  assert.equal(h.events.at(-1)[0], 'overview');
  h.tour.stop(); assert.equal(h.timer(), null);
});

test('removed current event advances, added event is visited, empty queue stays idle', async () => {
  const h = harness();
  h.tour.setItems([]); h.tour.start(); await Promise.resolve();
  assert.equal(h.timer(), null);
  h.tour.setItems([{ id: 'a' }, { id: 'b' }]); await Promise.resolve();
  await h.tick();
  h.tour.setItems([{ id: 'b' }, { id: 'c' }]); await Promise.resolve();
  assert.equal(h.tour.currentId(), 'b');
  await h.tick(); assert.equal(h.tour.currentId(), 'c');
});

test('stopping during flight cancels the pending dwell; reduced motion uses zero duration', async () => {
  let finish;
  let scheduled = 0;
  const tour = createPresentationTour({ overview: (_, duration) => {
    assert.equal(duration, 0); return new Promise((resolve) => { finish = resolve; });
  }, focus() {}, clearFocus() {}, reducedMotion: () => true,
  setTimer: () => scheduled++, clearTimer() {} });
  tour.setItems([{ id: 'a' }]); tour.start(); tour.stop(); finish(); await Promise.resolve();
  assert.equal(scheduled, 0);
});

test('coordinates validate and zoom expressions retain legal top-level interpolation', () => {
  assert.equal(validPosition({ lng: null, lat: 2 }), false);
  assert.equal(validPosition({ lng: 181, lat: 2 }), false);
  assert.equal(validPosition({ lng: 0, lat: 0 }), true);
  assert.deepEqual(scaleMapValue(['interpolate', ['linear'], ['zoom'], 0, 2, 7, 5], 2),
    ['interpolate', ['linear'], ['zoom'], 0, 4, 7, 10]);
});

test('4K mode persists, disables tools, and restores desktop camera and interaction', () => {
  const originals = Object.fromEntries(['document', 'window', 'localStorage', 'matchMedia', 'setInterval', 'clearInterval', 'cancelAnimationFrame'].map((key) => [key, globalThis[key]]));
  const surface = () => ({ listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; }, removeEventListener(type) { delete this.listeners[type]; } });
  const button = { ...surface(), dataset: {}, setAttribute() {}, contains: () => false };
  const other = { disabled: false };
  const classes = new Set(); const styles = {};
  const storage = new Map(); const intervals = new Set();
  const changes = []; const jumps = [];
  let expanded = false;
  const handler = () => ({ enabled: true, isEnabled() { return this.enabled; }, disable() { this.enabled = false; }, enable() { this.enabled = true; } });
  const map = { getCenter: () => ({ lng: 120, lat: 30 }), getZoom: () => 4.2, getBearing: () => 0, getPitch: () => 0,
    getStyle: () => ({ layers: [] }), fire() {}, resize() {}, stop() {}, on() {}, off() {}, jumpTo: (camera) => jumps.push(camera),
    dragPan: handler(), scrollZoom: handler() };
  try {
    globalThis.document = { ...surface(), hidden: false,
      documentElement: { classList: { add: (key) => classes.add(key), remove: (key) => classes.delete(key) }, style: { setProperty: (key, value) => { styles[key] = value; } } },
      getElementById: (id) => id === 'dashboard-v2-presentation-mode' ? button : null,
      querySelectorAll: (selector) => selector === 'button, input, select' ? [button, other] : [],
    };
    globalThis.window = { ...surface(), innerWidth: 3840, innerHeight: 2160 };
    globalThis.localStorage = { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value) };
    globalThis.matchMedia = () => ({ matches: false });
    globalThis.setInterval = (fn) => { intervals.add(fn); return fn; };
    globalThis.clearInterval = (fn) => intervals.delete(fn);
    globalThis.cancelAnimationFrame = () => {};
    const controller = initializePresentationMode({ map, config: {}, drawer: { isExpanded: () => expanded, setExpanded: (value) => { expanded = value; } }, onModeChange: (active) => changes.push(active) });
    assert.equal(controller.isActive(), false);
    button.listeners.click();
    assert.equal(styles['--presentation-scale'], 2);
    assert.equal(intervals.size, 0, 'presentation never starts a separate list scrolling timer');
    assert.equal(expanded, true); assert.equal(other.disabled, true); assert.equal(map.dragPan.enabled, false);
    assert.equal(storage.get('dashboard-v2-display-mode'), 'screen');
    button.listeners.click();
    assert.equal(expanded, false); assert.equal(other.disabled, false); assert.equal(map.dragPan.enabled, true);
    assert.equal(jumps.at(-1).zoom, 4.2); assert.equal(intervals.size, 0);
    assert.deepEqual(changes, [true, false]);
    controller.destroy(); assert.equal(button.listeners.click, undefined);
  } finally {
    for (const [key, value] of Object.entries(originals)) { if (value === undefined) delete globalThis[key]; else globalThis[key] = value; }
  }
});

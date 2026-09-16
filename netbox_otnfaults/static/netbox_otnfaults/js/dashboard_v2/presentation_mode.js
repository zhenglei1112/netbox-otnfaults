import { createPresentationTour, validPosition } from './presentation_tour.js?v=20260911-orbit-v3';
import { createOverviewOrbit } from './overview_orbit.js?v=20260911-orbit-v3';
import { createPresentationPages } from './presentation_pages.js?v=20260910-sections-v2';

const LIST_IDS = ['dashboard-v2-info-fault-list', 'dashboard-v2-info-cutover-list', 'dashboard-v2-info-heavy-list'];
const HANDLERS = ['dragPan', 'scrollZoom', 'boxZoom', 'doubleClickZoom', 'touchZoomRotate', 'keyboard'];

// Preserve the local geographic extent as presentation pixels scale (not devicePixelRatio).
export function presentationFocusZoom(scale = 1) {
  const safeScale = Number.isFinite(scale) && scale > 0 ? scale : 1;
  return 6.5 + Math.log2(Math.max(.5, safeScale));
}

export function scaleMapValue(value, factor) {
  if (typeof value === 'number') return value * factor;
  if (Array.isArray(value) && value[0] === 'interpolate') return value.map((part, i) => i >= 4 && i % 2 === 0 ? scaleMapValue(part, factor) : part);
  if (Array.isArray(value) && value[0] === 'step') return value.map((part, i) => i >= 2 && i % 2 === 0 ? scaleMapValue(part, factor) : part);
  return ['*', value, factor];
}

export function initializePresentationMode({ map, config, drawer, onModeChange }) {
  const button = document.getElementById('dashboard-v2-presentation-mode');
  if (!button || !map) return { setItems() {}, isActive: () => false, destroy() {} };
  const root = document.documentElement;
  const content = document.getElementById('dashboard-v2-info-drawer-content');
  let active = false;
  let saved = null;
  let items = null;
  let focusedId = null;
  let resizeFrame = null;
  let motionCleanup = null;
  let scale = 1;
  let overviewActive = false;
  const layerDefaults = new Map();
  const applyMapScale = () => {
    for (const layer of map.getStyle()?.layers || []) {
      if (!layerDefaults.has(layer.id)) layerDefaults.set(layer.id, { layout: { ...layer.layout }, paint: { ...layer.paint } });
      const original = layerDefaults.get(layer.id);
      if (layer.type === 'symbol' && original.layout['text-field']) {
        map.setLayoutProperty(layer.id, 'text-size', active ? 16 * scale : original.layout['text-size'] ?? 16);
      }
      for (const property of ['circle-radius', 'circle-stroke-width', 'line-width']) {
        if (original.paint[property] !== undefined) map.setPaintProperty(layer.id, property,
          active ? scaleMapValue(original.paint[property], 1.6 * scale) : original.paint[property]);
      }
    }
  };
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const orbit = createOverviewOrbit({ map, reduced });
  const listen = [];
  const on = (target, type, handler, options) => {
    target.addEventListener(type, handler, options);
    listen.push(() => target.removeEventListener(type, handler, options));
  };
  const lists = () => LIST_IDS.map((id) => document.getElementById(id)).filter(Boolean);
  const pages = createPresentationPages({ lists, content, scale: () => scale, reduced });
  const focusCard = (id, scroll = true) => {
    focusedId = id;
    document.querySelectorAll('[data-event-id]').forEach((card) => {
      const selected = card.dataset.eventId === id;
      card.classList.toggle('is-presentation-active', selected);
    });
    map.__dashboardPresentationFocus = id;
    if (active) pages.update(id);
    map.fire('resize');
  };
  const padding = () => ({ top: 90 * scale, bottom: 100 * scale, left: 510 * scale, right: 170 * scale });
  const stopMotion = () => { orbit.stop(); motionCleanup?.(); map.stop(); };
  const move = (camera, duration, fit = false) => {
    stopMotion();
    return new Promise((resolve) => {
      let timer;
      let revealTimer;
      let settled = false;
      const done = () => {
        if (settled) return;
        settled = true;
        clearTimeout(timer); clearTimeout(revealTimer);
        map.off('moveend', arrived);
        root.classList.remove('is-presentation-flying');
        motionCleanup = null; resolve();
      };
      const arrived = () => {
        map.off('moveend', arrived);
        clearTimeout(timer);
        if (fit) {
          map.__dashboardResetOverviewLayout = true;
          map.fire('resize');
        }
        // Let projected labels settle before fading in; opacity keeps layout measurable.
        revealTimer = setTimeout(() => {
          root.classList.remove('is-presentation-flying');
          revealTimer = setTimeout(done, duration ? 220 : 0);
        }, duration ? 40 : 0);
      };
      motionCleanup = done;
      const fly = () => {
        map.on('moveend', arrived);
        timer = setTimeout(arrived, duration + 500);
        try {
          if (fit) map.fitBounds(camera, { padding: padding(), maxZoom: 4, duration, bearing: 0, pitch: 0 });
          else map.flyTo({ ...camera, padding: padding(), duration, bearing: 0, pitch: 0 });
          if (!duration) done();
        } catch (_error) { done(); }
      };
      if (duration) {
        root.classList.add('is-presentation-flying');
        timer = setTimeout(fly, 180);
      } else fly();
    });
  };
  const tour = createPresentationTour({
    overview(events, duration) {
      overviewActive = true;
      pages.update(null, true);
      const points = events.filter(validPosition);
      if (!points.length) return move({ center: config.mapCenter || [103, 34.3], zoom: config.mapZoom ?? 4 }, duration);
      const longitude = points.map((point) => Number(point.lng));
      const latitude = points.map((point) => Number(point.lat));
      return move([[Math.min(...longitude), Math.min(...latitude)], [Math.max(...longitude), Math.max(...latitude)]], duration, true);
    },
    focus(item, duration) {
      overviewActive = false;
      orbit.stop();
      focusCard(item.id);
      if (item.kind === 'heavy_duty') {
        const points = (items || []).filter(validPosition);
        if (!points.length) return move({ center: config.mapCenter || [103, 34.3], zoom: config.mapZoom ?? 4 }, duration);
        const lng = points.map((point) => Number(point.lng));
        const lat = points.map((point) => Number(point.lat));
        return move([[Math.min(...lng), Math.min(...lat)], [Math.max(...lng), Math.max(...lat)]], duration, true);
      }
      if (validPosition(item)) return move({ center: [Number(item.lng), Number(item.lat)], zoom: presentationFocusZoom(scale) }, duration);
    },
    overviewReady: () => orbit.start(),
    clearFocus: () => focusCard(null, false), cancelMotion: stopMotion, reducedMotion: reduced,
  });
  const allocateLists = () => {
    if (active) pages.update(focusedId);
  };
  const resize = () => {
    if (!active) return;
    const restartOverview = overviewActive && !document.hidden;
    orbit.stop();
    scale = Math.max(.5, Math.min(window.innerWidth / 1920, window.innerHeight / 1080));
    root.style.setProperty('--presentation-scale', scale);
    map.__dashboardPresentationScale = scale;
    allocateLists();
    applyMapScale();
    map.resize();
    onModeChange(true, scale);
    if (restartOverview) tour.restart();
  };
  const switchMode = (next) => {
    if (next === active) return;
    active = next;
    if (active) {
      saved = { center: map.getCenter(), zoom: map.getZoom(), bearing: map.getBearing(), pitch: map.getPitch(),
        padding: map.getPadding?.(), expanded: drawer?.isExpanded(), handlers: {}, disabled: [] };
      for (const name of HANDLERS) { saved.handlers[name] = map[name]?.isEnabled(); map[name]?.disable(); }
      document.querySelectorAll('button, input, select').forEach((control) => {
        if (control !== button) { saved.disabled.push([control, control.disabled]); control.disabled = true; }
      });
      root.classList.add('is-presentation');
      button.focus?.();
      drawer?.setExpanded(true);
      resize();
      if (items !== null && !document.hidden) { tour.setItems(items); tour.start(); }
    } else {
      overviewActive = false;
      tour.stop();
      root.classList.remove('is-presentation');
      delete map.__dashboardPresentationScale;
      applyMapScale();
      pages.clear();
      onModeChange(false, 1);
      if (saved) {
        saved.disabled.forEach(([control, disabled]) => { control.disabled = disabled; });
        for (const name of HANDLERS) if (saved.handlers[name]) map[name]?.enable();
        drawer?.setExpanded(saved.expanded);
        const camera = { center: saved.center, zoom: saved.zoom, bearing: saved.bearing, pitch: saved.pitch, padding: saved.padding || { top: 0, bottom: 0, left: 0, right: 0 } };
        map.resize();
        if (reduced() || document.hidden) map.jumpTo(camera);
        else map.flyTo({ ...camera, duration: 1200 });
      }
      map.resize();
    }
    button.dataset.mode = active ? 'screen' : 'desktop';
    const status = document.getElementById('dashboard-v2-presentation-status');
    const label = active ? '当前：大屏模式 · 点击切换电脑' : '当前：电脑模式 · 点击切换大屏';
    if (status) status.textContent = label;
    button.setAttribute('aria-label', label);
    try { localStorage.setItem('dashboard-v2-display-mode', active ? 'screen' : 'desktop'); } catch (_error) { /* Session-only fallback. */ }
  };
  on(button, 'click', () => switchMode(!active));
  map.on('load', applyMapScale);
  listen.push(() => map.off('load', applyMapScale));
  on(document, 'click', (event) => { if (active && !button.contains(event.target)) { event.preventDefault(); event.stopImmediatePropagation(); } }, true);
  on(document, 'keydown', (event) => {
    if (active && (event.target !== button || event.key === 'Tab')) {
      event.preventDefault(); event.stopImmediatePropagation(); button.focus?.();
    }
  }, true);
  on(window, 'resize', () => { cancelAnimationFrame(resizeFrame); resizeFrame = requestAnimationFrame(resize); });
  on(document, 'visibilitychange', () => {
    if (!active) return;
    if (document.hidden) tour.stop();
    else if (items !== null) { tour.setItems(items); tour.start(); }
  });
  let remembered = false;
  try { remembered = localStorage.getItem('dashboard-v2-display-mode') === 'screen'; } catch (_error) { /* Default desktop. */ }
  if (remembered) switchMode(true);
  return {
    isActive: () => active,
    setItems(events) {
      items = events.map((item) => ({ ...item, id: String(item.id) }));
      if (active) {
        tour.setItems(items);
        if (!document.hidden) tour.start();
        focusCard(tour.currentId(), false);
        allocateLists();
      }
    },
    destroy() { tour.stop(); pages.clear(); cancelAnimationFrame(resizeFrame); listen.forEach((dispose) => dispose()); },
  };
}

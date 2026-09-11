export function validPosition(item) {
  return item?.lng !== null && item?.lng !== undefined && item?.lng !== ''
    && item?.lat !== null && item?.lat !== undefined && item?.lat !== ''
    && Number.isFinite(Number(item.lng)) && Number.isFinite(Number(item.lat))
    && Math.abs(Number(item.lng)) <= 180 && Math.abs(Number(item.lat)) <= 90;
}

// One timer owns the tour; refreshing identical data never restarts it.
export function createPresentationTour({ overview, focus, clearFocus, cancelMotion, overviewReady = () => {},
  setTimer = setTimeout, clearTimer = clearTimeout, reducedMotion = () => false }) {
  let items = [];
  let running = false;
  let timer = null;
  let currentId = null;
  let visited = new Set();
  let epoch = 0;
  const cancel = () => { epoch += 1; clearTimer(timer); timer = null; cancelMotion?.(); };
  const schedule = (fn, ms) => { timer = setTimer(fn, ms); };
  const afterMotion = (result, seconds, next, ready = () => {}) => {
    const token = epoch;
    Promise.resolve(result).then(() => {
      if (running && token === epoch) {
        ready();
        if (next) schedule(next, seconds * 1000);
      }
    }).catch(() => {
      if (running && token === epoch && next) schedule(next, seconds * 1000);
    });
  };
  const next = () => {
    if (!running) return;
    const item = items.find((entry) => !visited.has(entry.id));
    if (!item) { showOverview(); return; }
    visited.add(item.id);
    currentId = item.id;
    afterMotion(focus(item, reducedMotion() ? 0 : 2000), 12, next);
  };
  const showOverview = () => {
    if (!running) return;
    cancel();
    visited = new Set();
    currentId = null;
    clearFocus();
    const result = overview(items, reducedMotion() ? 0 : 2000);
    afterMotion(result, 45, items.length ? next : null, overviewReady);
  };
  return {
    setItems(nextItems) {
      const wasEmpty = !items.length;
      items = nextItems;
      if (!running) return;
      if (currentId !== null && !items.some((item) => item.id === currentId)) {
        cancel(); clearFocus(); currentId = null; next();
      } else if (wasEmpty && items.length) showOverview();
    },
    start() { if (!running) { running = true; showOverview(); } },
    stop() { running = false; cancel(); currentId = null; clearFocus(); },
    restart() { if (running) showOverview(); },
    currentId: () => currentId,
  };
}

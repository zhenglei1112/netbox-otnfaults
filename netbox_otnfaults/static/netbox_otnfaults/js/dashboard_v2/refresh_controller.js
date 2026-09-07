export function createDashboardMapRefresher({
  load,
  onData,
  onError,
  getDataSignature = null,
}) {
  let inFlight = null;
  let hasAppliedData = false;
  let lastDataSignature;

  return function refreshDashboardMapData() {
    if (inFlight) {
      return inFlight;
    }

    let request;
    try {
      request = Promise.resolve(load());
    } catch (error) {
      request = Promise.reject(error);
    }

    const handled = request
      .then((data) => {
        const nextDataSignature = getDataSignature?.(data);
        if (
          hasAppliedData
          && getDataSignature
          && Object.is(nextDataSignature, lastDataSignature)
        ) {
          return data;
        }
        onData(data);
        hasAppliedData = true;
        lastDataSignature = nextDataSignature;
        return data;
      })
      .catch((error) => {
        onError(error);
        return null;
      });
    const guarded = handled.finally(() => {
      if (inFlight === guarded) {
        inFlight = null;
      }
    });
    inFlight = guarded;
    return guarded;
  };
}

export function startDashboardAutoRefresh({
  refresh,
  intervalMs = 30000,
  eventTarget = globalThis.window,
  setIntervalFn = globalThis.setInterval,
  clearIntervalFn = globalThis.clearInterval,
}) {
  refresh();
  const timer = setIntervalFn(refresh, intervalMs);
  let stopped = false;
  const stop = () => {
    if (stopped) return;
    stopped = true;
    clearIntervalFn(timer);
    eventTarget?.removeEventListener?.('pagehide', stop);
  };
  eventTarget?.addEventListener?.('pagehide', stop, { once: true });
  return stop;
}

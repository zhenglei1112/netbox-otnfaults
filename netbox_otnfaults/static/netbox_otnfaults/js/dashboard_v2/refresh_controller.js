export function createDashboardMapRefresher({
  load,
  onData,
  onError,
  onSuccess = () => {},
  getDataSignature = null,
}) {
  let inFlight = null;
  let hasAppliedData = false;
  let lastDataSignature;
  let disposed = false;
  let controller = null;

  function refreshDashboardMapData() {
    if (disposed) return Promise.resolve(null);
    if (inFlight) {
      return inFlight;
    }

    let request;
    try {
      controller = new AbortController();
      request = Promise.resolve(load({ signal: controller.signal }));
    } catch (error) {
      request = Promise.reject(error);
    }

    const handled = request
      .then((data) => {
        if (disposed || controller?.signal.aborted) return null;
        const nextDataSignature = getDataSignature?.(data);
        onSuccess(data);
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
        if (!disposed && !controller?.signal.aborted) onError(error);
        return null;
      });
    const guarded = handled.finally(() => {
      if (inFlight === guarded) {
        inFlight = null;
      }
    });
    inFlight = guarded;
    return guarded;
  }
  refreshDashboardMapData.cancel = () => controller?.abort();
  refreshDashboardMapData.destroy = () => {
    disposed = true;
    controller?.abort();
  };
  return refreshDashboardMapData;
}

export function startDashboardAutoRefresh({
  refresh,
  intervalMs = 30000,
  eventTarget = globalThis.window,
  setIntervalFn = globalThis.setInterval,
  clearIntervalFn = globalThis.clearInterval,
}) {
  refresh();
  let timer = setIntervalFn(refresh, intervalMs);
  let stopped = false;
  const pause = () => {
    clearIntervalFn(timer);
    timer = null;
    refresh.cancel?.();
  };
  const resume = () => {
    if (stopped || timer !== null) return;
    refresh();
    timer = setIntervalFn(refresh, intervalMs);
  };
  const stop = () => {
    if (stopped) return;
    stopped = true;
    if (timer !== null) pause();
    eventTarget?.removeEventListener?.('pagehide', pause);
    eventTarget?.removeEventListener?.('pageshow', resume);
  };
  eventTarget?.addEventListener?.('pagehide', pause);
  eventTarget?.addEventListener?.('pageshow', resume);
  return stop;
}

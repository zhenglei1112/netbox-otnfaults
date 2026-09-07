const DEFAULT_MAX_FPS = 60;
const FRAME_TIME_TOLERANCE_MS = 0.25;
const INSTALLATION_KEY = Symbol.for('netboxOtnfaults.dashboardV2.frameRateLimit');

export function installDashboardV2FrameRateLimit(
  maxFps = DEFAULT_MAX_FPS,
  target = globalThis,
) {
  if (target?.[INSTALLATION_KEY]) return target[INSTALLATION_KEY];
  if (
    !target
    || typeof target.requestAnimationFrame !== 'function'
    || typeof target.cancelAnimationFrame !== 'function'
  ) {
    return null;
  }

  const configuredFps = Number(maxFps);
  const fps = Number.isFinite(configuredFps) && configuredFps > 0
    ? Math.min(configuredFps, DEFAULT_MAX_FPS)
    : DEFAULT_MAX_FPS;
  const frameInterval = 1000 / fps;
  const originalRequestAnimationFrame = target.requestAnimationFrame;
  const originalCancelAnimationFrame = target.cancelAnimationFrame;
  const nativeRequestAnimationFrame = originalRequestAnimationFrame.bind(target);
  const nativeCancelAnimationFrame = originalCancelAnimationFrame.bind(target);
  const callbacks = new Map();
  let callbackId = 0;
  let nativeFrameId = null;
  let nextFrameAt = null;
  let restored = false;

  const requestPump = () => {
    if (nativeFrameId !== null || callbacks.size === 0 || restored) return;
    nativeFrameId = nativeRequestAnimationFrame(pump);
  };
  const pump = (timestamp) => {
    nativeFrameId = null;
    if (callbacks.size === 0 || restored) return;
    if (nextFrameAt === null) nextFrameAt = timestamp;

    if (timestamp + FRAME_TIME_TOLERANCE_MS >= nextFrameAt) {
      const pending = [...callbacks.keys()];
      do {
        nextFrameAt += frameInterval;
      } while (nextFrameAt <= timestamp);
      pending.forEach((id) => {
        const callback = callbacks.get(id);
        if (!callback) return;
        callbacks.delete(id);
        try {
          callback(timestamp);
        } catch (error) {
          if (typeof target.reportError === 'function') target.reportError(error);
          else console.error('[Dashboard V2] 动画回调失败:', error);
        }
      });
    }
    requestPump();
  };

  target.requestAnimationFrame = (callback) => {
    if (typeof callback !== 'function') {
      throw new TypeError('requestAnimationFrame callback must be a function');
    }
    callbackId += 1;
    callbacks.set(callbackId, callback);
    requestPump();
    return callbackId;
  };
  target.cancelAnimationFrame = (id) => {
    callbacks.delete(id);
    if (callbacks.size === 0 && nativeFrameId !== null) {
      nativeCancelAnimationFrame(nativeFrameId);
      nativeFrameId = null;
    }
  };

  const controller = {
    maxFps: fps,
    restore() {
      if (restored) return;
      restored = true;
      callbacks.clear();
      if (nativeFrameId !== null) nativeCancelAnimationFrame(nativeFrameId);
      nativeFrameId = null;
      target.requestAnimationFrame = originalRequestAnimationFrame;
      target.cancelAnimationFrame = originalCancelAnimationFrame;
      delete target[INSTALLATION_KEY];
    },
  };
  target[INSTALLATION_KEY] = controller;
  return controller;
}

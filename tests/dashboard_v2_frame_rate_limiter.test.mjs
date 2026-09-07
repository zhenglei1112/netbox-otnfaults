import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';


const MODULE_PATH = new URL(
  '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/frame_rate_limiter.js',
  import.meta.url,
);
const MODULE_SOURCE = await readFile(MODULE_PATH, 'utf8');


async function loadFrameRateLimiter(tag) {
  const encoded = Buffer.from(MODULE_SOURCE).toString('base64');
  return import(`data:text/javascript;base64,${encoded}#${tag}`);
}


function createNativeFrameTarget() {
  const nativeFrames = new Map();
  let nextId = 0;
  const target = {
    requestAnimationFrame(callback) {
      nextId += 1;
      nativeFrames.set(nextId, callback);
      return nextId;
    },
    cancelAnimationFrame(id) {
      nativeFrames.delete(id);
    },
  };
  return {
    target,
    runFrame(timestamp) {
      const entry = nativeFrames.entries().next().value;
      assert.ok(entry, `missing native frame at ${timestamp}`);
      const [id, callback] = entry;
      nativeFrames.delete(id);
      callback(timestamp);
    },
    pendingCount: () => nativeFrames.size,
  };
}


test('page frame scheduler caps a 120 Hz source at 60 FPS', async () => {
  const { installDashboardV2FrameRateLimit } = await loadFrameRateLimiter('60-fps');
  const native = createNativeFrameTarget();
  const controller = installDashboardV2FrameRateLimit(60, native.target);
  const renderedAt = [];
  const render = (timestamp) => {
    renderedAt.push(timestamp);
    if (renderedAt.length < 4) native.target.requestAnimationFrame(render);
  };

  native.target.requestAnimationFrame(render);
  for (const timestamp of [0, 8.33, 16.67, 25, 33.34, 41.67, 50.01]) {
    native.runFrame(timestamp);
  }

  assert.deepEqual(renderedAt, [0, 16.67, 33.34, 50.01]);
  assert.equal(controller.maxFps, 60);
  assert.equal(native.pendingCount(), 0);
});


test('page frame scheduler supports cancellation and restoring native functions', async () => {
  const { installDashboardV2FrameRateLimit } = await loadFrameRateLimiter('restore');
  const native = createNativeFrameTarget();
  const originalRequest = native.target.requestAnimationFrame;
  const originalCancel = native.target.cancelAnimationFrame;
  const controller = installDashboardV2FrameRateLimit(120, native.target);
  const id = native.target.requestAnimationFrame(() => {});

  native.target.cancelAnimationFrame(id);
  assert.equal(native.pendingCount(), 0);
  assert.equal(controller.maxFps, 60);

  controller.restore();
  assert.equal(native.target.requestAnimationFrame, originalRequest);
  assert.equal(native.target.cancelAnimationFrame, originalCancel);
});

import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';


const MODULE_PATH = new URL(
  '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/refresh_controller.js',
  import.meta.url,
);
const MODULE_SOURCE = await readFile(MODULE_PATH, 'utf8');


async function loadRefreshController(tag) {
  const encoded = Buffer.from(MODULE_SOURCE).toString('base64');
  return import(`data:text/javascript;base64,${encoded}#${tag}`);
}


function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

test('identical successful response clears request error without a data redraw', async () => {
  const { createDashboardMapRefresher } = await loadRefreshController('recover-identical');
  let calls = 0;
  let redraws = 0;
  let status;
  const refresh = createDashboardMapRefresher({
    load: async () => { if (++calls === 2) throw Error('offline'); return { sites: [] }; },
    getDataSignature: JSON.stringify,
    onSuccess: () => { status = 'success'; },
    onData: () => { redraws++; },
    onError: () => { status = 'error'; },
  });
  await refresh(); await refresh(); await refresh();
  assert.equal(status, 'success');
  assert.equal(redraws, 1);
});

test('destroy aborts in-flight work and suppresses late rendering', async () => {
  const { createDashboardMapRefresher } = await loadRefreshController('destroy');
  const request = deferred();
  let signal;
  let applied = 0;
  const refresh = createDashboardMapRefresher({
    load: (options) => { signal = options.signal; return request.promise; },
    onData: () => applied++, onSuccess: () => applied++, onError: () => applied++,
  });
  const running = refresh();
  refresh.destroy();
  request.resolve({});
  await running;
  assert.equal(signal.aborted, true);
  assert.equal(applied, 0);
  assert.equal(await refresh(), null);
});


test('refresh controller suppresses overlapping requests and applies data once', async () => {
  const firstRequest = deferred();
  const loaded = [];
  const applied = [];
  const errors = [];
  const { createDashboardMapRefresher } = await loadRefreshController('overlap');
  const refresh = createDashboardMapRefresher({
    load: () => {
      loaded.push('request');
      return firstRequest.promise;
    },
    onData: (data) => applied.push(data),
    onError: (error) => errors.push(error),
  });

  const firstRefresh = refresh();
  const overlappingRefresh = refresh();

  assert.equal(loaded.length, 1);
  firstRequest.resolve({ sites: [{ id: 1 }], faultPaths: [] });
  await Promise.all([firstRefresh, overlappingRefresh]);
  assert.equal(applied.length, 1);
  assert.equal(errors.length, 0);
});


test('refresh controller releases the in-flight guard after failure', async () => {
  let requestCount = 0;
  const errors = [];
  const { createDashboardMapRefresher } = await loadRefreshController('retry-after-error');
  const refresh = createDashboardMapRefresher({
    load: async () => {
      requestCount += 1;
      if (requestCount === 1) throw new Error('HTTP 503');
      return { sites: [], faultPaths: [] };
    },
    onData() {},
    onError: (error) => errors.push(error.message),
  });

  await refresh();
  await refresh();

  assert.equal(requestCount, 2);
  assert.deepEqual(errors, ['HTTP 503']);
});


test('refresh controller skips rendering when the data signature is unchanged', async () => {
  const responses = [
    { timestamp: '10:00:00', summary: { processing: 1 } },
    { timestamp: '10:00:30', summary: { processing: 1 } },
    { timestamp: '10:01:00', summary: { processing: 2 } },
  ];
  const applied = [];
  const { createDashboardMapRefresher } = await loadRefreshController('unchanged-data');
  const refresh = createDashboardMapRefresher({
    load: async () => responses.shift(),
    getDataSignature: (data) => JSON.stringify(data.summary),
    onData: (data) => applied.push(data),
    onError() {},
  });

  await refresh();
  await refresh();
  await refresh();

  assert.equal(applied.length, 2);
  assert.equal(applied[0].timestamp, '10:00:00');
  assert.equal(applied[1].timestamp, '10:01:00');
});


test('auto refresh runs immediately, repeats every 30 seconds and stops on pagehide', async () => {
  const intervals = [];
  const cleared = [];
  const listeners = {};
  const refreshes = [];
  const eventTarget = {
    addEventListener(name, callback) { listeners[name] = callback; },
    removeEventListener(name, callback) {
      if (listeners[name] === callback) delete listeners[name];
    },
  };
  const { startDashboardAutoRefresh } = await loadRefreshController('lifecycle');
  const stop = startDashboardAutoRefresh({
    refresh: () => refreshes.push('refresh'),
    intervalMs: 30000,
    eventTarget,
    setIntervalFn(callback, interval) {
      intervals.push([callback, interval]);
      return 17;
    },
    clearIntervalFn: (timer) => cleared.push(timer),
  });

  assert.deepEqual(refreshes, ['refresh']);
  assert.equal(intervals[0][1], 30000);
  intervals[0][0]();
  assert.deepEqual(refreshes, ['refresh', 'refresh']);
  listeners.pagehide();
  assert.deepEqual(cleared, [17]);
  stop();
  assert.deepEqual(cleared, [17]);
});

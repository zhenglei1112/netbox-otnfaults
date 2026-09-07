import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';


const MODULE_PATH = new URL(
  '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/data_service.js',
  import.meta.url,
);
const MODULE_SOURCE = await readFile(MODULE_PATH, 'utf8');

test('site version reuses snapshot and rejects unmatched omitted payload', async () => {
  const { fetchDashboardV2Data } = await loadDataService('versions');
  installFetch({ data: { sites_version: 'one', sites: [{ id: 1 }] } });
  const initial = await fetchDashboardV2Data('/data');
  const calls = installFetch({ data: { sites_version: 'one' } });
  const next = await fetchDashboardV2Data('/data');
  assert.equal(next.sites, initial.sites);
  assert.equal(calls[0][0], '/data?sites_version=one');
  installFetch({ data: { sites_version: 'two' } });
  await assert.rejects(fetchDashboardV2Data('/data'), /版本不匹配/);
});

test('elapsed-only changes preserve accepted fault order but fresh duration', async () => {
  const { reconcileDashboardData } = await loadDataService('reconcile');
  const previous = { processing_faults: [{ id: 1 }, { id: 2 }] };
  const next = reconcileDashboardData(previous, {
    processing_faults: [{ id: 2, duration: '2分' }, { id: 1, duration: '3分' }],
  });
  assert.deepEqual(next.processing_faults.map((fault) => fault.id), [1, 2]);
  assert.equal(next.processing_faults[0].duration, '3分');
});

test('stalled requests time out and can be aborted by owner', async () => {
  const { fetchDashboardV2Data } = await loadDataService('abort');
  globalThis.fetch = (url, { signal }) => new Promise((resolve, reject) => {
    signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true });
  });
  await assert.rejects(fetchDashboardV2Data('/data', { timeoutMs: 5 }), /aborted/);
  const controller = new AbortController();
  const pending = fetchDashboardV2Data('/data', { signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, /aborted/);
});


async function loadDataService(tag) {
  const encoded = Buffer.from(MODULE_SOURCE).toString('base64');
  return import(`data:text/javascript;base64,${encoded}#${tag}`);
}


function installFetch({ ok = true, status = 200, data = {} } = {}) {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push([url, options]);
    return {
      ok,
      status,
      async json() {
        return data;
      },
    };
  };
  return calls;
}


test('dashboard V2 data normalizes summary, processing faults and sites', async () => {
  const calls = installFetch({
    data: {
      sites: [{ id: 1, name: 'A站', lng: 116, lat: 39 }],
      timestamp: '2026-09-02T12:00:00+08:00',
      summary: {
        total_faults: 12,
        processing_faults: 3,
        today_faults: 2,
        active_business_interruptions: 4,
      },
      processing_faults: [{ id: 3, fault_number: 'F1' }],
    },
  });
  const { fetchDashboardV2Data } = await loadDataService('success');

  const result = await fetchDashboardV2Data('/plugins/otnfaults/dashboard-v2/data/');

  assert.deepEqual(result.sites, [{ id: 1, name: 'A站', lng: 116, lat: 39 }]);
  assert.deepEqual(result.processing_faults, [{ id: 3, fault_number: 'F1' }]);
  assert.deepEqual(result.summary, {
    total_faults: 12,
    processing_faults: 3,
    today_faults: 2,
    active_business_interruptions: 4,
  });
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], '/plugins/otnfaults/dashboard-v2/data/');
  assert.equal(calls[0][1].credentials, 'same-origin');
  assert.equal(calls[0][1].headers['X-Requested-With'], 'XMLHttpRequest');
});


test('dashboard V2 data defaults missing and invalid values safely', async () => {
  installFetch({ data: { summary: {} } });
  const { fetchDashboardV2Data } = await loadDataService('missing-arrays');

  const result = await fetchDashboardV2Data('/dashboard-v2/data/');

  assert.deepEqual(result.sites, []);
  assert.deepEqual(result.processing_faults, []);
  assert.deepEqual(result.summary, {
    total_faults: 0,
    processing_faults: 0,
    today_faults: 0,
    active_business_interruptions: 0,
  });
});


test('render signature ignores timestamps, derived fields and collection order', async () => {
  const { createDashboardV2RenderSignature } = await loadDataService('render-signature');
  const first = {
    timestamp: '2026-09-03T10:00:00+08:00',
    summary: { total_faults: 2, processing_faults: 1 },
    processing_faults: [
      { id: 7, fault_number: 'F-7', duration: '2小时1分', priority_score: 8.4 },
      { id: 8, fault_number: 'F-8', duration: '31分', priority_score: 6.2 },
    ],
    sites: [{ id: 3, name: '北京' }, { id: 4, name: '上海' }],
  };
  const sameContent = {
    timestamp: '2026-09-03T10:00:30+08:00',
    sites: [{ name: '上海', id: 4 }, { name: '北京', id: 3 }],
    processing_faults: [
      { priority_score: 6.19, duration: '32分', fault_number: 'F-8', id: 8 },
      { priority_score: 8.39, duration: '2小时2分', fault_number: 'F-7', id: 7 },
    ],
    summary: { processing_faults: 1, total_faults: 2 },
  };
  const changedContent = {
    ...sameContent,
    summary: { processing_faults: 2, total_faults: 2 },
  };
  const changedFaultContent = {
    ...sameContent,
    processing_faults: sameContent.processing_faults.map((fault) => (
      fault.id === 7 ? { ...fault, handler: '新处理人' } : fault
    )),
  };

  assert.equal(
    createDashboardV2RenderSignature(first),
    createDashboardV2RenderSignature(sameContent),
  );
  assert.notEqual(
    createDashboardV2RenderSignature(first),
    createDashboardV2RenderSignature(changedContent),
  );
  assert.notEqual(
    createDashboardV2RenderSignature(first),
    createDashboardV2RenderSignature(changedFaultContent),
  );
});


test('dashboard map data reports HTTP failures', async () => {
  installFetch({ ok: false, status: 503 });
  const { fetchDashboardV2Data } = await loadDataService('http-error');

  await assert.rejects(
    fetchDashboardV2Data('/dashboard-v2/data/'),
    /HTTP 503/,
  );
});


test('dashboard map data rejects a non-object JSON payload', async () => {
  installFetch({ data: [] });
  const { fetchDashboardV2Data } = await loadDataService('invalid-json');

  await assert.rejects(
    fetchDashboardV2Data('/dashboard-v2/data/'),
    /数据格式无效/,
  );
});

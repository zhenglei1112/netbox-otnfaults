import assert from 'node:assert/strict';
import test from 'node:test';
import { allocatePageSlots, eventPage, createPresentationPages, pageRangeLabel } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/presentation_pages.js';

test('range labels show total only when all items fit', () => {
  assert.equal(pageRangeLabel(5, 0, 5), '共5条');
  assert.equal(pageRangeLabel(0, 0, 0), '共0条');
  assert.equal(pageRangeLabel(8, 0, 3), '1–3 / 共8条');
  assert.equal(pageRangeLabel(8, 6, 3), '7–8 / 共8条');
});

test('six slots are shared fairly and donated; short screens retain both sections', () => {
  for (const scale of [1, 2]) {
    for (const [counts, expected] of [[[8, 8], [3, 3]], [[5, 1], [5, 1]], [[0, 8], [0, 6]], [[2, 2], [2, 2]], [[0, 0], [0, 0]]]) {
      assert.deepEqual(allocatePageSlots(counts, 720 * scale, 114 * scale, 6 * scale), expected);
    }
    assert.deepEqual(allocatePageSlots([8, 8], 360 * scale, 114 * scale, 6 * scale), [2, 1]);
  }
});

test('page follows selected ID, remains stable otherwise, and clamps after removal', () => {
  assert.equal(eventPage(['a', 'b', 'c', 'd'], 3, 0, 'd'), 1);
  assert.equal(eventPage(['a', 'b', 'c', 'd'], 3, 1, 'cutover-1'), 1);
  assert.equal(eventPage(['a', 'b'], 3, 1, null), 0);
  assert.equal(eventPage(['d', 'a', 'b', 'c'], 3, 1, 'd'), 0);
});

test('DOM pages switch only at boundary, reset in overview, preserve peer, and clean up', () => {
  const previousDocument = globalThis.document;
  const previousStyle = globalThis.getComputedStyle;
  const counters = new Map();
  let fades = 0;
  const makeList = (id, prefix) => {
    const cards = Array.from({ length: 7 }, (_, i) => ({ dataset: { eventId: `${prefix}${i}` } }));
    const list = { id, cards, dataset: {}, style: {}, querySelectorAll: () => cards, animate: () => { fades++; return { cancel() {} }; } };
    counters.set(id.replace('-list', '-count'), { dataset: {} });
    return list;
  };
  const lists = [makeList('fault-list', 'f'), makeList('cutover-list', 'c')];
  try {
    globalThis.document = { getElementById: (id) => counters.get(id) };
    globalThis.getComputedStyle = () => ({ maxHeight: '720px' });
    const pages = createPresentationPages({ lists: () => lists, content: { children: lists, clientHeight: 200 }, scale: () => 1, reduced: () => false });
    pages.update(null, true);
    assert.equal(lists[0].dataset.presentationRange, '1–3 / 共7条');
    pages.update('f2'); assert.equal(fades, 0);
    pages.update('f3'); assert.equal(fades, 1);
    assert.equal(lists[0].cards[0].dataset.presentationHidden, 'true');
    assert.equal(lists[0].cards[3].dataset.presentationHidden, 'false');
    pages.update('f3'); assert.equal(fades, 1);
    pages.update('c4'); assert.equal(fades, 2);
    assert.equal(lists[0].dataset.presentationRange, '4–6 / 共7条');
    pages.update('f6');
    assert.equal(lists[0].style.height, '114px', 'last page shrinks to one complete card');
    pages.update(null, true);
    assert.equal(lists[1].dataset.presentationRange, '1–3 / 共7条');
    pages.clear();
    assert.equal(lists[0].cards[0].dataset.presentationHidden, undefined);
    assert.equal(lists[0].style.height, '');
  } finally {
    globalThis.document = previousDocument; globalThis.getComputedStyle = previousStyle;
  }
});

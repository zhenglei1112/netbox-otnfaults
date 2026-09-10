import assert from 'node:assert/strict';
import test from 'node:test';
import { leaderSegment, segmentsIntersect, scorePlacement, buildPlacementCandidates } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/fault_layout.js';

test('presentation layout uses measured box dimensions rather than desktop constants', () => {
  const candidates = buildPlacementCandidates({ x: 1600, y: 1000 }, 3840, 2160, { width: 704, height: 310, scale: 3.2 });
  for (const candidate of candidates) {
    assert.equal(Math.round(candidate.rect.right - candidate.rect.left), 704);
    assert.equal(Math.round(candidate.rect.bottom - candidate.rect.top), 310);
  }
});

test('detects crossing, collinear overlap and separated leaders', () => {
  const a = { start: { x: 0, y: 0 }, end: { x: 100, y: 100 } };
  assert.equal(segmentsIntersect(a, { start: { x: 0, y: 100 }, end: { x: 100, y: 0 } }), true);
  assert.equal(segmentsIntersect(a, { start: { x: 50, y: 50 }, end: { x: 150, y: 150 } }), true);
  assert.equal(segmentsIntersect(a, { start: { x: 0, y: 10 }, end: { x: 80, y: 100 } }), false);
});

test('uses nearest box edge and prefers a noncrossing placement', () => {
  const point = { x: 400, y: 200 };
  const crossed = { rect: { left: 100, top: 400, right: 320, bottom: 488 }, x: -300, y: 200, rank: 0 };
  const clear = { rect: { left: 100, top: 100, right: 320, bottom: 188 }, x: -300, y: -100, rank: 1 };
  crossed.leader = leaderSegment(point, crossed.rect);
  clear.leader = leaderSegment(point, clear.rect);
  assert.deepEqual(crossed.leader.end, { x: 320, y: 400 });
  const context = { width: 1000, height: 800, placedRects: [], radarRects: [], reservedRects: [],
    placedLeaders: [{ start: { x: 300, y: 200 }, end: { x: 420, y: 400 } }] };
  assert.ok(scorePlacement(crossed, context) > scorePlacement(clear, context) + 1000000);
});

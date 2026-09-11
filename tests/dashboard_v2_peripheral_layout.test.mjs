import test from 'node:test';
import assert from 'node:assert/strict';
import { solvePeripheralLayout, peripheralCompatible } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/peripheral_layout.js';

test('joint peripheral placement has no crossing, overlap or box penetration', () => {
  const entries = [[650, 250], [900, 340], [700, 450], [870, 580], [650, 670], [920, 740]]
    .map(([x, y], i) => ({ faultId: String(i), point: { x, y }, boxWidth: 220, boxHeight: 88 }));
  const result = solvePeripheralLayout(entries, { width: 1500, height: 1000, reservedRects: [{ left: 0, top: 0, right: 300, bottom: 800 }] });
  assert.equal(result?.size, 6);
  const placements = [...result.values()];
  placements.forEach((a, i) => {
    for (const b of placements.slice(i + 1)) assert.equal(peripheralCompatible(a, b), true);
    assert.ok(a.rect.left >= 48 && a.rect.right <= 1452);
    assert.ok(a.rect.top >= 48 && a.rect.bottom <= 952);
  });
  assert.deepEqual(solvePeripheralLayout(entries, { width: 1500, height: 1000, reservedRects: [{ left: 0, top: 0, right: 300, bottom: 800 }] }), result);
});

test('presentation uses staggered diagonal positions with scaled viewport breathing room', () => {
  for (const scale of [1, 2]) {
    const entries = [[850, 240], [1020, 390], [800, 480], [1080, 620]]
      .map(([x, y], i) => ({ faultId: String(i), point: { x: x * scale, y: y * scale },
        boxWidth: 352 * scale, boxHeight: 141 * scale, radius: 22 * scale }));
    const result = solvePeripheralLayout(entries, { width: 1920 * scale, height: 1000 * scale, presentationScale: scale });
    assert.equal(result?.size, 4);
    const values = [...result.values()];
    assert.ok(values.filter((item) => item.direction.length === 2).length >= 3);
    values.forEach((a, i) => {
      assert.ok(a.rect.left >= 48 * scale && a.rect.right <= 1872 * scale);
      assert.ok(a.rect.top >= 48 * scale && a.rect.bottom <= 952 * scale);
      for (const b of values.slice(i + 1)) assert.ok(peripheralCompatible(a, b));
    });
  }
});

test('impossible viewport and exhausted search return explicit fallback', () => {
  const entries = [{ faultId: 'x', point: { x: 50, y: 50 }, boxWidth: 220, boxHeight: 88 }];
  assert.equal(solvePeripheralLayout(entries, { width: 100, height: 100 }), null);
  assert.equal(solvePeripheralLayout(entries, { width: 1500, height: 1000 }, 0), null);
});

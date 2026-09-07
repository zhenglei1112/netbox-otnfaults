import assert from 'node:assert/strict';
import test from 'node:test';

import { galacticTextureCoordinates } from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/galaxy.js';


test('maps the Galactic center to the middle of the panorama', () => {
  assert.deepEqual(galacticTextureCoordinates([1, 0, 0]), { u: 0.5, v: 0.5 });
});


test('maps Galactic poles to the panorama edges', () => {
  assert.deepEqual(galacticTextureCoordinates([0, 0, 1]), { u: 0.5, v: 0 });
  assert.deepEqual(galacticTextureCoordinates([0, 0, -1]), { u: 0.5, v: 1 });
});

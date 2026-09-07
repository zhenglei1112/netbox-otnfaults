import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildMilkyWayParticles,
  createCelestialView,
  galacticToEquatorialVector,
  greenwichMeanSiderealDegrees,
  projectCelestialVector,
} from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/starfield.js';


test('computes Greenwich sidereal angle at the J2000 epoch', () => {
  const angle = greenwichMeanSiderealDegrees(new Date('2000-01-01T12:00:00.000Z'));
  assert.ok(Math.abs(angle - 280.46061837) < 1e-7);
});


test('projects the celestial view direction to the screen center', () => {
  const view = createCelestialView([103, 34.3], -5);
  const projected = projectCelestialVector(view.forward, view, 1000, 600, 90);
  assert.ok(projected);
  assert.ok(Math.abs(projected.x - 500) < 1e-9);
  assert.ok(Math.abs(projected.y - 300) < 1e-9);
});


test('builds a deterministic Milky Way band in the real galactic plane', () => {
  const galacticCenter = galacticToEquatorialVector(0, 0);
  assert.ok(Math.abs(galacticCenter[0] - -0.0548755604) < 1e-9);
  assert.ok(Math.abs(galacticCenter[1] - -0.8734370902) < 1e-9);
  assert.ok(Math.abs(galacticCenter[2] - -0.4838350155) < 1e-9);
  const particles = buildMilkyWayParticles();
  assert.equal(particles.length, 2880);
  assert.deepEqual(particles.slice(0, 3), buildMilkyWayParticles().slice(0, 3));
});

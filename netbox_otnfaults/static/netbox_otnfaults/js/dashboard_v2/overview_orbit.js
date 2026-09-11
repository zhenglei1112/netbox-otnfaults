export function orbitLongitude(base, amplitude, progress) {
  const phase = Math.max(0, Math.min(1, progress));
  // Zero velocity at the start, both turnarounds and finish.
  return base + amplitude * Math.sin(2 * Math.PI * phase) ** 3;
}

export function createOverviewOrbit({ map, reduced }) {
  let endHandler = null;
  let generation = 0;
  const stop = () => {
    generation++;
    if (endHandler) {
      map.off('moveend', endHandler);
      endHandler = null;
      map.stop();
    }
    delete map.__dashboardOverviewLayoutLocked;
    if (map.__dashboardOverviewOrbit) map.__dashboardOverviewOrbit.state = 'stopped';
  };
  const start = () => {
    stop();
    map.__dashboardOverviewLayoutLocked = true;
    const diagnostics = { round: (map.__dashboardOverviewOrbit?.round || 0) + 1, state: 'starting', amplitude: 0 };
    map.__dashboardOverviewOrbit = diagnostics;
    if (reduced()) { diagnostics.state = 'reduced-motion'; return; }
    const center = map.getCenter();
    const zoom = map.getZoom();
    const pixelPerDegree = 512 * 2 ** zoom / 360;
    const margin = map.__dashboardOverviewMargin;
    const amplitude = Number.isFinite(margin) ? Math.min(8, Math.max(0, margin - 16) / (pixelPerDegree * 2)) : 8;
    diagnostics.amplitude = amplitude;
    diagnostics.margin = margin;
    diagnostics.state = amplitude ? 'running' : 'insufficient-space';
    if (!amplitude) return;
    const token = generation;
    const legs = [[amplitude, 11250], [-amplitude, 22500], [0, 11250]];
    const next = () => {
      if (token !== generation) return;
      const leg = legs.shift();
      if (!leg) { diagnostics.state = 'complete'; return; }
      endHandler = () => {
        if (token !== generation) return;
        map.off('moveend', endHandler);
        endHandler = null;
        next();
      };
      map.on('moveend', endHandler);
      map.easeTo({ center: [center.lng + leg[0], center.lat], zoom, bearing: 0, pitch: 0,
        duration: leg[1], easing: (t) => (1 - Math.cos(Math.PI * t)) / 2 });
    };
    next();
  };
  return { start, stop };
}

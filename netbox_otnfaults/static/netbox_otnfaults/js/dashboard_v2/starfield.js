const DEG_TO_RAD = Math.PI / 180;
const RAD_TO_DEG = 180 / Math.PI;
const STAR_DATA_URL = new URL(
  '../../data/dashboard_v2_hyg_bright_stars.json',
  import.meta.url,
);
const PRIMARY_STAR_MAX_MAGNITUDE = 3;

const GALACTIC_TO_EQUATORIAL = [
  [-0.0548755604, 0.4941094279, -0.8676661490],
  [-0.8734370902, -0.44482963, -0.1980763734],
  [-0.4838350155, 0.7469822445, 0.4559837762],
];

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function normalizeDegrees(value) {
  return ((value % 360) + 360) % 360;
}

function sphericalVector(longitudeDegrees, latitudeDegrees) {
  const longitude = longitudeDegrees * DEG_TO_RAD;
  const latitude = latitudeDegrees * DEG_TO_RAD;
  const latitudeCosine = Math.cos(latitude);
  return [
    latitudeCosine * Math.cos(longitude),
    latitudeCosine * Math.sin(longitude),
    Math.sin(latitude),
  ];
}

function dot(a, b) {
  return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2]);
}

export function greenwichMeanSiderealDegrees(date = new Date()) {
  const julianDate = (date.getTime() / 86400000) + 2440587.5;
  const daysSinceJ2000 = julianDate - 2451545.0;
  return normalizeDegrees(280.46061837 + (360.98564736629 * daysSinceJ2000));
}

export function galacticToEquatorialVector(longitudeDegrees, latitudeDegrees) {
  const galactic = sphericalVector(longitudeDegrees, latitudeDegrees);
  return GALACTIC_TO_EQUATORIAL.map((row) => dot(row, galactic));
}

function equatorialVector(rightAscensionHours, declinationDegrees) {
  return sphericalVector(rightAscensionHours * 15, declinationDegrees);
}

function rotateEquatorialToEarth(vector, siderealDegrees) {
  const angle = siderealDegrees * DEG_TO_RAD;
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return [
    (vector[0] * cosine) + (vector[1] * sine),
    (vector[1] * cosine) - (vector[0] * sine),
    vector[2],
  ];
}

export function createCelestialView(center, bearingDegrees = 0) {
  const longitude = (Number(center?.lng ?? center?.[0] ?? 0) + 180) * DEG_TO_RAD;
  const latitude = -Number(center?.lat ?? center?.[1] ?? 0) * DEG_TO_RAD;
  const forward = [
    Math.cos(latitude) * Math.cos(longitude),
    Math.cos(latitude) * Math.sin(longitude),
    Math.sin(latitude),
  ];
  const east = [-Math.sin(longitude), Math.cos(longitude), 0];
  const north = [
    -Math.sin(latitude) * Math.cos(longitude),
    -Math.sin(latitude) * Math.sin(longitude),
    Math.cos(latitude),
  ];
  const bearing = bearingDegrees * DEG_TO_RAD;
  const right = east.map((value, index) => (
    (value * Math.cos(bearing)) - (north[index] * Math.sin(bearing))
  ));
  const up = north.map((value, index) => (
    (east[index] * Math.sin(bearing)) + (value * Math.cos(bearing))
  ));
  return { forward, right, up };
}

export function projectCelestialVector(vector, view, width, height, fieldOfViewDegrees = 100) {
  const depth = dot(vector, view.forward);
  if (depth <= 0.08) return null;
  const focalLength = (Math.min(width, height) * 0.5)
    / Math.tan(fieldOfViewDegrees * DEG_TO_RAD * 0.5);
  return {
    x: (width * 0.5) + ((dot(vector, view.right) / depth) * focalLength),
    y: (height * 0.5) - ((dot(vector, view.up) / depth) * focalLength),
    depth,
  };
}

function seededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function gaussian(random) {
  const first = Math.max(random(), 1e-7);
  return Math.sqrt(-2 * Math.log(first)) * Math.cos(2 * Math.PI * random());
}

export function buildMilkyWayParticles() {
  const random = seededRandom(20260901);
  const particles = [];
  for (let longitude = 0; longitude < 360; longitude += 0.75) {
    const centerWeight = 0.35 + (0.65 * Math.exp(-(
      Math.min(longitude, 360 - longitude) ** 2
    ) / (2 * 52 ** 2)));
    for (let index = 0; index < 6; index += 1) {
      const latitude = clamp(gaussian(random) * (3.2 + (4.5 * random())), -18, 18);
      particles.push({
        vector: galacticToEquatorialVector(longitude + ((random() - 0.5) * 1.2), latitude),
        radius: 0.45 + (random() * 2.4) + (centerWeight * 1.5),
        alpha: 0.012 + (random() * 0.038) + (centerWeight * 0.025),
        warm: centerWeight > 0.7 && random() > 0.45,
      });
    }
  }
  return particles;
}

function colorForIndex(colorIndex) {
  if (!Number.isFinite(colorIndex)) return '#d7e8ff';
  if (colorIndex < -0.1) return '#91bdff';
  if (colorIndex < 0.35) return '#bed8ff';
  if (colorIndex < 0.8) return '#fff4dc';
  if (colorIndex < 1.35) return '#ffd19b';
  return '#ffad79';
}

function prepareStars(rows) {
  return rows.map(([rightAscension, declination, magnitude, colorIndex]) => ({
    vector: equatorialVector(Number(rightAscension), Number(declination)),
    magnitude: Number(magnitude),
    color: colorForIndex(Number(colorIndex)),
  }));
}

export function celestialFieldOfView(map) {
  const zoom = Number(map?.getZoom?.() ?? 1.8);
  return clamp(108 - (zoom * 7), 66, 104);
}

function drawSpaceBase(context, width, height) {
  context.clearRect(0, 0, width, height);
  const glow = context.createRadialGradient(
    width * 0.52, height * 0.48, 0,
    width * 0.52, height * 0.48, Math.max(width, height) * 0.72,
  );
  glow.addColorStop(0, 'rgba(12, 28, 48, 0.34)');
  glow.addColorStop(0.55, 'rgba(4, 12, 24, 0.16)');
  glow.addColorStop(1, 'rgba(0, 1, 5, 0)');
  context.fillStyle = glow;
  context.fillRect(0, 0, width, height);
}

function drawMilkyWay(context, particles, siderealDegrees, view, width, height, fieldOfView) {
  context.globalCompositeOperation = 'screen';
  for (const particle of particles) {
    const earthVector = rotateEquatorialToEarth(particle.vector, siderealDegrees);
    const projected = projectCelestialVector(earthVector, view, width, height, fieldOfView);
    if (!projected || projected.x < -20 || projected.x > width + 20
      || projected.y < -20 || projected.y > height + 20) continue;
    context.globalAlpha = particle.alpha * clamp(projected.depth * 1.6, 0.25, 1);
    context.fillStyle = particle.warm ? '#a66d55' : '#7894b7';
    context.beginPath();
    context.arc(projected.x, projected.y, particle.radius, 0, Math.PI * 2);
    context.fill();
  }
}

function drawStars(context, stars, siderealDegrees, view, width, height, fieldOfView) {
  for (const star of stars) {
    const earthVector = rotateEquatorialToEarth(star.vector, siderealDegrees);
    const projected = projectCelestialVector(earthVector, view, width, height, fieldOfView);
    if (!projected || projected.x < -4 || projected.x > width + 4
      || projected.y < -4 || projected.y > height + 4) continue;
    const radius = clamp(2.15 - ((star.magnitude + 1.45) * 0.235), 0.32, 2.65);
    const alpha = clamp(1.04 - ((star.magnitude + 1) * 0.085), 0.38, 0.96);
    context.globalAlpha = alpha;
    context.fillStyle = star.color;
    context.beginPath();
    context.arc(projected.x, projected.y, radius, 0, Math.PI * 2);
    context.fill();
  }
  context.globalAlpha = 1;
  context.globalCompositeOperation = 'source-over';
}

export async function initializeDashboardV2Starfield(map) {
  const canvas = document.getElementById('dashboard-v2-starfield');
  if (!canvas || !map) return null;
  const context = canvas.getContext('2d', { alpha: true });
  if (!context) return null;

  const response = await fetch(STAR_DATA_URL);
  if (!response.ok) throw new Error(`星表加载失败 (${response.status})`);
  const stars = prepareStars(await response.json());
  const primaryStars = stars.filter((star) => star.magnitude <= PRIMARY_STAR_MAX_MAGNITUDE);
  const milkyWay = buildMilkyWayParticles();
  let animationFrame = 0;
  let mode = 'full';

  const render = () => {
    animationFrame = 0;
    const bounds = canvas.getBoundingClientRect();
    const pixelRatio = clamp(window.devicePixelRatio || 1, 1, 2);
    const width = Math.max(1, Math.round(bounds.width * pixelRatio));
    const height = Math.max(1, Math.round(bounds.height * pixelRatio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    drawSpaceBase(context, width, height);
    if (mode === 'off') return;
    const view = createCelestialView(map.getCenter?.() ?? [103, 34.3], map.getBearing?.() ?? 0);
    const siderealDegrees = greenwichMeanSiderealDegrees(new Date());
    const fieldOfView = celestialFieldOfView(map);
    if (mode === 'full') {
      drawMilkyWay(context, milkyWay, siderealDegrees, view, width, height, fieldOfView);
    }
    const visibleStars = mode === 'primary'
      ? primaryStars
      : stars;
    drawStars(context, visibleStars, siderealDegrees, view, width, height, fieldOfView);
  };
  const scheduleRender = () => {
    if (animationFrame) return;
    animationFrame = requestAnimationFrame(render);
  };

  map.on('move', scheduleRender);
  map.on('resize', scheduleRender);
  const resizeObserver = typeof ResizeObserver === 'function'
    ? new ResizeObserver(scheduleRender)
    : null;
  resizeObserver?.observe(canvas);
  const clockTimer = window.setInterval(scheduleRender, 60000);
  scheduleRender();

  return {
    render: scheduleRender,
    setMode(nextMode) {
      mode = ['full', 'primary', 'off'].includes(nextMode) ? nextMode : 'full';
      scheduleRender();
    },
    destroy() {
      resizeObserver?.disconnect();
      window.clearInterval(clockTimer);
      if (animationFrame) cancelAnimationFrame(animationFrame);
    },
  };
}

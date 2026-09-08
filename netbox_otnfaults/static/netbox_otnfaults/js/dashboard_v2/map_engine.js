import { createFaultOverlayController } from './fault_overlays.js?v=20260908-toolbar-icons-v1';
let dashboardMap = null;
let hasRuntimeMapError = false;
let pmtilesProtocolRegistered = false;
const sourceSignatures = new WeakMap();

function setSourceDataIfChanged(source, data) {
  const signature = JSON.stringify(data);
  if (sourceSignatures.get(source) === signature) return;
  source.setData(data);
  sourceSignatures.set(source, signature);
}

const SMALL_SCALE_LABEL_MIN_ZOOM = 5.5;
const GRATICULE_SOURCE_ID = 'dashboard-v2-graticule-source';
const GRATICULE_LAYER_ID = 'dashboard-v2-graticule';
const CHINA_PROVINCES_SOURCE_ID = 'dashboard-v2-china-provinces';
const CHINA_PROVINCES_GLOW_LAYER_ID = 'dashboard-v2-china-provinces-glow';
const CHINA_PROVINCES_MAIN_LAYER_ID = 'dashboard-v2-china-provinces-main';
const OTN_PATHS_SOURCE_ID = 'dashboard-v2-otn-paths';
const OTN_PATHS_GLOW_LAYER_ID = 'dashboard-v2-otn-paths-glow';
const OTN_PATHS_MAIN_LAYER_ID = 'dashboard-v2-otn-paths-main';
const SITES_SOURCE_ID = 'dashboard-v2-sites';
const SITES_GLOW_LAYER_ID = 'dashboard-v2-sites-glow';
const SITES_CORE_LAYER_ID = 'dashboard-v2-sites-core';
const SITES_LABEL_LAYER_ID = 'dashboard-v2-sites-label';
const PROCESSING_FAULTS_SOURCE_ID = 'dashboard-v2-processing-faults';
const PROCESSING_FAULTS_GLOW_LAYER_ID = 'dashboard-v2-processing-faults-glow';
const PROCESSING_FAULTS_RING_LAYER_ID = 'dashboard-v2-processing-faults-ring';
const PROCESSING_FAULTS_CORE_LAYER_ID = 'dashboard-v2-processing-faults-core';
const PROCESSING_FAULTS_LABEL_LAYER_ID = 'dashboard-v2-processing-faults-label';
const BASE_NETWORK_LAYER_IDS = [
  OTN_PATHS_GLOW_LAYER_ID,
  OTN_PATHS_MAIN_LAYER_ID,
  SITES_GLOW_LAYER_ID,
  SITES_CORE_LAYER_ID,
  SITES_LABEL_LAYER_ID,
];
const LONGITUDE_STEP = 15;
const LATITUDE_STEP = 10;
const LATITUDE_SEGMENT_SPAN = 45;
const SITE_LABEL_MIN_ZOOM = 6;
const SITE_LABEL_FONT = 'HarmonyOS Sans SC Regular';
const FIXED_MAP_BEARING = 0;

const GLOBE_PALETTE = {
  space: '#020814',
  land: '#142b4d',
  landAccent: '#183457',
  water: '#031522',
  road: '#243d5b',
  waterLine: '#1c4568',
  boundary: '#53657a',
  label: '#a9bad0',
  labelHalo: '#0b1b31',
};

const NON_CAPITAL_POINT_FILTER = [
  '!',
  [
    'in',
    ['to-string', ['coalesce', ['get', 'capital'], ['get', 'is_capital'], '']],
    ['literal', ['2', '4', 'yes', 'true']],
  ],
];

const HIDDEN_PLACE_LABEL_NAMES = [
  '台湾', '臺灣', '台湾省', '臺灣省', '台北', '臺北', '台北市', '臺北市',
  'Taiwan', 'Taiwan Province', 'Taipei', 'Taipei City',
];

const GLOBE_SKY_CONFIG = {
  'sky-color': 'rgba(2, 7, 19, 0)',
  'horizon-color': 'rgba(2, 7, 19, 0)',
  'fog-color': 'rgba(2, 7, 19, 0)',
  'sky-horizon-blend': 0,
  'horizon-fog-blend': 0,
  'fog-ground-blend': 0,
  'atmosphere-blend': 0,
};

function setMapStatus(message, state) {
  const status = document.getElementById('dashboard-v2-map-status');
  const dot = document.getElementById('dashboard-v2-status-dot');
  const text = document.getElementById('dashboard-v2-status-text');

  if (status) {
    status.textContent = message;
    status.className = state ? `is-${state}` : '';
  }
  if (text) {
    text.textContent = message;
  }
  if (dot) {
    dot.classList.toggle('is-error', state === 'error');
  }
}

function resolveUrl(url) {
  if (!url || typeof url !== 'string') return url;
  if (/^(?:[a-z]+:)?\/\//i.test(url) || url.startsWith('data:') || url.startsWith('blob:')) {
    return url;
  }
  return new URL(url, window.location.origin)
    .toString()
    .replace(/%7B/gi, '{')
    .replace(/%7D/gi, '}');
}

function registerPmtilesProtocol() {
  if (pmtilesProtocolRegistered) return;
  if (typeof pmtiles === 'undefined') {
    throw new Error('PMTiles 库未加载');
  }
  const protocol = new pmtiles.Protocol();
  maplibregl.addProtocol('pmtiles', protocol.tile);
  pmtilesProtocolRegistered = true;
}

function lockMapRotation(map) {
  map.touchZoomRotate?.disableRotation?.();
  map.keyboard?.disableRotation?.();
}

const mapDomDisposers = new WeakMap();

function listenForMap(map, element, event, handler) {
  element.addEventListener(event, handler);
  if (!mapDomDisposers.has(map)) mapDomDisposers.set(map, []);
  mapDomDisposers.get(map).push(() => element.removeEventListener(event, handler));
}

function enableRightButtonZoom(map) {
  const canvas = map.getCanvas?.();
  if (!canvas) return;

  let activePointerId = null;
  let startY = 0;
  let startZoom = 0;

  listenForMap(map, canvas, 'contextmenu', (event) => event.preventDefault());
  listenForMap(map, canvas, 'pointerdown', (event) => {
    if (event.button !== 2) return;
    event.preventDefault();
    activePointerId = event.pointerId;
    startY = event.clientY;
    startZoom = map.getZoom();
    canvas.setPointerCapture?.(event.pointerId);
  });
  listenForMap(map, canvas, 'pointermove', (event) => {
    if (event.pointerId !== activePointerId) return;
    event.preventDefault();
    const minZoom = map.getMinZoom?.() ?? 0;
    const maxZoom = map.getMaxZoom?.() ?? 24;
    const nextZoom = Math.min(
      maxZoom,
      Math.max(minZoom, startZoom + ((startY - event.clientY) / 120)),
    );
    map.setZoom(nextZoom);
  });
  const finishZoom = (event) => {
    if (event.pointerId !== activePointerId) return;
    canvas.releasePointerCapture?.(event.pointerId);
    activePointerId = null;
  };
  listenForMap(map, canvas, 'pointerup', finishZoom);
  listenForMap(map, canvas, 'pointercancel', finishZoom);
}

function initializeHomeControl(map, initialCamera) {
  const homeButton = document.getElementById('dashboard-v2-map-home');
  if (!homeButton) return;

  listenForMap(map, homeButton, 'click', () => {
    const camera = {
      center: [...initialCamera.center],
      zoom: initialCamera.zoom,
      pitch: initialCamera.pitch,
      bearing: initialCamera.bearing,
      duration: 800,
      essential: true,
    };
    if (typeof map.easeTo === 'function') {
      map.easeTo(camera);
    } else {
      map.jumpTo?.(camera);
    }
  });
}

function buildGraticuleGeoJson() {
  const features = [];

  for (let longitude = -180; longitude < 180; longitude += LONGITUDE_STEP) {
    const coordinates = [];
    for (let latitude = -85; latitude <= 85; latitude += 1) {
      coordinates.push([longitude, latitude]);
    }
    features.push({
      type: 'Feature',
      properties: { kind: 'longitude', value: longitude },
      geometry: { type: 'LineString', coordinates },
    });
  }

  for (let latitude = -80; latitude <= 80; latitude += LATITUDE_STEP) {
    const segments = [];
    for (
      let segmentStart = -180;
      segmentStart < 180;
      segmentStart += LATITUDE_SEGMENT_SPAN
    ) {
      const coordinates = [];
      const segmentEnd = Math.min(segmentStart + LATITUDE_SEGMENT_SPAN, 180);
      for (let longitude = segmentStart; longitude <= segmentEnd; longitude += 1) {
        coordinates.push([longitude, latitude]);
      }
      segments.push(coordinates);
    }
    features.push({
      type: 'Feature',
      properties: { kind: 'latitude', value: latitude },
      geometry: { type: 'MultiLineString', coordinates: segments },
    });
  }

  return { type: 'FeatureCollection', features };
}

function addGraticuleToStyle(style) {
  style.sources = style.sources || {};
  style.layers = Array.isArray(style.layers) ? style.layers : [];
  style.sources[GRATICULE_SOURCE_ID] = {
    type: 'geojson',
    data: buildGraticuleGeoJson(),
  };

  const graticuleLayer = {
    id: GRATICULE_LAYER_ID,
    type: 'line',
    source: GRATICULE_SOURCE_ID,
    layout: { visibility: 'none' },
    paint: {
      'line-color': '#463d4c',
      'line-opacity': 0.62,
      'line-width': ['interpolate', ['linear'], ['zoom'], 0, 0.45, 6, 0.8],
    },
  };
  const boundaryIndex = style.layers.findIndex((layer) => (
    /boundary|boundaries/i.test(`${layer?.id || ''} ${layer?.['source-layer'] || ''}`)
  ));
  if (boundaryIndex >= 0) {
    style.layers.splice(boundaryIndex, 0, graticuleLayer);
  } else {
    style.layers.push(graticuleLayer);
  }
}

function addBaseNetworkPathsToStyle(style, config) {
  style.sources = style.sources || {};
  style.layers = Array.isArray(style.layers) ? style.layers : [];
  const tilesUrl = config.otnPathsPmtilesUrl || '/maps/otn_paths.pmtiles';
  style.sources[OTN_PATHS_SOURCE_ID] = {
    type: 'vector',
    url: `pmtiles://${resolveUrl(tilesUrl)}`,
  };
  style.layers.push({
    id: OTN_PATHS_GLOW_LAYER_ID,
    type: 'line',
    source: OTN_PATHS_SOURCE_ID,
    'source-layer': 'otn_paths',
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': 'rgba(16, 185, 129, 0.22)',
      'line-width': ['interpolate', ['linear'], ['zoom'], 0, 2.6, 3, 3, 7, 6, 10, 10],
      'line-blur': 3,
    },
  }, {
    id: OTN_PATHS_MAIN_LAYER_ID,
    type: 'line',
    source: OTN_PATHS_SOURCE_ID,
    'source-layer': 'otn_paths',
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': '#10b981',
      'line-width': ['interpolate', ['linear'], ['zoom'], 0, 0.7, 3, 0.8, 7, 1.5, 10, 2.2],
      'line-opacity': 0.92,
    },
  });
}

function addChinaProvinceBoundariesToStyle(style, config) {
  style.sources = style.sources || {};
  style.layers = Array.isArray(style.layers) ? style.layers : [];
  const tilesUrl = config.chinaProvincesPmtilesUrl || '/maps/china_provinces.pmtiles';
  style.sources[CHINA_PROVINCES_SOURCE_ID] = {
    type: 'vector',
    url: `pmtiles://${resolveUrl(tilesUrl)}`,
  };

  const provinceLayers = [{
    id: CHINA_PROVINCES_GLOW_LAYER_ID,
    type: 'line',
    source: CHINA_PROVINCES_SOURCE_ID,
    'source-layer': 'china_provinces',
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': '#214d76',
      'line-opacity': ['interpolate', ['linear'], ['zoom'], 0, 0.55, 6, 0.82],
      'line-width': ['interpolate', ['linear'], ['zoom'], 0, 1.1, 6, 2.8],
      'line-blur': 1.2,
    },
  }, {
    id: CHINA_PROVINCES_MAIN_LAYER_ID,
    type: 'line',
    source: CHINA_PROVINCES_SOURCE_ID,
    'source-layer': 'china_provinces',
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': '#7896b7',
      'line-opacity': ['interpolate', ['linear'], ['zoom'], 0, 0.62, 6, 0.9],
      'line-width': ['interpolate', ['linear'], ['zoom'], 0, 0.32, 6, 1.05],
    },
  }];

  const roadOrSymbolIndex = style.layers.findIndex((layer) => {
    const identity = `${layer?.id || ''} ${layer?.['source-layer'] || ''}`;
    return layer?.type === 'symbol' || /road|transport|highway|motorway|trunk|street/i.test(identity);
  });
  if (roadOrSymbolIndex >= 0) {
    style.layers.splice(roadOrSymbolIndex, 0, ...provinceLayers);
  } else {
    style.layers.push(...provinceLayers);
  }
}

function addSitesToStyle(style) {
  style.sources = style.sources || {};
  style.layers = Array.isArray(style.layers) ? style.layers : [];
  style.sources[SITES_SOURCE_ID] = {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  };
  style.layers.push({
    id: SITES_GLOW_LAYER_ID,
    type: 'circle',
    source: SITES_SOURCE_ID,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 0, 2.8, 6, 5.5],
      'circle-color': 'rgba(16, 185, 129, 0.18)',
      'circle-blur': 1,
    },
  }, {
    id: SITES_CORE_LAYER_ID,
    type: 'circle',
    source: SITES_SOURCE_ID,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 0, 1, 6, 2.1],
      'circle-color': '#10b981',
      'circle-stroke-color': 'rgba(167, 243, 208, 0.72)',
      'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 0, 0.35, 6, 0.7],
    },
  }, {
    id: SITES_LABEL_LAYER_ID,
    type: 'symbol',
    source: SITES_SOURCE_ID,
    minzoom: SITE_LABEL_MIN_ZOOM,
    layout: {
      'text-field': ['get', 'name'],
      'text-font': [SITE_LABEL_FONT],
      'text-size': ['interpolate', ['linear'], ['zoom'], 6, 9, 10, 11],
      'text-anchor': 'top',
      'text-offset': [0, 0.55],
      'text-allow-overlap': false,
      'text-ignore-placement': false,
      'text-padding': 2,
    },
    paint: {
      'text-color': 'rgba(167, 243, 208, 0.88)',
      'text-halo-color': '#020814',
      'text-halo-width': 1.2,
      'text-halo-blur': 0.5,
    },
  });
}

function processingFaultColorExpression() {
  return ['coalesce', ['get', 'color'], '#ff334f'];
}

function processingFaultRadiusExpression(inactiveNear, activeNear, inactiveFar, activeFar) {
  const isActive = ['boolean', ['feature-state', 'active'], false];
  return [
    'interpolate', ['linear'], ['zoom'],
    0, ['case', isActive, activeNear, inactiveNear],
    7, ['case', isActive, activeFar, inactiveFar],
  ];
}

function addProcessingFaultsToStyle(style) {
  style.sources = style.sources || {};
  style.layers = Array.isArray(style.layers) ? style.layers : [];
  style.sources[PROCESSING_FAULTS_SOURCE_ID] = {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  };
  const isActive = ['boolean', ['feature-state', 'active'], false];
  style.layers.push({
    id: PROCESSING_FAULTS_GLOW_LAYER_ID,
    type: 'circle',
    source: PROCESSING_FAULTS_SOURCE_ID,
    paint: {
      'circle-radius': processingFaultRadiusExpression(7, 9, 10, 13),
      'circle-color': processingFaultColorExpression(),
      'circle-opacity': ['case', isActive, 0.38, 0.24],
      'circle-blur': 0.68,
    },
  }, {
    id: PROCESSING_FAULTS_RING_LAYER_ID,
    type: 'circle',
    source: PROCESSING_FAULTS_SOURCE_ID,
    paint: {
      'circle-radius': processingFaultRadiusExpression(5.8, 6.8, 7.2, 8.4),
      'circle-color': '#210912',
      'circle-opacity': 0.96,
      'circle-stroke-color': processingFaultColorExpression(),
      'circle-stroke-opacity': ['case', isActive, 1, 0.86],
      'circle-stroke-width': ['case', isActive, 2.2, 1.4],
    },
  }, {
    id: PROCESSING_FAULTS_CORE_LAYER_ID,
    type: 'circle',
    source: PROCESSING_FAULTS_SOURCE_ID,
    paint: {
      'circle-radius': processingFaultRadiusExpression(4.3, 5, 5.3, 6.2),
      'circle-color': '#3a0b17',
      'circle-opacity': 0.98,
      'circle-stroke-color': 'rgba(255, 111, 127, 0.52)',
      'circle-stroke-width': 0.6,
    },
  }, {
    id: PROCESSING_FAULTS_LABEL_LAYER_ID,
    type: 'symbol',
    source: PROCESSING_FAULTS_SOURCE_ID,
    layout: {
      'text-field': ['get', 'index_label'],
      'text-font': [SITE_LABEL_FONT],
      'text-size': ['interpolate', ['linear'], ['zoom'], 0, 10, 7, 13],
      'text-allow-overlap': true,
      'text-ignore-placement': true,
    },
    paint: {
      'text-color': '#f4f9ff',
      'text-halo-color': 'rgba(58, 11, 23, 0.92)',
      'text-halo-width': 0.35,
    },
  });
}

export function renderDashboardV2Sites(map, sites = []) {
  const source = map?.getSource?.(SITES_SOURCE_ID);
  if (!source?.setData) {
    if (typeof map?.once === 'function' && !map.loaded?.()) {
      map.once('load', () => renderDashboardV2Sites(map, sites));
    }
    return 0;
  }
  const features = sites.flatMap((site) => {
    if (site?.lng == null || site?.lat == null || site.lng === '' || site.lat === '') return [];
    const longitude = Number(site?.lng);
    const latitude = Number(site?.lat);
    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return [];
    if (longitude < -180 || longitude > 180 || latitude < -90 || latitude > 90) return [];
    return [{
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [longitude, latitude] },
      properties: {
        id: String(site.id ?? ''),
        name: String(site.name ?? ''),
      },
    }];
  });
  features.sort((a, b) => a.properties.id.localeCompare(b.properties.id));
  setSourceDataIfChanged(source, { type: 'FeatureCollection', features });
  return features.length;
}

const faultControllers = new WeakMap();
export function renderDashboardV2ProcessingFaults(map, faults = []) {
  if (!map) return 0;
  let controller = faultControllers.get(map);
  if (!controller) {
    controller = createFaultOverlayController(setSourceDataIfChanged);
    faultControllers.set(map, controller);
  }
  return controller.render(map, faults);
}

function initializeGraticuleControl(map) {
  const button = document.getElementById('dashboard-v2-map-graticule');
  const status = document.getElementById('dashboard-v2-graticule-status');
  if (!button) return;

  let visible = false;
  listenForMap(map, button, 'click', () => {
    if (!map.getLayer?.(GRATICULE_LAYER_ID)) return;
    visible = !visible;
    map.setLayoutProperty(GRATICULE_LAYER_ID, 'visibility', visible ? 'visible' : 'none');
    const label = visible ? '隐藏经纬网' : '显示经纬网';
    button.title = label;
    button.setAttribute('aria-label', label);
    button.setAttribute('aria-pressed', String(visible));
    if (status) {
      status.textContent = `经纬度 ${visible ? '开启' : '关闭'}`;
    }
  });
}

function initializeBaseNetworkControl(map) {
  const button = document.getElementById('dashboard-v2-map-base-network');
  const status = document.getElementById('dashboard-v2-base-network-status');
  if (!button) return;
  let visible = true;

  const applyVisibility = () => {
    const visibility = visible ? 'visible' : 'none';
    BASE_NETWORK_LAYER_IDS.forEach((layerId) => {
      if (map.getLayer?.(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', visibility);
      }
    });
    const state = visible ? '开启' : '关闭';
    button.title = `基础网络 ${state}`;
    button.setAttribute('aria-label', `基础网络 ${state}，点击切换`);
    button.setAttribute('aria-pressed', String(visible));
    if (status) status.textContent = `基础网络 ${state}`;
    faultControllers.get(map)?.invalidate();
  };

  listenForMap(map, button, 'click', () => {
    visible = !visible;
    applyVisibility();
  });
}

function applyGlobeVisualRulesToStyle(styleConfig) {
  if (!styleConfig || !Array.isArray(styleConfig.layers)) return styleConfig;

  const placeNameExpression = [
    'coalesce',
    ['get', 'name:zh'],
    ['get', 'name'],
  ];

  let administrativePointSource = null;
  let firstSymbolIndex = styleConfig.layers.length;

  styleConfig.layers.forEach((layer, index) => {
    if (!layer) return;

    const layerIdentity = `${layer.id || ''} ${layer['source-layer'] || ''}`.toLowerCase();
    const isWaterLayer = /water|ocean|lake|river/.test(layerIdentity);
    const isBoundaryLayer = /boundary|admin/.test(layerIdentity);
    const isRoadLayer = /road|transport|highway|motorway|trunk|street/.test(layerIdentity);
    const isAdministrativePointLayer = /place|settlement|admin/.test(layerIdentity);
    layer.paint = layer.paint || {};

    if (layer.type === 'background') {
      layer.paint['background-color'] = GLOBE_PALETTE.space;
    } else if (['fill', 'fill-extrusion', 'raster', 'hillshade', 'heatmap'].includes(layer.type)) {
      layer.layout = { ...(layer.layout || {}), visibility: 'none' };
    } else if (layer.type === 'line') {
      if (isBoundaryLayer) {
        layer.paint['line-color'] = GLOBE_PALETTE.boundary;
        layer.paint['line-opacity'] = 0.78;
      } else if (isRoadLayer && !isWaterLayer) {
        layer.paint['line-color'] = GLOBE_PALETTE.road;
      } else {
        layer.layout = { ...(layer.layout || {}), visibility: 'none' };
      }
    } else if (layer.type === 'circle') {
      if (!isAdministrativePointLayer) {
        layer.layout = { ...(layer.layout || {}), visibility: 'none' };
      } else {
        layer.filter = layer.filter
          ? ['all', layer.filter, NON_CAPITAL_POINT_FILTER]
          : NON_CAPITAL_POINT_FILTER;
      }
    }

    if (layer.type !== 'symbol' || !layer.layout?.['text-field']) return;

    firstSymbolIndex = Math.min(firstSymbolIndex, index);
    if (!isAdministrativePointLayer) {
      layer.layout.visibility = 'none';
      return;
    }
    if (!administrativePointSource && layer.source && layer['source-layer']) {
      administrativePointSource = {
        source: layer.source,
        sourceLayer: layer['source-layer'],
      };
    }

    layer.layout['text-field'] = [
      'step',
      ['zoom'],
      '',
      SMALL_SCALE_LABEL_MIN_ZOOM,
      [
        'case',
        ['in', ['coalesce', placeNameExpression, ''], ['literal', HIDDEN_PLACE_LABEL_NAMES]],
        '',
        placeNameExpression,
      ],
    ];
    layer.layout['text-font'] = [SITE_LABEL_FONT];
    layer.paint['text-color'] = GLOBE_PALETTE.label;
    layer.paint['text-halo-color'] = GLOBE_PALETTE.labelHalo;
  });

  if (administrativePointSource) {
    styleConfig.layers.splice(firstSymbolIndex, 0, {
      id: 'dashboard-v2-administrative-points',
      type: 'circle',
      source: administrativePointSource.source,
      'source-layer': administrativePointSource.sourceLayer,
      filter: NON_CAPITAL_POINT_FILTER,
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 0, 1.2, 6, 2.8],
        'circle-color': '#2c7ab8',
        'circle-opacity': 0.82,
      },
    });
  }

  return styleConfig;
}

async function loadRemoteGlobeStyle(config) {
  const styleUrl = resolveUrl(
    config.remoteStyleUrl || '/map-assets/alidade_smooth_dark_local.json'
  );
  const response = await fetch(styleUrl, { credentials: 'same-origin' });
  if (!response.ok) {
    throw new Error(`加载底图样式失败: HTTP ${response.status}`);
  }

  const styleConfig = await response.json();
  styleConfig.projection = { type: 'globe' };
  styleConfig.sky = GLOBE_SKY_CONFIG;
  delete styleConfig.terrain;
  styleConfig.sprite = resolveUrl(styleConfig.sprite);
  styleConfig.glyphs = resolveUrl(styleConfig.glyphs || config.localGlyphsUrl);

  if (styleConfig.sources) {
    const sourceEntries = Object.entries(styleConfig.sources);
    for (const [, sourceConfig] of sourceEntries) {
      if (!sourceConfig || typeof sourceConfig !== 'object') continue;

      if (typeof sourceConfig.url === 'string') {
        const sourceUrl = resolveUrl(sourceConfig.url);

        if (sourceUrl.toLowerCase().endsWith('.json') || sourceUrl.includes('.json?')) {
          try {
            const tileJsonResponse = await fetch(sourceUrl, { credentials: 'same-origin' });
            if (tileJsonResponse.ok) {
              const tileJson = await tileJsonResponse.json();
              const resolvedSource = {
                ...tileJson,
                type: tileJson.type || sourceConfig.type || 'vector',
              };
              if (Array.isArray(tileJson.tiles)) {
                resolvedSource.tiles = tileJson.tiles.map((t) => resolveUrl(t));
              }
              if (Array.isArray(tileJson.urls)) {
                resolvedSource.urls = tileJson.urls.map((u) => resolveUrl(u));
              }
              Object.assign(sourceConfig, resolvedSource);
              delete sourceConfig.url;
            }
          } catch (e) {
            console.warn('[Dashboard V2] 无法解析 TileJSON 来源:', sourceUrl, e);
          }
        } else {
          sourceConfig.url = sourceUrl;
        }
      }
    }
  }

  applyGlobeVisualRulesToStyle(styleConfig);
  return styleConfig;
}

function buildLocalGlobeStyle(config) {
  const localTilesUrl = config.localTilesUrl || '/maps/china.pmtiles';
  const isDark = true;
  return {
    version: 8,
    projection: { type: 'globe' },
    sources: {
      china_local: {
        type: 'vector',
        url: `pmtiles://${resolveUrl(localTilesUrl)}`,
        attribution: '© OpenStreetMap',
      },
    },
    sky: GLOBE_SKY_CONFIG,
    layers: [{
      id: 'background',
      type: 'background',
      paint: {
        'background-color': isDark ? GLOBE_PALETTE.space : '#cbd2d3',
      },
    }, {
      id: 'landuse_base',
      type: 'fill',
      source: 'china_local',
      'source-layer': 'landuse',
      layout: { visibility: 'none' },
      paint: { 'fill-color': isDark ? GLOBE_PALETTE.land : '#f5f5f0' },
    }, {
      id: 'landuse_green',
      type: 'fill',
      source: 'china_local',
      'source-layer': 'landuse',
      filter: ['in', 'class', 'park', 'grass', 'wood', 'scrub'],
      layout: { visibility: 'none' },
      paint: {
        'fill-color': isDark ? GLOBE_PALETTE.landAccent : '#dbece0',
        'fill-opacity': isDark ? 0.3 : 0.6,
      },
    }, {
      id: 'water',
      type: 'fill',
      source: 'china_local',
      'source-layer': 'water',
      layout: { visibility: 'none' },
      paint: { 'fill-color': isDark ? GLOBE_PALETTE.water : '#cbd2d3' },
    }, {
      id: 'roads_casing',
      type: 'line',
      source: 'china_local',
      'source-layer': 'transportation',
      minzoom: 5,
      paint: {
        'line-color': isDark ? GLOBE_PALETTE.road : '#cfcfcf',
        'line-width': { stops: [[5, 1], [10, 4], [15, 8]] },
      },
    }, {
      id: 'roads_inner',
      type: 'line',
      source: 'china_local',
      'source-layer': 'transportation',
      minzoom: 5,
      paint: {
        'line-color': isDark ? '#1b304b' : '#ffffff',
        'line-width': { stops: [[5, 0.5], [10, 2.5], [15, 6]] },
      },
    }, {
      id: 'boundary',
      type: 'line',
      source: 'china_local',
      'source-layer': 'boundary',
      paint: {
        'line-color': isDark ? GLOBE_PALETTE.boundary : '#aeb0b5',
        'line-opacity': isDark ? 0.78 : 1,
        'line-width': 1,
        'line-dasharray': [2, 2],
      },
    }, {
      id: 'administrative_points',
      type: 'circle',
      source: 'china_local',
      'source-layer': 'place',
      filter: NON_CAPITAL_POINT_FILTER,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 0, 1.2, 6, 2.8],
      'circle-color': '#2c7ab8',
      'circle-opacity': 0.82,
    },
    }],
  };
}

function buildProtomapsGlobeStyle(config) {
  const tilesUrl = config.protomapsTilesUrl || '/maps/protomaps-z0-z6.pmtiles';

  return {
    version: 8,
    name: 'Dashboard V2 Protomaps z0-z6',
    projection: { type: 'globe' },
    sources: {
      protomaps_z0_z6: {
        type: 'vector',
        url: `pmtiles://${resolveUrl(tilesUrl)}`,
        attribution: '© OpenStreetMap contributors · Protomaps',
      },
    },
    sky: GLOBE_SKY_CONFIG,
    layers: [{
      id: 'protomaps-space',
      type: 'background',
      paint: {
        'background-color': GLOBE_PALETTE.space,
      },
    }, {
      id: 'protomaps-earth',
      type: 'fill',
      source: 'protomaps_z0_z6',
      'source-layer': 'earth',
      paint: {
        'fill-color': GLOBE_PALETTE.land,
        'fill-opacity': 1,
      },
    }, {
      id: 'protomaps-boundaries-glow',
      type: 'line',
      source: 'protomaps_z0_z6',
      'source-layer': 'boundaries',
      paint: {
        'line-color': '#172f4f',
        'line-opacity': 0.88,
        'line-width': ['interpolate', ['linear'], ['zoom'], 0, 1.5, 6, 3.2],
        'line-blur': 1.4,
      },
    }, {
      id: 'protomaps-boundaries',
      type: 'line',
      source: 'protomaps_z0_z6',
      'source-layer': 'boundaries',
      paint: {
        'line-color': GLOBE_PALETTE.boundary,
        'line-opacity': ['interpolate', ['linear'], ['zoom'], 0, 0.62, 6, 0.9],
        'line-width': ['interpolate', ['linear'], ['zoom'], 0, 0.35, 6, 1.05],
      },
    }, {
      id: 'protomaps-roads-glow',
      type: 'line',
      source: 'protomaps_z0_z6',
      'source-layer': 'roads',
      minzoom: 3,
      paint: {
        'line-color': '#102f51',
        'line-opacity': ['interpolate', ['linear'], ['zoom'], 3, 0.28, 6, 0.7],
        'line-width': ['interpolate', ['linear'], ['zoom'], 3, 1.2, 6, 3],
        'line-blur': 1,
      },
    }, {
      id: 'protomaps-roads',
      type: 'line',
      source: 'protomaps_z0_z6',
      'source-layer': 'roads',
      minzoom: 3,
      paint: {
        'line-color': GLOBE_PALETTE.road,
        'line-opacity': ['interpolate', ['linear'], ['zoom'], 3, 0.52, 6, 0.9],
        'line-width': ['interpolate', ['linear'], ['zoom'], 3, 0.3, 6, 1.25],
      },
    }],
  };
}

export async function initializeDashboardV2Map(config = {}) {
  hasRuntimeMapError = false;

  if (typeof maplibregl === 'undefined') {
    hasRuntimeMapError = true;
    setMapStatus('地球模式加载失败：MapLibre 未加载', 'error');
    return null;
  }

  setMapStatus('地球初始化中...', '');

  try {
    const initialBearing = FIXED_MAP_BEARING;
    const initialCamera = {
      center: Array.isArray(config.mapCenter) ? [...config.mapCenter] : [103.0, 34.3],
      zoom: Number(config.mapZoom ?? 4),
      pitch: 0,
      bearing: initialBearing,
    };
    let style;
    registerPmtilesProtocol();
    if (config.basemapMode === 'protomaps') {
      style = buildProtomapsGlobeStyle(config);
    } else if (config.useLocalBasemap) {
      style = buildLocalGlobeStyle(config);
    } else {
      style = await loadRemoteGlobeStyle(config);
    }
    addGraticuleToStyle(style);
    addChinaProvinceBoundariesToStyle(style, config);
    addBaseNetworkPathsToStyle(style, config);
    style.glyphs = resolveUrl(
      config.localGlyphsUrl || '/maps/fonts/{fontstack}/{range}.pbf'
    );
    addSitesToStyle(style);
    addProcessingFaultsToStyle(style);

    const map = new maplibregl.Map({
      container: 'dashboard-v2-map',
      style,
      center: initialCamera.center,
      zoom: initialCamera.zoom,
      pitch: initialCamera.pitch,
      minPitch: 0,
      maxPitch: 0,
      pitchWithRotate: false,
      touchPitch: false,
      bearing: initialBearing,
      transformCameraUpdate: () => ({
        pitch: 0,
        bearing: initialBearing,
      }),
      dragRotate: false,
      attributionControl: false,
      antialias: true,
    });
    dashboardMap = map;
    lockMapRotation(map);
    enableRightButtonZoom(map);
    initializeHomeControl(map, initialCamera);
    initializeGraticuleControl(map);
    initializeBaseNetworkControl(map);

    map.on('load', () => {
      if (hasRuntimeMapError) return;
      setMapStatus('地球模式就绪', 'ready');
    });

    map.on('error', (event) => {
      hasRuntimeMapError = true;
      const rawReason = event?.error?.message || (typeof event?.error === 'string' ? event.error : '');
      let reason = rawReason;
      if (/404|Bad response code: 404/i.test(rawReason)) {
        reason = `底图瓦片资源不存在(404)，请检查地图服务配置 [${rawReason}]`;
      }
      const message = reason
        ? `地球模式加载失败：${reason}`
        : '地球模式加载失败';
      console.error('[Dashboard V2] 地球模式加载失败:', event?.error || event);
      setMapStatus(message, 'error');
    });
    return map;
  } catch (error) {
    hasRuntimeMapError = true;
    const reason = error instanceof Error ? error.message : '未知错误';
    setMapStatus(`地球模式加载失败：${reason}`, 'error');
    return null;
  }
}

export function getDashboardV2Map() {
  return dashboardMap;
}

export function destroyDashboardV2Map(map = dashboardMap) {
  for (const dispose of mapDomDisposers.get(map) || []) dispose();
  mapDomDisposers.delete(map);
  faultControllers.get(map)?.destroy();
  faultControllers.delete(map);
  map?.remove?.();
  if (dashboardMap === map) dashboardMap = null;
}

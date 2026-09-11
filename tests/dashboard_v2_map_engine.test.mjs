import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';


const MODULE_PATH = new URL(
  '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/map_engine.js',
  import.meta.url,
);
const MODULE_SOURCE = await readFile(MODULE_PATH, 'utf8');


async function loadMapModule(tag) {
  const layout = new URL('../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/fault_overlays.js', import.meta.url).href;
  const status = new URL('../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/status.js', import.meta.url).href;
  const encoded = Buffer.from(MODULE_SOURCE.replace('./fault_overlays.js?v=20260911-peripheral-v2', layout + '?test=' + tag)
    .replace('./status.js?v=20260911-status-v1', status)).toString('base64');
  return import(`data:text/javascript;base64,${encoded}#${tag}`);
}


function installDom() {
  const elements = new Map();
  for (const id of [
    'dashboard-v2-map-status',
    'dashboard-v2-status-dot',
    'dashboard-v2-status-text',
    'dashboard-v2-graticule-status',
    'dashboard-v2-base-network-status',
  ]) {
    elements.set(id, {
      className: '',
      textContent: '',
      classList: {
        toggle(name, enabled) {
          elements.get(id).toggledClass = enabled ? name : '';
        },
      },
    });
  }
  elements.set('dashboard-v2-map-home', {
    listeners: {},
    addEventListener(name, callback) {
      this.listeners[name] = callback;
    },
  });
  elements.set('dashboard-v2-map-graticule', {
    listeners: {},
    title: '显示经纬网',
    attributes: {},
    addEventListener(name, callback) {
      this.listeners[name] = callback;
    },
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
  });
  elements.set('dashboard-v2-map-base-network', {
    listeners: {},
    title: '基础网络 开启',
    attributes: {},
    addEventListener(name, callback) {
      this.listeners[name] = callback;
    },
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
  });
  globalThis.document = {
    getElementById(id) {
      return elements.get(id) || null;
    },
    createElement(tagName) {
      const node = {
        tagName: String(tagName).toUpperCase(),
        className: '',
        textContent: '',
        hidden: false,
        children: [],
        dataset: {},
        attributes: {},
        style: {},
        appendChild(child) {
          this.children.push(child);
          return child;
        },
        setAttribute(name, value) {
          this.attributes[name] = String(value);
        },
      };
      node.classList = {
        toggle(name, enabled) {
          const names = new Set(node.className.split(/\s+/).filter(Boolean));
          if (enabled) names.add(name);
          else names.delete(name);
          node.className = [...names].join(' ');
        },
      };
      return node;
    },
  };
  globalThis.window = { location: { origin: 'https://netbox.example.test' } };
  return elements;
}


function installMapLibre({ throwOnConstruct = false } = {}) {
  const state = { maps: [], protocolCalls: [], markers: [] };
  class FakeMarker {
    constructor(options) {
      this.options = options;
      this.element = options.element;
      this.removed = false;
      state.markers.push(this);
    }

    setLngLat(coordinates) {
      this.coordinates = coordinates;
      return this;
    }

    addTo(map) {
      this.map = map;
      return this;
    }

    getElement() {
      return this.element;
    }

    remove() {
      this.removed = true;
    }
  }
  class FakeMap {
    constructor(options) {
      if (throwOnConstruct) throw new Error('constructor failed');
      this.options = options;
      this.handlers = {};
      this.disabled = [];
      this.disabledRotations = [];
      this.zoomValues = [];
      this.easeValues = [];
      this.layoutValues = [];
      this.canvas = {
        listeners: {},
        addEventListener(name, callback) {
          this.listeners[name] = callback;
        },
        setPointerCapture() {},
        releasePointerCapture() {},
      };
      for (const name of [
        'dragRotate',
        'touchZoomRotate',
        'scrollZoom',
        'boxZoom',
        'doubleClickZoom',
        'dragPan',
      ]) {
        this[name] = { disable: () => this.disabled.push(name) };
      }
      this.touchZoomRotate.disableRotation = () => this.disabledRotations.push('touch');
      this.keyboard = { disableRotation: () => this.disabledRotations.push('keyboard') };
      state.maps.push(this);
    }

    on(name, callback) {
      this.handlers[name] = callback;
    }

    off(name, callback) {
      if (this.handlers[name] === callback) delete this.handlers[name];
    }

    project() {
      return { x: 900, y: 350 };
    }

    getContainer() {
      return { clientWidth: 1000, clientHeight: 700 };
    }

    getCanvas() {
      return this.canvas;
    }

    getZoom() {
      return this.zoomValues.at(-1) ?? this.options.zoom;
    }

    getMinZoom() {
      return 0;
    }

    getMaxZoom() {
      return 24;
    }

    setZoom(value) {
      this.zoomValues.push(value);
    }

    easeTo(camera) {
      this.easeValues.push(camera);
    }

    getLayer(id) {
      return this.options.style.layers.find((layer) => layer.id === id);
    }

    setLayoutProperty(id, property, value) {
      this.layoutValues.push([id, property, value]);
      const layer = this.getLayer(id);
      if (layer) layer.layout = { ...(layer.layout || {}), [property]: value };
    }
  }
  globalThis.maplibregl = {
    Map: FakeMap,
    Marker: FakeMarker,
    addProtocol(name, handler) {
      state.protocolCalls.push([name, handler]);
    },
  };
  return state;
}


function installPmtiles() {
  globalThis.pmtiles = {
    Protocol: class {
      constructor() {
        this.tile = () => {};
      }
    },
  };
}


test('initializes a globe with remote dark style by default (aligning with unified map)', async () => {
  const elements = installDom();
  const state = installMapLibre();
  installPmtiles();
  let requestedUrls = [];
  globalThis.fetch = async (url) => {
    requestedUrls.push(url);
    if (url.includes('alidade_smooth_dark_local.json')) {
      return {
        ok: true,
        json: async () => ({
          version: 8,
          sprite: '/map-assets/sprites/sprite',
          glyphs: '/map-assets/fonts/{fontstack}/{range}.pbf',
          terrain: { source: 'terrain-dem', exaggeration: 1 },
          sources: {
            openmaptiles: {
              type: 'vector',
              url: '/map-assets/tiles.json',
            },
            'terrain-dem': {
              type: 'raster-dem',
              tiles: ['/map-assets/terrain/{z}/{x}/{y}.png'],
            },
          },
          layers: [
            {
              id: 'background',
              type: 'background',
              paint: { 'background-color': '#000000' },
            },
            {
              id: 'landcover',
              type: 'fill',
              source: 'openmaptiles',
              'source-layer': 'landcover',
              paint: { 'fill-color': '#000000' },
            },
            {
              id: 'water',
              type: 'fill',
              source: 'openmaptiles',
              'source-layer': 'water',
              paint: { 'fill-color': '#000000' },
            },
            {
              id: 'boundary',
              type: 'line',
              source: 'openmaptiles',
              'source-layer': 'boundary',
              paint: { 'line-color': '#000000' },
            },
            {
              id: 'place_label',
              type: 'symbol',
              source: 'openmaptiles',
              'source-layer': 'place',
              minzoom: 1,
              layout: { 'text-field': ['get', 'name'] },
            },
          ],
        }),
      };
    }
    if (url.includes('tiles.json')) {
      return {
        ok: true,
        json: async () => ({
          tiles: ['/map-assets/tiles/{z}/{x}/{y}.pbf'],
        }),
      };
    }
    return { ok: false, status: 404 };
  };

  const { initializeDashboardV2Map } = await loadMapModule('globe-remote-default');
  const map = await initializeDashboardV2Map();

  assert.ok(map);
  assert.equal(state.maps.length, 1);
  assert.deepEqual(map.options.center, [103.0, 34.3]);
  assert.equal(map.options.zoom, 4);
  assert.equal(map.options.bearing, 0);
  assert.equal(map.options.dragRotate, false);
  assert.deepEqual(map.disabledRotations, ['touch', 'keyboard']);
  assert.deepEqual(map.options.style.projection, { type: 'globe' });
  assert.ok(map.options.style.sky);
  assert.equal(map.options.style.sky['sky-color'], 'rgba(2, 7, 19, 0)');
  assert.equal(map.options.style.terrain, undefined);
  assert.equal(
    map.options.style.sources['dashboard-v2-otn-paths'].url,
    'pmtiles://https://netbox.example.test/maps/otn_paths.pmtiles',
  );
  assert.equal(
    map.options.style.sources['dashboard-v2-china-provinces'].url,
    'pmtiles://https://netbox.example.test/maps/china_provinces.pmtiles',
  );
  assert.equal(
    map.options.style.sprite,
    'https://netbox.example.test/map-assets/sprites/sprite',
  );
  assert.equal(
    map.options.style.sources.openmaptiles.tiles[0],
    'https://netbox.example.test/map-assets/tiles/{z}/{x}/{y}.pbf',
  );
  assert.equal(map.options.style.layers[0].paint['background-color'], '#020814');
  assert.equal(map.options.style.layers[1].layout.visibility, 'none');
  assert.equal(map.options.style.layers[2].layout.visibility, 'none');
  assert.equal(
    map.options.style.layers.find((layer) => layer.id === 'boundary').paint['line-color'],
    '#53657a',
  );
  const administrativePoints = map.options.style.layers.find(
    (layer) => layer.id === 'dashboard-v2-administrative-points',
  );
  assert.ok(administrativePoints);
  assert.match(JSON.stringify(administrativePoints.filter), /capital/);
  assert.match(JSON.stringify(administrativePoints.filter), /\"2\",\"4\",\"yes\",\"true\"/);
  const placeLabel = map.options.style.layers.find((layer) => layer.id === 'place_label');
  assert.equal(placeLabel.minzoom, 1);
  assert.deepEqual(placeLabel.layout['text-field'].slice(0, 4), ['step', ['zoom'], '', 5.5]);
  assert.deepEqual(placeLabel.layout['text-font'], ['HarmonyOS Sans SC Regular']);

  map.handlers.load();
  assert.equal(elements.get('dashboard-v2-status-text').textContent, '数据加载中...');
  assert.equal(elements.get('dashboard-v2-map-status').className, 'is-ready');
});


test('initializes a globe with local PMTiles basemap when useLocalBasemap is true', async () => {
  const elements = installDom();
  const state = installMapLibre();
  installPmtiles();

  const { initializeDashboardV2Map } = await loadMapModule('globe-local-pmtiles');
  const map = await initializeDashboardV2Map({ useLocalBasemap: true });

  assert.ok(map);
  assert.equal(state.maps.length, 1);
  assert.deepEqual(map.options.center, [103.0, 34.3]);
  assert.equal(
    map.options.style.sources.china_local.url,
    'pmtiles://https://netbox.example.test/maps/china.pmtiles',
  );
  assert.equal(state.protocolCalls.length, 1);
  assert.equal(state.protocolCalls[0][0], 'pmtiles');
  assert.equal(map.options.style.layers[0].paint['background-color'], '#020814');
  assert.equal(map.options.style.layers[1].layout.visibility, 'none');
  assert.equal(map.options.style.layers[2].layout.visibility, 'none');
  assert.equal(map.options.style.layers[3].layout.visibility, 'none');
  const boundary = map.options.style.layers.find((layer) => layer.id === 'boundary');
  const administrativePoints = map.options.style.layers.find(
    (layer) => layer.id === 'administrative_points',
  );
  assert.equal(boundary.paint['line-color'], '#53657a');
  assert.match(JSON.stringify(administrativePoints.filter), /capital/);
  assert.equal(map.options.style.layers.some((layer) => (
    layer.source === 'china_local' && layer.type === 'symbol'
  )), false);

  map.handlers.load();
  assert.equal(elements.get('dashboard-v2-status-text').textContent, '数据加载中...');
});


test('initializes the Protomaps globe with HarmonyOS Sans site labels', async () => {
  const elements = installDom();
  const state = installMapLibre();
  installPmtiles();

  const { initializeDashboardV2Map } = await loadMapModule('globe-protomaps-z0-z6');
  const map = await initializeDashboardV2Map({
    basemapMode: 'protomaps',
    protomapsTilesUrl: '/maps/protomaps-z0-z6.pmtiles',
  });

  assert.ok(map);
  assert.equal(state.protocolCalls.length, 1);
  assert.equal(state.protocolCalls[0][0], 'pmtiles');
  assert.equal(
    map.options.style.sources.protomaps_z0_z6.url,
    'pmtiles://https://netbox.example.test/maps/protomaps-z0-z6.pmtiles',
  );
  assert.deepEqual(map.options.style.projection, { type: 'globe' });
  assert.ok(map.options.style.sky);
  assert.deepEqual(
    map.options.style.layers.map((layer) => layer.id),
    [
      'protomaps-space',
      'protomaps-earth',
      'dashboard-v2-graticule',
      'protomaps-boundaries-glow',
      'protomaps-boundaries',
      'dashboard-v2-china-provinces-glow',
      'dashboard-v2-china-provinces-main',
      'protomaps-roads-glow',
      'protomaps-roads',
      'dashboard-v2-otn-paths-glow',
      'dashboard-v2-otn-paths-main',
      'dashboard-v2-sites-glow',
      'dashboard-v2-sites-core',
      'dashboard-v2-sites-label',
      'dashboard-v2-processing-faults-glow',
      'dashboard-v2-processing-faults-ring',
      'dashboard-v2-processing-faults-core',
      'dashboard-v2-processing-faults-label',
    ],
  );
  assert.equal(map.options.style.layers[1]['source-layer'], 'earth');
  assert.equal(map.options.style.layers[3]['source-layer'], 'boundaries');
  assert.equal(map.options.style.layers[5]['source-layer'], 'china_provinces');
  assert.equal(map.options.style.layers[7]['source-layer'], 'roads');
  assert.equal(map.options.style.layers.some((layer) => (
    layer.source === 'protomaps_z0_z6' && layer.type === 'symbol'
  )), false);
  assert.equal(map.options.style.layers.some((layer) => (
    layer.source === 'protomaps_z0_z6' && layer.type === 'circle'
  )), false);
  assert.equal(
    map.options.style.layers.some((layer) => layer['source-layer'] === 'water'),
    false,
  );
  assert.equal(
    map.options.style.sources['dashboard-v2-otn-paths'].url,
    'pmtiles://https://netbox.example.test/maps/otn_paths.pmtiles',
  );
  const provinceLayers = map.options.style.layers.filter(
    (layer) => layer.source === 'dashboard-v2-china-provinces',
  );
  assert.equal(provinceLayers.length, 2);
  assert.equal(provinceLayers.every((layer) => layer.type === 'line'), true);
  assert.equal(provinceLayers.every((layer) => layer['source-layer'] === 'china_provinces'), true);
  const basePathLayers = map.options.style.layers.filter(
    (layer) => layer.source === 'dashboard-v2-otn-paths',
  );
  assert.equal(basePathLayers.length, 2);
  assert.equal(basePathLayers.every((layer) => layer['source-layer'] === 'otn_paths'), true);
  assert.equal(
    map.options.style.glyphs,
    'https://netbox.example.test/maps/fonts/{fontstack}/{range}.pbf',
  );
  const siteGlow = map.options.style.layers.find(
    (layer) => layer.id === 'dashboard-v2-sites-glow',
  );
  const siteCore = map.options.style.layers.find(
    (layer) => layer.id === 'dashboard-v2-sites-core',
  );
  assert.deepEqual(siteGlow.paint['circle-radius'].slice(-2), [6, 5.5]);
  assert.deepEqual(siteCore.paint['circle-radius'].slice(-2), [6, 2.1]);
  const siteLabel = map.options.style.layers.find(
    (layer) => layer.id === 'dashboard-v2-sites-label',
  );
  assert.equal(siteLabel.minzoom, 6);
  assert.deepEqual(siteLabel.layout['text-font'], ['HarmonyOS Sans SC Regular']);
  assert.deepEqual(siteLabel.layout['text-field'], ['get', 'name']);
  assert.equal(siteLabel.layout['text-allow-overlap'], false);
  assert.equal(siteLabel.layout['text-ignore-placement'], false);
  assert.equal(siteLabel.layout['text-padding'], 2);
  const faultLabel = map.options.style.layers.find(
    (layer) => layer.id === 'dashboard-v2-processing-faults-label',
  );
  assert.deepEqual(faultLabel.layout['text-font'], ['HarmonyOS Sans SC Regular']);
  assert.deepEqual(faultLabel.layout['text-field'], ['get', 'index_label']);
  assert.equal(faultLabel.layout['text-allow-overlap'], true);
  assert.equal(
    map.options.style.layers.some(
      (layer) => layer.id === 'dashboard-v2-processing-faults-index',
    ),
    false,
  );
  for (const layerId of [
    'dashboard-v2-processing-faults-glow',
    'dashboard-v2-processing-faults-ring',
    'dashboard-v2-processing-faults-core',
  ]) {
    const radius = map.options.style.layers.find((layer) => layer.id === layerId).paint['circle-radius'];
    assert.equal(radius[0], 'interpolate');
    assert.deepEqual(radius[2], ['zoom']);
  }
  const faultGlow = map.options.style.layers.find(
    (layer) => layer.id === 'dashboard-v2-processing-faults-glow',
  );
  const faultRing = map.options.style.layers.find(
    (layer) => layer.id === 'dashboard-v2-processing-faults-ring',
  );
  const faultCore = map.options.style.layers.find(
    (layer) => layer.id === 'dashboard-v2-processing-faults-core',
  );
  assert.deepEqual(faultGlow.paint['circle-radius'].slice(-2), [7, ['case', ['boolean', ['feature-state', 'active'], false], 13, 10]]);
  assert.deepEqual(faultGlow.paint['circle-color'], ['coalesce', ['get', 'color'], '#ff334f']);
  assert.equal(faultRing.paint['circle-color'], '#210912');
  assert.equal(faultCore.paint['circle-color'], '#3a0b17');
  assert.deepEqual(faultLabel.layout['text-size'].slice(-2), [7, 13]);
  assert.equal(faultLabel.paint['text-color'], '#f4f9ff');

  map.handlers.load();
  assert.equal(elements.get('dashboard-v2-status-text').textContent, '数据加载中...');
});


test('preserves camera position and constrains pitch and bearing before camera updates', async () => {
  installDom();
  const state = installMapLibre();
  installPmtiles();
  const { initializeDashboardV2Map } = await loadMapModule('globe-camera');

  await initializeDashboardV2Map({
    useLocalBasemap: true,
    mapCenter: [110, 25],
    mapZoom: 1.2,
    mapPitch: 15,
    mapBearing: -8,
  });

  assert.deepEqual(state.maps[0].options.center, [110, 25]);
  assert.equal(state.maps[0].options.zoom, 1.2);
  assert.equal(state.maps[0].options.pitch, 0);
  assert.equal(state.maps[0].options.minPitch, 0);
  assert.equal(state.maps[0].options.maxPitch, 0);
  assert.equal(state.maps[0].options.pitchWithRotate, false);
  assert.equal(state.maps[0].options.touchPitch, false);
  assert.equal(state.maps[0].options.bearing, 0);
  assert.deepEqual(state.maps[0].disabled, []);
  assert.deepEqual(
    state.maps[0].options.transformCameraUpdate({ pitch: 35, bearing: 0 }),
    { pitch: 0, bearing: 0 },
  );
});


test('uses vertical right-button dragging for zoom without rotating the globe', async () => {
  installDom();
  installMapLibre();
  installPmtiles();
  const { initializeDashboardV2Map } = await loadMapModule('right-button-zoom');
  const map = await initializeDashboardV2Map({ useLocalBasemap: true, mapZoom: 3 });
  const prevented = [];

  map.canvas.listeners.contextmenu({ preventDefault: () => prevented.push('menu') });
  map.canvas.listeners.pointerdown({
    button: 2,
    pointerId: 7,
    clientY: 300,
    preventDefault: () => prevented.push('down'),
  });
  map.canvas.listeners.pointermove({
    pointerId: 7,
    clientY: 180,
    preventDefault: () => prevented.push('move'),
  });
  map.canvas.listeners.pointerup({ pointerId: 7 });

  assert.deepEqual(prevented, ['menu', 'down', 'move']);
  assert.equal(map.zoomValues.at(-1), 4);
  assert.equal(map.options.bearing, 0);
});


test('home control restores every initial camera parameter', async () => {
  const elements = installDom();
  installMapLibre();
  installPmtiles();
  const { initializeDashboardV2Map } = await loadMapModule('home-control');
  const map = await initializeDashboardV2Map({
    useLocalBasemap: true,
    mapCenter: [103, 34.3],
    mapZoom: 1.8,
    mapBearing: -5,
  });

  elements.get('dashboard-v2-map-home').listeners.click();

  assert.deepEqual(map.easeValues, [{
    center: [103, 34.3],
    zoom: 1.8,
    pitch: 0,
    bearing: 0,
    duration: 800,
    essential: true,
  }]);
});


test('graticule control toggles 24 longitude lines and 17 latitude lines', async () => {
  const elements = installDom();
  installMapLibre();
  installPmtiles();
  const { initializeDashboardV2Map } = await loadMapModule('graticule-control');
  const map = await initializeDashboardV2Map({
    basemapMode: 'protomaps',
    protomapsTilesUrl: '/maps/protomaps-z0-z6.pmtiles',
  });
  const button = elements.get('dashboard-v2-map-graticule');
  const source = map.options.style.sources['dashboard-v2-graticule-source'];
  const layer = map.getLayer('dashboard-v2-graticule');

  assert.equal(source.type, 'geojson');
  assert.equal(source.data.type, 'FeatureCollection');
  const longitudeLines = source.data.features.filter(
    (feature) => feature.properties.kind === 'longitude',
  );
  const latitudeLines = source.data.features.filter(
    (feature) => feature.properties.kind === 'latitude',
  );
  assert.equal(longitudeLines.length, 24);
  assert.equal(latitudeLines.length, 17);
  assert.deepEqual(
    latitudeLines.map((feature) => feature.properties.value),
    [-80, -70, -60, -50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80],
  );
  assert.ok(latitudeLines.every((feature) => feature.geometry.type === 'MultiLineString'));
  assert.ok(latitudeLines.every((feature) => feature.geometry.coordinates.length === 8));
  assert.ok(latitudeLines.every((feature) => feature.geometry.coordinates.every(
    (segment) => segment.length === 46,
  )));
  assert.equal(layer.layout.visibility, 'visible');
  assert.deepEqual(new Set(source.data.features.map((feature) => feature.properties.kind)), new Set([
    'longitude', 'latitude',
  ]));

  button.listeners.click();
  assert.deepEqual(map.layoutValues.at(-1), [
    'dashboard-v2-graticule', 'visibility', 'none',
  ]);
  assert.equal(button.attributes['aria-pressed'], 'false');
  assert.equal(button.title, '显示经纬网');
  assert.equal(elements.get('dashboard-v2-graticule-status').textContent, '经纬度 关闭');

  button.listeners.click();
  assert.deepEqual(map.layoutValues.at(-1), [
    'dashboard-v2-graticule', 'visibility', 'visible',
  ]);
  assert.equal(button.attributes['aria-pressed'], 'true');
  assert.equal(elements.get('dashboard-v2-graticule-status').textContent, '经纬度 开启');
});


test('renders valid NetBox sites into the V2 globe site source', async () => {
  installDom();
  installMapLibre();
  const updates = [];
  const { renderDashboardV2Sites } = await loadMapModule('site-rendering');
  const map = {
    getSource(id) {
      if (id !== 'dashboard-v2-sites') return null;
      return { setData: (data) => updates.push(data) };
    },
  };

  const count = renderDashboardV2Sites(map, [
    { id: 1, name: '北京站', lng: 116.4, lat: 39.9 },
    { id: 2, name: '无坐标站', lng: null, lat: 31.2 },
    { id: 3, name: '越界站', lng: 181, lat: 30 },
  ]);

  assert.equal(count, 1);
  assert.deepEqual(updates[0].features[0], {
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [116.4, 39.9] },
    properties: { id: '1', name: '北京站' },
  });
});


test('renders numbered processing faults without card-selected feature state', async () => {
  installDom();
  const maplibreState = installMapLibre();
  const updates = [];
  const { renderDashboardV2ProcessingFaults } = await loadMapModule('processing-fault-rendering');
  const map = {
    getSource(id) {
      if (id !== 'dashboard-v2-processing-faults') return null;
      return { setData: (data) => updates.push(data) };
    },
  };

  const count = renderDashboardV2ProcessingFaults(map, [
    { id: 9, fault_number: 'F009', severity: 'critical', lng: 116.4, lat: 39.9 },
    { id: 10, fault_number: 'F010', severity: 'major', lng: 121.47, lat: 31.23 },
    { id: 11, fault_number: '无坐标', severity: 'minor', lng: null, lat: 30 },
  ]);

  assert.equal(count, 2);
  assert.deepEqual(updates[0].features.map((feature) => feature.properties.index_label), ['①', '②']);
  assert.deepEqual(updates[0].features[0], {
    type: 'Feature',
    id: '9',
    geometry: { type: 'Point', coordinates: [116.4, 39.9] },
    properties: { fault_number: 'F009', index_label: '①', severity: 'critical', color: '#ff334f' },
  });
  assert.equal(maplibreState.markers.length, 2);
  const pointOnly = { id: 9, fault_number: 'F009', lng: 116.4, lat: 39.9, mapDisplayMode: 'points' };
  renderDashboardV2ProcessingFaults(map, [pointOnly]);
  assert.equal(updates.at(-1).features.length, 1);
  assert.equal(maplibreState.markers.length, 2); // No new DOM callout.
  renderDashboardV2ProcessingFaults(map, [{ ...pointOnly, mapDisplayMode: 'hidden' }]);
  assert.equal(updates.at(-1).features.length, 0);
});


test('cutovers use a distinct arrow and status color in the shared map source', async () => {
  installDom();
  const state = installMapLibre();
  const updates = [];
  const { renderDashboardV2ProcessingFaults } = await loadMapModule('cutover-render');
  const map = { getSource: () => ({ setData: (value) => updates.push(value) }) };
  renderDashboardV2ProcessingFaults(map, [{ id: 'cutover-1', kind: 'cutover', lng: 116, lat: 39,
    status_color: 'green', category_display: '光缆割接 · 已完成', fault_number: 'C1', category_color: 'green' }]);
  assert.equal(updates[0].features[0].properties.index_label, '⇄');
  assert.equal(updates[0].features[0].properties.color, '#198754');
  assert.equal(state.markers.length, 1);
  const callout = state.markers[0].element.children.find((node) => node.className === 'dashboard-v2-fault-callout');
  assert.equal(callout.children[0].children[0].textContent, '⇄\n割\n接');
  assert.equal(callout.children[0].children[1].textContent, '光缆割接 · 已完成');
  assert.equal(callout.children[0].children[2].textContent, 'C1');
});

test('shows every fault callout together from zoom 3.9 without carousel selection', async () => {
  installDom();
  const maplibreState = installMapLibre();
  const handlers = {};
  const updates = [];
  let zoom = 3.8;
  const { renderDashboardV2ProcessingFaults } = await loadMapModule('processing-fault-callout');
  const map = {
    getSource: () => ({ setData: (data) => updates.push(data) }),
    getZoom: () => zoom,
    on(name, callback) {
      handlers[name] = callback;
    },
    off(name, callback) {
      if (handlers[name] === callback) delete handlers[name];
    },
    project: () => ({ x: 900, y: 350 }),
    getContainer: () => ({ clientWidth: 1000, clientHeight: 700 }),
  };
  const fault = {
    id: 9,
    fault_number: 'F009',
    category_display: '光缆故障',
    province: '北京市',
    site_a: '北京站',
    sites_z: ['济南站', '青岛站'],
    lng: 116.4,
    lat: 39.9,
  };

  renderDashboardV2ProcessingFaults(map, [fault, {
    ...fault,
    id: 10,
    fault_number: 'F010',
    site_a: '',
    sites_z: [],
    lng: 121.47,
    lat: 31.23,
  }, { ...fault, id: 11, lng: null, lat: null }]);

  assert.equal(updates.length, 1);
  assert.equal(maplibreState.markers.length, 2);
  const marker = maplibreState.markers[0];
  assert.deepEqual(marker.coordinates, [116.4, 39.9]);
  assert.equal(marker.options.opacityWhenCovered, 0);
  assert.equal(marker.element.hidden, true);
  assert.equal(maplibreState.markers[1].element.hidden, true);

  zoom = 3.9;
  handlers.zoom();
  assert.equal(marker.element.hidden, false);
  assert.equal(maplibreState.markers[1].element.hidden, false);
  assert.ok(['w', 'e', 'n', 's', 'ne', 'nw', 'se', 'sw'].includes(marker.element.dataset.placement));
  const collectText = (node) => [
    node.textContent,
    ...(node.children || []).flatMap((child) => collectText(child)),
  ].filter(Boolean);
  const renderedText = collectText(marker.element);
  assert.ok(renderedText.includes('①'));
  const radar = marker.element.children.find(
    (child) => child.className === 'dashboard-v2-fault-focus-radar',
  );
  const core = radar.children.find(
    (child) => child.className === 'dashboard-v2-fault-focus-core',
  );
  assert.equal(core.textContent, '①');
  assert.equal(
    radar.children.some(
      (child) => child.className === 'dashboard-v2-fault-focus-index',
    ),
    false,
  );
  assert.ok(renderedText.includes('北京站'));
  assert.ok(renderedText.includes('北京站-济南站等2站 OTN'));
  assert.ok(renderedText.includes('光缆故障'));
  assert.ok(renderedText.includes('F009'));
  assert.ok(renderedText.includes('⚠\n故\n障'));
  assert.ok(!renderedText.includes('!'));
  assert.ok(renderedText.includes('影响业务 0 项'));

  assert.ok(collectText(maplibreState.markers[1].element).includes('北京市 OTN'));

  zoom = 3.89;
  handlers.zoom();
  assert.equal(marker.element.hidden, true);
});


test('lays out clustered fault callouts inside the viewport without overlap or UI obstruction', async () => {
  const elements = installDom();
  elements.set('dashboard-v2-info-drawer', {
    hidden: false,
    getBoundingClientRect: () => ({
      left: 0, top: 0, right: 300, bottom: 230, width: 300, height: 230,
    }),
  });
  const maplibreState = installMapLibre();
  const { renderDashboardV2ProcessingFaults } = await loadMapModule('processing-fault-collision-layout');
  const projectedPoints = new Map([
    [1, { x: 325, y: 150 }],
    [2, { x: 520, y: 270 }],
    [3, { x: 545, y: 285 }],
    [4, { x: 570, y: 300 }],
    [5, { x: 595, y: 315 }],
  ]);
  const container = {
    clientWidth: 1200,
    clientHeight: 800,
    getBoundingClientRect: () => ({
      left: 0, top: 0, right: 1200, bottom: 800, width: 1200, height: 800,
    }),
  };
  const map = {
    getSource: () => ({ setData() {} }),
    getZoom: () => 4,
    getCenter: () => ({ lng: 110, lat: 32 }),
    getContainer: () => container,
    project: ([longitude]) => projectedPoints.get(longitude),
    on() {},
    off() {},
  };
  const faults = [...projectedPoints.keys()].map((id) => ({
    id,
    fault_number: `F00${id}`,
    category_display: '光缆故障',
    site_a: `站点${id}`,
    sites_z: [`对端${id}`],
    lng: id,
    lat: 30,
  }));

  renderDashboardV2ProcessingFaults(map, faults);

  assert.equal(maplibreState.markers.length, 5);
  const calloutRects = maplibreState.markers.map((marker) => {
    const point = projectedPoints.get(marker.coordinates[0]);
    const left = point.x + Number.parseFloat(marker.element.style['--fault-callout-x']);
    const top = point.y + Number.parseFloat(marker.element.style['--fault-callout-y']);
    return { left, top, right: left + 220, bottom: top + 88 };
  });
  for (const rect of calloutRects) {
    assert.ok(rect.left >= 12);
    assert.ok(rect.top >= 12);
    assert.ok(rect.right <= 1188);
    assert.ok(rect.bottom <= 788);
    assert.equal(
      Math.max(0, Math.min(rect.right, 300) - Math.max(rect.left, 0))
        * Math.max(0, Math.min(rect.bottom, 230) - Math.max(rect.top, 0)),
      0,
    );
  }
  for (let first = 0; first < calloutRects.length; first += 1) {
    for (let second = first + 1; second < calloutRects.length; second += 1) {
      const overlapWidth = Math.max(
        0,
        Math.min(calloutRects[first].right, calloutRects[second].right)
          - Math.max(calloutRects[first].left, calloutRects[second].left),
      );
      const overlapHeight = Math.max(
        0,
        Math.min(calloutRects[first].bottom, calloutRects[second].bottom)
          - Math.max(calloutRects[first].top, calloutRects[second].top),
      );
      assert.equal(overlapWidth * overlapHeight, 0);
    }
  }
});


test('prefers the seaward side when inland candidates cover sites and OTN paths', async () => {
  installDom();
  const maplibreState = installMapLibre();
  const queryBounds = [];
  const handlers = {};
  const { renderDashboardV2ProcessingFaults } = await loadMapModule('processing-fault-network-aware-layout');
  const container = {
    clientWidth: 1400,
    clientHeight: 800,
    getBoundingClientRect: () => ({
      left: 0, top: 0, right: 1400, bottom: 800, width: 1400, height: 800,
    }),
  };
  const map = {
    getSource: () => ({ setData() {} }),
    getLayer: () => ({}),
    getZoom: () => 4,
    getCenter: () => ({ lng: 110, lat: 32 }),
    getContainer: () => container,
    project: () => ({ x: 900, y: 360 }),
    queryRenderedFeatures(bounds) {
      queryBounds.push(bounds);
      if (bounds[0][0] >= 900) return [];
      return [{
        id: 'site-1',
        layer: { id: 'dashboard-v2-sites-core' },
        properties: { id: 'site-1' },
      }, {
        id: 'path-1',
        layer: { id: 'dashboard-v2-otn-paths-main' },
        properties: {},
      }];
    },
    on(name, callback) {
      handlers[name] = callback;
    },
    off(name, callback) {
      if (handlers[name] === callback) delete handlers[name];
    },
  };

  renderDashboardV2ProcessingFaults(map, [{
    id: 21,
    fault_number: 'F021',
    category_display: '设备故障',
    site_a: '上海浦东站',
    sites_z: ['苏州园区站'],
    lng: 121.47,
    lat: 31.23,
  }]);

  assert.equal(maplibreState.markers.length, 1);
  assert.ok(['e', 'ne', 'se'].includes(maplibreState.markers[0].element.dataset.placement));
  assert.ok(Number.parseFloat(maplibreState.markers[0].element.style['--fault-callout-x']) > 0);
  assert.ok(queryBounds.length > 1);
  assert.ok(queryBounds.length <= 8);
  const initialQueryCount = queryBounds.length;
  const lockedStyle = { ...maplibreState.markers[0].element.style };
  map.__dashboardOverviewLayoutLocked = true;
  handlers.moveend();
  assert.equal(queryBounds.length, initialQueryCount);
  assert.deepEqual(maplibreState.markers[0].element.style, lockedStyle);
  delete map.__dashboardOverviewLayoutLocked;
  handlers.move();
  assert.ok(queryBounds.length > initialQueryCount, 'deferred layout resumes after unlocking');
  const resumedQueryCount = queryBounds.length;
  handlers.move();
  assert.equal(queryBounds.length, resumedQueryCount);
  handlers.moveend();
  assert.ok(queryBounds.length > initialQueryCount);
});


test('removes obsolete markers but retains observers when processing data refreshes', async () => {
  installDom();
  const maplibreState = installMapLibre();
  const resizeObservers = [];
  globalThis.ResizeObserver = class {
    constructor(callback) {
      this.callback = callback;
      this.disconnected = false;
      resizeObservers.push(this);
    }

    observe() {}

    disconnect() {
      this.disconnected = true;
    }
  };
  const updates = [];
  const handlers = {};
  const { renderDashboardV2ProcessingFaults } = await loadMapModule('processing-fault-refresh');
  const map = {
    getZoom: () => 4,
    getSource: () => ({ setData: (data) => updates.push(data) }),
    on(name, callback) {
      handlers[name] = callback;
    },
    off(name, callback) {
      if (handlers[name] === callback) delete handlers[name];
    },
  };

  renderDashboardV2ProcessingFaults(map, [
    { id: 9, fault_number: 'F009', severity: 'critical', lng: 116.4, lat: 39.9 },
  ]);
  const firstMarker = maplibreState.markers[0];
  renderDashboardV2ProcessingFaults(map, [
    { id: 10, fault_number: 'F010', severity: 'major', lng: 121.47, lat: 31.23 },
  ]);

  assert.equal(updates.length, 2);
  assert.equal(firstMarker.removed, true);
  assert.equal(maplibreState.markers.length, 2);
  assert.equal(maplibreState.markers[1].removed, false);
  assert.ok(handlers.zoom);
  assert.equal(resizeObservers.length, 1);
  assert.equal(resizeObservers[0].disconnected, false);
  delete globalThis.ResizeObserver;
});


test('base network control toggles path and site layers together', async () => {
  const elements = installDom();
  installMapLibre();
  installPmtiles();
  const { initializeDashboardV2Map } = await loadMapModule('base-network-control');
  const map = await initializeDashboardV2Map({ basemapMode: 'protomaps' });
  const button = elements.get('dashboard-v2-map-base-network');
  const layerIds = [
    'dashboard-v2-otn-paths-glow',
    'dashboard-v2-otn-paths-main',
    'dashboard-v2-sites-glow',
    'dashboard-v2-sites-core',
    'dashboard-v2-sites-label',
  ];

  button.listeners.click();
  assert.deepEqual(map.layoutValues.slice(-layerIds.length), layerIds.map(
    (layerId) => [layerId, 'visibility', 'none'],
  ));
  assert.equal(button.attributes['aria-pressed'], 'false');
  assert.equal(button.title, '基础网络 关闭');
  assert.equal(elements.get('dashboard-v2-base-network-status').textContent, '基础网络 关闭');

  button.listeners.click();
  assert.deepEqual(map.layoutValues.slice(-layerIds.length), layerIds.map(
    (layerId) => [layerId, 'visibility', 'visible'],
  ));
  assert.equal(button.attributes['aria-pressed'], 'true');
  assert.equal(elements.get('dashboard-v2-base-network-status').textContent, '基础网络 开启');
});


test('runtime errors remain visible after a later load event', async () => {
  const elements = installDom();
  installMapLibre();
  installPmtiles();
  const { initializeDashboardV2Map } = await loadMapModule('globe-runtime-error');
  const map = await initializeDashboardV2Map({ useLocalBasemap: true });

  map.handlers.error({ error: new Error('Bad response code: 404') });
  map.handlers.load();

  assert.equal(
    elements.get('dashboard-v2-status-text').textContent,
    '地球模式加载失败：底图瓦片资源不存在(404)，请检查地图服务配置 [Bad response code: 404]',
  );
  assert.equal(elements.get('dashboard-v2-map-status').className, 'is-error');
});


test('reports missing MapLibre and constructor failures', async () => {
  let elements = installDom();
  delete globalThis.maplibregl;
  let module = await loadMapModule('globe-maplibre-missing');

  assert.equal(await module.initializeDashboardV2Map(), null);
  assert.match(elements.get('dashboard-v2-status-text').textContent, /MapLibre 未加载/);

  elements = installDom();
  installMapLibre({ throwOnConstruct: true });
  installPmtiles();
  module = await loadMapModule('globe-constructor-error');

  assert.equal(await module.initializeDashboardV2Map({ useLocalBasemap: true }), null);
  assert.match(elements.get('dashboard-v2-status-text').textContent, /constructor failed/);
});


test('reports a missing PMTiles runtime when useLocalBasemap is requested', async () => {
  const elements = installDom();
  const state = installMapLibre();
  delete globalThis.pmtiles;
  const module = await loadMapModule('globe-pmtiles-missing');

  assert.equal(await module.initializeDashboardV2Map({ useLocalBasemap: true }), null);
  assert.equal(state.maps.length, 0);
  assert.match(elements.get('dashboard-v2-status-text').textContent, /PMTiles 库未加载/);
});

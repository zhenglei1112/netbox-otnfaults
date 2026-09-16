const EMPTY = () => ({ type: 'FeatureCollection', features: [] });
export const RISK_STYLES = {
  rain: { label: '强降雨风险', unit: 'mm/小时', color: '#55c9ff' },
  wind: { label: '大风风险', unit: 'm/s', color: '#63e6c1' },
  heat: { label: '高温风险', unit: '℃', color: '#ff9659' },
  cold: { label: '低温风险', unit: '℃', color: '#bcadff' },
};
const INTENSITIES = {
  'Tropical Depression': ['热带低压', '#80c9ff'], 'Tropical Storm': ['热带风暴', '#54d69a'],
  'Severe Tropical Storm': ['强热带风暴', '#f2dd56'], Typhoon: ['台风', '#ffa350'],
  'Severe Typhoon': ['强台风', '#fa6c85'], 'Super Typhoon': ['超强台风', '#d686ff'],
};
const WX = 'v2-weather', TC = 'v2-typhoon';
const LAYERS = ['weather-glow', 'weather-icons', 'typhoon-past', 'typhoon-forecast', 'typhoon-points', 'typhoon-center'];
const dateText = (value) => Number.isFinite(Date.parse(value)) ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '未提供';

export function weatherDetails(properties) {
  if (properties.source === 'MET Norway') {
    let risks = properties.risks;
    if (typeof risks === 'string') { try { risks = JSON.parse(risks); } catch { risks = []; } }
    return [properties.name, '未来24小时模型预测风险（非官方预警）', ...(risks || []).map((risk) => {
      const style = RISK_STYLES[risk.kind];
      return `${style?.label || risk.kind}：${risk.value} ${style?.unit || ''} · ${dateText(risk.time)}`;
    }), `模型更新：${dateText(properties.updated_at)}`, '来源：MET Norway'].join('\n');
  }
  return [properties.name, properties.kind === 'forecast' ? '预测位置' : '实况位置',
    dateText(properties.time), INTENSITIES[properties.intensity]?.[0] || properties.intensity || '强度未提供',
    `最大持续风速：${properties.wind || '未提供'}`, `发布：${dateText(properties.issued)}`, '来源：香港天文台'].join('\n');
}

// Display primitives are painted locally; no third-party icons or font dependencies.
function sprite(kinds) {
  const canvas = document.createElement('canvas');
  canvas.width = 48 * kinds.length; canvas.height = 48;
  const ctx = canvas.getContext('2d');
  kinds.forEach((kind, index) => {
    ctx.save(); ctx.translate(index * 48 + 24, 24);
    ctx.fillStyle = '#102839'; ctx.strokeStyle = RISK_STYLES[kind]?.color || '#82daff';
    ctx.lineWidth = 2.6; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.beginPath(); ctx.arc(0, 0, 20, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath();
    if (kind === 'rain') {
      ctx.moveTo(0, -12); ctx.bezierCurveTo(-18, 5, -5, 16, 3, 10); ctx.bezierCurveTo(12, 5, 5, -4, 0, -12);
    } else if (kind === 'wind') {
      ctx.moveTo(-12, -5); ctx.lineTo(5, -5); ctx.bezierCurveTo(14, -5, 12, -15, 5, -10);
      ctx.moveTo(-12, 2); ctx.lineTo(11, 2); ctx.moveTo(-8, 8); ctx.lineTo(1, 8); ctx.bezierCurveTo(10, 8, 8, 16, 3, 13);
    } else if (kind === 'heat' || kind === 'cold') {
      ctx.moveTo(-4, 4); ctx.lineTo(-4, -11); ctx.quadraticCurveTo(0, -16, 4, -11); ctx.lineTo(4, 4);
      ctx.arc(0, 8, 6, -.75, Math.PI + .75); ctx.moveTo(0, -6); ctx.lineTo(0, 8);
      ctx.moveTo(9, -6); ctx.lineTo(15, -6);
      if (kind === 'heat') { ctx.moveTo(12, -9); ctx.lineTo(12, -3); }
    } else {
      for (let t = 0; t < Math.PI * 5; t += .08) {
        const radius = t * .8;
        ctx.lineTo(Math.cos(t) * radius, Math.sin(t) * radius);
      }
    }
    ctx.stroke(); ctx.restore();
  });
  return ctx.getImageData(0, 0, canvas.width, canvas.height);
}

export function createMockWeather(now = new Date()) {
  const stamp = now.toISOString();
  const point = (coordinates, properties) => ({ type: 'Feature', geometry: { type: 'Point', coordinates }, properties });
  const weather = [[116.4, 39.9, 'rain'], [121.47, 31.23, 'wind'], [113.26, 23.13, 'heat'], [126.63, 45.75, 'cold'], [114.3, 30.6, 'rain-wind']]
    .map(([lng, lat, icon], index) => point([lng, lat], { source: 'MET Norway', name: `模拟风险站点${index + 1}`, site_id: `mock-${index}`,
      icon, updated_at: stamp, risks: icon.split('-').map((kind) => ({ kind, value: { rain: 18, wind: 15, heat: 38, cold: -5 }[kind], time: stamp })) }));
  const common = { source: 'HKO', name: '模拟台风（非真实）', cyclone_id: 'mock', issued: stamp, intensity: 'Typhoon', wind: '130km/h' };
  const typhoon = [point([125, 20], { ...common, kind: 'center', time: stamp }),
    point([123, 22], { ...common, kind: 'forecast', time: new Date(+now + 86400000).toISOString() })];
  for (const [kind, coordinates] of [['past', [[129, 17], [127, 18], [125, 20]]], ['forecast', [[125, 20], [123, 22], [121, 25]]]]) {
    typhoon.push({ type: 'Feature', geometry: { type: 'LineString', coordinates }, properties: { ...common, kind } });
  }
  return { weather: { ...EMPTY(), features: weather }, typhoon: { ...EMPTY(), features: typhoon },
    sources: { weather: { state: 'ready' }, typhoon: { state: 'ready' } } };
}

export function unexpiredWeather(data, now = Date.now()) {
  if (!data) return null;
  let changed = false;
  const weather = data.weather.features.flatMap((item) => {
    const updated = Date.parse(item.properties.updated_at);
    const risks = item.properties.risks?.filter((risk) => Date.parse(risk.time) + 3600000 > now) || [];
    if (!Number.isFinite(updated) || now - updated > 86400000 || !risks.length) { changed = true; return []; }
    if (risks.length === item.properties.risks.length) return [item];
    changed = true;
    return [{ ...item, properties: { ...item.properties, risks, icon: risks.map((risk) => risk.kind).join('-') } }];
  });
  const typhoon = data.typhoon.features.filter((item) => {
    const issued = Date.parse(item.properties.issued);
    return Number.isFinite(issued) && now - issued <= 86400000;
  });
  return { ...data, weather: changed ? { ...data.weather, features: weather } : data.weather,
    typhoon: typhoon.length === data.typhoon.features.length ? data.typhoon : { ...data.typhoon, features: typhoon } };
}

export function initializeWeatherLayers(map, { url, onStatus = () => {} } = {}) {
  if (!map) return { setSimulation() {}, destroy() {} };
  let latest = null, mock = null, disposed = false, request = null, interval = null;
  let signatures = {}, lastHover = '', rotation = 0;
  let requestFailed = false;
  const visible = { weather: true, typhoon: true };
  const cleanup = [];
  const images = [];
  const popup = new globalThis.maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: '320px', className: 'dashboard-v2-weather-popup' });
  const on = (event, handler) => { map.on(event, handler); cleanup.push(() => map.off(event, handler)); };
  const closePopup = () => { popup.remove(); lastHover = ''; };
  const presentation = () => document.documentElement.classList.contains('is-presentation');
  function status() {
    for (const kind of Object.keys(visible)) {
      const sourceState = mock ? 'ready' : requestFailed ? 'error' : latest?.sources?.[kind]?.state || 'loading';
      const state = !visible[kind] ? 'off' : sourceState === 'ready' ? 'ready' : sourceState === 'loading' ? 'loading' : 'error';
      const button = document.getElementById(`dashboard-v2-${kind}-toggle`);
      button?.setAttribute('data-weather-state', state);
      const label = kind === 'weather' ? '天气风险' : '台风';
      const text = `${label} ${state === 'off' ? '关闭' : state === 'loading' ? '开启 · 加载中' : state === 'error' ? '开启 · 数据异常或过期' : mock ? '开启 · 模拟数据' : '开启 · 数据正常'}`;
      button?.setAttribute('aria-label', text);
      const output = document.getElementById(`dashboard-v2-${kind}-status`);
      if (output) output.textContent = text;
    }
    if (mock) { onStatus(''); return; }
    if (!Object.values(visible).some(Boolean)) { onStatus(''); return; }
    if (requestFailed) { onStatus('气象数据更新失败'); return; }
    if (!latest) { onStatus('气象数据加载中'); return; }
    const states = Object.entries(visible).filter(([, enabled]) => enabled).map(([kind]) => latest.sources?.[kind]?.state || 'loading');
    onStatus(states.some((state) => state === 'error' || state === 'stale') ? '气象数据更新失败／缓存可能过期'
      : states.includes('loading') ? '气象数据加载中' : '');
  }
  function apply() {
    status();
    if (!map.getSource(WX)) return;
    const data = mock || unexpiredWeather(latest);
    for (const [kind, source] of [['weather', WX], ['typhoon', TC]]) {
      const geojson = data?.[kind] || EMPTY();
      const signature = JSON.stringify(geojson);
      if (signature !== signatures[kind]) { map.getSource(source).setData(geojson); signatures[kind] = signature; }
    }
    for (const id of LAYERS) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', visible[id.startsWith('weather') ? 'weather' : 'typhoon'] ? 'visible' : 'none');
  }
  function scale() {
    if (!map.getLayer('weather-icons')) return;
    const size = map.__dashboardPresentationScale || 1;
    map.setLayoutProperty('weather-icons', 'icon-size', size);
    map.setLayoutProperty('typhoon-center', 'icon-size', size * 1.4);
    map.setPaintProperty('weather-glow', 'circle-radius', 18 * size);
    map.setPaintProperty('typhoon-points', 'circle-radius', 4 * size);
    map.setPaintProperty('typhoon-past', 'line-width', 2 * size);
    map.setPaintProperty('typhoon-forecast', 'line-width', 2 * size);
    if (presentation()) closePopup();
  }
  function install() {
    if (disposed || map.getSource(WX)) return;
    const riskKinds = Object.keys(RISK_STYLES);
    for (let mask = 1; mask < 16; mask++) {
      const kinds = riskKinds.filter((_, i) => mask & (1 << i));
      const id = `wx-${kinds.join('-')}`; map.addImage(id, sprite(kinds), { pixelRatio: 2 }); images.push(id);
    }
    map.addImage('wx-spiral', sprite(['spiral']), { pixelRatio: 2 }); images.push('wx-spiral');
    map.addSource(WX, { type: 'geojson', data: EMPTY(), cluster: false,
      attribution: 'Weather: <a href="https://api.met.no/" target="_blank" rel="noopener">MET Norway</a> · CC BY 4.0' });
    map.addSource(TC, { type: 'geojson', data: EMPTY(), attribution: 'Typhoon: <a href="https://data.gov.hk/en-data/dataset/hk-hko-rss-tc-track-info" target="_blank" rel="noopener">Hong Kong Observatory / DATA.GOV.HK</a>' });
    const point = ['==', '$type', 'Point'];
    map.addLayer({ id: 'weather-glow', type: 'circle', source: WX, paint: { 'circle-color': '#79cfff', 'circle-radius': 18, 'circle-blur': .8, 'circle-opacity': .25 } });
    map.addLayer({ id: 'weather-icons', type: 'symbol', source: WX, layout: { 'icon-image': ['concat', 'wx-', ['get', 'icon']], 'icon-offset': [16, -14], 'icon-allow-overlap': false } });
    for (const kind of ['past', 'forecast']) map.addLayer({ id: `typhoon-${kind}`, type: 'line', source: TC,
      filter: ['all', ['==', '$type', 'LineString'], ['==', 'kind', kind]], paint: { 'line-color': '#75d8f5', 'line-width': 2, ...(kind === 'forecast' ? { 'line-dasharray': [3, 3], 'line-opacity': .8 } : {}) } });
    map.addLayer({ id: 'typhoon-points', type: 'circle', source: TC, filter: point, paint: {
      'circle-radius': 4, 'circle-stroke-width': 1, 'circle-stroke-color': '#fff',
      'circle-color': ['match', ['get', 'intensity'], ...Object.entries(INTENSITIES).flatMap(([name, [, color]]) => [name, color]), '#b7c8d1'] } });
    map.addLayer({ id: 'typhoon-center', type: 'symbol', source: TC, filter: ['all', point, ['==', 'kind', 'center']],
      layout: { 'icon-image': 'wx-spiral', 'icon-allow-overlap': true, 'icon-size': 1.4 } });
    signatures = {}; apply(); scale();
  }
  for (const kind of Object.keys(visible)) {
    const button = document.getElementById(`dashboard-v2-${kind}-toggle`);
    const label = kind === 'weather' ? '天气风险' : '台风';
    try { visible[kind] = localStorage.getItem(`dashboard-v2-${kind}`) !== 'off'; } catch { /* Session default. */ }
    const update = () => {
      button?.setAttribute('aria-pressed', String(visible[kind]));
      button?.setAttribute('aria-label', `${label} ${visible[kind] ? '开启' : '关闭'}`);
      const output = document.getElementById(`dashboard-v2-${kind}-status`);
      if (output) output.textContent = `${label} ${visible[kind] ? '开启' : '关闭'}`;
      status();
    };
    const click = () => { visible[kind] = !visible[kind]; update(); closePopup(); apply(); try { localStorage.setItem(`dashboard-v2-${kind}`, visible[kind] ? 'on' : 'off'); } catch { /* Session only. */ } };
    button?.addEventListener('click', click); cleanup.push(() => button?.removeEventListener('click', click)); update();
  }
  on('mousemove', (event) => {
    if (presentation()) { closePopup(); return; }
    const layers = ['weather-icons', 'typhoon-center', 'typhoon-points'].filter((id) => map.getLayer(id));
    if (!layers.length) return;
    const hit = map.queryRenderedFeatures(event.point, { layers })[0];
    if (!hit) { closePopup(); return; }
    const content = weatherDetails(hit.properties);
    if (content !== lastHover) {
      const node = document.createElement('div'); node.textContent = `${mock ? '模拟数据\n' : ''}${content}`;
      popup.setDOMContent(node); lastHover = content;
    }
    popup.setLngLat(event.lngLat).addTo(map);
  });
  on('movestart', closePopup); on('resize', scale);
  const canvas = map.getCanvas(); canvas.addEventListener('mouseleave', closePopup); cleanup.push(() => canvas.removeEventListener('mouseleave', closePopup));
  const attribution = new globalThis.maplibregl.AttributionControl({ compact: true });
  map.addControl(attribution, 'bottom-right'); cleanup.push(() => map.removeControl(attribution));
  if (map.isStyleLoaded()) install(); else on('load', install);
  async function refresh() {
    if (disposed || request) return;
    if (!url) { requestFailed = true; status(); onStatus('气象接口未配置'); return; }
    request = new AbortController();
    const timeout = setTimeout(() => request?.abort(), 15000);
    try {
      const response = await fetch(url, { credentials: 'same-origin', signal: request.signal, cache: 'no-store' });
      if (response.status === 401 || response.status === 403) {
        latest = null; apply();
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data.weather?.features) || !Array.isArray(data.typhoon?.features) || !data.sources) throw new Error('Invalid weather data');
      if (!disposed) { requestFailed = false; latest = data; apply(); }
    } catch {
      if (!disposed) { requestFailed = true; apply(); }
    } finally { clearTimeout(timeout); request = null; }
  }
  refresh(); interval = setInterval(refresh, 30000);
  const animation = setInterval(() => {
    if (disposed || document.hidden || !visible.typhoon || matchMedia('(prefers-reduced-motion: reduce)').matches || !(mock || latest)?.typhoon?.features.some((f) => f.properties.kind === 'center')) return;
    if (map.getLayer('typhoon-center')) { rotation = (rotation + 2) % 360; map.setLayoutProperty('typhoon-center', 'icon-rotate', rotation); }
  }, 150);
  return {
    setSimulation(enabled) { mock = enabled ? createMockWeather() : null; closePopup(); apply(); },
    destroy() {
      disposed = true; request?.abort(); clearInterval(interval); clearInterval(animation); closePopup(); cleanup.reverse().forEach((fn) => fn());
      LAYERS.slice().reverse().forEach((id) => { if (map.getLayer(id)) map.removeLayer(id); });
      [WX, TC].forEach((id) => { if (map.getSource(id)) map.removeSource(id); });
      images.forEach((id) => { if (map.hasImage(id)) map.removeImage(id); });
    },
  };
}

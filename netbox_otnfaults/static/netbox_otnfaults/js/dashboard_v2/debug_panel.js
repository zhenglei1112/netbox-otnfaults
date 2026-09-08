const FIELD_DEFINITIONS = [
  { id: 'dashboard-v2-debug-longitude', key: 'longitude', label: '经度', min: -180, max: 180 },
  { id: 'dashboard-v2-debug-latitude', key: 'latitude', label: '纬度', min: -90, max: 90 },
  { id: 'dashboard-v2-debug-zoom', key: 'zoom', label: '缩放等级', min: 0, max: 24 },
  { id: 'dashboard-v2-debug-pitch', key: 'pitch', label: '倾斜角', min: 0, max: 0, locked: true },
  { id: 'dashboard-v2-debug-bearing', key: 'bearing', label: '方位角', min: -180, max: 180, locked: true },
];

const FPS_SAMPLE_INTERVAL_MS = 500;

function formatFps(value) {
  return Number.isFinite(value) ? String(Math.round(value)) : '--';
}

export function createDashboardV2FpsMonitor(outputs, scheduler = globalThis) {
  const requestFrame = scheduler?.requestAnimationFrame?.bind(scheduler);
  const cancelFrame = scheduler?.cancelAnimationFrame?.bind(scheduler);
  if (!requestFrame || !cancelFrame || !outputs?.current || !outputs?.average || !outputs?.minimum) {
    return null;
  }

  let animationFrameId = null;
  let startedAt = null;
  let lastSampleAt = null;
  let intervalFrames = 0;
  let totalFrames = 0;
  let minimumFps = Number.POSITIVE_INFINITY;

  const reset = () => {
    startedAt = null;
    lastSampleAt = null;
    intervalFrames = 0;
    totalFrames = 0;
    minimumFps = Number.POSITIVE_INFINITY;
    outputs.current.textContent = '--';
    outputs.average.textContent = '--';
    outputs.minimum.textContent = '--';
  };
  const sampleFrame = (timestamp) => {
    if (animationFrameId === null) return;
    if (startedAt === null) {
      startedAt = timestamp;
      lastSampleAt = timestamp;
      animationFrameId = requestFrame(sampleFrame);
      return;
    }
    intervalFrames += 1;
    totalFrames += 1;
    const intervalDuration = timestamp - lastSampleAt;
    if (intervalDuration >= FPS_SAMPLE_INTERVAL_MS) {
      const currentFps = (intervalFrames * 1000) / intervalDuration;
      const averageFps = (totalFrames * 1000) / Math.max(timestamp - startedAt, 1);
      minimumFps = Math.min(minimumFps, currentFps);
      outputs.current.textContent = formatFps(currentFps);
      outputs.average.textContent = formatFps(averageFps);
      outputs.minimum.textContent = formatFps(minimumFps);
      intervalFrames = 0;
      lastSampleAt = timestamp;
    }
    animationFrameId = requestFrame(sampleFrame);
  };

  return {
    start() {
      if (animationFrameId !== null) return;
      reset();
      animationFrameId = requestFrame(sampleFrame);
    },
    stop() {
      if (animationFrameId === null) return;
      cancelFrame(animationFrameId);
      animationFrameId = null;
    },
    get running() {
      return animationFrameId !== null;
    },
  };
}

export function isDashboardV2DebugEnabled(search = '') {
  const value = new URLSearchParams(search).get('debug');
  return ['ture', 'true'].includes(String(value || '').toLowerCase());
}

function formatCameraValue(value) {
  return String(Number(Number(value).toFixed(6)));
}

function initialCamera(config) {
  const center = Array.isArray(config.mapCenter) ? config.mapCenter : [103.0, 34.3];
  return {
    center: [Number(center[0]), Number(center[1])],
    zoom: Number(config.mapZoom ?? 4),
    pitch: 0,
    bearing: 0,
  };
}

function cameraFromMap(map, bearing) {
  const center = map.getCenter();
  return {
    center: [Number(center.lng), Number(center.lat)],
    zoom: Number(map.getZoom()),
    pitch: 0,
    bearing,
  };
}

function enableDebugInteractions(map) {
  ['dragPan', 'scrollZoom', 'doubleClickZoom', 'touchZoomRotate'].forEach((name) => {
    map[name]?.enable?.();
  });
  map.touchZoomRotate?.disableRotation?.();
  map.keyboard?.disableRotation?.();
}

export function initializeDashboardV2DebugPanel(map, config = {}) {
  const panel = document.getElementById('dashboard-v2-debug-panel');
  if (!panel || !map || !config.debugEnabled) {
    return null;
  }

  const fields = Object.fromEntries(FIELD_DEFINITIONS.map((definition) => [
    definition.key,
    document.getElementById(definition.id),
  ]));
  const toggleButton = document.getElementById('dashboard-v2-debug-toggle');
  const content = document.getElementById('dashboard-v2-debug-content');
  const applyButton = document.getElementById('dashboard-v2-debug-apply');
  const resetButton = document.getElementById('dashboard-v2-debug-reset');
  const simulationToggle = document.getElementById('dashboard-v2-debug-data-simulation');
  const message = document.getElementById('dashboard-v2-debug-message');
  const fpsOutputs = {
    current: document.getElementById('dashboard-v2-debug-fps-current'),
    average: document.getElementById('dashboard-v2-debug-fps-average'),
    minimum: document.getElementById('dashboard-v2-debug-fps-minimum'),
  };
  if (
    Object.values(fields).some((field) => !field)
    || !toggleButton
    || !content
    || !applyButton
    || !resetButton
    || !simulationToggle
    || !message
    || Object.values(fpsOutputs).some((output) => !output)
  ) {
    return null;
  }

  const initial = initialCamera(config);
  const fpsMonitor = createDashboardV2FpsMonitor(fpsOutputs);
  const writeCamera = (camera) => {
    fields.longitude.value = formatCameraValue(camera.center[0]);
    fields.latitude.value = formatCameraValue(camera.center[1]);
    fields.zoom.value = formatCameraValue(camera.zoom);
    fields.pitch.value = formatCameraValue(camera.pitch);
    fields.bearing.value = formatCameraValue(camera.bearing);
  };
  const showMessage = (text, isError = false) => {
    message.textContent = text;
    message.className = `dashboard-v2-debug-message${isError ? ' is-error' : ''}`;
  };
  const readCamera = () => {
    const values = {};
    for (const definition of FIELD_DEFINITIONS) {
      if (definition.locked) {
        values[definition.key] = definition.key === 'bearing' ? initial.bearing : 0;
        continue;
      }
      const rawValue = fields[definition.key].value.trim();
      const value = Number(rawValue);
      if (!rawValue || !Number.isFinite(value) || value < definition.min || value > definition.max) {
        throw new Error(`${definition.label}必须在 ${definition.min} 至 ${definition.max} 之间`);
      }
      values[definition.key] = value;
    }
    return {
      center: [values.longitude, values.latitude],
      zoom: values.zoom,
      pitch: values.pitch,
      bearing: values.bearing,
    };
  };
  const applyCamera = (camera, successMessage) => {
    map.jumpTo(camera);
    writeCamera(cameraFromMap(map, initial.bearing));
    showMessage(successMessage);
  };

  panel.hidden = false;
  content.hidden = false;
  toggleButton.textContent = '收起';
  toggleButton.setAttribute('aria-expanded', 'true');
  writeCamera(cameraFromMap(map, initial.bearing));
  enableDebugInteractions(map);
  fpsMonitor?.start();
  const onMove = () => writeCamera(cameraFromMap(map, initial.bearing));
  map.on('moveend', onMove);
  const onToggle = () => {
    const collapsed = !content.hidden;
    content.hidden = collapsed;
    toggleButton.textContent = collapsed ? '展开' : '收起';
    toggleButton.setAttribute('aria-expanded', String(!collapsed));
    if (collapsed) {
      fpsMonitor?.stop();
    } else {
      fpsMonitor?.start();
    }
  };
  toggleButton.addEventListener('click', onToggle);
  const onApply = () => {
    try {
      applyCamera(readCamera(), '已应用当前视野参数');
    } catch (error) {
      showMessage(error.message, true);
    }
  };
  applyButton.addEventListener('click', onApply);
  const onReset = () => applyCamera(initial, '已重置为初始视野');
  resetButton.addEventListener('click', onReset);
  const applySimulationState = (enabled) => {
    simulationToggle.checked = Boolean(enabled);
    config.onDataSimulationChange?.(enabled);
    showMessage(enabled ? '已开启故障及割接数据模拟' : '已恢复实时数据');
  };
  simulationToggle.checked = false;
  const onSimulation = () => {
    applySimulationState(Boolean(simulationToggle.checked));
  };
  simulationToggle.addEventListener('change', onSimulation);

  const destroy = () => {
    fpsMonitor?.stop();
    map.off?.('moveend', onMove);
    toggleButton.removeEventListener?.('click', onToggle);
    applyButton.removeEventListener?.('click', onApply);
    resetButton.removeEventListener?.('click', onReset);
    simulationToggle.removeEventListener?.('change', onSimulation);
  };

  return {
    apply: () => applyButton.click(),
    reset: () => resetButton.click(),
    setDataSimulation(enabled) {
      applySimulationState(Boolean(enabled));
    },
    destroy,
  };
}

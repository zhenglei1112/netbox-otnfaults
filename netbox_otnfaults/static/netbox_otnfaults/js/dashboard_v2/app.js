import * as maplibreglModule from '../../lib/maplibre-gl-v6.js?v=20260831-mime-v2';
import {
  initializeDashboardV2DebugPanel,
  isDashboardV2DebugEnabled,
} from './debug_panel.js?v=20260902-debug-data-v1';
import {
  createDashboardV2RenderSignature,
  fetchDashboardV2Data,
} from './data_service.js?v=20260904-refresh-diff-v2';
import { installDashboardV2FrameRateLimit } from './frame_rate_limiter.js?v=20260902-fps-limit-v1';
import { initializeDashboardV2InfoDrawer } from './info_drawer.js?v=20260903-fault-callout-v1';
import { createDashboardV2MockFaultData } from './mock_fault_data.js?v=20260903-fault-callout-v1';
import {
  createDashboardMapRefresher,
  startDashboardAutoRefresh,
} from './refresh_controller.js?v=20260903-refresh-diff-v1';
import { initializeDashboardV2DayNightControl } from './day_night_control.js?v=20260901-day-night-control-v1';
import { initializeDashboardV2DayNight } from './day_night_layer.js?v=20260901-day-night-control-v1';
import {
  initializeDashboardV2Map,
  renderDashboardV2ProcessingFaults,
  renderDashboardV2Sites,
} from './map_engine.js?v=20260904-fault-center-index-v1';
import { initializeDashboardV2Galaxy } from './galaxy.js?v=20260902-bearing-zero-v1';
import { initializeDashboardV2SkyControl } from './sky_control.js?v=20260901-sky-mode-v1';
import { initializeDashboardV2Starfield } from './starfield.js?v=20260902-bearing-zero-v1';

globalThis.maplibregl = maplibreglModule;
installDashboardV2FrameRateLimit(60);

function updateClock() {
  const now = new Date();
  const date = document.getElementById('dashboard-v2-date');
  const time = document.getElementById('dashboard-v2-time');

  if (date) {
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    date.textContent = `${year}/${month}/${day} ${weekdays[now.getDay()]}`;
  }

  if (time) {
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    time.textContent = `${hours}:${minutes}:${seconds}`;
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  updateClock();
  setInterval(updateClock, 1000);

  const configNode = document.getElementById('dashboard-v2-config');
  const config = configNode ? JSON.parse(configNode.textContent) : {};
  config.debugEnabled = isDashboardV2DebugEnabled(window.location.search);
  const map = await initializeDashboardV2Map(config);
  const infoDrawer = initializeDashboardV2InfoDrawer();
  const dayNight = initializeDashboardV2DayNight(map);
  initializeDashboardV2DayNightControl(dayNight);
  let hasDashboardData = false;
  let latestDashboardData = null;
  let dataSimulationEnabled = false;
  const renderFaultData = () => {
    if (dataSimulationEnabled) {
      const simulatedData = createDashboardV2MockFaultData(latestDashboardData || {});
      renderDashboardV2ProcessingFaults(map, simulatedData.processing_faults);
      infoDrawer?.render(simulatedData);
    } else if (latestDashboardData) {
      renderDashboardV2ProcessingFaults(map, latestDashboardData.processing_faults);
      infoDrawer?.render(latestDashboardData);
    }
  };
  const refreshDashboardData = createDashboardMapRefresher({
    load: () => fetchDashboardV2Data(config.dataUrl),
    getDataSignature: createDashboardV2RenderSignature,
    onData: (data) => {
      hasDashboardData = true;
      latestDashboardData = data;
      renderDashboardV2Sites(map, data.sites);
      renderFaultData();
    },
    onError: (error) => {
      console.error('[Dashboard V2] 态势数据加载失败:', error);
      if (!dataSimulationEnabled) {
        infoDrawer?.showError({ preserveData: hasDashboardData });
      }
    },
  });
  startDashboardAutoRefresh({
    refresh: refreshDashboardData,
    intervalMs: 30000,
  });
  let galaxy = null;
  let starfield = null;
  try {
    galaxy = await initializeDashboardV2Galaxy(map);
  } catch (error) {
    console.error('[Dashboard V2] 银河加载失败:', error);
  }
  try {
    starfield = await initializeDashboardV2Starfield(map);
  } catch (error) {
    console.error('[Dashboard V2] 恒星加载失败:', error);
  }
  initializeDashboardV2SkyControl(galaxy, starfield);
  initializeDashboardV2DebugPanel(map, {
    ...config,
    onDataSimulationChange(enabled) {
      dataSimulationEnabled = enabled;
      if (enabled) infoDrawer?.setExpanded(true);
      renderFaultData();
    },
  });
});

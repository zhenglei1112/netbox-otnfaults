import * as maplibreglModule from '../../lib/maplibre-gl-v6.js?v=20260907-worker-fix';
import {
  initializeDashboardV2DebugPanel,
  isDashboardV2DebugEnabled,
} from './debug_panel.js?v=20260908-toolbar-icons-v1';
import {
  reconcileDashboardData,
  fetchDashboardV2Data,
} from './data_service.js?v=20260908-toolbar-icons-v1';
import { installDashboardV2FrameRateLimit } from './frame_rate_limiter.js?v=20260908-toolbar-icons-v1';
import { initializeDashboardV2InfoDrawer, renderDashboardV2Cutovers } from './info_drawer.js?v=20260908-toolbar-icons-v1';
import { cutoverMapItems } from './cutovers.js?v=20260908-toolbar-icons-v1';
import { createDashboardV2MockFaultData } from './mock_fault_data.js?v=20260908-toolbar-icons-v1';
import {
  createDashboardMapRefresher,
  startDashboardAutoRefresh,
} from './refresh_controller.js?v=20260908-toolbar-icons-v1';
import { initializeDashboardV2DayNightControl } from './day_night_control.js?v=20260908-toolbar-icons-v1';
import { initializeDashboardV2DayNight } from './day_night_layer.js?v=20260908-toolbar-icons-v1';
import {
  initializeDashboardV2Map,
  destroyDashboardV2Map,
  renderDashboardV2ProcessingFaults,
  renderDashboardV2Sites,
} from './map_engine.js?v=20260908-toolbar-icons-v1';
import { initializeDashboardV2Galaxy } from './galaxy.js?v=20260908-toolbar-icons-v1';
import { initializeDashboardV2SkyControl } from './sky_control.js?v=20260908-toolbar-icons-v1';
import { initializeDashboardV2Starfield } from './starfield.js?v=20260908-toolbar-icons-v1';

globalThis.maplibregl = maplibreglModule;
import { applyDisplayModes, initializeDisplaySettings } from './display_settings.js?v=20260908-toolbar-icons-v1';

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
  const disposers = [];
  let disposed = false;
  const own = (component) => {
    if (component?.destroy) {
      if (disposed) component.destroy();
      else disposers.push(() => component.destroy());
    }
    return component;
  };
  const limiter = installDashboardV2FrameRateLimit(60);
  const destroy = (event) => {
    if (event?.persisted || disposed) return;
    disposed = true;
    window.removeEventListener('pagehide', destroy);
    disposers.reverse().forEach((dispose) => {
      try { dispose(); } catch (error) { console.error('[Dashboard V2] 清理失败:', error); }
    });
    limiter?.restore();
  };
  window.addEventListener('pagehide', destroy);
  updateClock();
  const clockTimer = setInterval(updateClock, 1000);
  disposers.push(() => clearInterval(clockTimer));

  const configNode = document.getElementById('dashboard-v2-config');
  const config = configNode ? JSON.parse(configNode.textContent) : {};
  config.debugEnabled = isDashboardV2DebugEnabled(window.location.search);
  const map = await initializeDashboardV2Map(config);
  own({ destroy: () => destroyDashboardV2Map(map) });
  if (disposed) return;
  const infoDrawer = own(initializeDashboardV2InfoDrawer());
  const dayNight = own(initializeDashboardV2DayNight(map));
  own(initializeDashboardV2DayNightControl(dayNight));
  let hasDashboardData = false;
  let latestDashboardData = null;
  let dataSimulationEnabled = false;
  let simulatedData = null;
  let serverTimeOffset = 0;
  let displayModes = { fault: 'full', cutover: 'full' };
  const renderFaultData = () => {
    const displayData = dataSimulationEnabled ? simulatedData : latestDashboardData;
    const cutovers = cutoverMapItems(displayData?.cutovers || []);
    renderDashboardV2Cutovers(displayData || { cutovers: [] });
    if (!displayData) renderDashboardV2ProcessingFaults(map, []);
    if (dataSimulationEnabled) {
      renderDashboardV2ProcessingFaults(map, applyDisplayModes([...simulatedData.processing_faults, ...cutovers], displayModes));
      infoDrawer?.render(simulatedData);
    } else if (latestDashboardData) {
      renderDashboardV2ProcessingFaults(map, applyDisplayModes([...latestDashboardData.processing_faults, ...cutovers], displayModes));
      infoDrawer?.render(latestDashboardData);
    }
  };
  own(initializeDisplaySettings((modes) => { displayModes = modes; renderFaultData(); }));
  const refreshDashboardData = createDashboardMapRefresher({
    load: (options) => fetchDashboardV2Data(config.dataUrl, options),
    onSuccess: (data) => {
      hasDashboardData = true;
      latestDashboardData = reconcileDashboardData(latestDashboardData, data);
      const serverTime = Date.parse(data.timestamp);
      if (Number.isFinite(serverTime)) serverTimeOffset = serverTime - Date.now();
      renderDashboardV2Sites(map, data.sites);
      renderFaultData();
    },
    onData() {},
    onError: (error) => {
      console.error('[Dashboard V2] 态势数据加载失败:', error);
      if (!dataSimulationEnabled) {
        infoDrawer?.showError({ preserveData: hasDashboardData });
      }
      if (!hasDashboardData && !dataSimulationEnabled) {
        const cutoverList = document.getElementById('dashboard-v2-info-cutover-list');
        if (cutoverList) cutoverList.textContent = '割接数据加载失败';
      }
    },
  });
  own({ destroy: () => refreshDashboardData.destroy() });
  const stopRefresh = startDashboardAutoRefresh({
    refresh: refreshDashboardData,
    intervalMs: 30000,
  });
  disposers.push(stopRefresh);
  const elapsedTimer = setInterval(() => {
    if (!dataSimulationEnabled) infoDrawer?.updateElapsed(Date.now() + serverTimeOffset);
  }, 1000);
  disposers.push(() => clearInterval(elapsedTimer));
  own(initializeDashboardV2DebugPanel(map, {
    ...config,
    onDataSimulationChange(enabled) {
      dataSimulationEnabled = enabled;
      simulatedData = enabled ? createDashboardV2MockFaultData(latestDashboardData || {}) : null;
      if (enabled) infoDrawer?.setExpanded(true);
      renderFaultData();
    },
  }));
  const results = await Promise.allSettled([
    initializeDashboardV2Galaxy(map).then(own),
    initializeDashboardV2Starfield(map).then(own),
  ]);
  if (disposed) return;
  results.forEach((result) => {
    if (result.status === 'rejected') console.error('[Dashboard V2] 星空加载失败:', result.reason);
  });
  own(initializeDashboardV2SkyControl(
    results[0].status === 'fulfilled' ? results[0].value : null,
    results[1].status === 'fulfilled' ? results[1].value : null,
  ));
});

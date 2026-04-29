/**
 * Statistics cable-break map mode.
 *
 * Reuses the unified map core and the fault-map data/popup conventions, but
 * keeps controls and layers isolated from the normal fault distribution mode.
 *
 * Performance optimisations (v9):
 *   - Shared site layers are "down-tuned" for iframe context
 *   - Fault points use clustered WebGL layers (not DOM Markers)
 *   - Clusters auto-expand on click; individual pins show popup on hover
 */

class CableBreakSkippedCountControl {
  constructor(skipped_count, defaulted_count) {
    this.skipped_count = skipped_count || 0;
    this.defaulted_count = defaulted_count || 0;
    this.container = null;
  }

  onAdd(map) {
    this.map = map;
    this.container = document.createElement("div");
    this.container.className = "maplibregl-ctrl statistics-cable-break-skipped-count";

    if (this.defaulted_count > 0 && this.skipped_count > 0) {
      this.container.textContent = `本期另有 ${this.defaulted_count} 条光缆中断缺失经纬度，已按默认站点坐标绘制；${this.skipped_count} 条缺少可用站点坐标，未在地图绘制`;
    } else if (this.defaulted_count > 0) {
      this.container.textContent = `本期另有 ${this.defaulted_count} 条光缆中断缺失经纬度，已按默认站点坐标绘制`;
    } else if (this.skipped_count > 0) {
      this.container.textContent = `本期另有 ${this.skipped_count} 条光缆中断缺少可用站点坐标，未在地图绘制`;
    } else {
      this.container.style.display = "none";
    }

    return this.container;
  }

  onRemove() {
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
    this.map = undefined;
  }
}

class CableBreakPeriodControl {
  constructor(periodLabel) {
    this.periodLabel = periodLabel || "";
    this.container = null;
    this.fullscreenChangeHandler = null;
  }

  onAdd(map) {
    this.map = map;
    this.container = document.createElement("div");
    this.container.className = "maplibregl-ctrl statistics-cable-break-period-control";

    if (this.periodLabel) {
      this.container.textContent = this.periodLabel;
    } else {
      this.container.style.display = "none";
    }
    this.fullscreenChangeHandler = () => this.updateVisibility();
    document.addEventListener("fullscreenchange", this.fullscreenChangeHandler);
    this.updateVisibility();

    return this.container;
  }

  updateVisibility() {
    if (!this.container || !this.map || !this.periodLabel) return;
    const fullscreenElement = document.fullscreenElement;
    const isMapFullscreen = Boolean(fullscreenElement && this.map.getContainer().contains(fullscreenElement));
    this.container.style.display = isMapFullscreen ? "block" : "none";
  }

  onRemove() {
    if (this.fullscreenChangeHandler) {
      document.removeEventListener("fullscreenchange", this.fullscreenChangeHandler);
      this.fullscreenChangeHandler = null;
    }
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
    this.map = undefined;
  }
}

class CableBreakQuickFilterControl {
  constructor(plugin) {
    this.plugin = plugin;
    this.container = null;
    this.buttons = new Map();
    this.filters = [
      { key: "selfControlled", label: "自控", icon: "shield", title: "仅显示自控光缆中断" },
      { key: "long", label: "长时", icon: "hourglass", title: "仅显示历时大于等于 6 小时的故障" },
      { key: "repeat", label: "重复", icon: "repeat", title: "仅显示历史重复故障" },
      { key: "validDuration", label: "滤除短时", icon: "filter", title: "<=30分钟" },
    ];
  }

  onAdd(map) {
    this.map = map;
    this.container = document.createElement("div");
    this.container.className = "maplibregl-ctrl statistics-cable-break-quick-filters";

    this.filters.forEach((filter) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "statistics-cable-break-quick-filter-button";
      button.innerHTML = `${renderQuickFilterIcon(filter.icon)}<span>${filter.label}</span>`;
      button.title = filter.title;
      button.setAttribute("aria-label", filter.title);
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", () => {
        this.plugin.toggleFilter(filter.key);
        this.update();
      });
      this.buttons.set(filter.key, button);
      this.container.appendChild(button);
    });

    return this.container;
  }

  update() {
    this.buttons.forEach((button, filterKey) => {
      const active = this.plugin.activeQuickFilters.has(filterKey);
      button.classList.toggle("statistics-cable-break-quick-filter-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  onRemove() {
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
    this.map = undefined;
  }
}

function renderQuickFilterIcon(icon) {
  const iconPaths = {
    shield: '<path d="M12 3.2 19 6v5.4c0 4.2-2.8 7.7-7 9.4-4.2-1.7-7-5.2-7-9.4V6z"></path><path d="M9.2 12.1 11.2 14l3.8-4"></path>',
    hourglass: '<path d="M7 3h10"></path><path d="M7 21h10"></path><path d="M8 3c0 4.2 2.2 6.2 4 8 1.8-1.8 4-3.8 4-8"></path><path d="M8 21c0-4.2 2.2-6.2 4-8 1.8 1.8 4 3.8 4 8"></path>',
    repeat: '<path d="M17 2.5l3.5 3.5L17 9.5"></path><path d="M3.5 11V9.5A3.5 3.5 0 0 1 7 6h13.5"></path><path d="M7 21.5 3.5 18 7 14.5"></path><path d="M20.5 13v1.5A3.5 3.5 0 0 1 17 18H3.5"></path>',
    filter: '<path d="M4 5h16l-6.2 7.1v5.2l-3.6 1.8v-7z"></path>',
  };
  const path = iconPaths[icon] || iconPaths.filter;
  return `<svg class="statistics-cable-break-quick-filter-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${path}</svg>`;
}

const StatisticsCableBreakModePlugin = {
  core: null,
  map: null,
  mapBase: null,
  config: null,
  features: [],
  filteredFeatures: [],
  activeQuickFilters: new Set(),
  currentPopup: null,
  popupCloseTimer: null,
  skippedCountControl: null,
  periodControl: null,
  legendControl: null,
  quickFilterControl: null,

  init(core) {
    this.core = core;
    this.map = core.map;
    this.mapBase = core.mapBase;
    this.config = core.config;

    this._optimizeSharedLayers();
    this._initData();
    this._addFaultLayer();
    this._addControls();
    this._setupEventListeners();
    this._setStableView();
  },

  // ─── 性能核心：降档共享图层的 GPU 密集属性 ───
  _optimizeSharedLayers() {
    const map = this.map;

    if (map.getLayer("netbox-sites-labels")) {
      map.setPaintProperty("netbox-sites-labels", "text-halo-blur", 0);
      map.setLayerZoomRange("netbox-sites-labels", 8, 24);
    }

    if (map.getLayer("netbox-sites-layer")) {
      map.setPaintProperty("netbox-sites-layer", "circle-stroke-width", 0);
      map.setPaintProperty("netbox-sites-layer", "circle-opacity", 0.55);
      map.setPaintProperty("netbox-sites-layer", "circle-radius", 3);
    }

    if (map.getLayer("user-geojson-fill")) {
      map.setPaintProperty("user-geojson-fill", "fill-opacity", 0.02);
    }
  },

  // ─── 数据初始化 ───
  _initData() {
    const markerData = this.config.markerData || [];
    this.features = FaultDataService.convertToFeatures(markerData);
    this.filteredFeatures = this.features;
  },

  // ─── 水滴形 SVG 图标生成（复刻原生 Marker 3D 效果） ───
  _createTeardropIcon(fillColor, dashed = false) {
    const svg = `<svg width="54" height="82" viewBox="0 0 27 41" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="13.5" cy="34.8" rx="10.5" ry="5.25" fill="black" opacity="0.12"/>
      <path fill="${fillColor}" d="M27,13.5C27,19.1 20.3,27 14.1,34.1C13.7,34.5 13.2,34.5 12.9,34.1C6.6,27 0,19.2 0,13.5C0,6 6,0 13.5,0C20.9,0 27,6 27,13.5Z"/>
      <path fill="none" stroke="white" stroke-width="2" stroke-dasharray="${dashed ? '3 2' : '0'}" d="M13.5,1C20.4,1 26,6.6 26,13.5C26,15.8 24.7,19.8 21.5,24.4C18.9,28.2 15.9,31.6 13.5,34C11.1,31.6 8.1,28.2 5.5,24.4C2.3,19.8 1,15.8 1,13.5C1,6.6 6.6,1 13.5,1Z"/>
      <path opacity="0.25" d="M13.5,0C6,0 0,6 0,13.5C0,19.2 6.6,27 12.9,34.1C13.2,34.5 13.7,34.5 14.1,34.1C20.3,27 27,19.1 27,13.5C27,6 20.9,0 13.5,0ZM13.5,1C20.4,1 26,6.6 26,13.5C26,15.8 24.7,19.8 21.5,24.4C18.9,28.2 15.9,31.6 13.5,34C11.1,31.6 8.1,28.2 5.5,24.4C2.3,19.8 1,15.8 1,13.5C1,6.6 6.6,1 13.5,1Z"/>
      <circle fill="white" cx="13.5" cy="13.5" r="5.5"/>
    </svg>`;

    return new Promise((resolve) => {
      const img = new Image(54, 82);
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    });
  },

  // ─── 聚合模式 + 水滴图标 ───
  async _addFaultLayer() {
    const map = this.map;
    const geojson = {
      type: "FeatureCollection",
      features: this.filteredFeatures,
    };

    // 启用聚合的 GeoJSON 数据源
    map.addSource("cable-break-faults", {
      type: "geojson",
      data: geojson,
      cluster: true,
      clusterMaxZoom: 12,
      clusterRadius: 50,
      clusterProperties: {
        hasProcessing: ["max", ["case", ["==", ["get", "statusKey"], "processing"], 1, 0]],
        hasSuspended: ["max", ["case", ["==", ["get", "statusKey"], "suspended"], 1, 0]],
        hasTemporaryRecovery: ["max", ["case", ["==", ["get", "statusKey"], "temporary_recovery"], 1, 0]],
        hasClosed: ["max", ["case", ["==", ["get", "statusKey"], "closed"], 1, 0]],
      },
    });

    // ── A. 聚合圆圈层 ──
    map.addLayer({
      id: "cb-clusters",
      type: "circle",
      source: "cable-break-faults",
      filter: ["has", "point_count"],
      paint: {
        // Cluster color follows the highest-priority fault status in the cluster.
        "circle-color": [
          "case",
          ["==", ["get", "hasProcessing"], 1], FAULT_STATUS_COLORS.processing || "#dc3545",
          ["==", ["get", "hasSuspended"], 1], FAULT_STATUS_COLORS.suspended || "#ffc107",
          ["==", ["get", "hasTemporaryRecovery"], 1], FAULT_STATUS_COLORS.temporary_recovery || "#0d6efd",
          ["==", ["get", "hasClosed"], 1], FAULT_STATUS_COLORS.closed || "#198754",
          "#51bbd6",
        ],
        "circle-radius": [
          "step", ["get", "point_count"],
          18,         // < 5: 18px
          5, 24,      // 5-10: 24px
          10, 30,     // ≥ 10: 30px
        ],
        "circle-stroke-width": 3,
        "circle-stroke-color": "rgba(255,255,255,0.7)",
        "circle-opacity": 0.85,
      },
    });

    // ── B. 聚合数字标签层 ──
    map.addLayer({
      id: "cb-cluster-count",
      type: "symbol",
      source: "cable-break-faults",
      filter: ["has", "point_count"],
      layout: {
        "text-field": "{point_count_abbreviated}",
        "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
        "text-size": 13,
        "text-allow-overlap": true,
      },
      paint: {
        "text-color": "#ffffff",
      },
    });

    // ── C. 非聚合的单个故障点（水滴图标） ──
    const statusEntries = {
      processing: FAULT_STATUS_COLORS.processing || "#dc3545",
      temporary_recovery: FAULT_STATUS_COLORS.temporary_recovery || "#0d6efd",
      suspended: FAULT_STATUS_COLORS.suspended || "#ffc107",
      closed: FAULT_STATUS_COLORS.closed || "#198754",
    };

    const iconPromises = Object.entries(statusEntries).map(async ([key, color]) => {
      const iconName = `cb-pin-${key}`;
      if (!map.hasImage(iconName)) {
        const img = await this._createTeardropIcon(color);
        if (img && !map.hasImage(iconName)) {
          map.addImage(iconName, img, { pixelRatio: 2 });
        }
      }

      const defaultedIconName = `cb-pin-${key}-defaulted`;
      if (!map.hasImage(defaultedIconName)) {
        const img = await this._createTeardropIcon(color, true);
        if (img && !map.hasImage(defaultedIconName)) {
          map.addImage(defaultedIconName, img, { pixelRatio: 2 });
        }
      }
    });
    await Promise.all(iconPromises);

    const iconImageExpr = [
      "case",
      ["to-boolean", ["get", "coordsFromSite"]],
      [
        "match",
        ["coalesce", ["get", "statusKey"], "processing"],
        "processing", "cb-pin-processing-defaulted",
        "temporary_recovery", "cb-pin-temporary_recovery-defaulted",
        "suspended", "cb-pin-suspended-defaulted",
        "closed", "cb-pin-closed-defaulted",
        "cb-pin-processing-defaulted",
      ],
      [
        "match",
        ["coalesce", ["get", "statusKey"], "processing"],
        "processing", "cb-pin-processing",
        "temporary_recovery", "cb-pin-temporary_recovery",
        "suspended", "cb-pin-suspended",
        "closed", "cb-pin-closed",
        "cb-pin-processing",
      ],
    ];

    map.addLayer({
      id: "cable-break-faults-layer",
      type: "symbol",
      source: "cable-break-faults",
      filter: ["!", ["has", "point_count"]],
      layout: {
        "icon-image": iconImageExpr,
        "icon-size": ["interpolate", ["linear"], ["zoom"], 4, 0.8, 10, 1.0],
        "icon-allow-overlap": true,
        "icon-anchor": "bottom",
        "icon-pitch-alignment": "viewport",
        "icon-rotation-alignment": "viewport",
      },
    });
  },

  // ─── 图层事件监听 ───
  _setupEventListeners() {
    const map = this.map;

    // 聚合圆圈：点击展开
    map.on("click", "cb-clusters", async (e) => {
      const features = map.queryRenderedFeatures(e.point, { layers: ["cb-clusters"] });
      if (!features.length) return;
      const clusterId = features[0].properties.cluster_id;
      try {
        const zoom = await map.getSource("cable-break-faults").getClusterExpansionZoom(clusterId);
        map.easeTo({
          center: features[0].geometry.coordinates,
          zoom: zoom,
          duration: 500,
        });
      } catch (err) {
        console.warn("[CableBreakMap] Cluster expansion failed:", err);
      }
    });

    map.on("mouseenter", "cb-clusters", () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "cb-clusters", () => {
      map.getCanvas().style.cursor = "";
    });

    // 单个故障点：悬浮弹窗
    const layerId = "cable-break-faults-layer";

    map.on("mouseenter", layerId, (e) => {
      map.getCanvas().style.cursor = "pointer";
      if (e.features && e.features.length) {
        this._showFaultPopup(e.features[0]);
      }
    });

    map.on("mouseleave", layerId, () => {
      map.getCanvas().style.cursor = "";
      this._startPopupCloseTimer();
    });

    map.on("click", layerId, (e) => {
      if (e.features && e.features.length) {
        this._showFaultPopup(e.features[0]);
      }
    });
  },

  // ─── 控件注册 ───
  _addControls() {
    if (typeof FaultLegendControl !== "undefined") {
      this.legendControl = new FaultLegendControl({ showCategories: false, showStatuses: true });
      this.map.addControl(this.legendControl, "bottom-right");
      this.legendControl.updateVisibility("points");
    }

    const map = this.map;
    this.periodControl = new CableBreakPeriodControl(this.config.mapPeriodLabel);
    map.addControl(this.periodControl, "top-left");

    this.quickFilterControl = new CableBreakQuickFilterControl(this);
    map.addControl(this.quickFilterControl, "top-left");

    this.skippedCountControl = new CableBreakSkippedCountControl(this.config.skipped_count || 0, this.config.defaulted_count || 0);
    map.addControl(this.skippedCountControl, 'bottom-left');
  },

  toggleFilter(filterKey) {
    if (this.activeQuickFilters.has(filterKey)) {
      this.activeQuickFilters.delete(filterKey);
    } else {
      this.activeQuickFilters.add(filterKey);
    }
    this.applyQuickFilters();
  },

  applyQuickFilters() {
    this.filteredFeatures = this.features.filter((feature) => {
      const matchesSelfControlled = feature.properties.sourceGroup === '自控';
      const matchesLong = feature.properties.isLong === true;
      const matchesRepeat = feature.properties.isRepeat === true;
      const matchesValidDuration = feature.properties.isValidDuration === true;

      if (this.activeQuickFilters.has("selfControlled") && !matchesSelfControlled) {
        return false;
      }
      if (this.activeQuickFilters.has("long") && !matchesLong) {
        return false;
      }
      if (this.activeQuickFilters.has("repeat") && !matchesRepeat) {
        return false;
      }
      if (this.activeQuickFilters.has("validDuration") && !matchesValidDuration) {
        return false;
      }
      return true;
    });

    const source = this.map.getSource("cable-break-faults");
    if (source) {
      source.setData({
        type: "FeatureCollection",
        features: this.filteredFeatures,
      });
    }

    if (this.currentPopup) {
      this.currentPopup.remove();
      this.currentPopup = null;
    }
  },

  // ─── Popup 显示（保留延迟关闭逻辑） ───
  _showFaultPopup(feature) {
    if (typeof PopupTemplates === "undefined") return;

    this._clearPopupCloseTimer();

    const props = feature.properties || {};

    const html = PopupTemplates.faultPopup(props)
      .replaceAll('target="_blank"', 'target="_parent"');

    if (this.currentPopup) {
      this.currentPopup.remove();
    }

    this.currentPopup = new maplibregl.Popup({
      closeButton: true,
      closeOnClick: false,
      maxWidth: "360px",
      className: "fault-popup-container",
    })
      .setLngLat(feature.geometry.coordinates)
      .setHTML(html)
      .addTo(this.map);

    const popupElement = this.currentPopup.getElement();
    popupElement.addEventListener("mouseenter", () => {
      this._clearPopupCloseTimer();
    });
    popupElement.addEventListener("mouseleave", () => {
      this._startPopupCloseTimer();
    });
  },

  _clearPopupCloseTimer() {
    if (this.popupCloseTimer) {
      clearTimeout(this.popupCloseTimer);
      this.popupCloseTimer = null;
    }
  },

  _startPopupCloseTimer() {
    this._clearPopupCloseTimer();
    this.popupCloseTimer = setTimeout(() => {
      if (this.currentPopup) {
        this.currentPopup.remove();
        this.currentPopup = null;
      }
      this.popupCloseTimer = null;
    }, 250);
  },

  // ─── 固定初始视野，避免故障点分布压缩地图窗口观感 ───
  _setStableView() {
    this.map.resize();
    this.map.jumpTo({
      center: this.config.center,
      zoom: this.config.zoom,
      bearing: 0,
      pitch: 0,
    });
  },
};

const statisticsCableBreakStyle = document.createElement("style");
statisticsCableBreakStyle.textContent = `
  .statistics-cable-break-skipped-count {
    max-width: min(360px, calc(100vw - 48px));
    padding: 8px 10px;
    border-radius: 4px;
    background: rgba(33, 37, 41, 0.88);
    color: #fff;
    font-size: 12px;
    line-height: 1.45;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
  }

  .maplibregl-ctrl-top-left .statistics-cable-break-period-control {
    display: none;
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    max-width: min(620px, calc(100vw - 96px));
    margin: 0;
    padding: 10px 16px;
    border-radius: 4px;
    background: rgba(33, 37, 41, 0.88);
    color: #fff;
    font-size: 16px;
    font-weight: 700;
    line-height: 1.4;
    text-align: center;
    white-space: normal;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
    pointer-events: none;
  }

  .statistics-cable-break-quick-filters.maplibregl-ctrl {
    display: flex;
    gap: 8px;
    overflow: visible;
    background: transparent;
    box-shadow: none;
  }

  .statistics-cable-break-quick-filter-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    width: auto;
    min-width: 66px;
    height: 38px;
    margin: 0;
    padding: 0 12px;
    border: 0;
    border-radius: 4px;
    color: #202124;
    background: #ffffff !important;
    box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.1);
    font-size: 12px;
    font-weight: 600;
    line-height: 1;
    white-space: nowrap;
    cursor: pointer;
  }

  .statistics-cable-break-quick-filter-button + .statistics-cable-break-quick-filter-button {
    border-left: 0;
  }

  .statistics-cable-break-quick-filter-button:hover,
  .statistics-cable-break-quick-filter-button:focus,
  .statistics-cable-break-quick-filter-button:active {
    background: #ffffff !important;
  }

  .statistics-cable-break-quick-filter-button.statistics-cable-break-quick-filter-active {
    color: #4f73ff;
    background: #ffffff !important;
  }

  .statistics-cable-break-quick-filter-icon {
    width: 18px;
    height: 18px;
    display: block;
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .statistics-cable-break-quick-filter-icon circle {
    fill: currentColor;
    stroke: none;
  }
`;
document.head.appendChild(statisticsCableBreakStyle);

window.initOTNMap(StatisticsCableBreakModePlugin);

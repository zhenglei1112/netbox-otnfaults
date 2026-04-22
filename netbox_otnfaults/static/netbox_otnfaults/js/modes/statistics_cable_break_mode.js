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

const StatisticsCableBreakModePlugin = {
  core: null,
  map: null,
  mapBase: null,
  config: null,
  features: [],
  currentPopup: null,
  popupCloseTimer: null,
  skippedCountControl: null,
  legendControl: null,

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
    this._fitBounds();
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
      features: this.features,
    };

    // 启用聚合的 GeoJSON 数据源
    map.addSource("cable-break-faults", {
      type: "geojson",
      data: geojson,
      cluster: true,
      clusterMaxZoom: 12,
      clusterRadius: 50,
    });

    // ── A. 聚合圆圈层 ──
    map.addLayer({
      id: "cb-clusters",
      type: "circle",
      source: "cable-break-faults",
      filter: ["has", "point_count"],
      paint: {
        // 根据聚合数量渐变大小和颜色
        "circle-color": [
          "step", ["get", "point_count"],
          "#51bbd6",   // < 5: 浅蓝
          5, "#f1a340", // 5-10: 橙色
          10, "#e04040", // ≥ 10: 红色
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
    this.skippedCountControl = new CableBreakSkippedCountControl(this.config.skipped_count || 0, this.config.defaulted_count || 0);
    map.addControl(this.skippedCountControl, 'bottom-left');
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

  // ─── 自适应视野 ───
  _fitBounds() {
    if (!this.features.length) return;

    const bounds = new maplibregl.LngLatBounds();
    this.features.forEach((feature) => {
      bounds.extend(feature.geometry.coordinates);
    });

    if (!bounds.isEmpty()) {
      this.map.fitBounds(bounds, {
        padding: 80,
        maxZoom: 10,
        duration: 700,
      });
    }
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
`;
document.head.appendChild(statisticsCableBreakStyle);

window.initOTNMap(StatisticsCableBreakModePlugin);

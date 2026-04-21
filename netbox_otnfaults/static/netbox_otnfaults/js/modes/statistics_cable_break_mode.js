/**
 * Statistics cable-break map mode.
 *
 * Reuses the unified map core and the fault-map data/popup conventions, but
 * keeps controls and layers isolated from the normal fault distribution mode.
 */

class CableBreakSkippedCountControl {
  constructor(skipped_count) {
    this.skipped_count = skipped_count || 0;
    this.container = null;
  }

  onAdd(map) {
    this.map = map;
    this.container = document.createElement("div");
    this.container.className = "maplibregl-ctrl statistics-cable-break-skipped-count";

    if (this.skipped_count > 0) {
      this.container.textContent = `本期另有 ${this.skipped_count} 条光缆中断缺失经纬度，未在地图绘制`;
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
  markers: [],
  currentPopup: null,
  popupCloseTimer: null,
  skippedCountControl: null,
  legendControl: null,

  init(core) {
    this.core = core;
    this.map = core.map;
    this.mapBase = core.mapBase;
    this.config = core.config;

    this._initData();
    this._addDefaultMarkers();
    this._addControls();
    this._fitBounds();
  },

  _initData() {
    const markerData = this.config.markerData || [];
    this.features = FaultDataService.convertToFeatures(markerData);
  },

  _addDefaultMarkers() {
    this.features.forEach((feature) => {
      const marker = new maplibregl.Marker({ color: this._getMarkerColor(feature) })
        .setLngLat(feature.geometry.coordinates)
        .addTo(this.map);

      marker.getElement().addEventListener("mouseenter", () => {
        this._showFaultPopup(feature);
      });
      marker.getElement().addEventListener("mouseleave", () => {
        this._startPopupCloseTimer();
      });
      marker.getElement().addEventListener("click", () => {
        this._showFaultPopup(feature);
      });

      this.markers.push(marker);
    });
  },

  _getMarkerColor(feature) {
    const properties = feature.properties || {};
    const statusKey = properties.statusKey || properties.status_key || 'processing';

    return (
      properties.statusColorHex ||
      (typeof FAULT_STATUS_COLORS !== "undefined" && FAULT_STATUS_COLORS[statusKey]) ||
      (typeof FAULT_STATUS_COLORS !== "undefined" && FAULT_STATUS_COLORS.processing) ||
      "#dc3545"
    );
  },

  _addControls() {
    if (typeof FaultLegendControl !== "undefined") {
      this.legendControl = new FaultLegendControl({ showCategories: false, showStatuses: true });
      this.map.addControl(this.legendControl, "bottom-right");
      this.legendControl.updateVisibility("points");
    }

    const map = this.map;
    this.skippedCountControl = new CableBreakSkippedCountControl(this.config.skipped_count || 0);
    map.addControl(this.skippedCountControl, 'bottom-left');
  },

  _showFaultPopup(feature) {
    if (typeof PopupTemplates === "undefined") return;

    this._clearPopupCloseTimer();

    const html = PopupTemplates.faultPopup(feature.properties)
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

class MapStylePreferenceService {
  static DEFAULT_MAP_STYLE_CONFIG = {
    province: {
      visible: true,
      fillColor: "#2c3e50",
      fillOpacity: 0.05,
      lineColor: "rgba(90, 140, 190, 0.7)",
      lineWidth: 1.5,
      lineOpacity: 0.9,
    },
    sites: {
      visible: true,
      circleColor: "#00aaff",
      circleRadius: 3,
      strokeColor: "#ffffff",
      strokeWidth: 1,
      labelColor: "#1a1a1a",
      labelSize: 14,
      labelMinZoom: 6,
    },
    paths: {
      visible: true,
      lineColor: "#00cc66",
      lineWidth: 2,
      lineOpacity: 0.8,
      highlightColor: "#FFD700",
      highlightWidth: 5,
    },
  };

  constructor(map, config) {
    this.map = map;
    this.config = config || {};
    this.defaultConfig = MapStylePreferenceService.clone(MapStylePreferenceService.DEFAULT_MAP_STYLE_CONFIG);
    this.currentConfig = this.merge(this.defaultConfig, this.config.mapStylePreferences || {});
  }

  static clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  merge(baseConfig, overrideConfig) {
    const merged = MapStylePreferenceService.clone(baseConfig);
    const override = overrideConfig || {};
    ["province", "sites", "paths"].forEach((groupName) => {
      const groupOverride = override[groupName];
      if (!groupOverride || typeof groupOverride !== "object") return;
      Object.keys(merged[groupName]).forEach((fieldName) => {
        if (Object.prototype.hasOwnProperty.call(groupOverride, fieldName)) {
          merged[groupName][fieldName] = groupOverride[fieldName];
        }
      });
    });
    return merged;
  }

  getConfig() {
    return MapStylePreferenceService.clone(this.currentConfig);
  }

  resetToDefaults() {
    this.currentConfig = MapStylePreferenceService.clone(this.defaultConfig);
    this.apply(this.currentConfig);
    return this.getConfig();
  }

  apply(config) {
    this.currentConfig = this.merge(this.defaultConfig, config || {});
    this.applyProvince(this.currentConfig.province);
    this.applySites(this.currentConfig.sites);
    this.applyPaths(this.currentConfig.paths);
    return this.getConfig();
  }

  _hasLayer(layerId) {
    return Boolean(this.map && this.map.getLayer && this.map.getLayer(layerId));
  }

  _setPaint(layerId, propertyName, value) {
    if (this._hasLayer(layerId)) {
      this.map.setPaintProperty(layerId, propertyName, value);
    }
  }

  _setLayout(layerId, propertyName, value) {
    if (this._hasLayer(layerId)) {
      this.map.setLayoutProperty(layerId, propertyName, value);
    }
  }

  _setZoomRange(layerId, minZoom, maxZoom) {
    if (this._hasLayer(layerId) && typeof this.map.setLayerZoomRange === "function") {
      this.map.setLayerZoomRange(layerId, minZoom, maxZoom);
    }
  }

  applyProvince(config) {
    const visibility = config.visible ? "visible" : "none";
    this._setLayout("user-geojson-fill", "visibility", visibility);
    this._setLayout("user-geojson-line", "visibility", visibility);
    this._setPaint("user-geojson-fill", "fill-color", config.fillColor);
    this._setPaint("user-geojson-fill", "fill-opacity", config.fillOpacity);
    this._setPaint("user-geojson-line", "line-color", config.lineColor);
    this._setPaint("user-geojson-line", "line-width", config.lineWidth);
    this._setPaint("user-geojson-line", "line-opacity", config.lineOpacity);
  }

  applySites(config) {
    const visibility = config.visible ? "visible" : "none";
    this._setLayout("netbox-sites-layer", "visibility", visibility);
    this._setLayout("netbox-sites-labels", "visibility", visibility);
    this._setPaint("netbox-sites-layer", "circle-color", config.circleColor);
    this._setPaint("netbox-sites-layer", "circle-radius", config.circleRadius);
    this._setPaint("netbox-sites-layer", "circle-stroke-color", config.strokeColor);
    this._setPaint("netbox-sites-layer", "circle-stroke-width", config.strokeWidth);
    this._setPaint("netbox-sites-labels", "text-color", config.labelColor);
    this._setLayout("netbox-sites-labels", "text-size", config.labelSize);
    this._setZoomRange("netbox-sites-labels", config.labelMinZoom, 24);
  }

  applyPaths(config) {
    const visibility = config.visible ? "visible" : "none";
    this._setLayout("otn-paths-layer", "visibility", visibility);
    this._setLayout("otn-paths-highlight-outline", "visibility", visibility);
    this._setLayout("otn-paths-highlight-layer", "visibility", visibility);
    this._setPaint("otn-paths-layer", "line-color", config.lineColor);
    this._setPaint("otn-paths-layer", "line-width", config.lineWidth);
    this._setPaint("otn-paths-layer", "line-opacity", config.lineOpacity);
    this._setPaint("otn-paths-highlight-outline", "line-color", "#ffffff");
    this._setPaint("otn-paths-highlight-outline", "line-width", config.highlightWidth + 2);
    this._setPaint("otn-paths-highlight-layer", "line-color", config.highlightColor);
    this._setPaint("otn-paths-highlight-layer", "line-width", config.highlightWidth);
  }
}

window.MapStylePreferenceService = MapStylePreferenceService;

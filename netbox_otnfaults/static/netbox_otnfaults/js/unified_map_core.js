/**
 * 统一地图核心类
 * 负责地图初始化、通用控件加载和模式插件分发
 */

class OTNMapCore {
  constructor(configKey = "OTNMapConfig") {
    this.configKey = configKey;
    this.mapBase = new NetBoxMapBase();
    this.map = null;
    this.modePlugin = null;
    this.config = window[configKey];
  }

  /**
   * 初始化地图入口
   * @param {Object} modePlugin - 模式特定插件对象
   */
  async init(modePlugin) {
    console.log("OTNMapCore: Initializing with mode", this.config.mode);
    this.modePlugin = modePlugin;

    // 1. 初始化地图实例
    try {
      this.map = this.mapBase.init("map", this.config.apiKey);
      // 暴露给控制台调试
      window.map = this.map;
      window.mapBase = this.mapBase;
    } catch (e) {
      NetBoxMapBase.showError("map", e.message);
      return;
    }

    // 显示加载状态
    NetBoxMapBase.showLoading("map");

    // 2. 基础底图设置
    this.map.on("load", () => {
      NetBoxMapBase.hideLoading("map");
      this._setupBasemapFeatures();

      // 3. 加载共享层（如站点、OTN路径）
      this._initSharedLayers();

      // 4. 初始化模式插件
      if (this.modePlugin && typeof this.modePlugin.init === "function") {
        try {
          this.modePlugin.init(this);
        } catch (pluginError) {
          console.error("OTNMapCore: Plugin init failed", pluginError);
          NetBoxMapBase.showError(
            "map",
            "Map mode initialization check console."
          );
        }
      }
    });

    // 5. 添加通用控件
    this._addCommonControls();
  }

  /**
   * 设置底图特性 (中国边界、中文标签、高速盾标)
   */
  _setupBasemapFeatures() {
    if (!this.config.useLocalBasemap) {
      this.mapBase.emphasizeChinaBoundaries();
      this.mapBase.setLanguageToChinese();
      this.mapBase.filterLabels();
      this.mapBase.initHighwayShields();
    }
  }

  /**
   * 初始化共享图层 (站点和 OTN 路径底图)
   */
  _initSharedLayers() {
    // A. OTN 路径 PMTiles
    if (this.config.otnPathsPmtilesUrl) {
      this.map.addSource("otn_paths_pmtiles", {
        type: "vector",
        url: "pmtiles://" + this.config.otnPathsPmtilesUrl,
      });

      // 查找插入位置 (放在符号层之下)
      const firstSymbolId = this._findFirstSymbolLayerId();

      // 路径显示层
      this.mapBase.addLayer(
        {
          id: "otn-paths-layer",
          type: "line",
          source: "otn_paths_pmtiles",
          "source-layer": "otn_paths",
          layout: {
            "line-join": "round",
            "line-cap": "round",
            visibility: "visible",
          },
          paint: {
            "line-color": "#00cc66", // 默认绿色，模式插件可覆盖样式
            "line-width": 2,
            "line-opacity": 0.8,
          },
        },
        firstSymbolId
      );

      // 透明点击检测层
      this.mapBase.addLayer(
        {
          id: "otn-paths-labels",
          type: "line",
          source: "otn_paths_pmtiles",
          "source-layer": "otn_paths",
          paint: { "line-width": 10, "line-opacity": 0 },
        },
        firstSymbolId
      );

      // 鼠标样式
      this.map.on(
        "mouseenter",
        "otn-paths-labels",
        () => (this.map.getCanvas().style.cursor = "pointer")
      );
      this.map.on(
        "mouseleave",
        "otn-paths-labels",
        () => (this.map.getCanvas().style.cursor = "")
      );
    }

    // B. 站点图层
    if (this.config.sitesData && this.config.sitesData.length > 0) {
      const siteFeatures = this.config.sitesData.map((site) => ({
        type: "Feature",
        properties: site,
        geometry: {
          type: "Point",
          coordinates: [site.longitude, site.latitude],
        },
      }));

      this.mapBase.addGeoJsonSource("netbox-sites", {
        type: "FeatureCollection",
        features: siteFeatures,
      });

      // 站点圆点
      this.mapBase.addLayer({
        id: "netbox-sites-layer",
        type: "circle",
        source: "netbox-sites",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 3, 10, 6],
          "circle-color": "#00aaff",
          "circle-stroke-width": 1,
          "circle-stroke-color": "#fff",
        },
      });

      // 站点标签
      this.mapBase.addLayer({
        id: "netbox-sites-labels",
        type: "symbol",
        source: "netbox-sites",
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
          "text-offset": [0, 1.2],
          "text-anchor": "top",
          "text-size": 12,
        },
        paint: {
          "text-color": "#333",
          "text-halo-color": "#fff",
          "text-halo-width": 1,
        },
        minzoom: 6,
      });

      this.map.on(
        "mouseenter",
        "netbox-sites-layer",
        () => (this.map.getCanvas().style.cursor = "pointer")
      );
      this.map.on(
        "mouseleave",
        "netbox-sites-layer",
        () => (this.map.getCanvas().style.cursor = "")
      );
    }
  }

  _addCommonControls() {
    this.mapBase.addStandardControls();
    this.mapBase.addHomeControl();

    // 如果配置中包含 measures 控件
    const controlsConfig =
      this.config.layers?.controls || this.config.modeConfig?.controls || [];
    // 注意：layers_config 是从 json.dumps 出来的，可能是 Object 或 undefined。
    // 在 map_modes.py 中 controls 是顶级键。
    // 我们需要在视图中将 controls 传递给前端，或者在这里硬编码逻辑。
    // 为了简单，我们对所有 Mercator 投影启用测距，或者检查是否存在特定 JS/CSS
    if (window.maplibreGLMeasures) {
      this._addMeasuresControl();
    }
  }

  _addMeasuresControl() {
    const MeasuresControl = window.maplibreGLMeasures.default;
    const measuresControl = new MeasuresControl({
      lang: {
        areaMeasurementButtonTitle: "测量面积",
        lengthMeasurementButtonTitle: "测量距离",
        clearMeasurementsButtonTitle: "清除测量",
      },
      units: "metric",
      style: {
        text: { color: "#D20C0C", font: "Open Sans Regular" },
        common: { midPointColor: "#D20C0C" },
        lengthMeasurement: { lineColor: "#D20C0C" },
      },
    });

    // Monkey patch specific to 'km' -> '公里'
    const originalFormatMetric =
      measuresControl._formatToMetricSystem.bind(measuresControl);
    measuresControl._formatToMetricSystem = function (value) {
      return originalFormatMetric(value).replace("km", "公里");
    };

    this.mapBase.addControl(measuresControl, "top-right");
  }

  _findFirstSymbolLayerId() {
    const layers = this.map.getStyle().layers;
    for (const layer of layers) {
      if (layer.type === "symbol") return layer.id;
    }
    return undefined;
  }

  /**
   * 注册模式插件的全局入口
   */
  static register(plugin) {
    const core = new OTNMapCore();
    // 等待 DOMContentLoaded 以确保 config 已注入
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => core.init(plugin));
    } else {
      core.init(plugin);
    }
  }
}

// 暴露全局注册函数供插件使用
window.initOTNMap = OTNMapCore.register;

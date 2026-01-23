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
    if (window.OTNPerf) window.OTNPerf.mark('init_start');
    this.modePlugin = modePlugin;

    // 1. 初始化地图实例 (立即渲染容器)
    try {
      this.map = this.mapBase.init("map", this.config.apiKey);

      // 初始隐藏地图画布，防止显示平面模式的短暂跳变
      if (this.config.projection === 'globe') {
        this.map.getCanvas().style.opacity = '0';
        this.map.getCanvas().style.transition = 'opacity 0.3s ease-in';
      }

      if (window.OTNPerf) window.OTNPerf.mark('map_instance_created');
      window.map = this.map;
      window.mapBase = this.mapBase;
    } catch (e) {
      NetBoxMapBase.showError("map", e.message);
      return;
    }

    // 显示加载状态 (覆盖在地图上)
    NetBoxMapBase.showLoading("map");

    // 2. 异步加载数据 (与地图初始化并行)
    let dataPromise = Promise.resolve(null);
    if (this.config.mapDataUrl) {
      console.log('[OTNMapCore] Fetching data from:', this.config.mapDataUrl);
      dataPromise = fetch(this.config.mapDataUrl)
        .then(async res => {
          if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
          return await res.json();
        })
        .catch(err => {
          console.error("Failed to load map data:", err);
          // 错误处理：可以在这里显示 Toast，或者在 load 事件中处理
          // 返回 null 以便能继续渲染地图(虽然没有数据)
          return null;
        });
    }

    // 3. 基础底图设置 & 等待数据
    this.map.on("load", async () => {
      if (window.OTNPerf) window.OTNPerf.mark('map_load_event');

      // 等待数据返回
      try {
        const data = await dataPromise;
        if (data) {
          this.config.sitesData = data.sites_data;
          this.config.markerData = data.marker_data;
          this.config.heatmapData = data.heatmap_data;
          if (window.OTNPerf) window.OTNPerf.mark('data_fetched');
        }
      } catch (err) {
        // fetch catch 已经捕获了，这里主要是防止赋值出错
        console.error("Error processing fetched data", err);
      }

      NetBoxMapBase.hideLoading("map");
      this._setupBasemapFeatures();

      // 投影设置完成后，显示地图
      if (this.config.projection === 'globe') {
        // 使用 requestAnimationFrame 确保渲染帧已更新
        requestAnimationFrame(() => {
          this.map.getCanvas().style.opacity = '1';
        });
      }

      // 3. 加载共享层（如站点、OTN路径）
      this._initSharedLayers();
      if (window.OTNPerf) window.OTNPerf.mark('shared_layers_done');

      // 4. 初始化模式插件
      if (this.modePlugin && typeof this.modePlugin.init === "function") {
        try {
          this.modePlugin.init(this);
          if (window.OTNPerf) window.OTNPerf.mark('mode_plugin_done');
        } catch (pluginError) {
          console.error("OTNMapCore: Plugin init failed", pluginError);
          NetBoxMapBase.showError(
            "map",
            "Map mode initialization check console."
          );
        }
      }

      // 渲染调试面板
      if (window.OTN_SHOW_DEBUG_PANEL && this._renderDebugPanel) {
        this._renderDebugPanel();
      }

      // 5. 添加通用控件 (必须在 load 事件内，确保样式和字形加载完成)
      this._addCommonControls();
    });
  }

  /**
   * 设置底图特性 (中国边界、中文标签、高速盾标)
   */
  _setupBasemapFeatures() {
    if (!this.config.useLocalBasemap) {
      this.mapBase.emphasizeChinaBoundaries();
      this.mapBase.setLanguageToChinese();
      this.mapBase.filterLabels();
      this.mapBase.filterLabels();
      this.mapBase.initHighwayShields();
    }

    // 设置投影 (Globe 或 Mercator)
    if (this.config.projection) {
      this.mapBase.setProjection(this.config.projection);
      // 同步图标状态
      this.mapBase.updateProjectionIcon();
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
          "circle-opacity": ["step", ["zoom"], 0.5, 6, 1], // Zoom < 6: 50%, Zoom >= 6: 100%
          "circle-stroke-opacity": ["step", ["zoom"], 0.5, 6, 1],
        },
      });

      // 站点标签 (带3D效果)
      this.mapBase.addLayer({
        id: "netbox-sites-labels",
        type: "symbol",
        source: "netbox-sites",
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
          "text-offset": [0, -0.8],  // 负值向上偏移，文本显示在圆点上方
          "text-anchor": "bottom",   // 文本底部锚定在坐标点
          "text-size": [
            "interpolate",
            ["linear"],
            ["zoom"],
            6, 11,   // zoom=6: 11px
            10, 14,  // zoom=10: 14px
            14, 16   // zoom=14: 16px
          ],
          // 3D 效果关键配置: 文本始终面向屏幕
          "text-pitch-alignment": "viewport",
          "text-rotation-alignment": "viewport",
          // 允许文本重叠，确保在3D视角下不被剔除
          "text-allow-overlap": false,
          "text-optional": true,
        },
        paint: {
          "text-color": "#1a1a1a",  // 更深的文本颜色，增强对比
          "text-halo-color": "#ffffff",
          "text-halo-width": 2,      // 增大光晕，增强悬浮和可读性
          "text-halo-blur": 1,       // 添加光晕模糊，增强3D感
          "text-opacity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            6, 0.85,   // 低缩放级别稍微透明
            8, 1       // 高缩放级别完全不透明
          ],
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

    // C. 3D 建筑图层（缩放级别 >= 15 时显示）
    // 添加 OpenFreeMap 矢量瓦片源（包含 OSM 建筑高度数据）
    this.map.addSource('openfreemap-buildings', {
      type: 'vector',
      url: 'https://tiles.openfreemap.org/planet'
    });

    // 查找第一个符号图层，确保 3D 建筑在标签下方显示
    const firstSymbolId = this._findFirstSymbolLayerId();

    // 添加 3D 建筑图层
    this.mapBase.addLayer(
      {
        id: '3d-buildings-layer',
        type: 'fill-extrusion',
        source: 'openfreemap-buildings',
        'source-layer': 'building',
        minzoom: 15, // 只在缩放级别 >= 15 时显示
        filter: ['!=', ['get', 'hide_3d'], true], // 过滤掉标记为隐藏的建筑
        paint: {
          // 建筑颜色：根据高度渐变（低→灰色，高→蓝色）
          'fill-extrusion-color': [
            'interpolate',
            ['linear'],
            ['get', 'render_height'], // 使用建筑渲染高度属性
            0, 'lightgray',      // 0米：浅灰色
            200, 'royalblue',    // 200米：皇家蓝
            400, 'lightblue'     // 400米以上：浅蓝色
          ],
          // 建筑高度：根据缩放级别插值，实现平滑过渡
          'fill-extrusion-height': [
            'interpolate',
            ['linear'],
            ['zoom'],
            15, 0,                        // zoom=15: 高度为0（不显示立体效果）
            16, ['get', 'render_height']  // zoom=16: 显示完整高度
          ],
          // 建筑底部高度（用于多层建筑）
          'fill-extrusion-base': [
            'interpolate',
            ['linear'],
            ['zoom'],
            15, 0,                                          // zoom=15: 底部高度为0
            16, ['coalesce', ['get', 'render_min_height'], 0]  // zoom=16: 使用底部高度（默认0）
          ],
          // 建筑不透明度（可选，用于更好的视觉效果）
          'fill-extrusion-opacity': 0.8
        }
      },
      firstSymbolId // 插入到符号图层之前
    );
  }

  _addCommonControls() {
    this.mapBase.addStandardControls();
    this.mapBase.addProjectionControl(); // 添加投影切换按钮
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
    const map = this.map; // 定义局部变量以便在回调中使用

    // 动态从当前底图样式中提取一个正在使用的有效字体
    // 这确保了无论使用什么瓦片服务商（本地、Stadia、MapTiler等）都能正常显示
    const getWorkingFont = () => {
      const style = map.getStyle();
      if (style && style.layers) {
        for (const layer of style.layers) {
          // 只查找 symbol 类型的图层，它们有 text-font 属性
          if (layer.type === "symbol" && layer.layout) {
            const textFont = layer.layout["text-font"];
            // 样式中的 text-font 可能是数组（直接值）或表达式
            if (Array.isArray(textFont) && textFont.length > 0 && typeof textFont[0] === "string") {
              // 确保不是 MapLibre 表达式（表达式数组第一个元素通常是 "literal", "step", "match" 等关键字）
              const expressionKeywords = ["literal", "step", "match", "case", "coalesce", "interpolate", "get", "concat"];
              if (!expressionKeywords.includes(textFont[0])) {
                console.log("[OTNMap] Extracted working font from basemap:", textFont[0]);
                return textFont; // 返回整个字体栈
              }
            }
          }
        }
      }
      console.warn("[OTNMap] Could not extract font from basemap, using fallback.");
      // 回退：如果无法提取，使用通用的后备字体
      return this.config.useLocalBasemap ? ["Open Sans Regular", "Arial Unicode MS Regular"] : ["Stadia Regular"];
    };

    // 直接根据底图类型选择字体，不依赖复杂的提取逻辑
    // 本地底图使用 Open Sans，在线底图尝试 Noto Sans Regular
    let fontStack;
    if (this.config.useLocalBasemap) {
      fontStack = ["Open Sans Regular", "Arial Unicode MS Regular"];
      console.log("[OTNMap] Using local basemap font: Open Sans Regular");
    } else {
      // 尝试多种常见字体
      fontStack = ["Noto Sans Regular", "Open Sans Regular", "Arial Unicode MS Regular"];
      console.log("[OTNMap] Using online basemap font: Noto Sans Regular");
    }

    const TOTAL_DISTANCE_SOURCE = "measures-total-distance";
    const TOTAL_DISTANCE_LAYER = "measures-total-distance-labels";

    // 格式化距离显示
    const formatDistance = (meters) => {
      if (meters >= 1000) {
        return (meters / 1000).toFixed(2) + " 公里";
      }
      return meters.toFixed(0) + " m";
    };

    // 计算 LineString 的总长度（米）
    const calculateLineLength = (coords) => {
      let total = 0;
      for (let i = 1; i < coords.length; i++) {
        const [lon1, lat1] = coords[i - 1];
        const [lon2, lat2] = coords[i];
        // Haversine 公式计算两点距离
        const R = 6371000; // 地球半径（米）
        const dLat = ((lat2 - lat1) * Math.PI) / 180;
        const dLon = ((lon2 - lon1) * Math.PI) / 180;
        const a =
          Math.sin(dLat / 2) * Math.sin(dLat / 2) +
          Math.cos((lat1 * Math.PI) / 180) *
          Math.cos((lat2 * Math.PI) / 180) *
          Math.sin(dLon / 2) *
          Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        total += R * c;
      }
      return total;
    };

    // 初始化总距离图层（确保只添加一次）
    const initTotalDistanceLayer = () => {
      if (!map.getSource(TOTAL_DISTANCE_SOURCE)) {
        map.addSource(TOTAL_DISTANCE_SOURCE, {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
        map.addLayer({
          id: TOTAL_DISTANCE_LAYER,
          type: "symbol",
          source: TOTAL_DISTANCE_SOURCE,
          layout: {
            "text-field": ["get", "label"],
            "text-font": fontStack,
            "text-size": 14,
            "text-anchor": "top",
            "text-offset": [0, 1],
            "text-allow-overlap": true,
            "text-ignore-placement": true,
            "text-pitch-alignment": "viewport", // 确保在地球模式下文字面朝屏幕
            "text-rotation-alignment": "viewport",
          },
          paint: {
            "text-color": "#1565C0",
            "text-halo-color": "#fff",
            "text-halo-width": 2,
          },
        });
      }
    };

    // 使用 requestAnimationFrame 防抖
    let animationFrameId = null;

    const measuresControl = new MeasuresControl({
      lang: {
        areaMeasurementButtonTitle: "测量面积",
        lengthMeasurementButtonTitle: "测量距离",
        clearMeasurementsButtonTitle: "清除测量",
      },
      units: "metric",
      style: {
        text: {
          radialOffset: 0.9,
          letterSpacing: 0.05,
          color: "#D20C0C",
          haloColor: "#fff",
          haloWidth: 1,
          // 不设置 font，使用插件默认值
        },
        common: {
          midPointRadius: 3,
          midPointColor: "#D20C0C",
          midPointHaloRadius: 5,
          midPointHaloColor: "#FFF",
        },
        areaMeasurement: {
          fillColor: "#D20C0C",
          fillOutlineColor: "#D20C0C",
          fillOpacity: 0.1,
          lineWidth: 2,
        },
        lengthMeasurement: {
          lineWidth: 2,
          lineColor: "#D20C0C",
        },
      },
      // 渲染回调：在每条线的终点显示总距离
      onRender: (features) => {
        // 如果有挂起的更新，取消它
        if (animationFrameId) {
          cancelAnimationFrame(animationFrameId);
        }

        // 安排新的更新
        animationFrameId = requestAnimationFrame(() => {
          // 确保图层存在
          if (!map.getSource(TOTAL_DISTANCE_SOURCE)) {
            initTotalDistanceLayer();
          }

          const totalLabels = [];
          if (features && features.features) {
            // 获取绘图控件的原始 features
            const drawFeatures =
              measuresControl._drawCtrl?.getAll?.()?.features || [];
            drawFeatures.forEach((feature) => {
              if (feature.geometry.type === "LineString") {
                const coords = feature.geometry.coordinates;
                if (coords.length >= 2) {
                  const totalLength = calculateLineLength(coords);
                  const endPoint = coords[coords.length - 1];
                  totalLabels.push({
                    type: "Feature",
                    properties: {
                      label: "总计: " + formatDistance(totalLength),
                    },
                    geometry: {
                      type: "Point",
                      coordinates: endPoint,
                    },
                  });
                }
              }
            });
          }

          // 更新总距离标签数据
          const source = map.getSource(TOTAL_DISTANCE_SOURCE);
          if (source) {
            source.setData({
              type: "FeatureCollection",
              features: totalLabels,
            });
          }

          // 修复插件图层字体：确保使用 fontStack 覆盖插件默认字体
          if (map.getLayer("layer-draw-labels")) {
            const currentFont = map.getLayoutProperty("layer-draw-labels", "text-font");
            // 只在第一次检测到默认字体时进行覆盖
            if (currentFont && currentFont[0] && currentFont[0].includes("Klokantech")) {
              console.log("[OTNMap] Overriding plugin layer font from", currentFont[0], "to", fontStack[0]);
              map.setLayoutProperty("layer-draw-labels", "text-font", fontStack);
            }
          }
        });
      },
    });

    // Monkey patch: 'km' -> '公里'
    const originalFormatMetric =
      measuresControl._formatToMetricSystem.bind(measuresControl);
    measuresControl._formatToMetricSystem = function (value) {
      try {
        const text = originalFormatMetric(value);
        return text ? text.replace("km", "公里") : text;
      } catch (e) {
        return value;
      }
    };

    this.mapBase.addControl(measuresControl, "top-right");

    // 控件添加后，立即尝试修复插件图层字体
    // 使用短延时确保插件已完成图层创建
    setTimeout(() => {
      if (map.getLayer("layer-draw-labels")) {
        console.log("[OTNMap] Patching plugin layer font to:", fontStack);
        map.setLayoutProperty("layer-draw-labels", "text-font", fontStack);
      }
    }, 100);

    // 确保在地图加载完成后初始化（防止过早添加）
    if (map.loaded()) {
      initTotalDistanceLayer();
    } else {
      map.on("load", initTotalDistanceLayer);
    }
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

  /**
   * 渲染调试面板 (性能监控)
   */
  _renderDebugPanel() {
    if (!window.OTNPerf) return;

    // 再次标记渲染时间
    window.OTNPerf.mark('render_debug_start');

    const perf = window.OTNPerf;
    const nav = perf.getNavigationTiming ? perf.getNavigationTiming() : null;

    let stats = [];

    // 添加网络计时
    if (nav) {
      stats.push(
        { label: '后端响应 (TTFB)', duration: nav.ttfb },
        { label: '内容下载', duration: nav.download },
        { label: 'DOM解析', duration: nav.dom_processing },
        { label: '----------------', duration: '' },
      );
    }

    stats.push(
      { label: '页面初始化', duration: perf.getDuration('page_start', 'init_start') },
      { label: '地图实例', duration: perf.getDuration('init_start', 'map_instance_created') },
      { label: '异步加载', duration: perf.getDuration('map_instance_created', 'map_load_event') },
      { label: '共享图层', duration: perf.getDuration('map_load_event', 'shared_layers_done') },
      { label: '插件初始化', duration: perf.getDuration('shared_layers_done', 'mode_plugin_done') },
      { label: '总耗时 (JS)', duration: perf.getDuration('page_start', 'mode_plugin_done') },
    );

    const container = document.createElement('div');
    container.className = 'debug-perf-panel';

    let html = '<div class="debug-perf-header">性能监控</div><div class="debug-perf-body">';
    stats.forEach(item => {
      // 处理分隔线
      if (item.label.startsWith('--')) {
        html += `<div style="border-bottom: 1px dashed #555; margin: 4px 0;"></div>`;
        return;
      }
      const val = item.duration === '' ? '' : item.duration + ' ms';
      html += `
        <div class="debug-perf-row">
          <span class="label">${item.label}</span>
          <span class="value">${val}</span>
        </div>
      `;
    });
    html += '</div>';

    container.innerHTML = html;

    // 添加到地图容器中 (左下角，避开 Logo)
    const mapContainer = this.map.getContainer();
    mapContainer.appendChild(container);

    // 为容器添加标识类，用于 CSS 调整其他组件位置（如故障统计窗口）
    mapContainer.classList.add('has-debug-panel');

    console.log('[OTNPerf] Debug panel rendered');
  }
}

// 暴露全局注册函数供插件使用
window.initOTNMap = OTNMapCore.register;

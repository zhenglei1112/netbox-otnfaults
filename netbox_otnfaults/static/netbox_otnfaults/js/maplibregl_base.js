/**
 * NetBox MapLibre GL 基础类
 * 封装通用的地图操作和配置。
 */

class NetBoxMapBase {
  constructor() {
    this.map = null;
    this.svgIcons = {
      home: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>',
      heatmap:
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>',
      marker:
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>',
      network:
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="2"/><circle cx="16" cy="8" r="2"/><circle cx="12" cy="16" r="2"/><line x1="8" y1="8" x2="16" y2="8"/><line x1="8" y1="8" x2="12" y2="16"/><line x1="16" y1="8" x2="12" y2="16"/></svg>',
      filter:
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>',
      projection_globe:
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
      projection_flat:
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg>',
    };
  }

  /**
   * 初始化地图
   * @param {string} containerId - 地图容器的 HTML ID
   * @param {string} apiKey - Stadia Maps API 密钥
   * @param {Array} center - 中心点 [经度, 纬度]，默认使用全局配置
   * @param {number} zoom - 缩放级别，默认使用全局配置
   */
  init(containerId, apiKey, center, zoom) {
    // 使用传入的配置或全局配置
    const config = window.OTNFaultMapConfig || {};
    center = center || config.mapCenter || [112.53, 33.0];
    zoom = zoom || config.mapZoom || 4.2;

    // 记录是否使用本地底图（供后续方法判断）
    this.useLocalBasemap = config.useLocalBasemap || false;

    if (typeof maplibregl === "undefined") {
      throw new Error("MapLibre GL 库未加载。");
    }

    let mapOptions = {
      container: containerId,
      center: center,
      zoom: zoom,
    };


    // 始终注册 pmtiles 协议（用于加载路径数据）
    if (typeof pmtiles !== "undefined") {
      const protocol = new pmtiles.Protocol();
      maplibregl.addProtocol("pmtiles", protocol.tile);
    } else {
      console.warn("pmtiles 库未加载，路径数据可能无法正常加载");
    }

    // 根据配置选择底图
    if (this.useLocalBasemap) {
      // 使用本地底图样式
      mapOptions.style = this._getLocalBasemapStyle(config);
    } else {
      // 使用网络底图
      mapOptions.style =
        "https://tiles.stadiamaps.com/styles/alidade_smooth.json?api_key=" +
        apiKey;
    }

    this.map = new maplibregl.Map(mapOptions);

    return this.map;
  }

  /**
   * 获取本地底图样式配置（样式来自 test.html）
   * @param {Object} config - 全局配置对象
   * @returns {Object} MapLibre GL 样式对象
   */
  _getLocalBasemapStyle(config) {
    return {
      version: 8,
      glyphs:
        config.localGlyphsUrl ||
        "/maps/fonts/{fontstack}/{range}.pbf",
      sources: {
        china_local: {
          type: "vector",
          url:
            "pmtiles://" +
            (config.localTilesUrl ||
              "/maps/china.pmtiles"),
          attribution: "© OpenStreetMap",
        },
        // OTN 路径数据源现在统一在 otnfault_map_app.js 中添加
      },
      layers: [
        // === 1. 背景 (海洋颜色) - 冷淡的灰蓝色 ===
        {
          id: "background",
          type: "background",
          paint: { "background-color": "#cbd2d3" },
        },
        // === 2. 陆地 - 极浅的暖灰色 ===
        {
          id: "landuse_base",
          type: "fill",
          source: "china_local",
          "source-layer": "landuse",
          paint: { "fill-color": "#f5f5f0" },
        },
        // === 3. 绿地/公园 - 低饱和度浅绿 ===
        {
          id: "landuse_green",
          type: "fill",
          source: "china_local",
          "source-layer": "landuse",
          filter: ["in", "class", "park", "grass", "wood", "scrub"],
          paint: {
            "fill-color": "#dbece0",
            "fill-opacity": 0.6,
          },
        },
        // === 4. 水系 - 与背景融合或稍深 ===
        {
          id: "water",
          type: "fill",
          source: "china_local",
          "source-layer": "water",
          paint: { "fill-color": "#cbd2d3" },
        },
        // === 5. 道路 (底层描边) - 浅灰色 ===
        {
          id: "roads_casing",
          type: "line",
          source: "china_local",
          "source-layer": "transportation",
          minzoom: 5,
          paint: {
            "line-color": "#cfcfcf",
            "line-width": {
              stops: [
                [5, 1],
                [10, 4],
                [15, 8],
              ],
            },
          },
        },
        // === 6. 道路 (顶层填充) - 纯白色 ===
        {
          id: "roads_inner",
          type: "line",
          source: "china_local",
          "source-layer": "transportation",
          minzoom: 5,
          paint: {
            "line-color": "#ffffff",
            "line-width": {
              stops: [
                [5, 0.5],
                [10, 2.5],
                [15, 6],
              ],
            },
          },
        },
        // === 7. 边界线 - 柔和的虚线 ===
        {
          id: "boundary",
          type: "line",
          source: "china_local",
          "source-layer": "boundary",
          paint: {
            "line-color": "#aeb0b5",
            "line-width": 1,
            "line-dasharray": [2, 2],
          },
        },
        // === 8. 城市名称 - 深蓝灰色，高可读性 ===
        {
          id: "place_label",
          type: "symbol",
          source: "china_local",
          "source-layer": "place",
          minzoom: 3,
          layout: {
            "text-field": "{name}",
            "text-size": {
              stops: [
                [3, 10],
                [8, 14],
              ],
            },
            "text-font": ["Open Sans Regular"],
            "text-max-width": 8,
          },
          paint: {
            "text-color": "#434850",
            "text-halo-color": "#ffffff",
            "text-halo-width": 2,
            "text-halo-blur": 0.5,
          },
        },
        // OTN 路径图层现在统一在 otnfault_map_app.js 中添加
      ],
    };
  }

  /**
   * 添加标准控件（导航、全屏）
   */
  addStandardControls() {
    const navControl = new maplibregl.NavigationControl();
    this.map.addControl(navControl);

    // 设置导航控件按钮的中文 hint
    const navContainer = navControl._container;
    if (navContainer) {
      const zoomInBtn = navContainer.querySelector(".maplibregl-ctrl-zoom-in");
      const zoomOutBtn = navContainer.querySelector(
        ".maplibregl-ctrl-zoom-out"
      );
      const compassBtn = navContainer.querySelector(".maplibregl-ctrl-compass");

      if (zoomInBtn) zoomInBtn.title = "放大";
      if (zoomOutBtn) zoomOutBtn.title = "缩小";
      if (compassBtn) compassBtn.title = "重置北向";
    }

    const fullscreenControl = new maplibregl.FullscreenControl({
      container: document.querySelector("#" + this.map.getContainer().id),
    });
    this.map.addControl(fullscreenControl);

    // 设置全屏控件按钮的中文 hint，并使用 MutationObserver 防止被覆盖
    const fullscreenContainer = fullscreenControl._container;
    if (fullscreenContainer) {
      const fullscreenBtn = fullscreenContainer.querySelector(
        ".maplibregl-ctrl-fullscreen"
      );
      if (fullscreenBtn) {
        // 设置初始中文 hint
        fullscreenBtn.title = "全屏";

        // 使用 MutationObserver 监听 title 属性变化，强制覆盖为中文
        const observer = new MutationObserver((mutations) => {
          mutations.forEach((mutation) => {
            if (
              mutation.type === "attributes" &&
              mutation.attributeName === "title"
            ) {
              const currentTitle = fullscreenBtn.title;
              if (currentTitle === "Enter fullscreen") {
                fullscreenBtn.title = "全屏";
              } else if (currentTitle === "Exit fullscreen") {
                fullscreenBtn.title = "退出全屏";
              }
            }
          });
        });

        observer.observe(fullscreenBtn, {
          attributes: true,
          attributeFilter: ["title"],
        });
      }
    }
  }

  /**
   * 添加 Home 控件以重置视野
   */
  addHomeControl(position = "top-right") {
    // 保存引用供内部类使用
    const base = this;

    class HomeControl {
      constructor() {
        // 使用全局配置的中心点和缩放级别
        const config = window.OTNFaultMapConfig || {};
        this.initialCenter = config.mapCenter || [112.53, 33.0];
        this.initialZoom = config.mapZoom || 4.2;
        this.targetBounds = null; // 支持动态设置目标边界
      }

      onAdd(map) {
        this.map = map;
        this.container = document.createElement("div");
        this.container.className = "maplibregl-ctrl maplibregl-ctrl-group";

        this.homeButton = document.createElement("button");
        this.homeButton.className = "maplibregl-ctrl-icon";
        this.homeButton.type = "button"; // 明确类型防止表单提交
        // 使用 base.svgIcons 访问外部属性
        this.homeButton.innerHTML = base.svgIcons.home;
        this.homeButton.title =
          "恢复初始视野（包括比例尺、视野、北向、俯仰等）";

        // 绑定点击事件，确保 this 指向 HomeControl 实例
        this.homeButton.addEventListener("click", () => {
          this.goHome();
        });

        this.container.appendChild(this.homeButton);
        return this.container;
      }

      onRemove() {
        this.container.parentNode.removeChild(this.container);
        this.map = undefined;
      }

      goHome() {
        if (this.targetBounds) {
          // 如果设置了动态边界（如路径模式），则适配边界
          this.map.fitBounds(this.targetBounds, {
            padding: 80,
            maxZoom: 12,
            pitch: 0,
            bearing: 0,
            essential: true,
          });
        } else {
          // 默认逻辑：回到全局视图
          this.map.flyTo({
            center: this.initialCenter,
            zoom: this.initialZoom,
            bearing: 0,
            pitch: 0,
            essential: true,
          });
          this.map.setProjection({ type: "globe" });
        }
      }
    }

    this.homeControl = new HomeControl();
    this.map.addControl(this.homeControl, position);
  }

  /**
   * 添加投影切换控件 (Globe <-> Mercator)
   */
  addProjectionControl(position = "top-right") {
    const base = this;

    class ProjectionControl {
      onAdd(map) {
        this.map = map;
        this.container = document.createElement("div");
        this.container.className = "maplibregl-ctrl maplibregl-ctrl-group";
        this.button = document.createElement("button");
        this.button.className = "maplibregl-ctrl-icon";
        this.button.type = "button";

        // 绑定点击事件
        this.button.addEventListener("click", () => this.toggleProjection());

        this.container.appendChild(this.button);

        // 初始化图标和提示
        this.updateUI();

        // 监听投影变化以同步 UI (防止外部修改导致不同步)
        // MapLibre 目前没有明确的 'projection' 事件，但我们可以依赖点击更新
        // 或者在 render 中检查? 不，简单处理即可。

        return this.container;
      }

      onRemove() {
        this.container.parentNode.removeChild(this.container);
        this.map = undefined;
      }

      toggleProjection() {
        const props = this.map.getProjection && this.map.getProjection();
        const currentProjection = (props && props.type) ? props.type : 'mercator';
        const newProjection = currentProjection === 'globe' ? 'mercator' : 'globe';
        this.map.setProjection({ type: newProjection });
        // 立即更新 UI，虽然 setProjection 可能是异步动画，但状态通常立即变更
        // 稍微延迟一下确保 getProjection 获取到新值，或者直接根据 newProjection 更新
        setTimeout(() => this.updateUI(), 100);
      }

      updateUI() {
        if (!this.map) return;
        const props = this.map.getProjection && this.map.getProjection();
        const currentProjection = (props && props.type) ? props.type : 'mercator';

        if (currentProjection === 'globe') {
          // 当前是地球，显示切换到平面的图标
          this.button.innerHTML = base.svgIcons.projection_flat;
          this.button.title = "切换为平面地图 (Mercator)";
        } else {
          // 当前是平面，显示切换到地球的图标
          this.button.innerHTML = base.svgIcons.projection_globe;
          this.button.title = "切换为地球模式 (Globe)";
        }
      }
    }

    this.projectionControl = new ProjectionControl();
    this.map.addControl(this.projectionControl, position);
  }

  /**
   * 手动更新投影控件图标状态
   */
  updateProjectionIcon() {
    if (this.projectionControl && this.projectionControl.updateUI) {
      this.projectionControl.updateUI();
    }
  }

  /**
   * 设置 Home 控件的动态目标边界
   * @param {Object} bounds - LngLatBounds 对象
   */
  setHomeBounds(bounds) {
    if (this.homeControl) {
      this.homeControl.targetBounds = bounds;
    }
  }

  /**
   * 设置地图语言为中文
   */
  setLanguageToChinese() {
    const layers = this.map.getStyle().layers;
    layers.forEach((layer) => {
      if (layer.layout && layer.layout["text-field"]) {
        this.map.setLayoutProperty(layer.id, "text-field", [
          "coalesce",
          ["get", "name:zh"],
          ["get", "name"],
        ]);
      }
    });
  }

  /**
   * 强化中国边界显示
   * 尝试找到省级边界图层并加深加粗
   */
  /**
   * 强化中国边界显示
   * 尝试找到省级边界图层并加深加粗
   */
  emphasizeChinaBoundaries() {
    const style = this.map.getStyle();
    if (!style || !style.layers) return;

    style.layers.forEach((layer) => {
      // 匹配常见的行政边界图层名称模式 (admin, boundary)
      if (
        (layer.id.indexOf("admin") !== -1 ||
          layer.id.indexOf("boundary") !== -1) &&
        layer.type === "line"
      ) {
        // 排除可能是国界 (level-0, level-2) 的图层，专注更细粒度的边界
        // 如果图层ID包含 '0' 或 '2' 但不包含 'province'，跳过（可选策略，先全量尝试）

        // 强制确保可见
        if (this.map.getLayoutProperty(layer.id, "visibility") === "none") {
          this.map.setLayoutProperty(layer.id, "visibility", "visible");
        }

        this.map.setPaintProperty(layer.id, "line-width", [
          "interpolate",
          ["linear"],
          ["zoom"],
          3,
          0.5,
          5,
          2.0, // 增加到 2.0
          10,
          4.0,
        ]);

        // 设置为明显的深灰色，确保不透明
        this.map.setPaintProperty(layer.id, "line-color", "#555555");
        this.map.setPaintProperty(layer.id, "line-opacity", 1.0);
      }
    });
  }

  /**
   * 过滤地图标签（隐藏道路、小城镇）
   */
  filterLabels() {
    const layers = this.map.getStyle().layers;
    layers.forEach((layer) => {
      if (layer.type === "symbol") {
        // 隐藏道路标签
        if (
          layer.id.includes("road") ||
          layer.id.includes("highway") ||
          layer.id.includes("street") ||
          layer.id.includes("route") ||
          layer.id.includes("motorway") ||
          layer.id.includes("trunk") ||
          layer.id.includes("primary") ||
          layer.id.includes("secondary") ||
          layer.id.includes("tertiary") ||
          layer.id.includes("path") ||
          layer.id.includes("track") ||
          layer.id.includes("service") ||
          layer.id.includes("pedestrian") ||
          layer.id.includes("cycleway") ||
          layer.id.includes("footway") ||
          layer.id.includes("steps") ||
          layer.id.includes("ferry") ||
          layer.id.includes("rail") ||
          layer.id.includes("transit")
        ) {
          this.map.setLayoutProperty(layer.id, "visibility", "none");
        }

        // 隐藏小居民点
        if (
          (layer.id.includes("place") ||
            layer.id.includes("settlement") ||
            layer.id.includes("label")) &&
          (layer.id.includes("village") ||
            layer.id.includes("town") ||
            layer.id.includes("hamlet") ||
            layer.id.includes("suburb") ||
            layer.id.includes("neighbourhood") ||
            layer.id.includes("neighborhood") ||
            layer.id.includes("quarter") ||
            layer.id.includes("locality") ||
            layer.id.includes("isolated_dwelling"))
        ) {
          this.map.setLayoutProperty(layer.id, "visibility", "none");
        }
      }
    });
  }

  /**
   * 设置投影类型
   * @param {string} type - 'globe' 或 'mercator'
   */
  setProjection(type) {
    this.map.setProjection({ type: type });
  }

  /**
   * 添加 GeoJSON 数据源
   */
  addGeoJsonSource(id, data, options = {}) {
    this.map.addSource(id, {
      type: "geojson",
      data: data,
      ...options,
    });
  }

  /**
   * 添加图层
   */
  addLayer(config, beforeId) {
    this.map.addLayer(config, beforeId);
  }

  /**
   * 添加控件
   */
  addControl(control, position) {
    this.map.addControl(control, position);
  }

  /**
   * 设置布局属性
   */
  setLayoutProperty(layerId, prop, value) {
    if (this.map.getLayer(layerId)) {
      this.map.setLayoutProperty(layerId, prop, value);
    }
  }

  /**
   * 自适应地图边界
   */
  fitBounds(bounds, options = {}) {
    this.map.fitBounds(bounds, options);
  }

  /**
   * 添加 SVG 图标
   * @param {string} imageId - 图片 ID
   * @param {string} svgString - SVG 内容字符串
   * @param {Object} options - addImage 选项 (可选)
   */
  addSvgIcon(imageId, svgString, options = {}) {
    const img = new Image();
    img.onload = () => {
      if (!this.map.hasImage(imageId)) {
        this.map.addImage(imageId, img, options);
      }
    };
    img.src =
      "data:image/svg+xml;base64," +
      btoa(unescape(encodeURIComponent(svgString)));
  }

  /**
   * 添加标记
   */
  addMarker(lng, lat, options = {}) {
    const marker = new maplibregl.Marker({ color: options.color }).setLngLat([
      lng,
      lat,
    ]);

    if (options.popup) {
      const popup = new maplibregl.Popup(options.popupOptions || {}).setHTML(
        options.popup
      );
      marker.setPopup(popup);
    }

    marker.addTo(this.map);
    return marker;
  }

  /**
   * 显示加载覆盖层的辅助方法
   */
  static showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // 防止重复添加
    if (document.getElementById(containerId + "-loading")) return;

    const overlay = document.createElement("div");
    overlay.id = containerId + "-loading";
    overlay.className = "map-overlay map-loading";
    overlay.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <div class="mt-3">正在加载地图数据...</div>
        `;
    container.appendChild(overlay);
    return overlay;
  }

  /**
   * 隐藏加载覆盖层的辅助方法
   */
  static hideLoading(containerId) {
    const overlay = document.getElementById(containerId + "-loading");
    if (overlay && overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
  }

  /**
   * 初始化高速公路盾标显示
   * 支持国家高速（G开头）和省级高速（S开头），使用灰度色调与底图风格一致
   */
  initHighwayShields() {
    const map = this.map;

    // 盾标 SVG 内联数据 - 浅灰色调，与底图风格一致
    // 国家高速：浅灰底 + 稍深灰顶（柔和对比）
    const shieldNationalSvg = `<svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="36" height="36" rx="4" fill="#b8bcc4"/>
      <path d="M6 2h28a4 4 0 0 1 4 4v4H2V6a4 4 0 0 1 4-4z" fill="#9ca3af"/>
      <rect x="2" y="2" width="36" height="36" rx="4" fill="none" stroke="#d1d5db" stroke-width="1" opacity="0.6"/>
    </svg>`;

    // 省级高速：更浅灰底 + 浅米灰顶
    const shieldProvincialSvg = `<svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="36" height="36" rx="4" fill="#c9ccd2"/>
      <path d="M6 2h28a4 4 0 0 1 4 4v4H2V6a4 4 0 0 1 4-4z" fill="#e5e7eb"/>
      <rect x="2" y="2" width="36" height="36" rx="4" fill="none" stroke="#e5e7eb" stroke-width="1" opacity="0.6"/>
    </svg>`;

    /**
     * 将 SVG 字符串转换为 Image 并添加到地图
     * @param {string} svgString - SVG 内容
     * @param {string} imageId - 地图中的图片 ID
     */
    const addShieldImage = (svgString, imageId) => {
      const img = new Image(40, 40);
      img.onload = () => {
        if (!map.hasImage(imageId)) {
          map.addImage(imageId, img, {
            // content 定义文字显示的矩形范围 [x1, y1, x2, y2]
            // 避开顶部的灰条区域（y从12开始）
            content: [4, 12, 36, 36],
            // stretchX 定义横向哪段可以拉伸（中间位置）
            stretchX: [[10, 30]],
            // stretchY 定义纵向哪段可以拉伸（底色部分）
            stretchY: [[15, 30]],
          });
        }
      };
      img.onerror = (e) => {
        console.error(`高速盾标图标加载失败: ${imageId}`, e);
      };
      // 使用 Base64 编码的 SVG
      img.src =
        "data:image/svg+xml;base64," +
        btoa(unescape(encodeURIComponent(svgString)));
    };

    // 加载盾标图标
    addShieldImage(shieldNationalSvg, "shield-cn-national");
    addShieldImage(shieldProvincialSvg, "shield-cn-provincial");

    // 延迟添加图层（等待图标加载完成）
    setTimeout(() => {
      // 检查数据源是否存在（Stadia Maps 使用 'openmaptiles'）
      const sourceId = map.getSource("openmaptiles")
        ? "openmaptiles"
        : map.getSource("china_local")
          ? "china_local"
          : null;

      if (!sourceId) {
        console.warn("未找到合适的数据源用于高速盾标");
        return;
      }

      // 检查 transportation_name 图层是否存在
      const sourceLayerId =
        sourceId === "openmaptiles" ? "transportation_name" : "transportation";

      // 查找插入位置：在城市名称标签之下
      let beforeLayerId = null;
      const layers = map.getStyle().layers;
      for (const layer of layers) {
        if (layer.id.includes("place") && layer.type === "symbol") {
          beforeLayerId = layer.id;
          break;
        }
      }

      // 避免重复添加
      if (map.getLayer("highway-shields")) {
        return;
      }

      try {
        map.addLayer(
          {
            id: "highway-shields",
            type: "symbol",
            source: sourceId,
            "source-layer": sourceLayerId,
            filter: ["has", "ref"],
            minzoom: 6, // 保持低缩放级别可见
            layout: {
              "symbol-placement": "point", // 使用点放置，保持盾标始终正向朝上
              "symbol-spacing": 2000, // 极大间距，确保同一编号在视口中少于5个
              "icon-padding": 50, // 增加图标间的最小像素距离

              // 排序优先级：G（国家高速）优先于 S（省级高速）
              // 数值越小优先级越高
              "symbol-sort-key": [
                "match",
                ["slice", ["get", "ref"], 0, 1],
                "G",
                1, // 国家高速优先级最高
                "S",
                2, // 省级高速次之
                3, // 其他默认最低
              ],

              // 图标和文字始终保持正向
              "icon-rotation-alignment": "viewport",
              "text-rotation-alignment": "viewport",
              "icon-pitch-alignment": "viewport",

              // 根据编号首字母选择图标
              "icon-image": [
                "match",
                ["slice", ["get", "ref"], 0, 1],
                "G",
                "shield-cn-national",
                "S",
                "shield-cn-provincial",
                "shield-cn-national", // 默认值
              ],

              // 关键属性：让图标自动包裹文字
              "icon-text-fit": "both",
              "icon-text-fit-padding": [2, 5, 2, 5],

              // 文字设置：只显示编号部分（截取前6位，适应如 G1011 等）
              "text-field": [
                "case",
                [">=", ["length", ["get", "ref"]], 6],
                ["slice", ["get", "ref"], 0, 6],
                ["get", "ref"],
              ],
              "text-font": ["Open Sans Bold", "Noto Sans Regular"],
              "text-size": [
                "interpolate",
                ["linear"],
                ["zoom"],
                8,
                9,
                12,
                11,
                16,
                12,
              ],
              "text-anchor": "center",
              "text-letter-spacing": 0.05,

              "icon-allow-overlap": false,
              "text-allow-overlap": false,
              "icon-ignore-placement": false,
              "text-ignore-placement": false,

              // 缩放控制
              "icon-size": [
                "interpolate",
                ["linear"],
                ["zoom"],
                8,
                0.7,
                12,
                0.9,
                16,
                1.0,
              ],
            },
            paint: {
              "text-color": "#ffffff",
              "text-halo-color": "rgba(0,0,0,0.15)",
              "text-halo-width": 1,
            },
          },
          beforeLayerId
        );
      } catch (e) {
        console.error("高速盾标图层添加失败:", e);
      }
    }, 500); // 等待图标加载
  }

  /**
   * 显示错误覆盖层的辅助方法
   */
  static showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // 如果存在加载层则移除
    this.hideLoading(containerId);

    const overlay = document.createElement("div");
    overlay.className = "map-overlay map-error";
    overlay.innerHTML = `
              <h5>地图加载失败</h5>
              <p>${message}</p>
              <ul>
                  <li>请检查网络连接</li>
                  <li>确保API密钥有效</li>
                  <li>刷新页面重试</li>
                  <li>如果问题持续，请联系管理员</li>
              </ul>
              <button class="btn btn-primary mt-3" onclick="window.location.reload()">
                  刷新页面
              </button>
          `;
    container.appendChild(overlay);
  }
}

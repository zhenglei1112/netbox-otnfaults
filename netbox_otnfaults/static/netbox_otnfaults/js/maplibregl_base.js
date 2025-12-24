/**
 * NetBox Mapbox GL 基础类
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
    };
  }

  /**
   * 初始化地图
   * @param {string} containerId - 地图容器的 HTML ID
   * @param {string} accessToken - Mapbox Access Token
   * @param {Array} center - 中心点 [经度, 纬度]，默认使用全局配置
   * @param {number} zoom - 缩放级别，默认使用全局配置
   */
  init(containerId, accessToken, center, zoom) {
    // 使用传入的配置或全局配置
    const config = window.OTNFaultMapConfig || {};
    center = center || config.mapCenter || [112.53, 33.0];
    zoom = zoom || config.mapZoom || 4.2;

    if (typeof mapboxgl === "undefined") {
      throw new Error("Mapbox GL 库未加载。");
    }

    // 设置 Mapbox Access Token
    mapboxgl.accessToken = accessToken;

    // 注意: Mapbox GL JS v3 不支持 addProtocol，PMTiles 需要使用其他方式加载
    // 路径数据将使用 GeoJSON 或 Mapbox Vector Tiles 替代
    console.log("Mapbox GL JS 模式：PMTiles 协议暂不可用");

    let mapOptions = {
      container: containerId,
      style: "mapbox://styles/mapbox/standard",  // 使用 Mapbox Standard 底图
      center: center,
      zoom: zoom,
    };

    this.map = new mapboxgl.Map(mapOptions);
    
    // 设置中文语言标签（确保在样式完全加载后执行）
    const self = this;
    const setupChineseLabels = () => {
      console.log('开始设置中文标签...');
      self._setChineseLabels();
    };
    
    // 延迟执行以确保样式完全加载
    this.map.on('load', () => {
      setTimeout(setupChineseLabels, 500);
    });

    return this.map;
  }
  
  /**
   * 设置地图标签为中文
   * 优先使用 mapbox-gl-language 插件，失败时遍历图层设置
   */
  _setChineseLabels() {
    // 方式1：使用 mapbox-gl-language 插件
    if (typeof MapboxLanguage !== 'undefined') {
      try {
        const language = new MapboxLanguage({
          defaultLanguage: 'zh-Hans'
        });
        this.map.addControl(language);
        console.log('已使用 MapboxLanguage 插件设置中文');
        return;
      } catch (e) {
        console.warn('MapboxLanguage 插件添加失败:', e.message);
      }
    }
    
    // 方式2：遍历图层手动设置（兜底方案）
    try {
      const style = this.map.getStyle();
      if (!style || !style.layers) return;
      
      let count = 0;
      style.layers.forEach(layer => {
        if (layer.type === 'symbol') {
          try {
            this.map.setLayoutProperty(layer.id, 'text-field', [
              'coalesce',
              ['get', 'name_zh-Hans'],
              ['get', 'name_zh'],
              ['get', 'name']
            ]);
            count++;
          } catch (e) {
            // 某些图层可能不支持此属性，忽略错误
          }
        }
      });
      
      if (count > 0) {
        console.log(`已手动设置 ${count} 个图层的语言为中文`);
      }
    } catch (e) {
      console.warn('设置中文标签失败:', e.message);
    }
  }

  /**
   * 添加标准控件（导航、全屏）
   */
  addStandardControls() {
    this.map.addControl(new mapboxgl.NavigationControl());
    this.map.addControl(
      new mapboxgl.FullscreenControl({
        container: document.querySelector("#" + this.map.getContainer().id),
      })
    );
  }

  /**
   * 添加 Home 控件以重置视野
   */
  addHomeControl(position = "top-right") {
    const svgIcons = this.svgIcons;

    class HomeControl {
      constructor(options) {
        this.options = options || {};
        // 使用全局配置的中心点和缩放级别
        const config = window.OTNFaultMapConfig || {};
        this.initialCenter = config.mapCenter || [112.53, 33.0];
        this.initialZoom = config.mapZoom || 4.2;
      }

      onAdd(map) {
        this.map = map;
        this.container = document.createElement("div");
        this.container.className = "mapboxgl-ctrl mapboxgl-ctrl-group";

        this.homeButton = document.createElement("button");
        this.homeButton.className = "mapboxgl-ctrl-icon";
        this.homeButton.innerHTML = svgIcons.home;
        this.homeButton.title =
          "恢复初始视野（包括比例尺、视野、北向、俯仰等）";
        this.homeButton.onclick = () => this.goHome();

        this.container.appendChild(this.homeButton);
        return this.container;
      }

      onRemove() {
        this.container.parentNode.removeChild(this.container);
        this.map = undefined;
      }

      goHome() {
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

    this.map.addControl(new HomeControl(), position);
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
   * 添加标记
   */
  addMarker(lng, lat, options = {}) {
    const marker = new mapboxgl.Marker({ color: options.color }).setLngLat([
      lng,
      lat,
    ]);

    if (options.popup) {
      const popup = new mapboxgl.Popup(options.popupOptions || {}).setHTML(
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

    const overlay = document.createElement("div");
    overlay.id = containerId + "-loading";
    overlay.className = "map-overlay map-loading";
    overlay.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <div class="mt-3">正在加载地图...</div>
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
                  <li>确保Access Token有效</li>
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


/**
 * NetBox MapLibre GL 基础类
 * 封装通用的地图操作和配置。
 */

class NetBoxMapBase {
    constructor() {
        this.map = null;
        this.svgIcons = {
            home: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>',
            heatmap: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>',
            marker: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>',
            network: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="2"/><circle cx="16" cy="8" r="2"/><circle cx="12" cy="16" r="2"/><line x1="8" y1="8" x2="16" y2="8"/><line x1="8" y1="8" x2="12" y2="16"/><line x1="16" y1="8" x2="12" y2="16"/></svg>',
            filter: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>'
        };
    }

    /**
     * 初始化地图
     * @param {string} containerId - 地图容器的 HTML ID
     * @param {string} apiKey - Stadia Maps API 密钥
     * @param {Array} center - 中心点 [经度, 纬度]
     * @param {number} zoom - 缩放级别
     */
    init(containerId, apiKey, center = [112.53, 33.00], zoom = 4.2) {
        if (typeof maplibregl === 'undefined') {
            throw new Error('MapLibre GL 库未加载。');
        }

        this.map = new maplibregl.Map({
            container: containerId,
            style: 'https://tiles.stadiamaps.com/styles/alidade_smooth.json?api_key=' + apiKey,
            center: center,
            zoom: zoom,
            projection: 'globe'  // 使用地球模式
        });

        return this.map;
    }

    /**
     * 添加标准控件（导航、全屏）
     */
    addStandardControls() {
        this.map.addControl(new maplibregl.NavigationControl());
        this.map.addControl(new maplibregl.FullscreenControl({
            container: document.querySelector('#' + this.map.getContainer().id)
        }));
    }

    /**
     * 添加 Home 控件以重置视野
     */
    addHomeControl(position = 'top-right') {
        const svgIcons = this.svgIcons;
        
        class HomeControl {
            constructor(options) {
                this.options = options || {};
                this.initialCenter = [112.53, 33.00]; // 南阳市中心
                this.initialZoom = 4.2;
            }

            onAdd(map) {
                this.map = map;
                this.container = document.createElement('div');
                this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group';

                this.homeButton = document.createElement('button');
                this.homeButton.className = 'maplibregl-ctrl-icon';
                this.homeButton.innerHTML = svgIcons.home;
                this.homeButton.title = '恢复初始视野（包括比例尺、视野、北向、俯仰等）';
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
                    essential: true
                });
                this.map.setProjection({ type: 'globe' });
            }
        }

        this.map.addControl(new HomeControl(), position);
    }

    /**
     * 设置地图语言为中文
     */
    setLanguageToChinese() {
        const layers = this.map.getStyle().layers;
        layers.forEach(layer => {
            if (layer.layout && layer.layout['text-field']) {
                this.map.setLayoutProperty(layer.id, 'text-field', ['coalesce', ['get', 'name:zh'], ['get', 'name']]);
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

        style.layers.forEach(layer => {
            // 匹配常见的行政边界图层名称模式 (admin, boundary)
            if ((layer.id.indexOf('admin') !== -1 || layer.id.indexOf('boundary') !== -1) && layer.type === 'line') {
                
                // 排除可能是国界 (level-0, level-2) 的图层，专注更细粒度的边界
                // 如果图层ID包含 '0' 或 '2' 但不包含 'province'，跳过（可选策略，先全量尝试）
                
                // 强制确保可见
                if (this.map.getLayoutProperty(layer.id, 'visibility') === 'none') {
                     this.map.setLayoutProperty(layer.id, 'visibility', 'visible');
                }

                this.map.setPaintProperty(layer.id, 'line-width', [
                    'interpolate', ['linear'], ['zoom'],
                    3, 0.5,
                    5, 2.0,  // 增加到 2.0
                    10, 4.0
                ]);
                
                // 设置为明显的深灰色，确保不透明
                this.map.setPaintProperty(layer.id, 'line-color', '#555555');
                this.map.setPaintProperty(layer.id, 'line-opacity', 1.0);
            }
        });
    }

    /**
     * 过滤地图标签（隐藏道路、小城镇）
     */
    filterLabels() {
        const layers = this.map.getStyle().layers;
        layers.forEach(layer => {
            if (layer.type === 'symbol') {
                // 隐藏道路标签
                if (layer.id.includes('road') || layer.id.includes('highway') || layer.id.includes('street') ||
                    layer.id.includes('route') || layer.id.includes('motorway') || layer.id.includes('trunk') ||
                    layer.id.includes('primary') || layer.id.includes('secondary') || layer.id.includes('tertiary') ||
                    layer.id.includes('path') || layer.id.includes('track') || layer.id.includes('service') ||
                    layer.id.includes('pedestrian') || layer.id.includes('cycleway') || layer.id.includes('footway') ||
                    layer.id.includes('steps') || layer.id.includes('ferry') || layer.id.includes('rail') ||
                    layer.id.includes('transit')) {
                    this.map.setLayoutProperty(layer.id, 'visibility', 'none');
                }

                // 隐藏小居民点
                if ((layer.id.includes('place') || layer.id.includes('settlement') || layer.id.includes('label')) &&
                    (layer.id.includes('village') || layer.id.includes('town') || layer.id.includes('hamlet') ||
                        layer.id.includes('suburb') || layer.id.includes('neighbourhood') || layer.id.includes('neighborhood') ||
                        layer.id.includes('quarter') || layer.id.includes('locality') || layer.id.includes('isolated_dwelling'))) {
                    this.map.setLayoutProperty(layer.id, 'visibility', 'none');
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
            type: 'geojson',
            data: data,
            ...options
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
        const marker = new maplibregl.Marker({ color: options.color })
            .setLngLat([lng, lat]);
        
        if (options.popup) {
            const popup = new maplibregl.Popup(options.popupOptions || {})
                .setHTML(options.popup);
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

        const overlay = document.createElement('div');
        overlay.id = containerId + '-loading';
        overlay.className = 'map-overlay map-loading';
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
        const overlay = document.getElementById(containerId + '-loading');
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

        const overlay = document.createElement('div');
        overlay.className = 'map-overlay map-error';
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

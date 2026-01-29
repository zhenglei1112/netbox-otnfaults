/**
 * 位置/路径地图模式插件
 * 处理 Location, Path, PathGroup 三种模式
 */

const LocationModePlugin = {
  core: null,
  map: null,
  config: null,
  mapBase: null,

  // 模式切换状态 (仅路径组模式使用)
  viewMode: 'detail', // 'detail' | 'simple'
  arcLayers: [],      // 弧形线图层ID列表

  init(core) {
    this.core = core;
    this.map = core.map;
    this.mapBase = core.mapBase;
    this.config = core.config;

    // 0. 初始化模式切换控件 (仅路径组模式)
    if (this.config.mode === 'pathgroup' && this.config.highlightSitesData && this.config.highlightSitesData.length > 0) {
      this._addViewModeControl();
    }

    // 0.5 初始化空间选择控件 (仅路径组模式, 需要 pathGroupId)
    if (this.config.mode === 'pathgroup' && this.config.pathGroupId) {
      this._initSpatialSelectControl();
    }

    // 1. 处理高亮路径 (Path / PathGroup 模式)
    if (this.config.highlightPathData) {
      this._initHighlightPath(this.config.highlightPathData);
    }

    // 1.5. 处理高亮站点 (PathGroup 模式)
    if (this.config.highlightSitesData && this.config.highlightSitesData.length > 0) {
      this._initHighlightSites(this.config.highlightSitesData);
    }

    // 2. 处理目标位置标记 (Location 模式)
    if (
      !this.config.highlightPathData &&
      this.config.targetLat &&
      this.config.targetLng
    ) {
      this._initTargetMarker(this.config.targetLat, this.config.targetLng);
    }

    // 3. 事件监听
    this._setupClickHandler();
  },

  _initHighlightSites(sitesData) {
    const map = this.map;
    const mapBase = this.mapBase;

    if (!sitesData || sitesData.length === 0) return;

    // 构建 GeoJSON FeatureCollection
    const features = sitesData.map(site => ({
      type: 'Feature',
      properties: {
        id: site.id,
        name: site.name,
        role: site.role,
        role_display: site.role_display,
        color: site.color,
        url: site.url
      },
      geometry: {
        type: 'Point',
        coordinates: [site.lng, site.lat]
      }
    }));

    // 添加数据源
    mapBase.addGeoJsonSource('highlight-sites', {
      type: 'FeatureCollection',
      features: features
    });

    // 添加圆形标记层 (底层光晕) - 使用站点颜色的光晕
    mapBase.addLayer({
      id: 'highlight-sites-glow',
      type: 'circle',
      source: 'highlight-sites',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 16, 6, 18, 10, 20],
        'circle-color': ['get', 'color'], // 使用站点角色颜色
        'circle-opacity': 0.4,
        'circle-blur': 0.5
      }
    });

    // 添加圆形标记层 (主层) - 使用更大的半径和更粗的描边
    mapBase.addLayer({
      id: 'highlight-sites-layer',
      type: 'circle',
      source: 'highlight-sites',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 10, 6, 12, 10, 14],
        'circle-color': ['get', 'color'],
        'circle-opacity': 1,
        'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 3, 3, 6, 3, 10, 4],
        'circle-stroke-color': '#FFFFFF'
      }
    });

    // 添加标签层
    mapBase.addLayer({
      id: 'highlight-sites-labels',
      type: 'symbol',
      source: 'highlight-sites',
      layout: {
        'text-field': ['get', 'name'],
        'text-size': 11,
        'text-offset': [0, 1.5],
        'text-anchor': 'top',
        'text-allow-overlap': false
      },
      paint: {
        'text-color': '#333333',
        'text-halo-color': '#ffffff',
        'text-halo-width': 1.5
      }
    });

    // 添加点击事件处理
    map.on('click', 'highlight-sites-layer', (e) => {
      if (!e.features || e.features.length === 0) return;
      const props = e.features[0].properties;
      const coords = e.features[0].geometry.coordinates;

      const html = `
        <div style="padding: 8px;">
          <b style="color: ${props.color};">${props.name}</b>
          <br><span style="font-size: 12px; padding: 2px 6px; background: ${props.color}; color: white; border-radius: 4px;">
            ${props.role_display}
          </span>
        </div>
      `;

      new maplibregl.Popup({ offset: 15 })
        .setLngLat(coords)
        .setHTML(html)
        .addTo(map);
    });

    // 鼠标样式
    map.on('mouseenter', 'highlight-sites-layer', () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'highlight-sites-layer', () => {
      map.getCanvas().style.cursor = '';
    });
  },

  _initHighlightPath(highlightPathData) {
    const map = this.map;
    const mapBase = this.mapBase;

    let allFeatures = [];
    const isFeatureCollection = highlightPathData.type === "FeatureCollection";

    if (isFeatureCollection) {
      allFeatures = highlightPathData.features || [];
    } else if (
      highlightPathData.type === "Feature" &&
      highlightPathData.geometry
    ) {
      allFeatures = [highlightPathData];
    }

    if (allFeatures.length === 0) return;

    // 计算边界
    const bounds = new maplibregl.LngLatBounds();
    allFeatures.forEach((feature) => {
      if (feature.geometry && feature.geometry.coordinates) {
        feature.geometry.coordinates.forEach((c) => bounds.extend(c));
      }
    });

    // 添加源
    mapBase.addGeoJsonSource("highlight-path", {
      type: "FeatureCollection",
      features: allFeatures,
    });

    // 区分：路径组(多条)显示静态红色，单条路径显示动画 (统一逻辑)
    // 路径高亮底层：金色轮廓线
    // 插入到站点图层之前，避免遮挡站点
    const beforeLayerId = map.getLayer('netbox-sites-layer') ? 'netbox-sites-layer' : undefined;

    mapBase.addLayer({
      id: "highlight-path-outline",
      type: "line",
      source: "highlight-path",
      paint: {
        "line-color": "#FFD700", // 金色
        "line-width": ["interpolate", ["linear"], ["zoom"], 3, 2, 6, 3, 10, 4],
        "line-opacity": 0.8,
      },
      layout: { visibility: "none" }, // 初始隐藏，动画结束后显示
    }, beforeLayerId);

    // 路径高亮顶层
    mapBase.addLayer({
      id: "highlight-path-layer",
      type: "line",
      source: "highlight-path",
      paint: {
        "line-color": "#FFD700",
        "line-width": ["interpolate", ["linear"], ["zoom"], 3, 1.5, 6, 2, 10, 3],
        "line-opacity": 0.9,
      },
      layout: { visibility: "none" },
    }, beforeLayerId);

    // 启动 Deck.gl 动画
    // 单条或多条均支持
    if (!this.flowAnimator) {
      this.flowAnimator = new DeckGLFlowAnimator(map);
    }

    // 构造 FeatureCollection 或 Feature
    const featureData = {
      type: "FeatureCollection",
      features: allFeatures,
    }; // 统一传 FeatureCollection

    // 定义回调
    const showStatic = () => {
      if (map.getLayer("highlight-path-outline"))
        map.setLayoutProperty(
          "highlight-path-outline",
          "visibility",
          "visible"
        );
      if (map.getLayer("highlight-path-layer"))
        map.setLayoutProperty("highlight-path-layer", "visibility", "visible");
    };

    // 优化：如果是多条路径（路径组），则直接显示静态高亮，不进行流向动画
    if (allFeatures.length > 1) {
      showStatic();
      // 如果之前有动画，可能需要清理？这里假设是新进入的模式
      if (this.flowAnimator) this.flowAnimator.clearHighlight();
    } else {
      // 单条路径：启动 Deck.gl 往返动画
      this.flowAnimator.animateHighlight(featureData, showStatic);
      // Safety
      setTimeout(showStatic, 2500);
    }

    // 自动缩放
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: 80, maxZoom: 12 });
      // 设置 Home 按钮的重置目标为当前边界
      if (this.mapBase && typeof this.mapBase.setHomeBounds === "function") {
        this.mapBase.setHomeBounds(bounds);
      }
    }
  },

  _initTargetMarker(lat, lng) {
    const marker = new maplibregl.Marker({ color: "#dc3545" })
      .setLngLat([lng, lat])
      .setPopup(
        new maplibregl.Popup({ offset: 25 }).setHTML(
          `<div style="padding:5px;"><b>目标位置</b><br>${lat}, ${lng}</div>`
        )
      )
      .addTo(this.map);
    marker.togglePopup();
  },

  _setupClickHandler() {
    this.map.on("click", (e) => {
      // 简化版点击处理，主要针对站点和路径标签
      // 安全检查：只查询当前样式中确实存在的图层
      const targetLayers = ["netbox-sites-layer", "otn-paths-labels"].filter(
        (id) => this.map.getLayer(id)
      );

      if (targetLayers.length === 0) return;

      const features = this.map.queryRenderedFeatures(e.point, {
        layers: targetLayers,
      });
      if (!features.length) return;

      const feature = features[0];
      const props = feature.properties;

      let html = "";
      let coords = e.lngLat;

      if (feature.layer.id === "netbox-sites-layer") {
        html = `<div style="padding:5px;"><b>${props.name}</b></div>`;
        coords = feature.geometry.coordinates;
      } else if (feature.layer.id === "otn-paths-labels") {
        html = `<div style="padding:5px;"><b>${props.name || "路径"}</b></div>`;
      }

      if (html) {
        new maplibregl.Popup().setLngLat(coords).setHTML(html).addTo(this.map);
      }
    });
  },

  // =============================================
  // 空间选择控件 (仅路径组模式)
  // =============================================

  _initSpatialSelectControl() {
    const map = this.map;
    const config = this.config;

    // 检查 SpatialSelectControl 是否已加载
    if (typeof SpatialSelectControl === 'undefined') {
      console.warn('SpatialSelectControl 未加载');
      return;
    }

    // 创建控件实例
    // 注意：站点和路径数据现在由控件从底图数据源动态获取
    this.spatialSelectControl = new SpatialSelectControl({
      pathGroupId: config.pathGroupId,
      pathGroupName: config.pathGroupName || '当前路径组',
      onAddComplete: (result) => {
        // 添加完成后刷新页面
        console.log('批量添加完成:', result);
        if (result.added_sites > 0 || result.added_paths > 0) {
          // 延迟刷新，让用户看到 Toast 消息
          setTimeout(() => window.location.reload(), 1500);
        }
      }
    });

    // 添加控件到地图左上角
    map.addControl(this.spatialSelectControl, 'top-left');
  },

  // =============================================
  // 模式切换控件 (仅路径组模式)
  // =============================================

  _addViewModeControl() {
    const map = this.map;
    const self = this;

    // 创建控件容器
    const container = document.createElement('div');
    container.className = 'maplibregl-ctrl maplibregl-ctrl-group view-mode-toggle';
    container.innerHTML = `
      <button type="button" class="view-mode-btn active" data-mode="detail" title="详细模式：显示所有站点和路径">
        <i class="mdi mdi-map-marker-multiple"></i>
      </button>
      <button type="button" class="view-mode-btn" data-mode="simple" title="简洁模式：仅显示终端站和光分插复用站">
        <i class="mdi mdi-vector-polyline"></i>
      </button>
    `;

    // 绑定点击事件
    container.querySelectorAll('.view-mode-btn').forEach(btn => {
      btn.addEventListener('click', function () {
        const mode = this.dataset.mode;
        if (mode === self.viewMode) return;

        // 更新按钮状态
        container.querySelectorAll('.view-mode-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');

        // 切换模式
        if (mode === 'simple') {
          self._switchToSimpleMode();
        } else {
          self._switchToDetailMode();
        }
        self.viewMode = mode;
      });
    });

    // 添加到地图左上角
    map.getContainer().querySelector('.maplibregl-ctrl-top-left').prepend(container);
  },

  _switchToSimpleMode() {
    const map = this.map;

    // 1. 隐藏路径高亮图层
    if (map.getLayer('highlight-path-outline')) {
      map.setLayoutProperty('highlight-path-outline', 'visibility', 'none');
    }
    if (map.getLayer('highlight-path-layer')) {
      map.setLayoutProperty('highlight-path-layer', 'visibility', 'none');
    }

    // 2. 过滤站点：仅显示 OTM 和 OADM (隐藏 OLA)
    const siteLayers = ['highlight-sites-glow', 'highlight-sites-layer', 'highlight-sites-labels'];
    siteLayers.forEach(layerId => {
      if (map.getLayer(layerId)) {
        map.setFilter(layerId, ['!=', ['get', 'role'], 'ola']);
      }
    });

    // 3. 绘制弧形连接线
    this._drawArcConnections();
  },

  _switchToDetailMode() {
    const map = this.map;

    // 1. 显示路径高亮图层
    if (map.getLayer('highlight-path-outline')) {
      map.setLayoutProperty('highlight-path-outline', 'visibility', 'visible');
    }
    if (map.getLayer('highlight-path-layer')) {
      map.setLayoutProperty('highlight-path-layer', 'visibility', 'visible');
    }

    // 2. 恢复所有站点显示
    const siteLayers = ['highlight-sites-glow', 'highlight-sites-layer', 'highlight-sites-labels'];
    siteLayers.forEach(layerId => {
      if (map.getLayer(layerId)) {
        map.setFilter(layerId, null);
      }
    });

    // 3. 移除弧形连接线
    this._removeArcConnections();
  },

  _drawArcConnections() {
    const map = this.map;
    const sitesData = this.config.highlightSitesData;

    if (!sitesData || sitesData.length < 2) return;

    // 过滤并排序：仅 OTM 和 OADM，按 position 排序
    const sortedSites = sitesData
      .filter(s => s.role === 'otm' || s.role === 'oadm')
      .sort((a, b) => (a.position || 0) - (b.position || 0));

    if (sortedSites.length < 2) return;

    // 生成弧形线 Features
    const arcFeatures = [];
    for (let i = 0; i < sortedSites.length - 1; i++) {
      const from = sortedSites[i];
      const to = sortedSites[i + 1];
      const arcCoords = this._generateArc([from.lng, from.lat], [to.lng, to.lat], 20);
      arcFeatures.push({
        type: 'Feature',
        properties: {
          from: from.name,
          to: to.name,
          index: i
        },
        geometry: {
          type: 'LineString',
          coordinates: arcCoords
        }
      });
    }

    // 添加数据源
    if (map.getSource('arc-connections')) {
      map.getSource('arc-connections').setData({
        type: 'FeatureCollection',
        features: arcFeatures
      });
    } else {
      this.mapBase.addGeoJsonSource('arc-connections', {
        type: 'FeatureCollection',
        features: arcFeatures
      });
    }

    // 添加弧形线图层（如果不存在）
    if (!map.getLayer('arc-connections-layer')) {
      // 添加底层（发光效果）- 先添加，确保在主层下方
      this.mapBase.addLayer({
        id: 'arc-connections-glow',
        type: 'line',
        source: 'arc-connections',
        paint: {
          'line-color': '#FF6B35',
          'line-width': 16,           // 增大线宽
          'line-opacity': 0.5,        // 增大透明度
          'line-blur': 8              // 增大模糊值
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round'
        }
      }, 'highlight-sites-glow');

      // 添加主层 - 后添加，在发光层上方
      this.mapBase.addLayer({
        id: 'arc-connections-layer',
        type: 'line',
        source: 'arc-connections',
        paint: {
          'line-color': '#FF6B35',
          'line-width': 3,
          'line-opacity': 1
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round'
        }
      });  // 不指定 beforeId，添加到最上层
    }

    // 添加脉冲动画
    this._startArcAnimation();
    this.arcLayers.push('arc-connections-layer', 'arc-connections-glow');
  },

  _removeArcConnections() {
    const map = this.map;

    // 停止动画
    if (this.arcAnimationId) {
      cancelAnimationFrame(this.arcAnimationId);
      this.arcAnimationId = null;
    }

    // 移除图层
    ['arc-connections-layer', 'arc-connections-glow'].forEach(layerId => {
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
    });
    if (map.getSource('arc-connections')) {
      map.removeSource('arc-connections');
    }
    this.arcLayers = [];
  },

  _generateArc(start, end, segments = 20) {
    // 生成贝塞尔弧形线的坐标点
    const coords = [];
    const [x1, y1] = start;
    const [x2, y2] = end;

    // 计算弧线控制点 (中点偏移)
    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;
    const dist = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);

    // 向北偏移（弧形向上凸）
    const offset = dist * 0.35;  // 弧度系数（增大弧度）
    const ctrlX = midX;
    const ctrlY = midY + offset;

    // 生成二次贝塞尔曲线点
    for (let i = 0; i <= segments; i++) {
      const t = i / segments;
      const x = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * ctrlX + t ** 2 * x2;
      const y = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * ctrlY + t ** 2 * y2;
      coords.push([x, y]);
    }
    return coords;
  },

  _startArcAnimation() {
    const map = this.map;
    let phase = 0;
    const self = this;

    const animate = () => {
      // 检查图层是否存在，不存在则停止
      if (!map.getLayer('arc-connections-glow')) {
        self.arcAnimationId = null;
        return;
      }

      // 闪烁动画：调整发光层的透明度和宽度
      phase += 0.08;  // 加快动画速度
      const pulse = 0.3 + Math.sin(phase) * 0.3;   // 0.0 ~ 0.6 闪烁幅度更大
      const width = 12 + Math.sin(phase) * 8;      // 4 ~ 20 宽度变化更大

      map.setPaintProperty('arc-connections-glow', 'line-opacity', pulse);
      map.setPaintProperty('arc-connections-glow', 'line-width', width);

      self.arcAnimationId = requestAnimationFrame(animate);
    };

    animate();
  },
}; // End of LocationModePlugin

// 辅助类：流向动画（优化版 - 按需渲染，与 fault_mode.js 保持一致）
class DeckGLFlowAnimator {
  constructor(map) {
    this.map = map;
    this.deckOverlay = null;  // ← 延迟创建，按需初始化


    // 高亮动画状态
    this.highlightPath = null;
    this.highlightTime = 0;
    this.highlightDirection = 1; // 1: A->Z, -1: Z->A
    this.highlightActive = false;
    this.highlightLoopCount = 0;
    this.highlightCallback = null;

    // 动画控制
    this.isRunning = false;
    this.animationFrameId = null;

    // 复用的Layer对象（避免每帧创建）
    this.highlightLayer = null;
  }

  // 统一入口：启动单次往返动画
  animateHighlight(feature, onComplete) {
    this.setHighlightPath(feature);
    this.highlightTime = 0;
    this.highlightDirection = 1;
    this.highlightActive = true;
    this.highlightLoopCount = 0;
    this.highlightCallback = onComplete;

    // 启动动画循环
    this._start();
  }

  // 设置高亮路径数据
  setHighlightPath(feature) {
    if (!feature) return;

    // FIX: FeatureCollection 没有 geometry 属性，需单独检查
    if (feature.type !== "FeatureCollection" && !feature.geometry) return;

    let pathData = [];
    const processLine = (coordinates) => {
      const len = coordinates.length;
      const timestamps = coordinates.map((_, i) => (i / (len - 1)) * 100);
      pathData.push({
        path: coordinates,
        timestamps: timestamps,
        color: [255, 100, 0], // 橙色高亮
      });
    };

    if (feature.type === "FeatureCollection") {
      feature.features.forEach((f) => {
        if (f.geometry.type === "LineString") {
          processLine(f.geometry.coordinates);
        } else if (f.geometry.type === "MultiLineString") {
          f.geometry.coordinates.forEach((c) => processLine(c));
        }
      });
    } else {
      const coords = feature.geometry.coordinates;
      const type = feature.geometry.type;
      if (type === "LineString") {
        processLine(coords);
      } else if (type === "MultiLineString") {
        coords.forEach((c) => processLine(c));
      }
    }

    this.highlightPath = pathData;

    // 创建或更新Layer对象（复用以提升性能）
    if (!this.highlightLayer) {
      this.highlightLayer = new deck.TripsLayer({
        id: "path-highlight-flow",
        data: pathData,
        getPath: (d) => d.path,
        getTimestamps: (d) => d.timestamps,
        getColor: [255, 165, 0],  // 金橙色
        currentTime: 0,
        trailLength: 50,
        widthMinPixels: 5,
        opacity: 1.0,
      });
    } else {
      // 复用现有对象，只更新数据（避免重复创建）
      this.highlightLayer = this.highlightLayer.clone({
        data: pathData,
        currentTime: 0,
      });
    }
  }

  clearHighlight() {
    this.highlightPath = null;
    this.highlightActive = false;
    this.highlightCallback = null;
    this._stop();
  }

  stop() {
    this.clearHighlight();
  }

  // 内部方法：启动动画循环
  _start() {
    if (!this.isRunning) {
      this.isRunning = true;

      // 按需创建Overlay（避免永久RAF）
      if (!this.deckOverlay) {
        this.deckOverlay = new deck.MapboxOverlay({
          interleaved: false,
          layers: [],
        });
        this.map.addControl(this.deckOverlay);
      }

      this._animate();
    }
  }

  // 内部方法：停止动画循环
  _stop() {
    this.isRunning = false;
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }

    // 完全移除Overlay（停止DeckGL的RAF循环）
    if (this.deckOverlay) {
      this.map.removeControl(this.deckOverlay);
      this.deckOverlay.finalize();  // DeckGL清理方法
      this.deckOverlay = null;
    }
  }

  _animate() {
    // 检查是否应该继续运行
    if (!this.isRunning) {
      return;
    }

    // 高亮动画控制 (0 -> 100 -> 0, 重复2次后停止)
    if (this.highlightActive && this.highlightPath) {
      this.highlightTime += 2 * this.highlightDirection; // 速度快一点

      if (this.highlightDirection === 1 && this.highlightTime >= 100) {
        this.highlightTime = 100;
        this.highlightDirection = -1; // 掉头
      } else if (this.highlightDirection === -1 && this.highlightTime <= 0) {
        this.highlightTime = 0;
        this.highlightLoopCount++; // 完成一次往返

        if (this.highlightLoopCount < 2) {
          // 继续循环
          this.highlightDirection = 1;
        } else {
          // 结束动画
          this.highlightActive = false;
          if (this.highlightCallback) {
            this.highlightCallback();
          }
          // 停止循环，释放CPU
          this._stop();
          return;
        }
      }

      // 更新Layer的currentTime属性（使用clone复用对象）
      if (this.highlightLayer) {
        this.highlightLayer = this.highlightLayer.clone({
          currentTime: this.highlightTime,
        });
        this.deckOverlay.setProps({ layers: [this.highlightLayer] });
      }
    }

    // 继续下一帧
    this.animationFrameId = requestAnimationFrame(this._animate.bind(this));
  }
}

window.initOTNMap(LocationModePlugin);

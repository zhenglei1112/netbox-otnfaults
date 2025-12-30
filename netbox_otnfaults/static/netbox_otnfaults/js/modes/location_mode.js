/**
 * 位置/路径地图模式插件
 * 处理 Location, Path, PathGroup 三种模式
 */

const LocationModePlugin = {
  core: null,
  map: null,
  config: null,
  mapBase: null,

  init(core) {
    console.log("LocationModePlugin: initializing...");
    this.core = core;
    this.map = core.map;
    this.mapBase = core.mapBase;
    this.config = core.config;

    // 1. 处理高亮路径 (Path / PathGroup 模式)
    if (this.config.highlightPathData) {
      this._initHighlightPath(this.config.highlightPathData);
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
    mapBase.addLayer({
      id: "highlight-path-outline",
      type: "line",
      source: "highlight-path",
      paint: {
        "line-color": "#FFD700", // 金色
        "line-width": 6,
        "line-opacity": 0.8,
      },
      layout: { visibility: "none" }, // 初始隐藏，动画结束后显示
    });

    // 路径高亮顶层
    mapBase.addLayer({
      id: "highlight-path-layer",
      type: "line",
      source: "highlight-path",
      paint: {
        "line-color": "#FFD700",
        "line-width": 5,
        "line-opacity": 0.9,
      },
      layout: { visibility: "none" },
    });

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
      const features = this.map.queryRenderedFeatures(e.point, {
        layers: ["netbox-sites-layer", "otn-paths-labels"],
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
}; // End of LocationModePlugin

// 辅助类：流向动画 (与 fault_mode.js 保持一致)
class DeckGLFlowAnimator {
  constructor(map) {
    this.map = map;
    this.deckOverlay = new deck.MapboxOverlay({
      interleaved: false,
      layers: [],
    });
    map.addControl(this.deckOverlay);

    // 背景动画状态
    this.time = 0;
    this.paths = [];

    // 高亮动画状态 (独立)
    this.highlightPath = null;
    this.highlightTime = 0;
    this.highlightDirection = 1; // 1: A->Z, -1: Z->A
    this.highlightActive = false;
    this.highlightLoopCount = 0;
    this.highlightCallback = null;

    this._animate();
  }

  updatePaths(paths) {
    this.paths = paths || [];
  }

  // 统一入口：启动单次往返动画
  animateHighlight(feature, onComplete) {
    this.setHighlightPath(feature);
    this.highlightTime = 0;
    this.highlightDirection = 1;
    this.highlightActive = true;
    this.highlightLoopCount = 0;
    this.highlightCallback = onComplete;
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
  }

  clearHighlight() {
    this.highlightPath = null;
    this.highlightActive = false;
    this.highlightCallback = null;
  }

  stop() {
    this.clearHighlight();
  }

  _animate() {
    // 1. 背景动画循环 (0 -> 100 loop)
    this.time = (this.time + 0.5) % 100;

    // 2. 高亮动画控制 (0 -> 100 -> 0 stop)
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
          // 结束
          this.highlightActive = false;
          this.highlightPath = null;
          if (this.highlightCallback) {
            this.highlightCallback();
          }
        }
      }
    }

    const layers = [];

    // 高亮层
    if (this.highlightActive && this.highlightPath) {
      const highlightLayer = new deck.TripsLayer({
        id: "path-highlight-flow",
        data: this.highlightPath,
        getPath: (d) => d.path,
        getTimestamps: (d) => d.timestamps,
        getColor: [255, 165, 0], // 金橙色
        currentTime: this.highlightTime,
        trailLength: 50, // 拖尾长一点
        widthMinPixels: 5,
        opacity: 1.0,
      });
      layers.push(highlightLayer);
    }

    this.deckOverlay.setProps({ layers: layers });
    requestAnimationFrame(this._animate.bind(this));
  }
}

window.initOTNMap(LocationModePlugin);

/**
 * 故障分布图模式插件
 */

const FaultModePlugin = {
  core: null,
  map: null,
  config: null,
  mapBase: null,

  // 状态
  heatmapData: [],
  markerData: [],
  timeRange: "year",
  currentCategory: "all",

  // 弹窗动画配置常量
  POPUP_ANIMATION: {
    FADE_IN_DURATION: 250,    // 淡入动画时长(ms)
    FADE_OUT_DURATION: 200,   // 淡出动画时长(ms)
    CLOSE_DELAY: 300,         // 延迟关闭时长(ms),给用户时间移到弹窗上
  },

  // 控件引用
  layerToggleControl: null,
  statsControl: null,
  legendControl: null,
  searchControl: null,

  init(core) {
    this.core = core;
    this.map = core.map;
    this.mapBase = core.mapBase;
    this.config = core.config;

    // 1. 初始化数据
    this._initData();

    // 2. 添加图层
    this._addLayers();

    // 3. 初始化业务控件
    this._initControls();

    // 4. 事件监听
    this._setupEventListeners();

    // 5. 初始状态更新
    this.updateMapState();

    // 6. 加载额外数据 (OTN路径元数据)
    this._loadPathMetadata();

    // 7. 暴露全局方法供控件调用
    window.updateMapState = this.updateMapState.bind(this);
    window.highlightPath = this.highlightPath.bind(this); // 统一高亮入口

    if (this.layerToggleControl) {
      window.layerToggleControl = this.layerToggleControl;
    }
    if (this.statsControl) {
      window.faultStatisticsControl = this.statsControl;
    }
  },

  _initData() {
    // 预处理热力图数据
    this.heatmapData = (this.config.heatmapData || [])
      .map((item) => ({
        lat: parseFloat(item.lat),
        lng: parseFloat(item.lng),
        count: parseInt(item.count, 10),
        ids: item.ids,
      }))
      .filter((d) => !isNaN(d.lat) && !isNaN(d.lng));

    // 预处理标记数据
    this.markerData = this.config.markerData || [];

    // 预设时间范围（通常由URL参数传递，这里暂时简化，视图层并未传此具体参数，默认year）
    // 实际应该从 config 中读取 current_time_range，但在 map_modes 中未配置传参
    // 视图修改时需要传递 current_time_range
    this.timeRange = "year";
  },

  _addLayers() {
    const map = this.map;
    const mapBase = this.mapBase;

    // --- 热力图源 ---
    mapBase.addGeoJsonSource("fault-heatmap", {
      type: "FeatureCollection",
      features: this.heatmapData.map((d) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [d.lng, d.lat] },
        properties: { count: d.count },
      })),
    });

    // 热力图层
    mapBase.addLayer(
      {
        id: "fault-heatmap-layer",
        type: "heatmap",
        source: "fault-heatmap",
        maxzoom: 9,
        paint: {
          "heatmap-weight": [
            "interpolate",
            ["linear"],
            ["get", "count"],
            0,
            0,
            10,
            1,
          ],
          "heatmap-intensity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            0,
            1,
            9,
            3,
          ],
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(33,102,172,0)",
            0.2,
            "rgb(103,169,207)",
            0.4,
            "rgb(209,229,240)",
            0.6,
            "rgb(253,219,199)",
            0.8,
            "rgb(239,138,98)",
            1,
            "rgb(178,24,43)",
          ],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 0, 2, 9, 20],
          "heatmap-opacity": 0.8,
        },
      },
      "netbox-sites-layer"
    ); // 插入在站点层之下

    // --- 故障点源 ---
    // 使用 FaultDataService (假定已加载) 转换数据
    // 注意：需要确保 FaultDataService.js 已在 map_modes.py 的 js_files 中定义
    if (typeof FaultDataService !== "undefined") {
      const features = FaultDataService.convertToFeatures(this.markerData);
      mapBase.addGeoJsonSource("fault-points", {
        type: "FeatureCollection",
        features: features,
      });
    } else {
      console.warn(
        "FaultDataService not found, raw marker handling not implemented in this snippet."
      );
    }

    // 故障点图层 (图标)
    // 需要加载图标 - 移植 otnfault_map_app.js 的逻辑
    this._loadFaultIcons(() => {
      // 图标加载完成后更新图层（如果需要）
      // 这里只是为了确保图标存在，图层引用会自动生效
    });

    // 构建 icon-image 匹配表达式
    const iconImageExpression = [
      "concat",
      "fault-marker-",
      ["get", "category"],
      "-",
      ["coalesce", ["get", "statusKey"], "processing"],
    ];

    mapBase.addLayer({
      id: "fault-points-layer",
      type: "symbol",
      source: "fault-points",
      layout: {
        "icon-image": iconImageExpression,
        "icon-size": ["interpolate", ["linear"], ["zoom"], 4, 0.6, 10, 1.2], // 放大显示比例
        "icon-allow-overlap": true,
        visibility: "none", // 初始隐藏，由 updateMapState 控制
      },
    });

    // --- 路径高亮层 (恢复旧版逻辑) ---
    // 添加路径高亮源
    mapBase.addGeoJsonSource("otn-paths-highlight", {
      type: "Feature",
      geometry: { type: "LineString", coordinates: [] },
    });

    // 路径高亮底层：金色轮廓线
    mapBase.addLayer(
      {
        id: "otn-paths-highlight-outline",
        type: "line",
        source: "otn-paths-highlight",
        paint: {
          "line-color": "#FFD700",
          "line-width": 6,
          "line-opacity": 0.8,
        },
      },
      "netbox-sites-layer" // 放在站点之下
    );

    // 路径高亮顶层：保留作为底色背景
    mapBase.addLayer(
      {
        id: "otn-paths-highlight-layer",
        type: "line",
        source: "otn-paths-highlight",
        paint: {
          "line-color": "#FFD700",
          "line-width": 5,
          "line-opacity": 0.9,
        },
      },
      "netbox-sites-layer"
    );

    // --- Deck.gl 流动效果 (针对路径) ---
    // 仅初始化容器，具体数据由 flowAnimator 管理
    this.flowAnimator = new DeckGLFlowAnimator(map);
  },

  _loadFaultIcons(callback) {
    const map = this.map;
    // 故障状态列表
    const statusKeys = Object.keys(FAULT_STATUS_COLORS);
    // 故障类型列表
    const categoryKeys = Object.keys(FAULT_CATEGORY_COLORS);

    // 为不同故障类型创建不同形状的图标（具有象形意义）
    // category: 'fiber'=光纤波浪线, 'power'=闪电, 'pigtail'=雪花, 'device'=芯片, 'other'=警告三角
    const createMarkerIcon = (category, color) => {
      const size = 64; // 增大 Canvas 尺寸 (64x64) -> 逻辑像素 32x32
      const canvas = document.createElement("canvas");
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext("2d");

      // 缩放绘图环境，使得后续坐标仍可按 32x32 的逻辑坐标系绘制
      // 这里的 16,16 将被映射为物理像素 32,32
      ctx.scale(2, 2);

      const centerX = 16; // 逻辑中心 x
      const centerY = 16; // 逻辑中心 y
      const radius = 9; // 逻辑半径 (物理半径 18)

      // 1. 绘制底色圆形 (带白色描边以增加对比度)
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      // 增加白色描边 (发光效果)
      ctx.strokeStyle = "white";
      ctx.lineWidth = 1.5; // 逻辑线宽 1.5 -> 实际 3px
      ctx.stroke();

      // 2. 绘制图标 (白色)
      ctx.strokeStyle = "white";
      ctx.fillStyle = "white";
      ctx.lineWidth = 1.2; // 逻辑线宽 1.2 -> 实际 2.4px
      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      switch (category) {
        case "fiber":
          // 光纤波浪线图标
          const waveW = 7;
          ctx.beginPath();
          ctx.moveTo(centerX - waveW, centerY);
          ctx.quadraticCurveTo(
            centerX - waveW / 2,
            centerY - 4,
            centerX,
            centerY
          );
          ctx.quadraticCurveTo(
            centerX + waveW / 2,
            centerY + 4,
            centerX + waveW,
            centerY
          );
          ctx.stroke();
          // 端点
          ctx.beginPath();
          ctx.arc(centerX - waveW, centerY, 1, 0, Math.PI * 2);
          ctx.arc(centerX + waveW, centerY, 1, 0, Math.PI * 2);
          ctx.fill();
          break;

        case "power":
          // 闪电图标
          ctx.beginPath();
          ctx.moveTo(centerX + 1, centerY - 6);
          ctx.lineTo(centerX - 3, centerY + 1);
          ctx.lineTo(centerX, centerY + 1);
          ctx.lineTo(centerX - 1, centerY + 6); // 闪电尖端
          ctx.lineTo(centerX + 3, centerY - 1); // 回折点
          ctx.lineTo(centerX, centerY - 1);
          ctx.closePath();
          ctx.fill();
          break;

        case "pigtail":
          // 雪花图标：空调故障（制冷）
          ctx.lineWidth = 1.2;
          const armLength = 6;
          for (let i = 0; i < 6; i++) {
            const angle = (i * 60 * Math.PI) / 180;
            const x1 = centerX;
            const y1 = centerY;
            const x2 = centerX + Math.cos(angle) * armLength;
            const y2 = centerY + Math.sin(angle) * armLength;
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
            // 分支
            const branchLen = 2;
            const bA1 = angle + Math.PI / 4;
            const bA2 = angle - Math.PI / 4;
            const midX = centerX + Math.cos(angle) * (armLength * 0.6);
            const midY = centerY + Math.sin(angle) * (armLength * 0.6);
            ctx.beginPath();
            ctx.moveTo(midX, midY);
            ctx.lineTo(
              midX + Math.cos(bA1) * branchLen,
              midY + Math.sin(bA1) * branchLen
            );
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(midX, midY);
            ctx.lineTo(
              midX + Math.cos(bA2) * branchLen,
              midY + Math.sin(bA2) * branchLen
            );
            ctx.stroke();
          }
          break;

        case "device":
          // 芯片/服务器图标
          const chipSize = 10;
          const pinLen = 2;
          ctx.fillRect(
            centerX - chipSize / 2,
            centerY - chipSize / 2,
            chipSize,
            chipSize
          );
          ctx.lineWidth = 1;

          // 上边
          for (let i = -1; i <= 1; i++) {
            ctx.beginPath();
            ctx.moveTo(centerX + i * 3, centerY - chipSize / 2);
            ctx.lineTo(centerX + i * 3, centerY - chipSize / 2 - pinLen);
            ctx.stroke();
          }
          // 下边
          for (let i = -1; i <= 1; i++) {
            ctx.beginPath();
            ctx.moveTo(centerX + i * 3, centerY + chipSize / 2);
            ctx.lineTo(centerX + i * 3, centerY + chipSize / 2 + pinLen);
            ctx.stroke();
          }
          // 左边
          for (let i = -1; i <= 1; i++) {
            ctx.beginPath();
            ctx.moveTo(centerX - chipSize / 2, centerY + i * 3);
            ctx.lineTo(centerX - chipSize / 2 - pinLen, centerY + i * 3);
            ctx.stroke();
          }
          // 右边
          for (let i = -1; i <= 1; i++) {
            ctx.beginPath();
            ctx.moveTo(centerX + chipSize / 2, centerY + i * 3);
            ctx.lineTo(centerX + chipSize / 2 + pinLen, centerY + i * 3);
            ctx.stroke();
          }

          ctx.fillStyle = color;
          ctx.fillRect(centerX - 2, centerY - 2, 4, 4);
          break;

        case "other":
        default:
          // 警告三角形
          ctx.beginPath();
          ctx.moveTo(centerX, centerY - 5);
          ctx.lineTo(centerX + 5, centerY + 4);
          ctx.lineTo(centerX - 5, centerY + 4);
          ctx.closePath();
          ctx.stroke();
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(centerX, centerY - 2);
          ctx.lineTo(centerX, centerY + 1);
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(centerX, centerY + 3, 0.8, 0, Math.PI * 2);
          ctx.fill();
          break;
      }
      return ctx.getImageData(0, 0, size, size);
    };

    const addIconToMap = (name, category, color) => {
      if (!map.hasImage(name)) {
        const imageData = createMarkerIcon(category, color);
        map.addImage(name, imageData, { pixelRatio: 2 });
      }
    };

    // 默认图标
    addIconToMap("fault-marker", "other", FAULT_STATUS_COLORS["processing"]);

    // 组合图标
    categoryKeys.forEach((category) => {
      statusKeys.forEach((status) => {
        const color = FAULT_STATUS_COLORS[status];
        const iconName = `fault-marker-${category}-${status}`;
        addIconToMap(iconName, category, color);
      });
    });

    if (callback) callback();
  },

  _initControls() {
    const map = this.map;

    // 图层控制
    if (typeof LayerToggleControl !== "undefined") {
      this.layerToggleControl = new LayerToggleControl({
        onToggle: (type) => {
          // 处理 3D/2D 切换等
        },
      });
      this.mapBase.addControl(this.layerToggleControl, "top-left");
    }

    // 统计面板
    if (typeof FaultStatisticsControl !== "undefined") {
      this.statsControl = new FaultStatisticsControl({
        onTimeRangeChange: (range) => {
          this.timeRange = range;
          this.updateMapState();
        },
        onCategoryChange: (cat) => {
          this.currentCategory = cat;
          this.updateMapState();
        },
      });
      this.mapBase.addControl(this.statsControl, "bottom-left");
    }

    // 图例
    if (typeof FaultLegendControl !== "undefined") {
      this.legendControl = new FaultLegendControl();
      this.mapBase.addControl(this.legendControl, "bottom-right");
    }

    // 搜索
    if (typeof SearchControl !== "undefined") {
      this.searchControl = new SearchControl({
        sitesData: this.config.sitesData,
        onSelect: (site) => {
          map.flyTo({ center: [site.longitude, site.latitude], zoom: 12 });
        },
      });
      this.mapBase.addControl(this.searchControl, "top-left");
    }
  },

  _setupEventListeners() {
    const map = this.map;

    // 1. 故障点交互 (悬停显示,带延迟关闭和动画效果)
    map.on("mouseenter", "fault-points-layer", (e) => {
      map.getCanvas().style.cursor = "pointer";

      // 显示故障弹窗(_showFaultPopup内部已实现防抖和定时器清除)
      if (e.features.length) {
        this._showFaultPopup(e.features[0]);
      }
    });

    map.on("mouseleave", "fault-points-layer", () => {
      map.getCanvas().style.cursor = "";
      // 启动延迟关闭
      this._startPopupCloseTimer();
    });

    // 2. 点击事件 (保留站点和路径的点击)
    map.on("click", (e) => {
      const features = map.queryRenderedFeatures(e.point, {
        layers: [
          // "fault-points-layer", // 故障点已移至 hover
          "netbox-sites-layer",
          "otn-paths-layer",
          "otn-paths-labels",
        ],
      });


      if (!features.length) return;

      const feature = features[0];
      // 处理弹窗... (逻辑复用 PopupTemplates)
      if (feature.layer.id === "netbox-sites-layer") {
        this._showSitePopup(feature);
      } else if (
        feature.layer.id === "otn-paths-labels" ||
        feature.layer.id === "otn-paths-layer"
      ) {
        this._showPathPopup(feature, e.lngLat);
      }
    });

    map.on("zoom", () => this.updateMapState());
  },

  /**
   * 重置弹窗动画状态
   * @param {HTMLElement} popupEl - 弹窗DOM元素
   * @param {string} animationType - 动画类型: 'enter' 或 'leave'
   */
  _resetPopupAnimation(popupEl, animationType) {
    // 移除所有动画类
    popupEl.classList.remove('popup-enter-active', 'popup-leave-active');
    // 强制重排,确保动画重新开始
    void popupEl.offsetWidth;
    // 添加指定的动画类
    popupEl.classList.add(`popup-${animationType}-active`);
  },

  /**
   * 清理弹窗的事件监听器
   * 防止内存泄漏
   */
  _cleanupPopupListeners() {
    if (this.currentPopupListeners && this.currentFaultPopup) {
      const popupEl = this.currentFaultPopup.getElement();
      Object.entries(this.currentPopupListeners).forEach(([event, handler]) => {
        popupEl.removeEventListener(event, handler);
      });
      this.currentPopupListeners = null;
    }
  },

  _showFaultPopup(feature) {
    if (typeof PopupTemplates !== "undefined") {
      const faultId = feature.properties.id || feature.properties.number;

      // 先清除未执行的关闭定时器和动画移除定时器(无论是否是同一个故障)
      if (this.popupCloseTimer) {
        clearTimeout(this.popupCloseTimer);
        this.popupCloseTimer = null;
      }
      if (this.popupRemoveTimer) {
        clearTimeout(this.popupRemoveTimer);
        this.popupRemoveTimer = null;
      }

      // 防抖:如果当前已经显示同一个故障的弹窗,不重复显示,避免鼠标事件循环
      if (this.currentFaultPopup && this.currentFaultId === faultId) {
        return; // 已显示相同故障的弹窗,直接返回
      }

      const html = PopupTemplates.faultPopup(feature.properties);

      // 清理旧弹窗的事件监听器
      this._cleanupPopupListeners();

      if (this.currentFaultPopup) {
        this.currentFaultPopup.remove();
      }

      // 保存当前故障ID
      this.currentFaultId = faultId;

      this.currentFaultPopup = new maplibregl.Popup({
        closeButton: false, // 悬停模式通常无需关闭按钮
        closeOnClick: false,
        className: "fault-popup-container" // 方便样式控制或查找
      })
        .setLngLat(feature.geometry.coordinates)
        .setHTML(html)
        .addTo(this.map);

      // 为弹窗 DOM 添加鼠标交互，防止移动到弹窗上时消失
      const popupEl = this.currentFaultPopup.getElement();

      // 监听动画结束事件,自动清理动画类,避免重复播放
      const handleAnimationEnd = (e) => {
        // 只清理淡入动画类,淡出动画类保留到DOM移除前
        // 避免淡出完成后移除类导致弹窗闪现
        if (e.animationName === 'faultPopupFadeIn') {
          popupEl.classList.remove('popup-enter-active');
        }
        // 注意:faultPopupFadeOut动画结束后不移除类,避免闪烁
      };

      const handleMouseEnter = () => {
        // 防抖:避免在短时间内重复处理(100ms内只处理一次)
        if (this._isHandlingPopupInteraction) {
          return;
        }
        this._isHandlingPopupInteraction = true;
        setTimeout(() => {
          this._isHandlingPopupInteraction = false;
        }, 100);

        // 清除延迟关闭定时器
        if (this.popupCloseTimer) {
          clearTimeout(this.popupCloseTimer);
          this.popupCloseTimer = null;
        }
        // 清除动画移除定时器(如果用户在淡出动画期间移到弹窗上)
        if (this.popupRemoveTimer) {
          clearTimeout(this.popupRemoveTimer);
          this.popupRemoveTimer = null;
          // 只有当正在播放离开动画时,才重置为进入动画
          if (popupEl.classList.contains('popup-leave-active')) {
            this._resetPopupAnimation(popupEl, 'enter');
          }
        }
      };

      const handleMouseLeave = () => {
        this._startPopupCloseTimer();
      };

      // 添加事件监听器
      popupEl.addEventListener('animationend', handleAnimationEnd);
      popupEl.addEventListener("mouseenter", handleMouseEnter);
      popupEl.addEventListener("mouseleave", handleMouseLeave);

      // 保存监听器引用,便于清理
      this.currentPopupListeners = {
        'animationend': handleAnimationEnd,
        'mouseenter': handleMouseEnter,
        'mouseleave': handleMouseLeave
      };

      // 触发进入动画
      requestAnimationFrame(() => {
        popupEl.classList.add('popup-enter-active');
      });
    }
  },

  _startPopupCloseTimer() {
    if (this.popupCloseTimer) clearTimeout(this.popupCloseTimer);
    this.popupCloseTimer = setTimeout(() => {
      if (this.currentFaultPopup) {
        const popupEl = this.currentFaultPopup.getElement();

        // 移除进入动画类,添加离开动画类
        popupEl.classList.remove('popup-enter-active');
        popupEl.classList.add('popup-leave-active');

        // 等待离开动画完成后再移除弹窗
        this.popupRemoveTimer = setTimeout(() => {
          if (this.currentFaultPopup) {
            // 清理事件监听器
            this._cleanupPopupListeners();
            // 移除弹窗DOM
            this.currentFaultPopup.remove();
            this.currentFaultPopup = null;
            this.currentFaultId = null; // 清除故障ID,允许下次重新显示
          }
          this.popupRemoveTimer = null;
        }, this.POPUP_ANIMATION.FADE_OUT_DURATION);
      }
    }, this.POPUP_ANIMATION.CLOSE_DELAY);
  },

  _showSitePopup(feature) {
    if (typeof PopupTemplates === "undefined") return;

    const props = feature.properties;
    const siteName = props.name;
    const siteUrl = props.url || "#";

    // 构建详情链接
    const faultListUrl =
      window.OTNFaultMapConfig.faultListUrl ||
      "/plugins/netbox_otnfaults/faults/";
    const detailUrl = `${faultListUrl}?single_site_a_id=${props.id}`;

    // 计算统计数据
    let timeStatsHtml = "";
    if (window.faultStatisticsControl) {
      const timeStats =
        window.faultStatisticsControl.calculateSiteTimeStats(siteName);
      const monthlyStats =
        window.faultStatisticsControl.calculateSiteMonthlyStats(siteName);
      timeStatsHtml = window.faultStatisticsControl.renderTimeStatsHtml(
        timeStats,
        "此站点",
        monthlyStats,
        detailUrl
      );
    }

    const html = PopupTemplates.sitePopup({
      siteName,
      siteUrl,
      detailUrl,
      props,
      timeStatsHtml,
    });

    const popup = new maplibregl.Popup({ maxWidth: "300px", className: "stats-popup" })
      .setLngLat(feature.geometry.coordinates)
      .setHTML(html)
      .addTo(this.map);

    // 触发淡入动画
    const popupEl = popup.getElement();
    requestAnimationFrame(() => {
      popupEl.classList.add('popup-enter-active');
    });

    // 动画结束后清理类
    popupEl.addEventListener('animationend', (e) => {
      if (e.animationName === 'faultPopupFadeIn') {
        popupEl.classList.remove('popup-enter-active');
      }
    }, { once: true });
  },

  _showPathPopup(feature, lngLat) {
    if (typeof PopupTemplates === "undefined") return;

    const props = feature.properties;
    const pathName = props.name || "未命名路径";
    let pathUrl = props.url || "";

    // 如果 props.url 或 total_length 为空，尝试从元数据中查找
    if ((!pathUrl || !props.total_length) && window.OTNPathsMetadata) {
      // props.id 是路径 ID
      const meta = window.OTNPathsMetadata.find(
        (p) => p.properties && p.properties.id == props.id
      );
      if (meta) {
        if (!pathUrl && meta.properties.url) {
          pathUrl = meta.properties.url;
        }
        if (props.total_length == null && meta.properties.total_length != null) {
          props.total_length = meta.properties.total_length;
        }
      }
    }
    const siteAName = props.site_a || "站点A";
    const siteZName = props.site_z || "站点Z";

    // 计算统计需要 A 和 Z 名字
    let timeStatsHtml = "";
    if (window.faultStatisticsControl) {
      const timeStats = window.faultStatisticsControl.calculatePathTimeStats(
        siteAName,
        siteZName
      );
      const monthlyStats =
        window.faultStatisticsControl.calculatePathMonthlyStats(
          siteAName,
          siteZName
        );

      const faultListUrl =
        window.OTNFaultMapConfig.faultListUrl ||
        "/plugins/netbox_otnfaults/faults/";
      let detailUrl = "";
      if (props.site_a_id && props.site_z_id) {
        detailUrl = `${faultListUrl}?bidirectional_pair=${props.site_a_id},${props.site_z_id}`;
      }

      timeStatsHtml = window.faultStatisticsControl.renderTimeStatsHtml(
        timeStats,
        "此路径",
        monthlyStats,
        detailUrl
      );
    }

    const html = PopupTemplates.pathPopup({
      pathName,
      pathUrl,
      siteAName,
      siteZName,
      detailUrl: "",
      props,
      timeStatsHtml,
    });

    // 优先使用传入的点击坐标，否则使用 geometry 的第一个坐标
    const pos =
      lngLat ||
      (feature.geometry.type === "Point"
        ? feature.geometry.coordinates
        : feature.geometry.coordinates[0]);

    // 修复：先关闭现有的路径 popup（如果存在），防止其 close 事件清除新高亮
    if (window._currentPathPopup) {
      // 移除 close 事件监听器，防止清除新高亮
      // 注意：MapLibre Popup 没有 public 的 .off 方法来移除特定匿名函数??
      // 实际上 .on('close', fn) 绑定的 fn 如果是匿名的，无法 .off。
      // 但我们可以直接 .remove() 它，它会触发 close。
      // 关键是：在旧逻辑里，我们是先 .off 再 remove。
      // 这里我们需要确保 'close' 事件里的逻辑不执行。
      // 方法1：给 popup 仅绑定一次，或者保存 callback 引用。
      // 方法2：旧代码是 window._currentPathPopup.off("close"); 这假设了 popup 实例支持 off (Evented)。MapLibre Popup 继承自 Evented。
      // 但我们需要移除的是 *那个* 特定的清理函数。
      // 简单起见，我们可以在那个清理函数里检查 "是否我是最新的 popup"。
      // 或者：直接暴力移除所有 close 监听器（如果支持 .off('close') 不带 callback）或者无法做到。

      // 更可靠的方法：在此处标记 "suppressCloseEvent" 或者移除监听器（如果保存了引用）。
      // 由于之前代码是匿名函数，无法 .off。
      // 所以我们采用策略：
      // 在 window._currentPathPopup 对象上挂一个标志位 ._suppressClear = true
      window._currentPathPopup._suppressClear = true;
      window._currentPathPopup.remove();
      window._currentPathPopup = null;
    }

    // 创建弹窗
    const pathPopup = new maplibregl.Popup({
      maxWidth: "300px",
      className: "stats-popup",
    })
      .setLngLat(pos)
      .setHTML(html)
      .addTo(this.map);

    // 触发淡入动画
    const popupEl = pathPopup.getElement();
    requestAnimationFrame(() => {
      popupEl.classList.add('popup-enter-active');
    });

    // 动画结束后清理类
    popupEl.addEventListener('animationend', (e) => {
      if (e.animationName === 'faultPopupFadeIn') {
        popupEl.classList.remove('popup-enter-active');
      }
    }, { once: true });

    // 保存引用
    window._currentPathPopup = pathPopup;

    // --- 高亮逻辑 (统一调用) ---
    // 1. 获取完整几何信息 (从缓存或当前 feature)
    let highlightFeature = null;
    const pathId = props.id;
    if (pathId && window.OTNPathsMetadata) {
      const cachedPath = window.OTNPathsMetadata.find(
        (p) => p.properties && p.properties.id == pathId
      );
      if (cachedPath) {
        highlightFeature = {
          type: "Feature",
          properties: cachedPath.properties,
          geometry: cachedPath.geometry,
        };
      }
    }
    // 回退
    if (!highlightFeature) {
      highlightFeature = {
        type: "Feature",
        properties: props,
        geometry: feature.geometry,
      };
    }

    // 调用统一高亮方法
    this.highlightPath(highlightFeature);

    // 4. 关闭事件清理
    pathPopup.on("close", () => {
      // 如果标记了由于切换弹窗而关闭，则不清除高亮
      if (pathPopup._suppressClear) return;

      if (this.flowAnimator) {
        this.flowAnimator.clearHighlight();
      }
      const map = this.map;
      if (map.getSource("otn-paths-highlight")) {
        map.getSource("otn-paths-highlight").setData({
          type: "Feature",
          geometry: { type: "LineString", coordinates: [] },
        });
      }
      // 清除引用
      if (window._currentPathPopup === pathPopup) {
        window._currentPathPopup = null;
      }
    });
  },

  updateMapState() {
    const map = this.map;
    // const zoom = map.getZoom(); // 由 getEffectiveMode 内部处理

    // 获取状态：优先从 layerToggleControl 获取，否则使用本地状态
    let timeRange = this.timeRange;
    let selectedCategories = [];

    if (this.layerToggleControl) {
      timeRange = this.layerToggleControl.currentTimeRange;
      selectedCategories = this.layerToggleControl.selectedCategories;
    } else {
      // Fallback or local state
      if (this.currentCategory === "all") {
        selectedCategories = window.FAULT_CATEGORY_COLORS
          ? Object.keys(window.FAULT_CATEGORY_COLORS)
          : [];
      } else {
        selectedCategories = [this.currentCategory];
      }
    }

    // 1. 筛选数据
    let filteredFeatures = [];
    if (typeof FaultDataService !== "undefined") {
      filteredFeatures = FaultDataService.filter(
        FaultDataService.convertToFeatures(this.markerData), // 重新生成或缓存
        timeRange,
        selectedCategories
      );
    }

    // 2. 更新源 (Points)
    const sourcePoints = map.getSource("fault-points");
    if (sourcePoints) {
      sourcePoints.setData({
        type: "FeatureCollection",
        features: filteredFeatures,
      });
    }

    // 3. 更新源 (Heatmap) - 必须更新，否则热力图不随时间变化
    const sourceHeatmap = map.getSource("fault-heatmap");
    if (sourceHeatmap) {
      // 热力图可能需要不同的属性格式 (如 weight)，已经在 convertToFeatures 中包含 (properties.weight 暂未设置，需检查)
      // FaultDataService.convertToFeatures 返回 feature.properties.weight 吗？
      // 回看 FaultDataService.js (lines 11-53)，properties 中没有 weight。
      // 原 otnfault_map_app.js 会在 convert 后追加 weight。

      // 我们临时修正：在此处添加 weight
      const heatmapFeatures = filteredFeatures.map((f) => {
        const props = { ...f.properties, weight: 1 }; // 简单处理，每个点权重为1，或根据 count (如果是聚合数据)
        return { ...f, properties: props };
      });

      sourceHeatmap.setData({
        type: "FeatureCollection",
        features: heatmapFeatures,
      });
    }

    // 4. 更新统计
    if (this.statsControl) {
      // 提取属性数据传递给统计控件 (FaultStatisticsControl 内部会计算统计)
      const faultDataList = filteredFeatures.map((f) => f.properties);
      this.statsControl.setData(faultDataList);
    }

    // 5. 切换显示模式 (智能/热力图/点)
    let mode = "smart";
    if (this.layerToggleControl) {
      mode = this.layerToggleControl.getEffectiveMode();
    } else {
      mode = map.getZoom() >= 9 ? "points" : "heatmap";
    }

    if (mode === "points") {
      map.setLayoutProperty("fault-heatmap-layer", "visibility", "none");
      map.setLayoutProperty("fault-points-layer", "visibility", "visible");
    } else {
      // heatmap
      map.setLayoutProperty("fault-heatmap-layer", "visibility", "visible");
      map.setLayoutProperty("fault-points-layer", "visibility", "none");
    }

    // 6. 更新图例可见性
    if (this.legendControl) {
      this.legendControl.updateVisibility(mode);
    }
  },

  _loadPathMetadata() {
    // 加载 top5 路径等
    if (typeof OTNFaultMapAPI !== "undefined") {
      // 确保传入 apiKey，否则请求会失败
      const apiKey = this.config ? this.config.apiKey : null;
      console.log("[FaultMode] Loading metadata. APIKey present:", !!apiKey);

      const loadPromise = OTNFaultMapAPI.fetchPaths(apiKey).then((data) => {
        // 预处理数据：确保 total_length 存在
        if (data && Array.isArray(data)) {
          // 定义计算距离函数 (Haversine Formula)
          const calcLineDist = (coords) => {
            let total = 0;
            const R = 6371; // km
            for (let i = 0; i < coords.length - 1; i++) {
              const [lon1, lat1] = coords[i];
              const [lon2, lat2] = coords[i + 1];
              const dLat = (lat2 - lat1) * Math.PI / 180;
              const dLon = (lon2 - lon1) * Math.PI / 180;
              const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon / 2) * Math.sin(dLon / 2);
              const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
              total += R * c;
            }
            return total;
          };

          data.forEach(item => {
            if (item.properties && item.geometry) {
              // 如果 total_length 缺失或为 null，尝试从其他字段或几何计算获取
              if (item.properties.total_length == null) {
                // 1. 尝试备选字段
                if (item.properties.distance != null) item.properties.total_length = item.properties.distance;
                else if (item.properties.length != null) item.properties.total_length = item.properties.length;

                // 2. 如果仍无效，从几何计算
                if (item.properties.total_length == null) {
                  try {
                    let totalKm = 0;
                    if (item.geometry.type === 'LineString') {
                      totalKm = calcLineDist(item.geometry.coordinates);
                    } else if (item.geometry.type === 'MultiLineString') {
                      item.geometry.coordinates.forEach(coords => {
                        totalKm += calcLineDist(coords);
                      });
                    }
                    if (totalKm > 0) {
                      // 保留3位小数
                      item.properties.total_length = Math.round(totalKm * 1000) / 1000;
                    }
                  } catch (e) {
                    console.warn("[FaultMode] Failed to calculate length for path:", item.properties.id, e);
                  }
                }
              }
            }
          });
        }

        // 保存元数据到全局变量
        window.OTNPathsMetadata = data || [];
        // 更新 FlowAnimator
        if (this.flowAnimator) {
          this.flowAnimator.updatePaths(data);
        }
        return data;
      });
      // 暴露 Promise 供控件(如FaultStatisticsControl)等待
      window.OTNPathsLoadingPromise = loadPromise;
    }
  },

  /**
   * 统一路径高亮入口
   * 逻辑：隐藏静态高亮 -> 播放DeckGL流动(A-Z-A) -> 动画结束 -> 显示静态高亮
   */
  highlightPath(feature) {
    if (!feature) return;

    const map = this.map;

    // 1. 设置数据但不显示 (等待动画结束)
    const highlightSource = map.getSource("otn-paths-highlight");
    if (highlightSource) {
      highlightSource.setData(feature);
    }

    // 初始隐藏静态高亮层
    if (map.getLayer("otn-paths-highlight-outline"))
      map.setLayoutProperty(
        "otn-paths-highlight-outline",
        "visibility",
        "none"
      );
    if (map.getLayer("otn-paths-highlight-layer"))
      map.setLayoutProperty("otn-paths-highlight-layer", "visibility", "none");

    // 定义回调：显示 MapLibre 静态高亮
    const showStaticHighlight = () => {
      if (map.getLayer("otn-paths-highlight-outline"))
        map.setLayoutProperty(
          "otn-paths-highlight-outline",
          "visibility",
          "visible"
        );
      if (map.getLayer("otn-paths-highlight-layer"))
        map.setLayoutProperty(
          "otn-paths-highlight-layer",
          "visibility",
          "visible"
        );
    };

    // 2. 启动 Deck.gl 往返动画
    if (this.flowAnimator) {
      this.flowAnimator.animateHighlight(feature, showStaticHighlight);

      // Safety Timeout: 确保即使动画失败，2.5秒后也显示静态高亮
      setTimeout(showStaticHighlight, 2500);
    } else {
      // 如果没有动画器，直接显示
      showStaticHighlight();
    }
  },
};

// 辅助类：流向动画
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
    this.highlightActive = true;
    this.highlightLoopCount = 0; // 新增循环计数器
    this.highlightCallback = onComplete;
  }

  // 设置高亮路径数据 (与之前逻辑一致，处理 FeatureCollection)
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

  // 兼容旧 API
  start(feature) {
    // Top 5 如果调用 start，我们默认进行 standard highlight animation??
    // 或者直接 setHighlightPath 但无法控制 MapLibre。
    // 为了一致性，Top 5 应该调用 window.highlightPath()。
    // 但为了防止 JS 报错，这里保留 setHighlightPath，但它不会触发 callback (maplibre show)
    // 这意味着如果旧的 flyToPath 还在用 start，它将只有动画没有静态高亮(除非它自己处理了)。
    // 实际上 flyToPath 自己会设置 MapLibre 数据，所以这里只管 deck 动画即可。
    // 但用户要求"一套逻辑"。所以 flyToPath 应该被重构。
    // 这里保留 start 仅作底层兼容。
    this.setHighlightPath(feature);
    this.highlightTime = 0;
    this.highlightDirection = 1;
    this.highlightActive = true;
    // 无 callback
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

    // 背景层
    if (this.paths && this.paths.length > 0) {
      const bgLayer = new deck.TripsLayer({
        id: "fault-flow-layer",
        data: this.paths,
        getPath: (d) => d.geometry.coordinates,
        getTimestamps: (d) => d.timestamps || [0, 100],
        getColor: [255, 0, 0],
        currentTime: this.time,
        trailLength: 30,
        opacity: 0.3,
      });
      layers.push(bgLayer);
    }

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

window.initOTNMap(FaultModePlugin);

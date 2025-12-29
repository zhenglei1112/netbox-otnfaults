/**
 * NetBox OTN 故障分布图应用逻辑
 * 主要入口文件
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. 配置与初始化
  const config = window.OTNFaultMapConfig;
  let heatmapData = config.heatmapData;
  let markerData = config.markerData;
  let sitesData = config.sitesData;
  const apiKey = config.apiKey;

  // 验证并处理热力图数据

  // 如果是数组（旧格式/后端直接返回），转换为 GeoJSON
  if (Array.isArray(heatmapData)) {
    heatmapData = {
      type: "FeatureCollection",
      features: heatmapData.map((item) => ({
        type: "Feature",
        properties: {
          count: item.count || 1,
          date: item.occurrence_time,
          category: item.category,
        },
        geometry: {
          type: "Point",
          coordinates: [item.lng, item.lat],
        },
      })),
    };
  } else if (!heatmapData || !heatmapData.features) {
    console.warn("Heatmap data is missing or invalid.");
    heatmapData = { type: "FeatureCollection", features: [] };
  }

  // 确保每个 feature 都有 weight 属性供样式使用
  heatmapData.features.forEach((f) => {
    if (f.properties.weight === undefined) {
      f.properties.weight = f.properties.count || 1;
    }
  });

  // CRITICAL: 更新全局配置，以便控件访问转换后的 GeoJSON 数据
  config.heatmapData = heatmapData;
  if (!markerData) {
    console.warn("Marker data is missing.");
    markerData = [];
  }
  if (!sitesData) {
    console.warn("Sites data is missing.");
    sitesData = [];
  }

  // 初始化地图基类
  const mapBase = new NetBoxMapBase();
  window.mapBase = mapBase; // 公开以便控件访问

  let map;
  try {
    map = mapBase.init("map", apiKey);
  } catch (e) {
    NetBoxMapBase.showError("map", e.message);
    return;
  }

  // 显示加载指示器
  NetBoxMapBase.showLoading("map");

  map.on("load", () => {
    NetBoxMapBase.hideLoading("map");

    // 仅网络底图执行后处理（本地底图样式已优化，无需处理）
    if (!mapBase.useLocalBasemap) {
      // 强化中国省界
      mapBase.emphasizeChinaBoundaries();
      // 确保语言为中文
      mapBase.setLanguageToChinese();
      // 过滤无关标签
      mapBase.filterLabels();
      // 初始化高速公路盾标
      mapBase.initHighwayShields();
    }
  });

  // 添加通用控件
  mapBase.addStandardControls();
  mapBase.addHomeControl();

  // 2. 初始化业务控件

  // 图层切换控件
  const layerToggleControl = new LayerToggleControl();
  window.layerToggleControl = layerToggleControl; // 全局引用
  // 注意：位置稍后添加以确保层级

  // 分类筛选已整合到 LayerToggleControl 中
  // 设置别名以保持兼容性
  window.categoryFilterControl = layerToggleControl;

  // 故障统计面板
  const faultStatisticsControl = new FaultStatisticsControl();
  window.faultStatisticsControl = faultStatisticsControl;
  mapBase.addControl(faultStatisticsControl, "bottom-left");

  // 故障点图例控件（右下角，仅在故障点模式下显示）
  const faultLegendControl = new FaultLegendControl();
  window.faultLegendControl = faultLegendControl;
  mapBase.addControl(faultLegendControl, "bottom-right");

  // 搜索控件（左上角，视图设置按钮右侧）
  const searchControl = new SearchControl();
  window.searchControl = searchControl;
  mapBase.addControl(searchControl, "top-left");

  // 添加图层控制 (放在左上角，搜索控件左侧)
  mapBase.addControl(layerToggleControl, "top-left");

  // 测距控件 (maplibre-gl-measures)
  const MeasuresControl = window.maplibreGLMeasures?.default;
  if (MeasuresControl) {
    // 总距离标签源 ID
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
          font: "Open Sans Regular",
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
        // 延迟确保地图已加载
        setTimeout(() => {
          if (!map.getSource(TOTAL_DISTANCE_SOURCE)) {
            // 首次添加源和图层
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
                "text-font": ["Open Sans Bold"],
                "text-size": 14,
                "text-anchor": "top",
                "text-offset": [0, 1],
              },
              paint: {
                "text-color": "#1565C0",
                "text-halo-color": "#fff",
                "text-halo-width": 2,
              },
            });
          }

          // 收集所有 LineString 的总距离标签
          const totalLabels = [];
          if (features && features.features) {
            // 按原始线分组（库会将每段拆分）
            // 我们需要从 draw 控件获取原始 features
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

          // 更新数据源
          const source = map.getSource(TOTAL_DISTANCE_SOURCE);
          if (source) {
            source.setData({
              type: "FeatureCollection",
              features: totalLabels,
            });
          }

          // 确保所有测量相关图层在最顶层（解决闪烁问题）
          const measureLayers = [
            "layer-draw-labels", // 库的标签图层
            TOTAL_DISTANCE_LAYER, // 总距离标签图层
          ];
          measureLayers.forEach((layerId) => {
            if (map.getLayer(layerId)) {
              map.moveLayer(layerId);
            }
          });

          // 同时确保绘图图层也在顶层
          const drawLayers = map
            .getStyle()
            .layers.filter((l) => l.id.startsWith("gl-draw-"))
            .map((l) => l.id);
          drawLayers.forEach((layerId) => {
            if (map.getLayer(layerId)) {
              map.moveLayer(layerId);
            }
          });
        }, 100);
      },
    });

    // MONKEY PATCH: 覆盖库的默认格式化方法以本地化单位
    // library's _formatToMetricSystem returns "value unit", we want to replace "km" with "公里"
    const originalFormatMetric =
      measuresControl._formatToMetricSystem.bind(measuresControl);
    measuresControl._formatToMetricSystem = function (value) {
      const result = originalFormatMetric(value);
      return result.replace("km", "公里");
    };

    mapBase.addControl(measuresControl, "top-right");
  } else {
    console.warn("MeasuresControl 未加载，测距功能不可用");
  }

  // 3. 地图加载逻辑：添加图层和源
  map.on("load", () => {
    // 设置 globe 投影（需要在样式加载后设置）
    map.setProjection({ type: "globe" });

    // --- 热力图图层 ---
    mapBase.addGeoJsonSource("fault-heatmap", heatmapData);

    mapBase.addLayer({
      id: "fault-heatmap-layer",
      type: "heatmap",
      source: "fault-heatmap",
      maxzoom: 9,
      layout: {
        visibility: "none", // 初始隐藏，智能模式下默认时间范围为一周，显示故障点
      },
      paint: {
        "heatmap-weight": [
          "interpolate",
          ["linear"],
          ["get", "weight"],
          0,
          0,
          6,
          1,
        ],
        "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 0, 1, 9, 3],
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
        "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 7, 1, 9, 0],
      },
    });

    // Helper to move layer safety
    const moveLayerSafe = (id) => {
      if (map.getLayer(id)) map.moveLayer(id);
    };

    // Move others first
    moveLayerSafe("otn-paths-labels");
    moveLayerSafe("netbox-sites-labels");

    // Move Heatmap to ABSOLUTE top (as requested, ignoring occlusion)
    moveLayerSafe("fault-heatmap-layer");
    moveLayerSafe("fault-point-layer");

    // heatmap 的点图层（高缩放级别显示）
    mapBase.addLayer({
      id: "fault-point-layer",
      type: "circle",
      source: "fault-heatmap",
      minzoom: 7,
      layout: {
        visibility: "none", // 初始隐藏，由 updateMapState 控制
      },
      paint: {
        "circle-radius": [
          "interpolate",
          ["linear"],
          ["zoom"],
          7,
          ["interpolate", ["linear"], ["get", "weight"], 1, 1, 6, 4],
          16,
          ["interpolate", ["linear"], ["get", "weight"], 1, 5, 6, 50],
        ],
        "circle-color": [
          "interpolate",
          ["linear"],
          ["get", "weight"],
          1,
          "rgba(33,102,172,0)",
          2,
          "rgb(103,169,207)",
          3,
          "rgb(209,229,240)",
          4,
          "rgb(253,219,199)",
          5,
          "rgb(239,138,98)",
          6,
          "rgb(178,24,43)",
        ],
        "circle-stroke-color": "white",
        "circle-stroke-width": 1,
        "circle-opacity": ["interpolate", ["linear"], ["zoom"], 7, 0, 8, 1],
      },
    });

    // --- 故障标记图层 (Symbol Layer) ---
    // 将 markerData 转换为 GeoJSON 以便使用 Symbol Layer 提高性能
    const faultFeatures = markerData.map((m) => {
      const category = m.category || "other";
      const categoryColor =
        FAULT_CATEGORY_COLORS[category] || FAULT_CATEGORY_COLORS["other"];
      const dateStr = m.occurrence_time || "";
      const isoDateStr = dateStr.replace(" ", "T");

      // 获取故障状态键（用于图标匹配）
      // 使用后端传递的 status_key 字段
      const statusKey = m.status_key || "processing";
      const statusColorHex =
        FAULT_STATUS_COLORS[statusKey] || FAULT_STATUS_COLORS["processing"];

      // console.log(`故障点转换: id=${m.id}, category=${category}, statusKey=${statusKey}, date=${dateStr}`);

      return {
        type: "Feature",
        properties: {
          id: m.id || Math.random().toString(36).substr(2, 9),
          number: m.number || "未知编号",
          title: m.details || m.number || "未命名故障",
          site: m.a_site || "未指定",
          zSites: m.z_sites || "",
          status: m.status || "",
          statusKey: statusKey, // 状态键，用于图标匹配
          statusColor: m.status_color || "secondary",
          statusColorHex: statusColorHex, // 状态对应的实际颜色
          category: category,
          categoryName: FAULT_CATEGORY_NAMES[category] || category,
          date: dateStr,
          isoDate: isoDateStr,
          recoveryTime: m.recovery_time || "未恢复",
          faultDuration: m.fault_duration || "未知",
          reason: m.reason || "-",
          url: m.url || "#",
          color: categoryColor, // 保留类型颜色用于其他用途
          hasImages: m.has_images || false,
          imageCount: m.image_count || 0,
          images: JSON.stringify(m.images || []),
          impactsDetails: JSON.stringify(m.impacts_details || []), // 影响业务详情
          // 原始数据备份，用于统计等
          raw: m,
        },
        geometry: {
          type: "Point",
          coordinates: [m.lng, m.lat],
        },
      };
    });

    // 全局存储故障点数据以便筛选（在创建数据源之前）
    window.OTNMapFeatures = faultFeatures;

    // 创建故障点数据源（初始为空，由 updateMapState 填充过滤后的数据）
    mapBase.addGeoJsonSource("fault-points", {
      type: "FeatureCollection",
      features: [], // 初始为空，避免闪烁
    });

    // --- 先加载图标，完成后再创建图层 ---
    const loadIconsAndCreateLayer = () => {
      // 故障状态列表
      const statusKeys = Object.keys(FAULT_STATUS_COLORS);
      // 故障类型列表
      const categoryKeys = Object.keys(FAULT_CATEGORY_COLORS);

      // 总图标数 = 类型数 * 状态数 + 默认图标
      const totalIcons = categoryKeys.length * statusKeys.length + 1;
      let iconsLoaded = 0;

      // 图标全部加载完成后的回调：创建图层
      const onAllIconsLoaded = () => {
        // 构建 icon-image 匹配表达式
        // 使用 concat 表达式组合 category 和 status
        const iconImageExpression = [
          "concat",
          "fault-marker-",
          ["get", "category"],
          "-",
          ["coalesce", ["get", "statusKey"], "processing"],
        ];

        // 创建 Symbol Layer 显示故障点
        mapBase.addLayer({
          id: "fault-points-layer",
          type: "symbol",
          source: "fault-points",
          layout: {
            "icon-image": iconImageExpression,
            "icon-size": 1.0,
            "icon-allow-overlap": true,
            "icon-ignore-placement": true,
          },
          paint: {
            // 注意：icon-color 仅对 SDF 图标有效，普通 Canvas 图标无效
          },
        });

        // 将故障点图层移到最上层
        if (map.getLayer("fault-points-layer")) {
          map.moveLayer("fault-points-layer");
        }

        // 初始化图层可见性（默认为 points 模式）
        if (window.updateMapState) {
          window.updateMapState();
        }
      };

      const checkAllIconsLoaded = () => {
        iconsLoaded++;
        if (iconsLoaded === totalIcons) {
          onAllIconsLoaded();
        }
      };

      // 为不同故障类型创建不同形状的图标（具有象形意义）
      // category: 'fiber'=光纤波浪线, 'power'=闪电, 'pigtail'=雪花, 'device'=芯片, 'other'=警告三角
      const createMarkerIcon = (category, color) => {
        const size = 48;
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d");

        const centerX = size / 2;
        const centerY = size / 2;

        // 先绘制圆形背景
        ctx.beginPath();
        ctx.arc(centerX, centerY, 18, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = "white";
        ctx.lineWidth = 2;
        ctx.stroke();

        // 在圆形背景上绘制白色图标
        ctx.strokeStyle = "white";
        ctx.fillStyle = "white";
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";

        switch (category) {
          case "fiber":
            // 光纤图标：波浪线表示光纤/光缆
            ctx.beginPath();
            ctx.lineWidth = 2.5;
            // 绘制波浪线（光纤传输的形象）
            ctx.moveTo(centerX - 10, centerY);
            ctx.bezierCurveTo(
              centerX - 6,
              centerY - 6,
              centerX - 2,
              centerY + 6,
              centerX + 2,
              centerY
            );
            ctx.bezierCurveTo(
              centerX + 6,
              centerY - 6,
              centerX + 10,
              centerY,
              centerX + 10,
              centerY
            );
            ctx.stroke();
            // 两端的小圆点表示连接器
            ctx.beginPath();
            ctx.arc(centerX - 10, centerY, 2, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.arc(centerX + 10, centerY, 2, 0, Math.PI * 2);
            ctx.fill();
            break;

          case "power":
            // 闪电图标：电力故障
            ctx.beginPath();
            ctx.moveTo(centerX + 2, centerY - 10);
            ctx.lineTo(centerX - 4, centerY);
            ctx.lineTo(centerX, centerY);
            ctx.lineTo(centerX - 2, centerY + 10);
            ctx.lineTo(centerX + 4, centerY);
            ctx.lineTo(centerX, centerY);
            ctx.closePath();
            ctx.fill();
            break;

          case "pigtail":
            // 雪花图标：空调故障（制冷）
            ctx.lineWidth = 2;
            // 中心点
            const armLength = 9;
            // 绘制6条主臂
            for (let i = 0; i < 6; i++) {
              const angle = (i * 60 * Math.PI) / 180;
              const x1 = centerX;
              const y1 = centerY;
              const x2 = centerX + Math.cos(angle) * armLength;
              const y2 = centerY + Math.sin(angle) * armLength;

              // 主臂
              ctx.beginPath();
              ctx.moveTo(x1, y1);
              ctx.lineTo(x2, y2);
              ctx.stroke();

              // 在主臂末端添加小分支
              const branchLen = 3;
              const branchAngle1 = angle + Math.PI / 4;
              const branchAngle2 = angle - Math.PI / 4;
              const midX = centerX + Math.cos(angle) * (armLength * 0.6);
              const midY = centerY + Math.sin(angle) * (armLength * 0.6);

              ctx.beginPath();
              ctx.moveTo(midX, midY);
              ctx.lineTo(
                midX + Math.cos(branchAngle1) * branchLen,
                midY + Math.sin(branchAngle1) * branchLen
              );
              ctx.stroke();

              ctx.beginPath();
              ctx.moveTo(midX, midY);
              ctx.lineTo(
                midX + Math.cos(branchAngle2) * branchLen,
                midY + Math.sin(branchAngle2) * branchLen
              );
              ctx.stroke();
            }
            break;

          case "device":
            // 芯片/服务器图标：设备故障
            const chipSize = 12;
            const pinLen = 3;

            // 主体正方形
            ctx.fillRect(
              centerX - chipSize / 2,
              centerY - chipSize / 2,
              chipSize,
              chipSize
            );

            // 四边的引脚
            ctx.lineWidth = 1.5;
            // 上边引脚
            for (let i = -1; i <= 1; i++) {
              ctx.beginPath();
              ctx.moveTo(centerX + i * 4, centerY - chipSize / 2);
              ctx.lineTo(centerX + i * 4, centerY - chipSize / 2 - pinLen);
              ctx.stroke();
            }
            // 下边引脚
            for (let i = -1; i <= 1; i++) {
              ctx.beginPath();
              ctx.moveTo(centerX + i * 4, centerY + chipSize / 2);
              ctx.lineTo(centerX + i * 4, centerY + chipSize / 2 + pinLen);
              ctx.stroke();
            }
            // 左边引脚
            for (let i = -1; i <= 1; i++) {
              ctx.beginPath();
              ctx.moveTo(centerX - chipSize / 2, centerY + i * 4);
              ctx.lineTo(centerX - chipSize / 2 - pinLen, centerY + i * 4);
              ctx.stroke();
            }
            // 右边引脚
            for (let i = -1; i <= 1; i++) {
              ctx.beginPath();
              ctx.moveTo(centerX + chipSize / 2, centerY + i * 4);
              ctx.lineTo(centerX + chipSize / 2 + pinLen, centerY + i * 4);
              ctx.stroke();
            }

            // 中心小方块（表示核心）
            ctx.fillStyle = color;
            ctx.fillRect(centerX - 2, centerY - 2, 4, 4);
            break;

          case "other":
          default:
            // 警告三角形：其他故障
            ctx.beginPath();
            ctx.moveTo(centerX, centerY - 9);
            ctx.lineTo(centerX + 9, centerY + 7);
            ctx.lineTo(centerX - 9, centerY + 7);
            ctx.closePath();
            ctx.stroke();
            ctx.lineWidth = 1;

            // 感叹号
            ctx.beginPath();
            ctx.moveTo(centerX, centerY - 4);
            ctx.lineTo(centerX, centerY + 2);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(centerX, centerY + 5, 1.5, 0, Math.PI * 2);
            ctx.fill();
            break;
        }

        return ctx.getImageData(0, 0, size, size);
      };

      // 添加图标到地图
      const addIconToMap = (name, category, color) => {
        try {
          if (!map.hasImage(name)) {
            const imageData = createMarkerIcon(category, color);
            map.addImage(name, imageData, { pixelRatio: 2 });
          }
          checkAllIconsLoaded();
        } catch (e) {
          console.error(`图标创建失败: ${name}`, e);
          checkAllIconsLoaded();
        }
      };

      // 创建默认图标（使用 other 类型 + processing 状态）
      const defaultColor = FAULT_STATUS_COLORS["processing"];
      addIconToMap("fault-marker", "other", defaultColor);

      // 为每个类型-状态组合创建图标
      categoryKeys.forEach((category) => {
        statusKeys.forEach((status) => {
          const color = FAULT_STATUS_COLORS[status];
          const iconName = `fault-marker-${category}-${status}`;
          addIconToMap(iconName, category, color);
        });
      });
    };

    // 开始加载图标（异步，完成后自动创建图层）
    loadIconsAndCreateLayer();

    // 为故障点图层添加交互（延迟绑定，等待图层创建）
    let hoveredFeatureId = null;
    let popup = null;
    let popupTimeout;

    // 使用 setTimeout 确保图层创建完成后再绑定事件
    const bindFaultPointsInteraction = () => {
      if (!map.getLayer("fault-points-layer")) {
        // 图层尚未创建，稍后重试
        setTimeout(bindFaultPointsInteraction, 100);
        return;
      }

      // 鼠标悬停时显示弹出窗口
      map.on("mouseenter", "fault-points-layer", (e) => {
        if (e.features && e.features.length > 0) {
          const feature = e.features[0];
          hoveredFeatureId = feature.id;

          // 更改鼠标指针
          map.getCanvas().style.cursor = "pointer";

          // 清除之前的超时
          clearTimeout(popupTimeout);

          // 创建或更新弹出窗口
          const props = feature.properties;

          // 使用 PopupTemplates 服务生成弹窗内容
          const popupContent = PopupTemplates.faultPopup(props);

          if (!popup) {
            popup = new maplibregl.Popup({
              offset: 25,
              maxWidth: "300px",
              closeButton: false,
              closeOnClick: false,
            });
          }

          popup
            .setLngLat(feature.geometry.coordinates)
            .setHTML(popupContent)
            .addTo(map);
        }
      });

      // 鼠标离开时隐藏弹出窗口
      map.on("mouseleave", "fault-points-layer", () => {
        map.getCanvas().style.cursor = "";
        hoveredFeatureId = null;

        // 延迟关闭弹出窗口，给用户时间移动到弹出窗口上
        popupTimeout = setTimeout(() => {
          if (popup) {
            // 检查鼠标是否在弹出窗口上
            const popupEl = popup.getElement();
            if (popupEl && popupEl.matches(":hover")) {
              // 鼠标在弹出窗口上，不关闭，并监听离开事件
              popupEl.addEventListener("mouseleave", function closePopup() {
                popupEl.removeEventListener("mouseleave", closePopup);
                // 再次延迟一点，以防用户不小心移出
                setTimeout(() => {
                  if (popup && !popupEl.matches(":hover")) {
                    popup.remove();
                    popup = null;
                  }
                }, 200);
              });
            } else {
              popup.remove();
              popup = null;
            }
          }
        }, 300); // 增加延迟到 300ms
      });

      // 点击故障点时阻止事件传播到地图
      map.on("click", "fault-points-layer", (e) => {
        e.preventDefault();
        e.originalEvent.stopPropagation();
      });
    };

    // 开始尝试绑定交互事件
    bindFaultPointsInteraction();

    // 初始自适应边界 (已禁用：默认定位于南阳市)
    /*
        const bounds = new maplibregl.LngLatBounds();
        const features = heatmapData.features || [];
        if (features.length > 0) features.forEach(f => bounds.extend(f.geometry.coordinates));
        markerData.forEach(m => bounds.extend([m.lng, m.lat]));
        if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 50 });
        */

    // --- 异步加载数据 ---

    // 1. OTN 路径 - 统一使用 PMTiles 加载

    // 获取 PMTiles 路径服务地址
    const otnPathsPmtilesUrl = config.otnPathsPmtilesUrl;

    // 添加 PMTiles 路径数据源
    map.addSource("otn_paths_pmtiles", {
      type: "vector",
      url: "pmtiles://" + otnPathsPmtilesUrl,
    });

    // 查找插入位置：在标签下方
    const pathLayers = map.getStyle().layers;
    let firstSymbolIdForPath;
    for (const layer of pathLayers) {
      if (layer.type === "symbol") {
        firstSymbolIdForPath = layer.id;
        break;
      }
    }

    // 路径显示图层
    mapBase.addLayer(
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
          "line-color": "#00cc66",
          "line-width": 2,
          "line-opacity": 0.8,
        },
      },
      firstSymbolIdForPath
    );

    // 透明可点击区域图层
    mapBase.addLayer(
      {
        id: "otn-paths-labels",
        type: "line",
        source: "otn_paths_pmtiles",
        "source-layer": "otn_paths",
        paint: {
          "line-width": 10,
          "line-opacity": 0,
        },
      },
      firstSymbolIdForPath
    );

    // 添加路径高亮源（仍需 GeoJSON 格式）
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
      firstSymbolIdForPath
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
      firstSymbolIdForPath
    );

    // === deck.gl 流动动画控制器 ===
    const DeckGLFlowAnimator = {
      overlay: null,
      animationId: null,
      isRunning: false,
      currentTime: 0,
      direction: 1,
      maxTime: 100,
      pathData: null,
      tripsData: null,

      /**
       * 将 GeoJSON LineString 转换为 TripsLayer 数据格式
       * @param {Object} geojsonFeature - GeoJSON Feature 或 FeatureCollection
       * @returns {Array} TripsLayer 所需的数据格式
       */
      convertToTripsData: function (geojsonFeature) {
        const features =
          geojsonFeature.type === "FeatureCollection"
            ? geojsonFeature.features
            : [geojsonFeature];

        const tripsData = [];

        /**
         * 处理单条 LineString 坐标数组，生成 TripsLayer 数据项
         * @param {Array} coordinates - LineString 坐标数组
         */
        const processLineString = (coordinates) => {
          if (coordinates.length < 2) return;

          // 计算每个点的时间戳（基于累积距离）
          const timestamps = [0];
          let totalDistance = 0;

          for (let i = 1; i < coordinates.length; i++) {
            const [lon1, lat1] = coordinates[i - 1];
            const [lon2, lat2] = coordinates[i];
            // 简化的距离计算（欧氏距离，仅用于相对比例）
            const dx = lon2 - lon1;
            const dy = lat2 - lat1;
            const dist = Math.sqrt(dx * dx + dy * dy);
            totalDistance += dist;
            timestamps.push(totalDistance);
          }

          // 归一化时间戳到 [0, maxTime]
          const normalizedTimestamps = timestamps.map((t) =>
            totalDistance > 0 ? (t / totalDistance) * this.maxTime : 0
          );

          tripsData.push({
            path: coordinates,
            timestamps: normalizedTimestamps,
            color: [255, 100, 0], // 橙红色流动点
          });
        };

        features.forEach((feature, featureIndex) => {
          if (!feature.geometry) return;

          const geomType = feature.geometry.type;
          const coordinates = feature.geometry.coordinates;

          if (geomType === "LineString") {
            // 单条线
            processLineString.call(this, coordinates);
          } else if (geomType === "MultiLineString") {
            // 多段线：遍历每条子线
            coordinates.forEach((lineCoords) => {
              processLineString.call(this, lineCoords);
            });
          }
          // 其他类型（Point, Polygon等）忽略
        });

        return tripsData;
      },

      /**
       * 启动流动动画
       * @param {Object} pathData - GeoJSON 路径数据
       */
      start: function (pathData) {
        // 如果已在运行，先停止
        if (this.isRunning) {
          this.stop();
        }

        if (!pathData) return;

        this.pathData = pathData;
        this.tripsData = this.convertToTripsData(pathData);

        if (this.tripsData.length === 0) return;

        this.isRunning = true;
        this.currentTime = 0;
        this.direction = 1;

        // 创建 deck.gl overlay（如果不存在）
        if (!this.overlay) {
          this.overlay = new deck.MapboxOverlay({
            interleaved: false,
            layers: [],
          });
          map.addControl(this.overlay);
        }

        this.animate();
      },

      /**
       * 停止流动动画
       */
      stop: function () {
        this.isRunning = false;

        if (this.animationId) {
          cancelAnimationFrame(this.animationId);
          this.animationId = null;
        }

        // 清空 deck.gl 图层
        if (this.overlay) {
          this.overlay.setProps({ layers: [] });
        }

        this.pathData = null;
        this.tripsData = null;
      },

      /**
       * 动画循环
       */
      animate: function () {
        if (!this.isRunning || !this.tripsData) return;

        // 更新当前时间
        this.currentTime += 1.5 * this.direction;

        // 检查是否需要反向
        if (this.currentTime >= this.maxTime) {
          this.direction = -1;
        } else if (this.currentTime <= 0) {
          this.direction = 1;
        }

        // 创建 TripsLayer
        const tripsLayer = new deck.TripsLayer({
          id: "path-flow-trips",
          data: this.tripsData,
          getPath: (d) => d.path,
          getTimestamps: (d) => d.timestamps,
          getColor: (d) => d.color,
          opacity: 1,
          widthMinPixels: 6,
          jointRounded: true,
          capRounded: true,
          trailLength: 30,
          currentTime: this.currentTime,
          fadeTrail: true,
        });

        // 更新 overlay
        this.overlay.setProps({ layers: [tripsLayer] });

        this.animationId = requestAnimationFrame(() => this.animate());
      },
    };

    // 公开动画控制器（保持向后兼容的别名）
    window.DeckGLFlowAnimator = DeckGLFlowAnimator;
    window.PathFlowAnimator = DeckGLFlowAnimator; // 兼容旧调用

    // 鼠标交互
    map.on(
      "mouseenter",
      "otn-paths-labels",
      () => (map.getCanvas().style.cursor = "pointer")
    );
    map.on(
      "mouseleave",
      "otn-paths-labels",
      () => (map.getCanvas().style.cursor = "")
    );

    // 异步获取路径元数据用于统计功能
    OTNFaultMapAPI.fetchPaths(apiKey)
      .then((pathFeatures) => {
        window.OTNPathsMetadata = pathFeatures || [];
        // 更新统计
        if (window.faultStatisticsControl)
          window.faultStatisticsControl.update();
      })
      .catch((err) => console.warn("Failed to load path metadata:", err));

    // 2. 站点图层 (使用 sitesData 配置)
    if (sitesData && sitesData.length > 0) {
      const siteFeatures = sitesData.map((site) => ({
        type: "Feature",
        properties: {
          id: site.id,
          name: site.name,
          region: site.region || "",
          status: site.status || "",
          description: site.description || "",
          url: site.url || "#",
        },
        geometry: {
          type: "Point",
          coordinates: [site.longitude, site.latitude],
        },
      }));

      mapBase.addGeoJsonSource("netbox-sites", {
        type: "FeatureCollection",
        features: siteFeatures,
      });

      // 站点圆点
      mapBase.addLayer({
        id: "netbox-sites-layer",
        type: "circle",
        source: "netbox-sites",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 3, 10, 6],
          "circle-color": "#00aaff",
          "circle-stroke-width": 1,
          "circle-stroke-color": "#fff",
          "circle-opacity": [
            "step",
            ["zoom"],
            0.5, // Opacity 0.2 when zoom < 6 (labels hidden)
            6,
            1, // Opacity 1.0 when zoom >= 6 (labels visible)
          ],
          "circle-stroke-opacity": ["step", ["zoom"], 0.5, 6, 1],
        },
      });

      // 站点标签
      mapBase.addLayer({
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

      // 站点交互
      map.on(
        "mouseenter",
        "netbox-sites-layer",
        () => (map.getCanvas().style.cursor = "pointer")
      );
      map.on(
        "mouseleave",
        "netbox-sites-layer",
        () => (map.getCanvas().style.cursor = "")
      );

      // map.on('click', 'netbox-sites-layer', ...) REMOVED for unified handler
    }

    // Unified Click Handler for Map Layers (Sites > Paths)
    map.on("click", (e) => {
      // Priority 1: Check if a DOM Marker was clicked
      // MapLibre Markers are DOM elements. If clicked, let them handle it (default popup).
      // We detect this by checking the original event target.
      if (
        e.originalEvent &&
        e.originalEvent.target &&
        e.originalEvent.target.closest(".marker")
      ) {
        return;
      }

      const bbox = [
        [e.point.x - 5, e.point.y - 5],
        [e.point.x + 5, e.point.y + 5],
      ];
      const features = map.queryRenderedFeatures(bbox, {
        layers: ["netbox-sites-layer", "otn-paths-labels"],
      });

      if (features.length > 0) {
        // Determine priority: Site > Path
        // Since we query both, the order in 'features' usually respects layer order (top to bottom)
        // We explicit check types
        const siteFeature = features.find(
          (f) => f.layer.id === "netbox-sites-layer"
        );
        const pathFeature = features.find(
          (f) => f.layer.id === "otn-paths-labels"
        );

        if (siteFeature) {
          // Show Site Popup - 使用 PopupTemplates 服务
          const props = siteFeature.properties;
          const siteName = props.name;
          const siteId = props.id;

          // 构建故障列表详情链接
          const faultListUrl =
            window.OTNFaultMapConfig.faultListUrl ||
            "/plugins/netbox_otnfaults/faults/";
          const detailUrl = siteId
            ? `${faultListUrl}?single_site_a_id=${siteId}`
            : props.url;

          // 获取统计数据（复用 FaultStatisticsControl 的方法）
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

          // 使用 PopupTemplates 服务生成弹窗内容
          const siteUrl = props.url || "#"; // NetBox 站点对象链接
          const content = PopupTemplates.sitePopup({
            siteName,
            siteUrl,
            detailUrl,
            props,
            timeStatsHtml,
          });

          new maplibregl.Popup({ maxWidth: "300px", className: "stats-popup" })
            .setLngLat(siteFeature.geometry.coordinates)
            .setHTML(content)
            .addTo(map);
        } else if (pathFeature) {
          // Show Path Popup - 使用 PopupTemplates 服务
          const props = pathFeature.properties;
          const pathName = props.name;
          // 兼容 PMTiles (site_a/site_z) 和 API (a_site/z_site) 两种属性名格式
          const siteAName = props.a_site || props.site_a || "-";
          const siteZName = props.z_site || props.site_z || "-";

          // 先关闭现有的路径 popup（如果存在），防止其 close 事件清除新高亮
          if (window._currentPathPopup) {
            // 移除 close 事件监听器，防止清除新高亮
            window._currentPathPopup.off("close");
            window._currentPathPopup.remove();
            window._currentPathPopup = null;
          }

          // Highlight - 使用路径 ID 从 OTNPathsMetadata 获取完整几何数据
          const pathId = props.id;

          // 从缓存的完整路径数据中查找
          let highlightFeature = null;
          const cachedPaths = window.OTNPathsMetadata || [];

          if (pathId) {
            const cachedPath = cachedPaths.find(
              (p) => p.properties && p.properties.id === pathId
            );
            if (cachedPath) {
              highlightFeature = {
                type: "Feature",
                properties: cachedPath.properties,
                geometry: cachedPath.geometry,
              };
            }
          }

          // 如果缓存中找不到，回退使用 PMTiles 返回的数据
          if (!highlightFeature) {
            highlightFeature = {
              type: "Feature",
              properties: pathFeature.properties || {},
              geometry: pathFeature.geometry,
            };
          }

          // 设置高亮数据
          const highlightSource = map.getSource("otn-paths-highlight");

          if (highlightSource && highlightFeature.geometry) {
            highlightSource.setData(highlightFeature);

            // 将高亮图层移到最上层，确保不被遮挡
            if (map.getLayer("otn-paths-highlight-outline")) {
              map.moveLayer("otn-paths-highlight-outline");
            }
            if (map.getLayer("otn-paths-highlight-layer")) {
              map.moveLayer("otn-paths-highlight-layer");
            }
          }

          // 启动流动动画
          if (window.PathFlowAnimator && highlightFeature.geometry) {
            window.PathFlowAnimator.start(highlightFeature);
          }

          // 获取站点ID用于构建详情链接
          const sites = window.OTNFaultMapConfig.sitesData || [];
          const siteAObj = sites.find((s) => s.name === siteAName);
          const siteZObj = sites.find((s) => s.name === siteZName);

          // 构建故障列表详情链接
          const faultListUrl =
            window.OTNFaultMapConfig.faultListUrl ||
            "/plugins/netbox_otnfaults/faults/";
          let detailUrl = faultListUrl;
          if (siteAObj && siteZObj) {
            detailUrl = `${faultListUrl}?bidirectional_pair=${siteAObj.id},${siteZObj.id}`;
          }

          // 获取统计数据（复用 FaultStatisticsControl 的方法）
          let timeStatsHtml = "";
          if (
            window.faultStatisticsControl &&
            siteAName !== "-" &&
            siteZName !== "-"
          ) {
            const timeStats =
              window.faultStatisticsControl.calculatePathTimeStats(
                siteAName,
                siteZName
              );
            const monthlyStats =
              window.faultStatisticsControl.calculatePathMonthlyStats(
                siteAName,
                siteZName
              );
            timeStatsHtml = window.faultStatisticsControl.renderTimeStatsHtml(
              timeStats,
              "此线路",
              monthlyStats,
              detailUrl
            );
          }

          // 使用 PopupTemplates 服务生成弹窗内容
          // PMTiles 数据可能没有 url 属性，需要通过 id 构建
          // 确保 pathId 是有效的数字ID（防止 PMTiles 数据不同步时使用路径名作为ID）
          const isValidPathId =
            pathId && !isNaN(Number(pathId)) && Number(pathId) > 0;
          const pathUrl =
            props.url ||
            (isValidPathId ? `/plugins/otnfaults/paths/${pathId}/` : "#");
          const content = PopupTemplates.pathPopup({
            pathName,
            pathUrl,
            siteAName,
            siteZName,
            detailUrl,
            props,
            timeStatsHtml,
          });

          const pathPopup = new maplibregl.Popup({
            maxWidth: "300px",
            className: "stats-popup",
          })
            .setLngLat(e.lngLat)
            .setHTML(content)
            .addTo(map);

          // 保存当前 popup 的引用
          window._currentPathPopup = pathPopup;

          // 弹窗关闭时停止动画并清除高亮
          pathPopup.on("close", () => {
            if (window.PathFlowAnimator) {
              window.PathFlowAnimator.stop();
            }
            if (map.getSource("otn-paths-highlight")) {
              map.getSource("otn-paths-highlight").setData({
                type: "Feature",
                geometry: { type: "LineString", coordinates: [] },
              });
            }
            window._currentPathPopup = null;
          });
        }
      }
    });

    // 4. 中央状态管理函数
    // 4. 中央状态管理函数
    window.updateMapState = function () {
      const layerControl = window.layerToggleControl;

      // Debug Data Dates
      if (
        window.OTNFaultMapConfig &&
        window.OTNFaultMapConfig.heatmapData &&
        window.OTNFaultMapConfig.heatmapData.features
      ) {
        // 计算数据日期范围以便调试时使用
      }
      // 故障类型筛选已整合到 layerToggleControl 中
      const statsControl = window.faultStatisticsControl;

      if (!layerControl) return;

      // 使用有效模式（智能模式会根据时间范围和缩放级别自动选择）
      const mode = layerControl.getEffectiveMode
        ? layerControl.getEffectiveMode()
        : layerControl.currentMode; // 'points' | 'heatmap'
      const timeRange = layerControl.currentTimeRange;
      const selectedCategories = layerControl.getSelectedCategories
        ? layerControl.getSelectedCategories()
        : [];

      // --- 1. 计算时间过滤条件 (Days) ---
      let maxDays = 3650; // 默认很大
      switch (timeRange) {
        case "1week":
          maxDays = 7;
          break;
        case "2weeks":
          maxDays = 14;
          break;
        case "1month":
          maxDays = 30;
          break;
        case "3months":
          maxDays = 90;
          break;
        case "1year":
          maxDays = 365;
          break;
      }

      // 调试配置（全局变量，可被其他模块使用）
      window.OTN_DEBUG_MODE = true; // 启用调试模式，使用调试时间
      window.OTN_DEBUG_DATE = "2025-12-05 12:00:00"; // 调试模式固定时间

      const now = window.OTN_DEBUG_MODE
        ? new Date(window.OTN_DEBUG_DATE)
        : new Date();

      // 辅助函数：判断是否符合过滤条件
      const isFaultVisible = (faultDateStr, faultCategory) => {
        // 时间过滤
        if (!faultDateStr) return false;

        // 尝试解析日期，支持多种格式
        let d;
        if (faultDateStr.includes("T")) {
          // ISO 格式: YYYY-MM-DDTHH:MM:SS
          d = new Date(faultDateStr);
        } else {
          // 字符串格式: YYYY-MM-DD HH:MM:SS
          d = new Date(faultDateStr.replace(" ", "T"));
        }

        if (isNaN(d.getTime())) {
          console.warn("无法解析日期:", faultDateStr);
          return false;
        }

        const diffTime = now - d;
        const diffDays = diffTime / (1000 * 3600 * 24);

        // console.log(`日期检查: 故障日期=${faultDateStr}, 解析后=${d.toISOString()}, 现在=${now.toISOString()}, 差异天数=${diffDays}, 最大天数=${maxDays}`);

        if (diffDays > maxDays || diffDays < 0) return false;

        // 分类过滤
        if (!selectedCategories.includes(faultCategory)) return false;

        return true;
      };

      // --- 2. 过滤数据 ---

      // 过滤故障点数据 (Symbol Layer)
      if (window.OTNMapFeatures && map.getSource("fault-points")) {
        const pointsVisible = mode === "points";

        // 根据时间和分类过滤特征
        const filteredFeatures = window.OTNMapFeatures.filter((f) => {
          const props = f.properties;
          return isFaultVisible(props.isoDate, props.category);
        });

        // 更新数据源
        map.getSource("fault-points").setData({
          type: "FeatureCollection",
          features: pointsVisible ? filteredFeatures : [],
        });
      }

      // 过滤热力图数据
      // 热力图始终应该更新数据，但可见性由 mode 决定
      const baseHeatmapData = window.OTNFaultMapConfig.heatmapData; // 原始全量数据
      if (baseHeatmapData && baseHeatmapData.features) {
        const filteredFeatures = baseHeatmapData.features.filter((f) => {
          return isFaultVisible(f.properties.date, f.properties.category);
        });

        const filteredHeatmapData = {
          type: "FeatureCollection",
          features: filteredFeatures,
        };

        if (map.getSource("fault-heatmap")) {
          map.getSource("fault-heatmap").setData(filteredHeatmapData);
        }
      }

      // 切换图层可见性
      const heatmapVisibility = mode === "heatmap" ? "visible" : "none";
      const pointsVisibility = mode === "points" ? "visible" : "none";

      if (map.getLayer("fault-heatmap-layer")) {
        map.setLayoutProperty(
          "fault-heatmap-layer",
          "visibility",
          heatmapVisibility
        );
      }
      if (map.getLayer("fault-point-layer")) {
        map.setLayoutProperty(
          "fault-point-layer",
          "visibility",
          heatmapVisibility
        );
      }
      if (map.getLayer("fault-points-layer")) {
        map.setLayoutProperty(
          "fault-points-layer",
          "visibility",
          pointsVisibility
        );
        // 确保故障点图层始终在最上层
        map.moveLayer("fault-points-layer");
      }
      // 热力图模式时，也要确保热力图相关图层在上层
      if (mode === "heatmap") {
        if (map.getLayer("fault-heatmap-layer"))
          map.moveLayer("fault-heatmap-layer");
        if (map.getLayer("fault-point-layer"))
          map.moveLayer("fault-point-layer");
      }

      // --- 2.5. 控制图例可见性 ---
      // 故障点图例仅在故障点模式下显示，热力图模式下隐藏
      if (window.faultLegendControl) {
        window.faultLegendControl.updateVisibility(mode);
      }

      // --- 3. 更新统计面板 ---
      // 统计面板应该基于当前过滤后的数据（无论 View Mode 是什么，统计均应反映当前的过滤条件）
      if (statsControl && window.OTNMapFeatures) {
        // 找出所有符合时间与分类条件的故障
        const activeFaults = window.OTNMapFeatures.filter((f) => {
          const props = f.properties;
          return isFaultVisible(props.isoDate, props.category);
        }).map((f) => f.properties.raw); // 获取原始属性数据

        statsControl.setData(activeFaults);
      }
    };

    // 初始化调用，应用默认过滤
    // 延时一点确保控件和数据都就绪
    setTimeout(() => {
      window.updateMapState();
    }, 500);

    // 监听缩放事件，智能模式需要重新计算有效模式
    map.on("zoomend", () => {
      const layerControl = window.layerToggleControl;
      if (!layerControl) return;

      // 智能模式下，缩放变化可能导致显示模式切换，需要重新调用 updateMapState
      if (layerControl.currentMode === "smart") {
        if (window.updateMapState) {
          window.updateMapState();
        }
        return;
      }

      // 非智能模式，只需确保图层在正确的层级
      const mode = layerControl.currentMode;

      if (mode === "points" && map.getLayer("fault-points-layer")) {
        map.moveLayer("fault-points-layer");
      } else if (mode === "heatmap") {
        if (map.getLayer("fault-heatmap-layer"))
          map.moveLayer("fault-heatmap-layer");
        if (map.getLayer("fault-point-layer"))
          map.moveLayer("fault-point-layer");
      }
    });
  }); // end map.on('load')
});

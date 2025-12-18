/**
 * NetBox OTN 故障分布图应用逻辑
 * 主要入口文件
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. 配置与初始化
    const config = window.OTNFaultMapConfig;
    let heatmapData = config.heatmapData;
    let markerData = config.markerData;
    let sitesData = config.sitesData;
    const apiKey = config.apiKey;

    // 验证并处理热力图数据
    console.log('Received Heatmap Data:', heatmapData);
    
    // 如果是数组（旧格式/后端直接返回），转换为 GeoJSON
    if (Array.isArray(heatmapData)) {
        heatmapData = {
            type: 'FeatureCollection',
            features: heatmapData.map(item => ({
                type: 'Feature',
                properties: {
                    count: item.count || 1,
                    date: item.occurrence_time,
                    category: item.category
                },
                geometry: {
                    type: 'Point',
                    coordinates: [item.lng, item.lat]
                }
            }))
        };
    } else if (!heatmapData || !heatmapData.features) {
        console.warn('Heatmap data is missing or invalid.');
        heatmapData = { type: 'FeatureCollection', features: [] };
    }
    
    // 确保每个 feature 都有 weight 属性供样式使用
    heatmapData.features.forEach(f => {
        if (f.properties.weight === undefined) {
            f.properties.weight = f.properties.count || 1;
        }
    });

    // CRITICAL: 更新全局配置，以便控件访问转换后的 GeoJSON 数据
    config.heatmapData = heatmapData;
    if (!markerData) {
        console.warn('Marker data is missing.');
        markerData = [];
    }
    if (!sitesData) {
        console.warn('Sites data is missing.');
        sitesData = [];
    }

    // 初始化地图基类
    const mapBase = new NetBoxMapBase();
    window.mapBase = mapBase; // 公开以便控件访问

    let map;
    try {
        map = mapBase.init('map', apiKey);
    } catch (e) {
        NetBoxMapBase.showError('map', e.message);
        return;
    }

    // 显示加载指示器
    NetBoxMapBase.showLoading('map');

    map.on('load', () => {
        NetBoxMapBase.hideLoading('map');

        // 强化中国省界
        mapBase.emphasizeChinaBoundaries();
        // 确保语言为中文
        mapBase.setLanguageToChinese();
        
        // 过滤无关标签
        mapBase.filterLabels();
    });

    // 添加通用控件
    mapBase.addStandardControls();
    mapBase.addHomeControl();

    // 2. 初始化业务控件
    
    // 图层切换控件
    const layerToggleControl = new LayerToggleControl();
    window.layerToggleControl = layerToggleControl; // 全局引用
    // 注意：位置稍后添加以确保层级
    
    // 分类筛选控件
    const categoryFilterControl = new CategoryFilterControl();
    window.categoryFilterControl = categoryFilterControl;
    mapBase.addControl(categoryFilterControl, 'top-right');

    // 故障统计面板
    const faultStatisticsControl = new FaultStatisticsControl();
    window.faultStatisticsControl = faultStatisticsControl;
    mapBase.addControl(faultStatisticsControl, 'bottom-left');
    
    // 添加图层控制 (放在左上角，确保在其他左侧控件之前)
    mapBase.addControl(layerToggleControl, 'top-left');


    // 3. 地图加载逻辑：添加图层和源
    map.on('load', () => {
        
        // 设置 globe 投影（需要在样式加载后设置）
        map.setProjection({ type: 'globe' });
        console.log('已设置 globe 投影模式');
        
        // --- 热力图图层 ---
        mapBase.addGeoJsonSource('fault-heatmap', heatmapData);

        mapBase.addLayer({
            id: 'fault-heatmap-layer',
            type: 'heatmap',
            source: 'fault-heatmap',
            maxzoom: 9,
            layout: {
                'visibility': 'none'  // 初始隐藏，默认模式是 points
            },
            paint: {
                'heatmap-weight': [
                    'interpolate', ['linear'], ['get', 'weight'],
                    0, 0,
                    6, 1
                ],
                'heatmap-intensity': [
                    'interpolate', ['linear'], ['zoom'],
                    0, 1,
                    9, 3
                ],
                'heatmap-color': [
                    'interpolate', ['linear'], ['heatmap-density'],
                    0, 'rgba(33,102,172,0)',
                    0.2, 'rgb(103,169,207)',
                    0.4, 'rgb(209,229,240)',
                    0.6, 'rgb(253,219,199)',
                    0.8, 'rgb(239,138,98)',
                    1, 'rgb(178,24,43)'
                ],
                'heatmap-radius': [
                    'interpolate', ['linear'], ['zoom'],
                    0, 2,
                    9, 20
                ],
                'heatmap-opacity': [
                    'interpolate', ['linear'], ['zoom'],
                    7, 1,
                    9, 0
                ]
            }
        });
        
        // Helper to move layer safety
        const moveLayerSafe = (id) => {
            if (map.getLayer(id)) map.moveLayer(id);
        };

        // Move others first
        moveLayerSafe('otn-paths-labels'); 
        moveLayerSafe('netbox-sites-labels'); 

        // Move Heatmap to ABSOLUTE top (as requested, ignoring occlusion)
        moveLayerSafe('fault-heatmap-layer');
        moveLayerSafe('fault-point-layer');
        
        // heatmap 的点图层（高缩放级别显示）
        mapBase.addLayer({
            id: 'fault-point-layer',
            type: 'circle',
            source: 'fault-heatmap',
            minzoom: 7,
            layout: {
                'visibility': 'none'  // 初始隐藏，默认模式是 points
            },
            paint: {
                'circle-radius': [
                    'interpolate', ['linear'], ['zoom'],
                    7, ['interpolate', ['linear'], ['get', 'weight'], 1, 1, 6, 4],
                    16, ['interpolate', ['linear'], ['get', 'weight'], 1, 5, 6, 50]
                ],
                'circle-color': [
                    'interpolate', ['linear'], ['get', 'weight'],
                    1, 'rgba(33,102,172,0)',
                    2, 'rgb(103,169,207)',
                    3, 'rgb(209,229,240)',
                    4, 'rgb(253,219,199)',
                    5, 'rgb(239,138,98)',
                    6, 'rgb(178,24,43)'
                ],
                'circle-stroke-color': 'white',
                'circle-stroke-width': 1,
                'circle-opacity': [
                    'interpolate', ['linear'], ['zoom'],
                    7, 0,
                    8, 1
                ]
            }
        });

        // --- 故障标记图层 (Symbol Layer) ---
        // 将 markerData 转换为 GeoJSON 以便使用 Symbol Layer 提高性能
        console.log('=== 开始创建故障点数据 ===');
        console.log('FAULT_CATEGORY_COLORS 是否定义:', typeof FAULT_CATEGORY_COLORS !== 'undefined');
        console.log('FAULT_CATEGORY_NAMES 是否定义:', typeof FAULT_CATEGORY_NAMES !== 'undefined');
        console.log('原始 markerData:', markerData);
        const faultFeatures = markerData.map(m => {
            const category = m.category || 'other';
            const color = FAULT_CATEGORY_COLORS[category] || FAULT_CATEGORY_COLORS['other'];
            const dateStr = m.occurrence_time || '';
            const isoDateStr = dateStr.replace(' ', 'T');
            
            // console.log(`故障点转换: id=${m.id}, category=${category}, date=${dateStr}, lng=${m.lng}, lat=${m.lat}`);
            
            return {
                type: 'Feature',
                properties: {
                    id: m.id || Math.random().toString(36).substr(2, 9),
                    number: m.number || '未知编号',
                    title: m.details || m.number || '未命名故障',
                    site: m.a_site || '未指定',
                    zSites: m.z_sites || '',
                    status: m.status || '',
                    statusColor: m.status_color || 'secondary',
                    category: category,
                    categoryName: FAULT_CATEGORY_NAMES[category] || category,
                    date: dateStr,
                    isoDate: isoDateStr,
                    recoveryTime: m.recovery_time || '未恢复',
                    faultDuration: m.fault_duration || '未知',
                    reason: m.reason || '-',
                    url: m.url || '#',
                    color: color,
                    hasImages: m.has_images || false,
                    imageCount: m.image_count || 0,
                    images: JSON.stringify(m.images || []),
                    // 原始数据备份，用于统计等
                    raw: m
                },
                geometry: {
                    type: 'Point',
                    coordinates: [m.lng, m.lat]
                }
            };
        });
        
        console.log(`转换后的故障点特征数: ${faultFeatures.length}`);
        
        // 全局存储故障点数据以便筛选（在创建数据源之前）
        window.OTNMapFeatures = faultFeatures;
        
        // 创建故障点数据源（初始为空，由 updateMapState 填充过滤后的数据）
        mapBase.addGeoJsonSource('fault-points', {
            type: 'FeatureCollection',
            features: []  // 初始为空，避免闪烁
        });
        
        console.log('故障点数据源已创建（初始为空）');
        
        // --- 先加载图标，完成后再创建图层 ---
        const loadIconsAndCreateLayer = () => {
            let iconsLoaded = 0;
            const totalIcons = Object.keys(FAULT_CATEGORY_COLORS).length + 1; // 所有分类图标 + 默认图标
            
            // 图标全部加载完成后的回调：创建图层
            const onAllIconsLoaded = () => {
                console.log('所有故障点图标已加载，开始创建图层...');
                
                // 创建 Symbol Layer 显示故障点
                mapBase.addLayer({
                    id: 'fault-points-layer',
                    type: 'symbol',
                    source: 'fault-points',
                    layout: {
                        'icon-image': [
                            'match',
                            ['get', 'category'],
                            ...Object.keys(FAULT_CATEGORY_COLORS).flatMap(cat => [cat, `fault-marker-${cat}`]),
                            'fault-marker' // 默认图标
                        ],
                        'icon-size': 1.0,
                        'icon-allow-overlap': true,
                        'icon-ignore-placement': true
                    },
                    paint: {
                        // 注意：icon-color 仅对 SDF 图标有效，普通 SVG 图标无效
                        // 我们已经通过不同颜色的图标变体实现了颜色区分
                    }
                });
                
                console.log('故障点图层已创建');
                
                // 将故障点图层移到最上层
                if (map.getLayer('fault-points-layer')) {
                    map.moveLayer('fault-points-layer');
                    console.log('故障点图层已移到最上层');
                }
                
                // 初始化图层可见性（默认为 points 模式）
                if (window.updateMapState) {
                    window.updateMapState();
                }
            };
            
            const checkAllIconsLoaded = () => {
                iconsLoaded++;
                console.log(`图标加载进度: ${iconsLoaded}/${totalIcons}`);
                if (iconsLoaded === totalIcons) {
                    onAllIconsLoaded();
                }
            };
            
            // 使用 Canvas 绘制地图标记图标
            const createMarkerIcon = (color) => {
                const size = 48;  // 增大图标尺寸
                const canvas = document.createElement('canvas');
                canvas.width = size;
                canvas.height = size;
                const ctx = canvas.getContext('2d');
                
                // 绘制水滴形状的标记
                ctx.beginPath();
                // 水滴形状：上半部分是圆形，下半部分是尖角
                const centerX = size / 2;
                const topY = 8;
                const radius = 14;  // 增大半径
                
                // 上半部分圆弧
                ctx.arc(centerX, topY + radius, radius, Math.PI, 0, false);
                // 下半部分三角形（尖角）
                ctx.lineTo(centerX, size - 4);
                ctx.lineTo(centerX - radius, topY + radius);
                ctx.closePath();
                
                // 填充颜色
                ctx.fillStyle = color;
                ctx.fill();
                
                // 白色边框
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 2;
                ctx.stroke();
                
                // 中心白点
                ctx.beginPath();
                ctx.arc(centerX, topY + radius, 4, 0, Math.PI * 2);  // 增大白点
                ctx.fillStyle = 'white';
                ctx.fill();
                
                return ctx.getImageData(0, 0, size, size);
            };
            
            // 添加图标到地图
            const addIconToMap = (name, color) => {
                try {
                    if (!map.hasImage(name)) {
                        const imageData = createMarkerIcon(color);
                        map.addImage(name, imageData, { pixelRatio: 2 });
                        console.log(`图标已创建: ${name}`);
                    }
                    checkAllIconsLoaded();
                } catch (e) {
                    console.error(`图标创建失败: ${name}`, e);
                    checkAllIconsLoaded();
                }
            };
            
            // 创建默认图标
            const defaultColor = FAULT_CATEGORY_COLORS[Object.keys(FAULT_CATEGORY_COLORS)[0]];
            addIconToMap('fault-marker', defaultColor);
            
            // 创建各分类颜色的图标变体
            Object.keys(FAULT_CATEGORY_COLORS).forEach(category => {
                const color = FAULT_CATEGORY_COLORS[category];
                addIconToMap(`fault-marker-${category}`, color);
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
            if (!map.getLayer('fault-points-layer')) {
                // 图层尚未创建，稍后重试
                setTimeout(bindFaultPointsInteraction, 100);
                return;
            }
            
            console.log('绑定故障点图层交互事件...');
        
        // 鼠标悬停时显示弹出窗口
        map.on('mouseenter', 'fault-points-layer', (e) => {
            if (e.features && e.features.length > 0) {
                const feature = e.features[0];
                hoveredFeatureId = feature.id;
                
                // 更改鼠标指针
                map.getCanvas().style.cursor = 'pointer';
                
                // 清除之前的超时
                clearTimeout(popupTimeout);
                
                // 创建或更新弹出窗口
                const props = feature.properties;
                
                // 提取历时中的小时数（格式：xxx.xx小时）
                let durationHtml = '';
                if (props.faultDuration && props.faultDuration !== '未知') {
                    // 从 "x天x小时x分x秒（xx.xx小时）" 格式中提取小时数
                    const hourMatch = props.faultDuration.match(/（([\d.]+)小时）/);
                    const hours = hourMatch ? hourMatch[1] : props.faultDuration;
                    durationHtml = `<div class="popup-row"><span class="popup-label">历时</span><span>${hours}小时</span></div>`;
                }
                
                // Z端站点（仅在非空时显示）
                const zSitesHtml = props.zSites && props.zSites !== '未指定' ? 
                    `<div class="popup-row"><span class="popup-label">Z端</span><span>${props.zSites}</span></div>` : '';
                
                // 图片（若有）
                let imagesHtml = '';
                if (props.hasImages) {
                    try {
                        const images = typeof props.images === 'string' ? JSON.parse(props.images) : props.images;
                        if (images && images.length > 0) {
                            const thumbnails = images.slice(0, 3).map(img => 
                                `<a href="${img.url}" target="_blank" title="${img.name}"><img src="${img.url}" style="width:40px;height:40px;object-fit:cover;border-radius:3px;" alt="${img.name}"></a>`
                            ).join('');
                            const moreText = images.length > 3 ? `<span class="text-muted small">+${images.length - 3}</span>` : '';
                            imagesHtml = `<div class="popup-row" style="align-items:flex-start;"><span class="popup-label">图片</span><div class="d-flex gap-1 flex-wrap">${thumbnails}${moreText}</div></div>`;
                        }
                    } catch (e) {
                        console.warn('解析图片数据失败:', e);
                    }
                }
                
                // NetBox 颜色映射：将后端传递的颜色名转换为 Bootstrap 类名
                // 故障类型颜色：power=orange, fiber=red, pigtail=blue, device=green, other=gray
                // 故障状态颜色：processing=orange, temporary_recovery=blue, suspended=yellow, closed=green
                const categoryColorMap = {
                    'power': '#f5a623',    // orange
                    'fiber': '#dc3545',    // red
                    'pigtail': '#0d6efd',  // blue
                    'device': '#198754',   // green
                    'other': '#6c757d'     // gray
                };
                const statusColorMap = {
                    'orange': '#f5a623',
                    'blue': '#0d6efd',
                    'yellow': '#ffc107',
                    'green': '#198754',
                    'gray': '#6c757d',
                    'red': '#dc3545',
                    'secondary': '#6c757d'
                };
                
                const categoryBgColor = categoryColorMap[props.category] || '#6c757d';
                const statusBgColor = statusColorMap[props.statusColor] || '#6c757d';
                
                const popupContent = `
                    <style>
                        .fault-popup { font-size: 13px; line-height: 1.5; }
                        .fault-popup .popup-sites { font-weight: 600; color: #212529; padding-bottom: 6px; margin-bottom: 6px; border-bottom: 1px solid #dee2e6; }
                        .fault-popup .popup-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; color: #fff !important; }
                        .fault-popup .popup-badges { display: flex; gap: 6px; margin-bottom: 8px; }
                        .fault-popup .popup-row { display: flex; margin-bottom: 4px; }
                        .fault-popup .popup-label { color: #6c757d; min-width: 52px; flex-shrink: 0; }
                        .fault-popup .popup-row span:last-child { color: #212529; }
                        .fault-popup .popup-footer { padding-top: 6px; margin-top: 6px; border-top: 1px solid #dee2e6; }
                        .fault-popup .popup-footer a { font-weight: 600; color: var(--bs-link-color, #0097a7); text-decoration: none; transition: color 0.15s ease-in-out; }
                        .fault-popup .popup-footer a:hover { color: var(--bs-link-hover-color, #007c8a); text-decoration: underline; }
                    </style>
                    <div class="fault-popup">
                        <div class="popup-sites">${props.site}${props.zSites && props.zSites !== '未指定' ? ' —— ' + props.zSites : ''}</div>
                        <div class="popup-badges"><span class="popup-badge" style="background-color: ${categoryBgColor};">${props.categoryName}</span><span class="popup-badge" style="background-color: ${statusBgColor};">${props.status}</span></div>
                        <div class="popup-row"><span class="popup-label">中断</span><span>${props.date}</span></div>
                        <div class="popup-row"><span class="popup-label">恢复</span><span>${props.recoveryTime}</span></div>
                        ${durationHtml}
                        <div class="popup-row"><span class="popup-label">原因</span><span>${props.reason}</span></div>
                        ${imagesHtml}
                        <div class="popup-footer">
                            <a href="${props.url}" target="_blank">${props.number}</a>
                        </div>
                    </div>
                `;
                
                if (!popup) {
                    popup = new maplibregl.Popup({
                        offset: 25,
                        maxWidth: '300px',
                        closeButton: false,
                        closeOnClick: false
                    });
                }
                
                popup
                    .setLngLat(feature.geometry.coordinates)
                    .setHTML(popupContent)
                    .addTo(map);
            }
        });
        
        // 鼠标离开时隐藏弹出窗口
        map.on('mouseleave', 'fault-points-layer', () => {
            map.getCanvas().style.cursor = '';
            hoveredFeatureId = null;
            
            // 延迟关闭弹出窗口，给用户时间移动到弹出窗口上
            popupTimeout = setTimeout(() => {
                if (popup) {
                    // 检查鼠标是否在弹出窗口上
                    const popupEl = popup.getElement();
                    if (popupEl && popupEl.matches(':hover')) {
                        // 鼠标在弹出窗口上，不关闭，并监听离开事件
                        popupEl.addEventListener('mouseleave', function closePopup() {
                            popupEl.removeEventListener('mouseleave', closePopup);
                            // 再次延迟一点，以防用户不小心移出
                            setTimeout(() => {
                                if (popup && !popupEl.matches(':hover')) {
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
            }, 300);  // 增加延迟到 300ms
        });
        
        // 点击故障点时阻止事件传播到地图
        map.on('click', 'fault-points-layer', (e) => {
            e.preventDefault();
            e.originalEvent.stopPropagation();
        });
        
            console.log('故障点图层交互事件绑定完成');
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

        
        // 1. OTN 路径
        OTNFaultMapAPI.fetchPaths(apiKey).then(pathFeatures => {
            console.log('Loaded OTN Path Features:', pathFeatures);
            
            // 确保 pathFeatures 是有效数组
            if (!Array.isArray(pathFeatures)) {
                console.error('pathFeatures is not an array:', pathFeatures);
                pathFeatures = [];
            }
            
            // 全局存储以进行统计匹配
            window.OTNPathsMetadata = pathFeatures;
            
            // 更新统计
            if (window.faultStatisticsControl) window.faultStatisticsControl.update();

            mapBase.addGeoJsonSource('otn-paths', {
                type: 'FeatureCollection',
                features: pathFeatures
            });

            // 查找插入位置：在标签下方
            const layers = map.getStyle().layers;
            let firstSymbolId;
            for (const layer of layers) {
                if (layer.type === 'symbol') {
                    firstSymbolId = layer.id;
                    break;
                }
            }

            // 路径图层
            // 获取主题颜色（简化处理，使用固定色或 CSS 变量无法直接在 JS paint properties 中使用，需预处理）
            // 这里使用默认色
            mapBase.addLayer({
                id: 'otn-paths-layer',
                type: 'line',
                source: 'otn-paths',
                layout: {
                    'line-join': 'round',
                    'line-cap': 'round',
                    'visibility': 'visible'
                },
                paint: {
                    'line-color': '#00cc66', // 默认绿色
                    'line-width': 2,
                    'line-opacity': 0.8
                }
            }, firstSymbolId);

            // 路径交互：高亮和弹窗
            mapBase.addGeoJsonSource('otn-paths-highlight', {
                type: 'Feature',
                geometry: { type: 'LineString', coordinates: [] }
            });
            mapBase.addLayer({
                id: 'otn-paths-highlight-layer',
                type: 'line',
                source: 'otn-paths-highlight',
                paint: {
                    'line-color': '#FFD700', // Gold
                    'line-width': 4,
                    'line-opacity': 1
                }
            }, firstSymbolId);
            
            mapBase.addLayer({
                id: 'otn-paths-labels', // 透明路径用于扩大点击区域
                type: 'line',
                source: 'otn-paths',
                paint: {
                    'line-width': 10,
                    'line-opacity': 0
                }
            }, firstSymbolId);

            // 鼠标交互
            map.on('mouseenter', 'otn-paths-labels', () => map.getCanvas().style.cursor = 'pointer');
            map.on('mouseleave', 'otn-paths-labels', () => map.getCanvas().style.cursor = '');
            
            // map.on('click', 'otn-paths-labels', ...) REMOVED for unified handler
        }).catch(err => console.error('Failed to load paths:', err));

        // 2. 站点图层 (使用 sitesData 配置)
        if (sitesData && sitesData.length > 0) {
            const siteFeatures = sitesData.map(site => ({
                type: 'Feature',
                properties: {
                    id: site.id,
                    name: site.name,
                    region: site.region || '',
                    status: site.status || '',
                    description: site.description || '',
                    url: site.url || '#'
                },
                geometry: {
                    type: 'Point',
                    coordinates: [site.longitude, site.latitude]
                }
            }));
            
            mapBase.addGeoJsonSource('netbox-sites', {
                type: 'FeatureCollection',
                features: siteFeatures
            });
            
            // 站点圆点
            mapBase.addLayer({
                id: 'netbox-sites-layer',
                type: 'circle',
                source: 'netbox-sites',
                paint: {
                    'circle-radius': [
                        'interpolate', ['linear'], ['zoom'],
                        4, 3,
                        10, 6
                    ],
                    'circle-color': '#00aaff',
                    'circle-stroke-width': 1,
                    'circle-stroke-color': '#fff',
                    'circle-opacity': [
                        'step', ['zoom'],
                        0.2, // Opacity 0.2 when zoom < 6 (labels hidden)
                        6, 1 // Opacity 1.0 when zoom >= 6 (labels visible)
                    ],
                    'circle-stroke-opacity': [
                        'step', ['zoom'],
                        0.2,
                        6, 1
                    ]
                }
            });
            
            // 站点标签
            mapBase.addLayer({
                id: 'netbox-sites-labels',
                type: 'symbol',
                source: 'netbox-sites',
                layout: {
                    'text-field': ['get', 'name'],
                    'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
                    'text-offset': [0, 1.2],
                    'text-anchor': 'top',
                    'text-size': 12
                },
                paint: {
                    'text-color': '#333',
                    'text-halo-color': '#fff',
                    'text-halo-width': 1
                },
                minzoom: 6
            });
            
            // 站点交互
            map.on('mouseenter', 'netbox-sites-layer', () => map.getCanvas().style.cursor = 'pointer');
            map.on('mouseleave', 'netbox-sites-layer', () => map.getCanvas().style.cursor = '');
            
            // map.on('click', 'netbox-sites-layer', ...) REMOVED for unified handler
        }
        
        // Unified Click Handler for Map Layers (Sites > Paths)
        map.on('click', (e) => {
            // Priority 1: Check if a DOM Marker was clicked
            // MapLibre Markers are DOM elements. If clicked, let them handle it (default popup).
            // We detect this by checking the original event target.
            if (e.originalEvent && e.originalEvent.target && e.originalEvent.target.closest('.marker')) {
                return;
            }

            const bbox = [
                [e.point.x - 5, e.point.y - 5],
                [e.point.x + 5, e.point.y + 5]
            ];
            const features = map.queryRenderedFeatures(bbox, {
                layers: ['netbox-sites-layer', 'otn-paths-labels']
            });

            if (features.length > 0) {
                // Determine priority: Site > Path
                // Since we query both, the order in 'features' usually respects layer order (top to bottom)
                // We explicit check types
                const siteFeature = features.find(f => f.layer.id === 'netbox-sites-layer');
                const pathFeature = features.find(f => f.layer.id === 'otn-paths-labels');
                
                if (siteFeature) {
                    // Show Site Popup
                     const props = siteFeature.properties;
                    let content = `
                    <h6>${props.name}</h6>
                    <table class="table table-sm table-striped">
                        <tr><td>区域:</td><td>${props.region}</td></tr>
                        <tr><td>状态:</td><td>${props.status}</td></tr>
                    </table>
                    <a href="${props.url}" target="_blank">查看详情</a>`;
                    
                    new maplibregl.Popup()
                        .setLngLat(siteFeature.geometry.coordinates) // Use feature coordinates for point
                        .setHTML(content)
                        .addTo(map);
                } else if (pathFeature) {
                    // Show Path Popup
                    const props = pathFeature.properties;
                    // Highlight
                    map.getSource('otn-paths-highlight').setData(pathFeature);
    
                    let content = `
                        <h6>${props.name}</h6>
                        <table class="table table-sm mb-0">
                            <tr><td>状态:</td><td>${props.operational_status}</td></tr>
                            <tr><td>A端:</td><td>${props.a_site || '-'}</td></tr>
                            <tr><td>Z端:</td><td>${props.z_site || '-'}</td></tr>
                            <tr><td>长度:</td><td>${props.total_length || '-'} km</td></tr>
                        </table>
                    `;
                    new maplibregl.Popup()
                        .setLngLat(e.lngLat) // Use click location for line
                        .setHTML(content)
                        .addTo(map);
                }
            }
        });
        
    // 4. 中央状态管理函数
    // 4. 中央状态管理函数
    window.updateMapState = function() {
        console.log('UpdateMapState: Starting update...');
        
        const layerControl = window.layerToggleControl;
        
        // Debug Data Dates
        if (window.OTNFaultMapConfig && window.OTNFaultMapConfig.heatmapData && window.OTNFaultMapConfig.heatmapData.features) {
            const dates = window.OTNFaultMapConfig.heatmapData.features.map(f => new Date(f.properties.date).getTime()).filter(t => !isNaN(t));
            if (dates.length > 0) {
                const minDate = new Date(Math.min(...dates));
                const maxDate = new Date(Math.max(...dates));
                console.log(`Debug Data Range: Min=${minDate.toISOString()}, Max=${maxDate.toISOString()}`);
            }
        }
        const categoryControl = window.categoryFilterControl;
        const statsControl = window.faultStatisticsControl;
        
        if (!layerControl || !categoryControl) return;
        
        const mode = layerControl.currentMode; // 'points' | 'heatmap'
        const timeRange = layerControl.currentTimeRange;
        const selectedCategories = categoryControl.getSelectedCategories();
        
        // --- 1. 计算时间过滤条件 (Days) ---
        let maxDays = 3650; // 默认很大
        switch(timeRange) {
            case '1week': maxDays = 7; break;
            case '2weeks': maxDays = 14; break;
            case '1month': maxDays = 30; break;
            case '3months': maxDays = 90; break;
            case '1year': maxDays = 365; break;
        }

        
        // 调试配置
        const DEBUG_MODE = true; // 启用调试模式，使用调试时间
        const DEBUG_DATE = '2025-12-05 12:00:00'; // 调试模式固定时间
        
        const now = DEBUG_MODE ? new Date(DEBUG_DATE) : new Date();
        if (DEBUG_MODE) {
            console.log(`[Debug] Mode ON. Current Time Fixed to: ${now.toLocaleString()}`);
        }

        // 辅助函数：判断是否符合过滤条件
        const isFaultVisible = (faultDateStr, faultCategory) => {
            // 时间过滤
            if (!faultDateStr) return false;
            
            // 尝试解析日期，支持多种格式
            let d;
            if (faultDateStr.includes('T')) {
                // ISO 格式: YYYY-MM-DDTHH:MM:SS
                d = new Date(faultDateStr);
            } else {
                // 字符串格式: YYYY-MM-DD HH:MM:SS
                d = new Date(faultDateStr.replace(' ', 'T'));
            }
            
            if (isNaN(d.getTime())) {
                console.warn('无法解析日期:', faultDateStr);
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
        if (window.OTNMapFeatures && map.getSource('fault-points')) {
            const pointsVisible = (mode === 'points');
            
            // 根据时间和分类过滤特征
            const filteredFeatures = window.OTNMapFeatures.filter(f => {
                const props = f.properties;
                return isFaultVisible(props.isoDate, props.category);
            });
            
            console.log(`故障点过滤: mode=${mode}, pointsVisible=${pointsVisible}, 总特征数=${window.OTNMapFeatures.length}, 过滤后特征数=${filteredFeatures.length}`);
            console.log('时间范围:', timeRange, '最大天数:', maxDays);
            console.log('选中分类:', selectedCategories);
            
            // 更新数据源
            map.getSource('fault-points').setData({
                type: 'FeatureCollection',
                features: pointsVisible ? filteredFeatures : []
            });
            
            // 调试：检查数据源是否设置成功
            setTimeout(() => {
                const source = map.getSource('fault-points');
                if (source) {
                    const data = source._data;
                    console.log('故障点数据源特征数:', data ? data.features.length : 0);
                }
            }, 100);
        }
        
        // 过滤热力图数据
        // 热力图始终应该更新数据，但可见性由 mode 决定
        const baseHeatmapData = window.OTNFaultMapConfig.heatmapData; // 原始全量数据
        if (baseHeatmapData && baseHeatmapData.features) {
             const filteredFeatures = baseHeatmapData.features.filter(f => {
                return isFaultVisible(f.properties.date, f.properties.category);
            });
            
            const filteredHeatmapData = {
                type: 'FeatureCollection',
                features: filteredFeatures
            };
            
            if (map.getSource('fault-heatmap')) {
                map.getSource('fault-heatmap').setData(filteredHeatmapData);
            }
        }
        
        // 切换图层可见性
        const heatmapVisibility = (mode === 'heatmap') ? 'visible' : 'none';
        const pointsVisibility = (mode === 'points') ? 'visible' : 'none';
        
        if (map.getLayer('fault-heatmap-layer')) {
            map.setLayoutProperty('fault-heatmap-layer', 'visibility', heatmapVisibility);
        }
        if (map.getLayer('fault-point-layer')) {
            map.setLayoutProperty('fault-point-layer', 'visibility', heatmapVisibility);
        }
        if (map.getLayer('fault-points-layer')) {
            map.setLayoutProperty('fault-points-layer', 'visibility', pointsVisibility);
            // 确保故障点图层始终在最上层
            map.moveLayer('fault-points-layer');
        }
        // 热力图模式时，也要确保热力图相关图层在上层
        if (mode === 'heatmap') {
            if (map.getLayer('fault-heatmap-layer')) map.moveLayer('fault-heatmap-layer');
            if (map.getLayer('fault-point-layer')) map.moveLayer('fault-point-layer');
        }
        
        // --- 3. 更新统计面板 ---
        // 统计面板应该基于当前过滤后的数据（无论 View Mode 是什么，统计均应反映当前的过滤条件）
        if (statsControl && window.OTNMapFeatures) {
            // 找出所有符合时间与分类条件的故障
            const activeFaults = window.OTNMapFeatures
                .filter(f => {
                    const props = f.properties;
                    return isFaultVisible(props.isoDate, props.category);
                })
                .map(f => f.properties.raw); // 获取原始属性数据
                
            statsControl.setData(activeFaults);
        }
    };
    
    // 初始化调用，应用默认过滤
    // 延时一点确保控件和数据都就绪
    setTimeout(() => {
        window.updateMapState();
    }, 500);
    
    // 监听缩放事件，确保故障图层始终在最上层
    map.on('zoomend', () => {
        const layerControl = window.layerToggleControl;
        const mode = layerControl ? layerControl.currentMode : 'points';
        
        if (mode === 'points' && map.getLayer('fault-points-layer')) {
            map.moveLayer('fault-points-layer');
        } else if (mode === 'heatmap') {
            if (map.getLayer('fault-heatmap-layer')) map.moveLayer('fault-heatmap-layer');
            if (map.getLayer('fault-point-layer')) map.moveLayer('fault-point-layer');
        }
    });

    }); // end map.on('load')
});

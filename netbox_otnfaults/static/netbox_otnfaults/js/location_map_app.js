/**
 * NetBox OTN 位置地图应用逻辑
 * 精简版 - 用于展示指定位置，支持站点/路径点击查看
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. 配置与初始化
    const config = window.OTNFaultMapConfig;
    let sitesData = config.sitesData || [];
    const apiKey = config.apiKey;
    const targetLat = config.targetLat;
    const targetLng = config.targetLng;
    const highlightPathData = config.highlightPathData;  // 高亮路径 GeoJSON 数据
    const pathName = config.pathName;  // 路径名称

    // 初始化地图基类
    const mapBase = new NetBoxMapBase();
    window.mapBase = mapBase;

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

        // 仅网络底图执行后处理
        if (!mapBase.useLocalBasemap) {
            mapBase.emphasizeChinaBoundaries();
            mapBase.setLanguageToChinese();
            mapBase.filterLabels();
        }
    });

    // 添加标准控件（导航、全屏）
    mapBase.addStandardControls();
    mapBase.addHomeControl();

    // 2. 地图加载后添加图层
    map.on('load', () => {
        
        // --- OTN 路径图层 (PMTiles) ---
        const otnPathsPmtilesUrl = config.otnPathsPmtilesUrl;
        if (otnPathsPmtilesUrl) {
            map.addSource('otn_paths_pmtiles', {
                type: 'vector',
                url: 'pmtiles://' + otnPathsPmtilesUrl
            });

            // 查找插入位置
            const pathLayers = map.getStyle().layers;
            let firstSymbolId;
            for (const layer of pathLayers) {
                if (layer.type === 'symbol') {
                    firstSymbolId = layer.id;
                    break;
                }
            }

            // 路径显示图层
            mapBase.addLayer({
                id: 'otn-paths-layer',
                type: 'line',
                source: 'otn_paths_pmtiles',
                'source-layer': 'otn_paths',
                layout: {
                    'line-join': 'round',
                    'line-cap': 'round',
                    'visibility': 'visible'
                },
                paint: {
                    'line-color': '#00cc66',
                    'line-width': 2,
                    'line-opacity': 0.8
                }
            }, firstSymbolId);

            // 透明可点击区域
            mapBase.addLayer({
                id: 'otn-paths-labels',
                type: 'line',
                source: 'otn_paths_pmtiles',
                'source-layer': 'otn_paths',
                paint: {
                    'line-width': 10,
                    'line-opacity': 0
                }
            }, firstSymbolId);

            // 路径交互
            map.on('mouseenter', 'otn-paths-labels', () => map.getCanvas().style.cursor = 'pointer');
            map.on('mouseleave', 'otn-paths-labels', () => map.getCanvas().style.cursor = '');
        }

        // --- 站点图层 ---
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
                        0.2,
                        6, 1
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
        }

        // --- 高亮路径动画 (参照 DeckGLFlowAnimator) ---
        if (highlightPathData && highlightPathData.geometry) {
            const coords = highlightPathData.geometry.coordinates;
            const maxTime = 100;
            
            // 计算每个点的时间戳（基于累积距离，与 DeckGLFlowAnimator 一致）
            const timestamps = [0];
            let totalDistance = 0;
            for (let i = 1; i < coords.length; i++) {
                const [lon1, lat1] = coords[i - 1];
                const [lon2, lat2] = coords[i];
                const dx = lon2 - lon1;
                const dy = lat2 - lat1;
                totalDistance += Math.sqrt(dx * dx + dy * dy);
                timestamps.push(totalDistance);
            }
            
            // 归一化时间戳到 [0, maxTime]
            const normalizedTimestamps = timestamps.map(t =>
                totalDistance > 0 ? (t / totalDistance) * maxTime : 0
            );
            
            const tripData = [{
                path: coords,
                timestamps: normalizedTimestamps,
                color: [255, 100, 0]  // 橙红色（与 DeckGLFlowAnimator 一致）
            }];
            
            let currentTime = 0;
            let direction = 1;
            
            // 创建 Deck.gl 叠加层
            const deckOverlay = new deck.MapboxOverlay({
                interleaved: false,
                layers: []
            });
            map.addControl(deckOverlay);
            
            function updateAnimation() {
                // 往返流动效果
                currentTime += 1.5 * direction;
                if (currentTime >= maxTime) {
                    direction = -1;
                } else if (currentTime <= 0) {
                    direction = 1;
                }
                
                const tripsLayer = new deck.TripsLayer({
                    id: 'highlight-path-trips',
                    data: tripData,
                    getPath: d => d.path,
                    getTimestamps: d => d.timestamps,
                    getColor: d => d.color,
                    opacity: 1,
                    widthMinPixels: 6,
                    jointRounded: true,
                    capRounded: true,
                    trailLength: 30,  // 与 DeckGLFlowAnimator 一致
                    currentTime: currentTime,
                    fadeTrail: true
                });
                
                deckOverlay.setProps({ layers: [tripsLayer] });
                requestAnimationFrame(updateAnimation);
            }
            
            updateAnimation();
            
            // 添加静态底层路径（半透明底色）
            mapBase.addGeoJsonSource('highlight-path', {
                type: 'FeatureCollection',
                features: [highlightPathData]
            });
            
            mapBase.addLayer({
                id: 'highlight-path-layer',
                type: 'line',
                source: 'highlight-path',
                paint: {
                    'line-color': '#ff6400',  // 橙红色底色
                    'line-width': 4,
                    'line-opacity': 0.3
                }
            });
            
            // 自适应缩放到路径范围
            const bounds = new maplibregl.LngLatBounds();
            coords.forEach(c => bounds.extend(c));
            map.fitBounds(bounds, { padding: 80, maxZoom: 12 });
        }

        // --- 目标位置标记（仅当没有高亮路径时显示） ---
        if (!highlightPathData && targetLat !== null && targetLng !== null) {
            // 添加目标位置标记
            const targetMarker = new maplibregl.Marker({
                color: '#dc3545'  // 红色标记
            })
            .setLngLat([targetLng, targetLat])
            .setPopup(
                new maplibregl.Popup({ offset: 25 })
                    .setHTML(`
                        <div style="padding: 8px;">
                            <div style="font-weight: 600; margin-bottom: 4px;">目标位置</div>
                            <div style="font-size: 12px; color: #666;">
                                纬度: ${targetLat.toFixed(6)}<br>
                                经度: ${targetLng.toFixed(6)}
                            </div>
                        </div>
                    `)
            )
            .addTo(map);

            // 自动打开弹窗
            targetMarker.togglePopup();
        }

        // --- 统一点击处理 ---
        map.on('click', (e) => {
            const bbox = [
                [e.point.x - 5, e.point.y - 5],
                [e.point.x + 5, e.point.y + 5]
            ];
            
            const layersToQuery = [];
            if (map.getLayer('netbox-sites-layer')) layersToQuery.push('netbox-sites-layer');
            if (map.getLayer('otn-paths-labels')) layersToQuery.push('otn-paths-labels');
            
            if (layersToQuery.length === 0) return;
            
            const features = map.queryRenderedFeatures(bbox, { layers: layersToQuery });
            
            if (features.length === 0) return;
            
            const feature = features[0];
            const props = feature.properties;
            
            let popupContent = '';
            let popupCoords = e.lngLat;
            
            if (feature.layer.id === 'netbox-sites-layer') {
                // 站点弹窗 - 简化版（无详情图标）
                const regionHtml = props.region ? `<span style="font-size: 11px; color: #6c757d;"><i class="mdi mdi-earth"></i> ${props.region}</span>` : '';
                const statusHtml = props.status ? `<span style="font-size: 11px; color: #6c757d;"><i class="mdi mdi-check-circle"></i> ${props.status}</span>` : '';
                popupContent = `
                    <div style="padding: 8px 10px;">
                        <div style="font-weight: 600; font-size: 13px; margin-bottom: 6px;">
                            <i class="mdi mdi-map-marker" style="color: #0d6efd;"></i>
                            <a href="${props.url}" target="_blank" style="color: inherit; text-decoration: none;">${props.name}</a>
                        </div>
                        <div style="display: flex; gap: 12px;">
                            ${regionHtml}
                            ${statusHtml}
                        </div>
                    </div>
                `;
                popupCoords = feature.geometry.coordinates;
            } else if (feature.layer.id === 'otn-paths-labels') {
                // 路径弹窗 - 简化版（只保留标题）
                const pathName = props.name || '光缆路径';
                popupContent = `
                    <div style="padding: 8px 10px;">
                        <div style="font-weight: 600; font-size: 13px;">
                            <i class="mdi mdi-vector-polyline" style="color: #198754;"></i>
                            <a href="${props.url || '#'}" target="_blank" style="color: inherit; text-decoration: none;">${pathName}</a>
                        </div>
                    </div>
                `;
            }
            
            if (popupContent) {
                new maplibregl.Popup({ offset: 10, maxWidth: '320px' })
                    .setLngLat(popupCoords)
                    .setHTML(popupContent)
                    .addTo(map);
            }
        });
    });
});

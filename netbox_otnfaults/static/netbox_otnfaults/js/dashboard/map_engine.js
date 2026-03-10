/**
 * OTN 大屏 - 地图引擎 (MapLibre GL)
 * 
 * 负责：初始化 3D 地球、渲染图层、摄像机控制、光流动画
 */
window.MapEngine = (function () {
    'use strict';

    let map = null;
    let markers = [];
    let animationFrame = null;
    let flowOffset = 0;
    let _mapReady = false;
    let _pendingData = null;  // 地图未就绪时暂存数据

    const CONFIG = window.DASHBOARD_CONFIG;

    /**
     * 初始化地图
     */
    function init() {
        const style = _buildMapStyle();

        map = new maplibregl.Map({
            container: 'map-container',
            style: style,
            center: CONFIG.mapCenter,
            zoom: CONFIG.mapZoom,
            pitch: 45,
            bearing: 0,
            maxPitch: 70,
            attributionControl: false,
            antialias: true,
        });

        // 禁用大屏交互（自动播控模式）
        map.dragRotate.disable();
        map.touchZoomRotate.disable();
        map.scrollZoom.disable();
        map.boxZoom.disable();
        map.doubleClickZoom.disable();
        map.dragPan.disable();

        map.on('load', function () {
            _mapReady = true;
            _loadProvinceLayer();
            _startFlowAnimation();

            // 如果有待渲染的数据，立即渲染
            if (_pendingData) {
                if (_pendingData.sites) renderSites(_pendingData.sites);
                if (_pendingData.paths) renderPaths(_pendingData.paths);
                if (_pendingData.faults) renderFaultMarkers(_pendingData.faults);
                _pendingData = null;
            }
        });

        return map;
    }

    /**
     * 构建地图样式
     */
    function _buildMapStyle() {
        // 字体服务：优先使用本地字体，否则使用项目默认字体服务
        var glyphsUrl = CONFIG.localGlyphsUrl || '/maps/fonts/{fontstack}/{range}.pbf';

        if (CONFIG.useLocalBasemap && CONFIG.localTilesUrl) {
            return {
                version: 8,
                glyphs: glyphsUrl,
                sources: {
                    'local-tiles': {
                        type: 'vector',
                        url: 'pmtiles://' + CONFIG.localTilesUrl
                    }
                },
                layers: [{
                    id: 'background',
                    type: 'background',
                    paint: { 'background-color': '#060a14' }
                }]
            };
        }

        // 暗色底图样式
        return {
            version: 8,
            glyphs: glyphsUrl,
            sources: {},
            layers: [{
                id: 'background',
                type: 'background',
                paint: { 'background-color': '#060a14' }
            }]
        };
    }

    /* ═══ GCJ-02 → WGS-84 坐标转换 ═══
     * 省界 GeoJSON 通常来源于高德等平台，使用 GCJ-02（火星坐标系），
     * 而故障/站点数据使用 WGS-84（国际标准）。
     * 两者偏移约 300~600m，导致故障标记相对省界整体偏南。
     */
    var _PI = Math.PI;
    var _A = 6378245.0;           // 长半轴
    var _EE = 0.00669342162296594; // 偏心率平方

    function _transformLat(x, y) {
        var ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y
            + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
        ret += (20.0 * Math.sin(6.0 * x * _PI) + 20.0 * Math.sin(2.0 * x * _PI)) * 2.0 / 3.0;
        ret += (20.0 * Math.sin(y * _PI) + 40.0 * Math.sin(y / 3.0 * _PI)) * 2.0 / 3.0;
        ret += (160.0 * Math.sin(y / 12.0 * _PI) + 320 * Math.sin(y * _PI / 30.0)) * 2.0 / 3.0;
        return ret;
    }

    function _transformLng(x, y) {
        var ret = 300.0 + x + 2.0 * y + 0.1 * x * x
            + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
        ret += (20.0 * Math.sin(6.0 * x * _PI) + 20.0 * Math.sin(2.0 * x * _PI)) * 2.0 / 3.0;
        ret += (20.0 * Math.sin(x * _PI) + 40.0 * Math.sin(x / 3.0 * _PI)) * 2.0 / 3.0;
        ret += (150.0 * Math.sin(x / 12.0 * _PI) + 300.0 * Math.sin(x / 30.0 * _PI)) * 2.0 / 3.0;
        return ret;
    }

    function _gcj02ToWgs84(lng, lat) {
        var dlat = _transformLat(lng - 105.0, lat - 35.0);
        var dlng = _transformLng(lng - 105.0, lat - 35.0);
        var radlat = lat / 180.0 * _PI;
        var magic = Math.sin(radlat);
        magic = 1 - _EE * magic * magic;
        var sqrtmagic = Math.sqrt(magic);
        dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtmagic) * _PI);
        dlng = (dlng * 180.0) / (_A / sqrtmagic * Math.cos(radlat) * _PI);
        return [lng - dlng, lat - dlat];
    }

    /** 递归转换 GeoJSON 中所有坐标点 */
    function _convertGeoJsonCoords(geojson) {
        function convertCoords(coords) {
            if (typeof coords[0] === 'number') {
                // 叶子节点 [lng, lat]
                var wgs = _gcj02ToWgs84(coords[0], coords[1]);
                coords[0] = wgs[0];
                coords[1] = wgs[1];
            } else {
                for (var i = 0; i < coords.length; i++) {
                    convertCoords(coords[i]);
                }
            }
        }
        if (geojson.features) {
            geojson.features.forEach(function (f) {
                if (f.geometry && f.geometry.coordinates) {
                    convertCoords(f.geometry.coordinates);
                }
            });
        }
        return geojson;
    }

    /**
     * 加载省界图层
     */
    function _loadProvinceLayer() {
        fetch(CONFIG.provinceGeoJsonUrl)
            .then(r => r.json())
            .then(data => {
                // GCJ-02 → WGS-84 坐标转换，使省界与故障/站点坐标对齐
                _convertGeoJsonCoords(data);

                map.addSource('provinces', {
                    type: 'geojson',
                    data: data
                });

                // 省区底色
                map.addLayer({
                    id: 'province-fill',
                    type: 'fill',
                    source: 'provinces',
                    paint: {
                        'fill-color': '#0b1225',
                        'fill-opacity': 0.6
                    }
                });
                // 省界描边
                map.addLayer({
                    id: 'province-border',
                    type: 'line',
                    source: 'provinces',
                    paint: {
                        'line-color': 'rgba(0, 210, 255, 0.2)',
                        'line-width': 1
                    }
                });

                // 省界发光
                map.addLayer({
                    id: 'province-border-glow',
                    type: 'line',
                    source: 'provinces',
                    paint: {
                        'line-color': 'rgba(0, 210, 255, 0.06)',
                        'line-width': 4,
                        'line-blur': 4
                    }
                });

                // 省份/城市名称标注 (辅助定位)
                map.addLayer({
                    id: 'province-labels',
                    type: 'symbol',
                    source: 'provinces',
                    minzoom: 5.5,
                    filter: [
                        'all',
                        ['has', 'name'],
                        ['!', ['in', '境界线', ['get', 'name']]],
                        ['!', ['in', '国界', ['get', 'name']]],
                        ['!', ['in', '九段线', ['get', 'name']]],
                        ['!', ['in', '十段线', ['get', 'name']]]
                    ],
                    layout: {
                        'text-field': ['get', 'name'],
                        'text-font': ['Noto Sans SC Regular'],
                        'text-size': ['interpolate', ['linear'], ['zoom'],
                            6, 10,
                            8, 14,
                            10, 16
                        ],
                        'text-justify': 'center',
                        'text-anchor': 'center',
                        'text-padding': 120, // 显著增大碰撞缓冲区，降低显示密度
                        'symbol-avoid-edges': true,
                    },
                    paint: {
                        'text-color': 'rgba(160, 180, 200, 0.45)',
                        'text-halo-color': 'rgba(6, 10, 20, 0.8)',
                        'text-halo-width': 1.5,
                    }
                });
            })
            .catch(err => console.warn('省界数据加载失败:', err));
    }

    /**
     * 渲染站点图层
     */
    function renderSites(sites) {
        if (!map || !_mapReady) {
            _pendingData = _pendingData || {};
            _pendingData.sites = sites;
            return;
        }

        const geojson = {
            type: 'FeatureCollection',
            features: sites.map(s => ({
                type: 'Feature',
                geometry: { type: 'Point', coordinates: [s.lng, s.lat] },
                properties: { name: s.name, id: s.id }
            }))
        };

        if (map.getSource('sites')) {
            map.getSource('sites').setData(geojson);
        } else {
            map.addSource('sites', { type: 'geojson', data: geojson });

            // 站点光晕
            map.addLayer({
                id: 'sites-glow',
                type: 'circle',
                source: 'sites',
                paint: {
                    'circle-radius': 8,
                    'circle-color': 'rgba(0, 210, 255, 0.1)',
                    'circle-blur': 1
                }
            });

            // 站点核心点
            map.addLayer({
                id: 'sites-core',
                type: 'circle',
                source: 'sites',
                paint: {
                    'circle-radius': 3,
                    'circle-color': '#00D2FF',
                    'circle-stroke-color': 'rgba(0, 210, 255, 0.5)',
                    'circle-stroke-width': 1
                }
            });

            // 站点标签
            map.addLayer({
                id: 'sites-label',
                type: 'symbol',
                source: 'sites',
                minzoom: 6,
                layout: {
                    'text-field': ['get', 'name'],
                    'text-size': 10,
                    'text-offset': [0, 1.2],
                    'text-anchor': 'top',
                    'text-font': ['Noto Sans SC Regular']
                },
                paint: {
                    'text-color': 'rgba(180, 210, 230, 0.8)',
                    'text-halo-color': 'rgba(6, 10, 20, 0.9)',
                    'text-halo-width': 1
                }
            });
        }
    }

    /**
     * 路径颜色配置
     * 96芯 → 蓝色系  |  144芯 → 绿色系  |  默认 → 青色系
     */
    const PATH_COLORS = {
        '96': {
            main: 'rgba(59, 130, 246, 0.6)',    // 蓝
            glow: 'rgba(59, 130, 246, 0.12)',
            flow: '#3B82F6',
            label: '#93C5FD',
        },
        '114': {
            main: 'rgba(16, 185, 129, 0.6)',    // 绿
            glow: 'rgba(16, 185, 129, 0.12)',
            flow: '#10B981',
            label: '#6EE7B7',
        },
        'default': {
            main: 'rgba(0, 210, 255, 0.45)',    // 青
            glow: 'rgba(0, 210, 255, 0.10)',
            flow: '#00D2FF',
            label: '#7DD3FC',
        }
    };

    const FAULT_PATH_COLOR = '#FF1E1E';  // 故障路径红色

    /**
     * 渲染光缆路径图层（增强版）
     *
     * 多层结构：
     *   1. paths-glow       底层光晕（按光缆类型着色）
     *   2. paths-main       路径主体（按光缆类型着色）
     *   3. paths-flow       光流动画（正常路径）
     *   4. paths-fault-glow 故障路径光晕（红色脉冲）
     *   5. paths-fault      故障路径主体（红色高亮）
     *   6. paths-label      路径名称标注
     *   7. paths-length     路径长度标注
     */
    function renderPaths(paths) {
        if (!map || !_mapReady) {
            _pendingData = _pendingData || {};
            _pendingData.paths = paths;
            return;
        }

        // 分离正常路径和故障关联路径
        var normalFeatures = [];
        var faultFeatures = [];
        var labelFeatures = [];

        paths.forEach(function (p) {
            var raw = p.geometry;
            if (!raw) return;
            // 字符串先解析
            if (typeof raw === 'string') {
                try { raw = JSON.parse(raw); } catch (e) { return; }
            }
            // 规范化为 GeoJSON geometry 对象
            var geom;
            if (raw.type && raw.coordinates) {
                // 已经是完整的 GeoJSON geometry
                geom = raw;
            } else if (Array.isArray(raw) && raw.length >= 2) {
                // 是纯坐标数组 [[lng, lat], ...]
                geom = { type: 'LineString', coordinates: raw };
            } else {
                console.warn('[MapEngine] 跳过无效路径几何:', p.name, raw);
                return;
            }

            var cableType = p.cable_type || 'default';
            var colorSet = PATH_COLORS[cableType] || PATH_COLORS['default'];

            // 构建标注文本
            var labelParts = [p.name];
            if (p.cable_type_display) labelParts.push(p.cable_type_display);
            if (p.length_km) labelParts.push(p.length_km);

            var feature = {
                type: 'Feature',
                geometry: geom,
                properties: {
                    id: p.id,
                    name: p.name,
                    cable_type: cableType,
                    main_color: colorSet.main,
                    glow_color: colorSet.glow,
                    flow_color: colorSet.flow,
                    label_color: colorSet.label,
                    label_text: labelParts.join(' · '),
                    site_a: p.site_a_name || '',
                    site_z: p.site_z_name || '',
                    groups: (p.groups || []).join(', '),
                    length_km: p.length_km || '',
                    has_fault: p.has_fault ? 1 : 0,
                }
            };

            if (p.has_fault) {
                faultFeatures.push(feature);
            }
            // 所有路径都加入正常集合（故障路径在上层覆盖高亮）
            normalFeatures.push(feature);

            // 路径中点用于标注
            if (geom.type === 'LineString' && geom.coordinates && geom.coordinates.length >= 2) {
                var midIdx = Math.floor(geom.coordinates.length / 2);
                labelFeatures.push({
                    type: 'Feature',
                    geometry: { type: 'Point', coordinates: geom.coordinates[midIdx] },
                    properties: {
                        label_text: p.name,
                        detail_text: (p.cable_type_display || '') + (p.length_km ? ' ' + p.length_km : ''),
                        label_color: colorSet.label,
                        has_fault: p.has_fault ? 1 : 0,
                    }
                });
            }
        });

        var normalGeoJson = { type: 'FeatureCollection', features: normalFeatures };
        var faultGeoJson = { type: 'FeatureCollection', features: faultFeatures };
        var labelGeoJson = { type: 'FeatureCollection', features: labelFeatures };

        // ── 更新或创建 Source ──
        if (map.getSource('paths')) {
            map.getSource('paths').setData(normalGeoJson);
        } else {
            map.addSource('paths', { type: 'geojson', data: normalGeoJson });
        }

        if (map.getSource('paths-fault')) {
            map.getSource('paths-fault').setData(faultGeoJson);
        } else {
            map.addSource('paths-fault', { type: 'geojson', data: faultGeoJson });
        }

        if (map.getSource('paths-labels')) {
            map.getSource('paths-labels').setData(labelGeoJson);
        } else {
            map.addSource('paths-labels', { type: 'geojson', data: labelGeoJson });
        }

        // ── 创建图层（仅首次）──
        if (!map.getLayer('paths-glow')) {
            // 1. 底层光晕
            map.addLayer({
                id: 'paths-glow',
                type: 'line',
                source: 'paths',
                paint: {
                    'line-color': ['get', 'glow_color'],
                    'line-width': ['interpolate', ['linear'], ['zoom'],
                        3, 4,
                        7, 8,
                        10, 12
                    ],
                    'line-blur': 4
                }
            });

            // 2. 路径主体（按光缆类型着色）
            map.addLayer({
                id: 'paths-main',
                type: 'line',
                source: 'paths',
                paint: {
                    'line-color': ['get', 'main_color'],
                    'line-width': ['interpolate', ['linear'], ['zoom'],
                        3, 1.2,
                        7, 2,
                        10, 3
                    ]
                }
            });

            // 3. 光流动画层
            map.addLayer({
                id: 'paths-flow',
                type: 'line',
                source: 'paths',
                filter: ['!=', ['get', 'has_fault'], 1],
                paint: {
                    'line-color': ['get', 'flow_color'],
                    'line-width': ['interpolate', ['linear'], ['zoom'],
                        3, 1.5,
                        7, 2.5
                    ],
                    'line-dasharray': [0, 4, 3],
                    'line-opacity': 0.7
                }
            });

            // 4. 故障路径光晕（红色呼吸）
            map.addLayer({
                id: 'paths-fault-glow',
                type: 'line',
                source: 'paths-fault',
                paint: {
                    'line-color': 'rgba(255, 30, 30, 0.25)',
                    'line-width': ['interpolate', ['linear'], ['zoom'],
                        3, 8,
                        7, 14,
                        10, 20
                    ],
                    'line-blur': 6
                }
            });

            // 5. 故障路径主体（红色高亮）
            map.addLayer({
                id: 'paths-fault-main',
                type: 'line',
                source: 'paths-fault',
                paint: {
                    'line-color': FAULT_PATH_COLOR,
                    'line-width': ['interpolate', ['linear'], ['zoom'],
                        3, 2,
                        7, 3,
                        10, 4
                    ],
                    'line-opacity': 0.9
                }
            });

            // 6. 路径名称标注（中等缩放时显示）
            map.addLayer({
                id: 'paths-label',
                type: 'symbol',
                source: 'paths-labels',
                minzoom: 5.5,
                layout: {
                    'text-field': ['get', 'label_text'],
                    'text-size': ['interpolate', ['linear'], ['zoom'],
                        5.5, 9,
                        8, 11,
                        10, 13
                    ],
                    'text-font': ['Noto Sans SC Regular'],
                    'text-allow-overlap': false,
                    'text-ignore-placement': false,
                    'text-padding': 10,
                },
                paint: {
                    'text-color': ['case',
                        ['==', ['get', 'has_fault'], 1], '#FF6B6B',
                        ['get', 'label_color']
                    ],
                    'text-halo-color': 'rgba(6, 10, 20, 0.95)',
                    'text-halo-width': 2,
                    'text-halo-blur': 1,
                }
            });

            // 7. 路径详情标注（高缩放时显示）
            map.addLayer({
                id: 'paths-detail',
                type: 'symbol',
                source: 'paths-labels',
                minzoom: 7.5,
                layout: {
                    'text-field': ['get', 'detail_text'],
                    'text-size': 9,
                    'text-font': ['Noto Sans SC Regular'],
                    'text-offset': [0, 1.3],
                    'text-anchor': 'top',
                    'text-allow-overlap': false,
                    'text-padding': 5,
                },
                paint: {
                    'text-color': 'rgba(160, 180, 200, 0.6)',
                    'text-halo-color': 'rgba(6, 10, 20, 0.9)',
                    'text-halo-width': 1,
                }
            });
        }
    }

    /**
     * 路径动画（仅使用 opacity/blur 属性，避免 LineAtlas 溢出）
     *
     * 注意：不能使用 setPaintProperty('line-dasharray', ...) 做动画，
     * 因为每个新的 dasharray 值会在 LineAtlas 中创建新纹理，
     * 快速耗尽内存导致 "LineAtlas out of space" 崩溃。
     */
    function _startFlowAnimation() {
        var phase = 0;

        function animate() {
            phase += 0.03;

            // 光流层：opacity 脉冲（呼吸感）
            if (map.getLayer('paths-flow')) {
                var flowOpacity = 0.4 + Math.sin(phase * 2) * 0.3;
                map.setPaintProperty('paths-flow', 'line-opacity', flowOpacity);
            }

            // 故障路径：红色光晕呼吸
            if (map.getLayer('paths-fault-glow')) {
                var pulseOpacity = 0.15 + Math.sin(phase) * 0.12;
                map.setPaintProperty('paths-fault-glow', 'line-opacity', pulseOpacity);
            }

            // 故障标记：脉冲扩散环呼吸动画
            if (map.getLayer('faults-pulse')) {
                var pulseRadius = 14 + Math.sin(phase * 1.5) * 8;
                var pulseStrokeOp = 0.6 - Math.sin(phase * 1.5) * 0.4;
                map.setPaintProperty('faults-pulse', 'circle-radius', pulseRadius);
                map.setPaintProperty('faults-pulse', 'circle-stroke-opacity', Math.max(0.05, pulseStrokeOp));
            }

            animationFrame = requestAnimationFrame(animate);
        }
        animate();
    }

    /**
     * 渲染故障标记（WebGL Circle Layer 实现）
     *
     * 使用 Circle Layer 替代 HTML Marker，确保与站点/路径等
     * 其他 WebGL 图层使用相同的投影管道，避免 CSS 缩放/容器
     * 布局导致 HTML Marker 像素定位偏移。
     *
     * 三层结构：
     *   1. faults-pulse  脉冲扩散环（动画驱动 radius + opacity）
     *   2. faults-glow   静态光晕
     *   3. faults-core   核心亮点
     */
    function renderFaultMarkers(faults) {
        if (!map || !_mapReady) {
            _pendingData = _pendingData || {};
            _pendingData.faults = faults;
            return;
        }

        var colors = CONFIG.colors;

        var geojson = {
            type: 'FeatureCollection',
            features: faults.map(function (fault) {
                var severity = fault.severity || 'minor';
                var color = (colors.alert_colors && colors.alert_colors[severity]) || '#FADB14';

                return {
                    type: 'Feature',
                    geometry: { type: 'Point', coordinates: [fault.lng, fault.lat] },
                    properties: {
                        id: fault.id,
                        severity: severity,
                        color: color,
                    }
                };
            })
        };

        // 更新或创建数据源
        if (map.getSource('faults')) {
            map.getSource('faults').setData(geojson);
        } else {
            map.addSource('faults', { type: 'geojson', data: geojson });

            // 0. 定位引导环 (静态背景)
            map.addLayer({
                id: 'faults-localization-ring',
                type: 'circle',
                source: 'faults',
                paint: {
                    'circle-radius': 40,
                    'circle-color': 'transparent',
                    'circle-stroke-color': ['get', 'color'],
                    'circle-stroke-width': 1,
                    'circle-stroke-opacity': 0.15
                }
            });

            // 1. 脉冲扩散环（动画驱动）
            map.addLayer({
                id: 'faults-pulse',
                type: 'circle',
                source: 'faults',
                paint: {
                    'circle-radius': 20,
                    'circle-color': 'transparent',
                    'circle-stroke-color': ['get', 'color'],
                    'circle-stroke-width': 3,
                    'circle-stroke-opacity': 0.7,
                }
            });

            // 2. 静态光晕
            map.addLayer({
                id: 'faults-glow',
                type: 'circle',
                source: 'faults',
                paint: {
                    'circle-radius': 16,
                    'circle-color': ['get', 'color'],
                    'circle-opacity': 0.15,
                    'circle-blur': 1,
                }
            });

            // 3. 核心亮点
            map.addLayer({
                id: 'faults-core',
                type: 'circle',
                source: 'faults',
                paint: {
                    'circle-radius': 6,
                    'circle-color': ['get', 'color'],
                    'circle-opacity': 1.0,
                    'circle-stroke-color': '#ffffff',
                    'circle-stroke-width': 1.5,
                    'circle-stroke-opacity': 0.6,
                }
            });
        }
    }

    /**
     * 高亮故障路径（将受影响路径变为告警色）
     */
    function highlightFaultPath(faultId, color) {
        // 简化实现：暂不支持单条路径高亮
    }

    /**
     * 摄像机飞行（带贝塞尔缓动）
     */
    function flyTo(lng, lat, zoom, options) {
        if (!map) return Promise.resolve();

        const opts = Object.assign({
            center: [lng, lat],
            zoom: zoom || 8,
            pitch: 50,
            bearing: 0,
            duration: 4000,
            essential: true,
            curve: 1.42,
            easing: _easeInOutCubic,
        }, options || {});

        return new Promise(resolve => {
            map.once('moveend', resolve);
            map.flyTo(opts);
        });
    }

    /**
     * 平滑平移到位置
     */
    function easeTo(lng, lat, zoom, options) {
        if (!map) return Promise.resolve();

        const opts = Object.assign({
            center: [lng, lat],
            zoom: zoom || map.getZoom(),
            duration: 2000,
            easing: _easeInOutCubic,
        }, options || {});

        return new Promise(resolve => {
            map.once('moveend', resolve);
            map.easeTo(opts);
        });
    }

    /**
     * 缓慢旋转（全局巡航用）
     */
    function rotateTo(targetBearing, duration) {
        if (!map) return Promise.resolve();

        return new Promise(resolve => {
            map.once('moveend', resolve);
            map.easeTo({
                bearing: targetBearing,
                duration: duration || 30000,
                easing: function (t) { return t; }  // 线性
            });
        });
    }

    /**
     * 重置到全国视图
     */
    function resetView() {
        // 保持当前角度(bearing)返回中心点，避免强制回正则产生的跳变
        return flyTo(CONFIG.mapCenter[0], CONFIG.mapCenter[1], CONFIG.mapZoom, {
            pitch: 45,
            duration: 3500
        });
    }

    /**
     * 获取地图实例
     */
    function getMap() {
        return map;
    }

    /**
     * 三阶贝塞尔缓动函数
     */
    function _easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    return {
        init,
        renderSites,
        renderPaths,
        renderFaultMarkers,
        highlightFaultPath,
        flyTo,
        easeTo,
        rotateTo,
        resetView,
        getMap
    };
})();

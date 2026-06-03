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
    let focusedSiteIds = [];

    const CONFIG = window.DASHBOARD_CONFIG;
    const SITE_LABEL_MIN_ZOOM = 6;

    const DASHBOARD_LAYER_STACK = [
        'province-shadow',
        'province-extrusion',
        'province-border-glow-bottom',
        'province-border-top',
        'province-labels',
        'otn-paths-base-glow',
        'otn-paths-base-main',
        'sites-glow',
        'sites-core',
        'sites-label',
        'closed-heatmap-layer',
        'sites-focus-glow',
        'sites-focus-core',
        'sites-focus-label',
        'paths-fault-glow',
        'paths-fault-main',
        'paths-label',
        'paths-detail',
        'faults-pulse',
        'faults-glow',
        'faults-core',
    ];

    /**
     * 初始化地图
     */
    function init() {
        _registerPmtilesProtocol();
        const style = _buildMapStyle();

        map = new maplibregl.Map({
            container: 'map-container',
            style: style,
            center: CONFIG.mapCenter,
            zoom: CONFIG.mapZoom,
            pitch: CONFIG.mapPitch || 48,  // 增加初始俯仰角以显示 3D
            bearing: 0,
            maxPitch: 85, // 允许更大的倾斜以便查看 3D
            attributionControl: false,
            antialias: true, // 开启抗锯齿对 3D 渲染很重要
        });

        // 禁用大屏交互（自动播控模式）
        if (window.OTNMapFrameRateToggle) {
            window.OTNMapFrameRateToggle.register(map);
        }

        map.dragRotate.disable();
        map.touchZoomRotate.disable();
        map.scrollZoom.disable();
        map.boxZoom.disable();
        map.doubleClickZoom.disable();
        map.dragPan.disable();

        map.on('load', function () {
            _mapReady = true;
            _loadProvinceLayer();
            _loadTopologyLayer();
            _startFlowAnimation();

            // 如果有待渲染的数据，立即渲染
            if (_pendingData) {
                if (_pendingData.sites) renderSites(_pendingData.sites);
                if (_pendingData.faultPaths) renderFaultPaths(_pendingData.faultPaths);
                if (_pendingData.heatmap) renderHeatmap(_pendingData.heatmap);
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
                        url: 'pmtiles://' + _resolveUrl(CONFIG.localTilesUrl)
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

    function _resolveUrl(url) {
        if (!url) return '';
        if (/^(?:[a-z]+:)?\/\//i.test(url) || url.startsWith('data:') || url.startsWith('blob:')) {
            return url;
        }
        return new URL(url, window.location.origin).toString();
    }

    function _registerPmtilesProtocol() {
        if (window.__dashboardPmtilesProtocolRegistered || typeof pmtiles === 'undefined') {
            return;
        }
        var protocol = new pmtiles.Protocol();
        maplibregl.addProtocol('pmtiles', protocol.tile);
        window.__dashboardPmtilesProtocolRegistered = true;
    }

    function _loadTopologyLayer() {
        if (!CONFIG.otnPathsPmtilesUrl) return;

        var resolvedPmtilesUrl = _resolveUrl(CONFIG.otnPathsPmtilesUrl);
        if (!resolvedPmtilesUrl) return;

        if (!map.getSource('otn_paths_pmtiles')) {
            map.addSource('otn_paths_pmtiles', {
                type: 'vector',
                url: 'pmtiles://' + resolvedPmtilesUrl
            });
        }

        if (!map.getLayer('otn-paths-base-glow')) {
            map.addLayer({
                id: 'otn-paths-base-glow',
                type: 'line',
                source: 'otn_paths_pmtiles',
                'source-layer': 'otn_paths',
                paint: {
                    'line-color': 'rgba(16, 185, 129, 0.16)',
                    'line-width': ['interpolate', ['linear'], ['zoom'], 3, 3, 7, 6, 10, 10],
                    'line-blur': 3
                }
            });
        }

        if (!map.getLayer('otn-paths-base-main')) {
            map.addLayer({
                id: 'otn-paths-base-main',
                type: 'line',
                source: 'otn_paths_pmtiles',
                'source-layer': 'otn_paths',
                layout: {
                    'line-join': 'round',
                    'line-cap': 'round'
                },
                paint: {
                    'line-color': 'rgba(16, 185, 129, 0.48)',
                    'line-width': ['interpolate', ['linear'], ['zoom'], 3, 0.8, 7, 1.5, 10, 2.2],
                    'line-opacity': 0.9
                }
            });
        }

        _restackDashboardLayers();
    }

    function _restackDashboardLayers() {
        if (!map) return;

        var beforeLayerId;
        for (var i = DASHBOARD_LAYER_STACK.length - 1; i >= 0; i--) {
            var layerId = DASHBOARD_LAYER_STACK[i];
            if (!map.getLayer(layerId)) continue;
            map.moveLayer(layerId, beforeLayerId);
            beforeLayerId = layerId;
        }
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

                // 1. 底部悬浮投影 (向下延伸后的深视感)
                map.addLayer({
                    id: 'province-shadow',
                    type: 'fill',
                    source: 'provinces',
                    paint: {
                        'fill-color': '#02050a',
                        'fill-opacity': 0.9,
                        'fill-translate': [5, 10], // 减小偏移，因为厚度向下延申
                        'fill-translate-anchor': 'viewport'
                    }
                });

                // 2. 3D 立体省份 (向下延伸：使业务线/点在顶面显示)
                map.addLayer({
                    id: 'province-extrusion',
                    type: 'fill-extrusion',
                    source: 'provinces',
                    paint: {
                        'fill-extrusion-color': '#0f2040',
                        'fill-extrusion-height': 0,        // 顶面设为地平线 0
                        'fill-extrusion-base': 0,          // 修复：底座不能为负数
                        'fill-extrusion-opacity': 0.9      // 增加不透明度，强化侧边厚度感
                    }
                });

                // 3. 顶面边界轮廓线
                map.addLayer({
                    id: 'province-border-top',
                    type: 'line',
                    source: 'provinces',
                    filter: ['==', '$type', 'Polygon'], // Ensure it renders slightly above cleanly
                    paint: {
                        'line-color': 'rgba(100, 130, 170, 0.7)',
                        'line-width': 1.5,
                        // Not natively supported to offset line height purely in GL easily without line-extrusion, 
                        // but it naturally drapes over the fill-extrusion if drawn after or we rely on map style.
                        // For true 3D edge, we might need a separate source or rely on MapLibre's draping behavior.
                    }
                });

                // 为了更好的 3D 发光效果，我们可以增强全局的光照 (如果在 initMap 中未设置)
                // 这里暂用底层环境光模拟发光边缘
                map.addLayer({
                    id: 'province-border-glow-bottom',
                    type: 'line',
                    source: 'provinces',
                    paint: {
                        'line-color': 'rgba(100, 130, 170, 0.25)',
                        'line-width': 10,
                        'line-blur': 10
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

                _restackDashboardLayers();
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
                properties: { name: s.name, id: String(s.id) }
            }))
        };

        let layerAdded = false;
        if (map.getSource('sites')) {
            map.getSource('sites').setData(geojson);
        } else {
            layerAdded = true;
            map.addSource('sites', { type: 'geojson', data: geojson });

            // 站点光晕
            map.addLayer({
                id: 'sites-glow',
                type: 'circle',
                source: 'sites',
                paint: {
                    'circle-radius': 8,
                    'circle-color': 'rgba(16, 185, 129, 0.14)',
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
                    'circle-color': '#10B981',
                    'circle-stroke-color': 'rgba(16, 185, 129, 0.65)',
                    'circle-stroke-width': 1
                }
            });

            // 站点标签
            map.addLayer({
                id: 'sites-label',
                type: 'symbol',
                source: 'sites',
                minzoom: SITE_LABEL_MIN_ZOOM,
                layout: {
                    'text-field': ['get', 'name'],
                    'text-size': 10,
                    'text-offset': [0, 1.2],
                    'text-anchor': 'top',
                    'text-font': ['Noto Sans SC Regular']
                },
                paint: {
                    'text-color': 'rgba(167, 243, 208, 0.82)',
                    'text-halo-color': 'rgba(6, 10, 20, 0.9)',
                    'text-halo-width': 1
                }
            });

            // 聚焦站点光晕
            map.addLayer({
                id: 'sites-focus-glow',
                type: 'circle',
                source: 'sites',
                filter: ['in', ['get', 'id'], ['literal', []]],
                paint: {
                    'circle-radius': 16,
                    'circle-color': 'rgba(34, 197, 94, 0.45)',
                    'circle-blur': 1
                }
            });

            // 聚焦站点核心点
            map.addLayer({
                id: 'sites-focus-core',
                type: 'circle',
                source: 'sites',
                filter: ['in', ['get', 'id'], ['literal', []]],
                paint: {
                    'circle-radius': 7,
                    'circle-color': '#10B981',
                    'circle-stroke-color': '#D1FAE5',
                    'circle-stroke-width': 2
                }
            });

            map.addLayer({
                id: 'sites-focus-label',
                type: 'symbol',
                source: 'sites',
                filter: ['in', ['get', 'id'], ['literal', []]],
                layout: {
                    'text-field': ['get', 'name'],
                    'text-size': 12,
                    'text-offset': [0, 1.45],
                    'text-anchor': 'top',
                    'text-font': ['Noto Sans SC Regular'],
                    'text-allow-overlap': true,
                    'text-ignore-placement': true,
                    'text-padding': 12
                },
                paint: {
                    'text-color': '#D1FAE5',
                    'text-halo-color': 'rgba(6, 10, 20, 0.98)',
                    'text-halo-width': 2,
                    'text-halo-blur': 1
                }
            });
        }

        _applyFocusedSiteFilter();
        _applyRegularSiteLabelFilter();
        _applyRegularSiteFilter();
        if (layerAdded) {
            _restackDashboardLayers();
        }
    }

    function _extractFaultSiteIds(fault) {
        var ids = [];
        if (!fault) return ids;

        if (fault.site_a_id) ids.push(String(fault.site_a_id));
        (fault.site_z_ids || []).forEach(function (siteId) {
            if (siteId != null && siteId !== '') ids.push(String(siteId));
        });

        // 去重 + 确保全部为非空字符串
        return ids.filter(function (siteId, index) {
            return typeof siteId === 'string' && siteId.length > 0 && ids.indexOf(siteId) === index;
        });
    }

    function _applyFocusedSiteFilter() {
        if (!map || !map.getLayer('sites-focus-label')) return;

        const emptySiteFilter = ['in', ['get', 'id'], ['literal', []]];
        const focusedSiteFilter = ['in', ['get', 'id'], ['literal', focusedSiteIds]];
        const filter = (!focusedSiteIds || focusedSiteIds.length === 0) ? emptySiteFilter : focusedSiteFilter;

        map.setFilter('sites-focus-label', filter);
        if (!focusedSiteIds || focusedSiteIds.length === 0) {
            if (map.getLayer('sites-focus-glow')) map.setFilter('sites-focus-glow', emptySiteFilter);
            if (map.getLayer('sites-focus-core')) map.setFilter('sites-focus-core', emptySiteFilter);
            return;
        }

        if (map.getLayer('sites-focus-glow')) map.setFilter('sites-focus-glow', focusedSiteFilter);
        if (map.getLayer('sites-focus-core')) map.setFilter('sites-focus-core', focusedSiteFilter);
    }

    function _applyRegularSiteFilter() {
        if (!map) return;

        if (!focusedSiteIds || focusedSiteIds.length === 0) {
            // 清除所有普通站点层的过滤器
            if (map.getLayer('sites-glow'))  map.setFilter('sites-glow', null);
            if (map.getLayer('sites-core'))  map.setFilter('sites-core', null);
            return;
        }

        // 排除聚焦站点，由 focus 层单独渲染
        var excludeFilter = ['!', ['in', ['get', 'id'], ['literal', focusedSiteIds]]];
        if (map.getLayer('sites-glow'))  map.setFilter('sites-glow', excludeFilter);
        if (map.getLayer('sites-core'))  map.setFilter('sites-core', excludeFilter);
    }

    function _applyRegularSiteLabelFilter() {
        if (!map) return;

        if (!focusedSiteIds || focusedSiteIds.length === 0) {
            if (map.getLayer('sites-label')) map.setFilter('sites-label', null);
            return;
        }

        var excludeFilter = ['!', ['in', ['get', 'id'], ['literal', focusedSiteIds]]];
        if (map.getLayer('sites-label')) map.setFilter('sites-label', excludeFilter);
    }

    function _setRegularSiteLabelCollision(enabled) {
        if (!map || !map.getLayer('sites-label')) return;

        map.setLayoutProperty('sites-label', 'text-allow-overlap', !enabled);
        map.setLayoutProperty('sites-label', 'text-ignore-placement', !enabled);
    }

    function focusFaultSites(fault) {
        focusedSiteIds = _extractFaultSiteIds(fault);
        _applyFocusedSiteFilter();
        _applyRegularSiteLabelFilter();
        _applyRegularSiteFilter();
        _setRegularSiteLabelCollision(false);
        // 不再调用 _restackDashboardLayers()：图层顺序仅在首次创建时确定，
        // filter/layout 属性变更不需要重排，避免与动画帧竞态导致闪烁
    }

    function clearFaultSiteFocus() {
        focusedSiteIds = [];
        _applyFocusedSiteFilter();
        _applyRegularSiteLabelFilter();
        _applyRegularSiteFilter();
        _setRegularSiteLabelCollision(true);
        // 同上，不再重排图层
    }

    /**
     * 路径颜色配置
     * 态势大屏统一使用绿色系，按光缆类型仅调整明度与透明度。
     */
    const PATH_COLORS = {
        '96': {
            main: 'rgba(34, 197, 94, 0.62)',
            glow: 'rgba(34, 197, 94, 0.14)',
            flow: '#22C55E',
            label: '#BBF7D0',
        },
        '114': {
            main: 'rgba(16, 185, 129, 0.68)',
            glow: 'rgba(16, 185, 129, 0.16)',
            flow: '#10B981',
            label: '#A7F3D0',
        },
        'default': {
            main: 'rgba(74, 222, 128, 0.52)',
            glow: 'rgba(74, 222, 128, 0.12)',
            flow: '#4ADE80',
            label: '#DCFCE7',
        }
    };

    const FAULT_PATH_COLOR = '#FF1E1E';  // 故障路径保留红色告警语义

    /**
     * 渲染故障关联路径覆盖层
     *
     * 基础网络拓扑由 PMTiles 常驻渲染，这里只更新与活跃故障相关的高亮覆盖。
     */
    function renderFaultPaths(paths) {
        if (!map || !_mapReady) {
            _pendingData = _pendingData || {};
            _pendingData.faultPaths = paths;
            return;
        }

        var faultFeatures = [];
        var labelFeatures = [];

        paths.forEach(function (p) {
            var raw = p.geometry;
            if (!raw) return;
            // 字符串先解析
            if (typeof raw === 'string') {
                try { raw = JSON.parse(raw); } catch (e) { return; }
            }

            var geom;
            if (raw.type && raw.coordinates) {
                geom = raw;
            } else if (Array.isArray(raw) && raw.length >= 2) {
                geom = { type: 'LineString', coordinates: raw };
            } else {
                console.warn('[MapEngine] 跳过无效路径几何:', p.name, raw);
                return;
            }

            var cableType = p.cable_type || 'default';
            var colorSet = PATH_COLORS[cableType] || PATH_COLORS['default'];

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
                    has_fault: 1,
                }
            };

            faultFeatures.push(feature);

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

        var faultGeoJson = { type: 'FeatureCollection', features: faultFeatures };
        var labelGeoJson = { type: 'FeatureCollection', features: labelFeatures };

        let layerAdded = false;

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

        if (!map.getLayer('paths-fault-glow')) {
            layerAdded = true;
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

        if (layerAdded) {
            _restackDashboardLayers();
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
                var status = fault.status || 'processing';
                var color = (colors.status_colors && colors.status_colors[status]) || '#FADB14';

                return {
                    type: 'Feature',
                    geometry: { type: 'Point', coordinates: [fault.lng, fault.lat] },
                    properties: {
                        id: fault.id,
                        status: status,
                        color: color,
                    }
                };
            })
        };

        let layerAdded = false;

        // 更新或创建数据源
        if (map.getSource('faults')) {
            map.getSource('faults').setData(geojson);
        } else {
            layerAdded = true;
            map.addSource('faults', { type: 'geojson', data: geojson });

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

        if (layerAdded) {
            _restackDashboardLayers();
        }
    }

    /**
     * 渲染已关闭故障热力图层
     *
     * 展示历史故障的空间密度分布：
     *   - 颜色从冷（深蓝/透明）到热（红/橙）渐变
     *   - 权重由故障严重度驱动
     *   - 低缩放级别使用较大半径呈现宏观趋势
     *   - 高缩放级别使用较小半径展示精细分布
     *   - 置于活跃故障和路径图层之下，不遮挡运行态信息
     */
    function renderHeatmap(closedPoints) {
        if (!map || !_mapReady) {
            _pendingData = _pendingData || {};
            _pendingData.heatmap = closedPoints;
            return;
        }

        if (!closedPoints || closedPoints.length === 0) return;

        var geojson = {
            type: 'FeatureCollection',
            features: closedPoints.map(function (pt) {
                return {
                    type: 'Feature',
                    geometry: { type: 'Point', coordinates: [pt.lng, pt.lat] },
                    properties: {
                        weight: pt.weight || 0.5,
                        category: pt.category || 'unknown',
                    }
                };
            })
        };

        let layerAdded = false;

        // 更新或创建数据源
        if (map.getSource('closed-heatmap')) {
            map.getSource('closed-heatmap').setData(geojson);
            // 如果 Layer 已存在，仅更新数据即可
            if (map.getLayer('closed-heatmap-layer')) {
                return;
            }
            // Source 在但 Layer 不在（初次创建失败）→ 继续补画 Layer
        } else {
            layerAdded = true;
            map.addSource('closed-heatmap', { type: 'geojson', data: geojson });
        }

        if (!map.getLayer('closed-heatmap-layer')) {
            layerAdded = true;
            // 热力图层（年度数据降温：降低强度和半径，红色仅保留给极高密度核心）
            map.addLayer({
                id: 'closed-heatmap-layer',
                type: 'heatmap',
                source: 'closed-heatmap',
                paint: {
                    // 热力权重：使用 feature 的 weight 属性
                    'heatmap-weight': ['get', 'weight'],

                    // 热力强度：避免年度点位在全国视角下快速顶满为红色
                    'heatmap-intensity': ['interpolate', ['linear'], ['zoom'],
                        3, 1.0,
                        6, 0.9,
                        10, 1.2
                    ],

                    // 热力颜色渐变：以青蓝和黄橙表达趋势，红色后移到最高密度
                    'heatmap-color': [
                        'interpolate', ['linear'], ['heatmap-density'],
                        0,    'rgba(0, 0, 0, 0)',           // 透明
                        0.10, 'rgba(0, 180, 255, 0.18)',    // 淡青
                        0.25, 'rgba(0, 210, 255, 0.32)',    // 青色
                        0.45, 'rgba(16, 185, 129, 0.42)',   // 绿色
                        0.65, 'rgba(250, 219, 20, 0.55)',   // 黄色
                        0.82, 'rgba(255, 138, 0, 0.65)',    // 橙色
                        1.0,  'rgba(255, 50, 30, 0.72)',    // 红色（最高密度核心）
                    ],

                    // 热力半径：缩小扩散范围，减少相邻线路热点在全国视角下连成片
                    'heatmap-radius': ['interpolate', ['linear'], ['zoom'],
                        3, 28,
                        5, 22,
                        7, 16,
                        10, 10
                    ],

                    // 整体不透明度
                    'heatmap-opacity': ['interpolate', ['linear'], ['zoom'],
                        3, 0.45,
                        7, 0.38,
                        10, 0.3
                    ],
                }
            });
        }

        if (layerAdded) {
            _restackDashboardLayers();
        }

        console.log('[MapEngine] 热力图层创建成功，数据点:', closedPoints.length);
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

    function getSiteLabelMinZoom() {
        return SITE_LABEL_MIN_ZOOM;
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
        renderFaultPaths,
        renderFaultMarkers,
        renderHeatmap,
        focusFaultSites,
        clearFaultSiteFocus,
        highlightFaultPath,
        flyTo,
        easeTo,
        rotateTo,
        resetView,
        getSiteLabelMinZoom,
        getMap
    };
})();

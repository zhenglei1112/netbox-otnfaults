
/**
 * NetBox OTN 故障分布图应用逻辑
 * 处理业务逻辑、数据处理和特定 UI 控件。
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. 配置与初始化
    const config = window.OTNFaultMapConfig;
    let heatmapData = config.heatmapData;
    let markerData = config.markerData;
    const apiKey = config.apiKey;

    // 验证数据
    if (!Array.isArray(heatmapData)) {
        console.warn('heatmap_data 不是有效的数组，使用空数组');
        heatmapData = [];
    }
    if (!Array.isArray(markerData)) {
        console.warn('marker_data 不是有效的数组，使用空数组');
        markerData = [];
    }

    // 初始化地图基础类
    const mapBase = new NetBoxMapBase();
    
    // 立即显示加载提示
    const loadingOverlay = NetBoxMapBase.showLoading('map');

    let map;
    try {
        map = mapBase.init('map', apiKey);
    } catch (error) {
        console.error('地图初始化错误:', error);
        NetBoxMapBase.showError('map', '地图初始化失败: ' + error.message);
        return;
    }

    // 访问通用图标
    const svgIcons = mapBase.svgIcons;

    // 添加通用控件
    mapBase.addStandardControls();
    mapBase.addHomeControl();

    // 2. 定义特定控件

    // 图层切换控件
    class LayerToggleControl {
        constructor(options) {
            this.options = options || {};
            this.heatmapVisible = true;
            this.markersVisible = true;
            this.arcgisVisible = true;
            this.markers = [];
            this.currentTimeRange = 'year';
            this.menuHovered = false;
            this.lastMouseX = 0;
            this.lastMouseY = 0;

            document.addEventListener('mousemove', (e) => {
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
            });
        }

        onAdd(map) {
            this.map = map;
            this.container = document.createElement('div');
            this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group layer-toggle-control';

            this.heatmapContainer = document.createElement('div');
            this.heatmapContainer.className = 'heatmap-button-container';
            this.heatmapContainer.style.position = 'relative';

            this.heatmapButton = document.createElement('button');
            this.heatmapButton.className = 'maplibregl-ctrl-icon toggle-button heatmap-toggle active';
            this.heatmapButton.innerHTML = svgIcons.heatmap;
            this.heatmapButton.title = '热力图开关';
            this.heatmapButton.onclick = (e) => {
                e.stopPropagation();
                this.toggleHeatmap();
            };

            this.markersButton = document.createElement('button');
            this.markersButton.className = 'maplibregl-ctrl-icon toggle-button markers-toggle active';
            this.markersButton.innerHTML = svgIcons.marker;
            this.markersButton.title = '故障点开关';
            this.markersButton.onclick = () => this.toggleMarkers();

            this.arcgisButton = document.createElement('button');
            this.arcgisButton.className = 'maplibregl-ctrl-icon toggle-button arcgis-toggle';
            this.arcgisButton.innerHTML = svgIcons.network;
            this.arcgisButton.title = 'OTN网络图层';
            this.arcgisButton.onclick = () => this.toggleArcgis();

            if (this.arcgisVisible) {
                this.arcgisButton.classList.add('active');
            }

            this.heatmapContainer.appendChild(this.heatmapButton);
            this.container.appendChild(this.heatmapContainer);
            this.container.appendChild(this.markersButton);
            this.container.appendChild(this.arcgisButton);

            this.createTimeRangeMenu();

            return this.container;
        }

        onRemove() {
            this.container.parentNode.removeChild(this.container);
            this.map = undefined;
        }

        createTimeRangeMenu() {
            // ... 复制原始逻辑 ...
            this.timeRangeMenu = document.createElement('div');
            this.timeRangeMenu.className = 'heatmap-time-range-menu';

            const menuItems = [
                { range: 'month', text: '一个月' },
                { range: 'three_months', text: '三个月' },
                { range: 'year', text: '本年' }
            ];

            menuItems.forEach(item => {
                const menuItem = document.createElement('div');
                menuItem.className = 'dropdown-item';
                menuItem.setAttribute('data-range', item.range);
                menuItem.textContent = item.text;

                if (item.range === this.currentTimeRange) {
                    menuItem.classList.add('active');
                }

                menuItem.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const range = e.target.getAttribute('data-range');
                    this.selectTimeRange(range);
                    this.hideTimeRangeMenu();
                });

                this.timeRangeMenu.appendChild(menuItem);
            });

            this.timeRangeMenu.addEventListener('mouseenter', () => { this.menuHovered = true; });
            this.timeRangeMenu.addEventListener('mouseleave', () => {
                this.menuHovered = false;
                setTimeout(() => {
                    if (!this.menuHovered && !this.isMouseOverButton()) {
                        this.hideTimeRangeMenu();
                    }
                }, 300);
            });

            this.heatmapContainer.appendChild(this.timeRangeMenu);
            document.addEventListener('click', () => { this.hideTimeRangeMenu(); });
        }

        isMouseOverButton() {
            if (!this.heatmapButton) return false;
            const rect = this.heatmapButton.getBoundingClientRect();
            const mouseX = this.lastMouseX || 0;
            const mouseY = this.lastMouseY || 0;
            return mouseX >= rect.left && mouseX <= rect.right &&
                mouseY >= rect.top && mouseY <= rect.bottom;
        }

        hideTimeRangeMenu() {
            if (this.timeRangeMenu) this.timeRangeMenu.style.display = 'none';
        }

        selectTimeRange(range) {
            this.currentTimeRange = range;
            let rangeText = '本年';
            if (range === 'month') rangeText = '一个月';
            else if (range === 'three_months') rangeText = '三个月';

            this.heatmapButton.title = `热力图开关 - 当前范围: ${rangeText}`;
            
            // 更新菜单高亮
             if (this.timeRangeMenu) {
                const menuItems = this.timeRangeMenu.querySelectorAll('.dropdown-item');
                menuItems.forEach(item => {
                    const r = item.getAttribute('data-range');
                    if (r === this.currentTimeRange) item.classList.add('active');
                    else item.classList.remove('active');
                });
            }

            this.reloadHeatmapData(range);
        }

        reloadHeatmapData(timeRange) {
             // 筛选数据并更新源的逻辑
             // 我们需要访问 heatmapData，它在外部作用域中。
             const now = new Date();
             let startDate;
             if (timeRange === 'month') startDate = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
             else if (timeRange === 'three_months') startDate = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
             else startDate = new Date(now.getFullYear(), 0, 1);

             const filteredData = heatmapData.filter(point => {
                 if (!point.occurrence_time) return false;
                 const pointDate = new Date(point.occurrence_time);
                 return pointDate >= startDate;
             });

             // 通知 CategoryFilter（如果存在）
             if (window.categoryFilterControl && window.categoryFilterControl.reloadHeatmapData) {
                 window.categoryFilterControl.reloadHeatmapData(); 
                 // 注意：这种循环依赖处理有点简单，但很有效。
                 // 更好的实现是使用中央数据管理器，但为了重构，这模仿了原始行为。
             } else {
                 // 如果没有分类筛选器（当前流程中不应发生）的回退
                  const features = filteredData.map(point => ({
                     type: 'Feature',
                     properties: { count: point.count },
                     geometry: { type: 'Point', coordinates: [point.lng, point.lat] }
                 }));
                 if (this.map.getSource('faults')) {
                     this.map.getSource('faults').setData({ type: 'FeatureCollection', features: features });
                 }
             }
             
            this.updateButtonTitle(timeRange);
        }

        updateButtonTitle(timeRange) {
             let rangeText = '本年';
             if (timeRange === 'month') rangeText = '一个月';
             else if (timeRange === 'three_months') rangeText = '三个月';
             this.heatmapButton.title = `热力图开关 - 当前范围: ${rangeText}`;
             this.currentTimeRange = timeRange;
        }

        toggleHeatmap() {
            this.heatmapVisible = !this.heatmapVisible;
            if (this.heatmapVisible) {
                this.heatmapButton.classList.add('active');
                mapBase.setLayoutProperty('faults-heat', 'visibility', 'visible');
            } else {
                this.heatmapButton.classList.remove('active');
                mapBase.setLayoutProperty('faults-heat', 'visibility', 'none');
            }
        }

        toggleMarkers() {
            this.markersVisible = !this.markersVisible;
            if (this.markersVisible) {
                this.markersButton.classList.add('active');
                this.markers.forEach(marker => marker.getElement().style.display = 'block');
                if (this.legendContainer) this.legendContainer.style.display = 'block';
            } else {
                this.markersButton.classList.remove('active');
                this.markers.forEach(marker => marker.getElement().style.display = 'none');
                if (this.legendContainer) this.legendContainer.style.display = 'none';
            }
        }
        
        setLegend(container) { this.legendContainer = container; }
        addMarker(marker) { this.markers.push(marker); }

        toggleArcgis() {
            this.arcgisVisible = !this.arcgisVisible;
            this.updateArcgisLayersVisibility();
        }

        updateArcgisLayersVisibility() {
             if (!this.arcgisVisible) {
                ['arcgis-province-layer', 'arcgis-otn-points-0', 'arcgis-otn-points-1', 'arcgis-otn-lines-2', 'arcgis-otn-lines-3', 'arcgis-otn-labels-0', 'arcgis-otn-labels-1'].forEach(layerId => {
                    mapBase.setLayoutProperty(layerId, 'visibility', 'none');
                });
                this.arcgisButton.classList.remove('active');
                return;
             }

             const currentZoom = this.map.getZoom();
             const isProvincialView = currentZoom >= 5;

             if (this.map.getLayer('arcgis-province-layer')) mapBase.setLayoutProperty('arcgis-province-layer', 'visibility', 'visible');
             if (this.map.getLayer('arcgis-otn-lines-2')) mapBase.setLayoutProperty('arcgis-otn-lines-2', 'visibility', 'visible');
             if (this.map.getLayer('arcgis-otn-lines-3')) mapBase.setLayoutProperty('arcgis-otn-lines-3', 'visibility', 'visible');

             const pointVisibility = isProvincialView ? 'visible' : 'none';
             ['arcgis-otn-points-0', 'arcgis-otn-points-1', 'arcgis-otn-labels-0', 'arcgis-otn-labels-1'].forEach(layerId => {
                 if (this.map.getLayer(layerId)) mapBase.setLayoutProperty(layerId, 'visibility', pointVisibility);
             });
             
             this.arcgisButton.classList.add('active');
        }
    }

    const layerToggleControl = new LayerToggleControl();
    mapBase.addControl(layerToggleControl, 'top-left');

    
    // 分类筛选控件
    const faultCategoryColors = {
        'power': '#FF0000', 'fiber': '#00FF00', 'pigtail': '#0000FF', 'device': '#FFA500', 'other': '#800080'
    };
    const faultCategoryNames = {
        'power': '电力故障', 'fiber': '光缆故障', 'pigtail': '空调故障', 'device': '设备故障', 'other': '其他故障'
    };

    class CategoryFilterControl {
        constructor() {
            this.selectedCategories = Object.keys(faultCategoryColors);
            this.menuHovered = false;
             document.addEventListener('mousemove', (e) => {
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
            });
        }
        
        onAdd(map) {
            this.map = map;
            this.container = document.createElement('div');
            this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group category-filter-control';
            
            this.filterContainer = document.createElement('div');
            this.filterContainer.className = 'category-filter-button-container';
            this.filterContainer.style.position = 'relative';

            this.filterButton = document.createElement('button');
            this.filterButton.className = 'maplibregl-ctrl-icon toggle-button category-filter-toggle';
            this.filterButton.innerHTML = svgIcons.filter;
            this.filterButton.title = '故障分类筛选';
            this.filterButton.onmouseenter = (e) => { e.stopPropagation(); this.showCategoryMenu(); };
            this.filterButton.onmouseleave = (e) => {
                e.stopPropagation();
                setTimeout(() => { if (!this.isMouseOverMenu()) this.hideCategoryMenu(); }, 300);
            };

            this.createCategoryMenu();
            this.filterContainer.appendChild(this.filterButton);
            this.filterContainer.appendChild(this.categoryMenu); // 将菜单添加到容器
            this.container.appendChild(this.filterContainer);
            return this.container;
        }

        onRemove() {
             this.container.parentNode.removeChild(this.container);
        }

        createCategoryMenu() {
            this.categoryMenu = document.createElement('div');
            this.categoryMenu.className = 'category-filter-menu';
            this.categoryMenu.style.cssText = `position: absolute; background-color: white; border: 1px solid #ddd; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); z-index: 1000; min-width: 150px; padding: 8px 0; display: none; top: 100%; left: 0;`;
            this.categoryMenu.onclick = (e) => e.stopPropagation();

            // 时间范围部分
            const trTitle = document.createElement('div');
            trTitle.className = 'dropdown-item';
            trTitle.innerHTML = '<strong>时间范围</strong>';
            trTitle.style.borderBottom = '1px solid #eee';
            this.categoryMenu.appendChild(trTitle);
            
            const timeRanges = [
                { range: 'month', text: '一个月' },
                { range: 'three_months', text: '三个月' },
                { range: 'year', text: '本年' }
            ];
            timeRanges.forEach(item => {
                 const div = document.createElement('div');
                 div.className = 'dropdown-item';
                 div.setAttribute('data-range', item.range);
                 div.textContent = item.text;
                 if (item.range === layerToggleControl.currentTimeRange) div.classList.add('active'); // 与图层控件同步
                 div.onclick = (e) => {
                     e.stopPropagation();
                     layerToggleControl.selectTimeRange(item.range);
                 };
                 this.categoryMenu.appendChild(div);
            });

             const sep = document.createElement('div');
             sep.style.cssText = 'height: 1px; background-color: #eee; margin: 8px 0;';
             this.categoryMenu.appendChild(sep);

             // 全选/全不选
             const allBtn = document.createElement('div');
             allBtn.className = 'dropdown-item';
             allBtn.innerHTML = '<strong>全选/全不选</strong>';
             allBtn.onclick = (e) => { e.stopPropagation(); this.toggleAllCategories(); };
             this.categoryMenu.appendChild(allBtn);

             // 分类
             Object.keys(faultCategoryColors).forEach(category => {
                 const item = document.createElement('div');
                 item.className = 'dropdown-item';
                 item.style.cssText = 'display: flex; align-items: center; padding: 6px 12px;';
                 
                 const cb = document.createElement('input');
                 cb.type = 'checkbox';
                 cb.id = `category-${category}`;
                 cb.checked = this.selectedCategories.includes(category);
                 cb.style.marginRight = '8px';
                 cb.onchange = (e) => { e.stopPropagation(); this.toggleCategory(category, cb.checked); };

                 const label = document.createElement('label');
                 label.htmlFor = cb.id;
                 label.style.cssText = 'display: flex; align-items: center; cursor: pointer; flex: 1;';
                 label.innerHTML = `<div style="width: 12px; height: 12px; background-color: ${faultCategoryColors[category]}; margin-right: 8px;"></div><span>${faultCategoryNames[category]}</span>`;
                 label.onclick = (e) => { e.stopPropagation(); cb.checked = !cb.checked; this.toggleCategory(category, cb.checked); };

                 item.appendChild(cb);
                 item.appendChild(label);
                 this.categoryMenu.appendChild(item);
             });

             this.categoryMenu.onmouseenter = () => { this.menuHovered = true; };
             this.categoryMenu.onmouseleave = () => {
                 this.menuHovered = false;
                 setTimeout(() => { if (!this.menuHovered && !this.isMouseOverButton()) this.hideCategoryMenu(); }, 300);
             };
             
             document.addEventListener('click', (e) => {
                 if (!this.categoryMenu.contains(e.target) && !this.filterButton.contains(e.target)) this.hideCategoryMenu();
             });
        }
        
        isMouseOverMenu() { return this.menuHovered; }
        isMouseOverButton() {
             const rect = this.filterButton.getBoundingClientRect();
             return (this.lastMouseX >= rect.left && this.lastMouseX <= rect.right && this.lastMouseY >= rect.top && this.lastMouseY <= rect.bottom);
        }
        showCategoryMenu() { 
            this.hideCategoryMenu(); 
            this.categoryMenu.style.display = 'block'; 
            this.updateTimeRangeUI(); // Use shared method
        }

        updateTimeRangeUI() {
             if (!this.categoryMenu) return;
             const timeRangeItems = this.categoryMenu.querySelectorAll('.dropdown-item[data-range]');
             timeRangeItems.forEach(item => {
                 if (item.getAttribute('data-range') === layerToggleControl.currentTimeRange) item.classList.add('active');
                 else item.classList.remove('active');
             });
        }
        hideCategoryMenu() { if (this.categoryMenu) this.categoryMenu.style.display = 'none'; }

        toggleCategory(cat, checked) {
            if (checked) { if (!this.selectedCategories.includes(cat)) this.selectedCategories.push(cat); }
            else { this.selectedCategories = this.selectedCategories.filter(c => c !== cat); }
            this.reloadHeatmapData();
        }
        
        toggleAllCategories() {
            if (this.selectedCategories.length === Object.keys(faultCategoryColors).length) this.selectedCategories = [];
            else this.selectedCategories = [...Object.keys(faultCategoryColors)];
            
            // 更新 UI
            Object.keys(faultCategoryColors).forEach(cat => {
                const cb = document.getElementById(`category-${cat}`);
                if (cb) cb.checked = this.selectedCategories.includes(cat);
            });
            this.reloadHeatmapData();
        }

        reloadHeatmapData() {
            const timeRange = layerToggleControl.currentTimeRange;
             const now = new Date();
             let startDate;
             if (timeRange === 'month') startDate = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
             else if (timeRange === 'three_months') startDate = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
             else startDate = new Date(now.getFullYear(), 0, 1);

             const filteredData = heatmapData.filter(point => {
                 if (!point.occurrence_time) return false;
                 const pointDate = new Date(point.occurrence_time);
                 if (pointDate < startDate) return false;
                 
                  const category = point.category || 'other';
                  return this.selectedCategories.includes(category);
             });
             
             const features = filteredData.map(point => ({
                 type: 'Feature',
                 properties: { count: point.count },
                 geometry: { type: 'Point', coordinates: [point.lng, point.lat] }
             }));
             
             if (map.getSource('faults')) map.getSource('faults').setData({ type: 'FeatureCollection', features: features });
             
             this.updateButtonTitle();
        }
        
        updateButtonTitle() {
             const count = this.selectedCategories.length;
             let catText = count === Object.keys(faultCategoryColors).length ? `全部${count}种分类` : (count === 0 ? '无分类' : `${count}种分类`);
             this.filterButton.title = `故障分类筛选 - 时间: ..., 分类: ${catText}`;
        }
    }

    const categoryFilterControl = new CategoryFilterControl();
    window.categoryFilterControl = categoryFilterControl; // 全局访问，用于同步
    mapBase.addControl(categoryFilterControl, 'top-left');
    
    // 覆盖 layerToggleControl 的方法以调用我们的刷新
    const originalReload = layerToggleControl.reloadHeatmapData.bind(layerToggleControl);
    layerToggleControl.reloadHeatmapData = function(range) {
        // 直接调用 categoryFilterControl，它同处理时间和分类
        this.currentTimeRange = range;
        this.updateButtonTitle(range);
        categoryFilterControl.reloadHeatmapData();
        categoryFilterControl.updateTimeRangeUI(); // Update UI
    };


    // 3. 地图加载逻辑
    map.on('style.load', function () {
        mapBase.setLanguageToChinese();
        mapBase.filterLabels();
    });

    map.on('load', function () {
        mapBase.setProjection('globe');

        // 设置热力图数据源
        const features = heatmapData.map(point => ({
             type: 'Feature',
             properties: { count: point.count },
             geometry: { type: 'Point', coordinates: [point.lng, point.lat] }
        }));
        
        // 自适应边界
        const bounds = new maplibregl.LngLatBounds();
        if (features.length > 0) features.forEach(f => bounds.extend(f.geometry.coordinates));
        markerData.forEach(m => bounds.extend([m.lng, m.lat]));
        if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 50 });

        // Helper to get theme link color using canvas to normalize format (MapLibre compatibility)
        const getThemeColor = (fallback) => {
            try {
                // 1. Get computed color from dummy anchor
                const temp = document.createElement('a');
                temp.href = '#';
                temp.style.visibility = 'hidden';
                temp.style.position = 'absolute';
                document.body.appendChild(temp);
                const computedColor = getComputedStyle(temp).color;
                document.body.removeChild(temp);

                // 2. Normalize using Canvas to force RGBA
                if (computedColor) {
                    const canvas = document.createElement('canvas');
                    canvas.width = 1; 
                    canvas.height = 1;
                    const ctx = canvas.getContext('2d');
                    ctx.fillStyle = computedColor;
                    ctx.fillRect(0,0,1,1);
                    const [r, g, b, a] = ctx.getImageData(0,0,1,1).data;
                    // Standardize to rgba(r, g, b, a) where a is 0-1
                    return `rgba(${r}, ${g}, ${b}, ${(a / 255).toFixed(3)})`;
                }
                
                return fallback;
            } catch (e) {
                console.warn('Failed to resolve theme color', e);
                return fallback;
            }
        };
        const themeLinkColor = getThemeColor('#00cc66');
        console.log('Resolved Theme Link Color (normalized RGBA):', themeLinkColor);

        // ArcGIS 图层
        try {
            const layersConfig = [
                { id: 'arcgis-otn-lines-2', urlId: 2, type: 'line', color: themeLinkColor, width: 3, opacity: 0.8 },
                { id: 'arcgis-otn-lines-3', urlId: 3, type: 'line', color: themeLinkColor, width: 3, opacity: 0.7 }
            ];
            
            layersConfig.forEach(l => {
                mapBase.addGeoJsonSource(l.id.replace('lines', 'layer'), `http://192.168.70.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/${l.urlId}/query?where=1%3D1&outFields=*&f=geojson`, { promoteId: 'OBJECTID' });
                mapBase.addLayer({
                    id: l.id, type: l.type, source: l.id.replace('lines', 'layer'),
                    paint: { 'line-color': l.color, 'line-width': l.width, 'line-opacity': l.opacity }
                });
                // 添加悬停/点击交互
                map.on('mouseenter', l.id, () => map.getCanvas().style.cursor = 'pointer');
                map.on('mouseleave', l.id, () => map.getCanvas().style.cursor = '');
                map.on('click', l.id, (e) => {
                     const props = e.features[0].properties;
                     let content = '<h6>OTN网络线路</h6><table class="table table-sm">';
                     for (let k in props) if (props[k] !== null) content += `<tr><th>${k}</th><td>${props[k]}</td></tr>`;
                     content += '</table>';
                     new maplibregl.Popup().setLngLat(e.lngLat).setHTML(content).addTo(map);
                });
            });

            // 点图层
             const pointsConfig = [
                { id: 'arcgis-otn-points-0', urlId: 0, color: '#007bff', radius: [6, 4, 10, 8, 15, 12] },
                { id: 'arcgis-otn-points-1', urlId: 1, color: '#00aaff', radius: [6, 3, 10, 6, 15, 10] }
            ];
            
            pointsConfig.forEach(p => {
                const srcId = p.id.replace('points', 'layer');
                mapBase.addGeoJsonSource(srcId, `http://192.168.70.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/${p.urlId}/query?where=1%3D1&outFields=*&f=geojson`, { promoteId: 'OBJECTID' });
                mapBase.addLayer({
                    id: p.id, type: 'circle', source: srcId,
                    paint: {
                        'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, p.radius[1], 10, p.radius[3], 15, p.radius[5]],
                        'circle-color': p.color, 'circle-stroke-width': 1, 'circle-stroke-color': '#fff'
                    }
                });
                
                // 标签
                mapBase.addLayer({
                    id: p.id.replace('points', 'labels'), type: 'symbol', source: srcId,
                    layout: {
                        'text-field': ['coalesce', ['get', 'O_name'], ['get', 'O_NAME'], ['get', 'name'], ''],
                        'text-font': ['Arial Unicode MS Bold', 'sans-serif'], 'text-size': 13,
                        'text-offset': [0, -1.5], 'text-anchor': 'bottom'
                    },
                    paint: { 'text-color': '#fff', 'text-halo-color': 'rgba(0,0,0,0.8)', 'text-halo-width': 2 }
                });

                // 交互
                let hoveredStateId = null;
                map.on('mouseenter', p.id, (e) => {
                     map.getCanvas().style.cursor = 'pointer';
                     if (e.features.length > 0) {
                         if (hoveredStateId !== null) map.setFeatureState({ source: srcId, id: hoveredStateId }, { hover: false });
                         hoveredStateId = e.features[0].id;
                         map.setFeatureState({ source: srcId, id: hoveredStateId }, { hover: true });
                     }
                });
                map.on('mouseleave', p.id, () => {
                     map.getCanvas().style.cursor = '';
                     if (hoveredStateId !== null) map.setFeatureState({ source: srcId, id: hoveredStateId }, { hover: false });
                     hoveredStateId = null;
                });
                 map.on('click', p.id, (e) => {
                     const props = e.features[0].properties;
                     let content = '<h6>OTN网络节点</h6><table class="table table-sm">';
                     for (let k in props) if (props[k] !== null) content += `<tr><th>${k}</th><td>${props[k]}</td></tr>`;
                     content += '</table>';
                     new maplibregl.Popup().setLngLat(e.lngLat).setHTML(content).addTo(map);
                 });
            });

            // 热力图图层
             if (features.length > 0) {
                mapBase.addGeoJsonSource('faults', { type: 'FeatureCollection', features: features });
                mapBase.addLayer({
                    id: 'faults-heat', type: 'heatmap', source: 'faults', maxzoom: 15,
                    paint: {
                        'heatmap-weight': ['interpolate', ['linear'], ['get', 'count'], 0, 0, 4, 1],
                        'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1, 9, 4],
                        'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'], 0, 'rgba(33,102,172,0)', 0.1, 'rgb(103,169,207)', 0.3, 'rgb(209,229,240)', 0.5, 'rgb(253,219,199)', 0.7, 'rgb(239,138,98)', 1, 'rgb(178,24,43)'],
                        'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 3, 9, 25],
                        'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 7, 1, 9, 0]
                    }
                });
            }

            // 省份图层
            mapBase.addGeoJsonSource('arcgis-province-source', 'http://192.168.70.216:6080/arcgis/rest/services/OTN/province/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson', { promoteId: 'OBJECTID' });
            mapBase.addLayer({
                 id: 'arcgis-province-layer', type: 'line', source: 'arcgis-province-source',
                 paint: { 'line-color': '#E3CF57', 'line-width': 1, 'line-opacity': 0.5 }
            });

             // 同步按钮状态
             layerToggleControl.updateArcgisLayersVisibility();
             map.on('zoom', () => { if (layerToggleControl.arcgisVisible) layerToggleControl.updateArcgisLayersVisibility(); });

        } catch (e) {
            console.warn('ArcGIS图层加载失败', e);
        }

        // 添加标记
        markerData.forEach(m => {
             const category = m.category || 'other';
             const color = faultCategoryColors[category] || faultCategoryColors['other'];
             const content = `
                <div style="font-size:13px; max-width:300px;">
                    <h6 style="border-bottom:1px solid #eee; padding-bottom:5px;">
                        <a href="${m.url}" target="_blank">${m.number}</a>
                        <span style="background:${color}; color:#fff; padding:2px 5px; border-radius:3px; font-size:11px; margin-left:5px;">${faultCategoryNames[category]}</span>
                    </h6>
                    <div><b>A端:</b> ${m.a_site || '-'}</div>
                    <div><b>Z端:</b> ${m.z_sites || '-'}</div>
                    <div><b>发生:</b> ${m.occurrence_time}</div>
                    <div><b>恢复:</b> ${m.recovery_time}</div>
                </div>`;
             
             const marker = mapBase.addMarker(m.lng, m.lat, { color: color, popup: content });
             layerToggleControl.addMarker(marker);
        });

        // 图例
        const legendItems = Object.keys(faultCategoryColors).map(k => ({
            label: faultCategoryNames[k], color: faultCategoryColors[k]
        }));
        
        const legendDiv = document.createElement('div');
        legendDiv.className = 'maplibregl-ctrl maplibregl-ctrl-group fault-legend';
        legendDiv.style.cssText = 'padding: 10px; background: rgba(255,255,255,0.9); max-width: 200px;';
        legendDiv.innerHTML = '<div style="border-bottom:1px solid #ddd; margin-bottom:5px;"><b>故障分类图例</b></div>';
        legendItems.forEach(item => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex; align-items:center; margin-bottom:3px;';
            row.innerHTML = `<div style="width:12px; height:12px; background:${item.color}; margin-right:8px;"></div><span style="font-size:12px;">${item.label}</span>`;
            legendDiv.appendChild(row);
        });
        
        mapBase.addControl({ onAdd: () => legendDiv, onRemove: () => {} }, 'bottom-right');
        layerToggleControl.setLegend(legendDiv);

        NetBoxMapBase.hideLoading('map');

    });

    map.on('error', function (e) {
         console.error('地图加载错误', e);
         NetBoxMapBase.showError('map', e.error.message);
    });
});


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
            this.markers = [];            this.currentTimeRange = 'year';
            this.currentMarkerTimeRange = 'one_week'; // Default marker filter
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

        filterMarkers(range) {
            this.currentMarkerTimeRange = range;
            const now = new Date();
            let startDate;
            
            // Calculate start date based on range
            if (range === 'one_week') {
                startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
            } else if (range === 'two_weeks') {
                startDate = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000);
            } else if (range === 'month') {
                const temp = new Date(now);
                temp.setMonth(temp.getMonth() - 1);
                startDate = temp;
            } else {
                // Fallback or 'all', though UI only offers valid options
                startDate = new Date(now.getFullYear(), 0, 1); 
            }

            // Filter markers
            this.markers.forEach(markerWrapper => {
                // Assuming markerWrapper is the object we pushed: { marker: ..., data: ... } 
                // Wait, previous code pushed just the mapboxgl marker object.
                // We need to attach data to the marker object to filter it.
                // Let's check how markers are added. 
                // In generic init: layerToggleControl.addMarker(marker); 
                // We need to store data with the marker.
                
                // Inspecting line 692: const marker = mapBase.addMarker(...)
                // The marker object itself doesn't easily hold custom data unless we added it on creation.
                // We need to modify the addMarker usage in the main loop to store the time data.
                
                // BUT, looking at the code I'm editing, I can just attach the element display style logic here 
                // IF I had access to the data. 
                // I will modify the addMarker method and the main loop to pass data.
            });
            
            // Re-implementing filter logic requires data access. 
            // Instead of complicating this method blindly, let's look at how addMarker is used.
            // It is used in line 693: layerToggleControl.addMarker(marker);
            // I should change addMarker to accept data or the date string.
        }

        // Modified addMarker to store date
        addMarker(marker, dateStr) { 
            this.markers.push({ marker: marker, date: new Date(dateStr) }); 
        }

        // Updated toggleMarkers to use both visibility flag and time filter
        updateMarkerVisibility() {
            if (!this.markersVisible) {
                this.markers.forEach(item => item.marker.getElement().style.display = 'none');
                if (this.legendContainer) this.legendContainer.style.display = 'none';
                return;
            }

            if (this.legendContainer) this.legendContainer.style.display = 'block';
            
            const now = new Date();
            let startDate;
            if (this.currentMarkerTimeRange === 'one_week') {
                startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
            } else if (this.currentMarkerTimeRange === 'two_weeks') {
                startDate = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000);
            } else if (this.currentMarkerTimeRange === 'month') {
                const temp = new Date(now);
                temp.setMonth(temp.getMonth() - 1);
                startDate = temp;
            } else {
                 startDate = new Date(0); // Show all
            }

            this.markers.forEach(item => {
                if (item.date >= startDate) {
                    item.marker.getElement().style.display = 'block';
                } else {
                    item.marker.getElement().style.display = 'none';
                }
            });
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
            } else {
                this.markersButton.classList.remove('active');
            }
            this.updateMarkerVisibility();
        }
        
        setLegend(container) { this.legendContainer = container; }


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

            // 故障点时间范围
            const markerTitle = document.createElement('div');
            markerTitle.className = 'dropdown-item';
            markerTitle.innerHTML = '<strong>故障点时间范围</strong>';
            markerTitle.style.borderBottom = '1px solid #eee';
            this.categoryMenu.appendChild(markerTitle);

            const markerTimeRanges = [
                { range: 'one_week', text: '一周' },
                { range: 'two_weeks', text: '两周' },
                { range: 'month', text: '一个月' }
            ];

            markerTimeRanges.forEach(item => {
                const div = document.createElement('div');
                div.className = 'dropdown-item marker-time-range-item'; 
                div.setAttribute('data-marker-range', item.range);
                div.textContent = item.text;
                // Check if active (default is one_week)
                if (item.range === layerToggleControl.currentMarkerTimeRange) div.classList.add('active'); 
                
                div.onclick = (e) => {
                    e.stopPropagation();
                    layerToggleControl.currentMarkerTimeRange = item.range;
                    layerToggleControl.updateMarkerVisibility();
                    this.updateMarkerTimeRangeUI();
                };
                this.categoryMenu.appendChild(div);
            });

             const sep1 = document.createElement('div');
             sep1.style.cssText = 'height: 1px; background-color: #eee; margin: 8px 0;';
             this.categoryMenu.appendChild(sep1);

            // 热力图时间范围
            const trTitle = document.createElement('div');
            trTitle.className = 'dropdown-item';
            trTitle.innerHTML = '<strong>热力图时间范围</strong>';
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
                     this.updateTimeRangeUI(); // Update immediate UI feedback
                 };
                 this.categoryMenu.appendChild(div);
            });

             const sep = document.createElement('div');
             sep.style.cssText = 'height: 1px; background-color: #eee; margin: 8px 0;';
             this.categoryMenu.appendChild(sep);

             // 全选/全不选
             const allBtn = document.createElement('div');
             allBtn.className = 'dropdown-item';
             allBtn.innerHTML = '<strong>热力图全选/全不选</strong>';
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
            this.updateTimeRangeUI();
            this.updateMarkerTimeRangeUI(); // Update marker UI
        }

        updateMarkerTimeRangeUI() {
            if (!this.categoryMenu) return;
            const items = this.categoryMenu.querySelectorAll('.dropdown-item[data-marker-range]');
            items.forEach(item => {
                if (item.getAttribute('data-marker-range') === layerToggleControl.currentMarkerTimeRange) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
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
                mapBase.addGeoJsonSource(l.id.replace('lines', 'layer'), `http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/${l.urlId}/query?where=1%3D1&outFields=*&f=geojson`, { promoteId: 'OBJECTID' });
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
                mapBase.addGeoJsonSource(srcId, `http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/${p.urlId}/query?where=1%3D1&outFields=*&f=geojson`, { promoteId: 'OBJECTID' });
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
            mapBase.addGeoJsonSource('arcgis-province-source', 'http://192.168.30.216:6080/arcgis/rest/services/OTN/province/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson', { promoteId: 'OBJECTID' });
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

        // 定义全局弹窗切换函数
        window.toggleFaultPopup = function(id) {
            const details = document.getElementById(`popup-details-${id}`);
            const icon = document.getElementById(`popup-icon-${id}`);
            if (details.style.display === 'none') {
                details.style.display = 'block';
                icon.className = 'mdi mdi-chevron-up'; // 假设使用了 MDI 图标，或者用字符
                icon.innerHTML = '▲'; 
            } else {
                details.style.display = 'none';
                icon.className = 'mdi mdi-chevron-down';
                icon.innerHTML = '▼';
            }
        };

        // 添加标记
        markerData.forEach((m, index) => {
             const category = m.category || 'other';
             const color = faultCategoryColors[category] || faultCategoryColors['other'];
             const uniqueId = `fault-${index}-${m.number}`;
             
             // 构建弹窗内容
             let popupHtml = `
                <div style="font-size:13px; max-width:350px; font-family: sans-serif;">
                    <h6 style="border-bottom:1px solid #eee; padding-bottom:8px; display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span>
                            <a href="${m.url}" target="_blank" style="font-weight:bold; color:#007bff; text-decoration:none;">${m.number}</a>
                            <span style="background:${color}; color:#fff; padding:2px 6px; border-radius:3px; font-size:11px; margin-left:5px; vertical-align:middle;">${m.category_display || faultCategoryNames[category]}</span>
                        </span>
                        <span style="background:${m.status_color || '#6c757d'}; color:#fff; padding:2px 6px; border-radius:3px; font-size:11px;">${m.status}</span>
                    </h6>
                    
                    <!-- 精简信息 -->
                    <table class="table table-sm table-borderless" style="margin-bottom:0; font-size:12px; width:100%;">
                        <tr><td style="width:70px; color:#666; font-weight:bold;">A端站点:</td><td>${m.a_site}</td></tr>
                        ${(m.z_sites && m.z_sites !== '未指定') ? `<tr><td style="color:#666; font-weight:bold;">Z端站点:</td><td>${m.z_sites}</td></tr>` : ''}
                        <tr><td style="color:#666; font-weight:bold;">中断时间:</td><td>${m.occurrence_time}</td></tr>
                        <tr><td style="color:#666; font-weight:bold;">故障历时:</td><td>${m.fault_duration}</td></tr>
                    </table>

                     <!-- 照片信息 (精简模式常驻显示) -->
                     ${(m.has_images && m.images.length > 0) ? `
                        <div style="margin-top:5px; margin-bottom:5px;">
                            <div style="display:flex; flex-wrap:wrap; gap:5px;">
                                ${m.images.map(img => {
                                    const isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(img.url);
                                    return isImage ? 
                                        `<a href="${img.url}" target="_blank" title="${img.name}"><img src="${img.url}" style="width:50px; height:50px; object-fit:cover; border-radius:3px; border:1px solid #ddd;" /></a>` :
                                        `<a href="${img.url}" target="_blank" style="font-size:11px;">📄 ${img.name}</a>`;
                                }).join('')}
                            </div>
                        </div>
                     ` : ''}

                    <!-- 展开按钮 -->
                    <div style="text-align:center; border-top:1px solid #eee; margin-top:5px; padding-top:5px; cursor:pointer; color:#007bff;" onclick="window.toggleFaultPopup('${uniqueId}')">
                        <span id="popup-icon-${uniqueId}">▼</span> 更多详情
                    </div>

                    <!-- 详细信息 (默认隐藏) -->
                    <div id="popup-details-${uniqueId}" style="display:none; border-top:1px dashed #eee; margin-top:5px; padding-top:5px;">
                        <table class="table table-sm table-borderless" style="margin-bottom:0; font-size:12px; width:100%;">
                            <tr><td style="width:70px; color:#666; font-weight:bold;">省份:</td><td>${m.province}</td></tr>
                            <tr><td style="color:#666; font-weight:bold;">恢复时间:</td><td>${m.recovery_time}</td></tr>
                            <tr><td style="color:#666; font-weight:bold;">故障原因:</td><td>${m.reason}</td></tr>
                            <tr><td style="color:#666; font-weight:bold;">故障详情/处理过程:</td><td>${m.fault_details}</td></tr>
                        </table>
             `;

             // 光缆故障特定字段 (放在详细信息中)
             if (category === 'fiber') {
                 popupHtml += `
                    <div style="margin-top:8px; padding-top:8px; border-top:1px dashed #eee;">
                        <div style="font-weight:bold; margin-bottom:4px; color:#333;">光缆故障信息</div>
                        <table class="table table-sm table-borderless" style="margin-bottom:0; font-size:12px; width:100%;">
                            <tr><td style="width:70px; color:#666;">资源类型:</td><td>${m.resource_type}</td></tr>
                            <tr><td style="color:#666;">路由属性:</td><td>${m.cable_route}</td></tr>
                            <tr><td style="color:#666;">中断部位:</td><td>${m.cable_break_location}</td></tr>
                            <tr><td style="color:#666;">恢复方式:</td><td>${m.recovery_mode}</td></tr>
                            <tr><td style="color:#666;">维护方式:</td><td>${m.maintenance_mode}</td></tr>
                            <tr><td style="color:#666;">处理单位:</td><td>${m.handling_unit}</td></tr>
                            <tr><td style="color:#666;">处理人:</td><td>${m.handler}</td></tr>
                        </table>
                    </div>
                 `;
             }

             popupHtml += `</div></div></div>`; // Close details, then wrapper
             
             const marker = mapBase.addMarker(m.lng, m.lat, { color: color, popup: popupHtml });
             // 传递发生时间用于筛选
             layerToggleControl.addMarker(marker, m.occurrence_time);
        });

        // 初始化只显示一周
        layerToggleControl.updateMarkerVisibility();

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

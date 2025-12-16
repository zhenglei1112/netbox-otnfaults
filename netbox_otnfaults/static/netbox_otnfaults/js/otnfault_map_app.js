
/**
 * NetBox OTN 故障分布图应用逻辑
 * 处理业务逻辑、数据处理和特定 UI 控件。
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. 配置与初始化
    const config = window.OTNFaultMapConfig;
    let heatmapData = config.heatmapData;
    let markerData = config.markerData;
    let sitesData = config.sitesData;
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
    if (!Array.isArray(sitesData)) {
        console.warn('sitesData 不是有效的数组，使用空数组');
        sitesData = [];
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
            this.arcgisButton.title = '传输网络图层'; // Updated title
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
                if (this.map.getLayer('otn-paths-layer')) mapBase.setLayoutProperty('otn-paths-layer', 'visibility', 'none');

                ['netbox-sites-layer', 'netbox-sites-labels'].forEach(layerId => {
                    mapBase.setLayoutProperty(layerId, 'visibility', 'none');
                });
                this.arcgisButton.classList.remove('active');
                return;
             }

             const currentZoom = this.map.getZoom();
             const isProvincialView = currentZoom >= 5;

             if (this.map.getLayer('otn-paths-layer')) mapBase.setLayoutProperty('otn-paths-layer', 'visibility', 'visible');

             const pointVisibility = isProvincialView ? 'visible' : 'none';
             ['netbox-sites-layer', 'netbox-sites-labels'].forEach(layerId => {
                 if (this.map.getLayer(layerId)) mapBase.setLayoutProperty(layerId, 'visibility', pointVisibility);
             });
             
             this.arcgisButton.classList.add('active');
        }
    }

    const layerToggleControl = new LayerToggleControl();
    // Move addControl to after CategoryFilterControl to ensure Filter is on top
    // mapBase.addControl(layerToggleControl, 'top-left');

    
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
             if (this.categoryMenu && this.categoryMenu.parentNode) {
                 this.categoryMenu.parentNode.removeChild(this.categoryMenu);
             }
        }

        createCategoryMenu() {
            this.categoryMenu = document.createElement('div');
            this.categoryMenu.className = 'category-filter-menu dropdown-menu';
            // Absolute positioning relative to the map container
            // REMOVED max-height and overflow-y per user request to avoid scrollbar
            this.categoryMenu.style.cssText = 'display: none; position: absolute; z-index: 99999; width: 220px; background-color: white; border: 1px solid #ddd; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); padding: 8px 0;'; 
            
            // Append to Map Container to support Fullscreen mode
            this.map.getContainer().appendChild(this.categoryMenu);

            this.categoryMenu.onclick = (e) => e.stopPropagation();

            // 标题
            const title = document.createElement('div');
            title.className = 'dropdown-item';
            title.innerHTML = '<strong>故障点时间范围</strong>';
            title.style.borderBottom = '1px solid #eee';
            this.categoryMenu.appendChild(title);

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
            
            // Calculate position relative to Map Container
            const mapRect = this.map.getContainer().getBoundingClientRect();
            const btnRect = this.filterButton.getBoundingClientRect();

            const relTop = btnRect.top - mapRect.top;
            const relLeft = btnRect.left - mapRect.left;
            
            // User Request: Pop up at the "Top-Right" of the filter button
            // Meaning: Right side of the button, aligned with the top edge
            this.categoryMenu.style.left = `${relLeft + btnRect.width + 5}px`; // 5px gap
            this.categoryMenu.style.top = `${relTop}px`;
            
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

             // Update Stats
             if (window.faultStatisticsControl) window.faultStatisticsControl.update();
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
    // Add LayerToggleControl AFTER CategoryFilterControl so it appears BELOW it
    mapBase.addControl(layerToggleControl, 'top-left');
    
    // 覆盖 layerToggleControl 的方法以调用我们的刷新
    const originalReload = layerToggleControl.reloadHeatmapData.bind(layerToggleControl);
    layerToggleControl.reloadHeatmapData = function(range) {
        // 直接调用 categoryFilterControl，它同处理时间和分类
        this.currentTimeRange = range;
        this.updateButtonTitle(range);
        categoryFilterControl.reloadHeatmapData();
        categoryFilterControl.updateTimeRangeUI(); // Update UI
    };

    // 统计控件类
    class FaultStatisticsControl {
        constructor() {
            this.container = null;
            this.toggleBtn = null;
            this.panel = null;
            this.faults = [];
            this.stats = { sites: [], paths: [] };
            this.expanded = false; // Initial state: Collapsed
        }

        onAdd(map) {
            this.map = map;
            this.container = document.createElement('div');
            this.container.className = 'maplibregl-ctrl fault-stats-control';
            
            // Container styles (transparent wrapper)
            this.container.style.cssText = `
                pointer-events: auto;
                margin: 0 0 40px 10px; /* Positioned at bottom-left, slightly above scale/attrib if any */
                display: flex;
                flex-direction: column;
                align-items: flex-start;
            `;

            // 1. Toggle Button (Visible when collapsed)
            this.toggleBtn = document.createElement('button');
            this.toggleBtn.className = 'btn btn-sm btn-light border';
            this.toggleBtn.title = '查看高发故障统计';
            this.toggleBtn.style.cssText = `
                width: 32px;
                height: 32px;
                padding: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                background-color: var(--bs-body-bg, #ffffff);
            `;
            // Icon: Top-Right Arrow (↗)
            this.toggleBtn.innerHTML = `<svg viewBox="0 0 24 24" style="width:20px;height:20px;stroke:currentColor;stroke-width:2;fill:none;"><path d="M7 17L17 7M17 7H7M17 7V17"></path></svg>`;
            
            this.toggleBtn.onclick = () => {
                this.expanded = true;
                this.renderVisibility();
            };

            // 2. Content Panel (Visible when expanded)
            this.panel = document.createElement('div');
            this.panel.style.cssText = `
                background-color: var(--bs-body-bg, #ffffff);
                color: var(--bs-body-color, #212529);
                border: 1px solid var(--bs-border-color, #dee2e6);
                border-radius: 4px;
                padding: 10px;
                width: 300px;
                /* max-height: 400px; REMOVED per user request */
                /* overflow-y: auto; REMOVED per user request */
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                font-size: 12px;
                display: none; /* Initially hidden */
            `;

            // Header with Close Button
            const header = document.createElement('div');
            header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid var(--bs-border-color); padding-bottom: 5px;';
            
            const title = document.createElement('strong');
            title.textContent = '高发故障统计';
            
            const closeBtn = document.createElement('button');
            closeBtn.className = 'btn btn-sm btn-link p-0';
            closeBtn.title = '收起';
            closeBtn.style.cssText = 'color: var(--bs-secondary-text); text-decoration: none;';
            // Icon: Bottom-Left Arrow (↙)
            closeBtn.innerHTML = `<svg viewBox="0 0 24 24" style="width:20px;height:20px;stroke:currentColor;stroke-width:2;fill:none;"><path d="M17 7L7 17M7 17V7M7 17H17"></path></svg>`;
            
            closeBtn.onclick = (e) => {
                e.stopPropagation();
                this.expanded = false;
                this.renderVisibility();
            };

            header.appendChild(title);
            header.appendChild(closeBtn);
            this.panel.appendChild(header);

            // Content Area
            this.content = document.createElement('div');
            this.panel.appendChild(this.content);

            this.container.appendChild(this.toggleBtn);
            this.container.appendChild(this.panel);
            
            this.update(); // Initial calculation and render
            this.renderVisibility(); // Set initial visibility state
            
            return this.container;
        }

        renderVisibility() {
            if (this.expanded) {
                this.toggleBtn.style.display = 'none';
                this.panel.style.display = 'block';
            } else {
                this.toggleBtn.style.display = 'flex';
                this.panel.style.display = 'none';
            }
        }

        onRemove() {
            if (this.container && this.container.parentNode) {
                this.container.parentNode.removeChild(this.container);
            }
            this.map = undefined;
        }

        update() {
            if (!this.container) return;
            this.calculateStats();
            this.renderContent();
        }

        calculateStats() {
            // 获取当前的过滤条件
            const timeRange = layerToggleControl.currentTimeRange;
            const selectedCategories = categoryFilterControl ? categoryFilterControl.selectedCategories : [];
            const markers = markerData || []; // markerData 包含完整信息

            const now = new Date();
            let startDate;
            if (timeRange === 'month') startDate = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
            else if (timeRange === 'three_months') startDate = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
            else startDate = new Date(now.getFullYear(), 0, 1);

            // 过滤故障
            const filteredFaults = markers.filter(fault => {
                if (!fault.occurrence_time) return false;
                const faultDate = new Date(fault.occurrence_time);
                if (faultDate < startDate) return false;
                
                const category = fault.category || 'other';
                return selectedCategories.includes(category);
            });

            // 统计
            const siteCounts = {};
            const pathCounts = {};
            
            // 辅助：获取 Site ID -> Info 映射
            if (!this.siteMap) {
                this.siteMap = {};
                (sitesData || []).forEach(s => this.siteMap[s.id] = s);
            }

            // 辅助：获取 Path 映射 (从全局 window.OTNPathsMetadata)
            const paths = window.OTNPathsMetadata || [];

            filteredFaults.forEach(fault => {
                if (!fault.z_site_ids || fault.z_site_ids.length === 0) {
                    // 单站点故障
                    const siteId = fault.a_site_id;
                    if (siteId) {
                        if (!siteCounts[siteId]) siteCounts[siteId] = { id: siteId, name: fault.a_site, count: 0 };
                        siteCounts[siteId].count++;
                    }
                } else {
                    // 多站点（路径）故障
                    fault.z_site_ids.forEach(zId => {
                        // 查找路径
                        const aId = fault.a_site_id;
                        if (!aId) return;

                        // 在路径库中查找匹配的
                        const path = paths.find(p => {
                            const pA = p.properties.site_a_id;
                            const pZ = p.properties.site_z_id;
                            return (pA === aId && pZ === zId) || (pA === zId && pZ === aId);
                        });

                        if (path) {
                            const pathId = path.properties.id;
                            if (!pathCounts[pathId]) pathCounts[pathId] = { id: pathId, name: path.properties.name, count: 0, geometry: path.geometry };
                            pathCounts[pathId].count++;
                        } else {
                            // 未找到路径模型，忽略或记录为未知
                        }
                    });
                }
            });

            // 排序并取 Top 5
            this.stats.sites = Object.values(siteCounts).sort((a, b) => b.count - a.count).slice(0, 5);
            this.stats.paths = Object.values(pathCounts).sort((a, b) => b.count - a.count).slice(0, 5);
        }

        renderContent() {
            this.content.innerHTML = '';

            // Filter Info Sub-header (Global for the panel)
            const filterInfoDiv = document.createElement('div');
            filterInfoDiv.style.cssText = 'font-size: 11px; color: #6c757d; margin-bottom: 10px; padding: 0 4px;';
            
            // 1. Get Time Range Text
            const timeRangeMap = {
                'one_week': '一周',
                'month': '一个月',
                'three_months': '三个月', 
                'year': '一年'
            };
            const trKey = layerToggleControl.currentTimeRange || 'year';
            const timeText = timeRangeMap[trKey] || '本年度';

            // 2. Get Category Text
            const allCats = Object.keys(faultCategoryNames);
            const selectedCats = categoryFilterControl ? categoryFilterControl.selectedCategories : [];
            let catText = '';
            if (selectedCats.length === allCats.length) {
                catText = '全部故障';
            } else {
                catText = selectedCats.map(c => faultCategoryNames[c]).join('、');
            }

            filterInfoDiv.textContent = `${timeText}，${catText}`;
            this.content.appendChild(filterInfoDiv);
            
            // Icons (SVG)
            const icons = {
                // Site: House Icon with 2 lines (matched to reference)
                site: `<svg viewBox="0 0 1024 1024" style="width:14px;height:14px;fill:var(--bs-danger);"><path d="M512 44.23L45.42 411.58h41.01v568.19h851.14V411.58h41.01L512 44.23z m-212.78 454.55h425.57v85.11H299.22v-85.11z m0 198.6h425.57v85.11H299.22v-85.11z" /></svg>`,
                // Path: Network/Molecule Icon (matched to reference)
                path: `<svg viewBox="0 0 1024 1024" style="width:14px;height:14px;fill:var(--bs-primary);"><path d="M512 512m-128 0a128 128 0 1 0 256 0 128 128 0 1 0-256 0Z"/><path d="M512 128m-96 0a96 96 0 1 0 192 0 96 96 0 1 0-192 0Z"/><path d="M192 768m-96 0a96 96 0 1 0 192 0 96 96 0 1 0-192 0Z"/><path d="M832 768m-96 0a96 96 0 1 0 192 0 96 96 0 1 0-192 0Z"/><path d="M512 384V224" stroke="currentColor" stroke-width="64" stroke-linecap="round"/><path d="M370.4 679.6L274.5 768" stroke="currentColor" stroke-width="64" stroke-linecap="round"/><path d="M653.6 679.6l95.9 88.4" stroke="currentColor" stroke-width="64" stroke-linecap="round"/></svg>`
            };

            const createSection = (title, items, type) => {
                const section = document.createElement('div');
                section.style.marginBottom = '15px';
                
                const titleEl = document.createElement('h6');
                titleEl.textContent = title;
                titleEl.style.cssText = 'font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid var(--bs-border-color); padding-bottom: 4px;';
                section.appendChild(titleEl);

                if (items.length === 0) {
                    const empty = document.createElement('div');
                    empty.textContent = '无数据';
                    empty.style.color = 'var(--bs-secondary-color)';
                    section.appendChild(empty);
                } else {
                    const ul = document.createElement('ul');
                    ul.style.cssText = 'list-style: none; padding: 0; margin: 0;';
                    
                    // Find max count for progress bar percentage
                    // Use the first item (max value) as 100% baseline to maximize visual differentiation
                    const maxVal = items.length > 0 ? items[0].count : 0;
                    const maxCount = maxVal > 0 ? maxVal : 1;

                    items.forEach((item, index) => {
                        const li = document.createElement('li');
                        li.style.cssText = 'padding: 6px 0; border-bottom: 1px dashed var(--bs-border-color); cursor: pointer; display: flex; align-items: center;';
                        
                        // 1. Ranking Badge (Neutral 1-5)
                        const rankBadge = document.createElement('div');
                        rankBadge.textContent = index + 1;
                        rankBadge.style.cssText = `
                            width: 18px; height: 18px; 
                            background-color: #e9ecef; 
                            color: #495057; 
                            border-radius: 50%; 
                            display: flex; align-items: center; justify-content: center; 
                            font-size: 10px; font-weight: bold;
                            margin-right: 8px; flex-shrink: 0;
                        `;
                        
                        // 3. Content (Name + Progress Bar)
                        const contentDiv = document.createElement('div');
                        contentDiv.style.cssText = 'flex: 1; min-width: 0;';
                        
                        const nameDiv = document.createElement('div');
                        nameDiv.textContent = item.name;
                        nameDiv.title = item.name;
                        nameDiv.style.cssText = 'white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500;';
                        
                        // Progress Bar
                        const countVal = Number(item.count) || 0;
                        const maxCountNum = Number(maxCount) || 1;
                        let percent = (countVal / maxCountNum) * 100;
                        if (percent > 100) percent = 100;
                        
                        console.log(`[StatsDebug] ${item.name}: ${countVal}/${maxCountNum} = ${percent}%`);

                        const progressWrapper = document.createElement('div');
                        progressWrapper.style.cssText = 'height: 4px; background-color: #f0f0f0; border-radius: 2px; margin-top: 3px; overflow: hidden;';
                        
                        const progressBar = document.createElement('div');
                        progressBar.style.height = '100%';
                        // Use CSS vars with fallbacks
                        // Updated to use NetBox theme link color as requested
                        const barColor = 'var(--bs-link-color, #0097a7)';
                        progressBar.style.backgroundColor = barColor;
                        progressBar.style.width = `${percent}%`;
                        
                        progressWrapper.appendChild(progressBar);

                        contentDiv.appendChild(nameDiv);
                        contentDiv.appendChild(progressWrapper);

                        // 4. Count Badge
                        const countSpan = document.createElement('span');
                        countSpan.textContent = `${item.count}次`;
                        countSpan.style.cssText = 'margin-left: 10px; font-size: 11px; color: var(--bs-secondary-color); white-space: nowrap;';

                        li.appendChild(rankBadge);
                        // li.appendChild(iconWrapper); // Removed
                        li.appendChild(contentDiv);
                        li.appendChild(countSpan);
                        
                        li.onclick = () => {
                            if (type === 'site') this.flyToSite(item.id);
                            else this.flyToPath(item);
                        };
                        li.onmouseenter = () => li.style.backgroundColor = 'var(--bs-tertiary-bg)';
                        li.onmouseleave = () => li.style.backgroundColor = 'transparent';

                        ul.appendChild(li);
                    });
                    section.appendChild(ul);
                }
                return section;
            };

            this.content.appendChild(createSection('故障高发站点 (Top 5)', this.stats.sites, 'site'));
            this.content.appendChild(createSection('故障高发路径 (Top 5)', this.stats.paths, 'path'));
        }

        flyToSite(siteId) {
            const site = this.siteMap[siteId];
            if (site) {
                this.map.flyTo({
                    center: [site.longitude, site.latitude],
                    zoom: 12,
                    speed: 1.5
                });
                 new maplibregl.Popup({ closeOnClick: true })
                    .setLngLat([site.longitude, site.latitude])
                    .setHTML(`<strong>${site.name}</strong>`)
                    .addTo(this.map);
            }
        }

        flyToPath(pathItem) {
            if (pathItem.geometry) {
                // Highlight Path
                const highlightSource = this.map.getSource('otn-paths-highlight');
                if (highlightSource) {
                    highlightSource.setData({
                        type: 'Feature',
                        geometry: pathItem.geometry
                    });
                    mapBase.setLayoutProperty('otn-paths-highlight-layer', 'visibility', 'visible');
                }

                const bounds = new maplibregl.LngLatBounds();
                if (pathItem.geometry.type === 'LineString') {
                    pathItem.geometry.coordinates.forEach(c => bounds.extend(c));
                }
                if (!bounds.isEmpty()) {
                    this.map.fitBounds(bounds, { padding: 100 });
                }
            }
        }
    }

    const faultStatisticsControl = new FaultStatisticsControl();
    window.faultStatisticsControl = faultStatisticsControl;
    mapBase.addControl(faultStatisticsControl, 'bottom-left');




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

        // OtnPath 图层 (NetBox Internal)
        fetch('/api/plugins/otnfaults/paths/?limit=0', {
            headers: {
                'Authorization': `Token ${apiKey}`, // Assuming apiKey can be used as token or is handled by session cookies if same domain
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            const results = data.results || [];
            const pathFeatures = results
                .filter(path => path.geometry) // Only process paths with geometry
                .map(path => {
                    let geometry = path.geometry;
                    // Handle raw coordinate array format (e.g. [[lng, lat], ...])
                    if (Array.isArray(geometry)) {
                        geometry = {
                            type: 'LineString',
                            coordinates: geometry
                        };
                    }
                    
                    return {
                        type: 'Feature',
                        properties: {
                            id: path.id,
                            name: path.name,
                            cable_type: path.cable_type?.label || path.cable_type,
                            description: path.description,
                            site_a_id: path.site_a.id, // Ensure we have these for matching
                            site_z_id: path.site_z.id
                        },
                        geometry: geometry
                    };
                });

            // Store globally for stats matching
            window.OTNPathsMetadata = pathFeatures;
            // Update stats now that we have paths
            if (window.faultStatisticsControl) window.faultStatisticsControl.update();

            mapBase.addGeoJsonSource('otn-paths', {
                type: 'FeatureCollection',
                features: pathFeatures
            });

            // Find the first symbol layer to place the path layer under labels
            const layers = map.getStyle().layers;
            let firstSymbolId;
            for (const layer of layers) {
                if (layer.type === 'symbol') {
                    firstSymbolId = layer.id;
                    break;
                }
            }

            mapBase.addLayer({
                id: 'otn-paths-layer',
                type: 'line',
                source: 'otn-paths',
                paint: {
                    'line-color': themeLinkColor,
                    'line-width': 3,
                    'line-opacity': 0.8
                },
                layout: {
                    'line-join': 'round',
                    'line-cap': 'round'
                }
            }, firstSymbolId);

            // 添加高亮图层
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
                    'line-width': 6,
                    'line-opacity': 0.8
                },
                layout: {
                    'line-join': 'round',
                    'line-cap': 'round',
                    'visibility': 'none'
                }
            });

            // 移除弹窗逻辑 (No click/hover listener for otn-paths-layer as requested)
            
            // 自适应包含路径
             if (pathFeatures.length > 0) {
                 const pathBounds = new maplibregl.LngLatBounds();
                 pathFeatures.forEach(f => {
                     // Handle LineString coordinates
                     if (f.geometry.type === 'LineString') {
                        f.geometry.coordinates.forEach(coord => pathBounds.extend(coord));
                     }
                 });
                 // We don't necessarily force fit bounds here as we have faults and sites too, 
                 // but it's good data availability check.
             }
        })
        .catch(error => console.error('Error fetching OTN paths:', error));

            // NetBox 站点图层
            // 创建GeoJSON数据源
            const siteFeatures = sitesData.map(site => ({
                type: 'Feature',
                properties: {
                    id: site.id,
                    name: site.name,
                    url: site.url,
                    status: site.status,
                    status_color: site.status_color,
                    tenant: site.tenant || '-',
                    region: site.region || '-',
                    group: site.group || '-',
                    facility: site.facility || '-',
                    description: site.description || ''
                },
                geometry: {
                    type: 'Point',
                    coordinates: [site.longitude, site.latitude]
                }
            }));

            mapBase.addGeoJsonSource('netbox-sites', { type: 'FeatureCollection', features: siteFeatures });

            // 站点点图层
            mapBase.addLayer({
                id: 'netbox-sites-layer',
                type: 'circle',
                source: 'netbox-sites',
                paint: {
                    'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, 4, 10, 6, 15, 10],
                    'circle-color': '#00aaff', // 使用之前的蓝色系
                    'circle-stroke-width': 1,
                    'circle-stroke-color': '#fff'
                }
            });

            // 站点标签图层
            mapBase.addLayer({
                id: 'netbox-sites-labels',
                type: 'symbol',
                source: 'netbox-sites',
                layout: {
                    'text-field': ['get', 'name'],
                    'text-font': ['Arial Unicode MS Bold', 'sans-serif'],
                    'text-size': 13,
                    'text-offset': [0, -1.5],
                    'text-anchor': 'bottom'
                },
                paint: {
                    'text-color': '#fff',
                    'text-halo-color': 'rgba(0,0,0,0.8)',
                    'text-halo-width': 2
                }
            });

            // 站点交互
            let hoveredSiteId = null;
            map.on('mouseenter', 'netbox-sites-layer', (e) => {
                map.getCanvas().style.cursor = 'pointer';
            });
            map.on('mouseleave', 'netbox-sites-layer', () => {
                map.getCanvas().style.cursor = '';
            });

            map.on('click', 'netbox-sites-layer', (e) => {
                const props = e.features[0].properties;
                let content = `
                <h6>${props.name}</h6>
                <table class="table table-sm table-striped">
                    <tr><th>地区</th><td>${props.region || '-'}</td></tr>
                    <tr><th>状态</th><td><span class="badge" style="background-color: #${props.status_color || '6c757d'}">${props.status || '-'}</span></td></tr>
                    <tr><td colspan="2"><a href="${props.url}" target="_blank">查看详情</a></td></tr>
                </table>`;
                
                new maplibregl.Popup()
                    .setLngLat(e.lngLat)
                    .setHTML(content)
                    .addTo(map);
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



             // 同步按钮状态
             layerToggleControl.updateArcgisLayersVisibility();
             map.on('zoom', () => { if (layerToggleControl.arcgisVisible) layerToggleControl.updateArcgisLayersVisibility(); });



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
                        <tr><td style="color:#666; font-weight:bold;">影响业务:</td><td>${m.impacted_business}</td></tr>
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

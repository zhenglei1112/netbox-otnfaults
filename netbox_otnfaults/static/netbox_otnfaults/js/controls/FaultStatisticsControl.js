/**
 * 故障统计面板控件
 */
class FaultStatisticsControl {
    constructor() {
        this.container = null;
        this.minimized = true; // 初始状态为收起
        this.currentPopup = null;
    }

    onAdd(map) {
        this.map = map;
        this.container = document.createElement('div');
        this.container.className = 'maplibregl-ctrl fault-statistics';
        
        // 初始渲染
        this.renderContent();

        // 阻止地图事件传播
        ['mousedown', 'click', 'dblclick', 'touchstart'].forEach(event => {
            this.container.addEventListener(event, e => e.stopPropagation());
        });

        return this.container;
    }
    
    // 渲染最小化按钮状态
    renderVisibility() {
        const contentDiv = this.container.querySelector('.stats-content');
        const headerIcon = this.container.querySelector('.toggle-icon');
        
        if (this.minimized) {
            if (contentDiv) contentDiv.style.display = 'none';
            if (headerIcon) headerIcon.className = 'mdi mdi-chevron-up toggle-icon';
        } else {
            if (contentDiv) contentDiv.style.display = 'block';
            if (headerIcon) headerIcon.className = 'mdi mdi-chevron-down toggle-icon';
        }
    }

    onRemove() {
        this.container.parentNode.removeChild(this.container);
        this.map = undefined;
    }

    update() {
        if (this.container) {
            this.renderContent();
            this.renderVisibility(); // 保持折叠状态
        }
    }
    
    /**
     * 设置用于统计的故障数据列表
     * @param {Array} faultDataList - 包含故障属性的对象数组
     */
    setData(faultDataList) {
        this.faultDataList = faultDataList;
        this.update();
    }

    // 计算统计数据
    calculateStats() {
        // 如果有显式设置的数据列表，则使用它
        // 否则回退到旧逻辑（遍历 DOM markers，不推荐）
        if (this.faultDataList) {
            return this.calculateStatsFromList(this.faultDataList);
        }
        
        // 旧逻辑 fallback (如果 updateMapState 还没调用)
        // 如果没有通过 setData 提供数据，则使用旧的基于 DOM marker 的逻辑
        const visibleMarkers = (window.OTNMapMarkers || []).filter(item => {
            return item.marker.getElement().style.display !== 'none';
        });

        const totalFaults = visibleMarkers.length;
        
        // 按站点统计
        const siteCounts = {};
        // 按波道/路径统计
        const pathCounts = {};
        
        let totalDurationHours = 0;
        let validDurationCount = 0;

        visibleMarkers.forEach(item => {
            const props = item.feature.properties;
            
            // 站点
            if (props.site_name) {
                siteCounts[props.site_name] = (siteCounts[props.site_name] || 0) + 1;
            }
            // 路径 (a_site -> z_site)
            const pathName = `${props.a_site_name || '?'} <-> ${props.z_site_name || '?'}`;
            if (!pathCounts[pathName]) {
                pathCounts[pathName] = {
                    count: 0,
                    pathId: props.otn_path_id, // 假设关联了路径ID
                    a_site: props.a_site_name,
                    z_site: props.z_site_name
                };
            }
            pathCounts[pathName].count++;
            
            // 统计时长
            if (props.fault_occurrence_time && props.fault_recovery_time) {
                const start = new Date(props.fault_occurrence_time);
                const end = new Date(props.fault_recovery_time);
                const hours = (end - start) / (1000 * 3600);
                if (hours > 0) {
                    totalDurationHours += hours;
                    validDurationCount++;
                }
            } else if (props.fault_occurrence_time) {
                // 未恢复，计算至当前
                 const start = new Date(props.fault_occurrence_time);
                 const end = new Date();
                 const hours = (end - start) / (1000 * 3600);
                 if (hours > 0) {
                    totalDurationHours += hours;
                    validDurationCount++;
                 }
            }
        });

        const sortedSites = Object.entries(siteCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5); // Top 5
            
        const sortedPaths = Object.entries(pathCounts)
            .sort((a, b) => b[1].count - a[1].count)
            .slice(0, 5); // Top 5

        const avgDuration = validDurationCount > 0 ? (totalDurationHours / validDurationCount).toFixed(1) : 0;

        return {
            total: totalFaults,
            topSites: sortedSites,
            topPaths: sortedPaths,
            avgDuration: avgDuration
        };
    }

    calculateStatsFromList(faults) {
        let totalFaults = faults.length;
        let totalDurationHours = 0;
        let validDurationCount = 0;
        const siteCounts = {};
        const pathCounts = {};
        
        faults.forEach(f => {
            // 统计站点
            if (f.a_site) siteCounts[f.a_site] = (siteCounts[f.a_site] || 0) + 1;
            // if (f.z_sites) ... (Z端可能是列表，这里简化)

            // 统计路径
            // 假设我们能构建唯一路径标识
             if (f.a_site && f.z_sites) {
                 const key = `${f.a_site} <-> ${f.z_sites}`; 
                 if (!pathCounts[key]) {
                      pathCounts[key] = { count: 0, a_site: f.a_site, z_site: f.z_sites }; // 保存元数据供飞行动画使用
                 }
                 pathCounts[key].count++;
             }
             
             // 统计时长
             // 解析 "Xh" 字符串 或 使用 raw minutes
             // 假设后端传的是 "12.5h" 或 类似，或者我们有原始时间
             // 这里尝试直接用 duration_minutes 如果存在，或者重新计算
             if (f.occurrence_time) {
                 const start = new Date(f.occurrence_time);
                 const end = f.recovery_time ? new Date(f.recovery_time) : new Date();
                 const hours = (end - start) / (1000 * 3600);
                 if (hours > 0) {
                     totalDurationHours += hours;
                     validDurationCount++;
                 }
             }
        });

        // Top 5 站点
        const topSites = Object.entries(siteCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5); // [name, count]
            
        // Top 5 路径
        const topPaths = Object.entries(pathCounts)
            .sort((a, b) => b[1].count - a[1].count)
             .slice(0, 5); // [name, {count, ...}]

        const avgDuration = validDurationCount > 0 ? (totalDurationHours / validDurationCount).toFixed(1) : 0;

        return {
            total: totalFaults,
            avgDuration,
            topSites,
            topPaths
        };
    }

    renderContent() {
        const stats = this.calculateStats();
        const layerToggle = window.layerToggleControl;
        const categoryFilter = window.categoryFilterControl;
        
        // 获取当前筛选状态文本
        let timeRangeText = '最近1周';
        if (layerToggle) {
            const texts = { 
                '1week': '最近1周', 
                '2weeks': '最近2周', 
                '1month': '最近1月',
                '3months': '最近3月',
                '1year': '最近1年'
            };
            timeRangeText = texts[layerToggle.currentTimeRange] || layerToggle.currentTimeRange;
        }
        
        let categoryText = '全部类型';
        if (categoryFilter) {
            const count = categoryFilter.selectedCategories.length;
            const total = Object.keys(FAULT_CATEGORY_COLORS).length;
            if (count === total) {
                categoryText = '全部类型';
            } else if (count === 0) {
                categoryText = '无类型';
            } else {
                // Map category keys to names
                // FAULT_CATEGORY_NAMES should be globally available from CategoryFilterControl.js
                const names = categoryFilter.selectedCategories.map(cat => FAULT_CATEGORY_NAMES[cat] || cat);
                categoryText = names.join('、');
            }
        }

        // 初始图标根据 minimized 状态设置
        const toggleIconClass = this.minimized ? 'mdi mdi-chevron-up toggle-icon' : 'mdi mdi-chevron-down toggle-icon';
        const contentDisplay = this.minimized ? 'none' : 'block';
        
        this.container.innerHTML = `
            <div class="card shadow-sm" style="width: 240px; opacity: 0.95;">
                <div class="card-header py-2 d-flex justify-content-between align-items-center bg-body-tertiary" 
                     style="cursor: pointer;" onclick="this.closest('.fault-statistics')._control.toggleMinimize(event)">
                    <span class="fw-bold mb-0" style="font-size: 14px;">故障统计</span>
                    <i class="${toggleIconClass}"></i>
                </div>
                <div class="card-header py-1 bg-body text-body-secondary" style="font-size: 11px; border-top: 1px solid var(--bs-border-color);">
                     <span>筛选: ${timeRangeText} · ${categoryText}</span>
                </div>
                <div class="stats-summary px-2 py-2 bg-body" style="font-size: 12px; border-top: 1px solid var(--bs-border-color);">
                    <span>故障数: </span><span class="fw-bold" style="color: var(--bs-link-color, #0097a7) !important;">${stats.total}</span>
                    <span class="mx-2 text-body-secondary">|</span>
                    <span>平均: </span><span class="fw-bold" style="color: var(--bs-link-color, #0097a7) !important;">${stats.avgDuration}小时</span>
                </div>
                <div class="card-body p-2 stats-content" style="font-size: 13px; display: ${contentDisplay}; border-top: 1px solid var(--bs-border-color);">
                    ${this.createSection('Top 5 故障站点', stats.topSites, 'site')}
                    ${this.createSection('Top 5 故障路径', stats.topPaths, 'path')}
                </div>
            </div>
        `;
        
        // 绑定实例以便 onclick 访问
        this.container._control = this;
    }
    
    toggleMinimize(e) {
        e.stopPropagation();
        this.minimized = !this.minimized;
        this.renderVisibility();
    }
    
    createSection(title, items, type) {
        if (items.length === 0) return '';
        
        // Calculate max value for the progress bar explicitly
        let maxVal = 0;
        if (items.length > 0) {
            if (type === 'site') {
                maxVal = items[0][1];
            } else {
                maxVal = items[0][1].count;
            }
        }
        
        const rows = items.map((item, index) => {
            const name = item[0];
            let count = 0;
            
            if (type === 'site') {
                count = item[1];
            } else {
                count = item[1].count;
            }
            
            const percent = maxVal > 0 ? (count / maxVal) * 100 : 0;
            const func = type === 'site' ? 'flyToSite' : 'flyToPath';
            
            // 安全处理名称中的引号
            const safeName = name.replace(/'/g, "\\'");

            return `
                <div class="mb-2 clickable-stat-row" 
                     title="点击定位"
                     style="cursor: pointer;"
                     onclick="window.faultStatisticsControl.${func}('${safeName}')">
                    <div class="d-flex justify-content-between align-items-center mb-1" style="font-size: 12px;">
                        <div class="text-truncate me-2 text-body-secondary" style="max-width: 180px;">${index + 1}. ${name}</div>
                        <span class="fw-bold" style="color: var(--bs-link-color, #0097a7) !important;">${count}</span>
                    </div>
                    <div class="progress" style="height: 4px; background-color: #e9ecef;">
                         <div class="progress-bar" role="progressbar" 
                              style="width: ${percent}%; background-color: var(--bs-link-color, #0097a7);">
                         </div>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="mb-2 border-top pt-2">
                <div class="fw-bold mb-1 text-secondary" style="font-size: 12px;">${title}</div>
                ${rows}
            </div>
        `;
    }
    
    // 定位到站点
    flyToSite(siteName) {
        // 先找到对应的 Site Feature
        // 假设 window.OTNFaultMapConfig.sitesData 是原始数据，但已转换为 GeoJSON
        // 我们从 map source 获取或直接遍历 sitesData
        const sites = window.OTNFaultMapConfig.sitesData;
        const target = sites.find(s => s.name === siteName);
        
        if (target) {
            // Robustly remove ANY existing popups
            const existingPopups = document.getElementsByClassName('maplibregl-popup');
            while (existingPopups.length > 0) {
                existingPopups[0].remove();
            }
            if (this.currentPopup) {
                this.currentPopup.remove();
                this.currentPopup = null;
            }

            this.map.flyTo({
                center: [target.longitude, target.latitude],
                zoom: 12,
                essential: true,
                speed: 2.5 // Adjusted speed
            });
            
            // 可以触发 Popup
            this.currentPopup = new maplibregl.Popup()
                    .setLngLat([target.longitude, target.latitude])
                    .setHTML(`<b>${target.name}</b><br>位于此处的故障高发站点`)
                    .addTo(this.map);
             
             // Cleanup on close
             this.currentPopup.on('close', () => {
                 this.currentPopup = null;
             });
        }
    }
    
    // 定位到路径
    // pathItemKey 是 "A <-> Z" 字符串，这里我们需要解析它
    // 实际上上面的 onclick 传递了 name，我们可以重新在 paths 中查找
    flyToPath(pathName) {
        // 解析 A 和 Z
        // 格式 "A <-> Z"
        const parts = pathName.split(' <-> ');
        if (parts.length !== 2) return;
        const siteA = parts[0];
        const siteZ = parts[1];
        
        // 在 OTNPathsMetadata 中查找
        const paths = window.OTNPathsMetadata || [];
        const targetPath = paths.find(p => {
             // 简单的名称匹配，可能不严谨，最好用 ID
             const props = p.properties;
             return (props.a_site === siteA && props.z_site === siteZ) || 
                    (props.a_site === siteZ && props.z_site === siteA);
        });

        if (targetPath) {
             // 计算 Bounds
             const coords = targetPath.geometry.coordinates; // LineString
             const bounds = new maplibregl.LngLatBounds();
             coords.forEach(c => bounds.extend(c));
             
             this.map.fitBounds(bounds, { padding: 100, speed: 2.5 }); // Adjusted speed
             
              // 高亮
             if (this.map.getSource('otn-paths-highlight')) {
                this.map.getSource('otn-paths-highlight').setData(targetPath);
             }
        }
    }
}

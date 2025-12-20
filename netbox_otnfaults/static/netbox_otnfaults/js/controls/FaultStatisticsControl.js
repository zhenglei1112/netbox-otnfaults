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
            // 统计站点（只统计A端有值且Z端为空的故障，与 single_site_a_id 过滤器逻辑一致）
            const hasZSites = f.z_site_ids && f.z_site_ids.length > 0;
            if (f.a_site && !hasZSites) {
                siteCounts[f.a_site] = (siteCounts[f.a_site] || 0) + 1;
            }

            // 统计路径（仅统计光缆故障且A、Z端都有值的故障）
            // 路径故障必须满足：1) 故障类型为光缆（fiber）2) A端有值 3) Z端有值
             if (f.a_site && f.z_sites && f.category === 'fiber') {
                 // 规范化路径key：使用字典序排序，确保A->Z和Z->A被视为同一条路径
                 const siteA = f.a_site;
                 const siteZ = f.z_sites;
                 
                 // 使用字典序较小的作为key的第一个站点
                 const [site1, site2] = siteA < siteZ ? [siteA, siteZ] : [siteZ, siteA];
                 const normalizedKey = `${site1} <-> ${site2}`;
                 
                 if (!pathCounts[normalizedKey]) {
                      pathCounts[normalizedKey] = { 
                          count: 0, 
                          a_site: site1,  // 保存规范化后的站点顺序
                          z_site: site2,
                          displayName: normalizedKey  // 显示名称
                      };
                 }
                 pathCounts[normalizedKey].count++;
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
    
    /**
     * 计算站点在不同时间范围内的故障统计
     * @param {string} siteName - 站点名称
     * @returns {Object} 各时间范围的故障次数
     */
    calculateSiteTimeStats(siteName) {
        // 使用原始的一年内所有故障数据，不受时间范围筛选影响
        const markerData = (window.OTNFaultMapConfig && window.OTNFaultMapConfig.markerData) || [];
        // 使用DEBUG模式的时间或当前时间
        const now = window.OTN_DEBUG_MODE ? new Date(window.OTN_DEBUG_DATE) : new Date();
        
        // 时间范围定义（毫秒）
        const ranges = {
            '1week': 7 * 24 * 60 * 60 * 1000,
            '2weeks': 14 * 24 * 60 * 60 * 1000,
            '1month': 30 * 24 * 60 * 60 * 1000,
            '3months': 90 * 24 * 60 * 60 * 1000,
            '1year': 365 * 24 * 60 * 60 * 1000
        };
        
        const stats = { '1week': 0, '2weeks': 0, '1month': 0, '3months': 0, '1year': 0 };
        
        markerData.forEach(m => {
            // 站点统计：A端站点匹配且Z端为空
            const hasZSites = m.z_site_ids && m.z_site_ids.length > 0;
            if (m.a_site === siteName && !hasZSites && m.occurrence_time) {
                const occTime = new Date(m.occurrence_time);
                const timeDiff = now - occTime;
                
                // 累积统计各时间范围
                if (timeDiff <= ranges['1week']) stats['1week']++;
                if (timeDiff <= ranges['2weeks']) stats['2weeks']++;
                if (timeDiff <= ranges['1month']) stats['1month']++;
                if (timeDiff <= ranges['3months']) stats['3months']++;
                if (timeDiff <= ranges['1year']) stats['1year']++;
            }
        });
        
        return stats;
    }
    
    /**
     * 计算路径在不同时间范围内的故障统计
     * @param {string} siteAName - A端站点名称
     * @param {string} siteZName - Z端站点名称
     * @returns {Object} 各时间范围的故障次数
     */
    calculatePathTimeStats(siteAName, siteZName) {
        // 使用原始的一年内所有故障数据，不受时间范围筛选影响
        const markerData = (window.OTNFaultMapConfig && window.OTNFaultMapConfig.markerData) || [];
        // 使用DEBUG模式的时间或当前时间
        const now = window.OTN_DEBUG_MODE ? new Date(window.OTN_DEBUG_DATE) : new Date();
        
        // 时间范围定义（毫秒）
        const ranges = {
            '1week': 7 * 24 * 60 * 60 * 1000,
            '2weeks': 14 * 24 * 60 * 60 * 1000,
            '1month': 30 * 24 * 60 * 60 * 1000,
            '3months': 90 * 24 * 60 * 60 * 1000,
            '1year': 365 * 24 * 60 * 60 * 1000
        };
        
        const stats = { '1week': 0, '2weeks': 0, '1month': 0, '3months': 0, '1year': 0 };
        
        markerData.forEach(m => {
            // 路径统计：光缆故障且匹配站点对（双向匹配）
            if (m.category === 'fiber' && m.a_site && m.z_sites && m.occurrence_time) {
                const matchAZ = (m.a_site === siteAName && m.z_sites === siteZName);
                const matchZA = (m.a_site === siteZName && m.z_sites === siteAName);
                
                if (matchAZ || matchZA) {
                    const occTime = new Date(m.occurrence_time);
                    const timeDiff = now - occTime;
                    
                    // 累积统计各时间范围
                    if (timeDiff <= ranges['1week']) stats['1week']++;
                    if (timeDiff <= ranges['2weeks']) stats['2weeks']++;
                    if (timeDiff <= ranges['1month']) stats['1month']++;
                    if (timeDiff <= ranges['3months']) stats['3months']++;
                    if (timeDiff <= ranges['1year']) stats['1year']++;
                }
            }
        });
        
        return stats;
    }
    
    /**
     * 计算站点月度故障统计（最近12个月）
     * @param {string} siteName - 站点名称
     * @returns {Array} 每月故障数量数组
     */
    calculateSiteMonthlyStats(siteName) {
        const markerData = (window.OTNFaultMapConfig && window.OTNFaultMapConfig.markerData) || [];
        // 使用DEBUG模式的时间或当前时间
        const now = window.OTN_DEBUG_MODE ? new Date(window.OTN_DEBUG_DATE) : new Date();
        
        // 初始化最近12个月的统计
        const monthlyStats = [];
        for (let i = 11; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            monthlyStats.push({
                year: d.getFullYear(),
                month: d.getMonth() + 1,
                label: `${String(d.getFullYear()).slice(-2)}.${d.getMonth() + 1}`,
                count: 0
            });
        }
        
        markerData.forEach(m => {
            const hasZSites = m.z_site_ids && m.z_site_ids.length > 0;
            if (m.a_site === siteName && !hasZSites && m.occurrence_time) {
                const occTime = new Date(m.occurrence_time);
                const occYear = occTime.getFullYear();
                const occMonth = occTime.getMonth() + 1;
                
                // 找到对应的月份
                const match = monthlyStats.find(s => s.year === occYear && s.month === occMonth);
                if (match) match.count++;
            }
        });
        
        return monthlyStats;
    }
    
    /**
     * 计算路径月度故障统计（最近12个月）
     * @param {string} siteAName - A端站点名称
     * @param {string} siteZName - Z端站点名称
     * @returns {Array} 每月故障数量数组
     */
    calculatePathMonthlyStats(siteAName, siteZName) {
        const markerData = (window.OTNFaultMapConfig && window.OTNFaultMapConfig.markerData) || [];
        // 使用DEBUG模式的时间或当前时间
        const now = window.OTN_DEBUG_MODE ? new Date(window.OTN_DEBUG_DATE) : new Date();
        
        // 初始化最近12个月的统计
        const monthlyStats = [];
        for (let i = 11; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            monthlyStats.push({
                year: d.getFullYear(),
                month: d.getMonth() + 1,
                label: `${String(d.getFullYear()).slice(-2)}.${d.getMonth() + 1}`,
                count: 0
            });
        }
        
        markerData.forEach(m => {
            if (m.category === 'fiber' && m.a_site && m.z_sites && m.occurrence_time) {
                const matchAZ = (m.a_site === siteAName && m.z_sites === siteZName);
                const matchZA = (m.a_site === siteZName && m.z_sites === siteAName);
                
                if (matchAZ || matchZA) {
                    const occTime = new Date(m.occurrence_time);
                    const occYear = occTime.getFullYear();
                    const occMonth = occTime.getMonth() + 1;
                    
                    const match = monthlyStats.find(s => s.year === occYear && s.month === occMonth);
                    if (match) match.count++;
                }
            }
        });
        
        return monthlyStats;
    }
    
    /**
     * 渲染SVG折线图
     * @param {Array} monthlyStats - 月度统计数据
     * @returns {string} SVG HTML 片段
     */
    renderLineChart(monthlyStats) {
        const width = 260;
        const height = 65;  // 紧凑高度
        const padding = { top: 5, right: 5, bottom: 15, left: 22 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;
        
        const counts = monthlyStats.map(s => s.count);
        const maxCount = Math.max(...counts, 1); // 至少为1，避免除零
        
        // 计算点的位置
        const points = monthlyStats.map((s, i) => {
            const x = padding.left + (i / (monthlyStats.length - 1)) * chartWidth;
            const y = padding.top + chartHeight - (s.count / maxCount) * chartHeight;
            return { x, y, count: s.count, label: s.label, year: s.year, month: s.month };
        });
        
        // 生成折线路径
        const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
        
        // 生成填充区域路径
        const areaPath = `${linePath} L ${points[points.length-1].x.toFixed(1)} ${height - padding.bottom} L ${padding.left} ${height - padding.bottom} Z`;
        
        // 生成数据点（使用g元素包裹circle和title以修复tooltip）
        const pointsHtml = points.map(p => {
            const tooltipText = `${String(p.year).slice(-2)}年${p.month}月，${p.count}次故障`;
            return `
            <g class="chart-point">
                <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3" fill="#0097a7" stroke="#fff" stroke-width="1">
                    <title>${tooltipText}</title>
                </circle>
            </g>
        `;
        }).join('');
        
        // X轴标签：单行显示；只在1月份显示年份
        const xLabelsHtml = monthlyStats.map((s, i) => {
            const x = padding.left + (i / (monthlyStats.length - 1)) * chartWidth;
            const y = height - 3;
            // 只在1月份时显示年份前缀，其他月份只显示月份数字
            const displayLabel = s.month === 1 ? s.label : String(s.month);
            return `<text x="${x.toFixed(1)}" y="${y}" font-size="7" fill="#6c757d" text-anchor="middle">${displayLabel}</text>`;
        }).join('');
        
        return `
            <div class="stats-chart-section">
                <div class="stats-chart-title">月度故障趋势</div>
                <svg width="${width}" height="${height}" class="stats-line-chart">
                    <!-- 填充区域 -->
                    <path d="${areaPath}" fill="rgba(0, 151, 167, 0.1)" />
                    <!-- 折线 -->
                    <path d="${linePath}" fill="none" stroke="#0097a7" stroke-width="1.5" />
                    <!-- 数据点 -->
                    ${pointsHtml}
                    <!-- Y轴最大值标签 -->
                    <text x="${padding.left - 3}" y="${padding.top + 3}" font-size="8" fill="#6c757d" text-anchor="end">${maxCount}</text>
                    <text x="${padding.left - 3}" y="${height - padding.bottom}" font-size="8" fill="#6c757d" text-anchor="end">0</text>
                    <!-- X轴标签 -->
                    ${xLabelsHtml}
                </svg>
            </div>
        `;
    }
    
    /**
     * 生成故障统计HTML片段（含折线图）
     * @param {Object} stats - 统计数据
     * @param {string} label - 标签（"此站点" 或 "此线路"）
     * @param {Array} monthlyStats - 月度统计数据
     * @returns {string} HTML 片段
     */
    renderTimeStatsHtml(stats, label, monthlyStats) {
        const items = [
            { key: '1week', text: '1周内' },
            { key: '2weeks', text: '2周内' },
            { key: '1month', text: '1月内' },
            { key: '3months', text: '3月内' },
            { key: '1year', text: '1年内' }
        ];
        
        const chartHtml = monthlyStats ? this.renderLineChart(monthlyStats) : '';
        
        return `
            <div class="stats-time-section">
                <div class="stats-time-title">${label}历史故障统计</div>
                <div class="stats-time-grid">
                    ${items.map(item => `
                        <div class="stats-time-item">
                            <span class="stats-time-label">${item.text}</span>
                            <span class="stats-time-value">${stats[item.key]}</span>
                            <span class="stats-time-unit">次</span>
                        </div>
                    `).join('')}
                </div>
                ${chartHtml}
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
            
            // 构建故障列表详情链接（使用 single_site_a_id 筛选：A端站点为此站点且Z端为空）
            const faultListUrl = window.OTNFaultMapConfig.faultListUrl || '/plugins/netbox_otnfaults/faults/';
            const detailUrl = `${faultListUrl}?single_site_a_id=${target.id}`;
            
            // 计算此站点的历史故障统计
            const timeStats = this.calculateSiteTimeStats(siteName);
            const monthlyStats = this.calculateSiteMonthlyStats(siteName);
            const timeStatsHtml = this.renderTimeStatsHtml(timeStats, '此站点', monthlyStats);
            
            // 触发美化的弹窗
            this.currentPopup = new maplibregl.Popup({ maxWidth: '300px', className: 'stats-popup' })
                    .setLngLat([target.longitude, target.latitude])
                    .setHTML(`
                        <div class="stats-popup-content">
                            <div class="stats-popup-header">
                                <div class="stats-popup-title">
                                    <i class="mdi mdi-map-marker"></i>
                                    <span>${target.name}</span>
                                </div>
                                <a href="${detailUrl}" class="stats-popup-link" target="_blank" title="查看详情">
                                    <i class="mdi mdi-open-in-new"></i>
                                </a>
                            </div>
                            <div class="stats-popup-body">
                                <span class="stats-tag stats-tag-warning">故障高发站点</span>
                                <span class="stats-tag-sub">非线路故障</span>
                            </div>
                            ${timeStatsHtml}
                        </div>
                        <style>
                            .stats-popup .maplibregl-popup-content { padding: 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
                            .stats-popup-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; padding-right: 28px; background: #f8f9fa; border-bottom: 1px solid #e9ecef; }
                            .stats-popup-title { display: flex; align-items: center; gap: 6px; font-weight: 600; font-size: 13px; color: #212529; }
                            .stats-popup-title i { color: #0d6efd; font-size: 16px; }
                            .stats-popup-link { display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; color: #6c757d; border-radius: 4px; transition: all 0.15s; }
                            .stats-popup-link:hover { background: #e9ecef; color: #0d6efd; }
                            .stats-popup-link i { font-size: 14px; }
                            .stats-popup-body { padding: 8px 10px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #e9ecef; }
                            .stats-tag { font-size: 11px; padding: 2px 6px; border-radius: 3px; font-weight: 500; }
                            .stats-tag-warning { background: #fff3cd; color: #856404; }
                            .stats-tag-sub { font-size: 11px; color: #6c757d; }
                            .stats-time-section { padding: 8px 10px; }
                            .stats-time-title { font-size: 11px; font-weight: 600; color: #495057; margin-bottom: 6px; }
                            .stats-time-grid { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-bottom: 8px; }
                            .stats-time-item { display: flex; align-items: center; gap: 2px; font-size: 11px; color: #6c757d; }
                            .stats-time-label { color: #6c757d; }
                            .stats-time-value { font-weight: 700; color: #0097a7; font-size: 12px; }
                            .stats-time-unit { color: #6c757d; }
                            .stats-chart-section { padding: 0 10px 8px 10px; }
                            .stats-chart-title { font-size: 10px; color: #6c757d; margin-bottom: 4px; }
                            .stats-line-chart { display: block; }
                        </style>
                    `)
                    .addTo(this.map);
             
             // Cleanup on close
             this.currentPopup.on('close', () => {
                 this.currentPopup = null;
             });
        }
    }
    
    // 定位到路径
    // pathItemKey 是 "A <-> Z" 字符串（站点名称），需要：
    // 1. 根据站点名称获取站点ID
    // 2. 用站点ID在光缆路径模型中匹配（考虑AZ与ZA双向）
    // 3. fly to并高亮路径
    // 4. 弹窗中提供详情链接（使用bidirectional_pair筛选器）
    flyToPath(pathName) {
        console.log('[flyToPath] 开始定位路径:', pathName);
        
        // 解析 A 和 Z 站点名称
        const parts = pathName.split(' <-> ');
        if (parts.length !== 2) {
            console.warn('[flyToPath] 路径名称格式错误:', pathName);
            return;
        }
        const siteAName = parts[0].trim();
        const siteZName = parts[1].trim();
        console.log('[flyToPath] 解析的站点名称: A端=', siteAName, ', Z端=', siteZName);
        
        // 获取站点数据
        const sites = window.OTNFaultMapConfig.sitesData || [];
        const paths = window.OTNPathsMetadata || [];
        
        // 根据站点名称查找站点对象（获取ID）
        const siteAObj = sites.find(s => s.name === siteAName);
        const siteZObj = sites.find(s => s.name === siteZName);
        
        console.log('[flyToPath] 站点查找结果:',
            'A端:', siteAObj ? `${siteAObj.name}(id=${siteAObj.id})` : '未找到',
            'Z端:', siteZObj ? `${siteZObj.name}(id=${siteZObj.id})` : '未找到'
        );
        
        if (!siteAObj || !siteZObj) {
            console.warn('[flyToPath] 无法找到站点对象，无法匹配路径');
            return;
        }
        
        // 在光缆路径模型中匹配（使用站点名称，考虑AZ与ZA双向）
        // 路径模型中的a_site和z_site是站点名称
        const targetPath = paths.find(p => {
            const props = p.properties;
            if (!props.a_site || !props.z_site) return false;
            
            // 双向匹配：A-Z 或 Z-A
            const match = (props.a_site === siteAName && props.z_site === siteZName) ||
                          (props.a_site === siteZName && props.z_site === siteAName);
            return match;
        });
        
        // 清理已有弹窗
        const existingPopups = document.getElementsByClassName('maplibregl-popup');
        while (existingPopups.length > 0) {
            existingPopups[0].remove();
        }
        if (this.currentPopup) {
            this.currentPopup.remove();
            this.currentPopup = null;
        }

        // 构建故障列表详情链接（使用bidirectional_pair筛选器，自动处理AZ与ZA双向）
        const faultListUrl = window.OTNFaultMapConfig.faultListUrl || '/plugins/netbox_otnfaults/faults/';
        const detailUrl = `${faultListUrl}?bidirectional_pair=${siteAObj.id},${siteZObj.id}`;
        
        // 计算此线路的历史故障统计
        const timeStats = this.calculatePathTimeStats(siteAName, siteZName);
        const monthlyStats = this.calculatePathMonthlyStats(siteAName, siteZName);
        const timeStatsHtml = this.renderTimeStatsHtml(timeStats, '此线路', monthlyStats);
        
        if (!targetPath) {
            // 未找到匹配的光缆路径，使用站点坐标定位
            console.warn('[flyToPath] 未在光缆路径模型中找到匹配的路径，使用站点坐标定位');
            console.log('[flyToPath] 尝试匹配的站点对:', siteAName, '<->', siteZName);
            
            // 计算两个站点的中心点
            const centerLng = (siteAObj.longitude + siteZObj.longitude) / 2;
            const centerLat = (siteAObj.latitude + siteZObj.latitude) / 2;
            
            // fly to中心点
            this.map.flyTo({
                center: [centerLng, centerLat],
                zoom: 8,
                speed: 2.5
            });
            
            // 显示弹窗（标注无对应光缆路径）
            this.currentPopup = new maplibregl.Popup({ maxWidth: '300px', className: 'stats-popup' })
                    .setLngLat([centerLng, centerLat])
                    .setHTML(`
                        <div class="stats-popup-content">
                            <div class="stats-popup-header">
                                <div class="stats-popup-title">
                                    <i class="mdi mdi-transit-connection-variant" style="color: #dc3545;"></i>
                                    <span>故障路径</span>
                                </div>
                                <a href="${detailUrl}" class="stats-popup-link" target="_blank" title="查看详情">
                                    <i class="mdi mdi-open-in-new"></i>
                                </a>
                            </div>
                            <div class="stats-popup-body">
                                <div class="stats-popup-sites">
                                    <span><i class="mdi mdi-alpha-a-circle-outline"></i> ${siteAName}</span>
                                    <span class="stats-popup-arrow">→</span>
                                    <span><i class="mdi mdi-alpha-z-circle-outline"></i> ${siteZName}</span>
                                </div>
                                <span class="stats-tag stats-tag-warning">无对应光缆路径</span>
                            </div>
                            ${timeStatsHtml}
                        </div>
                        <style>
                            .stats-popup .maplibregl-popup-content { padding: 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
                            .stats-popup-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; padding-right: 28px; background: #f8f9fa; border-bottom: 1px solid #e9ecef; }
                            .stats-popup-title { display: flex; align-items: center; gap: 6px; font-weight: 600; font-size: 13px; color: #212529; }
                            .stats-popup-title i { font-size: 16px; }
                            .stats-popup-link { display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; color: #6c757d; border-radius: 4px; transition: all 0.15s; }
                            .stats-popup-link:hover { background: #e9ecef; color: #0d6efd; }
                            .stats-popup-link i { font-size: 14px; }
                            .stats-popup-body { padding: 8px 10px; border-bottom: 1px solid #e9ecef; }
                            .stats-popup-sites { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #495057; margin-bottom: 6px; flex-wrap: wrap; }
                            .stats-popup-sites i { color: #0d6efd; font-size: 14px; }
                            .stats-popup-arrow { color: #adb5bd; }
                            .stats-tag { font-size: 11px; padding: 2px 6px; border-radius: 3px; font-weight: 500; }
                            .stats-tag-warning { background: #fff3cd; color: #856404; }
                            .stats-time-section { padding: 8px 10px; }
                            .stats-time-title { font-size: 11px; font-weight: 600; color: #495057; margin-bottom: 6px; }
                            .stats-time-grid { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-bottom: 8px; }
                            .stats-time-item { display: flex; align-items: center; gap: 2px; font-size: 11px; color: #6c757d; }
                            .stats-time-label { color: #6c757d; }
                            .stats-time-value { font-weight: 700; color: #0097a7; font-size: 12px; }
                            .stats-time-unit { color: #6c757d; }
                            .stats-chart-section { padding: 0 10px 8px 10px; }
                            .stats-chart-title { font-size: 10px; color: #6c757d; margin-bottom: 4px; }
                            .stats-line-chart { display: block; }
                        </style>
                    `)
                    .addTo(this.map);
             
            this.currentPopup.on('close', () => {
                this.currentPopup = null;
            });
            return;
        }
        
        console.log('[flyToPath] 匹配成功，路径:', targetPath.properties.name);

        // 计算路径边界并fly to
        const coords = targetPath.geometry.coordinates;
        const bounds = new maplibregl.LngLatBounds();
        coords.forEach(c => bounds.extend(c));
        
        this.map.fitBounds(bounds, { padding: 100, speed: 2.5 });
        
        // 高亮路径
        if (this.map.getSource('otn-paths-highlight')) {
            this.map.getSource('otn-paths-highlight').setData(targetPath);
        }

        // 在路径中心显示弹窗
        const center = bounds.getCenter();
        
        this.currentPopup = new maplibregl.Popup({ maxWidth: '300px', className: 'stats-popup' })
                .setLngLat(center)
                .setHTML(`
                    <div class="stats-popup-content">
                        <div class="stats-popup-header">
                            <div class="stats-popup-title">
                                <i class="mdi mdi-vector-polyline" style="color: #198754;"></i>
                                <span>${targetPath.properties.name || '光缆路径'}</span>
                            </div>
                            <a href="${detailUrl}" class="stats-popup-link" target="_blank" title="查看详情">
                                <i class="mdi mdi-open-in-new"></i>
                            </a>
                        </div>
                        <div class="stats-popup-body">
                            <div class="stats-popup-sites">
                                <span><i class="mdi mdi-alpha-a-circle-outline"></i> ${siteAName}</span>
                                <span class="stats-popup-arrow">→</span>
                                <span><i class="mdi mdi-alpha-z-circle-outline"></i> ${siteZName}</span>
                            </div>
                            <span class="stats-tag stats-tag-danger">故障高发路径</span>
                        </div>
                        ${timeStatsHtml}
                    </div>
                    <style>
                        .stats-popup .maplibregl-popup-content { padding: 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
                        .stats-popup-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; padding-right: 28px; background: #f8f9fa; border-bottom: 1px solid #e9ecef; }
                        .stats-popup-title { display: flex; align-items: center; gap: 6px; font-weight: 600; font-size: 13px; color: #212529; }
                        .stats-popup-title i { font-size: 16px; }
                        .stats-popup-link { display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; color: #6c757d; border-radius: 4px; transition: all 0.15s; }
                        .stats-popup-link:hover { background: #e9ecef; color: #0d6efd; }
                        .stats-popup-link i { font-size: 14px; }
                        .stats-popup-body { padding: 8px 10px; border-bottom: 1px solid #e9ecef; }
                        .stats-popup-sites { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #495057; margin-bottom: 6px; flex-wrap: wrap; }
                        .stats-popup-sites i { color: #0d6efd; font-size: 14px; }
                        .stats-popup-arrow { color: #adb5bd; }
                        .stats-tag { font-size: 11px; padding: 2px 6px; border-radius: 3px; font-weight: 500; }
                        .stats-tag-danger { background: #f8d7da; color: #721c24; }
                        .stats-time-section { padding: 8px 10px; }
                        .stats-time-title { font-size: 11px; font-weight: 600; color: #495057; margin-bottom: 6px; }
                        .stats-time-grid { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-bottom: 8px; }
                        .stats-time-item { display: flex; align-items: center; gap: 2px; font-size: 11px; color: #6c757d; }
                        .stats-time-label { color: #6c757d; }
                        .stats-time-value { font-weight: 700; color: #0097a7; font-size: 12px; }
                        .stats-time-unit { color: #6c757d; }
                        .stats-chart-section { padding: 0 10px 8px 10px; }
                        .stats-chart-title { font-size: 10px; color: #6c757d; margin-bottom: 4px; }
                        .stats-line-chart { display: block; }
                    </style>
                `)
                .addTo(this.map);
         
        this.currentPopup.on('close', () => {
            this.currentPopup = null;
        });
    }
}

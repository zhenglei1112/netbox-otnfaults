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
    this.container = document.createElement("div");
    this.container.className = "maplibregl-ctrl fault-statistics";

    // 初始渲染
    this.renderContent();

    // 阻止地图事件传播
    ["mousedown", "click", "dblclick", "touchstart"].forEach((event) => {
      this.container.addEventListener(event, (e) => e.stopPropagation());
    });

    return this.container;
  }

  // 渲染最小化按钮状态
  renderVisibility() {
    const contentDiv = this.container.querySelector(".stats-content");
    const headerIcon = this.container.querySelector(".toggle-icon");

    if (this.minimized) {
      if (contentDiv) contentDiv.style.display = "none";
      if (headerIcon) headerIcon.className = "mdi mdi-chevron-up toggle-icon";
    } else {
      if (contentDiv) contentDiv.style.display = "block";
      if (headerIcon) headerIcon.className = "mdi mdi-chevron-down toggle-icon";
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
    this._cachedStats = null; // 清除缓存，强制重新计算
    this.update();
  }

  // ========== 公共工具方法 ==========

  /**
   * 将 Z 端站点字符串拆分为数组
   * @param {string} zSitesStr - Z端站点字符串，可能用"、"分隔
   * @returns {string[]} 站点名称数组
   */
  splitZSites(zSitesStr) {
    if (!zSitesStr || typeof zSitesStr !== "string") return [];
    return zSitesStr
      .split("、")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  }

  /**
   * 检查故障是否匹配指定的路径（双向匹配）
   * @param {string} faultASite - 故障的A端站点名称
   * @param {string} faultZSites - 故障的Z端站点字符串（可能包含多个用"、"分隔）
   * @param {string} targetASite - 目标A端站点名称
   * @param {string} targetZSite - 目标Z端站点名称（单个）
   * @returns {boolean} 是否匹配
   */
  matchesPath(faultASite, faultZSites, targetASite, targetZSite) {
    if (!faultASite || !faultZSites) return false;
    const zSitesList = this.splitZSites(faultZSites);
    // 双向匹配：A匹配且Z包含目标，或者反向匹配
    return (
      (faultASite === targetASite && zSitesList.includes(targetZSite)) ||
      (faultASite === targetZSite && zSitesList.includes(targetASite))
    );
  }

  // 计算统计数据 (带缓存)
  calculateStats() {
    // 如果已有缓存结果直接返回，避免重复计算
    if (this._cachedStats) {
      return this._cachedStats;
    }
    // 使用显式设置的数据列表进行统计
    this._cachedStats = this.calculateStatsFromList(this.faultDataList || []);
    return this._cachedStats;
  }

  calculateStatsFromList(faults) {
    let totalFaults = faults.length;
    let totalDurationHours = 0;
    let validDurationCount = 0;
    const siteCounts = {};
    const pathCounts = {};
    const businessCounts = {};
    const provinceCounts = {}; // 新增：省份统计

    faults.forEach((f) => {
      // 统计站点（只统计A端有值且Z端为空的故障）
      const hasZSites = f.z_site_ids && f.z_site_ids.length > 0;
      if (f.a_site && !hasZSites) {
        siteCounts[f.a_site] = (siteCounts[f.a_site] || 0) + 1;
      }

      // 统计路径（仅统计光缆故障且A、Z端都有值的故障）
      if (f.a_site && f.z_sites && f.category === "fiber") {
        const siteA = f.a_site;
        const zSitesList = this.splitZSites(f.z_sites);

        zSitesList.forEach((siteZ) => {
          const [site1, site2] =
            siteA < siteZ ? [siteA, siteZ] : [siteZ, siteA];
          const normalizedKey = `${site1} <-> ${site2}`;

          if (!pathCounts[normalizedKey]) {
            pathCounts[normalizedKey] = {
              count: 0,
              a_site: site1,
              z_site: site2,
              displayName: normalizedKey,
            };
          }
          pathCounts[normalizedKey].count++;
        });
      }

      // 新增：统计影响业务
      // in FaultDataService.js, it maps m.impacted_business -> properties.impactedBusiness
      const impactedBusinessStr = f.impactedBusiness || f.impacted_business; // 兼容驼峰和蛇形

      if (impactedBusinessStr && typeof impactedBusinessStr === 'string') {
        const businesses = impactedBusinessStr.split('、');
        businesses.forEach(b => {
          const name = b.trim();
          // 过滤无效值和默认占位符
          if (name && name !== '无重保/影响业务') {
            businessCounts[name] = (businessCounts[name] || 0) + 1;
          }
        });
      }

      // 新增：统计省份
      const province = f.province || (f.raw && f.raw.province);
      if (province && province !== '未指定') {
        provinceCounts[province] = (provinceCounts[province] || 0) + 1;
      }

      // 统计时长
      if (f.occurrence_time) {
        const start = new Date(f.occurrence_time);
        const recoveryTime =
          f.raw && f.raw.recovery_time ? f.raw.recovery_time : null;

        const now = window.OTN_DEBUG_MODE
          ? new Date(window.OTN_DEBUG_DATE)
          : new Date();

        const end = recoveryTime ? new Date(recoveryTime) : now;
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

    // 影响业务统计 (全部显示，按次数排序)
    const impactedBusinesses = Object.entries(businessCounts)
      .sort((a, b) => b[1] - a[1]);

    // 省份统计 (全部显示，按次数排序)
    const provinceStats = Object.entries(provinceCounts)
      .sort((a, b) => b[1] - a[1]);

    const avgDuration =
      validDurationCount > 0
        ? (totalDurationHours / validDurationCount).toFixed(1)
        : 0;

    return {
      total: totalFaults,
      avgDuration,
      topSites,
      topPaths,
      impactedBusinesses,
      provinceStats, // 新增返回
    };
  }

  renderContent() {
    const stats = this.calculateStats();
    const layerToggle = window.layerToggleControl;
    const categoryFilter = window.categoryFilterControl;

    // 获取当前筛选状态文本
    let timeRangeText = "最近1周";
    if (layerToggle) {
      const texts = {
        "1week": "最近1周",
        "2weeks": "最近2周",
        "1month": "最近1月",
        "3months": "最近3月",
        "1year": "最近1年",
      };
      timeRangeText =
        texts[layerToggle.currentTimeRange] || layerToggle.currentTimeRange;
    }

    let categoryText = "全部类型";
    if (categoryFilter) {
      const count = categoryFilter.selectedCategories.length;
      const total = Object.keys(FAULT_CATEGORY_COLORS).length;
      if (count === total) {
        categoryText = "全部类型";
      } else if (count === 0) {
        categoryText = "无类型";
      } else {
        const names = categoryFilter.selectedCategories.map(
          (cat) => FAULT_CATEGORY_NAMES[cat] || cat
        );
        categoryText = names.join("、");
      }
    }

    // 初始图标根据 minimized 状态设置
    const mainToggleIconClass = this.minimized
      ? "mdi mdi-chevron-up toggle-icon"
      : "mdi mdi-chevron-down toggle-icon";
    const contentDisplay = this.minimized ? "none" : "block";

    // 抽屉状态 (默认：业务展开，Top5折叠)
    // 使用 dataset 或内存状态维护，这里简单起见，如果尚未初始化状态，则默认初始化
    if (this.sectionStates === undefined) {
      this.sectionStates = {
        business: true, // true = open
        province: false,
        top5: false
      };
    }

    const businessDisplay = this.sectionStates.business ? 'block' : 'none';
    const businessIcon = this.sectionStates.business ? 'mdi mdi-chevron-down' : 'mdi mdi-chevron-right';

    const top5Display = this.sectionStates.top5 ? 'block' : 'none';
    const top5Icon = this.sectionStates.top5 ? 'mdi mdi-chevron-down' : 'mdi mdi-chevron-right';

    this.container.innerHTML = `
            <div class="card shadow-sm" style="width: 240px; opacity: 0.95;">
                <div class="card-header py-2 d-flex justify-content-between align-items-center bg-body-tertiary" 
                     style="cursor: pointer;" onclick="this.closest('.fault-statistics')._control.toggleMinimize(event)">
                    <span class="fw-bold mb-0" style="font-size: 14px;">故障统计</span>
                    <i class="${mainToggleIconClass}"></i>
                </div>
                <div class="card-header py-1 bg-body text-body-secondary" style="font-size: 11px; border-top: 1px solid var(--bs-border-color);">
                     <span>筛选: ${timeRangeText} · ${categoryText}</span>
                </div>
                <!-- 统计概览 -->
                <div class="stats-summary px-2 py-2 bg-body" style="font-size: 12px; border-top: 1px solid var(--bs-border-color);">
                    <span>故障数: </span><span class="fw-bold" style="color: var(--bs-link-color, #0097a7) !important;">${stats.total
      }</span>
                    <span class="mx-2 text-body-secondary">|</span>
                    <span>平均: </span><span class="fw-bold" style="color: var(--bs-link-color, #0097a7) !important;">${stats.avgDuration
      }小时</span>
                </div>
                
                <div class="card-body p-0 stats-content" style="display: ${contentDisplay}; border-top: 1px solid var(--bs-border-color);">
                    
                    <!-- 1. 影响业务统计 (抽屉) -->
                    <div class="stats-section">
                        <div class="d-flex justify-content-between align-items-center px-2 py-1 bg-light border-bottom" 
                             style="cursor: pointer; font-size: 12px;"
                             onclick="window.faultStatisticsControl.toggleSection('business', this)">
                            <span class="fw-bold text-secondary">影响业务统计</span>
                            <i class="${businessIcon}"></i>
                        </div>
                        <div class="section-content px-2 ${this.sectionStates.business ? 'expanded' : 'collapsed'}" 
                             style="font-size: 12px; max-height: ${this.sectionStates.business ? '200px' : '0'}; overflow-y: auto;">
                            ${this.renderBusinessList(stats.impactedBusinesses)}
                        </div>
                    </div>

                    <!-- 2. 省份统计 (抽屉) -->
                    <div class="stats-section border-top">
                        <div class="d-flex justify-content-between align-items-center px-2 py-1 bg-light border-bottom" 
                             style="cursor: pointer; font-size: 12px;"
                             onclick="window.faultStatisticsControl.toggleSection('province', this)">
                            <span class="fw-bold text-secondary">省份统计</span>
                            <i class="${this.sectionStates.province ? 'mdi mdi-chevron-down' : 'mdi mdi-chevron-right'}"></i>
                        </div>
                        <div class="section-content px-2 ${this.sectionStates.province ? 'expanded' : 'collapsed'}" 
                             style="font-size: 12px; max-height: ${this.sectionStates.province ? '200px' : '0'}; overflow-y: auto;">
                            ${this.renderBusinessList(stats.provinceStats)}
                        </div>
                    </div>

                    <!-- 3. Top 5 故障统计 (抽屉) -->
                     <div class="stats-section border-top">
                        <div class="d-flex justify-content-between align-items-center px-2 py-1 bg-light border-bottom" 
                             style="cursor: pointer; font-size: 12px;"
                             onclick="window.faultStatisticsControl.toggleSection('top5', this)">
                            <span class="fw-bold text-secondary">Top 5 故障统计</span>
                            <i class="${top5Icon}"></i>
                        </div>
                        <div class="section-content px-2 ${this.sectionStates.top5 ? 'expanded' : 'collapsed'}" 
                             style="max-height: ${this.sectionStates.top5 ? '500px' : '0'};">
                             ${this.createSection(
        "Top 5 故障站点",
        stats.topSites,
        "site"
      )}
                             ${this.createSection(
        "Top 5 故障路径",
        stats.topPaths,
        "path"
      )}
                        </div>
                    </div>

                </div>
            </div>
        `;

    // 绑定实例以便 onclick 访问
    this.container._control = this;

    // 绑定业务项悬停事件
    this._bindBusinessHighlightEvents();
  }

  toggleMinimize(e) {
    e.stopPropagation();
    this.minimized = !this.minimized;
    this.renderVisibility();
  }

  toggleSection(sectionKey, headerEl) {
    const isCurrentlyOpen = this.sectionStates[sectionKey];

    // 手风琴效果：展开当前区域时关闭其他区域
    if (!isCurrentlyOpen) {
      // 关闭所有其他区域
      Object.keys(this.sectionStates).forEach(key => {
        if (key !== sectionKey && this.sectionStates[key]) {
          this.sectionStates[key] = false;
        }
      });
    }

    // 切换当前区域状态
    this.sectionStates[sectionKey] = !isCurrentlyOpen;

    // 更新所有区域的 UI (重新渲染整个内容以确保同步)
    this.renderContent();
    this.renderVisibility(); // 保持折叠状态
  }

  renderBusinessList(items) {
    if (!items || items.length === 0) {
      return '<div class="text-muted text-center py-1">无影响业务记录</div>';
    }

    // Calculate max value for the progress bar
    let maxVal = 0;
    if (items.length > 0) {
      maxVal = items[0][1];
    }

    // items 是 [name, count] 数组
    return items.map(([name, count], index) => {
      const percent = maxVal > 0 ? (count / maxVal) * 100 : 0;
      const safeName = name.replace(/'/g, "\\'");

      return `
          <div class="mb-2 clickable-stat-row business-highlight-item" 
               title="${name}"
               data-business-name="${safeName}"
               style="cursor: default;">
              <div class="d-flex justify-content-between align-items-center mb-1" style="font-size: 12px;">
                  <div class="text-truncate me-2 text-body-secondary" style="max-width: 180px;">${index + 1
        }. ${name}</div>
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
  }

  createSection(title, items, type) {
    if (items.length === 0) return "";

    // Calculate max value for the progress bar explicitly
    let maxVal = 0;
    if (items.length > 0) {
      if (type === "site") {
        maxVal = items[0][1];
      } else {
        maxVal = items[0][1].count;
      }
    }

    const rows = items
      .map((item, index) => {
        const name = item[0];
        let count = 0;

        if (type === "site") {
          count = item[1];
        } else {
          count = item[1].count;
        }

        const percent = maxVal > 0 ? (count / maxVal) * 100 : 0;
        const func = type === "site" ? "flyToSite" : "flyToPath";

        // 安全处理名称中的引号
        const safeName = name.replace(/'/g, "\\'");

        return `
                <div class="mb-2 clickable-stat-row hover-highlight-item" 
                     title="点击定位，悬停高亮"
                     style="cursor: pointer;"
                     data-highlight-type="${type}"
                     data-highlight-name="${safeName}"
                     onclick="window.faultStatisticsControl.${func}('${safeName}')">
                    <div class="d-flex justify-content-between align-items-center mb-1" style="font-size: 12px;">
                        <div class="text-truncate me-2 text-body-secondary" style="max-width: 180px;">${index + 1
          }. ${name}</div>
                        <span class="fw-bold" style="color: var(--bs-link-color, #0097a7) !important;">${count}</span>
                    </div>
                    <div class="progress" style="height: 4px; background-color: #e9ecef;">
                         <div class="progress-bar" role="progressbar" 
                              style="width: ${percent}%; background-color: var(--bs-link-color, #0097a7);">
                         </div>
                    </div>
                </div>
            `;
      })
      .join("");

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
    const markerData =
      (window.OTNFaultMapConfig && window.OTNFaultMapConfig.markerData) || [];
    // 使用DEBUG模式的时间或当前时间
    const now = window.OTN_DEBUG_MODE
      ? new Date(window.OTN_DEBUG_DATE)
      : new Date();

    // 时间范围定义（毫秒）
    const ranges = {
      "1week": 7 * 24 * 60 * 60 * 1000,
      "2weeks": 14 * 24 * 60 * 60 * 1000,
      "1month": 30 * 24 * 60 * 60 * 1000,
      "3months": 90 * 24 * 60 * 60 * 1000,
      "1year": 365 * 24 * 60 * 60 * 1000,
    };

    const stats = {
      "1week": 0,
      "2weeks": 0,
      "1month": 0,
      "3months": 0,
      "1year": 0,
    };

    markerData.forEach((m) => {
      // 站点统计：A端站点匹配且Z端为空
      const hasZSites = m.z_site_ids && m.z_site_ids.length > 0;
      if (m.a_site === siteName && !hasZSites && m.occurrence_time) {
        const occTime = new Date(m.occurrence_time);
        const timeDiff = now - occTime;

        // 累积统计各时间范围
        if (timeDiff <= ranges["1week"]) stats["1week"]++;
        if (timeDiff <= ranges["2weeks"]) stats["2weeks"]++;
        if (timeDiff <= ranges["1month"]) stats["1month"]++;
        if (timeDiff <= ranges["3months"]) stats["3months"]++;
        if (timeDiff <= ranges["1year"]) stats["1year"]++;
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
    const markerData =
      (window.OTNFaultMapConfig && window.OTNFaultMapConfig.markerData) || [];
    // 使用DEBUG模式的时间或当前时间
    const now = window.OTN_DEBUG_MODE
      ? new Date(window.OTN_DEBUG_DATE)
      : new Date();

    // 时间范围定义（毫秒）
    const ranges = {
      "1week": 7 * 24 * 60 * 60 * 1000,
      "2weeks": 14 * 24 * 60 * 60 * 1000,
      "1month": 30 * 24 * 60 * 60 * 1000,
      "3months": 90 * 24 * 60 * 60 * 1000,
      "1year": 365 * 24 * 60 * 60 * 1000,
    };

    const stats = {
      "1week": 0,
      "2weeks": 0,
      "1month": 0,
      "3months": 0,
      "1year": 0,
    };

    markerData.forEach((m) => {
      // 路径统计：光缆故障且匹配站点对（双向匹配）
      if (
        m.category === "fiber" &&
        m.occurrence_time &&
        this.matchesPath(m.a_site, m.z_sites, siteAName, siteZName)
      ) {
        const occTime = new Date(m.occurrence_time);
        const timeDiff = now - occTime;

        // 累积统计各时间范围
        if (timeDiff <= ranges["1week"]) stats["1week"]++;
        if (timeDiff <= ranges["2weeks"]) stats["2weeks"]++;
        if (timeDiff <= ranges["1month"]) stats["1month"]++;
        if (timeDiff <= ranges["3months"]) stats["3months"]++;
        if (timeDiff <= ranges["1year"]) stats["1year"]++;
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
    const markerData =
      (window.OTNFaultMapConfig && window.OTNFaultMapConfig.markerData) || [];
    // 使用DEBUG模式的时间或当前时间
    const now = window.OTN_DEBUG_MODE
      ? new Date(window.OTN_DEBUG_DATE)
      : new Date();

    // 初始化最近12个月的统计
    const monthlyStats = [];
    for (let i = 11; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      monthlyStats.push({
        year: d.getFullYear(),
        month: d.getMonth() + 1,
        label: `${String(d.getFullYear()).slice(-2)}.${d.getMonth() + 1}`,
        count: 0,
      });
    }

    markerData.forEach((m) => {
      const hasZSites = m.z_site_ids && m.z_site_ids.length > 0;
      if (m.a_site === siteName && !hasZSites && m.occurrence_time) {
        const occTime = new Date(m.occurrence_time);
        const occYear = occTime.getFullYear();
        const occMonth = occTime.getMonth() + 1;

        // 找到对应的月份
        const match = monthlyStats.find(
          (s) => s.year === occYear && s.month === occMonth
        );
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
    const markerData =
      (window.OTNFaultMapConfig && window.OTNFaultMapConfig.markerData) || [];
    // 使用DEBUG模式的时间或当前时间
    const now = window.OTN_DEBUG_MODE
      ? new Date(window.OTN_DEBUG_DATE)
      : new Date();

    // 初始化最近12个月的统计
    const monthlyStats = [];
    for (let i = 11; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      monthlyStats.push({
        year: d.getFullYear(),
        month: d.getMonth() + 1,
        label: `${String(d.getFullYear()).slice(-2)}.${d.getMonth() + 1}`,
        count: 0,
      });
    }

    markerData.forEach((m) => {
      // 路径统计：光缆故障且匹配站点对（双向匹配）
      if (
        m.category === "fiber" &&
        m.occurrence_time &&
        this.matchesPath(m.a_site, m.z_sites, siteAName, siteZName)
      ) {
        const occTime = new Date(m.occurrence_time);
        const occYear = occTime.getFullYear();
        const occMonth = occTime.getMonth() + 1;

        const match = monthlyStats.find(
          (s) => s.year === occYear && s.month === occMonth
        );
        if (match) match.count++;
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
    const height = 58; // 紧凑高度
    const padding = { top: 3, right: 3, bottom: 12, left: 18 }; // 减少空白
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    const counts = monthlyStats.map((s) => s.count);
    const maxCount = Math.max(...counts, 1); // 至少为1，避免除零

    // 计算点的位置
    const points = monthlyStats.map((s, i) => {
      const x = padding.left + (i / (monthlyStats.length - 1)) * chartWidth;
      const y = padding.top + chartHeight - (s.count / maxCount) * chartHeight;
      return {
        x,
        y,
        count: s.count,
        label: s.label,
        year: s.year,
        month: s.month,
      };
    });

    // 生成折线路径
    const linePath = points
      .map(
        (p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`
      )
      .join(" ");

    // 生成填充区域路径
    const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${height - padding.bottom
      } L ${padding.left} ${height - padding.bottom} Z`;

    // 生成数据点（使用g元素包裹circle和title以修复tooltip）
    const pointsHtml = points
      .map((p) => {
        const tooltipText = `${String(p.year).slice(-2)}年${p.month}月，${p.count
          }次故障`;
        return `
            <g class="chart-point">
                <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(
          1
        )}" r="3" fill="#0097a7" stroke="#fff" stroke-width="1">
                    <title>${tooltipText}</title>
                </circle>
            </g>
        `;
      })
      .join("");

    // X轴标签：单行显示；只在1月份显示年份
    const xLabelsHtml = monthlyStats
      .map((s, i) => {
        const x = padding.left + (i / (monthlyStats.length - 1)) * chartWidth;
        const y = height - 3;
        // 只在1月份时显示年份前缀，其他月份只显示月份数字
        const displayLabel = s.month === 1 ? s.label : String(s.month);
        return `<text x="${x.toFixed(
          1
        )}" y="${y}" font-size="7" fill="#6c757d" text-anchor="middle">${displayLabel}</text>`;
      })
      .join("");

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
                    <text x="${padding.left - 3}" y="${padding.top + 3
      }" font-size="8" fill="#6c757d" text-anchor="end">${maxCount}</text>
                    <text x="${padding.left - 3}" y="${height - padding.bottom
      }" font-size="8" fill="#6c757d" text-anchor="end">0</text>
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
   * @param {string} detailUrl - 可选，详情链接（用于查看详情按钮）
   * @returns {string} HTML 片段
   */
  renderTimeStatsHtml(stats, label, monthlyStats, detailUrl = null) {
    const items = [
      { key: "1week", text: "1周内" },
      { key: "1month", text: "1月内" },
      { key: "3months", text: "3月内" },
      { key: "1year", text: "1年内" },
    ];

    const chartHtml = monthlyStats ? this.renderLineChart(monthlyStats) : "";

    // 查看详情按钮（如果提供了 detailUrl）
    const detailLinkHtml = detailUrl
      ? `
            <a href="${detailUrl}" class="stats-popup-link" target="_blank" title="查看详情">
                <i class="mdi mdi-open-in-new"></i>
            </a>
        `
      : "";

    return `
            <div class="stats-time-section">
                <div class="stats-time-header">
                    <div class="stats-time-title">${label}历史故障统计</div>
                    ${detailLinkHtml}
                </div>
                <div class="stats-time-grid">
                    ${items
        .map(
          (item) => `
                        <div class="stats-time-item">
                            <span class="stats-time-label">${item.text}</span>
                            <span class="stats-time-value">${stats[item.key]
            }</span>
                            <span class="stats-time-unit">次</span>
                        </div>
                    `
        )
        .join("")}
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
    const target = sites.find((s) => s.name === siteName);

    if (target) {
      // Robustly remove ANY existing popups
      const existingPopups =
        document.getElementsByClassName("maplibregl-popup");
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
        speed: 2.5, // Adjusted speed
      });

      // 构建故障列表详情链接（使用 single_site_a_id 筛选：A端站点为此站点且Z端为空）
      const faultListUrl =
        window.OTNFaultMapConfig.faultListUrl ||
        "/plugins/netbox_otnfaults/faults/";
      const detailUrl = `${faultListUrl}?single_site_a_id=${target.id}`;

      // 计算此站点的历史故障统计
      const timeStats = this.calculateSiteTimeStats(siteName);
      const monthlyStats = this.calculateSiteMonthlyStats(siteName);
      const timeStatsHtml = this.renderTimeStatsHtml(
        timeStats,
        "此站点",
        monthlyStats,
        detailUrl
      );

      // 触发美化的弹窗（使用 PopupTemplates 生成内容，与地图点击弹窗保持一致）
      const siteUrl = target.url || "#"; // NetBox 站点对象链接
      const props = {
        region: target.region || "",
        status: target.status || "",
      };
      const popupContent = PopupTemplates.sitePopup({
        siteName: target.name,
        siteUrl,
        detailUrl,
        props,
        timeStatsHtml,
      });

      this.currentPopup = new maplibregl.Popup({
        maxWidth: "300px",
        className: "stats-popup",
      })
        .setLngLat([target.longitude, target.latitude])
        .setHTML(popupContent)
        .addTo(this.map);

      // Cleanup on close
      this.currentPopup.on("close", () => {
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
  // 4. 弹窗中提供详情链接（使用bidirectional_pair筛选器）
  async flyToPath(pathName) {
    // 确保路径元数据已加载
    if (
      (!window.OTNPathsMetadata || window.OTNPathsMetadata.length === 0) &&
      window.OTNPathsLoadingPromise
    ) {
      console.log("[flyToPath] 等待路径元数据加载...");
      await window.OTNPathsLoadingPromise;
    }

    console.log("[flyToPath] 开始定位路径:", pathName);

    // 解析 A 和 Z 站点名称
    const parts = pathName.split(" <-> ");
    if (parts.length !== 2) {
      console.warn("[flyToPath] 路径名称格式错误:", pathName);
      return;
    }
    const siteAName = parts[0].trim();
    const siteZNameRaw = parts[1].trim();

    // 处理一对多情况：Z端可能包含多个站点（用"、"分隔）
    const siteZNames = siteZNameRaw
      .split("、")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    console.log(
      "[flyToPath] 解析的站点名称: A端=",
      siteAName,
      ", Z端=",
      siteZNames
    );

    // 获取站点数据
    const sites = window.OTNFaultMapConfig.sitesData || [];
    const paths = window.OTNPathsMetadata || [];

    // 根据站点名称查找站点对象（获取ID）
    const siteAObj = sites.find((s) => s.name === siteAName);
    const siteZObjs = siteZNames
      .map((name) => sites.find((s) => s.name === name))
      .filter(Boolean);

    console.log(
      "[flyToPath] 站点查找结果:",
      "A端:",
      siteAObj ? `${siteAObj.name}(id=${siteAObj.id})` : "未找到",
      "Z端:",
      siteZObjs.length > 0
        ? siteZObjs.map((s) => `${s.name}(id=${s.id})`).join(", ")
        : "未找到"
    );

    // 检查站点是否包含"未指定"或坐标无效
    const hasUnspecifiedSite =
      siteAName === "未指定" || siteZNames.includes("未指定");
    const hasInvalidCoords =
      !siteAObj ||
      siteZObjs.length === 0 ||
      !siteAObj.longitude ||
      !siteAObj.latitude ||
      siteZObjs.some((s) => !s.longitude || !s.latitude);

    console.log(
      "[flyToPath] 站点状态:",
      "包含未指定站点:",
      hasUnspecifiedSite,
      "坐标无效:",
      hasInvalidCoords
    );

    // 在光缆路径模型中匹配（使用站点名称，考虑AZ与ZA双向）
    // 对于一对多情况，查找所有匹配的路径
    const matchedPaths = [];
    siteZNames.forEach((siteZName) => {
      const matchingPath = paths.find((p) => {
        const props = p.properties;
        if (!props.a_site || !props.z_site) return false;

        // 双向匹配：A-Z 或 Z-A
        const match =
          (props.a_site === siteAName && props.z_site === siteZName) ||
          (props.a_site === siteZName && props.z_site === siteAName);
        return match;
      });
      if (matchingPath) {
        matchedPaths.push(matchingPath);
      }
    });

    console.log("[flyToPath] 匹配到的路径数:", matchedPaths.length);

    // 如果站点对象都找不到且也没有匹配的路径，则无法定位
    if ((!siteAObj || siteZObjs.length === 0) && matchedPaths.length === 0) {
      console.warn("[flyToPath] 无法找到站点对象且无匹配路径，无法定位");
      return;
    }

    // 清理已有弹窗
    // FIX: 优先处理 fault_mode.js 创建的全局 popup，防止其 close 事件干扰
    if (window._currentPathPopup) {
      window._currentPathPopup._suppressClear = true;
      window._currentPathPopup.remove();
      window._currentPathPopup = null;
    }

    const existingPopups = document.getElementsByClassName("maplibregl-popup");
    while (existingPopups.length > 0) {
      existingPopups[0].remove();
    }
    if (this.currentPopup) {
      this.currentPopup.remove();
      this.currentPopup = null;
    }

    // 清除之前高亮的路径（与站点top5的处理方式一致）
    if (this.map.getSource("otn-paths-highlight")) {
      this.map.getSource("otn-paths-highlight").setData({
        type: "FeatureCollection",
        features: [],
      });
      // 停止流动动画
      if (window.PathFlowAnimator) {
        window.PathFlowAnimator.stop();
      }
    }

    // 构建故障列表详情链接
    const faultListUrl =
      window.OTNFaultMapConfig.faultListUrl ||
      "/plugins/netbox_otnfaults/faults/";
    let detailUrl = faultListUrl;

    // 获取站点ID：优先从 sitesData 中获取，如果找不到则从 markerData 中获取
    let siteAId = siteAObj ? siteAObj.id : null;
    let siteZId = siteZObjs.length > 0 ? siteZObjs[0].id : null;

    // 如果从 sitesData 中找不到（可能是"未指定"站点没有经纬度），尝试从 markerData 中获取
    if (!siteAId || !siteZId) {
      const markerData =
        (window.OTNFaultMapConfig && window.OTNFaultMapConfig.markerData) || [];
      const siteZName = siteZNames[0] || "";

      // 查找匹配的故障记录，获取站点ID
      const matchingFault = markerData.find((m) => {
        if (m.category !== "fiber") return false;
        return this.matchesPath(m.a_site, m.z_sites, siteAName, siteZName);
      });

      if (matchingFault) {
        // 根据匹配方向获取正确的ID
        if (matchingFault.a_site === siteAName) {
          if (!siteAId) siteAId = matchingFault.a_site_id;
          if (
            !siteZId &&
            matchingFault.z_site_ids &&
            matchingFault.z_site_ids.length > 0
          ) {
            // 找到对应 siteZName 的 ID
            const zList = this.splitZSites(matchingFault.z_sites);
            const zIndex = zList.indexOf(siteZName);
            if (zIndex >= 0 && matchingFault.z_site_ids[zIndex]) {
              siteZId = matchingFault.z_site_ids[zIndex];
            }
          }
        } else {
          // 反向匹配
          if (!siteZId) siteZId = matchingFault.a_site_id;
          if (
            !siteAId &&
            matchingFault.z_site_ids &&
            matchingFault.z_site_ids.length > 0
          ) {
            const zList = this.splitZSites(matchingFault.z_sites);
            const zIndex = zList.indexOf(siteAName);
            if (zIndex >= 0 && matchingFault.z_site_ids[zIndex]) {
              siteAId = matchingFault.z_site_ids[zIndex];
            }
          }
        }
      }
    }

    // 如果成功获取到两个站点ID，构建带参数的链接
    if (siteAId && siteZId) {
      detailUrl = `${faultListUrl}?bidirectional_pair=${siteAId},${siteZId}`;
    }

    // 使用原始的siteZNameRaw显示
    const siteZDisplay = siteZNameRaw;

    // 计算此线路的历史故障统计（对于一对多，只使用第一个Z端站点计算）
    const timeStats = this.calculatePathTimeStats(
      siteAName,
      siteZNames[0] || ""
    );
    const monthlyStats = this.calculatePathMonthlyStats(
      siteAName,
      siteZNames[0] || ""
    );
    const timeStatsHtml = this.renderTimeStatsHtml(
      timeStats,
      "此线路",
      monthlyStats,
      detailUrl
    );

    // 如果找到了路径，优先使用路径几何数据进行飞行（即使站点包含"未指定"）
    if (matchedPaths.length > 0) {
      // 对于多路径，合并所有路径名称
      const pathNames = matchedPaths
        .map((p) => p.properties.name || "未命名")
        .join("、");
      console.log("[flyToPath] 匹配成功，使用路径几何数据飞行:", pathNames);

      // 计算所有路径的边界并fly to
      const bounds = new maplibregl.LngLatBounds();
      matchedPaths.forEach((path) => {
        const coords = path.geometry.coordinates;
        coords.forEach((c) => bounds.extend(c));
      });

      // 1. 立即显示静态高亮 (解决 FlyTo 过程无视觉反馈问题)
      // 高亮所有匹配的路径（使用FeatureCollection）
      const highlightData = {
        type: "FeatureCollection",
        features: matchedPaths,
      };

      if (this.map.getSource("otn-paths-highlight")) {
        this.map.getSource("otn-paths-highlight").setData(highlightData);
      }
      // 确保静态图层可见
      if (this.map.getLayer("otn-paths-highlight-outline"))
        this.map.setLayoutProperty(
          "otn-paths-highlight-outline",
          "visibility",
          "visible"
        );
      if (this.map.getLayer("otn-paths-highlight-layer"))
        this.map.setLayoutProperty(
          "otn-paths-highlight-layer",
          "visibility",
          "visible"
        );

      this.map.fitBounds(bounds, {
        padding: 100,
        linear: false,
        essential: true,
        duration: 2000,
      });

      // 2. 飞行结束后启动动态高亮 (覆盖静态 -> 动画 -> 静态)
      this.map.once("moveend", () => {
        // 使用全局统一的高亮逻辑 (A-Z-A 动画 -> 静态高亮)
        if (window.highlightPath) {
          window.highlightPath(highlightData);
        } else if (this.map.getSource("otn-paths-highlight")) {
          // Fallback legacy logic
          if (window.PathFlowAnimator) {
            window.PathFlowAnimator.start(highlightData);
          }
        }

        // 在第一条路径的中点显示弹窗
        const firstPath = matchedPaths[0];
        const coords = firstPath.geometry.coordinates;
        const midIndex = Math.floor(coords.length / 2);
        const midPoint = coords[midIndex];

        // 弹窗标题：如果多路径显示数量
        const popupTitle =
          matchedPaths.length > 1
            ? `光缆路径 (${matchedPaths.length}条)`
            : firstPath.properties.name || "光缆路径";

        // 使用 PopupTemplates 生成弹窗内容
        const pathUrl = firstPath.properties.url || "#";
        const pathProps = firstPath.properties;

        const pathPopupContent = PopupTemplates.pathPopup({
          pathName: popupTitle,
          pathUrl,
          siteAName: siteAName,
          siteZName: siteZDisplay,
          detailUrl,
          props: pathProps,
          timeStatsHtml,
        });

        // 创建弹窗
        const pathPopup = new maplibregl.Popup({
          maxWidth: "300px",
          className: "stats-popup",
        })
          .setLngLat(midPoint)
          .setHTML(pathPopupContent)
          .addTo(this.map);

        // 保存引用
        window._currentPathPopup = pathPopup;

        // 绑定关闭事件
        pathPopup.on("close", () => {
          // 如果标记了由于切换弹窗而关闭，则不清除高亮
          if (pathPopup._suppressClear) return;

          if (window.faultMapPlugin && window.faultMapPlugin.flowAnimator) {
            window.faultMapPlugin.flowAnimator.clearHighlight();
          } else if (window.PathFlowAnimator) {
            window.PathFlowAnimator.stop();
          }

          const map = this.map;
          if (map.getSource("otn-paths-highlight")) {
            map.getSource("otn-paths-highlight").setData({
              type: "FeatureCollection",
              features: [],
            });
          }

          if (window._currentPathPopup === pathPopup) {
            window._currentPathPopup = null;
          }
        });
      });

      return;
    }

    // 未找到匹配的光缆路径
    // 检查站点坐标是否有效
    if (hasUnspecifiedSite || hasInvalidCoords) {
      console.warn(
        '[flyToPath] 站点包含"未指定"或坐标无效，且无匹配路径，无法定位'
      );
      // 可以考虑显示一个提示
      return;
    }

    // 使用站点坐标定位（对于一对多情况，使用第一个Z端站点的坐标）
    console.warn(
      "[flyToPath] 未在光缆路径模型中找到匹配的路径，使用站点坐标定位"
    );
    console.log(
      "[flyToPath] 尝试匹配的站点对:",
      siteAName,
      "<->",
      siteZDisplay
    );

    // 计算两个站点的中心点（使用第一个Z端站点）
    const firstZObj = siteZObjs[0];
    const centerLng = (siteAObj.longitude + firstZObj.longitude) / 2;
    const centerLat = (siteAObj.latitude + firstZObj.latitude) / 2;

    // fly to中心点
    this.map.flyTo({
      center: [centerLng, centerLat],
      zoom: 8,
      essential: true,
      speed: 2.5,
    });

    // 显示弹窗（标注无对应光缆路径，使用 PopupTemplates 生成内容）
    const notFoundPopupContent = PopupTemplates.pathNotFoundPopup({
      siteAName,
      siteZName: siteZDisplay,
      detailUrl,
      timeStatsHtml,
    });

    this.currentPopup = new maplibregl.Popup({
      maxWidth: "300px",
      className: "stats-popup",
    })
      .setLngLat([centerLng, centerLat])
      .setHTML(notFoundPopupContent)
      .addTo(this.map);

    this.currentPopup.on("close", () => {
      this.currentPopup = null;
    });
  }

  /**
   * 根据业务名称高亮相关故障
   * @param {string} businessName - 业务名称
   */
  highlightBusinessFaults(businessName) {


    // 筛选包含该业务的故障
    const relatedFaults = (this.faultDataList || []).filter(f => {
      const impactedBusiness = f.impactedBusiness || f.impacted_business;

      if (!impactedBusiness) return false;
      const businesses = impactedBusiness.split('、').map(b => b.trim());
      return businesses.includes(businessName);
    });



    if (relatedFaults.length === 0) {
      console.warn('[BusinessHighlight] 未找到匹配的故障！');
      return;
    }

    // 启动高亮动画
    this._startBusinessHighlightAnimation(relatedFaults);
  }

  /**
   * 清除业务故障高亮
   */
  clearBusinessHighlight() {
    // 停止动画循环
    if (this._businessHighlightRunning) {
      this._businessHighlightRunning = false;
      if (this._businessAnimationFrameId) {
        cancelAnimationFrame(this._businessAnimationFrameId);
        this._businessAnimationFrameId = null;
      }
    }

    // 移除DeckGL Overlay
    if (this._businessDeckOverlay) {
      this.map.removeControl(this._businessDeckOverlay);
      if (this._businessDeckOverlay.finalize) {
        this._businessDeckOverlay.finalize();
      }
      this._businessDeckOverlay = null;
    }
  }

  /**
   * 启动业务高亮动画
   * @private
   * @param {Array} faults - 要高亮的故障列表
   */
  _startBusinessHighlightAnimation(faults) {
    // 确保先清除之前的动画
    this.clearBusinessHighlight();

    // 准备数据 - 统一收集所有故障点，带类型信息
    this._businessHighlightData = {
      faults: [] // 所有故障，包含位置、类型、状态等信息
    };

    // 从地图图层的GeoJSON source获取完整的故障features数据（包含坐标）
    const faultPointsSource = this.map.getSource('fault-points');
    const allFeatures = faultPointsSource ? faultPointsSource._data?.features || [] : [];



    // 收集所有故障数据（从地图GeoJSON features中查找）
    faults.forEach((fault, index) => {
      const faultId = fault.id;

      // 在地图GeoJSON features中查找对应的feature（包含geometry坐标）
      const feature = allFeatures.find(f =>
        f.properties?.id === faultId || f.id === faultId
      );

      if (feature && feature.geometry && feature.geometry.coordinates) {
        const [lng, lat] = feature.geometry.coordinates;
        this._businessHighlightData.faults.push({
          position: [lng, lat],
          id: faultId,
          category: feature.properties?.category || 'other',
          status: feature.properties?.statusKey || feature.properties?.status_key || 'processing'
        });
      } else if (index < 3) {
        console.warn('[BusinessHighlight] 未找到故障feature:', {
          索引: index,
          故障ID: faultId,
          在features中找到: !!feature
        });
      }
    });

    if (this._businessHighlightData.faults.length === 0) {
      console.error('[BusinessHighlight] 没有收集到任何有效的故障坐标！');
      return;
    }

    // 初始化动画状态
    this._businessAnimationTime = 0;
    this._businessHighlightRunning = true;

    // 创建DeckGL Overlay
    if (!this._businessDeckOverlay) {
      this._businessDeckOverlay = new deck.MapboxOverlay({
        interleaved: false,
        layers: []
      });
      this.map.addControl(this._businessDeckOverlay);
    }

    // 启动动画循环
    this._animateBusinessHighlight();
  }

  /**
   * 业务高亮动画循环
   * @private
   */
  _animateBusinessHighlight() {
    if (!this._businessHighlightRunning) {
      return;
    }

    // 更新时间 (0-100循环，产生脉冲效果)
    this._businessAnimationTime = (this._businessAnimationTime + 3) % 100;

    // 计算脉冲因子 (0 -> 1 -> 0)
    const pulse = Math.sin((this._businessAnimationTime / 100) * Math.PI * 2);
    const pulseFactor = (pulse + 1) / 2; // 归一化到 0-1

    // 创建图层 - 统一金色高亮
    const layers = [];

    if (this._businessHighlightData.faults.length > 0) {
      layers.push(
        new deck.ScatterplotLayer({
          id: 'business-faults-highlight',
          data: this._businessHighlightData.faults,
          getPosition: d => d.position,
          getRadius: 400 + pulseFactor * 200, // 400-600米范围脉冲
          getFillColor: [255, 215, 0, 150 + pulseFactor * 105], // 金色，透明度150-255
          radiusUnits: 'meters',
          radiusMinPixels: 12,
          radiusMaxPixels: 36,
          radiusScale: 1
        })
      );
    }

    // 更新DeckGL图层
    if (this._businessDeckOverlay) {
      this._businessDeckOverlay.setProps({ layers });
    }

    // 继续动画
    this._businessAnimationFrameId = requestAnimationFrame(
      this._animateBusinessHighlight.bind(this)
    );
  }

  /**
   * 绑定业务统计项、站点和路径的悬停高亮事件
   */
  _bindBusinessHighlightEvents() {
    // 绑定业务统计项
    const businessItems = this.container.querySelectorAll('.business-highlight-item');
    businessItems.forEach((item) => {
      item.addEventListener('mouseenter', (e) => {
        const businessName = e.currentTarget.dataset.businessName;
        if (businessName) {
          e.currentTarget.style.backgroundColor = 'rgba(0, 151, 167, 0.1)';
          this.highlightBusinessFaults(businessName);
        }
      });

      item.addEventListener('mouseleave', (e) => {
        e.currentTarget.style.backgroundColor = '';
        this.clearBusinessHighlight();
      });
    });

    // 绑定站点和路径项（通用处理）
    const hoverItems = this.container.querySelectorAll('.hover-highlight-item');
    hoverItems.forEach((item) => {
      item.addEventListener('mouseenter', (e) => {
        const type = e.currentTarget.dataset.highlightType;
        const name = e.currentTarget.dataset.highlightName;

        if (type && name) {
          e.currentTarget.style.backgroundColor = 'rgba(0, 151, 167, 0.1)';
          this._highlightByTypeAndName(type, name);
        }
      });

      item.addEventListener('mouseleave', (e) => {
        e.currentTarget.style.backgroundColor = '';
        this.clearBusinessHighlight();
      });
    });
  }

  /**
   * 根据类型和名称高亮故障
   * @private
   * @param {string} type - 类型: 'site' 或 'path'
   * @param {string} name - 站点名称或路径名称
   */
  _highlightByTypeAndName(type, name) {
    let relatedFaults = [];

    if (type === 'site') {
      // 筛选A端站点匹配的故障
      relatedFaults = (this.faultDataList || []).filter(f => {
        return f.a_site === name;
      });
    } else if (type === 'path') {
      // 路径名称格式: "站点A <-> 站点B"
      const parts = name.split(' <-> ').map(s => s.trim());
      if (parts.length === 2) {
        const [siteA, siteZ] = parts;
        relatedFaults = (this.faultDataList || []).filter(f => {
          return this.matchesPath(f.a_site, f.z_sites, siteA, siteZ);
        });
      }
    }

    if (relatedFaults.length === 0) {
      console.warn(`[Highlight] 未找到匹配的故障 (${type}: ${name})`);
      return;
    }

    // 复用业务高亮动画
    this._startBusinessHighlightAnimation(relatedFaults);
  }
}

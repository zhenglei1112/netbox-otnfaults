/**
 * 弹窗 HTML 模板服务
 * 集中管理所有 Popup 的 HTML 模板，解决 JS 中内嵌大量 HTML 的问题
 */
class PopupTemplates {
  /**
   * 生成故障点悬停弹窗 HTML
   * @param {Object} props - 故障点属性
   * @returns {string} HTML 字符串
   */
  static faultPopup(props) {
    // 提取历时中的小时数
    let durationHtml = "";
    if (props.faultDuration && props.faultDuration !== "未知") {
      const hourMatch = props.faultDuration.match(/（([\d.]+)小时）/);
      const hours = hourMatch ? hourMatch[1] : props.faultDuration;
      durationHtml = `<div class="popup-row"><span class="popup-label">历时</span><span>${hours}小时</span></div>`;
    }

    // 影响业务
    let impactsHtml = "";
    try {
      const impacts =
        typeof props.impactsDetails === "string"
          ? JSON.parse(props.impactsDetails)
          : props.impactsDetails;
      if (impacts && impacts.length > 0) {
        const impactItems = impacts
          .map((impact) => {
            const durationText = impact.duration_hours
              ? `${impact.duration_hours}小时`
              : "-";
            return `<div class="popup-impact-item"><span class="popup-impact-name">${impact.name}</span><span class="popup-impact-duration">${durationText}</span></div>`;
          })
          .join("");
        impactsHtml = `
                    <div class="popup-impacts">
                        <div class="popup-impacts-title">影响业务</div>
                        ${impactItems}
                    </div>`;
      }
    } catch (e) {
      console.warn("解析影响业务数据失败:", e);
    }

    // 图片
    let imagesHtml = "";
    if (props.hasImages) {
      try {
        const images =
          typeof props.images === "string"
            ? JSON.parse(props.images)
            : props.images;
        if (images && images.length > 0) {
          const thumbnails = images
            .slice(0, 3)
            .map(
              (img) =>
                `<a href="${img.url}" target="_blank" title="${img.name}"><img src="${img.url}" class="fault-popup-thumbnail" alt="${img.name}"></a>`
            )
            .join("");
          const moreText =
            images.length > 3
              ? `<span class="text-muted small">+${images.length - 3}</span>`
              : "";
          imagesHtml = `<div class="popup-row" style="align-items:flex-start;"><span class="popup-label">图片</span><div class="d-flex gap-1 flex-wrap">${thumbnails}${moreText}</div></div>`;
        }
      } catch (e) {
        console.warn("解析图片数据失败:", e);
      }
    }

    // 颜色映射
    const categoryBgColor = POPUP_CATEGORY_COLORS[props.category] || "#6c757d";
    const statusBgColor = POPUP_STATUS_COLORS[props.statusColor] || "#6c757d";

    // 站点显示
    const sitesDisplay =
      props.site +
      (props.zSites && props.zSites !== "未指定" ? " —— " + props.zSites : "");

    return `
            <div class="fault-popup">
                <div class="popup-sites">${sitesDisplay}</div>
                <div class="popup-badges">
                    <span class="popup-badge" style="background-color: ${categoryBgColor};">${props.categoryName}</span>
                    <span class="popup-badge" style="background-color: ${statusBgColor};">${props.status}</span>
                </div>
                <div class="popup-row"><span class="popup-label">中断</span><span>${props.date}</span></div>
                <div class="popup-row"><span class="popup-label">恢复</span><span>${props.recoveryTime}</span></div>
                ${durationHtml}
                <div class="popup-row"><span class="popup-label">原因</span><span>${props.reason}</span></div>
                ${impactsHtml}
                ${imagesHtml}
                <div class="popup-footer">
                    <a href="${props.url}" target="_blank">${props.number}</a>
                </div>
            </div>
        `;
  }

  /**
   * 生成站点弹窗 HTML
   * @param {Object} params - 参数对象
   * @param {string} params.siteName - 站点名称
   * @param {string} params.siteUrl - 站点对象链接（NetBox站点页面）
   * @param {string} params.detailUrl - 详情链接（故障列表筛选）
   * @param {Object} params.props - 站点属性
   * @param {string} params.timeStatsHtml - 时间统计 HTML
   * @returns {string} HTML 字符串
   */
  static sitePopup({ siteName, siteUrl, detailUrl, props, timeStatsHtml }) {
    const regionHtml = props.region
      ? `<span><i class="mdi mdi-earth"></i> ${props.region}</span>`
      : "";
    const statusHtml = props.status
      ? `<span><i class="mdi mdi-check-circle"></i> ${props.status}</span>`
      : "";
    // 站点名称超链接（跳转至 NetBox 站点对象）
    const siteNameHtml = siteUrl
      ? `<a href="${siteUrl}" target="_blank" class="stats-popup-title-link">${siteName}</a>`
      : `<span>${siteName}</span>`;

    return `
            <div class="stats-popup-content">
                <div class="stats-popup-header">
                    <div class="stats-popup-title">
                        <i class="mdi mdi-map-marker"></i>
                        ${siteNameHtml}
                    </div>
                </div>
                <div class="stats-popup-body">
                    <div class="stats-popup-info">
                        ${regionHtml}
                        ${statusHtml}
                    </div>
                </div>
                ${timeStatsHtml || ""}
            </div>
            ${PopupTemplates.statsPopupStyles()}
        `;
  }

  /**
   * 生成路径弹窗 HTML
   * @param {Object} params - 参数对象
   * @param {string} params.pathName - 路径名称
   * @param {string} params.pathUrl - 路径对象链接（NetBox路径页面）
   * @param {string} params.siteAName - A端站点名
   * @param {string} params.siteZName - Z端站点名
   * @param {string} params.detailUrl - 详情链接（故障列表筛选）
   * @param {Object} params.props - 路径属性
   * @param {string} params.timeStatsHtml - 时间统计 HTML
   * @returns {string} HTML 字符串
   */
  static pathPopup({
    pathName,
    pathUrl,
    siteAName,
    siteZName,
    detailUrl,
    props,
    timeStatsHtml,
  }) {
    // 保留旧的长度显示
    const lengthHtml = props.total_length
      ? `<span><i class="mdi mdi-ruler"></i> ${props.total_length} km</span>`
      : "";

    const statusHtml = props.operational_status
      ? `<span><i class="mdi mdi-information"></i> ${props.operational_status}</span>`
      : "";
    // 路径名称超链接（跳转至 NetBox 路径对象）
    const pathNameDisplay = pathName || "光缆路径";
    const pathNameHtml = pathUrl
      ? `<a href="${pathUrl}" target="_blank" class="stats-popup-title-link">${pathNameDisplay}</a>`
      : `<span>${pathNameDisplay}</span>`;

    return `
            <div class="stats-popup-content">
                <div class="stats-popup-header">
                    <div class="stats-popup-title">
                        <i class="mdi mdi-vector-polyline" style="color: #198754;"></i>
                        ${pathNameHtml}
                    </div>
                </div>
                <div class="stats-popup-body">
                    <div class="stats-popup-sites">
                        <span><i class="mdi mdi-alpha-a-circle-outline"></i> ${siteAName}</span>
                        <span class="stats-popup-arrow">→</span>
                        <span><i class="mdi mdi-alpha-z-circle-outline"></i> ${siteZName}</span>
                    </div>
                    <div class="stats-popup-meta">
                        ${lengthHtml}
                        ${statusHtml}
                    </div>
                </div>
                ${timeStatsHtml || ""}
            </div>
            ${PopupTemplates.statsPopupStyles()}
        `;
  }

  /**
   * 生成无匹配路径的弹窗 HTML（故障路径但无对应光缆）
   * @param {Object} params - 参数对象
   * @returns {string} HTML 字符串
   */
  static pathNotFoundPopup({ siteAName, siteZName, detailUrl, timeStatsHtml }) {
    return `
            <div class="stats-popup-content">
                <div class="stats-popup-header">
                    <div class="stats-popup-title">
                        <i class="mdi mdi-transit-connection-variant" style="color: #dc3545;"></i>
                        <span>故障路径</span>
                    </div>
                </div>
                <div class="stats-popup-body">
                    <div class="stats-popup-sites">
                        <span><i class="mdi mdi-alpha-a-circle-outline"></i> ${siteAName}</span>
                        <span class="stats-popup-arrow">→</span>
                        <span><i class="mdi mdi-alpha-z-circle-outline"></i> ${siteZName}</span>
                    </div>
                    <span class="stats-tag stats-tag-warning">无对应光缆路径</span>
                </div>
                ${timeStatsHtml || ""}
            </div>
            ${PopupTemplates.statsPopupStyles()}
        `;
  }

  /**
   * 生成统计站点弹窗 HTML（用于 FaultStatisticsControl 的 flyToSite）
   * @param {Object} params - 参数对象
   * @returns {string} HTML 字符串
   */
  static statsSitePopup({ siteName, detailUrl, timeStatsHtml }) {
    return `
            <div class="stats-popup-content">
                <div class="stats-popup-header">
                    <div class="stats-popup-title">
                        <i class="mdi mdi-map-marker"></i>
                        <span>${siteName}</span>
                    </div>
                </div>
                ${timeStatsHtml || ""}
            </div>
            ${PopupTemplates.statsPopupStyles()}
        `;
  }

  /**
   * 生成统计路径弹窗 HTML（用于 FaultStatisticsControl 的 flyToPath - 匹配成功）
   * @param {Object} params - 参数对象
   * @returns {string} HTML 字符串
   */
  static statsPathPopup({
    popupTitle,
    siteAName,
    siteZName,
    detailUrl,
    props,
    timeStatsHtml,
  }) {
    // 保留旧的长度显示
    const lengthHtml = props && props.total_length
      ? `<span><i class="mdi mdi-ruler"></i> ${props.total_length} km</span>`
      : "";

    return `
            <div class="stats-popup-content">
                <div class="stats-popup-header">
                    <div class="stats-popup-title">
                        <i class="mdi mdi-vector-polyline" style="color: #198754;"></i>
                        <span>${popupTitle}</span>
                    </div>
                </div>
                <div class="stats-popup-body">
                    <div class="stats-popup-sites">
                        <span><i class="mdi mdi-alpha-a-circle-outline"></i> ${siteAName}</span>
                        <span class="stats-popup-arrow">→</span>
                        <span><i class="mdi mdi-alpha-z-circle-outline"></i> ${siteZName}</span>
                    </div>
                    <div class="stats-popup-meta">
                        ${lengthHtml}
                    </div>
                </div>
                ${timeStatsHtml || ""}
            </div>
            ${PopupTemplates.statsPopupStyles()}
        `;
  }

  /**
   * 返回统计弹窗的公共 CSS 样式（避免重复内联）
   * @returns {string} style 标签 HTML
   */
  static statsPopupStyles() {
    // 检查 DOM 中是否已存在样式标签（弹窗关闭时样式不会被移除）
    if (document.getElementById("stats-popup-styles")) {
      return "";
    }
    return `
                <style id="stats-popup-styles">
                    .stats-popup .maplibregl-popup-content { padding: 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
                    .stats-popup-content { font-family: inherit; }
                    .stats-popup-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; background: #f8f9fa; border-bottom: 1px solid #e9ecef; }
                    .stats-popup-footer { display: flex; justify-content: flex-end; padding: 6px 10px; border-top: 1px solid #e9ecef; }
                    .stats-popup-title { display: flex; align-items: center; gap: 6px; font-weight: 600; font-size: 13px; color: #212529; }
                    .stats-popup-title i { color: #0d6efd; font-size: 16px; }
                    .stats-popup-title-link { color: inherit; text-decoration: none; outline: none; }
                    .stats-popup-title-link:hover { color: #0d6efd; text-decoration: underline; }
                    .stats-popup-title-link:focus { outline: none; }
                    .stats-popup-link { display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; color: #6c757d; border-radius: 4px; transition: all 0.15s; flex-shrink: 0; }
                    .stats-popup-link:hover { background: #e9ecef; color: #0d6efd; }
                    .stats-popup-link i { font-size: 14px; }
                    .stats-popup-body { padding: 8px 10px; border-bottom: 1px solid #e9ecef; }
                    .stats-popup-info { display: flex; gap: 12px; font-size: 11px; color: #6c757d; }
                    .stats-popup-sites { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #495057; margin-bottom: 6px; flex-wrap: wrap; }
                    .stats-popup-sites i { color: #0d6efd; font-size: 14px; }
                    .stats-popup-arrow { color: #adb5bd; }
                    .stats-popup-meta { display: flex; gap: 12px; font-size: 11px; color: #6c757d; }
                    .stats-tag { font-size: 11px; padding: 2px 6px; border-radius: 3px; font-weight: 500; }
                    .stats-tag-warning { background: #fff3cd; color: #856404; }
                    .stats-tag-danger { background: #f8d7da; color: #721c24; }
                    .stats-tag-sub { font-size: 11px; color: #6c757d; }
                    .stats-time-section { padding: 8px 10px; }
                    .stats-time-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: nowrap; gap: 8px; }
                    .stats-time-title { font-size: 11px; font-weight: 600; color: #495057; margin-bottom: 0; }
                    .stats-time-grid { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-bottom: 8px; }
                    .stats-time-item { display: flex; align-items: center; gap: 2px; font-size: 11px; color: #6c757d; }
                    .stats-time-label { color: #6c757d; }
                    .stats-time-value { font-weight: 700; color: #0097a7; font-size: 12px; }
                    .stats-time-unit { color: #6c757d; }
                    .stats-chart-section { padding: 0 10px 8px 10px; }
                    .stats-chart-title { font-size: 10px; color: #6c757d; margin-bottom: 4px; }
                    .stats-line-chart { display: block; }
                </style>
            `;
  }
}

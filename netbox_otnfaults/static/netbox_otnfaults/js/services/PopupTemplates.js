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
        let durationHtml = '';
        if (props.faultDuration && props.faultDuration !== '未知') {
            const hourMatch = props.faultDuration.match(/（([\d.]+)小时）/);
            const hours = hourMatch ? hourMatch[1] : props.faultDuration;
            durationHtml = `<div class="popup-row"><span class="popup-label">历时</span><span>${hours}小时</span></div>`;
        }
        
        // 图片
        let imagesHtml = '';
        if (props.hasImages) {
            try {
                const images = typeof props.images === 'string' ? JSON.parse(props.images) : props.images;
                if (images && images.length > 0) {
                    const thumbnails = images.slice(0, 3).map(img => 
                        `<a href="${img.url}" target="_blank" title="${img.name}"><img src="${img.url}" class="fault-popup-thumbnail" alt="${img.name}"></a>`
                    ).join('');
                    const moreText = images.length > 3 ? `<span class="text-muted small">+${images.length - 3}</span>` : '';
                    imagesHtml = `<div class="popup-row" style="align-items:flex-start;"><span class="popup-label">图片</span><div class="d-flex gap-1 flex-wrap">${thumbnails}${moreText}</div></div>`;
                }
            } catch (e) {
                console.warn('解析图片数据失败:', e);
            }
        }
        
        // 颜色映射
        const categoryBgColor = POPUP_CATEGORY_COLORS[props.category] || '#6c757d';
        const statusBgColor = POPUP_STATUS_COLORS[props.statusColor] || '#6c757d';
        
        // 站点显示
        const sitesDisplay = props.site + (props.zSites && props.zSites !== '未指定' ? ' —— ' + props.zSites : '');
        
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
     * @param {string} params.detailUrl - 详情链接
     * @param {Object} params.props - 站点属性
     * @param {string} params.timeStatsHtml - 时间统计 HTML
     * @returns {string} HTML 字符串
     */
    static sitePopup({ siteName, detailUrl, props, timeStatsHtml }) {
        const regionHtml = props.region ? `<span><i class="mdi mdi-earth"></i> ${props.region}</span>` : '';
        const statusHtml = props.status ? `<span><i class="mdi mdi-check-circle"></i> ${props.status}</span>` : '';
        
        return `
            <div class="stats-popup-content">
                <div class="stats-popup-header">
                    <div class="stats-popup-title">
                        <i class="mdi mdi-map-marker"></i>
                        <span>${siteName}</span>
                    </div>
                    <a href="${detailUrl}" class="stats-popup-link" target="_blank" title="查看详情">
                        <i class="mdi mdi-open-in-new"></i>
                    </a>
                </div>
                <div class="stats-popup-body">
                    <div class="stats-popup-info">
                        ${regionHtml}
                        ${statusHtml}
                    </div>
                </div>
                ${timeStatsHtml || ''}
            </div>
        `;
    }
    
    /**
     * 生成路径弹窗 HTML
     * @param {Object} params - 参数对象
     * @param {string} params.pathName - 路径名称
     * @param {string} params.siteAName - A端站点名
     * @param {string} params.siteZName - Z端站点名
     * @param {string} params.detailUrl - 详情链接
     * @param {Object} params.props - 路径属性
     * @param {string} params.timeStatsHtml - 时间统计 HTML
     * @returns {string} HTML 字符串
     */
    static pathPopup({ pathName, siteAName, siteZName, detailUrl, props, timeStatsHtml }) {
        const lengthHtml = props.total_length ? `<span><i class="mdi mdi-ruler"></i> ${props.total_length} km</span>` : '';
        const statusHtml = props.operational_status ? `<span><i class="mdi mdi-information"></i> ${props.operational_status}</span>` : '';
        
        return `
            <div class="stats-popup-content">
                <div class="stats-popup-header">
                    <div class="stats-popup-title">
                        <i class="mdi mdi-vector-polyline" style="color: #198754;"></i>
                        <span>${pathName || '光缆路径'}</span>
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
                    <div class="stats-popup-meta">
                        ${lengthHtml}
                        ${statusHtml}
                    </div>
                </div>
                ${timeStatsHtml || ''}
            </div>
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
                ${timeStatsHtml || ''}
            </div>
        `;
    }
}

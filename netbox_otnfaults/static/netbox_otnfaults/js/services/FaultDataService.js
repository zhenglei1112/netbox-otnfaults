/**
 * 故障数据服务
 * 负责数据转换、筛选和格式化
 */
class FaultDataService {
    /**
     * 将原始 markerData 转换为 GeoJSON Feature 格式
     * @param {Array} markerData - 原始故障数据数组
     * @returns {Array} GeoJSON Feature 数组
     */
    static convertToFeatures(markerData) {
        return markerData.map(m => {
            const category = m.category || 'other';
            const categoryColor = FAULT_CATEGORY_COLORS[category] || FAULT_CATEGORY_COLORS['other'];
            const dateStr = m.occurrence_time || '';
            const isoDateStr = dateStr.replace(' ', 'T');
            
            const statusKey = m.status_key || 'processing';
            const statusColorHex = FAULT_STATUS_COLORS[statusKey] || FAULT_STATUS_COLORS['processing'];
            
            return {
                type: 'Feature',
                properties: {
                    id: m.id || Math.random().toString(36).substr(2, 9),
                    number: m.number || '未知编号',
                    title: m.details || m.number || '未命名故障',
                    site: m.a_site || '未指定',
                    zSites: m.z_sites || '',
                    status: m.status || '',
                    statusKey: statusKey,
                    statusColor: m.status_color || 'secondary',
                    statusColorHex: statusColorHex,
                    category: category,
                    categoryName: FAULT_CATEGORY_NAMES[category] || category,
                    date: dateStr,
                    isoDate: isoDateStr,
                    recoveryTime: m.recovery_time || '未恢复',
                    faultDuration: m.fault_duration || '未知',
                    reason: m.reason || '-',
                    url: m.url || '#',
                    color: categoryColor,
                    hasImages: m.has_images || false,
                    imageCount: m.image_count || 0,
                    images: JSON.stringify(m.images || []),
                    raw: m
                },
                geometry: {
                    type: 'Point',
                    coordinates: [m.lng, m.lat]
                }
            };
        });
    }

    /**
     * 根据时间范围筛选故障数据
     * @param {Array} features - GeoJSON Feature 数组
     * @param {string} timeRange - 时间范围键值
     * @returns {Array} 筛选后的 Feature 数组
     */
    static filterByTimeRange(features, timeRange) {
        const now = window.OTN_DEBUG_MODE ? new Date(window.OTN_DEBUG_DATE) : new Date();
        const rangeOption = TIME_RANGE_OPTIONS.find(r => r.value === timeRange);
        const rangeDays = rangeOption ? rangeOption.days : 365;
        const rangeMs = rangeDays * 24 * 60 * 60 * 1000;
        
        return features.filter(f => {
            const dateStr = f.properties.isoDate;
            if (!dateStr) return false;
            
            const date = new Date(dateStr);
            return (now - date) <= rangeMs;
        });
    }

    /**
     * 根据故障类型筛选
     * @param {Array} features - GeoJSON Feature 数组
     * @param {Array} selectedCategories - 选中的类型数组
     * @returns {Array} 筛选后的 Feature 数组
     */
    static filterByCategories(features, selectedCategories) {
        if (!selectedCategories || selectedCategories.length === 0) {
            return [];
        }
        return features.filter(f => selectedCategories.includes(f.properties.category));
    }

    /**
     * 组合筛选：时间范围 + 类型
     * @param {Array} features - GeoJSON Feature 数组
     * @param {string} timeRange - 时间范围键值
     * @param {Array} selectedCategories - 选中的类型数组
     * @returns {Array} 筛选后的 Feature 数组
     */
    static filter(features, timeRange, selectedCategories) {
        let result = this.filterByTimeRange(features, timeRange);
        result = this.filterByCategories(result, selectedCategories);
        return result;
    }

    /**
     * 转换热力图数据格式
     * @param {Object|Array} heatmapData - 原始热力图数据
     * @returns {Object} GeoJSON FeatureCollection
     */
    static normalizeHeatmapData(heatmapData) {
        if (Array.isArray(heatmapData)) {
            return {
                type: 'FeatureCollection',
                features: heatmapData.map(item => ({
                    type: 'Feature',
                    properties: {
                        count: item.count || 1,
                        weight: item.count || 1,
                        date: item.occurrence_time,
                        category: item.category
                    },
                    geometry: {
                        type: 'Point',
                        coordinates: [item.lng, item.lat]
                    }
                }))
            };
        } else if (heatmapData && heatmapData.features) {
            // 确保每个 feature 都有 weight 属性
            heatmapData.features.forEach(f => {
                if (f.properties.weight === undefined) {
                    f.properties.weight = f.properties.count || 1;
                }
            });
            return heatmapData;
        }
        
        return { type: 'FeatureCollection', features: [] };
    }
}

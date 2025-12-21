/**
 * NetBox OTN 故障分布图 API 工具类
 * 处理所有与后端的数据交互
 */

const OTNFaultMapAPI = {
    /**
     * 获取 OTN 路径数据
     * @param {string} apiKey - API 密钥
     * @returns {Promise<Array>} - 路径 GeoJSON 特征数组
     */
    fetchPaths: function(apiKey) {
        return fetch('/api/plugins/otnfaults/paths/?limit=0', {
            method: 'GET',
            headers: {
                'Authorization': `Token ${apiKey}`,
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const results = data.results || [];
            return results
                .filter(path => path.geometry) // 仅处理带几何信息的路径
                .map(path => {
                    let geometry = path.geometry;
                    // 处理几何数据
                    if (typeof geometry === 'string') {
                        try {
                            const jsonString = geometry.replace(/'/g, '"');
                            const coordinates = JSON.parse(jsonString);
                            geometry = {
                                type: 'LineString',
                                coordinates: coordinates
                            };
                        } catch (e) {
                            console.warn(`Failed to parse geometry for path ${path.id}:`, e);
                            return null;
                        }
                    } else if (Array.isArray(geometry)) {
                        // 如果直接是坐标数组
                        geometry = {
                            type: 'LineString',
                            coordinates: geometry
                        };
                    } else if (typeof geometry === 'object') {
                        // 验证 GeoJSON 对象结构
                        if (!geometry.type || !geometry.coordinates) {
                            console.warn(`Invalid geometry object for path ${path.id}:`, geometry);
                            return null;
                        }
                    }

                    return {
                        type: 'Feature',
                        geometry: geometry,
                        properties: {
                            id: path.id,
                            name: path.name,
                            // 构建前端详情页 URL（非 API URL）
                            url: `/plugins/otnfaults/paths/${path.id}/`,
                            // site_a 和 site_z 是嵌套对象，需要提取 name 和 id
                            a_site: path.site_a ? path.site_a.name : null,
                            z_site: path.site_z ? path.site_z.name : null,
                            a_site_id: path.site_a ? path.site_a.id : null,
                            z_site_id: path.site_z ? path.site_z.id : null,
                            site_list: path.site_list,
                            admin_status: path.admin_status,
                            operational_status: path.operational_status,
                            segment_count: path.segment_count,
                            total_length: path.total_length
                        }
                    };
                })
                .filter(item => item !== null);
        });
    }
};

window.OTNFaultMapAPI = OTNFaultMapAPI;

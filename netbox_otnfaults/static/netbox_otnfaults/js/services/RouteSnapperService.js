/**
 * 路径吸附服务
 * 调用后端 API 计算高速公路路径
 */

class RouteSnapperService {
    constructor(apiUrl = '/api/plugins/otnfaults/route-snapper/calculate/') {
        this.apiUrl = apiUrl;
    }

    /**
     * 计算两点间沿高速公路的路径
     * @param {Array} waypoints - 途经点数组 [{lng, lat}, ...]
     * @returns {Promise} - 返回路径几何和长度
     */
    async calculateRoute(waypoints) {
        try {
            // 获取 CSRF Token
            const csrfToken = this._getCsrfToken();

            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ waypoints })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            if (result.fallback) {
                console.warn('[RouteSnapperService] 使用降级方案:', result.message);
            }

            return result;

        } catch (error) {
            console.error('[RouteSnapperService] API 调用失败:', error);
            // 降级为直线连接
            return {
                success: true,
                route: {
                    geometry: {
                        type: 'LineString',
                        coordinates: waypoints.map(w => [w.lng, w.lat])
                    },
                    length_meters: this._calculateStraightLineDistance(waypoints)
                },
                fallback: true,
                error: error.message
            };
        }
    }

    /**
     * 获取 CSRF Token
     */
    _getCsrfToken() {
        // 方法1: 从 cookie 获取
        const cookie = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        if (cookie) {
            return cookie.split('=')[1];
        }

        // 方法2: 从 meta 标签获取（NetBox 使用这种方式）
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) {
            return meta.getAttribute('content');
        }

        // 方法3: 从隐藏表单字段获取
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input) {
            return input.value;
        }

        console.warn('[RouteSnapperService] 无法获取 CSRF token');
        return '';
    }

    /**
     * 计算直线距离（降级方案）
     */
    _calculateStraightLineDistance(waypoints) {
        if (waypoints.length < 2) return 0;

        let total = 0;
        for (let i = 0; i < waypoints.length - 1; i++) {
            const R = 6371000;
            const lat1 = waypoints[i].lat * Math.PI / 180;
            const lat2 = waypoints[i + 1].lat * Math.PI / 180;
            const deltaLat = (waypoints[i + 1].lat - waypoints[i].lat) * Math.PI / 180;
            const deltaLng = (waypoints[i + 1].lng - waypoints[i].lng) * Math.PI / 180;

            const a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
                Math.cos(lat1) * Math.cos(lat2) *
                Math.sin(deltaLng / 2) * Math.sin(deltaLng / 2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

            total += R * c;
        }

        return total;
    }
}

// 导出为全局变量
window.RouteSnapperService = RouteSnapperService;

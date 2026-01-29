/**
 * 空间选择控件 (SpatialSelectControl)
 * 用于在路径组地图模式中选择站点和路径
 * 
 * 功能：
 * - 框选（矩形选择）
 * - 圈选（圆形选择）
 * - 自由选择（多边形选择）
 */

class SpatialSelectControl {
    constructor(options = {}) {
        this.map = null;
        this.pathGroupId = options.pathGroupId;
        this.pathGroupName = options.pathGroupName || '当前路径组';
        this.onAddComplete = options.onAddComplete;    // 添加完成回调

        // 控件状态
        this.isActive = false;
        this.currentMode = null;  // 'rectangle' | 'circle' | 'polygon'
        this.isDrawing = false;

        // 绘制状态
        this.startPoint = null;
        this.polygonPoints = [];

        // 选中的对象
        this.selectedSites = [];
        this.selectedPaths = [];

        // DOM 元素
        this.container = null;
        this.menuContainer = null;

        // 图层和数据源 ID
        this.DRAW_SOURCE = 'spatial-select-draw';
        this.DRAW_LAYER_FILL = 'spatial-select-fill';
        this.DRAW_LAYER_LINE = 'spatial-select-line';
        this.HIGHLIGHT_SOURCE = 'spatial-select-highlight';
        this.HIGHLIGHT_LAYER = 'spatial-select-highlight-layer';

        // 绑定事件处理器
        this._onMouseDown = this._onMouseDown.bind(this);
        this._onMouseMove = this._onMouseMove.bind(this);
        this._onMouseUp = this._onMouseUp.bind(this);
        this._onClick = this._onClick.bind(this);
        this._onDblClick = this._onDblClick.bind(this);
        this._onKeyDown = this._onKeyDown.bind(this);
    }

    // ========================================
    // MapLibre 控件接口
    // ========================================

    onAdd(map) {
        this.map = map;
        this._createContainer();
        this._initMapLayers();
        return this.container;
    }

    onRemove() {
        this._cleanup();
        this.container.parentNode?.removeChild(this.container);
        this.map = null;
    }

    // ========================================
    // UI 创建
    // ========================================

    _createContainer() {
        // 主容器
        this.container = document.createElement('div');
        this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group spatial-select-control';

        // 主按钮
        const mainBtn = document.createElement('button');
        mainBtn.type = 'button';
        mainBtn.className = 'spatial-select-main-btn';
        mainBtn.title = '图上选择站点路径';
        mainBtn.innerHTML = '<i class="mdi mdi-selection-drag"></i>';
        mainBtn.addEventListener('click', () => this._toggleMenu());
        this.container.appendChild(mainBtn);
        this.mainBtn = mainBtn;

        // 二级菜单
        this.menuContainer = document.createElement('div');
        this.menuContainer.className = 'spatial-select-menu';
        this.menuContainer.style.display = 'none';
        this.menuContainer.innerHTML = `
      <div class="spatial-select-menu-item" data-mode="rectangle">
        <i class="mdi mdi-selection"></i>
        <span>框选</span>
      </div>
      <div class="spatial-select-menu-item" data-mode="circle">
        <i class="mdi mdi-circle-outline"></i>
        <span>圈选</span>
      </div>
      <div class="spatial-select-menu-item" data-mode="polygon">
        <i class="mdi mdi-vector-polygon"></i>
        <span>自由选择</span>
      </div>
    `;
        this.container.appendChild(this.menuContainer);

        // 菜单项点击
        this.menuContainer.querySelectorAll('.spatial-select-menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const mode = item.dataset.mode;
                this._activateMode(mode);
            });
        });
    }

    _toggleMenu() {
        if (this.isActive) {
            this._deactivate();
        } else {
            const isVisible = this.menuContainer.style.display !== 'none';
            this.menuContainer.style.display = isVisible ? 'none' : 'block';
        }
    }

    // ========================================
    // 模式激活/停用
    // ========================================

    _activateMode(mode) {
        this.currentMode = mode;
        this.isActive = true;
        this.menuContainer.style.display = 'none';
        this.mainBtn.classList.add('active');

        // 更新光标样式
        this.map.getCanvas().style.cursor = 'crosshair';

        // 绑定事件
        if (mode === 'rectangle' || mode === 'circle') {
            this.map.on('mousedown', this._onMouseDown);
        } else if (mode === 'polygon') {
            this.map.on('click', this._onClick);
            this.map.on('dblclick', this._onDblClick);
            this.map.on('mousemove', this._onMouseMove);
        }

        // ESC 取消
        document.addEventListener('keydown', this._onKeyDown);

        // 显示提示
        this._showTip(mode);
    }

    _deactivate() {
        this.isActive = false;
        this.isDrawing = false;
        this.currentMode = null;
        this.startPoint = null;
        this.polygonPoints = [];
        this.selectedSites = [];
        this.selectedPaths = [];

        // 恢复光标
        this.map.getCanvas().style.cursor = '';
        this.mainBtn.classList.remove('active');

        // 解绑事件
        this.map.off('mousedown', this._onMouseDown);
        this.map.off('mousemove', this._onMouseMove);
        this.map.off('mouseup', this._onMouseUp);
        this.map.off('click', this._onClick);
        this.map.off('dblclick', this._onDblClick);
        document.removeEventListener('keydown', this._onKeyDown);

        // 清除绘制图层
        this._clearDrawing();
        this._clearHighlight();
        this._hideTip();
    }

    _showTip(mode) {
        const tips = {
            rectangle: '按住鼠标拖拽绘制矩形选择区域，松开完成选择',
            circle: '按住鼠标从中心点拖拽绘制圆形选择区域',
            polygon: '点击添加顶点，双击完成多边形绘制'
        };

        let tipDiv = document.getElementById('spatial-select-tip');
        if (!tipDiv) {
            tipDiv = document.createElement('div');
            tipDiv.id = 'spatial-select-tip';
            tipDiv.className = 'spatial-select-tip';
            this.map.getContainer().appendChild(tipDiv);
        }
        tipDiv.textContent = tips[mode] + '  (ESC 取消)';
        tipDiv.style.display = 'block';
    }

    _hideTip() {
        const tipDiv = document.getElementById('spatial-select-tip');
        if (tipDiv) tipDiv.style.display = 'none';
    }

    // ========================================
    // 地图图层初始化
    // ========================================

    _initMapLayers() {
        // 绘制区域数据源
        if (!this.map.getSource(this.DRAW_SOURCE)) {
            this.map.addSource(this.DRAW_SOURCE, {
                type: 'geojson',
                data: { type: 'FeatureCollection', features: [] }
            });
        }

        // 绘制区域填充层
        if (!this.map.getLayer(this.DRAW_LAYER_FILL)) {
            this.map.addLayer({
                id: this.DRAW_LAYER_FILL,
                type: 'fill',
                source: this.DRAW_SOURCE,
                paint: {
                    'fill-color': '#0d6efd',
                    'fill-opacity': 0.15
                }
            });
        }

        // 绘制区域边框层
        if (!this.map.getLayer(this.DRAW_LAYER_LINE)) {
            this.map.addLayer({
                id: this.DRAW_LAYER_LINE,
                type: 'line',
                source: this.DRAW_SOURCE,
                paint: {
                    'line-color': '#0d6efd',
                    'line-width': 2,
                    'line-dasharray': [3, 3]
                }
            });
        }

        // 高亮选中对象数据源
        if (!this.map.getSource(this.HIGHLIGHT_SOURCE)) {
            this.map.addSource(this.HIGHLIGHT_SOURCE, {
                type: 'geojson',
                data: { type: 'FeatureCollection', features: [] }
            });
        }

        // 高亮点层
        if (!this.map.getLayer(this.HIGHLIGHT_LAYER)) {
            this.map.addLayer({
                id: this.HIGHLIGHT_LAYER,
                type: 'circle',
                source: this.HIGHLIGHT_SOURCE,
                paint: {
                    'circle-radius': 12,
                    'circle-color': '#FFD700',
                    'circle-opacity': 0.8,
                    'circle-stroke-width': 3,
                    'circle-stroke-color': '#FF6B35'
                }
            });
        }
    }

    // ========================================
    // 事件处理
    // ========================================

    _onMouseDown(e) {
        if (!this.isActive) return;
        if (e.originalEvent.button !== 0) return; // 只处理左键

        this.isDrawing = true;
        this.startPoint = [e.lngLat.lng, e.lngLat.lat];

        this.map.on('mousemove', this._onMouseMove);
        this.map.on('mouseup', this._onMouseUp);

        // 禁用地图拖拽
        this.map.dragPan.disable();
    }

    _onMouseMove(e) {
        if (!this.isActive) return;

        const currentPoint = [e.lngLat.lng, e.lngLat.lat];

        if (this.currentMode === 'rectangle' && this.isDrawing && this.startPoint) {
            this._drawRectangle(this.startPoint, currentPoint);
        } else if (this.currentMode === 'circle' && this.isDrawing && this.startPoint) {
            this._drawCircle(this.startPoint, currentPoint);
        } else if (this.currentMode === 'polygon' && this.polygonPoints.length > 0) {
            // 预览多边形
            this._drawPolygonPreview(currentPoint);
        }
    }

    _onMouseUp(e) {
        if (!this.isActive || !this.isDrawing) return;

        this.isDrawing = false;
        this.map.dragPan.enable();

        this.map.off('mousemove', this._onMouseMove);
        this.map.off('mouseup', this._onMouseUp);

        const endPoint = [e.lngLat.lng, e.lngLat.lat];

        if (this.currentMode === 'rectangle') {
            this._finishRectangle(this.startPoint, endPoint);
        } else if (this.currentMode === 'circle') {
            this._finishCircle(this.startPoint, endPoint);
        }
    }

    _onClick(e) {
        if (!this.isActive || this.currentMode !== 'polygon') return;

        const point = [e.lngLat.lng, e.lngLat.lat];
        this.polygonPoints.push(point);
        this._drawPolygonPreview(point);
    }

    _onDblClick(e) {
        if (!this.isActive || this.currentMode !== 'polygon') return;
        if (this.polygonPoints.length < 3) return;

        e.preventDefault();
        this._finishPolygon();
    }

    _onKeyDown(e) {
        if (e.key === 'Escape') {
            this._deactivate();
        }
    }

    // ========================================
    // 绘制图形
    // ========================================

    _drawRectangle(start, end) {
        const polygon = {
            type: 'Feature',
            geometry: {
                type: 'Polygon',
                coordinates: [[
                    [start[0], start[1]],
                    [end[0], start[1]],
                    [end[0], end[1]],
                    [start[0], end[1]],
                    [start[0], start[1]]
                ]]
            }
        };
        this._updateDrawSource(polygon);
    }

    _drawCircle(center, edge) {
        const radius = this._calculateDistance(center, edge);
        const polygon = this._createCirclePolygon(center, radius);
        this._updateDrawSource(polygon);
    }

    _drawPolygonPreview(currentPoint) {
        if (this.polygonPoints.length === 0) return;

        const coords = [...this.polygonPoints, currentPoint, this.polygonPoints[0]];
        const polygon = {
            type: 'Feature',
            geometry: {
                type: 'Polygon',
                coordinates: [coords]
            }
        };
        this._updateDrawSource(polygon);
    }

    _updateDrawSource(feature) {
        const source = this.map.getSource(this.DRAW_SOURCE);
        if (source) {
            source.setData({
                type: 'FeatureCollection',
                features: feature ? [feature] : []
            });
        }
    }

    _clearDrawing() {
        this._updateDrawSource(null);
    }

    // ========================================
    // 完成选择
    // ========================================

    _finishRectangle(start, end) {
        const polygon = [
            [start[0], start[1]],
            [end[0], start[1]],
            [end[0], end[1]],
            [start[0], end[1]],
            [start[0], start[1]]
        ];
        this._selectObjectsInPolygon(polygon);
    }

    _finishCircle(center, edge) {
        const radius = this._calculateDistance(center, edge);
        const circlePolygon = this._createCirclePolygon(center, radius);
        this._selectObjectsInPolygon(circlePolygon.geometry.coordinates[0]);
    }

    _finishPolygon() {
        if (this.polygonPoints.length < 3) return;

        const polygon = [...this.polygonPoints, this.polygonPoints[0]];
        this._selectObjectsInPolygon(polygon);
    }

    // ========================================
    // 选择逻辑
    // ========================================

    _selectObjectsInPolygon(polygonCoords) {
        this.selectedSites = [];
        this.selectedPaths = [];

        // 从底图数据源动态获取站点数据
        this._selectSitesFromBasemap(polygonCoords);

        // 从底图数据源动态获取路径数据
        this._selectPathsFromBasemap(polygonCoords);

        // 高亮选中对象
        this._highlightSelected();

        // 显示确认弹窗
        if (this.selectedSites.length > 0 || this.selectedPaths.length > 0) {
            this._showConfirmDialog();
        } else {
            this._showNoSelectionTip();
            this._deactivate();
        }
    }

    /**
     * 从底图数据源选择站点
     * 同时查询 highlight-sites（已在路径组中）和 netbox-sites（所有站点），合并去重
     */
    _selectSitesFromBasemap(polygonCoords) {
        // 使用 queryRenderedFeatures 从可见图层查询（最可靠的方法）
        const bounds = this._getPolygonBounds(polygonCoords);
        const sw = this.map.project([bounds.minLng, bounds.minLat]);
        const ne = this.map.project([bounds.maxLng, bounds.maxLat]);

        // 查询两种图层
        const layersToQuery = ['highlight-sites-layer', 'netbox-sites-layer'].filter(
            id => this.map.getLayer(id)
        );

        if (layersToQuery.length === 0) {
            return;
        }

        const features = this.map.queryRenderedFeatures(
            [[sw.x, ne.y], [ne.x, sw.y]],
            { layers: layersToQuery }
        );

        features.forEach(feature => {
            const coords = feature.geometry.coordinates;
            if (this._pointInPolygon(coords, polygonCoords)) {
                // 去重
                if (!this.selectedSites.find(s => s.id === feature.properties.id)) {
                    this.selectedSites.push({
                        id: feature.properties.id,
                        name: feature.properties.name,
                        lng: coords[0],
                        lat: coords[1]
                    });
                }
            }
        });
    }

    /**
     * 从底图数据源选择路径
     * 使用 queryRenderedFeatures 从可见图层查询路径
     */
    _selectPathsFromBasemap(polygonCoords) {
        const bounds = this._getPolygonBounds(polygonCoords);
        const sw = this.map.project([bounds.minLng, bounds.minLat]);
        const ne = this.map.project([bounds.maxLng, bounds.maxLat]);

        // 查询多种路径图层
        const layersToQuery = [
            'highlight-path-layer',
            'highlight-path-outline',
            'otn-paths-layer',
            'otn-paths-labels'
        ].filter(id => this.map.getLayer(id));

        if (layersToQuery.length === 0) return;

        const features = this.map.queryRenderedFeatures(
            [[sw.x, ne.y], [ne.x, sw.y]],
            { layers: layersToQuery }
        );

        features.forEach(feature => {
            if (feature.geometry.type === 'LineString' || feature.geometry.type === 'MultiLineString') {
                const coords = feature.geometry.type === 'LineString'
                    ? feature.geometry.coordinates
                    : feature.geometry.coordinates.flat();

                const hasPointInside = coords.some(coord =>
                    this._pointInPolygon(coord, polygonCoords)
                );

                if (hasPointInside) {
                    const pathId = feature.properties.id || feature.id;
                    if (!this.selectedPaths.find(p => p.id === pathId)) {
                        this.selectedPaths.push({
                            id: pathId,
                            name: feature.properties.name || `路径 ${pathId}`,
                            geometry: feature.geometry
                        });
                    }
                }
            }
        });
    }

    /**
     * 获取多边形的边界框
     */
    _getPolygonBounds(polygonCoords) {
        let minLng = Infinity, maxLng = -Infinity;
        let minLat = Infinity, maxLat = -Infinity;

        polygonCoords.forEach(coord => {
            minLng = Math.min(minLng, coord[0]);
            maxLng = Math.max(maxLng, coord[0]);
            minLat = Math.min(minLat, coord[1]);
            maxLat = Math.max(maxLat, coord[1]);
        });

        return { minLng, maxLng, minLat, maxLat };
    }

    _highlightSelected() {
        const features = [];

        // 添加站点高亮
        this.selectedSites.forEach(site => {
            features.push({
                type: 'Feature',
                geometry: {
                    type: 'Point',
                    coordinates: [site.lng, site.lat]
                },
                properties: { type: 'site', id: site.id, name: site.name }
            });
        });

        const source = this.map.getSource(this.HIGHLIGHT_SOURCE);
        if (source) {
            source.setData({
                type: 'FeatureCollection',
                features: features
            });
        }
    }

    _clearHighlight() {
        const source = this.map.getSource(this.HIGHLIGHT_SOURCE);
        if (source) {
            source.setData({ type: 'FeatureCollection', features: [] });
        }
    }

    // ========================================
    // 确认弹窗
    // ========================================

    _showConfirmDialog() {
        // 移除已有弹窗
        const existing = document.getElementById('spatial-select-confirm');
        if (existing) existing.remove();

        const dialog = document.createElement('div');
        dialog.id = 'spatial-select-confirm';
        dialog.className = 'spatial-select-confirm-dialog';
        dialog.innerHTML = `
      <div class="spatial-select-confirm-content">
        <div class="spatial-select-confirm-header">
          <i class="mdi mdi-help-circle-outline"></i>
          <span>确认添加</span>
        </div>
        <div class="spatial-select-confirm-body">
          <p>将选择的 <strong>${this.selectedSites.length}</strong> 个站点和 
             <strong>${this.selectedPaths.length}</strong> 条路径加入路径组 
             <strong>${this.pathGroupName}</strong> 吗？</p>
          ${this._renderSelectedList()}
        </div>
        <div class="spatial-select-confirm-footer">
          <button type="button" class="btn btn-secondary btn-sm" id="spatial-select-cancel">
            取消
          </button>
          <button type="button" class="btn btn-primary btn-sm" id="spatial-select-confirm-btn">
            确认添加
          </button>
        </div>
      </div>
    `;

        this.map.getContainer().appendChild(dialog);

        // 绑定按钮事件
        document.getElementById('spatial-select-cancel').addEventListener('click', () => {
            dialog.remove();
            this._deactivate();
        });

        document.getElementById('spatial-select-confirm-btn').addEventListener('click', () => {
            this._confirmAdd();
            dialog.remove();
        });
    }

    _renderSelectedList() {
        let html = '<div class="spatial-select-selected-list">';

        if (this.selectedSites.length > 0) {
            html += '<div class="selected-category"><strong>站点：</strong>';
            html += this.selectedSites.slice(0, 5).map(s => s.name).join('、');
            if (this.selectedSites.length > 5) {
                html += ` 等 ${this.selectedSites.length} 个`;
            }
            html += '</div>';
        }

        if (this.selectedPaths.length > 0) {
            html += '<div class="selected-category"><strong>路径：</strong>';
            html += this.selectedPaths.slice(0, 5).map(p => p.name || p.id).join('、');
            if (this.selectedPaths.length > 5) {
                html += ` 等 ${this.selectedPaths.length} 条`;
            }
            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    _showNoSelectionTip() {
        const tipDiv = document.getElementById('spatial-select-tip');
        if (tipDiv) {
            tipDiv.textContent = '选择区域内没有站点或路径';
            tipDiv.style.background = '#ffc107';
            tipDiv.style.color = '#000';
            setTimeout(() => this._hideTip(), 2000);
        }
    }

    // ========================================
    // 后端 API 调用
    // ========================================

    async _confirmAdd() {
        const siteIds = this.selectedSites.map(s => s.id);
        const pathIds = this.selectedPaths.map(p => p.id);

        try {
            const response = await fetch(`/api/plugins/otnfaults/path-groups/${this.pathGroupId}/batch-add/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this._getCSRFToken()
                },
                body: JSON.stringify({
                    site_ids: siteIds,
                    path_ids: pathIds
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this._showSuccessMessage(result);
                if (this.onAddComplete) {
                    this.onAddComplete(result);
                }
            } else {
                this._showErrorMessage(result.error || '添加失败');
            }
        } catch (error) {
            console.error('批量添加失败:', error);
            this._showErrorMessage('网络错误，请重试');
        }

        this._deactivate();
    }

    _getCSRFToken() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    _showSuccessMessage(result) {
        let msg = `成功添加 ${result.added_sites || 0} 个站点和 ${result.added_paths || 0} 条路径`;
        const skipped = (result.skipped_sites || 0) + (result.skipped_paths || 0);
        if (skipped > 0) {
            msg += `（跳过 ${result.skipped_sites || 0} 个已存在站点，${result.skipped_paths || 0} 条已存在路径）`;
        }
        this._showToast(msg, 'success');
    }

    _showErrorMessage(error) {
        this._showToast(error, 'error');
    }

    _showToast(message, type = 'info') {
        let toast = document.getElementById('spatial-select-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'spatial-select-toast';
            toast.className = 'spatial-select-toast';
            document.body.appendChild(toast);
        }

        toast.textContent = message;
        toast.className = `spatial-select-toast ${type}`;
        toast.style.display = 'block';

        setTimeout(() => {
            toast.style.display = 'none';
        }, 3000);
    }

    // ========================================
    // 几何计算辅助方法
    // ========================================

    _calculateDistance(point1, point2) {
        // 使用 Haversine 公式计算两点间距离 (米)
        const R = 6371000;
        const lat1 = point1[1] * Math.PI / 180;
        const lat2 = point2[1] * Math.PI / 180;
        const dLat = (point2[1] - point1[1]) * Math.PI / 180;
        const dLng = (point2[0] - point1[0]) * Math.PI / 180;

        const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        return R * c;
    }

    _createCirclePolygon(center, radiusMeters, segments = 64) {
        const coords = [];
        const lat = center[1];
        const lng = center[0];

        // 将米转换为度（近似）
        const latDelta = radiusMeters / 111320;
        const lngDelta = radiusMeters / (111320 * Math.cos(lat * Math.PI / 180));

        for (let i = 0; i <= segments; i++) {
            const angle = (i / segments) * 2 * Math.PI;
            const x = lng + lngDelta * Math.cos(angle);
            const y = lat + latDelta * Math.sin(angle);
            coords.push([x, y]);
        }

        return {
            type: 'Feature',
            geometry: {
                type: 'Polygon',
                coordinates: [coords]
            }
        };
    }

    _pointInPolygon(point, polygon) {
        // 射线法判断点是否在多边形内
        const x = point[0], y = point[1];
        let inside = false;

        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i][0], yi = polygon[i][1];
            const xj = polygon[j][0], yj = polygon[j][1];

            if (((yi > y) !== (yj > y)) &&
                (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
                inside = !inside;
            }
        }

        return inside;
    }

    // ========================================
    // 清理
    // ========================================

    _cleanup() {
        this._deactivate();

        // 移除图层和数据源
        [this.DRAW_LAYER_FILL, this.DRAW_LAYER_LINE, this.HIGHLIGHT_LAYER].forEach(id => {
            if (this.map.getLayer(id)) this.map.removeLayer(id);
        });

        [this.DRAW_SOURCE, this.HIGHLIGHT_SOURCE].forEach(id => {
            if (this.map.getSource(id)) this.map.removeSource(id);
        });

        // 移除 DOM 元素
        const tip = document.getElementById('spatial-select-tip');
        if (tip) tip.remove();

        const confirm = document.getElementById('spatial-select-confirm');
        if (confirm) confirm.remove();

        const toast = document.getElementById('spatial-select-toast');
        if (toast) toast.remove();
    }

}

// 导出到全局
window.SpatialSelectControl = SpatialSelectControl;

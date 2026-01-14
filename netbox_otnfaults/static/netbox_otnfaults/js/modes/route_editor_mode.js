/**
 * OTN线路设计器模式插件
 * 复用 OTNMapCore 地图核心，实现站点选择和路径绘制
 */

const RouteEditorModePlugin = {
    core: null,
    map: null,
    config: null,
    routeSnapperService: null,

    // 设计数据状态
    designData: {
        version: '1.0',
        name: '',
        description: '',
        sites: [],
        paths: [],
        metadata: {
            total_length_km: 0,
            path_count: 0,
            site_count: 0
        }
    },

    // 当前操作模式
    editMode: 'select', // 'select' | 'drag'

    // 站点计数器
    siteCounter: 0,

    // 拖拽状态
    dragState: {
        isDragging: false,
        siteId: null
    },

    // 撤销/重做历史
    history: [],
    historyIndex: -1,
    maxHistorySize: 50,

    /**
     * 初始化插件
     */
    init(core) {
        this.core = core;
        this.map = core.map;
        this.config = core.config;

        console.log('[RouteEditorMode] 初始化线路设计器');

        // 初始化路径吸附服务
        this.routeSnapperService = new window.RouteSnapperService();

        // 初始化图层
        this._initLayers();

        // 初始化交互
        this._initInteractions();

        // 初始化侧边栏 UI
        this._initSidebarUI();

        // 设置光标样式
        this.map.getCanvas().style.cursor = 'crosshair';

        // 尝试恢复草稿
        this._restoreFromLocalStorage();
    },

    /**
     * 初始化地图图层
     */
    _initLayers() {
        // 设计站点图层 - 数据源
        this.map.addSource('design-sites', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });

        // 设计路径图层 - 数据源
        this.map.addSource('design-paths', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });

        // 路径线图层
        this.map.addLayer({
            id: 'design-paths-line',
            type: 'line',
            source: 'design-paths',
            paint: {
                'line-color': '#3b82f6',
                'line-width': 4,
                'line-opacity': 0.8
            }
        });

        // 站点圆点图层
        this.map.addLayer({
            id: 'design-sites-circle',
            type: 'circle',
            source: 'design-sites',
            paint: {
                'circle-radius': 10,
                'circle-color': '#ef4444',
                'circle-stroke-color': '#ffffff',
                'circle-stroke-width': 3
            }
        });

        // 站点标签图层
        this.map.addLayer({
            id: 'design-sites-label',
            type: 'symbol',
            source: 'design-sites',
            layout: {
                'text-field': ['get', 'label'],
                'text-size': 14,
                'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
                'text-offset': [0, -1.8],
                'text-anchor': 'bottom'
            },
            paint: {
                'text-color': '#1f2937',
                'text-halo-color': '#ffffff',
                'text-halo-width': 2
            }
        });

        console.log('[RouteEditorMode] 图层初始化完成');
    },

    /**
     * 初始化交互事件
     */
    _initInteractions() {
        // 地图点击 - 添加站点
        this.map.on('click', (e) => {
            if (this.dragState.isDragging) return;
            if (this.editMode !== 'select') return;
            this._addSite(e.lngLat);
        });

        // 站点悬停效果
        this.map.on('mouseenter', 'design-sites-circle', () => {
            this.map.getCanvas().style.cursor = 'grab';
        });

        this.map.on('mouseleave', 'design-sites-circle', () => {
            if (!this.dragState.isDragging) {
                this.map.getCanvas().style.cursor = 'crosshair';
            }
        });

        // 站点拖拽 - 开始
        this.map.on('mousedown', 'design-sites-circle', (e) => {
            e.preventDefault();
            const features = e.features;
            if (!features || features.length === 0) return;

            const siteId = features[0].properties.id;
            this.dragState.isDragging = true;
            this.dragState.siteId = siteId;
            this.map.getCanvas().style.cursor = 'grabbing';

            // 保存当前状态用于撤销
            this._saveHistory();
        });

        // 站点拖拽 - 移动
        this.map.on('mousemove', (e) => {
            if (!this.dragState.isDragging) return;

            const site = this.designData.sites.find(s => s.id === this.dragState.siteId);
            if (site) {
                site.coordinates = [e.lngLat.lng, e.lngLat.lat];
                this._updateMapDisplay();
            }
        });

        // 站点拖拽 - 结束
        this.map.on('mouseup', async () => {
            if (!this.dragState.isDragging) return;

            this.dragState.isDragging = false;
            this.map.getCanvas().style.cursor = 'crosshair';

            // 重新计算相关路径
            await this._regeneratePaths();

            this.dragState.siteId = null;
        });

        // 键盘事件 - 撤销/重做
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'z') {
                e.preventDefault();
                this._undo();
            } else if (e.ctrlKey && e.key === 'y') {
                e.preventDefault();
                this._redo();
            }
        });
    },

    /**
     * 添加站点
     */
    _addSite(lngLat) {
        // 保存历史用于撤销
        this._saveHistory();

        this.siteCounter++;
        const label = String.fromCharCode(64 + this.siteCounter); // A, B, C...
        const siteId = `site_${Date.now()}`;

        const site = {
            id: siteId,
            name: `站点 ${label}`,
            label: label,
            coordinates: [lngLat.lng, lngLat.lat],
            properties: {}
        };

        this.designData.sites.push(site);

        // 如果有上一个站点，创建路径（异步）
        if (this.designData.sites.length > 1) {
            const prevSite = this.designData.sites[this.designData.sites.length - 2];
            this._addPathAsync(prevSite, site);
        }

        // 更新地图显示
        this._updateMapDisplay();

        // 更新侧边栏
        this._updateSidebar();

        // 保存到 localStorage
        this._saveToLocalStorage();

        console.log(`[RouteEditorMode] 添加站点 ${label}:`, lngLat);
    },

    /**
     * 添加路径（调用后端 API 计算高速公路路径）
     */
    async _addPathAsync(siteA, siteZ) {
        const pathId = `path_${Date.now()}`;

        // 调用路径吸附服务
        const waypoints = [
            { lng: siteA.coordinates[0], lat: siteA.coordinates[1] },
            { lng: siteZ.coordinates[0], lat: siteZ.coordinates[1] }
        ];

        console.log('[RouteEditorMode] 计算路径:', siteA.name, '->', siteZ.name);

        const result = await this.routeSnapperService.calculateRoute(waypoints);

        // 检查结果有效性
        if (!result || !result.route || !result.route.geometry) {
            console.error('[RouteEditorMode] 路径计算返回无效结果:', result);
            // 使用直线作为备选
            const fallbackGeometry = {
                type: 'LineString',
                coordinates: [siteA.coordinates, siteZ.coordinates]
            };
            const path = {
                id: pathId,
                name: `${siteA.name} - ${siteZ.name}`,
                site_a_id: siteA.id,
                site_z_id: siteZ.id,
                waypoints: [],
                geometry: fallbackGeometry,
                length_meters: this._calculateDistance(siteA.coordinates, siteZ.coordinates),
                is_highway: false,
                properties: {}
            };
            this.designData.paths.push(path);
            this._updateMetadata();
            this._updateMapDisplay();
            this._updateSidebar();
            return;
        }

        const path = {
            id: pathId,
            name: `${siteA.name} - ${siteZ.name}`,
            site_a_id: siteA.id,
            site_z_id: siteZ.id,
            waypoints: [],
            geometry: result.route.geometry,
            length_meters: result.route.length_meters,
            is_highway: !result.fallback,
            properties: {}
        };

        this.designData.paths.push(path);

        // 更新统计
        this._updateMetadata();

        // 更新地图和侧边栏
        this._updateMapDisplay();
        this._updateSidebar();

        if (result.fallback) {
            console.warn('[RouteEditorMode] 降级为直线连接:', result.error || result.message);
        }
    },

    /**
     * 计算两点间距离（米）
     */
    _calculateDistance(coord1, coord2) {
        const R = 6371000; // 地球半径（米）
        const lat1 = coord1[1] * Math.PI / 180;
        const lat2 = coord2[1] * Math.PI / 180;
        const deltaLat = (coord2[1] - coord1[1]) * Math.PI / 180;
        const deltaLng = (coord2[0] - coord1[0]) * Math.PI / 180;

        const a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
            Math.cos(lat1) * Math.cos(lat2) *
            Math.sin(deltaLng / 2) * Math.sin(deltaLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        return R * c;
    },

    /**
     * 更新统计信息
     */
    _updateMetadata() {
        const totalLength = this.designData.paths.reduce((sum, p) => sum + p.length_meters, 0);
        this.designData.metadata = {
            total_length_km: (totalLength / 1000).toFixed(2),
            path_count: this.designData.paths.length,
            site_count: this.designData.sites.length
        };
    },

    /**
     * 更新地图显示
     */
    _updateMapDisplay() {
        // 更新站点显示
        const sitesGeoJSON = {
            type: 'FeatureCollection',
            features: this.designData.sites.map(site => ({
                type: 'Feature',
                properties: { id: site.id, name: site.name, label: site.label },
                geometry: { type: 'Point', coordinates: site.coordinates }
            }))
        };
        this.map.getSource('design-sites').setData(sitesGeoJSON);

        // 更新路径显示
        const pathsGeoJSON = {
            type: 'FeatureCollection',
            features: this.designData.paths.map(path => ({
                type: 'Feature',
                properties: { id: path.id, name: path.name },
                geometry: path.geometry
            }))
        };
        this.map.getSource('design-paths').setData(pathsGeoJSON);
    },

    /**
     * 初始化侧边栏 UI
     */
    _initSidebarUI() {
        // 查找或创建侧边栏容器
        let sidebar = document.getElementById('route-editor-sidebar');
        if (!sidebar) {
            sidebar = document.createElement('div');
            sidebar.id = 'route-editor-sidebar';
            sidebar.className = 'route-editor-sidebar';
            sidebar.innerHTML = this._getSidebarHTML();
            document.body.appendChild(sidebar);
        }

        // 绑定按钮事件
        this._bindSidebarEvents();
    },

    /**
     * 获取侧边栏 HTML
     */
    _getSidebarHTML() {
        return `
      <div class="sidebar-header">
        <h3>设计信息</h3>
      </div>
      <div class="sidebar-content">
        <div class="form-group">
          <label>名称</label>
          <input type="text" id="design-name" placeholder="输入设计名称" class="form-control" />
        </div>
        <div class="form-group">
          <label>描述</label>
          <input type="text" id="design-desc" placeholder="输入描述" class="form-control" />
        </div>
        <hr />
        <div class="sites-section">
          <h4>站点列表</h4>
          <div id="sites-list" class="sites-list">
            <div class="empty-hint">点击地图添加站点</div>
          </div>
        </div>
        <hr />
        <div class="stats-section">
          <h4>统计信息</h4>
          <div class="stat-item">
            <span>站点数:</span>
            <span id="stat-sites">0</span>
          </div>
          <div class="stat-item">
            <span>路径数:</span>
            <span id="stat-paths">0</span>
          </div>
          <div class="stat-item">
            <span>总长度:</span>
            <span id="stat-length">0 km</span>
          </div>
        </div>
        <hr />
        <div class="actions-section">
          <div class="btn-row">
            <button id="btn-undo" class="btn btn-secondary btn-sm" title="撤销 (Ctrl+Z)">↩</button>
            <button id="btn-redo" class="btn btn-secondary btn-sm" title="重做 (Ctrl+Y)">↪</button>
          </div>
          <div class="btn-row">
            <button id="btn-import" class="btn btn-secondary btn-sm">导入 JSON</button>
            <button id="btn-export" class="btn btn-primary btn-sm">导出 JSON</button>
          </div>
          <button id="btn-clear" class="btn btn-danger btn-sm">清空设计</button>
        </div>
        <input type="file" id="import-file" accept=".json" style="display: none" />
      </div>
    `;
    },

    /**
     * 绑定侧边栏事件
     */
    _bindSidebarEvents() {
        // 导出按钮
        const btnExport = document.getElementById('btn-export');
        if (btnExport) {
            btnExport.addEventListener('click', () => this._exportJSON());
        }

        // 导入按钮
        const btnImport = document.getElementById('btn-import');
        const importFile = document.getElementById('import-file');
        if (btnImport && importFile) {
            btnImport.addEventListener('click', () => importFile.click());
            importFile.addEventListener('change', (e) => this._importJSON(e));
        }

        // 清空按钮
        const btnClear = document.getElementById('btn-clear');
        if (btnClear) {
            btnClear.addEventListener('click', () => this._clearDesign());
        }

        // 撤销按钮
        const btnUndo = document.getElementById('btn-undo');
        if (btnUndo) {
            btnUndo.addEventListener('click', () => this._undo());
        }

        // 重做按钮
        const btnRedo = document.getElementById('btn-redo');
        if (btnRedo) {
            btnRedo.addEventListener('click', () => this._redo());
        }

        // 名称输入
        const nameInput = document.getElementById('design-name');
        if (nameInput) {
            nameInput.addEventListener('input', (e) => {
                this.designData.name = e.target.value;
                this._saveToLocalStorage();
            });
        }

        // 描述输入
        const descInput = document.getElementById('design-desc');
        if (descInput) {
            descInput.addEventListener('input', (e) => {
                this.designData.description = e.target.value;
                this._saveToLocalStorage();
            });
        }
    },

    /**
     * 更新侧边栏显示
     */
    _updateSidebar() {
        // 更新站点列表
        const sitesList = document.getElementById('sites-list');
        if (sitesList) {
            if (this.designData.sites.length === 0) {
                sitesList.innerHTML = '<div class="empty-hint">点击地图添加站点</div>';
            } else {
                sitesList.innerHTML = this.designData.sites.map(site => `
          <div class="site-item" data-id="${site.id}">
            <span class="site-label">${site.label}</span>
            <span class="site-name">${site.name}</span>
            <button class="btn-delete" data-id="${site.id}">&times;</button>
          </div>
        `).join('');

                // 绑定删除事件
                sitesList.querySelectorAll('.btn-delete').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        this._deleteSite(btn.dataset.id);
                    });
                });
            }
        }

        // 更新统计
        document.getElementById('stat-sites').textContent = this.designData.metadata.site_count;
        document.getElementById('stat-paths').textContent = this.designData.metadata.path_count;
        document.getElementById('stat-length').textContent = `${this.designData.metadata.total_length_km} km`;
    },

    /**
     * 删除站点
     */
    _deleteSite(siteId) {
        const index = this.designData.sites.findIndex(s => s.id === siteId);
        if (index === -1) return;

        // 删除站点
        this.designData.sites.splice(index, 1);

        // 删除相关路径
        this.designData.paths = this.designData.paths.filter(
            p => p.site_a_id !== siteId && p.site_z_id !== siteId
        );

        // 重新生成路径（连接相邻站点）
        this._regeneratePaths();

        // 更新显示
        this._updateMetadata();
        this._updateMapDisplay();
        this._updateSidebar();
    },

    /**
     * 重新生成路径
     */
    async _regeneratePaths() {
        this.designData.paths = [];
        for (let i = 0; i < this.designData.sites.length - 1; i++) {
            await this._addPathAsync(this.designData.sites[i], this.designData.sites[i + 1]);
        }
    },

    /**
     * 导出 JSON
     */
    _exportJSON() {
        this.designData.name = document.getElementById('design-name')?.value || '未命名设计';
        this.designData.description = document.getElementById('design-desc')?.value || '';

        const jsonStr = JSON.stringify(this.designData, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.designData.name || 'design'}.json`;
        a.click();

        URL.revokeObjectURL(url);
        console.log('[RouteEditorMode] 导出 JSON:', this.designData);
    },

    /**
     * 清空设计
     */
    _clearDesign() {
        if (!confirm('确定要清空当前设计吗？')) return;

        this.designData = {
            version: '1.0',
            name: '',
            description: '',
            sites: [],
            paths: [],
            metadata: { total_length_km: 0, path_count: 0, site_count: 0 }
        };
        this.siteCounter = 0;

        // 清空输入框
        const nameInput = document.getElementById('design-name');
        const descInput = document.getElementById('design-desc');
        if (nameInput) nameInput.value = '';
        if (descInput) descInput.value = '';

        this._updateMapDisplay();
        this._updateSidebar();

        console.log('[RouteEditorMode] 设计已清空');
    },

    /**
     * 保存当前状态到历史
     */
    _saveHistory() {
        // 截断后续历史（如果当前不在最新位置）
        if (this.historyIndex < this.history.length - 1) {
            this.history = this.history.slice(0, this.historyIndex + 1);
        }

        // 深拷贝当前状态
        const snapshot = JSON.parse(JSON.stringify({
            sites: this.designData.sites,
            paths: this.designData.paths,
            siteCounter: this.siteCounter
        }));

        this.history.push(snapshot);
        this.historyIndex = this.history.length - 1;

        // 限制历史大小
        if (this.history.length > this.maxHistorySize) {
            this.history.shift();
            this.historyIndex--;
        }

        console.log(`[RouteEditorMode] 历史保存，当前索引: ${this.historyIndex}`);
    },

    /**
     * 撤销
     */
    _undo() {
        if (this.historyIndex <= 0) {
            console.log('[RouteEditorMode] 无法撤销，已到最早状态');
            return;
        }

        this.historyIndex--;
        this._restoreFromHistory();
        console.log(`[RouteEditorMode] 撤销，当前索引: ${this.historyIndex}`);
    },

    /**
     * 重做
     */
    _redo() {
        if (this.historyIndex >= this.history.length - 1) {
            console.log('[RouteEditorMode] 无法重做，已到最新状态');
            return;
        }

        this.historyIndex++;
        this._restoreFromHistory();
        console.log(`[RouteEditorMode] 重做，当前索引: ${this.historyIndex}`);
    },

    /**
     * 从历史恢复状态
     */
    _restoreFromHistory() {
        const snapshot = this.history[this.historyIndex];
        if (!snapshot) return;

        this.designData.sites = JSON.parse(JSON.stringify(snapshot.sites));
        this.designData.paths = JSON.parse(JSON.stringify(snapshot.paths));
        this.siteCounter = snapshot.siteCounter;

        this._updateMetadata();
        this._updateMapDisplay();
        this._updateSidebar();
        this._saveToLocalStorage();
    },

    /**
     * 导入 JSON 文件
     */
    _importJSON(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);

                // 验证数据结构
                if (!data.sites || !Array.isArray(data.sites)) {
                    alert('无效的设计文件格式');
                    return;
                }

                // 保存当前状态用于撤销
                this._saveHistory();

                // 恢复数据
                this.designData = {
                    version: data.version || '1.0',
                    name: data.name || '',
                    description: data.description || '',
                    sites: data.sites || [],
                    paths: data.paths || [],
                    metadata: data.metadata || { total_length_km: 0, path_count: 0, site_count: 0 }
                };

                // 恢复站点计数器
                this.siteCounter = this.designData.sites.length;

                // 更新输入框
                const nameInput = document.getElementById('design-name');
                const descInput = document.getElementById('design-desc');
                if (nameInput) nameInput.value = this.designData.name;
                if (descInput) descInput.value = this.designData.description;

                // 更新显示
                this._updateMetadata();
                this._updateMapDisplay();
                this._updateSidebar();
                this._saveToLocalStorage();

                console.log('[RouteEditorMode] 导入成功:', this.designData.name);
            } catch (err) {
                console.error('[RouteEditorMode] 导入失败:', err);
                alert('导入失败: ' + err.message);
            }
        };
        reader.readAsText(file);

        // 清空文件输入以便重复选择同一文件
        event.target.value = '';
    },

    /**
     * 保存到 localStorage
     */
    _saveToLocalStorage() {
        const key = 'otn_route_editor_draft';
        try {
            const data = {
                designData: this.designData,
                siteCounter: this.siteCounter,
                timestamp: Date.now()
            };
            localStorage.setItem(key, JSON.stringify(data));
        } catch (err) {
            console.warn('[RouteEditorMode] localStorage 保存失败:', err);
        }
    },

    /**
     * 从 localStorage 恢复
     */
    _restoreFromLocalStorage() {
        const key = 'otn_route_editor_draft';
        try {
            const saved = localStorage.getItem(key);
            if (!saved) return;

            const data = JSON.parse(saved);
            if (!data.designData || !data.designData.sites) return;

            // 恢复数据
            this.designData = data.designData;
            this.siteCounter = data.siteCounter || 0;

            // 更新输入框
            const nameInput = document.getElementById('design-name');
            const descInput = document.getElementById('design-desc');
            if (nameInput) nameInput.value = this.designData.name || '';
            if (descInput) descInput.value = this.designData.description || '';

            // 更新显示
            this._updateMetadata();
            this._updateMapDisplay();
            this._updateSidebar();

            console.log('[RouteEditorMode] 从草稿恢复成功');
        } catch (err) {
            console.warn('[RouteEditorMode] localStorage 恢复失败:', err);
        }
    }
};

// 注册插件
window.initOTNMap(RouteEditorModePlugin);

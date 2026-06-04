/**
 * 视图控制控件 (ViewControl)
 * 统一管理：
 * 1. 视图模式：智能 (Smart) / 故障点 (Points) / 热力图 (Heatmap)
 * 2. 时间范围：1周, 2周, 1月, 3月, 1年（滑动条）
 * 3. 故障类型筛选：光缆、电力、空调、设备、其他
 * 4. 基础图层开关
 */
class LayerToggleControl {
    constructor(options) {
        this.options = options || {};
        this.floatingMenu = this.options.floatingMenu === true;
        this.sections = Object.assign({
            viewMode: true,
            timeRange: true,
            categories: true,
            topology: true,
            cutover: false
        }, this.options.sections || {});
        if (this.options.topologyOnly === true) {
            this.sections = {
                viewMode: false,
                timeRange: false,
                categories: false,
                topology: true,
                cutover: false
            };
        }
        if (this.options.cutoverOnly === true) {
            this.sections = {
                viewMode: false,
                timeRange: false,
                categories: false,
                topology: false,
                cutover: true
            };
        }
        this.boundPositionMenu = () => this.positionMenu();
        this.boundDocumentClick = (event) => {
            if (this.container?.contains(event.target) || this.menu?.contains(event.target)) return;
            this.hideMenu();
        };

        // 默认状态
        this.currentMode = 'smart'; // 'smart' | 'points' | 'heatmap'
        this.currentTimeRange = '1week'; // Default to 1 week
        this.arcgisVisible = true; // 网络拓扑可见性
        this.pathGroupOverlaysUrl = this.options.pathGroupOverlaysUrl;
        this.enablePathGroupOverlays = this.options.enablePathGroupOverlays === true;
        this.pathGroupOverlays = null;
        this.pathGroupOverlayDetails = new Map();
        this.pathGroupOverlayLoading = false;
        this.selectedPathGroupIds = new Set();

        // 故障类型筛选（整合自 CategoryFilterControl），默认为新6大类+其它
        this.selectedCategories = ['fiber_break', 'ac_fault', 'fiber_degradation', 'fiber_jitter', 'device_fault', 'power_fault', 'other'];

        // 时间范围选项（用于滑动条）
        this.timeRangeOptions = [
            { label: '1周', value: '1week' },
            { label: '2周', value: '2weeks' },
            { label: '1月', value: '1month' },
            { label: '3月', value: '3months' },
            { label: '1年', value: '1year' }
        ];

        // 割接过滤默认状态
        this.showCutover = true; // 默认勾选显示割接计划
        this.cutoverTimeRange = 'all'; // 默认全部时间范围
        this.selectedCutoverStatuses = ['pending_implementation']; // 默认仅勾选“待实施”
    }

    onAdd(map) {
        this.map = map;
        this.container = document.createElement('div');
        this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group layer-toggle-control bg-body';
        if (this.options.controlClass) {
            this.container.classList.add(this.options.controlClass);
        }
        this.container.style.overflow = 'visible';

        // 主按钮图标
        this.button = document.createElement('button');
        this.button.type = 'button';
        this.button.className = 'maplibregl-ctrl-icon toggle-button bg-transparent';
        this.button.innerHTML = this.options.buttonIcon || window.mapBase.svgIcons.fault;
        this.button.title = this.options.title || '故障视图与时间设置';
        this.button.addEventListener('click', (event) => {
            event.stopPropagation();
            this.toggleMenu();
        });

        // Interaction: Hover to show, Leave to hide (with delay)

        // Show menu on button hover
        this.button.onmouseenter = (e) => {
            this.showMenu();
        };

        // Hide menu when mouse leaves container
        this.container.onmouseleave = (e) => {
            this.hideMenuWithDelay();
        };

        this.container.appendChild(this.button);
        return this.container;
    }

    onRemove() {
        this.hideMenu();
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
        this.map = undefined;
    }

    toggleMenu() {
        if (this.menu) {
            this.hideMenu();
            return;
        }
        this.showMenu();
    }

    showMenu() {
        if (this.hideTimer) {
            clearTimeout(this.hideTimer);
            this.hideTimer = null;
        }
        this.createMenu();
    }

    hideMenuWithDelay() {
        this.hideTimer = setTimeout(() => {
            this.hideMenu();
        }, 200); // 200ms delay
    }

    createMenu() {
        if (this.menu) return;

        const menu = document.createElement('div');
        menu.className = 'heatmap-time-range-menu view-control-menu card shadow bg-body p-2 border border-secondary-subtle';
        if (this.options.topologyOnly === true) {
            menu.classList.add('layer-display-menu');
        }
        menu.addEventListener('click', (event) => event.stopPropagation());

        // Ensure menu is appended to container so mouseleave works for both button and menu
        if (this.floatingMenu) {
            menu.classList.add('floating-menu');
            document.body.appendChild(menu);
        } else {
            this.container.appendChild(menu);
        }
        this.menu = menu;

        let hasSection = false;
        const addSectionDivider = () => {
            if (hasSection) {
                this.addDivider(menu);
            }
            hasSection = true;
        };

        if (this.sections.viewMode) {
            // 1. 视图模式选择（卡片式UI）
            addSectionDivider();
            this.addHeader(menu, '故障视图模式');
            const modeGroup = document.createElement('div');
            modeGroup.className = 'view-mode-cards';
            modeGroup.style.cssText = 'display: flex; gap: 8px; padding: 8px 12px;';

            const modes = [
                { value: 'smart', label: '智能', desc: '自动切换' },
                { value: 'points', label: '故障点', desc: '显示标记' },
                { value: 'heatmap', label: '热力图', desc: '密度分布' }
            ];

            modes.forEach(mode => {
                const card = this.createModeCard(mode.value, mode.label, mode.desc, this.currentMode === mode.value);
                card.onclick = (e) => {
                    e.stopPropagation();
                    // 更新所有卡片样式（移除选中状态）
                    modeGroup.querySelectorAll('.mode-card').forEach(c => {
                        c.classList.remove('active');
                    });
                    // 高亮选中的卡片
                    card.classList.add('active');
                    this.setMode(mode.value);
                };
                modeGroup.appendChild(card);
            });

            menu.appendChild(modeGroup);
        }

        if (this.sections.timeRange) {
            // 2. 时间范围选择（滑动条）
            addSectionDivider();
            this.addHeader(menu, '故障时间范围');
            this.createTimeSlider(menu);
        }

        if (this.sections.categories) {
            // 3. 故障类型筛选（整合自 CategoryFilterControl）
            addSectionDivider();
            this.addHeader(menu, '故障类型');
            this.createCategoryFilter(menu);
        }

        if (this.sections.topology) {
            // 4. 其他图层
            addSectionDivider();
            this.addHeader(menu, '其他图层');
            this.createCheckbox(menu, '全部站点与路径', this.arcgisVisible, (checked) => {
                this.arcgisVisible = checked;
                this.updateArcgisLayersVisibility();
            });

            if (this.enablePathGroupOverlays) {
                this.createPathGroupOverlaySelector(menu);
            }
        }

        if (this.sections.cutover) {
            addSectionDivider();
            this.addHeader(menu, '割接显示');
            this.createCheckbox(menu, '显示割接计划', this.showCutover, (checked) => {
                this.showCutover = checked;
                if (this.cutoverFilterPanel) {
                    this.cutoverFilterPanel.style.display = checked ? 'block' : 'none';
                }
                this.updateCutoverLayersVisibility();
                this.fetchCutoverDataAndRefresh();
            });

            // 割接过滤器子面板
            this.createCutoverFilterPanel(menu);
        }

        // 定位菜单
        if (this.floatingMenu) {
            this.positionMenu();
            window.addEventListener('resize', this.boundPositionMenu);
            setTimeout(() => document.addEventListener('click', this.boundDocumentClick), 0);
        } else {
            menu.style.top = '0';
            menu.style.left = '48px';
        }

        // Prevent menu click from propagating to map
        menu.onmouseenter = () => {
            if (this.hideTimer) clearTimeout(this.hideTimer);
        };
        menu.onmouseleave = () => this.hideMenuWithDelay();
    }

    positionMenu() {
        if (!this.menu || !this.container) return;

        const buttonRect = this.container.getBoundingClientRect();
        const viewportWidth = window.innerWidth || document.documentElement.clientWidth;
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
        const menuWidth = Math.min(360, Math.max(300, viewportWidth - 24));
        const rightOfMenu = viewportWidth - buttonRect.left + 8;
        let left = viewportWidth - rightOfMenu - menuWidth;
        left = Math.max(12, left);

        const top = Math.max(8, Math.min(buttonRect.top, viewportHeight - 120));
        this.menu.style.width = `${menuWidth}px`;
        this.menu.style.left = `${left}px`;
        this.menu.style.right = 'auto';
        this.menu.style.top = `${top}px`;
    }

    /* --- UI Helpers --- */
    addHeader(container, text) {
        const header = document.createElement('div');
        header.className = 'dropdown-header bg-body-tertiary text-body-secondary rounded-1 mb-1';
        header.style.padding = '4px 16px';
        header.style.fontSize = '12px';
        header.innerText = text;
        container.appendChild(header);
    }

    addDivider(container) {
        const divider = document.createElement('div');
        divider.style.borderTop = '1px solid var(--bs-border-color)';
        divider.style.margin = '4px 0';
        container.appendChild(divider);
    }

    /**
     * 创建模式选择卡片
     */
    createModeCard(value, label, desc, active) {
        const card = document.createElement('div');
        card.className = 'mode-card' + (active ? ' active' : '');
        card.dataset.mode = value;

        const labelEl = document.createElement('div');
        labelEl.className = 'mode-card-label';
        labelEl.innerText = label;

        const descEl = document.createElement('div');
        descEl.className = 'mode-card-desc';
        descEl.innerText = desc;

        card.appendChild(labelEl);
        card.appendChild(descEl);

        // Mouse events styling is now fully handled by CSS

        return card;
    }

    /**
     * 创建时间范围滑动条
     */
    createTimeSlider(container) {
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'padding: 8px 16px 16px 16px;';

        // 滑动条容器
        const sliderContainer = document.createElement('div');
        sliderContainer.style.cssText = 'position: relative;';

        // 范围输入
        const slider = document.createElement('input');
        slider.type = 'range';
        slider.min = '0';
        slider.max = String(this.timeRangeOptions.length - 1);
        slider.value = String(this.timeRangeOptions.findIndex(opt => opt.value === this.currentTimeRange));
        slider.className = 'time-range-slider';
        slider.style.display = 'block';
        // 动态设置初始渐变背景
        const initialPercent = (parseInt(slider.value) / (this.timeRangeOptions.length - 1)) * 100;
        const initialGradient = `linear-gradient(to right, #0d6efd 0%, #0d6efd ${initialPercent}%, transparent ${initialPercent}%, transparent 100%)`;
        slider.style.setProperty('background-image', initialGradient, 'important');
        slider.style.setProperty('background-color', 'var(--slider-track, #6b7280)', 'important');

        // 刻度标签容器
        const ticksContainer = document.createElement('div');
        ticksContainer.style.cssText = `
            display: flex;
            justify-content: space-between;
            margin-top: 6px;
            font-size: 10px;
            color: var(--bs-secondary-color);
        `;

        this.timeRangeOptions.forEach((opt, index) => {
            const tick = document.createElement('span');
            tick.innerText = opt.label;
            tick.style.cssText = `
                flex: 1;
                text-align: center;
                cursor: pointer;
                transition: color 0.15s;
            `;
            // 高亮当前选中
            if (opt.value === this.currentTimeRange) {
                tick.style.color = 'var(--bs-link-color, #0d6efd)';
                tick.style.fontWeight = '600';
            }
            tick.onclick = (e) => {
                e.stopPropagation();
                slider.value = String(index);
                this.handleSliderChange(slider, ticksContainer);
            };
            ticksContainer.appendChild(tick);
        });

        // 滑动条变化事件
        slider.oninput = () => {
            this.handleSliderChange(slider, ticksContainer);
        };

        sliderContainer.appendChild(slider);
        wrapper.appendChild(sliderContainer);
        wrapper.appendChild(ticksContainer);
        container.appendChild(wrapper);

        // 保存引用以便更新
        this.timeSlider = slider;
        this.ticksContainer = ticksContainer;
    }

    /**
     * 处理滑动条变化
     */
    handleSliderChange(slider, ticksContainer) {
        const index = parseInt(slider.value);
        const selectedOption = this.timeRangeOptions[index];

        // 更新滑动条背景渐变
        const percent = (index / (this.timeRangeOptions.length - 1)) * 100;
        const gradient = `linear-gradient(to right, #0d6efd 0%, #0d6efd ${percent}%, transparent ${percent}%, transparent 100%)`;
        slider.style.setProperty('background-image', gradient, 'important');
        slider.style.setProperty('background-color', 'var(--slider-track, #6b7280)', 'important');

        // 更新刻度标签高亮
        const ticks = ticksContainer.querySelectorAll('span');
        ticks.forEach((tick, i) => {
            if (i === index) {
                tick.style.color = 'var(--bs-link-color, #0d6efd)';
                tick.style.fontWeight = '600';
            } else {
                tick.style.color = 'var(--bs-secondary-color)';
                tick.style.fontWeight = 'normal';
            }
        });

        // 设置时间范围
        this.setTimeRange(selectedOption.value);
    }

    /**
     * 创建故障类型筛选区域
     */
    createCategoryFilter(container) {
        const wrapper = document.createElement('div');
        wrapper.className = 'category-filter-wrapper p-2';

        // 全选复选框
        const allItem = document.createElement('label');
        allItem.className = 'd-flex align-items-center mb-2';

        const allCheckbox = document.createElement('input');
        allCheckbox.type = 'checkbox';
        allCheckbox.checked = this.selectedCategories.length >= 7;
        allCheckbox.className = 'form-check-input mt-0';
        allCheckbox.id = 'layer-cat-all';

        const allLabel = document.createElement('span');
        allLabel.innerText = '全选';
        allLabel.style.fontWeight = '500';

        allItem.appendChild(allCheckbox);
        allItem.appendChild(allLabel);

        allItem.onclick = (e) => {
            e.stopPropagation();
            if (e.target !== allCheckbox) allCheckbox.checked = !allCheckbox.checked;
            this.toggleAllCategories(allCheckbox.checked);
        };

        wrapper.appendChild(allItem);

        // 分类网格（2列布局）
        const grid = document.createElement('div');
        grid.className = 'category-grid';

        const categories = [
            { key: 'fiber_break', name: window.FAULT_CATEGORY_NAMES?.fiber_break || '光缆中断', color: window.FAULT_CATEGORY_COLORS?.fiber_break || '#dc3545' },
            { key: 'ac_fault', name: window.FAULT_CATEGORY_NAMES?.ac_fault || '空调故障', color: window.FAULT_CATEGORY_COLORS?.ac_fault || '#0d6efd' },
            { key: 'fiber_degradation', name: window.FAULT_CATEGORY_NAMES?.fiber_degradation || '光缆劣化', color: window.FAULT_CATEGORY_COLORS?.fiber_degradation || '#f5a623' },
            { key: 'fiber_jitter', name: window.FAULT_CATEGORY_NAMES?.fiber_jitter || '光缆抖动', color: window.FAULT_CATEGORY_COLORS?.fiber_jitter || '#ffc107' },
            { key: 'device_fault', name: window.FAULT_CATEGORY_NAMES?.device_fault || '设备故障', color: window.FAULT_CATEGORY_COLORS?.device_fault || '#d63384' },
            { key: 'power_fault', name: window.FAULT_CATEGORY_NAMES?.power_fault || '供电故障', color: window.FAULT_CATEGORY_COLORS?.power_fault || '#6f42c1' },
            { key: 'other', name: window.FAULT_CATEGORY_NAMES?.other || '其他', color: window.FAULT_CATEGORY_COLORS?.other || '#6c757d' }
        ];

        categories.forEach(cat => {
            const item = document.createElement('label');
            item.className = 'category-item d-flex align-items-center';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = this.selectedCategories.includes(cat.key);
            checkbox.className = 'form-check-input mt-0';
            checkbox.dataset.category = cat.key;

            const label = document.createElement('span');
            label.innerText = cat.name;

            item.appendChild(checkbox);
            item.appendChild(label);

            item.onclick = (e) => {
                e.stopPropagation();
                if (e.target !== checkbox) checkbox.checked = !checkbox.checked;
                this.toggleCategory(cat.key, checkbox.checked);

                // 更新全选状态
                const allChecked = this.selectedCategories.length >= categories.length;
                allCheckbox.checked = allChecked;
            };

            grid.appendChild(item);
        });

        wrapper.appendChild(grid);
        container.appendChild(wrapper);

        // 保存引用
        this.categoryWrapper = wrapper;
        this.allCategoryCheckbox = allCheckbox;
    }

    createCheckbox(container, label, checked, onChange) {
        const item = document.createElement('div');
        item.className = 'dropdown-item d-flex align-items-center gap-2';
        item.style.cursor = 'pointer';

        item.innerHTML = `
            <input type="checkbox" class="form-check-input mt-0" ${checked ? 'checked' : ''} style="pointer-events: none;">
            <span class="ms-1">${label}</span>
        `;

        item.onclick = (e) => {
            e.stopPropagation();
            const input = item.querySelector('input');
            input.checked = !input.checked;
            onChange(input.checked);
        };

        container.appendChild(item);
    }

    createPathGroupOverlaySelector(container) {
        const wrapper = document.createElement('div');
        wrapper.className = 'path-group-overlay-selector px-2 pb-2';
        wrapper.style.cssText = 'max-height: 220px; overflow-y: auto;';
        container.appendChild(wrapper);

        if (!this.pathGroupOverlaysUrl) {
            wrapper.innerHTML = '<div class="text-muted small px-2 py-1">路径组数据不可用</div>';
            return;
        }

        if (this.pathGroupOverlays) {
            this.renderPathGroupOverlayOptions(wrapper);
            return;
        }

        wrapper.innerHTML = '<div class="text-muted small px-2 py-1">正在加载路径组...</div>';
        if (this.pathGroupOverlayLoading) return;

        this.pathGroupOverlayLoading = true;
        fetch(this.pathGroupOverlaysUrl, { credentials: 'same-origin' })
            .then(response => response.json())
            .then(data => {
                this.pathGroupOverlays = data.results || [];
                this.pathGroupOverlayLoading = false;
                if (this.menu && wrapper.isConnected) {
                    this.renderPathGroupOverlayOptions(wrapper);
                }
            })
            .catch(() => {
                this.pathGroupOverlayLoading = false;
                if (wrapper.isConnected) {
                    wrapper.innerHTML = '<div class="text-danger small px-2 py-1">路径组加载失败</div>';
                }
            });
    }

    renderPathGroupOverlayOptions(container) {
        container.innerHTML = '';

        if (!this.pathGroupOverlays || this.pathGroupOverlays.length === 0) {
            container.innerHTML = '<div class="text-muted small px-2 py-1">暂无路径组</div>';
            return;
        }

        const title = document.createElement('div');
        title.className = 'text-muted small px-2 py-1';
        title.innerText = '路径组';
        container.appendChild(title);

        this.pathGroupOverlays.forEach(group => {
            const item = document.createElement('label');
            item.className = 'dropdown-item d-flex align-items-center gap-2';
            item.style.cursor = 'pointer';

            const input = document.createElement('input');
            input.type = 'checkbox';
            input.className = 'form-check-input mt-0';
            input.checked = this.selectedPathGroupIds.has(group.id);
            input.style.pointerEvents = 'none';

            const label = document.createElement('span');
            label.className = 'ms-1 text-truncate';
            const counts = [];
            if (Number.isFinite(group.path_count)) counts.push(`${group.path_count}路`);
            if (Number.isFinite(group.site_count)) counts.push(`${group.site_count}站`);
            label.innerText = counts.length ? `${group.name} (${counts.join('/')})` : group.name;

            item.appendChild(input);
            item.appendChild(label);
            item.onclick = (e) => {
                e.stopPropagation();
                input.checked = !input.checked;
                this.togglePathGroupOverlay(group.id, input.checked);
            };

            container.appendChild(item);
        });
    }

    async togglePathGroupOverlay(groupId, checked) {
        if (checked) {
            this.selectedPathGroupIds.add(groupId);
        } else {
            this.selectedPathGroupIds.delete(groupId);
        }

        const group = (this.pathGroupOverlays || []).find(item => item.id === groupId);
        if (!group || !this.map) return;

        this.ensurePathGroupOverlayLayers();
        if (checked) {
            await this.loadPathGroupOverlayDetail(group);
        }
        this.refreshPathGroupOverlaySources();
        this.setPathGroupOverlayVisibility(this.selectedPathGroupIds.size > 0);
        if (checked) {
            this.fitSelectedPathGroupOverlays();
        }
    }

    async loadPathGroupOverlayDetail(group) {
        const existing = this.pathGroupOverlayDetails.get(group.id);
        if (existing) {
            return existing;
        }

        const response = await fetch(group.detail_url, { credentials: 'same-origin' });
        if (!response.ok) {
            throw new Error(`Failed to load path group overlay ${group.id}: ${response.status}`);
        }
        const detail = await response.json();
        this.pathGroupOverlayDetails.set(group.id, detail);
        return detail;
    }

    ensurePathGroupOverlayLayers() {
        const pathSourceId = 'path-group-overlay-paths';
        const siteSourceId = 'path-group-overlay-sites';
        const beforeLayerId = this.getPathGroupOverlayBeforeLayerId();

        if (!this.map.getSource(pathSourceId)) {
            this.map.addSource(pathSourceId, {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: []
                }
            });
        }

        if (!this.map.getSource(siteSourceId)) {
            this.map.addSource(siteSourceId, {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: []
                }
            });
        }

        if (!this.map.getLayer('path-group-overlay-paths-outline')) {
            this.map.addLayer({
                id: 'path-group-overlay-paths-outline',
                type: 'line',
                source: pathSourceId,
                paint: {
                    "line-color": "#FFD700",
                    "line-width": ["interpolate", ["linear"], ["zoom"], 3, 2, 6, 3, 10, 4],
                    "line-opacity": 0.8
                },
                layout: { visibility: 'none' }
            }, beforeLayerId);
        }

        if (!this.map.getLayer('path-group-overlay-paths')) {
            this.map.addLayer({
                id: 'path-group-overlay-paths',
                type: 'line',
                source: pathSourceId,
                paint: {
                    "line-color": "#FFD700",
                    "line-width": ["interpolate", ["linear"], ["zoom"], 3, 1.5, 6, 2, 10, 3],
                    "line-opacity": 0.9
                },
                layout: { visibility: 'none' }
            }, beforeLayerId);
        }

        if (!this.map.getLayer('path-group-overlay-sites-glow')) {
            this.map.addLayer({
                id: 'path-group-overlay-sites-glow',
                type: 'circle',
                source: siteSourceId,
                paint: {
                    "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 8, 6, 10, 10, 12],
                    "circle-color": ["get", "color"],
                    "circle-opacity": 0.4,
                    "circle-blur": 0.5
                },
                layout: { visibility: 'none' }
            }, beforeLayerId);
        }

        if (!this.map.getLayer('path-group-overlay-sites')) {
            this.map.addLayer({
                id: 'path-group-overlay-sites',
                type: 'circle',
                source: siteSourceId,
                paint: {
                    "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 5, 6, 6, 10, 8],
                    "circle-color": ["get", "color"],
                    "circle-opacity": 1,
                    "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 3, 1.5, 6, 1.5, 10, 2],
                    "circle-stroke-color": "#FFFFFF"
                },
                layout: { visibility: 'none' }
            }, beforeLayerId);
        }

        const labelLayerId = 'path-group-overlay-site-labels';
        if (!this.map.getLayer(labelLayerId)) {
            this.map.addLayer({
                id: labelLayerId,
                type: 'symbol',
                source: siteSourceId,
                layout: {
                    "text-field": ["get", "name"],
                    "text-size": 11,
                    "text-offset": [0, 1.0],
                    "text-anchor": "top",
                    "text-allow-overlap": false,
                    visibility: 'none'
                },
                paint: {
                    "text-color": "#333333",
                    "text-halo-color": "#ffffff",
                    "text-halo-width": 1.5
                }
            }, beforeLayerId);
        }
    }

    getPathGroupOverlayBeforeLayerId() {
        const candidates = [
            'fault-points-layer',
            'netbox-sites-labels',
            'netbox-sites-layer'
        ];
        return candidates.find(id => this.map.getLayer(id));
    }

    raisePathGroupOverlayLayers() {
        const beforeLayerId = this.getPathGroupOverlayBeforeLayerId();
        const layerIds = [
            'path-group-overlay-paths-outline',
            'path-group-overlay-paths',
            'path-group-overlay-sites-glow',
            'path-group-overlay-sites',
            'path-group-overlay-site-labels'
        ];

        layerIds.forEach(id => {
            if (this.map.getLayer(id)) {
                this.map.moveLayer(id, beforeLayerId);
            }
        });
    }

    setPathGroupOverlayVisibility(visible) {
        this.raisePathGroupOverlayLayers();
        const visibility = visible ? 'visible' : 'none';
        const layerIds = [
            'path-group-overlay-paths-outline',
            'path-group-overlay-paths',
            'path-group-overlay-sites-glow',
            'path-group-overlay-sites',
            'path-group-overlay-site-labels'
        ];

        layerIds.forEach(id => {
            if (this.map.getLayer(id)) {
                this.map.setLayoutProperty(id, 'visibility', visibility);
            }
        });
    }

    refreshPathGroupOverlaySources() {
        if (!this.map) return;

        const pathFeatures = [];
        const siteFeatures = [];
        this.selectedPathGroupIds.forEach(groupId => {
            const detail = this.pathGroupOverlayDetails.get(groupId);
            if (!detail) return;
            pathFeatures.push(...(detail.paths || []));
            siteFeatures.push(...(detail.sites || []));
        });

        const pathSource = this.map.getSource('path-group-overlay-paths');
        if (pathSource) {
            pathSource.setData({ type: 'FeatureCollection', features: pathFeatures });
        }

        const siteSource = this.map.getSource('path-group-overlay-sites');
        if (siteSource) {
            siteSource.setData({ type: 'FeatureCollection', features: siteFeatures });
        }
    }

    fitSelectedPathGroupOverlays() {
        if (typeof maplibregl === 'undefined' || !this.map || !this.selectedPathGroupIds.size) {
            return;
        }

        const bounds = new maplibregl.LngLatBounds();
        this.selectedPathGroupIds.forEach(groupId => {
            const detail = this.pathGroupOverlayDetails.get(groupId);
            if (!detail) return;
            if (this._extendOverlayBoundsWithBbox(bounds, detail.bbox)) {
                return;
            }
            (detail.paths || []).forEach(feature => {
                if (feature.geometry) {
                    this._extendOverlayBoundsWithGeometry(bounds, feature.geometry);
                }
            });

            (detail.sites || []).forEach(feature => {
                const coordinates = feature.geometry?.coordinates;
                if (Array.isArray(coordinates) && coordinates.length >= 2) {
                    bounds.extend(coordinates);
                }
            });
        });

        if (!bounds.isEmpty()) {
            this.map.fitBounds(bounds, { padding: 80, maxZoom: 12, duration: 500 });
        }
    }

    _extendOverlayBoundsWithBbox(bounds, bbox) {
        if (!Array.isArray(bbox) || bbox.length !== 4) {
            return false;
        }
        bounds.extend([bbox[0], bbox[1]]);
        bounds.extend([bbox[2], bbox[3]]);
        return true;
    }

    _extendOverlayBoundsWithGeometry(bounds, geometry) {
        if (!geometry || !Array.isArray(geometry.coordinates)) {
            return;
        }

        const extendCoordinates = (coordinates) => {
            if (!Array.isArray(coordinates)) {
                return;
            }
            if (
                coordinates.length >= 2
                && typeof coordinates[0] === 'number'
                && typeof coordinates[1] === 'number'
            ) {
                bounds.extend(coordinates);
                return;
            }
            coordinates.forEach(item => extendCoordinates(item));
        };

        extendCoordinates(geometry.coordinates);
    }

    getPathGroupOverlayDebug() {
        const groups = this.pathGroupOverlays || [];
        return groups.map(group => {
            const detail = this.pathGroupOverlayDetails.get(group.id) || {};
            const layerIds = [
                'path-group-overlay-paths-outline',
                'path-group-overlay-paths',
                'path-group-overlay-sites-glow',
                'path-group-overlay-sites',
                'path-group-overlay-site-labels'
            ];

            return {
                id: group.id,
                name: group.name,
                selected: this.selectedPathGroupIds.has(group.id),
                pathFeatureCount: (detail.paths || []).length,
                siteFeatureCount: (detail.sites || []).length,
                sourceExists: {
                    paths: Boolean(this.map && this.map.getSource('path-group-overlay-paths')),
                    sites: Boolean(this.map && this.map.getSource('path-group-overlay-sites'))
                },
                layers: layerIds.map(id => ({
                    id,
                    exists: Boolean(this.map && this.map.getLayer(id)),
                    visibility: this.map && this.map.getLayer(id)
                        ? this.map.getLayoutProperty(id, 'visibility')
                        : null
                }))
            };
        });
    }

    hideMenu() {
        if (this.menu) {
            document.removeEventListener('click', this.boundDocumentClick);
            window.removeEventListener('resize', this.boundPositionMenu);
            if (this.menu.parentNode) {
                this.menu.parentNode.removeChild(this.menu);
            }
            this.menu = null;
        }
    }

    /* --- Logic --- */

    setMode(mode) {
        if (this.currentMode === mode) return;
        this.currentMode = mode;
        this.triggerGlobalUpdate();
    }

    setTimeRange(range) {
        if (this.currentTimeRange === range) return;
        this.currentTimeRange = range;
        this.triggerGlobalUpdate();
    }

    /**
     * 切换单个故障类型
     */
    toggleCategory(cat, checked) {
        if (checked) {
            if (!this.selectedCategories.includes(cat)) {
                this.selectedCategories.push(cat);
            }
        } else {
            this.selectedCategories = this.selectedCategories.filter(c => c !== cat);
        }
        this.triggerGlobalUpdate();
    }

    /**
     * 全选/反选故障类型
     */
    toggleAllCategories(checked) {
        // 更新所有复选框
        if (this.categoryWrapper) {
            const checkboxes = this.categoryWrapper.querySelectorAll('input[data-category]');
            checkboxes.forEach(cb => cb.checked = checked);
        }

        if (checked) {
            this.selectedCategories = ['fiber_break', 'ac_fault', 'fiber_degradation', 'fiber_jitter', 'device_fault', 'power_fault', 'other'];
        } else {
            this.selectedCategories = [];
        }
        this.triggerGlobalUpdate();
    }

    /**
     * 获取选中的故障类型列表
     */
    getSelectedCategories() {
        return this.selectedCategories;
    }

    triggerGlobalUpdate() {
        // 触发全局更新逻辑 (在 otnfault_map_app.js 中定义)
        if (window.updateMapState) {
            window.updateMapState();
        } else {
            console.warn('window.updateMapState is not defined');
        }
    }

    /**
     * 获取当前有效的显示模式
     * 在智能模式下，根据时间范围和缩放级别自动选择
     */
    getEffectiveMode() {
        if (this.currentMode !== 'smart') {
            return this.currentMode;
        }

        const zoom = this.map ? this.map.getZoom() : 0;

        if (zoom > 7) {
            return 'points';
        }

        if (this.currentTimeRange === '1week' || this.currentTimeRange === '2weeks') {
            return 'points';
        }

        return 'heatmap';
    }

    updateArcgisLayersVisibility() {
        if (!this.map) return;
        const visibility = this.arcgisVisible ? 'visible' : 'none';

        const layers = [
            'otn-paths-layer',
            'otn-paths-highlight-layer',
            'otn-paths-highlight-outline',
            'otn-paths-labels',
            'netbox-sites-layer',
            'netbox-sites-labels'
        ];

        layers.forEach(id => {
            if (this.map.getLayer(id)) {
                this.map.setLayoutProperty(id, 'visibility', visibility);
            }
        });
    }

    createCutoverFilterPanel(container) {
        const panel = document.createElement('div');
        panel.className = 'cutover-filter-panel';
        panel.style.cssText = `
            margin-left: 20px;
            padding: 8px 12px;
            margin-top: 4px;
            margin-bottom: 8px;
            border-left: 2px solid var(--bs-primary, #0d6efd);
            background-color: var(--bs-tertiary-bg, rgba(0,0,0,0.02));
            border-radius: 0 6px 6px 0;
            display: ${this.showCutover ? 'block' : 'none'};
            transition: all 0.25s ease-in-out;
        `;
        this.cutoverFilterPanel = panel;

        // 1. 时间范围下拉菜单
        const selectWrapper = document.createElement('div');
        selectWrapper.className = 'mb-2';
        selectWrapper.innerHTML = `
            <div class="text-muted small mb-1" style="font-size: 10px; font-weight: 600;">割接时间范围</div>
        `;
        const select = document.createElement('select');
        select.className = 'form-select form-select-sm';
        select.style.fontSize = '12px';
        select.style.padding = '2px 8px';
        select.innerHTML = `
            <option value="all">全部时间范围</option>
            <option value="24h">未来 24 小时</option>
            <option value="7d">未来 7 天</option>
            <option value="30d">未来 30 天</option>
            <option value="past30d">过去 30 天</option>
        `;
        select.value = this.cutoverTimeRange;
        select.onchange = (e) => {
            this.cutoverTimeRange = e.target.value;
            this.fetchCutoverDataAndRefresh();
        };
        selectWrapper.appendChild(select);
        panel.appendChild(selectWrapper);

        // 2. 状态多选
        const statusWrapper = document.createElement('div');
        statusWrapper.innerHTML = `
            <div class="text-muted small mb-1" style="font-size: 10px; font-weight: 600;">割接状态</div>
        `;
        
        const grid = document.createElement('div');
        grid.style.cssText = `
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4px 8px;
        `;

        const statuses = [
            { key: 'applying', name: '申请中', color: '#0d6efd' },
            { key: 'pending_implementation', name: '待实施', color: '#fd7e14' },
            { key: 'completed', name: '已完成', color: '#198754' },
            { key: 'cancelled', name: '被取消', color: '#6c757d' }
        ];

        statuses.forEach(status => {
            const item = document.createElement('label');
            item.className = 'd-flex align-items-center mb-0';
            item.style.cssText = 'cursor: pointer; font-size: 12px; padding: 2px 0; user-select: none;';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'form-check-input mt-0 me-1';
            checkbox.style.width = '13px';
            checkbox.style.height = '13px';
            checkbox.checked = this.selectedCutoverStatuses.includes(status.key);
            
            const dot = document.createElement('span');
            dot.style.cssText = `
                display: inline-block;
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background-color: ${status.color};
                margin-right: 4px;
                flex-shrink: 0;
            `;
            
            const labelText = document.createElement('span');
            labelText.innerText = status.name;
            labelText.style.fontSize = '11px';
            
            item.appendChild(checkbox);
            item.appendChild(dot);
            item.appendChild(labelText);
            
            item.onclick = (e) => {
                e.stopPropagation();
                if (e.target !== checkbox) checkbox.checked = !checkbox.checked;
                
                if (checkbox.checked) {
                    if (!this.selectedCutoverStatuses.includes(status.key)) {
                        this.selectedCutoverStatuses.push(status.key);
                    }
                } else {
                    this.selectedCutoverStatuses = this.selectedCutoverStatuses.filter(s => s !== status.key);
                }
                
                this.fetchCutoverDataAndRefresh();
            };
            
            grid.appendChild(item);
        });

        statusWrapper.appendChild(grid);
        panel.appendChild(statusWrapper);
        container.appendChild(panel);
    }

    fetchCutoverDataAndRefresh() {
        const config = window.OTNFaultMapConfig || (typeof FaultModePlugin !== 'undefined' ? FaultModePlugin.config : null);
        if (!config || !config.mapDataUrl) return;

        const url = new URL(config.mapDataUrl, window.location.origin);
        url.searchParams.append('mode', 'fault');

        this.selectedCutoverStatuses.forEach(status => {
            url.searchParams.append('cutover_status', status);
        });
        url.searchParams.append('cutover_time_range', this.cutoverTimeRange);

        fetch(url.toString(), { credentials: 'same-origin' })
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                return res.json();
            })
            .then(data => {
                if (config) {
                    config.cutoverData = data.cutover_data || [];
                }
                if (typeof FaultModePlugin !== 'undefined') {
                    FaultModePlugin.cutoverData = data.cutover_data || [];
                }
                this.triggerGlobalUpdate();
            })
            .catch(err => {
                console.error('[LayerToggleControl] 获取割接数据失败:', err);
            });
    }

    updateCutoverLayersVisibility() {
        if (!this.map) return;
        const visibility = this.showCutover ? 'visible' : 'none';
        if (this.map.getLayer('cutover-points-layer')) {
            this.map.setLayoutProperty('cutover-points-layer', 'visibility', visibility);
        }
    }
}

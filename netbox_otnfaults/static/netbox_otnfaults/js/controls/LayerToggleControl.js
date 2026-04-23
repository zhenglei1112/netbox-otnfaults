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
        this.sections = Object.assign({
            viewMode: true,
            timeRange: true,
            categories: true,
            topology: true
        }, this.options.sections || {});

        // 默认状态
        this.currentMode = 'smart'; // 'smart' | 'points' | 'heatmap'
        this.currentTimeRange = '1week'; // Default to 1 week
        this.arcgisVisible = true; // 网络拓扑可见性

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
    }

    onAdd(map) {
        this.map = map;
        this.container = document.createElement('div');
        this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group layer-toggle-control bg-body';
        this.container.style.overflow = 'visible';

        // 主按钮图标
        this.button = document.createElement('button');
        this.button.className = 'maplibregl-ctrl-icon toggle-button bg-transparent';
        this.button.innerHTML = window.mapBase.svgIcons.filter;
        this.button.title = this.options.title || '视图与时间设置';

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
        if (this.menu && this.menu.parentNode) {
            this.menu.parentNode.removeChild(this.menu);
        }
        this.container.parentNode.removeChild(this.container);
        this.map = undefined;
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
            if (this.menu) {
                this.container.removeChild(this.menu);
                this.menu = null;
            }
        }, 200); // 200ms delay
    }

    createMenu() {
        if (this.menu) return;

        const menu = document.createElement('div');
        menu.className = 'heatmap-time-range-menu view-control-menu card shadow bg-body p-2 border border-secondary-subtle';

        // Ensure menu is appended to container so mouseleave works for both button and menu
        this.container.appendChild(menu);
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
            this.addHeader(menu, '视图模式');
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
            this.addHeader(menu, '时间范围');
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
            this.createCheckbox(menu, '显示网络拓扑', this.arcgisVisible, (checked) => {
                this.arcgisVisible = checked;
                this.updateArcgisLayersVisibility();
            });
        }

        // 定位菜单
        menu.style.top = '40px';
        menu.style.left = '0';

        // Prevent menu click from propagating to map
        menu.onmouseenter = () => {
            if (this.hideTimer) clearTimeout(this.hideTimer);
        };
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

    hideMenu() {
        if (this.menu) {
            document.removeEventListener('click', this.closeHandler);
            this.container.removeChild(this.menu);
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
}

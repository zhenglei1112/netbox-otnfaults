/**
 * 视图控制控件 (ViewControl)
 * 统一管理：
 * 1. 视图模式：智能 (Smart) / 故障点 (Points) / 热力图 (Heatmap)
 * 2. 时间范围：1周, 2周, 1月, 3月, 1年
 * 3. 基础图层开关
 */
class LayerToggleControl {
    constructor(options) {
        this.options = options || {};
        
        // 默认状态
        this.currentMode = 'smart'; // 'smart' | 'points' | 'heatmap'
        this.currentTimeRange = '1week'; // Default to 1 week as requested
        this.arcgisVisible = true; // 网络拓扑可见性
    }

    onAdd(map) {
        this.map = map;
        this.container = document.createElement('div');
        this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group layer-toggle-control';
        
        // 主按钮图标
        this.button = document.createElement('button');
        this.button.className = 'maplibregl-ctrl-icon toggle-button';
        this.button.innerHTML = window.mapBase.svgIcons.filter;
        this.button.title = '视图与时间设置';
        
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
        this.menu.style.display = 'block';
    }

    hideMenuWithDelay() {
        this.hideTimer = setTimeout(() => {
            if (this.menu) {
                this.menu.style.display = 'none';
            }
        }, 200); // 200ms delay
    }

    createMenu() {
        if (this.menu) return;

        const menu = document.createElement('div');
        menu.className = 'heatmap-time-range-menu view-control-menu'; 
        
        // Ensure menu is appended to container so mouseleave works for both button and menu
        // But maplibregl controls often overflow, so we must be careful with Z-index
        this.container.appendChild(menu);
        this.menu = menu;

        // 1. 视图模式选择（卡片式UI）
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
                    c.style.borderColor = '#dee2e6';
                    c.style.backgroundColor = '#fff';
                    // 重置标题颜色
                    const label = c.querySelector('.mode-card-label');
                    if (label) label.style.color = '#212529';
                });
                // 高亮选中的卡片
                card.classList.add('active');
                card.style.borderColor = '#0d6efd';  // 直接使用颜色值
                card.style.backgroundColor = 'rgba(13, 110, 253, 0.08)';
                // 更新标题颜色
                const selectedLabel = card.querySelector('.mode-card-label');
                if (selectedLabel) selectedLabel.style.color = '#0d6efd';
                this.setMode(mode.value);
            };
            modeGroup.appendChild(card);
        });
        
        menu.appendChild(modeGroup);

        this.addDivider(menu);

        // 2. 时间范围选择
        this.addHeader(menu, '时间范围');
        const timeOptions = [
            { label: '最近1周', value: '1week' },
            { label: '最近2周', value: '2weeks' },
            { label: '最近1月', value: '1month' },
            { label: '最近3月', value: '3months' },
            { label: '最近1年', value: '1year' }
        ];

        timeOptions.forEach(opt => {
            this.createMenuOption(menu, 'time-range', opt.value, opt.label, this.currentTimeRange === opt.value, (val) => this.setTimeRange(val));
        });

        this.addDivider(menu);

        // 3. 其他图层
        this.addHeader(menu, '其他图层');
        this.createCheckbox(menu, '显示网络拓扑', this.arcgisVisible, (checked) => {
            this.arcgisVisible = checked;
            this.updateArcgisLayersVisibility();
        });

        // 定位菜单
        menu.style.top = '40px';
        menu.style.left = '0';
        
        // Prevent menu click from propagating to map
        // And prevent it from triggering container mouseleave prematurely if gaps exist (though structure avoids this)
        menu.onmouseenter = () => {
             if (this.hideTimer) clearTimeout(this.hideTimer);
        };
    }

    // Deprecated exact method, keeping signature or logic if needed by previous calls
    // But createMenu is now internal logic called by showMenu
    
    /* --- UI Helpers --- */
    addHeader(container, text) {
        const header = document.createElement('div');
        header.className = 'dropdown-header';
        header.style.padding = '4px 16px';
        header.style.fontSize = '12px';
        header.style.color = 'var(--bs-secondary-color)';
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
     * @param {string} value - 模式值
     * @param {string} label - 模式标签
     * @param {string} desc - 模式描述
     * @param {boolean} active - 是否选中
     * @returns {HTMLElement} 卡片元素
     */
    createModeCard(value, label, desc, active) {
        const card = document.createElement('div');
        card.className = 'mode-card' + (active ? ' active' : '');
        card.dataset.mode = value;
        
        // 卡片样式 - 使用直接颜色值确保正确显示
        const activeBorderColor = '#0d6efd';
        const activeBgColor = 'rgba(13, 110, 253, 0.08)';
        const inactiveBorderColor = '#dee2e6';
        const inactiveBgColor = '#fff';
        
        card.style.cssText = `
            flex: 1;
            min-width: 70px;
            padding: 8px 12px;
            border: 2px solid ${active ? activeBorderColor : inactiveBorderColor};
            border-radius: 8px;
            background-color: ${active ? activeBgColor : inactiveBgColor};
            cursor: pointer;
            text-align: center;
            white-space: nowrap;
            transition: all 0.15s ease-in-out;
        `;
        
        // 标题 - 添加类名便于后续查询和更新
        const labelEl = document.createElement('div');
        labelEl.className = 'mode-card-label';
        labelEl.style.cssText = `
            font-size: 13px;
            font-weight: 600;
            color: ${active ? '#0d6efd' : '#212529'};
            margin-bottom: 2px;
        `;
        labelEl.innerText = label;
        
        // 描述
        const descEl = document.createElement('div');
        descEl.className = 'mode-card-desc';
        descEl.style.cssText = `
            font-size: 10px;
            color: #6c757d;
        `;
        descEl.innerText = desc;
        
        card.appendChild(labelEl);
        card.appendChild(descEl);
        
        // 悬停效果
        card.onmouseenter = () => {
            if (!card.classList.contains('active')) {
                card.style.borderColor = '#86b7fe';
                card.style.backgroundColor = 'rgba(13, 110, 253, 0.04)';
            }
        };
        card.onmouseleave = () => {
            if (!card.classList.contains('active')) {
                card.style.borderColor = inactiveBorderColor;
                card.style.backgroundColor = inactiveBgColor;
            }
        };
        
        return card;
    }

    createRadioButton(container, groupName, value, label, checked, onChange) {
        const wrapper = document.createElement('div');
        wrapper.className = 'form-check'; // Bootstrap style
        
        const input = document.createElement('input');
        input.type = 'radio';
        input.className = 'form-check-input';
        input.name = groupName;
        input.value = value;
        input.id = `${groupName}-${value}`;
        input.checked = checked;
        
        const lbl = document.createElement('label');
        lbl.className = 'form-check-label';
        lbl.htmlFor = input.id;
        lbl.innerText = label;
        lbl.style.cursor = 'pointer';

        wrapper.appendChild(input);
        wrapper.appendChild(lbl);
        
        input.onchange = () => onChange(value);
        
        container.appendChild(wrapper);
    }

    createMenuOption(container, groupName, value, label, checked, onChange) {
        const item = document.createElement('div');
        item.className = 'dropdown-item d-flex align-items-center gap-2';
        item.style.cursor = 'pointer';
        
        item.innerHTML = `
            <input type="radio" name="${groupName}" value="${value}" ${checked ? 'checked' : ''} style="pointer-events: none;">
            <span>${label}</span>
        `;
        
        item.onclick = (e) => {
            e.stopPropagation();
            // Update UI
            container.querySelectorAll(`input[name="${groupName}"]`).forEach(el => el.checked = false);
            item.querySelector('input').checked = true;
            onChange(value);
        };
        
        container.appendChild(item);
    }

    createCheckbox(container, label, checked, onChange) {
         const item = document.createElement('div');
        item.className = 'dropdown-item d-flex align-items-center gap-2';
        item.style.cursor = 'pointer';
        
        item.innerHTML = `
            <input type="checkbox" ${checked ? 'checked' : ''} style="pointer-events: none;">
            <span>${label}</span>
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
        console.log('Mode changed to:', mode);
        this.triggerGlobalUpdate();
    }

    setTimeRange(range) {
        if (this.currentTimeRange === range) return;
        this.currentTimeRange = range;
        console.log('Time range changed to:', range);
        this.triggerGlobalUpdate();
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
     * 在智能模式下，根据时间范围和缩放级别自动选择：
     * - 时间范围为一周或两周时：显示故障点
     * - 其他时间范围：显示热力图
     * - 地图缩放级别 > 7 时：显示故障点
     * @returns {string} 'points' | 'heatmap'
     */
    getEffectiveMode() {
        // 非智能模式直接返回当前模式
        if (this.currentMode !== 'smart') {
            return this.currentMode;
        }
        
        // 智能模式逻辑
        const zoom = this.map ? this.map.getZoom() : 0;
        
        // 条件 1: 缩放级别 > 7 时显示故障点
        if (zoom > 7) {
            return 'points';
        }
        
        // 条件 2: 根据时间范围决定
        // 一周或两周 -> 故障点, 其他 -> 热力图
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

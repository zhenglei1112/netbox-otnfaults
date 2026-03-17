/**
 * 故障点图例控件
 * 在地图右下角显示故障类型图例（不同形状）和故障状态图例（不同颜色）
 * 仅在故障点模式下可见，热力图模式下隐藏
 */
class FaultLegendControl {
    constructor() {
        this.container = null;
        this.visible = false;
        this.isCollapsed = true; // 默认状态为收起
    }

    onAdd(map) {
        this.map = map;
        this.container = document.createElement('div');
        this.container.className = 'maplibregl-ctrl fault-legend-control';

        this.render();

        // 初始隐藏
        this.container.style.display = 'none';

        return this.container;
    }

    onRemove() {
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
        this.map = undefined;
    }

    render() {
        // 故障类型图例（不同形状 - 象形设计）
        const categories = [
            { key: 'fiber_break', name: '光缆', shape: 'fiber_break' },
            { key: 'ac_fault', name: '空调', shape: 'ac_fault' },
            { key: 'device_fault', name: '设备', shape: 'device_fault' },
            { key: 'power_fault', name: '供电', shape: 'power_fault' }
        ];

        // 故障状态图例（不同颜色）
        const statuses = [
            { key: 'processing', name: FAULT_STATUS_NAMES?.processing || '处理中', color: FAULT_STATUS_COLORS?.processing || '#f5a623' },
            { key: 'temporary_recovery', name: FAULT_STATUS_NAMES?.temporary_recovery || '临时恢复', color: FAULT_STATUS_COLORS?.temporary_recovery || '#0d6efd' },
            { key: 'suspended', name: FAULT_STATUS_NAMES?.suspended || '挂起', color: FAULT_STATUS_COLORS?.suspended || '#ffc107' },
            { key: 'closed', name: FAULT_STATUS_NAMES?.closed || '已关闭', color: FAULT_STATUS_COLORS?.closed || '#198754' }
        ];

        // 类型图例项（使用不同形状的SVG）
        const categoryItems = categories.map(cat => `
            <div class="legend-item">
                ${this.getShapeSvg(cat.shape, '#6c757d')}
                <span class="legend-label">${cat.name}</span>
            </div>
        `).join('');

        // 状态图例项（使用圆形颜色标记）
        const statusItems = statuses.map(st => `
            <div class="legend-item">
                <span class="legend-color-marker" style="background-color: ${st.color};"></span>
                <span class="legend-label">${st.name}</span>
            </div>
        `).join('');

        this.container.innerHTML = `
            <div class="legend-collapse-btn shadow-sm bg-body" title="展开图例" style="display: ${this.isCollapsed ? 'flex' : 'none'};">
                <i class="mdi mdi-arrow-top-left fs-5"></i>
            </div>
            <div class="card shadow-sm legend-card bg-body" style="opacity: 0.95; display: ${this.isCollapsed ? 'none' : 'block'};">
                <div class="card-header p-1 px-2 border-bottom text-start">
                    <span class="legend-title"><i class="mdi mdi-information-outline me-1"></i>图例</span>
                </div>
                <div class="card-body p-2 position-relative">
                    <div class="legend-section">
                        <div class="legend-header text-body-secondary">故障类型</div>
                        <div class="legend-body mt-1">
                            ${categoryItems}
                        </div>
                    </div>
                    <div class="legend-divider border-top my-2"></div>
                    <div class="legend-section">
                        <div class="legend-header text-body-secondary">故障状态</div>
                        <div class="legend-body mt-1">
                            ${statusItems}
                        </div>
                    </div>
                    
                    <button type="button" class="btn btn-sm btn-link text-body-secondary p-0 legend-close-btn position-absolute" style="bottom: 4px; right: 8px;" title="收起图例">
                        <i class="mdi mdi-arrow-bottom-right fs-5"></i>
                    </button>
                </div>
            </div>
            <style>
                .fault-legend-control {
                    pointer-events: auto;
                    margin-bottom: 20px !important;
                    margin-right: 20px !important;
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                    justify-content: flex-end;
                }
                .legend-collapse-btn {
                    width: 32px;
                    height: 32px;
                    border-radius: 4px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    border: 1px solid var(--bs-border-color, #dee2e6);
                    color: var(--bs-body-color);
                    transition: background-color 0.2s;
                }
                .legend-collapse-btn:hover {
                    background-color: var(--bs-tertiary-bg, #e9ecef) !important;
                }
                .legend-card {
                    min-width: 120px;
                }
                .legend-title {
                    font-size: 12px;
                    font-weight: 600;
                    color: var(--bs-body-color);
                }
                .legend-close-btn:hover {
                    color: var(--bs-primary) !important;
                }
                .legend-section {
                    margin-bottom: 0;
                }
                .legend-header {
                    font-size: 11px;
                    font-weight: 600;
                    margin-bottom: 2px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                .legend-body {
                    display: flex;
                    flex-direction: column;
                    gap: 3px;
                }
                .legend-item {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 11px;
                }
                .legend-shape-svg {
                    width: 14px;
                    height: 14px;
                    flex-shrink: 0;
                }
                .legend-color-marker {
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    flex-shrink: 0;
                }
                .legend-label {
                    color: inherit;
                }
            </style>
        `;

        // 绑定收缩与展开事件
        const collapseBtn = this.container.querySelector('.legend-collapse-btn');
        const expandCard = this.container.querySelector('.legend-card');
        const closeBtn = this.container.querySelector('.legend-close-btn');

        if (collapseBtn && expandCard && closeBtn) {
            collapseBtn.addEventListener('click', () => {
                this.isCollapsed = false;
                collapseBtn.style.display = 'none';
                expandCard.style.display = 'block';
            });

            closeBtn.addEventListener('click', () => {
                this.isCollapsed = true;
                expandCard.style.display = 'none';
                collapseBtn.style.display = 'flex';
            });
        }
    }

    /**
     * 根据形状类型从全局获取 SVG 图标
     * @param {string} shape - 形状类型
     * @param {string} color - 填充颜色
     * @returns {string} SVG HTML
     */
    getShapeSvg(shape, color) {
        let targetSvg = '';
        if (window.FAULT_SVG_ICONS && window.FAULT_SVG_ICONS[shape]) {
            targetSvg = window.FAULT_SVG_ICONS[shape];
        } else if (window.FAULT_SVG_ICONS && window.FAULT_SVG_ICONS['other']) {
            targetSvg = window.FAULT_SVG_ICONS['other'];
        } else {
            targetSvg = `<svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="4" fill="white"/></svg>`;
        }

        // 提取原 SVG 内容
        const parser = new DOMParser();
        const svgDoc = parser.parseFromString(targetSvg, 'image/svg+xml');
        let innerContent = '';
        if (svgDoc.documentElement) {
            Array.from(svgDoc.documentElement.children).forEach(child => {
                let html = child.outerHTML;
                // 单独处理设备芯片图标中间的小圆点填充色
                if (shape === 'device_fault') {
                    if (html.includes('rect x="11" y="11"')) {
                        html = html.replace('fill="white"', `fill="${color}"`);
                    }
                }
                innerContent += html;
            });
        }

        // 构造带有自身背景圆圈底色的内联 SVG
        const finalSvg = `
          <svg class="legend-shape-svg" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" style="width: 14px; height: 14px;">
            <circle cx="16" cy="16" r="14" fill="${color}" stroke="white" stroke-width="1.5"/>
            ${innerContent}
          </svg>
        `;

        return finalSvg;
    }

    /**
     * 显示图例
     */
    show() {
        if (this.container && !this.visible) {
            this.container.style.display = 'block';
            this.visible = true;
        }
    }

    /**
     * 隐藏图例
     */
    hide() {
        if (this.container && this.visible) {
            this.container.style.display = 'none';
            this.visible = false;
        }
    }

    /**
     * 根据模式更新可见性
     * @param {string} mode - 'points' | 'heatmap'
     */
    updateVisibility(mode) {
        if (mode === 'points') {
            this.show();
        } else {
            this.hide();
        }
    }
}

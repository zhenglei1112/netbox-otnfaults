/**
 * 故障点图例控件
 * 在地图右下角显示故障类型图例（不同形状）和故障状态图例（不同颜色）
 * 仅在故障点模式下可见，热力图模式下隐藏
 */
class FaultLegendControl {
    constructor() {
        this.container = null;
        this.visible = false;
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
            { key: 'fiber', name: FAULT_CATEGORY_NAMES.fiber || '光缆', shape: 'fiber' },
            { key: 'power', name: FAULT_CATEGORY_NAMES.power || '电力', shape: 'power' },
            { key: 'pigtail', name: FAULT_CATEGORY_NAMES.pigtail || '空调', shape: 'snowflake' },
            { key: 'device', name: FAULT_CATEGORY_NAMES.device || '设备', shape: 'chip' },
            { key: 'other', name: FAULT_CATEGORY_NAMES.other || '其他', shape: 'warning' }
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
            <div class="legend-card">
                <div class="legend-section">
                    <div class="legend-header">故障类型</div>
                    <div class="legend-body">
                        ${categoryItems}
                    </div>
                </div>
                <div class="legend-divider"></div>
                <div class="legend-section">
                    <div class="legend-header">故障状态</div>
                    <div class="legend-body">
                        ${statusItems}
                    </div>
                </div>
            </div>
            <style>
                .fault-legend-control {
                    pointer-events: auto;
                }
                .legend-card {
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
                    padding: 8px 12px;
                    min-width: 100px;
                }
                .legend-section {
                    margin-bottom: 6px;
                }
                .legend-section:last-child {
                    margin-bottom: 0;
                }
                .legend-divider {
                    height: 1px;
                    background: #e9ecef;
                    margin: 6px 0;
                }
                .legend-header {
                    font-size: 11px;
                    font-weight: 600;
                    color: #6c757d;
                    margin-bottom: 4px;
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
                    color: #495057;
                }
            </style>
        `;
    }
    
    /**
     * 根据形状类型生成 SVG 图标（与地图图标一致的象形设计）
     * @param {string} shape - 形状类型
     * @param {string} color - 填充颜色
     * @returns {string} SVG HTML
     */
    getShapeSvg(shape, color) {
        const svgStart = '<svg class="legend-shape-svg" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">';
        const svgEnd = '</svg>';
        
        let content = '';
        switch(shape) {
            case 'fiber':
                // 光纤波浪线图标
                content = `
                    <circle cx="12" cy="12" r="10" fill="${color}" stroke="white" stroke-width="1"/>
                    <path d="M6 12 Q9 8 12 12 T18 12" fill="none" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
                    <circle cx="6" cy="12" r="1.5" fill="white"/>
                    <circle cx="18" cy="12" r="1.5" fill="white"/>
                `;
                break;
            case 'power':
                // 闪电图标
                content = `
                    <circle cx="12" cy="12" r="10" fill="${color}" stroke="white" stroke-width="1"/>
                    <path d="M13 5 L9 12 L12 12 L11 19 L15 12 L12 12 Z" fill="white"/>
                `;
                break;
            case 'snowflake':
                // 雪花图标
                content = `
                    <circle cx="12" cy="12" r="10" fill="${color}" stroke="white" stroke-width="1"/>
                    <g stroke="white" stroke-width="1.5" stroke-linecap="round">
                        <line x1="12" y1="5" x2="12" y2="19"/>
                        <line x1="5" y1="12" x2="19" y2="12"/>
                        <line x1="7" y1="7" x2="17" y2="17"/>
                        <line x1="17" y1="7" x2="7" y2="17"/>
                    </g>
                `;
                break;
            case 'chip':
                // 芯片图标
                content = `
                    <circle cx="12" cy="12" r="10" fill="${color}" stroke="white" stroke-width="1"/>
                    <rect x="8" y="8" width="8" height="8" fill="white"/>
                    <g stroke="white" stroke-width="1">
                        <line x1="9" y1="8" x2="9" y2="5"/>
                        <line x1="12" y1="8" x2="12" y2="5"/>
                        <line x1="15" y1="8" x2="15" y2="5"/>
                        <line x1="9" y1="16" x2="9" y2="19"/>
                        <line x1="12" y1="16" x2="12" y2="19"/>
                        <line x1="15" y1="16" x2="15" y2="19"/>
                        <line x1="8" y1="9" x2="5" y2="9"/>
                        <line x1="8" y1="12" x2="5" y2="12"/>
                        <line x1="8" y1="15" x2="5" y2="15"/>
                        <line x1="16" y1="9" x2="19" y2="9"/>
                        <line x1="16" y1="12" x2="19" y2="12"/>
                        <line x1="16" y1="15" x2="19" y2="15"/>
                    </g>
                    <rect x="10" y="10" width="4" height="4" fill="${color}"/>
                `;
                break;
            case 'warning':
            default:
                // 警告三角形图标
                content = `
                    <circle cx="12" cy="12" r="10" fill="${color}" stroke="white" stroke-width="1"/>
                    <path d="M12 6 L18 17 L6 17 Z" fill="none" stroke="white" stroke-width="1.5" stroke-linejoin="round"/>
                    <line x1="12" y1="10" x2="12" y2="13" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
                    <circle cx="12" cy="15" r="1" fill="white"/>
                `;
                break;
        }
        
        return svgStart + content + svgEnd;
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

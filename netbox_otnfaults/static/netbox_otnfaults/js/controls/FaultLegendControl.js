/**
 * 故障点图例控件
 * 在地图右下角显示故障类型图例
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
        // 构建图例内容
        const categories = [
            { key: 'fiber', name: FAULT_CATEGORY_NAMES.fiber || '光缆', color: FAULT_CATEGORY_COLORS.fiber },
            { key: 'power', name: FAULT_CATEGORY_NAMES.power || '电力', color: FAULT_CATEGORY_COLORS.power },
            { key: 'pigtail', name: FAULT_CATEGORY_NAMES.pigtail || '空调', color: FAULT_CATEGORY_COLORS.pigtail },
            { key: 'device', name: FAULT_CATEGORY_NAMES.device || '设备', color: FAULT_CATEGORY_COLORS.device },
            { key: 'other', name: FAULT_CATEGORY_NAMES.other || '其他', color: FAULT_CATEGORY_COLORS.other }
        ];

        const legendItems = categories.map(cat => `
            <div class="legend-item">
                <span class="legend-marker" style="background-color: ${cat.color};"></span>
                <span class="legend-label">${cat.name}</span>
            </div>
        `).join('');

        this.container.innerHTML = `
            <div class="legend-card">
                <div class="legend-header">故障类型</div>
                <div class="legend-body">
                    ${legendItems}
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
                    min-width: 90px;
                }
                .legend-header {
                    font-size: 12px;
                    font-weight: 600;
                    color: #212529;
                    margin-bottom: 6px;
                    padding-bottom: 4px;
                    border-bottom: 1px solid #e9ecef;
                }
                .legend-body {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }
                .legend-item {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 11px;
                }
                .legend-marker {
                    width: 12px;
                    height: 12px;
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

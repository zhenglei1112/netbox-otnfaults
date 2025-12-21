/**
 * CategoryFilterControl.js
 * 
 * 此文件已被废弃。
 * 
 * 原因：
 * 1. 故障分类筛选功能已整合到 LayerToggleControl.js 中
 * 2. 全局常量（FAULT_CATEGORY_COLORS, FAULT_CATEGORY_NAMES 等）已移至 core/config.js
 * 
 * 此文件保留为空文件以防止引用错误，后续可安全删除。
 * 
 * @deprecated 使用 LayerToggleControl 替代，常量请从 core/config.js 获取
 */

// 为了向后兼容，确保全局对象存在（实际值由 config.js 提供）
// 如果 config.js 未加载，这里提供 fallback
if (typeof FAULT_CATEGORY_COLORS === 'undefined') {
    console.warn('CategoryFilterControl: config.js 未加载，使用 fallback 常量');
    
    window.FAULT_CATEGORY_COLORS = {
        'power': '#ff0000',
        'fiber': '#ffa500',
        'pigtail': '#ffff00',
        'device': '#800080',
        'other': '#808080'
    };
    
    window.FAULT_CATEGORY_NAMES = {
        'power': '电力故障',
        'fiber': '光缆故障',
        'pigtail': '空调故障',
        'device': '设备故障',
        'other': '其他故障'
    };
    
    window.FAULT_STATUS_COLORS = {
        'processing': '#dc3545',
        'temporary_recovery': '#0d6efd',
        'suspended': '#ffc107',
        'closed': '#198754'
    };
    
    window.FAULT_STATUS_NAMES = {
        'processing': '处理中',
        'temporary_recovery': '临时恢复',
        'suspended': '挂起',
        'closed': '已关闭'
    };
}

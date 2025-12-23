/**
 * 故障地图全局配置常量
 * 从 otnfault_map_app.js 和控件中提取
 */

// 获取全局配置中的颜色设置，如果不存在则使用默认空对象（防止报错）
const COLORS_CONFIG = (window.OTNFaultMapConfig && window.OTNFaultMapConfig.colorsConfig) || {};

// 故障类型颜色映射
const FAULT_CATEGORY_COLORS = COLORS_CONFIG.category_colors || {
    power: '#f5a623',      // 电力故障 - 橙色
    fiber: '#dc3545',      // 光缆故障 - 红色
    pigtail: '#0d6efd',    // 空调故障 - 蓝色
    device: '#198754',     // 设备故障 - 绿色
    other: '#6c757d'       // 其他故障 - 灰色
};

// 故障类型名称映射
const FAULT_CATEGORY_NAMES = COLORS_CONFIG.category_names || {
    power: '电力故障',
    fiber: '光缆故障',
    pigtail: '空调故障',
    device: '设备故障',
    other: '其他故障'
};

// 故障状态颜色映射
const FAULT_STATUS_COLORS = COLORS_CONFIG.status_colors || {
    processing: '#dc3545',         // 处理中 - 红色
    temporary_recovery: '#0d6efd', // 临时恢复 - 蓝色
    suspended: '#ffc107',          // 挂起 - 黄色
    closed: '#198754'              // 已关闭 - 绿色
};

// 故障状态名称映射
const FAULT_STATUS_NAMES = COLORS_CONFIG.status_names || {
    processing: '处理中',
    temporary_recovery: '临时恢复',
    suspended: '挂起',
    closed: '已关闭'
};

// ... existing code ...

// 弹窗颜色映射（用于故障点 hover 弹窗）
const POPUP_CATEGORY_COLORS = FAULT_CATEGORY_COLORS; // 复用类型颜色

const POPUP_STATUS_COLORS = COLORS_CONFIG.popup_status_colors || {
    orange: '#f5a623',
    blue: '#0d6efd',
    yellow: '#ffc107',
    green: '#198754',
    gray: '#6c757d',
    red: '#dc3545',
    secondary: '#6c757d'
};

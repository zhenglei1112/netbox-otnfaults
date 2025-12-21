/**
 * 故障地图全局配置常量
 * 从 otnfault_map_app.js 和控件中提取
 */

// 故障类型颜色映射
const FAULT_CATEGORY_COLORS = {
    power: '#f5a623',      // 电力故障 - 橙色
    fiber: '#dc3545',      // 光缆故障 - 红色
    pigtail: '#0d6efd',    // 空调故障 - 蓝色
    device: '#198754',     // 设备故障 - 绿色
    other: '#6c757d'       // 其他故障 - 灰色
};

// 故障类型名称映射
const FAULT_CATEGORY_NAMES = {
    power: '电力故障',
    fiber: '光缆故障',
    pigtail: '空调故障',
    device: '设备故障',
    other: '其他故障'
};

// 故障状态颜色映射
const FAULT_STATUS_COLORS = {
    processing: '#f5a623',         // 处理中 - 橙色
    temporary_recovery: '#0d6efd', // 临时恢复 - 蓝色
    suspended: '#ffc107',          // 挂起 - 黄色
    closed: '#198754'              // 已关闭 - 绿色
};

// 故障状态名称映射
const FAULT_STATUS_NAMES = {
    processing: '处理中',
    temporary_recovery: '临时恢复',
    suspended: '挂起',
    closed: '已关闭'
};

// 时间范围选项
const TIME_RANGE_OPTIONS = [
    { label: '1周', value: '1week', days: 7 },
    { label: '2周', value: '2weeks', days: 14 },
    { label: '1月', value: '1month', days: 30 },
    { label: '3月', value: '3months', days: 90 },
    { label: '1年', value: '1year', days: 365 }
];

// 默认地图配置（会被全局配置覆盖）
const MAP_DEFAULT_CONFIG = {
    center: [112.53, 33.00],
    zoom: 4.2
};

// 弹窗颜色映射（用于故障点 hover 弹窗）
const POPUP_CATEGORY_COLORS = {
    power: '#f5a623',
    fiber: '#dc3545',
    pigtail: '#0d6efd',
    device: '#198754',
    other: '#6c757d'
};

const POPUP_STATUS_COLORS = {
    orange: '#f5a623',
    blue: '#0d6efd',
    yellow: '#ffc107',
    green: '#198754',
    gray: '#6c757d',
    red: '#dc3545',
    secondary: '#6c757d'
};

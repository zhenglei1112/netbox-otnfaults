function occurrenceTime(now, minutesAgo) {
  const value = new Date(now.getTime() - (minutesAgo * 60 * 1000));
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  const hours = String(value.getHours()).padStart(2, '0');
  const minutes = String(value.getMinutes()).padStart(2, '0');
  return {
    iso: value.toISOString(),
    display: `${month}-${day} ${hours}:${minutes}`,
  };
}

const MOCK_FAULT_DEFINITIONS = [
  {
    fault_number: 'DEBUG-OTN-001',
    category_display: '光缆故障',
    category_color: 'purple',
    urgency_display: '紧急',
    severity: 'critical',
    priority_score: 100,
    lng: 116.4074,
    lat: 39.9042,
    province: '北京市',
    site_a: '北京核心站',
    sites_z: ['天津枢纽站'],
    minutes_ago: 38,
    duration: '38分',
    handling_unit: '网络运行中心',
    handler: '张工',
    interrupted_business_count: 2,
    interrupted_business_names: ['北京—天津 OTN 主用电路', '华北骨干互联网专线'],
    reason: '京津干线光缆受外力影响发生中断',
    details: '主用路由中断，业务已切换至保护路由，现场人员正在定位断点。',
  },
  {
    fault_number: 'DEBUG-OTN-002',
    category_display: '设备故障',
    category_color: 'pink',
    urgency_display: '高',
    severity: 'major',
    priority_score: 88,
    lng: 121.4737,
    lat: 31.2304,
    province: '上海市',
    site_a: '上海浦东站',
    sites_z: ['苏州园区站'],
    minutes_ago: 67,
    duration: '1小时7分',
    handling_unit: '华东维护中心',
    handler: '李工',
    interrupted_business_count: 1,
    interrupted_business_names: ['沪苏政企精品专线'],
    reason: 'OTN 设备线路板异常复位',
    details: '板卡持续上报告警，已安排备件并执行远程状态核查。',
  },
  {
    fault_number: 'DEBUG-OTN-003',
    category_display: '电源故障',
    category_color: 'indigo',
    urgency_display: '高',
    severity: 'major',
    priority_score: 76,
    lng: 113.2644,
    lat: 23.1291,
    province: '广东省',
    site_a: '广州白云站',
    sites_z: ['深圳龙岗站'],
    minutes_ago: 104,
    duration: '1小时44分',
    handling_unit: '华南维护中心',
    handler: '王工',
    interrupted_business_count: 0,
    interrupted_business_names: [],
    reason: '机房交流输入异常',
    details: '当前由蓄电池供电，维护单位正在检查市电与油机切换状态。',
  },
  {
    fault_number: 'DEBUG-OTN-004',
    category_display: '纤芯劣化',
    category_color: 'orange',
    urgency_display: '中',
    severity: 'minor',
    priority_score: 54,
    lng: 104.0665,
    lat: 30.5728,
    province: '四川省',
    site_a: '成都核心站',
    sites_z: ['重庆枢纽站'],
    minutes_ago: 152,
    duration: '2小时32分',
    handling_unit: '西南维护中心',
    handler: '赵工',
    interrupted_business_count: 1,
    interrupted_business_names: ['成渝骨干波分电路'],
    reason: '线路光功率缓慢劣化',
    details: '接收光功率接近门限，已启动沿线接头盒和机房尾纤排查。',
  },
  {
    fault_number: 'DEBUG-OTN-005',
    category_display: '空调故障',
    category_color: 'teal',
    urgency_display: '一般',
    severity: 'minor',
    priority_score: 32,
    lng: 108.9398,
    lat: 34.3416,
    province: '陕西省',
    site_a: '西安高新站',
    sites_z: [],
    minutes_ago: 219,
    duration: '3小时39分',
    handling_unit: '西北维护中心',
    handler: '刘工',
    interrupted_business_count: 0,
    interrupted_business_names: [],
    reason: '主用精密空调压缩机告警',
    details: '备用空调运行正常，机房温度稳定，厂家正在远程诊断。',
  },
];

function createMockCutovers(now) {
  const definitions = [
    ['applying', '申请中', 'blue', '浙江省', '杭州核心站', '宁波站', 120.15, 30.28],
    ['pending_implementation', '待实施', 'orange', '湖北省', '武汉核心站', '宜昌站', 114.30, 30.59],
    ['completed', '已完成', 'green', '山东省', '济南核心站', '青岛站', 117.12, 36.65],
    ['cancelled', '被取消', 'red', '福建省', '福州核心站', '厦门站', 119.30, 26.08],
  ];
  return definitions.map(([status, status_display, status_color, province, site_a, site_z, lng, lat], index) => {
    const planned = new Date(now);
    const tomorrow = index % 2 === 1;
    planned.setDate(planned.getDate() + Number(tomorrow));
    planned.setHours(2 + index, 30, 0, 0);
    const pad = (value) => String(value).padStart(2, '0');
    return {
      id: `debug-cutover-${index + 1}`, url: '', cutover_no: `DEBUG-CUT-${index + 1}`,
      day: tomorrow ? 'tomorrow' : 'today', planned_time: planned.toISOString(),
      planned_time_display: `${pad(planned.getMonth() + 1)}-${pad(planned.getDate())} ${pad(planned.getHours())}:30`,
      type_display: '光缆割接', status, status_display, status_color, province, site_a,
      sites_z: [site_z], lng, lat, location: '模拟线路迁改段', supervisor: '模拟主管', is_my_task: false,
    };
  });
}

export function createDashboardV2MockFaultData(realData = {}, now = new Date()) {
  const faults = MOCK_FAULT_DEFINITIONS.map((definition, index) => {
    const occurrence = occurrenceTime(now, definition.minutes_ago);
    return {
      id: `debug-${index + 1}`,
      url: '',
      ...definition,
      occurrence_time: occurrence.iso,
      occurrence_time_display: occurrence.display,
    };
  });
  const realSummary = realData.summary || {};
  return {
    timestamp: now.toISOString(),
    simulated: true,
    cutovers: createMockCutovers(now),
    cutover_summary: { today: 2, tomorrow: 2, total: 4 },
    summary: {
      total_faults: Math.max(Number(realSummary.total_faults) || 0, faults.length),
      processing_faults: faults.length,
      today_faults: Math.max(Number(realSummary.today_faults) || 0, faults.length),
      active_business_interruptions: faults.reduce(
        (total, fault) => total + fault.interrupted_business_count,
        0,
      ),
    },
    processing_faults: faults,
    sites: Array.isArray(realData.sites) ? realData.sites : [],
  };
}

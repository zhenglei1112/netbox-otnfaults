# OTN 全国网络故障自动化大屏可视化系统 - 需求文档

## 1. 系统定位

构建一套基于 GIS 的全国 OTN 网络故障自动化展示大屏，定位为网络操作中心（NOC）的"核心数字沙盘"与"自动化态势指挥官"。

核心价值：**无人值守、自动巡航、智能聚焦**。

## 2. 技术约束

- 基于现有 `netbox-otnfaults` 插件（NetBox 4.4.2）
- 前端技术：MapLibre GL JS + Deck.gl（已在项目中）
- 数据来源：NetBox REST API 定时轮询
- 无独立后端服务，所有逻辑在前端实现
- 开发环境无 NetBox 运行实例，需支持模拟数据模式

## 3. 核心功能

### 3.1 智能播控引擎（5 状态）

| 状态 | 模式名称 | 触发条件 | 视觉表现 |
|------|---------|---------|---------|
| STATE_GLOBAL_CRUISE | 全局和平巡航 | 默认状态/无故障 | 高空俯瞰，缓速环绕 |
| STATE_REGION_TOUR | 重点区域轮播 | 定时触发 | 拉近至枢纽区域，驻留15秒 |
| STATE_FAULT_INTERRUPT | 故障中断捕获 | 新故障事件 | 计算坐标，准备运镜 |
| STATE_CAMERA_FLIGHT | 空间机动运镜 | 中断完成后 | 贝塞尔曲线飞行 3~6秒 |
| STATE_FAULT_ANALYSIS | 深度聚焦推演 | 抵达故障点 | 锁定视角，展开面板 |

### 3.2 优先级评分模型

```
S_priority = severity_weight × impact_count × e^(-λ × age_minutes)
```

- `severity_weight`：故障分类权重（骨干断纤 > 设备故障 > 空调故障）
- `impact_count`：受影响业务数量
- `freshness_decay`：时间衰减，越新优先级越高

### 3.3 告警色彩规范

| 级别 | 色值 | 动效 |
|------|------|------|
| 致命 (Critical) | #FF1E1E | 高频脉冲 + Bloom |
| 严重 (Major) | #FF8A00 | 呼吸灯 + 光柱 |
| 次要 (Minor) | #FADB14 | 静态高亮描边 |
| 正常 (Normal) | #00D2FF | 微弱常亮 + 流光 |

### 3.4 屏幕布局

- 核心演播区（中央60%）：3D 地球 + 网络拓扑
- 左翼面板：全网健康度、24H 趋势、故障统计
- 右翼面板：当前焦点故障详情、影响业务、时间线
- 顶部栏：系统标题 + 实时时间
- 底部栏：告警滚动 Ticker

## 4. 数据依赖

- `OtnFault`：故障记录（含经纬度、分类、状态、紧急程度）
- `OtnFaultImpact`：故障影响的业务列表
- `OtnPath`：光缆路径 GeoJSON
- `OtnPathGroup`：路径组
- `Site`（NetBox 内置）：站点位置
- `中国_省.geojson`：省界底图

## 5. 设计风格

**暗黑科技风（Dark Tech Style）**：
- 底图：深空灰 #0a0e1a + 幽深蓝渐变
- 字体：Rajdhani（标题）+ JetBrains Mono（数据）
- 面板：毛玻璃效果 + 霓虹边框
- 动画：弹性物理参数过渡，杜绝生硬闪烁

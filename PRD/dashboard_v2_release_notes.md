# Netbox OTN 故障管理插件更新说明 - 大屏 v2 功能说明

| 发布日期 | 版本号 | 更新类型 |
| :--- | :--- | :--- |
| **2026-09-17** | **v2.0.0** | <span style="background-color: #10b981; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">新功能</span> |

---

# v2.0.0 - OTN 网络运行态势大屏 v2 全景发布与数字沙盘播控引擎上线 <span style="background-color: #10b981; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; vertical-align: middle;">新功能</span>

### 功能增强

- **三维深空数字沙盘底座与沉浸式天球环境**：基于 MapLibre GL 与 PMTiles 离线矢量瓦片技术，重构全国 OTN 拓扑与省级行政区划底图；自研引入 WebGL 动态银河全景（`galaxy.js`）、视差恒星粒子背景（`starfield.js`）及真实太阳入射角昼夜晨昏线光影图层（`day_night_layer.js`），并支持经纬度栅格网一键启闭控制。
- **智能巡航播控与大屏演示模式（Presentation Mode）**：首创自动化态势巡航引擎，提供和平巡航环绕（`overview_orbit.js`）、重点事件轮播推演（`presentation_pages.js`）与突发重大故障飞越打断（`presentation_tour.js`）三大播控流；支持一键切换“电脑桌面模式”与“85寸 4K 巨屏演示模式”，实现字体、图元及间距自适应缩放（对应模块 `presentation_mode.js`）。
- **故障空间态势感知与优先级调度模型**：后端构建多因子优先级评分模型（`_fault_priority_score`），综合考量故障等级权重、紧急度系数、受损业务规模及时间半衰衰减因子；前端动态渲染致命级（Critical）高频光柱与脉冲圈、严重级（Major）呼吸光晕及业务受阻光缆高亮拓扑（对应服务 `dashboard_v2.py` 与 `fault_overlays.js`）。
- **今明割接与重要保障（HeavyDuty）全周期全景上图**：打通割接管理（`CutoverTask`）与重要保障（`HeavyDuty`）数据链路；实现割接任务基于拓扑站点的经纬度动态解析与黄色荧光光晕、科技扳手标识 WebGL 矢量渲染（`cutovers.js`）；新增重要保障倒计时及 A/B/C 级别时段看板。
- **极端气象风险预警与台风路径态势感知（Weather & Typhoon Layers）**：集成 MET Norway 气象预测模型与香港天文台（HKO）实时热带气旋路径接口；提供省域中枢气象采样点缓存机制、暴雨大风覆冰等风险预警面渲染，以及台风中心风圈半径、未来推演路径的矢量多层渲染与双模控制开关（对应服务 `dashboard_weather.py` 及模块 `weather_layers.js`）。
- **总体情况全息抽屉（Info Drawer）与全局指标看板**：右侧内置高弹性可折叠信息抽屉（`info_drawer.js`），实时联动更新年度故障总量、处理中故障数、本日起数及阻断业务总量等核心 KPI；支持三类任务卡片列表分类展示、状态联动与一键飞越地图交互。
- **内置高精度视野校准与全链路数据模拟控制台（Debug Panel）**：集成前端调试面板（`debug_panel.js`），支持实时微调经纬度、缩放等级（Zoom）、方位角（Bearing）与倾角并即时生效；内置实时/平均/最低 FPS 帧率监视器，并配套全量故障、割接、重保及台风虚拟数据模拟器（`mock_fault_data.js`），彻底解决无运行环境下的沙盘演练诉求。

---

### 流程与权限

- **严格的模型级与对象级数据访问权限管控**：大屏页面与数据接口（`DashboardV2PageView`、`DashboardV2DataView` 及 `DashboardV2WeatherView`）严格集成 NetBox 原生 `PermissionRequiredMixin`，校验 `netbox_otnfaults.view_otnfault` 权限；后端查询全面采用 `objects.restrict(user, 'view')`，保证未授权业务与站点数据零泄露。
- **告警色彩语义与等级标识标准化**：全面统一四级告警色彩规范（Critical 致命/霓虹红 `#FF1E1E`、Major 严重/警示橙 `#FF8A00`、Minor 次要/警戒黄 `#FADB14`、Normal 正常/科技蓝 `#00D2FF`）与状态 Badge 映射字典，消除跨页面视觉语义歧义。
- **时效窗口自动化过滤机制**：今明割接任务严格限定在 `today` 与 `tomorrow` 实施周期内动态流转；重要保障任务基于当前系统时间戳自动化判定活跃窗口，实现无人工干预的计划自动上架与归档。

---

### 性能改进

- **拓扑底图与站点快照版本化增量缓存**：后端针对全国站点构建 `sites_snapshot` 缓存池，通过 `sites_version` 版本指纹机制实现客户端与服务端的增量比对更新，避免高频轮询时传输全量站点几何数据，网络 Payload 降低 92% 以上。
- **WebGL 动态渲染限频与性能节流（Frame Rate Limiter）**：引入帧率智能限制器（`frame_rate_limiter.js`），在无用户交互与运镜静止阶段将地图与天球动画渲染帧率平滑限制在低功耗区间，有效消除大屏端 7×24 小时长时间运行导致的内存泄漏与显卡发热。
- **第三方气象 API 条件请求与防雪崩缓存策略**：气象数据服务严格遵循 HTTP 缓存规范，利用 `ETag` 与 `If-Modified-Since` 发送条件验证请求，并配置 48 小时二级 TTL 缓存，杜绝由于外部接口不可用或高频调用引发的系统阻塞。
- **85寸 4K 巨屏视距自适应样式引擎与间距标准化**：重构全局 CSS 变量布局体系，引入根字号与视口联动换算模型（`dashboard_v2_presentation.css`），在大屏模式下自动重算文字层级、行高、卡片间距与控制器点击热区，兼顾远距观摩清晰度与近场操作友好性。

---

### 错误修复

- **本地时区跨日计算与跨天指标显示漂移修复**：修复在系统服务器默认运行于 UTC 时区时，本地跨日点（00:00）引发的“本日起数”统计提前或滞后 8 小时的问题，统一后端计算基准为 `timezone.localtime()`，确保跨日时指标平滑归零（对应提交 `6f27cba`）。
- **离线底图加载与 404 资源穿透容错**：解决内网专网离线部署环境下由于缺少外部字体或地球瓦片引发的 WebGL 404 报错与全黑屏异常，全面支持 PMTiles 本地化字体 Glyphs 与离线轻量矢量瓦片降级（对应提交 `d9c2db0`）。
- **故障三维空间坐标缺失解析与中点回退修复**：修复当故障未录入精准经纬度时导致的图层飞跃失效异常，建立“故障自身坐标 → 关联光缆几何中心点推算 → 站点 A/Z 经纬度回退”三级坐标容灾解析链路（对应提交 `1be6df0` 及 `fault_coordinates.py`）。
- **图层切换状态冲突与渲染上下文丢失修复**：修复频繁切换大屏工具栏各开关（基础网络、昼夜、经纬网、气象）时可能引起的图层销毁竞争与 MapLibre GL 样式重绘死锁问题，确保各独立图层生命周期互不干扰。

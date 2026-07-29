# 态势大屏时区一致性修复方案 (PRD)

## 1. 问题背景
在 OTN 态势大屏模块中，显示的故障起始时间、割接计划时间、重要保障时间以及事件队列时间比 Netbox 系统其他页面（如故障列表、割接详情）慢 8 小时。

## 2. 根因分析
1. **模型保存机制**：根据插件规范，Netbox 模型中的所有 `DateTimeField` 在保存入库时均统一转换为 UTC 时间存储。
2. **后端序列化未转 Localtime**：
   在 `dashboard_views.py`（`DashboardDataAPI`）中，后端读取 Python datetime 对象后，直接调用了：
   - `fault.fault_occurrence_time.strftime('%m-%d %H:%M')`
   - `cutover.planned_cutover_time.strftime('%m-%d %H:%M')`
   - `hd.start_time.strftime('%m月%d日 %H:%M')`
   Python 原生的 `strftime` 方法不会自动处理 Django 的 `TIME_ZONE` 转换，导致直接输出了 UTC 时间（比中国标准时间 Asia/Shanghai UTC+8 慢 8 小时）。
   此外，`isoformat()` 未经过 `timezone.localtime()` 包装，输出给前端的 ISO 时间也是 UTC 时区。

## 3. 修复方案

### 3.1 后端修复 (`netbox_otnfaults/dashboard_views.py`)
在 `DashboardDataAPI` 的 `get` 方法中，使用 `timezone.localtime()` 对所有返回给大屏前端的时间字段进行转换：

1. **活跃故障时间**：
   - `occurrence_time`: `timezone.localtime(fault.fault_occurrence_time).isoformat()`
   - `recovery_time`: `timezone.localtime(fault.fault_recovery_time).isoformat()`
   - `dispatch_time`, `departure_time`, `arrival_time`, `repair_time`: 均使用 `timezone.localtime(...)`
2. **综合事件队列 (`ticker_events`)**：
   - `time`: `timezone.localtime(fault.fault_occurrence_time).strftime('%m-%d %H:%M')`
3. **割接计划 (`cutovers`)**：
   - `planned_cutover_time`: `timezone.localtime(cutover.planned_cutover_time).isoformat()`
   - `planned_time_display`: `timezone.localtime(cutover.planned_cutover_time).strftime('%m-%d %H:%M')`
4. **重保通知 (`heavy_duties`)**：
   - `start_time_display`: `timezone.localtime(hd.start_time).strftime('%m月%d日 %H:%M')`
   - `end_time_display`: `timezone.localtime(hd.end_time).strftime('%m月%d日 %H:%M')`

### 3.2 前端兼容 (`netbox_otnfaults/static/netbox_otnfaults/js/dashboard/panels.js`)
- 在渲染焦点卡片与故障过程时间轴卡片时，确保前端 JS 的 `toLocaleString('zh-CN', { hour12: false })` 正确解析 ISO 时间，并以统一的 24 小时制进行展现。

## 4. 验证计划
1. 检查 API 接口 `/plugins/netbox-otnfaults/dashboard/data/` 返回的数据中，所有 `_display` 和 ISO 时间是否带有正确时区偏移 (+08:00) 且时间数值与本地系统相符。
2. 验证态势大屏的“割接计划”、“综合事件队列”、“焦点事件卡片”、“故障过程时间轴”显示的时间是否与 Netbox 列表界面完全一致。

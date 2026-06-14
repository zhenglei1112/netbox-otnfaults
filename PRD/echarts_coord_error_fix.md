# 需求文档：运行月历图隐藏 Tab 下 ECharts 报错修复

## 1. 问题背景
在 NetBox 故障统计插件中，包含两个主要的运行月历图表卡片（子公司绩效和业务卡片）。为了直观展示今年已过去月份与未来月份的对比，原设计使用 ECharts 的 `visualMap` 功能实现折线图的分段着色（前半段为深青色，后半段为浅灰色）。

然而，当用户切换 Tab（如切换至非活跃 Tab，导致对应的图表容器 `display: none`，尺寸为 0）并触发数据重新加载时，ECharts 在初始化/渲染该图表时，`visualMap` 无法计算隐藏 DOM 节点上类目轴的像素坐标，从而在底层抛出如下错误，阻塞后续 JS 逻辑执行：
```
TypeError: Cannot read properties of undefined (reading 'coord')
    at VS (echarts.min.js:45:340243)
```

## 2. 解决方案
为了彻底解决在隐藏 Tab 下报错的问题，同时保留今年未来月份呈现灰色的设计，我们弃用依赖 DOM 坐标计算的 `visualMap` 方案，改用 **双折线系列拼接方案**：

1. **数据分段处理**：
   - 提取折线的原始数据数组 `durationValues`（12个月的数据）。
   - 构建已发生月份数组 `durationValuesPast` 和未发生月份数组 `durationValuesFuture`。
   - 当为今年时，`durationValuesPast` 在索引 `0` 到 `currentMonth - 1` 处填入数据，其余处填 `null`；`durationValuesFuture` 在索引 `currentMonth - 1` 到 `11` 填入数据，其余处填 `null`。
   - 通过在当前月份（`currentMonth - 1`）重合，使两条折线在视觉上无缝拼接。
   - 当为往年时，数据全部归入 `durationValuesPast`。
   - 当为未来年份时，数据全部归入 `durationValuesFuture`。

2. **图表系列配置 (Series)**：
   - 将原来单一的“故障时长”折线系列拆分为两个折线系列。
   - **已发生/过去月份系列**：颜色设为深青色 `#078087`，面积填充 `areaStyle` 颜色 `#078087`。
   - **未发生/未来月份系列**：颜色设为浅灰色 `#cbd5e1`，面积填充 `areaStyle` 颜色 `#cbd5e1`。
   - 二者的 `areaStyle` 不透明度均设为 `0.08`。
   - 移除 `visualMap` 的配置。

## 3. 修改范围
修改只限于插件静态度目录下的 `statistics_dashboard.js`：
- 子公司绩效运行月历图：[initBranchPerformanceRuntimeCalendarCharts](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js#L1996-L2147)
- 业务卡片运行月历图：[initServiceRuntimeCalendarCharts](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js#L3382-L3526)

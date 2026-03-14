# Netbox OTN 可视化插件 - 故障详情页时间轴视图实现计划

## 1. 需求说明
将故障详情页内的 5 个关键时间字段（故障中断、处理派发、维修出发、到达现场、故障恢复）按照提供的设计图样式转换为顶部的水平时间轴节点视图，并在时间轴上方显示故障发生日期和总处理时长。节点之间需要显示各阶段的耗时。

## 2. 设计与实现步骤

### 第 1 步：模型方法扩展 (netbox_otnfaults/models.py)
在 `OtnFault` 模型中新增一个方法或属性（如 `timeline_steps` 和一段通用的时长计算方法），返回构造时间轴所需的数据字典：
- **阶段状态与时间**：
  1. 故障中断 (`fault_occurrence_time`)
  2. 处理派发 (`dispatch_time`)
  3. 维修出发 (`departure_time`)
  4. 到达现场 (`arrival_time`)
  5. 故障恢复 (`fault_recovery_time`)
- **耗时计算**：提取相邻两个存在的时间戳作差，格式化为 `X分Y秒` 或是 `X天Y小时Z分W秒` 的短格式文本。如果某个时间未填写，则后续耗时显示空白或隐藏。
- **总耗时**：计算 `fault_occurrence_time` 到 `fault_recovery_time` 的差值。

### 第 2 步：完善模板展示 (netbox_otnfaults/templates/netbox_otnfaults/otnfault.html)
- 在页面的 `{% block content %}` 顶部（2列布局之前）创建一个新的排版区域（全宽的 `card` 或无边框容器）。
- 利用自定义 CSS（甚至直接写在 `<style>` 标签或模板内部）重现原图中的深色底框、各彩色的发光节点圆圈、渐变连线及时间文本。
- 将原来的以 `table` 行显示的那几个时间（如故障中断时间到封包时间的表格行）或者保留封包时间，但去除前 5 个基础时间点的表格行以避免信息重复。

### 第 3 步：样式细节开发 (CSS & HTML 结构)
- 容器背景采用深蓝/黑灰色（近似 `#232734`）。
- 节点：分为 `red`, `blue`, `cyan`, `green`, `bright-green`。
- 图标：使用 MDI 字体图标如 `mdi-flash`, `mdi-refresh`, `mdi-truck`, `mdi-map-marker`, `mdi-check`。
- 采用 Flexbox 布局让节点居中对齐，并在每个节点间加入带有对应颜色渐变的连接线和用时微章。
- 日期和总时长的药丸形徽章置于容器左上角。

## 3. 测试与验证
1. 在无真实后端数据情况下，可以通过审查浏览器 HTML/CSS 以及运行模板单元验证逻辑。
2. 添加测试时间数据，验证是否只有 `fault_occurrence_time` 时，后续节点灰色或者无连线时长；完整 5 个时间时的正常展现，时长计算逻辑是否准确无误。

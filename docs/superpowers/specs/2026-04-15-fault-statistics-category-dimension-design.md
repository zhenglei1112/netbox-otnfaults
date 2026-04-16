# 故障统计物理故障维度扩展设计

**日期：** 2026-04-15

**目标**

在“故障统计”页面的“物理故障统计”Tab 中新增一个统计维度“故障类型”，作为第 4 张图表展示，并保持与现有三张图表一致的交互能力：

- 图表展示该时间范围内的故障类型分布
- 点击图表项可下钻筛选明细表
- 图例可用于排除维度值
- “清除图表过滤”可以恢复该维度在内的所有图表过滤状态

## 背景与当前实现

当前物理故障统计由以下文件组成：

- `netbox_otnfaults/statistics_views.py`
- `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`
- `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`

当前页面已有 3 个图表维度：

- 光缆属性 `resource_type`
- 省份 `province`
- 一级原因 `reason`

当前后端接口 `FaultStatisticsDataAPI` 已经在明细数据中返回：

- `category`: `fault.get_fault_category_display()`

这意味着明细表已经具备按“故障类型”过滤的必要字段，但后端 `charts` 返回值和前端图表区尚未把该维度独立展示出来。

## 范围

本次变更只覆盖“物理故障统计”Tab。

包含：

- 后端新增 `charts.category`
- 前端新增第 4 张图表“故障类型分布”
- 新增该图表的点击下钻和图例排除行为
- 将“清除图表过滤”扩展到该维度
- 增加对应回归测试

不包含：

- 不改动“业务故障统计”Tab
- 不改动 `OtnFault` 模型或数据库结构
- 不新增筛选器表单项
- 不改动 NetBox 核心目录

## 方案比较

### 方案 A：新增第 4 张图表

在现有 3 张图表旁新增“故障类型分布”。

优点：

- 最符合“增加一个统计维度”的直观预期
- 对现有数据结构改动最小
- 与现有图表交互方式完全一致，用户学习成本最低

缺点：

- 图表区需要从 3 列改成 4 列响应式布局

### 方案 B：做成维度切换器

在单个图表容器里切换“光缆属性 / 省份 / 原因 / 故障类型”。

优点：

- 页面更紧凑

缺点：

- 隐藏了其他维度，不符合本次“增加统计维度”的诉求
- 交互复杂度更高

### 方案 C：仅新增后端字段，不做 UI

优点：

- 改动最小

缺点：

- 用户无法直接看到新增维度，目标未完成

## 选定方案

采用方案 A：新增第 4 张图表。

## 数据设计

### 数据来源

故障类型直接使用 `OtnFault.fault_category`，展示文案使用 `fault.get_fault_category_display()`。

当前可覆盖的类型包括：

- 光缆中断
- 空调故障
- 光缆劣化
- 光缆抖动
- 设备故障
- 供电故障

### 后端返回结构

在 `FaultStatisticsDataAPI` 的 `charts` 中新增：

```json
"category": [
  {
    "name": "光缆中断",
    "value": 12,
    "duration": 36.5
  }
]
```

字段含义与现有 `reason` 维度一致：

- `name`: 故障类型展示名
- `value`: 故障次数
- `duration`: 累计时长（小时）

### 明细过滤字段

明细数据继续使用现有的：

- `details[].category`

前端点击“故障类型”图表时，直接按 `details.category` 进行本地过滤，不新增额外的 raw key 字段。

## 页面与交互设计

### 图表布局

当前图表区是 3 张图表并排布局。变更后调整为 4 张图表：

- 光缆属性分布
- 各省份故障 Top 10
- 主要原因分析
- 故障类型分布

建议容器列宽改为：

- `col-md-6 col-xl-3`

这样可以满足：

- `xl` 及以上屏幕一行 4 张
- `md` 到 `lg` 屏幕每行 2 张
- 小屏保持纵向堆叠

### 图表类型

“故障类型分布”使用 Pie 图，复用当前 `reason` 图表的展示方式，原因如下：

- 类型数有限，适合做占比对比
- 实现上可直接复用现有 tooltip、legend、click 模式
- 与“主要原因分析”视觉风格一致，用户理解成本低

### 下钻行为

新增维度后，交互规则与现有图表保持一致：

- 点击某个饼图分片时，设置 `activeFilterField = 'category'`
- 设置 `activeFilterValue = params.name`
- 明细表仅展示 `item.category === activeFilterValue` 的记录
- 过滤摘要区显示“下钻：故障类型=xxx”

### 图例排除

新增 `excludedCategories.category` 集合。

行为与现有 `resource_type`、`reason` 一致：

- 某图例取消勾选时，将该值加入排除集合
- 明细表过滤掉对应 `category`
- 摘要区显示“排除故障类型[...]”

### 清除过滤

“清除图表过滤”按钮需要同时清理：

- `activeFilterField`
- `activeFilterValue`
- `excludedCategories.category`

并触发新图表的 `legendAllSelect`，保证 4 个图表的状态恢复一致。

## 视觉设计

“故障类型分布”颜色采用与 `FaultCategoryChoices` 语义一致的前端映射：

- 光缆中断: `#8B5CF6`
- 空调故障: `#14B8A6`
- 光缆劣化: `#F97316`
- 光缆抖动: `#06B6D4`
- 设备故障: `#EC4899`
- 供电故障: `#6366F1`

若出现未映射值，回退到 ECharts 默认色。

## 实现边界

### 后端

修改：

- `netbox_otnfaults/statistics_views.py`

新增一个 `category_stats` 聚合字典，构造方式与 `reason_stats` 类似。

返回时在 `charts` 中追加：

- `category`

### 模板

修改：

- `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`

需要：

- 新增 `id="chart-category"` 容器
- 将 3 列图表布局改为 4 列响应式布局

### 前端脚本

修改：

- `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`

需要：

- 新增 `chartCategory` 实例初始化
- 把 `excludedCategories` 扩展到 `category`
- 为 `chartCategory` 绑定点击和 `legendselectchanged`
- 在 `renderCharts()` 中新增 category 图表渲染
- 在 `renderDetailsTable()` 中增加 category 排除和下钻条件
- 在清除过滤逻辑中恢复 category 图例状态

### 同步小范围清理

`statistics_dashboard.js` 当前已经存在重复的 click 绑定代码。由于本次要继续扩展同一套事件和过滤状态，实施时应同步做一次小范围整理：

- 保留一套统一的图表 click 绑定
- 保留一套统一的图例排除绑定
- 不重构到新模块，不拆文件，只做当前文件内的去重和收敛

该清理只限统计页脚本，避免扩大改动面。

## 测试与验证

由于当前仓库缺少完整的 NetBox 运行环境，本次验证分两层：

### 自动化回归

新增或更新测试，至少覆盖：

- 后端源码中返回了 `charts.category`
- 模板中存在 `chart-category`
- 前端中存在 `chartCategory` 初始化
- 前端中存在 `category` 的点击下钻和图例排除逻辑

### 浏览器验证

在可访问页面的浏览器环境中验证：

1. 物理故障统计页出现第 4 张图表
2. 图表显示故障类型分布数据
3. 点击某个故障类型后，明细表正确下钻
4. 图例取消勾选后，明细表按排除规则更新
5. 点击“清除图表过滤”后，所有过滤恢复
6. 页面在桌面端和中等宽度窗口下布局正常

## 风险与控制

### 风险 1：前端脚本继续堆积重复绑定

当前统计页脚本已有重复 click 绑定。若直接在现状上继续追加，很容易造成重复触发或后续维护混乱。

控制方式：

- 在本次实现中顺手收敛重复绑定
- 不扩大为整页重构，只做当前新增维度所需的最小整理

### 风险 2：布局压缩导致图表过窄

四图并排后，`md` 级别下若仍保持 3 列逻辑，会导致图表区域过窄。

控制方式：

- 使用 `col-md-6 col-xl-3`
- 保证中屏幕自动变成两列布局

### 风险 3：显示名过滤与原始值不一致

本次前端下钻按 `details.category` 的展示名过滤，而不是 raw key。

控制方式：

- 后端图表与明细都统一使用 `get_fault_category_display()`
- 避免前后端一边传 raw key、一边用展示名导致过滤失败

## 验收标准

满足以下条件时，认为本次设计目标达成：

- 物理故障统计区新增“故障类型分布”图表
- 新图表显示当前时间范围内的故障类型统计结果
- 点击图表项可以正确下钻到明细表
- 图例排除和清除过滤对该维度生效
- 页面在桌面端和中屏布局下保持可读
- 不改动 NetBox 核心目录

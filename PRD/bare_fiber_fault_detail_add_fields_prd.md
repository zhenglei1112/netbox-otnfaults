# 裸纤业务故障明细增加省份和原因字段 需求文档

## 1. 业务背景
在故障统计模块的“裸纤业务故障”Tab页面中，下方的故障明细表格缺少了故障发生的省份信息，以及具体的一级、二级故障原因。这不便于运维人员直观地在明细表格中进行问题归类与排查。

## 2. 需求描述
在故障统计模块（裸纤业务故障页）下方的“故障明细”表格中，增加以下三个字段的展示：
1. **故障省份**：显示该故障发生的省份名称（对应 `OtnFault.province`）。
2. **一级原因**：显示该故障的分类一级原因（对应 `OtnFault.interruption_reason` 的显示值）。
3. **二级原因**：显示该故障分类的二级原因（对应 `OtnFault.interruption_reason_detail` 的显示值）。

这三个新增字段的位置必须放在**“业务名称”**之后、**“中断时间”**之前，且原有的**“分类”**列需调整至**“故障省份”**之后。

## 3. 技术实现方案

### 3.1 后端 API 修改
- **文件**：`netbox_otnfaults/statistics_views.py` 中的 `ServiceStatisticsDetailsAPI`。
- **优化查询**：
  在查询 `OtnFaultImpact` 时，优化 `select_related`，添加 `'otn_fault__province'`，以防止产生 N+1 查询问题。
- **数据组装**：
  在 JSON 响应结果列表中，增加以下字段：
  - `fault_province`: 返回故障省份名称（如果不存在则返回空字符串 `""`）。
  - `fault_reason_level1`: 返回故障的一级原因显示名称（如为空则返回空字符串 `""`）。
  - `fault_reason_level2`: 返回故障的二级原因显示名称（如为空则返回空字符串 `""`）。

### 3.2 前端模板与逻辑修改
- **模板文件**：`netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`
  - 修改 `tab-service` 表格，在 `<th>业务名称</th>` 后增加并调整顺序：
    ```html
    <th>故障省份</th>
    <th>分类</th>
    <th>一级原因</th>
    <th>二级原因</th>
    ```
  - 将对应的初始 loading 提示行的 `colspan` 从 `8` 改为 `11`。
- **JS 文件**：`netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
  - 修改 `loadServiceDetails` 函数：根据 `tbodyId` 动态计算 `colspan`。如果 `tbodyId === 'service-details-tbody'` (即裸纤业务表)，则 `colspan` 为 `11`；如果是电路业务表，则 `colspan` 保持为 `8`。该 colspan 适用于数据加载中和加载失败提示。
  - 修改 `renderServiceDetailsTableHtml` 函数：
    - 无结果提示的 `colspan` 同样依据 `tbodyId` 动态调整为 `11` 或 `8`。
    - 渲染每一行数据时，若 `serviceType === '裸纤业务'`，渲染包含 `fault_province`、`fault_category`、`fault_reason_level1` 和 `fault_reason_level2` 等 11 列 HTML，其中“分类”（`fault_category`）放在“故障省份”之后；若是其他业务类型，则保持渲染原来的 8 列。

## 4. 验证与测试
- 启动本地/测试环境，进入故障统计模块 -> 裸纤业务故障 Tab，核对故障明细表格中的“业务名称”后是否出现“故障省份”、“一级原因”和“二级原因”三列，并能正常渲染数据。
- 检查电路业务故障 Tab 下的表格是否显示正常，没有受影响（维持原有8列布局）。

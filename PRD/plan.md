# OTN故障统计周报自定义脚本需求文档与执行计划

## 项目背景与需求目标
为满足每周定期统计并通报OTN光纤故障情况的需求，计划开发一个NetBox Custom Script (`extras.scripts.Script`)。该脚本将依据设定的时间周期（如：上周六至本周五），自动抓取 `OtnFault` 和 `OtnFaultImpact` 数据，进行多维度的挖掘与聚合，输出符合特定文本格式的 Markdown 报告。

要求实现“一键生成周报文本”，包含周度总体故障情况、同比上上周的数据对比、各细分故障原因（道路施工、线路整改等）次数、累计中断时长及长历时故障详情，最后附上重点裸纤业务（如百度、华为、腾讯等相关业务）的影响情况分析。

---

## 1. 业务逻辑与字段映射分析

### 1.1 查询周期定界
- 以“周六至周五”为一个计算周期。
- 脚本默认输入：`start_date`（周六）和 `end_date`（周五）。如果未提供，默认计算上周六到本周五。
- 需同时推算出上一周期（上上周六至上周五）的时间段作为“同比”基准。

### 1.2 宏观统计指标
- **总处理次数**：时间窗口内 `OtnFault` 的发生总数。
- **自建/协调/租赁次数**：过滤 `OtnFault.resource_type`。
- **总中断时长**：累加 `fault_recovery_time - fault_occurrence_time`。未恢复的计算到当前或区间结束。
- **去除道路施工后的总时长**：排除 `interruption_reason == 'construction'` 的记录。

### 1.3 细分故障原因统计
- 对应模型中的数据获取方式如下：
  - **道路施工**：`interruption_reason == 'construction'`
  - **线路整改**：`interruption_reason == 'cable_rectification'`
  - **自然劣化**：`fault_category == 'fiber_degradation'`
  - **无法查明**：`interruption_reason == 'unknown'`
  - **自然灾害**：`interruption_reason == 'natural_disaster'`
  - **交通事故**：`interruption_reason == 'traffic_accident'`
  - **动物破坏**：`interruption_reason == 'animal_damage'`
  - **线路抖动**：`fault_category == 'fiber_jitter'`
  - **尾纤损坏**：`cable_break_location == 'pigtail'` 或 `recovery_mode == 'tail_fiber_replacement'`

### 1.4 省份维度与重点故障段分析
- **省份**：获取 `OtnFault.province.name`。
- **中断次数较多/时长较长的省份**：聚合查询。
- **频繁故障段落**：提取 `interruption_location_a` 到 `interruption_location` 的站点名称。

### 1.5 裸纤业务线路中断情况表
- 查询所匹配的 `BareFiberService`（如 百度、华为 等预置名单）。
- 结合 `OtnFaultImpact` 进行分析：
  - **抖动次数**：影响关联的故障 `fault_category == 'fiber_jitter'`。
  - **业务阻断次数**：关联的故障不属于抖动的。
  - **阻断历时**：`service_recovery_time - service_interruption_time`。
  - **重点故障段**：提取省份 + A/Z站点 + 资源所有权与处理类型拼接（如山东兴隆租赁割接）。

---

## 2. 无法实现的需求点（重点说明）

经过模型交叉比对，目前下列用户原始需求由于后端缺少对应的数据字段或维度模型，**无法通过脚本自动实现，将在脚本输出中采取占位符（如 "___" 或 0）处理**：

1. **线路整改（满足/未满足24小时前报备）的次数统计**
   - **原因分析**：当前的 `OtnFault` 表中**不存在**“是否提前24小时报备”的相关字段，无法判定报备时间合规性。脚本中只能统计“线路整改”的总次数。
2. **重点故障段智能拼接**
   - **原因分析**：如“山东兴隆租赁割接”，系统虽然分别有 省份(山东)、站点(兴隆)、光纤来源(租赁)、原因(割接/整改) 字段，但拼接呈现上无法做到像人脑一样提取核心关键字。如果站点名叫“济南兴隆节点机房”，拼接出来可能过长。将采用 `故障所在省份 + 核心站点关键词 + 光纤来源` 粗略拼接替代。

---

## 3. 技术实现方案：NetBox Custom Script (`extras.scripts.Script`)

**脚本部署位置**：`d:\Src\netbox-otnfaults\netbox_otnfaults\scripts\weekly_report.py`

### 3.1 脚本入参定义 (`ObjectVar` 等)
- `start_date`：`DateVar`，选填，留空自动生成。
- `end_date`：`DateVar`，选填，留空自动生成。

### 3.2 核心代码流程
1. **日历推演**：利用 `datetime` / `timezone` 确定 `current_start`, `current_end`, `previous_start`, `previous_end`。
2. **多重查询**：对 `OtnFault` 的时长做 `annotate` 和 `aggregate` 计算，提取各个统计口径的记录。
3. **主因排序脱水处理**：通过 `Counter` 遍历统计主因（排除 `cable_rectification` 和 `fiber_jitter`），提炼前三名名称。
4. **长历时故障提取**：迭代排查大于 8 小时且非施工的故障，组装报告字典。
5. **裸纤业务影响迭代**：建立一个业务特征名的预置匹配库（比如 `["百度 昆汉广", "百度 京南昆", "华为 京汉广", "腾讯 上海至武汉"]` 等）。通过 `OtnFaultImpact.objects.filter(bare_fiber_service__name__contains=xxx)` 获取精确结果汇总累加。
6. **最终 Markdown / TXT 输出**：利用 `self.log_info()` 和 Python 字符串模板渲染并输出完整文本块，让运维人员可以直接拷贝。

## 4. 后续任务分配清单
1. 在 `d:\Src\netbox-otnfaults\netbox_otnfaults\scripts\weekly_report.py` 写入脚本源码。
2. 进行测试验证。

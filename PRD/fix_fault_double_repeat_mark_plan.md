# 需求文档：故障统计模块故障明细双向重复数据标记优化

本项目为 Netbox 4.4.2 自定义插件，用于管理光传送网（OTN）故障。本需求文档旨在对故障统计模块中重复故障的数据标记进行优化，确保同组重复故障的所有条目均能在 UI 列表中标记并突出显示为“重复”数据。

## 1. 业务背景与问题现象

在故障统计模块的故障明细列表中，加入了“按重复排序”以及“重复故障检测与前续历史故障回溯”功能。原重复判断逻辑采用“单向匹配”机制：
对于发生时间处于同一 60 天周期的两条重复故障 A（较早发生）与 B（较晚发生）：
- 系统仅检测并标记较晚发生的 B 为重复故障（即 B 的 `is_repeat` 为 `True`）；
- 较早发生的 A 无法与 B 建立重复反馈（A 的 `is_repeat` 依旧为 `False`）。

**问题与反馈**：
这种单向标记导致在故障明细列表中：
1. A 无法获得“重复”标签（徽章），用户容易误以为 A 是独立、唯一的故障；
2. A 会被当成普通非重复数据，导致无法参与前端的“按重复排序”的组聚类，使得本是同一重复事件的一对（或多条）故障在 UI 上无法挨在一起，破坏了重复排序的聚合效果。

**优化目标**：
在存在重复关联的情况下，**同一对（或多条）故障的所有条目都应标记为重复数据**，以便在列表中均显示“重复”标签，并可在“按重复排序”模式下聚集在同一个组中展示。

---

## 2. 详细技术方案

### 2.1 统计数据 API 调整 (`FaultStatisticsDataAPI`)

在 `netbox_otnfaults/statistics_views.py` 中，需要将宏观 KPI（重复故障总数卡片）与列表明细的重复状态（`is_repeat`）解耦。
- **原因**：如果明细列表直接改为双向判定，原先 KPI 计为 1 的重复故障此时会因为两个端点都被标记而变为 2。所以，必须区分 UI 展示标记与 KPI 统计标记。

#### 逻辑实现代码：

在 `FaultStatisticsDataAPI.get` 方法中：

1. **宏观 KPI 统计**（保持单向）：
   ```python
   # 仅检查先前发生的故障，用作大屏 KPI 卡片的计数口径
   is_repeat_kpi = False
   for pf in past_faults_list:
       if pf.id != fault.id and pf.fault_occurrence_time < fault.fault_occurrence_time:
           if (fault.fault_occurrence_time - pf.fault_occurrence_time) <= timedelta(days=60):
               if pf.interruption_location_a_id == fault.interruption_location_a_id:
                   pf_z_site_ids = fault_z_sites_cache.get(pf.id, set())
                   if pf_z_site_ids.intersection(fault_z_site_ids):
                       is_repeat_kpi = True
                       break
   ```

2. **明细项 UI 展示标记**（双向）：
   ```python
   # 检查前后 60 天内的所有故障，用于列表 UI 打标与排序聚合
   is_repeat_ui = False
   for pf in past_faults_list:
       if pf.id != fault.id:
           if abs(fault.fault_occurrence_time - pf.fault_occurrence_time) <= timedelta(days=60):
               if pf.interruption_location_a_id == fault.interruption_location_a_id:
                   pf_z_site_ids = fault_z_sites_cache.get(pf.id, set())
                   if pf_z_site_ids.intersection(fault_z_site_ids):
                       is_repeat_ui = True
                       break
   ```

3. **赋值与累加**：
   - 如果 `is_repeat_kpi` 为真，则 KPI 的 `repeat_faults_count += 1`。
   - 在 `details.append` 时，为字典设定 `'is_repeat': is_repeat_ui`。

---

## 3. 验证计划与回归测试

### 3.1 自动化单元测试回归
- 执行大屏统计相关的测试类，检验是否有 KPI 计数发生变动（由于解耦，卡片 KPI 的计算将保持一致，理应无破坏）：
  - 运行命令：`python -m unittest tests.test_statistics_dashboard_assets.py`
  - 运行命令：`python -m unittest tests.test_statistics_cable_break_overview.py`

### 3.2 手动功能核验
- 选择一个有重复故障发生的统计周期。
- 查看明细列表，确认原本没带重复徽章的第一条发生故障（例如 F20260403006）现在在 UI 上和后发生的故障均拥有“重复”的紫色标签。
- 切换为“按重复排序”，确认同一重复链条的所有故障成功聚类排列，第一条故障已经无缝编入重复组中，没有掉落和散开。

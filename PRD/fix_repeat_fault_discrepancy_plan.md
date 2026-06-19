# 修复重复故障卡片与下钻明细数量不一致及排序重复数据的执行计划

## 问题背景与原因

在故障统计的物理故障页面中，用户发现“重复起数”卡片显示的数字（例如 9 起）与点击卡片下钻过滤出的故障明细数量（例如 8 起）不一致。

经过排查，两处接口在判定重复故障时使用的**前序对比故障库的时间上限与过滤逻辑不一致**：
1. **统计卡片计算**：对比库 `past_faults_list` 的时间上限是当期结束时间（`lt=end_date`），未限制任何过滤条件（如未挂起过滤、省份过滤）。因此，同统计周期内挂起的故障或被过滤掉的故障可以作为背景对比源。
2. **下钻列表计算**：对比库 `preceding_qs` 的时间上限是当期开始时间（`lt=start_date`），这导致当期统计周期内的所有已被排除的故障（如挂起故障、其他省份故障等）在计算重复时被彻底漏掉。任何依赖这部分故障判定为重复的故障在明细中会被误判为非重复。

**引入的新问题**：
为了使下钻过滤出的数量和卡片一致，将下钻对比范围上限由 `lt=start_date` 修改为 `lt=end_date if end_date else now`。这导致 `preceding_qs` 对比库中包含当期周期内的全部故障。
在进行重复故障匹配检测 `detect_repeat_faults` 时，当期发生的某个故障 A 在与对比库匹配时，会被作为 `matched_preceding_faults`（前序匹配故障）捕获并返回。
后端在接口中将当期故障（`current_faults`，标记 `in_period: true`）与匹配故障（`matched_preceding_faults`，标记 `in_period: false`）一同返回，前端在“按时间排序”时会过滤 `in_period !== false`，但在“按重复排序”时不会过滤，导致同一个故障在列表中出现一亮一灰（双重显示）的重复行。

## 解决方案

1. **下钻对比库上限调整**：
   将下钻明细接口中的 `preceding_qs` 对比故障范围上限由 `lt=start_date` 修改为 `lt=end_date if end_date else now`。使得下钻列表判定重复时，能与指标卡片采取完全一致的对比背景，消除数据不一致。
2. **后端去重过滤**：
   在后端下钻明细接口中，计算出匹配故障 `matched_preceding_faults` 后，主动剔除其中已经包含在当期故障 `current_faults` 中的数据。确保同一个故障在返回的 `results` 列表中只以高亮的 `in_period: true` 形式出现一次，消除前端按重复排序时的行重复。

## 修改位置

修改文件：[statistics_views.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/statistics_views.py)

修改行区间：第 2824-2856 行附近。

```python
                preceding_qs = OtnFault.objects.filter(
                    fault_occurrence_time__gte=min_t - timedelta(days=60),
                    fault_occurrence_time__lt=end_date if end_date else now, # 上限调整
                    fault_category__in=[FaultCategoryChoices.FIBER_BREAK, 
                                        FaultCategoryChoices.FIBER_DEGRADATION, 
                                        FaultCategoryChoices.FIBER_JITTER]
                )
                ...
                repeat_result = detect_repeat_faults(
                    current_faults,
                    preceding_faults,
                    preceding_faults=preceding_faults,
                )
                kpi_repeat_ids = repeat_result.kpi_repeat_ids
                ui_repeat_ids = repeat_result.ui_repeat_ids
                matched_preceding_faults = repeat_result.matched_preceding_faults
                
                # 剔除当期已包含的故障，防止按重复排序时发生数据重复显示
                current_ids = {f.id for f in current_faults}
                matched_preceding_faults = [f for f in matched_preceding_faults if f.id not in current_ids]
                
                if detail_scope == 'cable_break':
                    matched_preceding_faults = []
```

## 验证计划

1. 代码修改后，确认系统不再报告“口径核对不一致”。
2. 检查下钻明细列表中显示的数据行数是否与卡片上的数量保持完全一致。
3. 切换“按重复排序”和“按时间排序”，检查列表不再出现任何完全一致（亮灰成对）的重复故障。
4. 运行物理故障统计单元测试，验证修改无 Regression。
   单元测试命令：`.\.venv\Scripts\python.exe -m unittest tests/test_statistics_cable_break_overview.py`

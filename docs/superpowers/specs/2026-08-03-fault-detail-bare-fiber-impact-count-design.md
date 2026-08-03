# 故障明细显示裸纤业务中断数量设计

## 目标

在故障统计模块的物理故障明细和子公司故障明细中增加“裸纤业务中断”列，显示每条物理故障实际中断的去重裸纤业务数量。没有影响时显示 `-`，不显示 `0`。

## 统计口径

数量基于故障关联的 `OtnFaultImpact` 记录计算，并同时满足：

- `service_type=ServiceTypeChoices.BARE_FIBER`；
- `business_impact=BusinessImpactChoices.INTERRUPTED`；
- `bare_fiber_service_id` 非空；
- 按 `bare_fiber_service_id` 去重。

该数量表示故障自身影响的裸纤业务总数，不受故障统计页面当前时间筛选影响。时间筛选决定展示哪些故障行，不裁剪一条故障自身的关联业务数量。

## 后端设计

在 `FaultStatisticsDetailsAPI` 的 `OtnFault` 查询上增加带条件的 `Count` 注解，一次查询得到 `bare_fiber_impact_count`，避免逐行查询：

```python
Count(
    'impacts__bare_fiber_service',
    filter=Q(
        impacts__service_type=ServiceTypeChoices.BARE_FIBER,
        impacts__business_impact=BusinessImpactChoices.INTERRUPTED,
        impacts__bare_fiber_service__isnull=False,
    ),
    distinct=True,
)
```

当前周期故障与回溯展示的历史重复故障均返回整数类型的 `bare_fiber_impact_count`。

## 前端与表格设计

- 物理故障明细和子公司故障明细增加“裸纤业务中断”表头。
- 新列位于“站点 (A → Z)”之后、“标签”之前。
- `bare_fiber_impact_count > 0` 时显示整数；否则显示 `-`。
- 两张表及其加载、空结果提示的列数从 11 调整为 12。
- 裸纤业务故障 Tab 和电路业务故障 Tab 的明细结构不变。

## 测试与验收

- 后端源码回归测试锁定带条件、去重的 `Count` 注解和返回字段。
- 模板测试锁定两张物理故障表的表头位置及 `colspan=12`。
- JavaScript 测试锁定当前故障、历史重复故障两种行渲染均使用 `bare_fiber_impact_count`，并在 0 时输出 `-`。
- 运行全部统计模块测试、Python 编译、JavaScript 语法和差异检查。

## 非目标

- 不修改裸纤业务中断四张卡片的统计公式。
- 不在业务故障明细表中增加该列。
- 不新增数据库字段或迁移。

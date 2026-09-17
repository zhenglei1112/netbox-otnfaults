# 故障统计性能测试与瓶颈排查

## 启用与关闭

在 NetBox 现有插件配置中增加以下配置项（合并进现有配置，不要覆盖其他键），按现有部署流程加载代码、更新静态资源并重启应用：

```python
PLUGINS_CONFIG['netbox_otnfaults']['statistics_diagnostics'] = True
```

使用具有统计查看权限的 staff/superuser 账户，在故障统计页面 URL 末尾增加 `?statistics_debug=1`，已有参数时使用 `&statistics_debug=1`。不需要开启全局 `DEBUG`；开发环境已有 `DEBUG=True` 时也可使用。页面顶部出现可折叠诊断区，提供“分析当前记录”和“导出诊断 JSON”。管理员开关和 URL 参数须同时生效，才会返回后端明细。

诊断状态仅用于当前页面，不写 localStorage，不永久拦截全站 fetch。去掉 URL 参数并刷新即关闭。服务器配置默认 False。普通请求不记录 SQL，不添加诊断响应字段；没有管理权限的请求也不能绕过缓存。

强制计算测试使用 `statistics_debug=1&statistics_cache_bypass=1`：仅跳过统计汇总业务缓存的读取和写入，不清理缓存，不影响其他用户的缓存。它不是数据库、操作系统或 Redis 的真正冷启动。不要将其称为全栈冷缓存测试。

## 采集内容与读数

| 层次 | 采集项 | 解释 |
|---|---|---|
| 初始导航 | 首字节、DOM 就绪、load | 浏览器 Navigation Timing，包含文档和资源加载；不代表异步统计全部完成 |
| 用户交互 | 日期、省份、Tab、指标、排序对应的 action_id | 每次操作后等待网络请求完成；连续快速操作另列场景 |
| 请求 | 接口、范围、状态、headers_ms、body_and_json_ms、complete_ms、明细条数 | headers_ms 包含网络/排队/后端；body_and_json_ms 包含响应体传输与 JSON 解析，不能视为纯解析 CPU |
| 后端 | total_ms、sql_ms、sql_count、response_bytes、cache | total_ms 为视图执行到原始响应完成，不包含外部中间件、网络、诊断元数据二次编码；response_bytes 为加入诊断前的未压缩响应大小 |
| 计算阶段 | 当前/对比周期、主管/子公司、绩效、重复检测、裸纤、日趋势、查询集加载 | ms 含子调用，self_ms 扣除被计时的直接子调用；self_ms 仍可能包含 SQL、未埋点函数和序列化，不是纯 CPU |
| SQL | 指纹、所属阶段、次数、累计/最大耗时 | 使用 Django execute_wrapper；不存 SQL 文本、查询参数、密码或 Token。执行耗时不完全覆盖结果抓取与模型实例化 |
| 前端 | 图表、绩效卡片、明细、重复分组及排序同步耗时 | 包含同步 setOption/DOM 操作，不包含完整异步动画、布局和最终绘制；长任务辅助判断主线程阻塞 |

阶段和前端嵌套函数的 ms **不可相加**。后端按 self_ms 排序定位自身耗时；结合 sql_ms 区分查询与其他工作。同一 SQL 指纹高频出现是 N+1/重复查询线索，不直接等于根因。

`cache` 取值：`hit`、`miss`、`bypass`、`live_period_uncached`、`not_applicable`。当前未结束周期不走汇总缓存；明细和业务接口标记为 not_applicable。对比周期阶段名包含起始日期，区分环比与同比。

前端最多保留最近 1000 条记录，SQL 最多记录 100 个“指纹+阶段”组合并将剩余计入 other，导出耗时最高的 20 组。每一轮测试后导出，避免前序记录被淘汰。导出只含诊断信息及白名单筛选维度，不含故障明细正文。诊断本身有开销，优化前后应使用相同配置。

## 可重复测试矩阵

固定账户、数据快照、浏览器、设备和网络。选一份数据量大的已结束月份及一个当前月份；每个场景先预热 1 次，再记录至少 5 次（正式 P95 建议 20 次），每组单独导出。不要把不同年份、数据量、缓存模式混在同一组。

| 编号 | 操作 | 必须记录/比较 |
|---|---|---|
| A | 首次打开统计页、刷新 | Navigation、汇总+明细请求数量、总体完成时间、资源是否缓存 |
| B | 已结束月份，先 bypass，再正常访问两次 | bypass/miss/hit 分组；同参数命中后计算阶段应消失，不能将 miss 当 hit |
| C | 当前月/周，连续刷新 | live_period_uncached 下的数据库、分组和绩效耗时 |
| D | 周→月→季度→年，前后日期切换 | 数据规模增加时查询/重复判定/响应体/DOM 是否明显增长 |
| E | 全省→单省→多省→全省 | 切换省份是否还重算无关的主管和子公司；请求参数与缓存状态 |
| F | 物理→主管→子公司→绩效→物理，不改日期 | 相同汇总请求重发次数、隐藏页图表和明细是否被重新构建 |
| G | 裸纤→电路→裸纤 | 同时请求两类明细、年度/月历响应与卡片绘制耗时 |
| H | 指标/图表下钻、清除、按时间/重复排序 | 明细数量、历史关联记录、sortDetailRows/assignRepeatGroupColors 耗时 |
| I | 连续快速切换日期/Tab 3 次 | Network 查看重叠、无效/过时请求；单独导出，不与单次串行测试混算 |

串行测试的 action_id 最可靠。快速切换时，request 的 action_id 固定为发起时交互；渲染/长任务关联当时最近的交互，可能来自较早请求，不能将该关联视为因果证明。Network 使用 request_id 与响应头 `X-Statistics-Request-ID` 对照。

导出后生成报告：

```powershell
python scripts/analyze_statistics_performance.py report-1.json report-2.json
```

输出请求中位数/P95、后端自身耗时 Top 15、前端渲染 Top 15 和自动线索。单次场景少于 20 个样本时 P95 接近最大值，只用于初筛。自动阈值：SQL ≥100 次、SQL 执行占视图耗时 >50%、原始响应 >1MiB、同步渲染 ≥50ms、同一交互同参数重复请求。这些是排查阈值，不是业务 SLA。

## 代码审查已确认的重复工作与待测瓶颈

以下已确认的是执行路径，**实际耗时排名尚待部署环境采集，不是线上压测结论**。

| 优先排查 | 代码证据/触发条件 | 如何验证 | 后续优化方向 |
|---|---|---|---|
| 每次加载三套完整故障明细 | `loadData()` 成功后无条件调用 loadFaultDetails、loadBranchDetails、loadSupervisorDetails | 每次进入/改日期/省份后应可看到汇总+三明细；比较响应字节/条数及 SQL | 仅加载当前 Tab 明细、延迟下钻、按范围复用 |
| 切换 Tab 重复汇总 | `shown.bs.tab` 对物理、主管、子公司、绩效均执行 loadData | 不改日期切回时检查相同请求及缓存 hit 仍有三明细 | 前端按参数缓存，Tab 切换复用，失效后再取 |
| 同期对比重复年度计算 | 汇总计算环比、同比、当前；每周期均构建子公司和主管分组，子公司还计算绩效/年度裸纤 | 常规汇总未命中时可见 6 次 group_statistics、3 次 performance_cards；按实际周期参数确认 | 将年度趋势/绩效与周期指标分离，复用同年份结果 |
| 省份导致无关数据重算 | 汇总缓存键含省份，但子公司/主管使用未经过省份过滤的数据 | 切省份时 group_statistics/绩效阶段仍出现 | 拆分物理省份缓存与固定范围缓存 |
| 当前周期不缓存 | is_ended 为 False 时跳过汇总缓存；明细/业务接口亦无该汇总缓存 | live_period_uncached 与已结束 hit 比较 | 短 TTL/事件失效，避免盲目增加长缓存 |
| 重复故障计算多次扫描 | `_count_repeat_fiber_faults`、`_build_repeat_fault_id_set` 遍历当前与历史候选；前端分组/排序再次匹配站点和 60 天窗口 | count_repeat_fiber_faults/performance_repeat_ids/sortDetailRows 阶段随条数增长 | 按站点和时间窗口建索引，复用检测结果 |
| 隐藏页绘制及业务双明细 | 汇总同时渲染主管、子公司/绩效图表；业务加载同时拉裸纤、电路明细 | 当前 Tab 下无关 render 阶段及请求仍发生；观察 long_task | 可见页优先渲染、图表复用、延迟卡片/月历 |
| 数据库/N+1（尚未确认） | 多次 select_related/prefetch 与逐条计算、历史关联 | SQL 次数、相同指纹、load_* 与计算阶段 SQL 次数 | 实测后补预加载、合并查询；不能仅凭代码先加索引 |

## 本地验证与限制

执行 Python 统计回归、Node 诊断/主管前端行为测试及 JS/Python 语法检查。覆盖权限开关、默认关闭、SQL 脱敏聚合与容量限制、请求 ContextVar 清理、缓存对象不污染、失败透传、诊断导出及报告分位数。

本仓库没有 NetBox/Django 运行环境，不能在本地给出生产数据耗时、数据库执行计划或实际页面绘制指标。部署后按上述矩阵采集 JSON，才可确定按耗时排序的优化清单。本次仅添加诊断，不修改统计口径、不直接执行缓存清除或部署。

后端数据库采集依据：[Django 5.0 数据库执行包装器文档](https://docs.djangoproject.com/en/5.0/topics/db/instrumentation/)。

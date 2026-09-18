# Netbox OTN 故障管理插件更新说明 - 故障统计模块效率优化

| 发布日期 | 版本号 | 更新类型 |
| :--- | :--- | :--- |
| **2026-09-17** | **v1.7.1** | <span style="background-color: #3b82f6; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">性能优化</span> |

---

# v1.7.1 - 故障统计模块性能与效率问题全面优化及全链路诊断发布 <span style="background-color: #3b82f6; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; vertical-align: middle;">性能优化</span>

### 性能改进

- **重复故障判定算法（detect_repeat_faults）百万次扫描消除与极速重构**：全面重构重复故障判定逻辑，消除内部对千级模型列表的 $O(N)$ 线性扫描并升级为 Set 哈希 $O(1)$ 高速检索；精简历史候选故障 ORM 加载字段（`.only(...)`）并批量预提取站点关系映射（`fault_id -> set of site_ids`）。3000 条故障对象判定耗时从 ~1200ms 降至 10.5ms，性能提升约 114 倍（对应提交 `ca92f55`，修改 `netbox_otnfaults/utils.py`）。
- **全国子公司与主管统计维度解耦与独立二级缓存**：将全国口径统计（子公司、主管维度）与物理省份筛选逻辑解耦，建立按时间维度的独立缓存复用机制。用户切换省份查看时，直接复用全国子公司与主管计算结果，跳过原本耗时 4.5 秒的无谓重算，省份切换响应时间由 6.2 秒降至 50ms 以内，耗时降低 99%（对应修改 `netbox_otnfaults/statistics_views.py`）。
- **未结周期（当前年份/月份）引入 180s 短 TTL 动态缓存机制**：废除此前对当前活跃周期一律穿透数据库（`live_period_uncached`）的无缓存策略；引入 180 秒短 TTL 缓存并与故障增删改信号绑定的版本号（`version_key`）强联动，实现多用户及同用户高频交互秒级响应，年度汇总在缓存期内响应耗时低于 30ms。
- **年度同环比区间重叠计算智能复用**：检测年度统计维度下环比与同比起止日期的完全重合特征，避免重复执行 2 遍全量 SQL 聚合与 Python 对象装配，直接内存复用 `prev_data`，彻底消除 ~800ms 的重复计算与数据库开销。
- **前端明细按需懒加载（Lazy Loading）与并发请求消峰**：彻底废除页面初次加载时无条件并发拉取物理、子公司、主管三大明细接口的做法；改为仅加载当前处于 Active 状态的 Tab 明细，将单次交互并发重请求减少 60%，彻底消除后端 WSGI worker 队列打满导致的 10 秒视图外排队等待异常（对应修改 `static/netbox_otnfaults/js/statistics_dashboard.js`）。

---

### 流程与权限

- **统一筛选快照机制（Filter Snapshot）与多维度参数一致性保障**：前端封装不可变 `getFilterSnapshot()` 状态对象，将当前筛选类型、年份、月份、周次及选定省份固化为原子快照向下透传，彻底解决因异步控件状态变动引发的“周汇总携带年度明细参数”等请求不一致问题。
- **异步并发乱序竞争保护（Request ID Guard）**：为汇总及各 Tab 明细请求引入递增序列号机制，在网络延迟波动导致历史响应滞后到达时，自动比对请求版本并丢弃过时响应，杜绝慢请求覆盖新日期图表与 KPI 指标数据。
- **跨周期在途明细请求失效阻断与状态机自愈**：在发起新周期汇总时立即失效在途的明细请求；建立四阶段状态机（`idle | loading | success | failed`），在汇总偶发异常或失败后，切换 Tab 自动执行就绪校验并触发自动重试恢复，杜绝脏数据残留。

---

### 功能增强

- **全链路性能诊断与劣化预警系统（Statistics Diagnostics）**：全面引入前端与后端性能诊断打点体系，监控各 API 请求全生命周期耗时、SQL 执行开销及 Python 数据装配占比；设定绝对耗时告警阈值（API > 2.0s，SQL > 500ms），并配套自动化诊断分析脚本 `scripts/analyze_statistics_performance.py`，实现性能隐患的可视化排查与常态化监管（对应新增 `statistics_diagnostics.py` 与 `statistics_diagnostics.js`）。

---

### 错误修复

- **修复重复故障判定传参冗余翻倍问题**：修复 `statistics_views.py` 中调用 `detect_repeat_faults` 时同时将 `preceding_faults` 传入位置参数与关键字参数，导致历史候选集合在底层被重复叠加合并、计算量翻倍的逻辑缺陷。
- **修复 Tab 切换无条件触发全量重算缺陷**：修复 Bootstrap 5 Tab 组件切换监听中无条件调用全量 `loadData()` 导致的数据反复刷新问题，改为按需拉取或命中前端缓存直接展示。

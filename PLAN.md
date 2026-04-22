# PLAN

## Statistics cable-break map coordinate fallback audit

- [x] Trace `skipped_count` from the statistics map API through `FaultDataService` and the MapLibre control
- [x] Identify that current fallback uses fault coordinates, then only the A-side site coordinates
- [x] Add a regression assertion that Z-side site coordinates are also considered before skipping a fault
- [x] Update the map data API to return source metadata for A-side and Z-side coordinate fallbacks
- [x] Run the focused source test and Python syntax check

## Statistics cable-break map modal matches picker UI

- [x] Add source regression assertions for picker-style modal structure and manual backdrop behavior
- [x] Align the statistics cable-break map modal header, close button, dialog classes, and iframe sizing with the map picker modal
- [x] Switch the statistics map modal to the same manual DOM show/hide behavior, including the dark 0.85 backdrop and outside-click close
- [x] Run targeted regression tests and JavaScript syntax validation

## Statistics cable-break map marker colors by fault status

- [x] Add source regression assertions that statistics cable-break markers use fault processing status colors
- [x] Update the statistics cable-break map mode to color standard MapLibre markers from `statusColorHex` / `FAULT_STATUS_COLORS`
- [x] Run targeted regression tests and JavaScript syntax validation

## Statistics cable-break map legend shows only statuses

- [x] Add source regression assertions that legend category hiding is scoped to the statistics cable-break map mode
- [x] Make `FaultLegendControl` accept backward-compatible display options for category/status sections
- [x] Configure only the statistics cable-break map mode to hide fault categories and keep processing statuses visible
- [x] Run targeted regression tests and JavaScript syntax validation

## Statistics cable-break map modal GPU usage reduction

- [x] Identify statistics map-specific GPU pressure from globe projection and unconditional 3D buildings layer
- [x] Switch only the statistics cable-break map mode to Mercator projection for modal point display
- [x] Add a scoped `disable3dBuildings` configuration path while preserving shared OTN paths and site layers
- [x] Preserve the province GeoJSON layer with the same fill and boundary styling as the fault distribution map
- [x] Run targeted regression tests and JavaScript/Python syntax validation

## 故障统计页光缆中断概览指标分组样式调整

- [x] 为光缆中断概览分组布局补充源码级回归测试，覆盖组标签下置和组间短竖线
- [x] 调整统计页脚本生成的分组 DOM 结构，使组标签显示在本组指标下方
- [x] 为分组容器补充样式，使用较短的竖向分隔线区分不同指标组
- [x] 运行目标测试与语法校验

## 故障统计页光缆中断概览首行拆分双卡

- [x] 为首行双卡不等宽布局补充源码级回归测试，覆盖卡片间距和主次宽度
- [x] 调整统计页模板，将中断起数和长时中断起数拆为同一行两张卡片
- [x] 调整样式，实现首行双卡不等宽布局，并让各卡片之间保留间隔
- [x] 运行目标测试与语法校验

## OtnFaultImpact list filter multi-select for services

- [x] Add a failing regression test covering multi-select filter fields for `bare_fiber_service` and `circuit_service`
- [x] Update `OtnFaultImpactFilterForm` to use multi-select widgets for both service filters
- [x] Update `OtnFaultImpactFilterSet` to accept multiple selected services
- [x] Run targeted regression tests and Python syntax validation

## OtnFaultImpact list interruption time range filter

- [x] Add a failing regression test covering start/end interruption time fields, filterset range filters, and list template shortcut UI
- [x] Update `OtnFaultImpactFilterForm` to use start/end `service_interruption_time` range fields
- [x] Update `OtnFaultImpactFilterSet` to apply `gte`/`lte` range filtering on `service_interruption_time`
- [x] Add an `otnfaultimpact_list.html` template matching the OtnFault list shortcut UI and bind the list view to it
- [x] Run targeted regression tests and Python syntax validation

## OtnFaultImpact list circuit category/group multi-select filters

- [x] Add a failing regression test covering multi-select filter fields for `circuit_business_category` and `circuit_service_group`
- [x] Update `OtnFaultImpactFilterForm` to expose both circuit-related choice filters as multi-select inputs
- [x] Update `OtnFaultImpactFilterSet` to filter `circuit_service__business_category` and `circuit_service__service_group` with multi-select choices
- [x] Run targeted regression tests and Python syntax validation

## ???????????????????

- [x] ????????????????????????????????/????????????????????
- [x] ?????????????????????????????????????
- [x] ?? `OtnFaultFilterSet` ? `OtnFaultFilterForm`????????????/????????
- [x] ?????????????????????????????????
- [x] ??????? Python ??????????????????

## 修复光缆中断指标切换周期后停留为 0

- [x] 更新统计页光缆中断概览源码测试，覆盖当前卡片结构与趋势对比接口
- [x] 增加前端回归断言，防止趋势箭头渲染删除主指标 DOM id
- [x] 调整趋势箭头渲染逻辑，仅更新数值和箭头占位，不重写父容器
- [x] 运行定向测试、JS 语法检查和 Python 语法校验

## 趋势箭头显示具体差值

- [x] 增加源码级回归测试，要求趋势箭头包含当前期与上期差值
- [x] 调整趋势箭头格式为升降图标加正负差值
- [x] 运行定向测试和 JS 语法检查

## 放大光缆中断分项指标数字

- [x] 增加源码级回归测试，要求动态与静态分项指标使用更大字号
- [x] 将动态分项指标数字从 `fs-4` 调整为 `fs-3`
- [x] 将平均历时静态分项数字从 `fs-4` 调整为 `fs-3`
- [x] 运行定向测试和 JS 语法检查

## 中断总历时原因标签改为原因TOP3

- [x] 增加源码级回归测试，要求中断总历时原因分组标签为 `原因TOP3`
- [x] 将中断总历时的 `reason_duration_top3` 分组标签从 `一级原因` 改为 `原因TOP3`
- [x] 运行定向测试和 JS 语法检查

## 故障统计增加手机扫码免登录查看

- [x] 为统计页二维码和公开只读入口增加源码级失败测试
- [x] 新增公开统计页、公开物理统计 API、公开业务统计 API URL
- [x] 复用现有统计页模板，登录页显示二维码，公开页隐藏二维码并使用公开 API
- [x] 为公开页提供最小基础模板，避免依赖 NetBox 登录布局
- [x] 运行定向测试、JS 语法检查和 Python 编译

## 故障统计增加光缆中断概览

- [x] 为统计页光缆中断概览增加源码级失败测试，覆盖后端过滤口径、返回结构、模板分区和 JS 渲染入口
- [x] 在统计 API 中新增 `cable_break_overview`，只统计故障类型为光缆中断且状态不是挂起的故障
- [x] 汇总中断起数、一级原因 Top3、来源起数，以及 6-8/8-10/10-12/12 小时以上长时中断起数
- [x] 在物理故障统计 Tab 增加“光缆中断概览”分区和两张卡片
- [x] 调整统计页脚本渲染新分区，并在无数据时显示 0
- [x] 运行定向测试、JS 语法检查和 Python 编译

## 故障统计增加总体情况卡片

- [x] 为统计页总体情况卡片增加源码级失败测试，覆盖卡片结构、总数显示与故障类型竖线分割
- [x] 在物理故障统计 Tab 增加总体情况卡片，复用现有卡片视觉风格
- [x] 调整统计页脚本，使用 `kpis.total_count` 和 `charts.category` 渲染总体情况
- [x] 增加小号类型统计与竖线分割样式
- [x] 运行定向测试与前端语法检查

## 故障统计日期选择改为日历驱动

- [x] 为故障统计顶部筛选增加源码级失败测试，覆盖只保留类型选择和单个日历日期输入
- [x] 为前端参数构造增加源码级失败测试，覆盖按类型从所选日期推导年/月/ISO 周
- [x] 调整故障统计页面上下文，提供默认日历日期
- [x] 调整统计页模板，将年/月/周分散控件替换为日历日期选择
- [x] 调整统计页脚本，根据类型和日期生成原有 API 参数
- [x] 运行定向测试与语法检查

## 故障统计周期显示按类型格式化

- [x] 为周期显示增加源码级失败测试，覆盖年/月/周统计中文文案格式
- [x] 增加前端周期显示辅助函数，按当前统计类型和日历日期生成说明
- [x] 替换物理故障与业务故障数据加载后的 `period-display` 文案
- [x] 运行定向测试与前端语法检查

## 故障统计跨月周按周日归属月份显示

- [x] 为周统计显示增加源码级失败测试，覆盖 `2026.3.30-2026.4.5` 显示为 `2026年4月第一周`
- [x] 调整周统计标题，使用周日所在年月作为周归属月份
- [x] 调整月内第几周计算，按归属月份的第一周计算
- [x] 运行定向测试与前端语法检查

## 故障统计周期文案跟随标题显示

- [x] 为统计页标题区域增加源码级失败测试，覆盖周期文案放在标题内并使用小号样式
- [x] 调整统计页模板，将 `period-display` 移入“故障统计”标题之后
- [x] 增加周期文案标题内样式，字号略小于标题且保持可换行
- [x] 运行定向测试与前端语法检查

## 故障统计周期文案横线格式并居中放大

- [x] 为周期文案增加源码级失败测试，覆盖 `周统计 - 2026年4月第二周...` 格式
- [x] 调整年/月/周周期文案为横线分隔格式
- [x] 调整标题组居中展示，并放大周期文案字号
- [x] 运行定向测试与前端语法检查

## 故障统计周期标题恢复当前与未到日期状态

- [x] 为周期状态增加源码级失败测试，覆盖“当前”和“未到日期”
- [x] 调整未来周期后端标签为“未到日期”
- [x] 调整前端周期标题范围，优先使用 API 返回的 `period.start` / `period.end`
- [x] 运行定向测试与前端语法检查

## 故障统计年/月标题显示范围并将当前置绿

- [x] 为年/月统计标题增加源码级失败测试，覆盖具体时间范围显示
- [x] 调整年/月统计标题，追加 `period.start` 到 `period.end` 范围
- [x] 调整周期状态样式，`period.end == 当前` 时使用绿色
- [x] 运行定向测试与前端语法检查

## 故障统计周期标题改为无横线与补零日期

- [x] 为周期标题增加源码级失败测试，覆盖 `周统计 2026年4月第二周（2026.04.06至2026.04.12）`
- [x] 调整点号日期格式为 `YYYY.MM.DD`
- [x] 去掉统计类型后的横线，范围连接符改为“至”
- [x] 运行定向测试与前端语法检查

## 故障统计周统计使用主题绿色旗标

- [x] 为周期标题增加源码级失败测试，覆盖周统计类型使用旗标元素
- [x] 将周期标题渲染从纯文本改为受控 HTML
- [x] 增加使用 NetBox/Tabler success 变量的绿色旗标样式，兼容浅深色模式
- [x] 运行定向测试与前端语法检查

## OtnFault 故障分布图取消动态图标

- [x] 为 `fault_mode.js` 增加源码级失败测试，覆盖故障分布图不再启动故障图标动画循环，且点位模式不再显示 `fault-points-pulse` / `fault-points-glow`
- [x] 先运行新增测试，确认当前实现仍会启动 `_startIconAnimation()` 且显示动态脉冲/发光图层
- [x] 调整 `fault_mode.js`，移除故障图标动画启动与动态脉冲/发光图层显示，保留静态图标、定位环、悬停与弹窗交互
- [x] 运行定向测试，确认故障分布图已改为静态图标展示

## OtnFault 详情页基本信息拆行展示

## OtnFault 故障详情左侧标签防折行

- [x] 为 `otnfault.html` 增加源码级失败测试，覆盖详情表格启用固定布局、左侧标签列最小宽度且不换行、右侧内容列允许长文本换行
- [x] 先运行新增测试，确认当前模板仍缺少上述布局约束
- [x] 调整故障详情页模板样式，避免“故障详情和处理过程”等长文本将左侧字段名称挤到折行
- [x] 运行定向测试，确认布局约束已经写入模板源码

## OtnFault 故障详情标签列固定宽度

- [x] 调整源码级测试，覆盖左侧标签列使用固定宽度而非百分比宽度，并显式禁止中文断字
- [x] 先运行更新后的测试，确认当前模板仍使用百分比宽度导致半屏卡片内标签列过窄
- [x] 调整故障详情页模板样式，将标签列改为固定宽度并增加 `word-break: keep-all`
- [x] 运行定向测试，确认标签列固定宽度约束生效

## OtnFault 故障信息表格结构化防折行

- [x] 调整源码级测试，覆盖故障信息表格通过 `colgroup` 固定标签列宽度，并为标签文本增加内联不换行约束
- [x] 先运行更新后的测试，确认当前模板仍只依赖 `extra_styles` 而缺少结构级宽度约束
- [x] 调整故障信息表格结构，改用表格内联样式与 `colgroup` 固定标签列，避免外层样式块失效时继续折行
- [x] 运行定向测试，确认结构级约束已写入模板源码

- [x] 为 `otnfault.html` 增加源码级失败测试，覆盖故障编号、故障类型、处理状态、紧急程度按独立行展示
- [x] 先运行新增测试，确认当前模板仍将四个字段组合在“故障基本信息”同一行
- [x] 调整故障详情页模板，将四个字段改为一个字段一行并保持现有 badge 风格
- [x] 运行定向测试，确认详情页展示结构符合预期

## OtnFault 时间轴恢复图标去歧义

- [x] 为 `otnfault.html` 增加源码级失败测试，覆盖“故障恢复”节点不再使用对勾图标
- [x] 先运行新增测试，确认当前模板第 5 个时间轴节点仍使用 `mdi-check`
- [x] 调整故障详情页时间轴图标映射，将“故障恢复”改为恢复语义图标
- [x] 运行定向测试，确认图标替换生效且不影响现有时间轴结构

## OtnFault 恢复图标统一替换

- [x] 为详情页与故障列表增加源码级失败测试，覆盖“故障恢复”统一使用新图标且不再出现 `mdi-restore`/`mdi-check`
- [x] 先运行新增测试，确认当前详情页仍为 `mdi-restore`，列表仍为 `mdi-check`
- [x] 调整详情页与列表时间轴图标映射，将“故障恢复”统一改为 `mdi-restore-alert`
- [x] 运行定向测试，确认详情页与列表图标一致且无旧图标残留

## OtnFault 故障分类颜色去重

- [x] 梳理故障分类与故障状态当前颜色映射，确认重叠范围
- [x] 调整模型与仪表盘中的故障分类配色，统一避开处理状态四色
- [x] 增加源码级测试，锁定故障分类颜色不得复用处理状态颜色
- [x] 运行定向测试，确认配色约束生效

## 192.168.30.34 地图反代缓存

## OtnFault 运维主管前端默认值加固

- [x] 为 `otnfault_edit.html` 增加源码级失败测试，覆盖“页面加载按当前故障分类尝试补默认运维主管”和“查不到用户时不清空已有运维主管”
- [x] 先运行新增测试，确认当前前端逻辑仅监听分类变更且会先清空后回填
- [x] 调整编辑页前端脚本，抽取可复用的运维主管默认值函数，并在页面初始化时按当前分类执行一次
- [x] 调整运维主管自动匹配逻辑，只有解析到用户后才覆盖选择，匹配失败时保留现有值
- [x] 运行定向测试与语法校验，确认前端加固逻辑可用

## OtnFault 故障类型必填与默认值

- [x] 为 `OtnFault.fault_category` 增加源码级失败测试，覆盖默认值为 `fiber_break` 且字段不允许 `blank/null`
- [x] 先运行新增测试，确认当前模型仍允许空值且没有默认故障类型
- [x] 将 `OtnFault.fault_category` 改为必填，并设置默认值为“光缆中断”
- [x] 新增迁移文件，收敛数据库层字段定义
- [x] 运行定向测试与语法校验，确认模型变更可用


- [ ] 梳理旧地图服务器 stadia_proxy.conf 当前代理与缓存位置，确认只缓存 /map-assets/stadia/
- [ ] 将 JSON 元数据与实际瓦片资源拆分为两段代理规则，避免对 .pbf/.png 走 sub_filter
- [ ] 保留本地 /map-assets/ 样式文件直出，避免样式修改被旧缓存干扰
- [ ] 输出 nginx 主配置与 conf.d 的落位说明，避免 proxy_cache_path 再次放错上下文

- [ ] 为 `import_arcgis_sites.py` 增加导入前的 NetBox 站点 100 米近邻重复检查
- [ ] 抽取可复用的近邻检测函数，便于脚本内复用和离线测试
- [ ] 补源码级回归测试，覆盖近邻检测结果和导入前日志输出
- [ ] 先运行新增测试确认失败，再实现最小代码改动使其通过
- [ ] 运行相关测试与静态校验，确认脚本功能完整

## import_otn_paths.py 站点匹配切换

- [ ] 为 `import_otn_paths.py` 增加基于 NetBox `Site` 坐标缓存的匹配测试
- [ ] 先运行新增测试，确认当前实现仍依赖 ArcGIS 点图层导致失败
- [ ] 将站点匹配来源从 ArcGIS 点图层改为 NetBox `Site` 模型
- [ ] 保持阈值匹配、`O_NAME` 回退、`unspecified` 兜底与双向去重逻辑不变
- [ ] 运行定向测试与语法校验，确认脚本基本功能可用

## import_otn_paths.py 代理修复

- [ ] 为 `fetch_arcgis_data()` 增加禁用环境代理的失败测试
- [ ] 先运行新增测试，确认当前实现仍直接走 `requests.get()`
- [ ] 将 ArcGIS 请求改为 `Session(trust_env=False)`，避免受本地坏代理影响
- [ ] 运行相关单测与语法校验，确认代理修复不影响现有导入逻辑

## import_otn_paths.py 模拟模式

- [ ] 为 `import_otn_paths.py` 增加 `dry_run` 的失败测试
- [ ] 先运行新增测试，确认当前实现在 `commit=True` 时仍会尝试保存
- [ ] 增加显式 `dry_run` 参数，并让它优先于 `commit`
- [ ] 补充模拟模式日志和汇总提示
- [ ] 运行相关单测与语法校验，确认模拟模式不影响现有逻辑

## import_otn_paths.py 未指定路径明细汇总

- [ ] 为涉及【未指定】路径的详细汇总增加失败测试
- [ ] 先运行新增测试，确认当前汇总缺少路径名称参考信息
- [ ] 收集涉及【未指定】路径的明细，包含 ArcGIS 原始路径名与导入路径名
- [ ] 在日志汇总和最终报告中输出未指定路径总数及逐条明细
- [ ] 运行相关单测与语法校验，确认汇总增强不影响现有逻辑

## import_otn_paths.py 未指定端模糊修正

- [ ] 为“未指定端”增加最近站点名称模糊修正的失败测试
- [ ] 先运行新增测试，确认当前实现仍保留为【未指定】
- [ ] 仅在会落到【未指定】时，对最近候选站点执行名称模糊匹配并尝试修正
- [ ] 为模糊修正成功与仍未指定分别输出汇总和逐条明细日志
- [ ] 运行相关单测与语法校验，确认新兜底逻辑不影响现有功能

## import_otn_paths.py 模糊后剩余未匹配明细

- [ ] 为“模糊匹配后仍未匹配”的日志口径增加失败测试
- [ ] 先运行新增测试，确认当前日志未明确标识这是模糊匹配后的剩余未匹配明细
- [ ] 调整未指定汇总和明细文案，明确表示这是模糊匹配后仍保持【未指定】的路径
- [ ] 运行相关单测与语法校验，确认日志调整不影响现有逻辑

## import_otn_paths.py 剩余未匹配候选诊断

- [ ] 为剩余未匹配明细增加最近候选站点、最近距离、最佳相似度的失败测试
- [ ] 先运行新增测试，确认当前日志缺少这些候选诊断信息
- [ ] 为模糊匹配后仍未命中的路径记录最近候选和最佳相似候选诊断
- [ ] 运行相关单测与语法校验，确认诊断增强不影响现有逻辑

## import_otn_paths.py AZ/ZA 名称双向匹配

- [ ] 为 A/Z 与 Z/A 名称顺序增加失败测试
- [ ] 先运行新增测试，确认当前实现仍按固定左右顺序解释名称
- [ ] 实现方向无关的双向名称回退和模糊匹配评分选择
- [ ] 在相关汇总中保留选中的名称方向信息
- [ ] 运行相关单测与语法校验，确认双向匹配不影响现有逻辑

## import_otn_paths.py 未匹配候选排除已用端点

- [ ] 为“未匹配端诊断不应推荐已被另一端使用的站点”增加失败测试
- [ ] 先运行新增测试，确认当前诊断仍会把已用站点当作最佳候选
- [ ] 仅为真正未匹配的端点输出诊断，并从候选中过滤本路径已确定站点
- [ ] 运行相关单测与语法校验，确认诊断修正不影响现有逻辑

## import_otn_paths.py 总是显示最近候选诊断

- [ ] 为未匹配端诊断增加“总是显示最近可用站点和匹配度”的失败测试
- [ ] 先运行新增测试，确认当前在无阈值内候选时仍显示无可用候选

## CircuitService 业务门类字段

- [x] 为 `CircuitService` 新增“业务门类”选择字段的源码级失败测试
- [x] 先运行新增测试，确认模型、表单、筛选、表格与序列化尚未暴露该字段
- [x] 新增 `BusinessCategoryChoices` 并为 `CircuitService` 模型添加可空选择字段
- [x] 同步更新 `CircuitService` 的表单、筛选器、表格与 API 序列化
- [x] 新增迁移文件并运行定向测试与语法校验，确认字段链路完整

## CircuitService 业务门类-业务组归属

- [x] 为 `CircuitService` 新增业务门类与业务组归属关系的源码级失败测试
- [x] 先运行新增测试，确认当前 `ServiceGroupChoices` 与归属校验尚未覆盖新分组体系
- [x] 按新的一级/二级结构重写 `ServiceGroupChoices`
- [x] 增加业务组到业务门类的归属映射，并在 `CircuitService.clean()` 中校验二者匹配
- [x] 运行定向测试与语法校验，确认新分组体系可用

## CircuitService 专线名称字段

- [x] 为 `CircuitService` 新增“专线名称”字段的源码级失败测试
- [x] 先运行新增测试，确认模型、表单、筛选、表格与序列化尚未完整暴露该字段
- [x] 新增必填 `special_line_name` 字段，并通过迁移使用现有 `name` 回填历史数据
- [x] 调整编辑表单顺序，将“专线名称”放到最上方
- [x] 同步更新导入、筛选、表格与 API 序列化
- [x] 运行定向测试与语法校验，确认字段链路完整

## CircuitService Excel 导入

- [x] 为电路业务 Excel 导入增加失败测试，覆盖表头识别、业务门类前缀清洗与字段映射
- [x] 先运行新增测试，确认当前仓库尚无该导入能力
- [x] 增加不依赖第三方库的 Excel 解析与记录归一化逻辑
- [x] 增加管理命令，将 Excel 导入到 `CircuitService`，并用电路编号填充缩写
- [x] 运行定向测试与语法校验，确认导入链路可用

## CircuitService Excel 详细日志

- [x] 为导入命令增加失败测试，覆盖逐条新增、更新、跳过与汇总日志
- [x] 先运行定向测试，确认当前命令日志仍只有简略汇总
- [x] 扩展导入命令输出，逐条打印新增、更新、跳过详情
- [x] 在汇总中补充新增、更新、跳过总数与名单
- [x] 运行定向测试与语法校验，确认详细日志可用

## OtnFaultImpact 电路业务三级联动

- [x] 为故障影响业务编辑表单增加失败测试，覆盖业务门类、业务组、专线名称三级联动字段
- [x] 先运行定向测试，确认当前表单仍只有电路业务组与电路业务两级
- [x] 调整 `OtnFaultImpactForm`，新增三级辅助字段并隐藏真实 `circuit_service`
- [x] 更新编辑模板脚本，实现业务门类 -> 业务组 -> 专线名称联动并自动回填 `circuit_service`
- [x] 运行定向测试与语法校验，确认新增编辑界面可用

## CircuitService 详情页补字段

- [x] 为电路业务详情页补字段增加失败测试，覆盖专线名称、业务门类、对部服务和电路编号标题
- [x] 先运行定向测试，确认当前详情页仍缺少这些字段
- [x] 调整详情页模板，按最小方案补齐缺失字段并保持现有展示风格
- [x] 运行定向测试与语法校验，确认详情页展示完整

## CircuitService 主标识切换

- [x] 为电路业务主标识切换增加失败测试，覆盖 `__str__`、默认排序和列表主列
- [x] 先运行定向测试，确认当前仍以电路编号作为主标识
- [x] 调整 `CircuitService` 模型与列表表格，改为以专线名称作为主标识
- [x] 运行定向测试与语法校验，确认主标识切换生效

## OtnFaultImpact 新增影响业务异常排查

- [x] 收集现有异常现象与服务器日志，确认后端未输出目标 traceback，但保存后相关时段存在 `TenantListExtension` 页面扩展异常
- [x] 排查 `OtnFaultImpactForm` 与编辑视图中的 `.get()` 调用点，确认已加 `initial` 空值保护且新增流程会在成功后跳回父故障详情页
- [x] 调整 `OtnFaultImpactEditView` 的上下文与成功回跳逻辑，优先返回影响业务自身详情页，规避父故障详情页第三方扩展报错
- [x] 补充源码级回归测试，覆盖空值容错与新的成功回跳行为
- [x] 运行定向测试与语法校验，确认代码侧兜底已落地
- [x] 对照上一个正常版本，定位 `circuit_service` 从标准绑定字段改为隐藏字段后的保存链路偏差
- [ ] 回退 `circuit_service` 的保存语义到接近旧版的稳定方案，同时保留三级联动界面
- [ ] 运行定向测试与语法校验，确认三级联动与保存链路同时可用
- [ ] 调整诊断逻辑为总是输出最近可用站点、距离和匹配度，同时保持自动修正阈值不变
- [ ] 运行相关单测与语法校验，确认诊断增强不影响现有逻辑

## views.py 恢复与最小兜底

- [x] 从 git 读取 `views.py` 的干净版本，确认当前服务器异常已转为文件导入失败
- [x] 将 `views.py` 恢复为无 BOM 的 UTF-8，并清除当前工作区里的损坏字符
- [x] 仅补回 `OtnFaultImpactEditView` 需要的最小容错与安全回跳
- [x] 更新相关源码级测试，避免继续绑定到实验性保存逻辑
- [x] 运行定向测试与语法校验，确认 `views.py` 可导入

## import_otn_paths.py 未匹配诊断参考名展示

- [ ] 为未匹配诊断增加“待匹配端站点名称”的失败测试
- [ ] 先运行新增测试，确认当前日志未显示从路径名提取的参考名称
- [ ] 调整未匹配明细格式，在最近候选前输出待匹配端站点名称
- [ ] 运行相关单测与语法校验，确认文案调整不影响现有逻辑

## import_otn_paths.py 成功匹配质量审计

- [ ] 为成功匹配路径增加低匹配度审计的失败测试
- [ ] 先运行新增测试，确认当前不会单独汇总低分成功匹配路径
- [ ] 实现基于原始路径名、A/Z 站点名、方向与距离的综合评分
- [ ] 对低分成功匹配路径输出汇总和逐条明细，辅助识别潜在误匹配
- [ ] 运行相关单测与语法校验，确认审计逻辑不影响现有匹配流程

## 每周通报裸纤业务影响标题统计

- [ ] 为裸纤业务影响统计增加失败测试，覆盖中断、抖动、未发生故障三类数量
- [ ] 先运行新增测试，确认当前周报接口尚未提供裸纤业务汇总数据
- [ ] 在周报后端补充 `bare_fiber_summary` 汇总字段，并保持现有表格数据口径不变
- [ ] 在裸纤业务影响标题栏右侧渲染彩色统计标签，适配桌面与移动端布局
- [ ] 运行定向测试与语法校验，确认周报页面统计可用

## 每周通报重点影响省份布局调整

- [ ] 将“重点影响省份”从分析三栏区拆出，改为下方独立的全宽模块
- [ ] 调整分析区布局，仅保留主要原因分析与重大事件两块内容
- [ ] 将省份列表改为适合全宽展示的自适应网格，减少大块留白
- [ ] 运行模板与样式检查，确认桌面和移动端布局稳定

## 每周通报配色对齐 NetBox

- [ ] 参考 NetBox 页面标准青色，统一每周通报页的品牌主色与辅色
- [ ] 保持中断、抖动、未发生故障的红橙绿语义色不变
- [ ] 同步调整标题强调、日期胶囊、原因分析横条、省份卡渐变与背景氛围色
- [ ] 运行静态检查，确认周报页未残留上一版绿色品牌色

## 每周通报 NetBox 原生风格细化

- [ ] 将周报卡片阴影、圆角、边框调整为更接近 NetBox 列表页的轻量风格
- [ ] 弱化大屏式悬浮和发光效果，保留青色品牌强调但减少视觉噪声
- [ ] 细化空状态、表格 hover、省份卡块面与胶囊样式，使之更贴近 NetBox 原生界面
- [ ] 运行静态检查，确认品牌青色与状态语义色保持一致

## 远端 NetBox 故障数据同步脚本

- [ ] 为远端故障 API 拉取与分页遍历增加失败测试，覆盖 Token 头、列表分页和异常响应
- [ ] 为本地故障 upsert 增加失败测试，覆盖按 `fault_number` 更新已有故障与创建缺失故障
- [ ] 为影响业务同步增加失败测试，覆盖按故障和业务主键去重，以及缺失关联对象时的跳过日志
- [ ] 先运行新增测试，确认当前仓库尚无远端 NetBox 故障同步能力
- [ ] 新增 NetBox 自定义脚本，默认访问 `http://192.168.70.177` 并支持可选 API Token、分页拉取、模拟执行
- [ ] 实现远端 `faults`/`impacts` 拉取、本地关联对象解析、故障与影响业务的 upsert
- [ ] 为缺失站点、用户、区域、服务商、业务对象输出汇总与逐条日志，避免静默失败
- [ ] 运行定向测试与语法校验，确认同步脚本在离线测试环境可验证

## 态势大屏 PMTiles 拓扑改造

- [ ] 为大屏拓扑数据拆分增加失败测试，覆盖“基础拓扑走 PMTiles、动态接口仅返回故障覆盖路径”
- [ ] 先运行新增测试，确认当前 `dashboard/data/` 仍返回全量 `paths`，且大屏模板尚未显式加载 `pmtiles.js`
- [ ] 在大屏模板与地图引擎中接入 PMTiles 协议注册，复用 `otn_paths_pmtiles_url` 绘制基础网络拓扑线
- [ ] 将大屏动态接口中的全量 `paths` 几何改为仅返回故障关联路径覆盖数据，并保持现有故障高亮效果
- [ ] 调整大屏前端渲染链路，改为“PMTiles 基础拓扑 + 前端故障覆盖层”，去掉全量路径同步渲染
- [ ] 运行新增测试与相关语法校验，确认外网场景下大屏首屏与轮询性能改善且现有效果不回退

## 态势大屏故障关联路径按 AZ 站点对定位

- [ ] 为故障关联路径筛选增加失败测试，覆盖“仅匹配故障 A/Z 站点对，不能只命中单端站点”
- [ ] 先运行新增测试，确认当前实现仍会把仅命中 A 端或 Z 端的相邻路径算作关联路径
- [ ] 将大屏后端的关联路径定位逻辑改为基于故障 A/Z 站点对匹配，并保持方向无关
- [ ] 运行定向测试与语法校验，确认大屏故障覆盖层只保留真正命中的 AZ 路径


## 故障分布图故障统计卡片展开延迟

- [x] 梳理 `FaultStatisticsControl` 展开时的同步渲染与地图动画耦合点，确认延迟来自前端控件层
- [x] 先补源码级回归测试，约束统计详情采用延迟渲染且展开时触发动画降载
- [x] 调整故障统计控件，最小化展开首帧工作量，并在展开后异步补齐详情内容
- [x] 调整故障分布图动画控制，避免统计卡片展开期间持续脉冲重绘拖慢交互
- [x] 运行定向测试与语法校验，确认统计卡片交互优化不影响现有地图功能

## OtnFault 标签字段说明

- [x] 为 `OtnFaultForm.tags` 增加源码级失败测试，约束标签字段提示文案
- [x] 先运行新增测试，确认当前标签字段下方尚未显示“88系统”提示
- [x] 在 `OtnFaultForm` 中为标签字段补充 help text，保持现有编辑页渲染方式不变
- [x] 运行定向测试，确认故障编辑页会透传该说明文案

## OtnFault 新增编辑页字段顺序调整

- [x] 为故障新增编辑页增加源码级失败测试，约束“第一报障来源”和“标签”紧跟在“紧急程度”之后
- [x] 先运行新增测试，确认当前模板中的字段顺序仍未调整
- [x] 调整 `otnfault_edit.html` 中的字段渲染顺序，不改动现有表单字段定义
- [x] 运行定向测试，确认新增和编辑页面都使用新的字段顺序

## OtnFault 详情页第一报障来源位置调整

- [x] 为故障详情页增加源码级失败测试，约束“第一报障来源”位于“故障基本信息”和“故障位置”之间
- [x] 先运行新增测试，确认当前详情模板中的字段顺序仍未调整
- [x] 调整 `otnfault.html` 中的详情行顺序，不改动现有字段内容
- [x] 运行定向测试，确认详情页使用新的字段顺序
## OtnFault 故障起始时间展示统一

- [x] 梳理插件内“故障中断时间/发生/故障发现”等主故障时间展示入口，明确仅修改主故障 UI 文案，不改“业务故障时间”
- [x] 统一表单、表格、详情/弹窗、地图统计与大屏中的主故障时间展示为“故障起始时间”
- [x] 运行定向检索与必要校验，确认未误改“业务故障时间”等不在范围内的展示

## OtnFault 详情页故障编号日期化展示

- [x] 为故障详情页增加源码级失败测试，约束模板改为使用格式化后的故障编号展示
- [x] 先运行新增测试，确认当前详情模板仍直接输出原始 `fault_number`
- [x] 在 `OtnFault` 模型中增加按 `FYYYYMMDDNNN` 提取日期的只读展示属性
- [x] 调整 `otnfault.html` 使用格式化属性，展示为 `F20260412003（2026年4月12日）`
- [x] 运行定向测试与语法校验，确认详情页展示更新且不影响原始编号存储

## OtnFault 故障恢复时间放宽校验

- [x] 为 `OtnFault.clean()` 增加源码级失败测试，覆盖“故障恢复时间只需晚于故障起始时间”
- [x] 先运行新增测试，确认当前实现仍要求恢复时间晚于处理派发、维修出发、到达现场
- [x] 调整 `OtnFault.clean()`，保留派发/出发/到场顺序校验，但将恢复时间改为仅校验不早于故障起始时间
- [x] 运行定向测试与语法校验，确认恢复时间规则放宽且其余时间顺序不回退

## OtnFault 详情页时间轴重点时间布局调整

- [x] 为 `otnfault.html` 增加源码级失败测试，覆盖历时信息位于时间轴下方，且“故障起始/故障恢复”的时间上移到图标上方并加大加粗
- [x] 先运行新增测试，确认当前详情模板仍将历时信息放在时间轴上方，且所有节点时间仍统一显示在标签下方
- [x] 调整 `otnfault.html` 时间轴结构，将历时信息移到下方，仅对首尾节点增加上方强调时间展示并保留下方标签文字
- [x] 运行定向测试，确认详情页时间轴布局符合新的展示要求

## OtnFault 时间轴跨天时间防压盖

- [x] 调整源码级测试，覆盖首尾节点上方时间区域支持双行日期时间且不与图标重叠
- [x] 先运行更新后的测试，确认当前模板仍按单行时间区域布局导致跨天时压盖图标
- [x] 调整 `otnfault.html` 上方强调时间样式与图标纵向位置，为双行时间预留稳定空间
- [x] 运行定向测试，确认起始/恢复时间跨天时不会与图标互相遮挡

## OtnFault 时间轴跨天日期文案调整

- [x] 为 `timeline_data` 增加源码级失败测试，覆盖跨天时间显示为“4月11日”且不再使用括号月日格式
- [x] 先运行新增测试，确认当前实现仍输出 `(%m-%d)` 样式
- [x] 调整 `OtnFault.timeline_data` 的跨天日期格式，改为“日期在上、时间在下”
- [x] 运行定向测试，确认时间轴首尾节点跨天文案符合新要求

## OtnFault 时间轴首尾时间底边对齐

- [x] 调整源码级测试，覆盖首尾节点上方时间区域使用固定高度，确保单行时间也贴底对齐
- [x] 先运行更新后的测试，确认当前模板仍使用 `min-height` 导致单行恢复时间上浮
- [x] 调整 `otnfault.html` 的上方时间高亮容器为固定高度，保持单行和双行时间底边一致
- [x] 运行定向测试，确认故障恢复时间不跨天时与故障起始时间底边平齐

## OtnFault 时间轴首尾日期时间双层渲染

- [x] 调整源码级测试，覆盖首尾节点单行时间通过保留空首行落到第二行，与双行时间底边对齐
- [x] 先运行更新后的测试，确认当前实现仍无法让单行恢复时间落到第二行
- [x] 调整 `OtnFault.timeline_data` 在首尾节点同日场景补空首行，并更新高亮时间样式使用 `pre-line`
- [x] 运行定向测试，确认故障恢复时间单行时与故障起始时间的时间行平齐

## OtnFault 时间轴同日时间占位行修正

- [x] 调整源码级测试，覆盖同日首尾节点使用不可见占位首行而非纯空行
- [x] 先运行更新后的测试，确认当前实现仍仅输出 `\\n{time}`，浏览器不会稳定保留空首行
- [x] 调整 `OtnFault.timeline_data`，将同日首行改为不可见占位字符，确保时间稳定落在第二行
- [x] 运行定向测试，确认故障恢复时间与故障起始时间真正平齐

## OtnFault 时间轴首尾时间宽屏稳定对齐

- [x] 调整源码级测试，覆盖首尾高亮时间采用独立日期行和时间行，而非依赖空白字符占位
- [x] 先运行更新后的测试，确认当前实现仍使用占位换行，宽屏下存在时间上浮风险
- [x] 调整 `OtnFault.timeline_data` 与 `otnfault.html`，将首尾高亮时间改为固定两行结构，确保不同窗口宽度下都稳定对齐
- [x] 运行定向测试，确认宽屏和窄屏场景下故障恢复时间都与故障起始时间平齐

## OtnFault 时间轴首尾时间超宽窗口防上跳

- [x] 调整源码级测试，覆盖首尾高亮时间容器使用固定两行网格而非 flex 布局
- [x] 先运行更新后的测试，确认当前宽屏场景下 flex 双行结构仍可能让故障恢复时间上跳
- [x] 调整 `otnfault.html`，将首尾高亮时间改为两行固定轨道的 grid 布局，确保超宽窗口下也稳定贴底
- [x] 运行定向测试，确认不同窗口宽度下时间块都不会再上跳

## OtnFault 时间轴首尾时间绝对定位锁定

- [x] 调整源码级测试，覆盖首尾高亮时间改为容器内上下绝对定位，不再依赖 grid/flex 行布局
- [x] 先运行更新后的测试，确认当前超宽窗口场景下 grid 双轨仍可能出现时间上跳
- [x] 调整 `otnfault.html`，将日期行固定贴顶、时间行固定贴底，彻底消除窗口宽度对垂直位置的影响
- [x] 运行定向测试，确认不同窗口宽度下时间块垂直位置恒定
# 故障统计物理故障新增故障类型维度

- [ ] 为物理故障统计新增源码级失败测试，覆盖后端 `charts.category`、模板第 4 张图表容器，以及前端 `chartCategory` 的初始化与过滤逻辑
- [ ] 先运行新增测试，确认当前实现尚未暴露“故障类型”统计维度
- [ ] 调整 `statistics_views.py`，新增故障类型聚合并返回 `charts.category`
- [ ] 调整 `statistics_dashboard.html`，将物理故障统计图表区扩展为 4 张响应式图表卡片并新增 `chart-category`
- [ ] 调整 `statistics_dashboard.js`，新增故障类型图表渲染、点击下钻、图例排除与清除过滤逻辑，并收敛当前重复的图表点击绑定
- [ ] 运行定向测试与语法校验，确认新增维度和过滤逻辑可用

## 故障月历小组件显示上限修复

- [x] 为 `dashboard.py` 增加源码级失败测试，覆盖月历按天收集故障点时不得再截断为前 5 个
- [x] 先运行新增测试，确认当前实现仍存在 `day_dots[day] = day_dots[day][:5]`
- [x] 调整 `OtnFaultsCalendarWidget`，保留每天全部故障点供模板渲染
- [x] 运行定向测试，确认月历小组件数据链路不再丢失第 6 个及之后的故障点

## 故障月历紧凑网格样式优化

- [x] 为 `dashboard_calendar_widget.html` 增加源码级失败测试，覆盖月历圆点容器改为紧凑网格布局
- [x] 先运行新增测试，确认当前模板仍使用松散 `flex-wrap` 圆点布局
- [x] 调整月历模板样式，使用固定列数紧凑网格、小尺寸圆点和稳定点阵高度
- [x] 运行定向测试，确认月历多故障日期的模板结构已更新

## 故障月历恢复紧凑点模式

- [x] 调整 `dashboard_calendar_widget.html` 的源码级测试，覆盖月历圆点恢复为紧凑 `flex-wrap` 模式且不再使用 grid
- [x] 先运行更新后的测试，确认当前模板仍是 4 列 grid 点阵
- [x] 调整月历模板样式，恢复旧版紧凑圆点排布并保留按实际数量换行显示
- [x] 运行定向测试，确认月历圆点样式已回退为紧凑模式

## 故障统计新增半年与季度周期

- [x] 为统计周期选择增加源码级失败测试，覆盖模板选项、前端参数构造/周期标签、后端半年与季度时间范围解析
- [x] 先运行更新后的测试，确认当前实现只支持年/月/周
- [x] 调整 `statistics_dashboard.html`，在统计类型下拉框中新增半年、季度选项
- [x] 调整 `statistics_dashboard.js`，根据所选日期构造半年/季度 API 参数，并渲染对应周期标题和对比文案
- [x] 调整 `statistics_views.py`，在 `_parse_time_range()` 中支持半年和季度，并计算上一周期范围
- [x] 运行定向测试、JS 语法检查和 Python 编译，确认新增周期可用

## 故障统计周期快捷加减

- [x] 为统计页快捷加减增加源码级失败测试，覆盖上一周期/下一周期按钮和 JS 周期偏移函数
- [x] 先运行更新后的测试，确认当前页面没有快捷加减入口
- [x] 调整 `statistics_dashboard.html`，在统计类型和日期选择器旁增加上一周期/下一周期按钮
- [x] 调整 `statistics_dashboard.js`，按当前统计类型对日期执行年/半年/季度/月/周偏移，并刷新当前 Tab
- [x] 运行定向测试和 JS 语法检查，确认快捷加减逻辑可用

## 故障统计概览指标点击过滤

- [x] 为故障统计概览指标点击过滤增加源码级失败测试，覆盖主指标、分项指标、重复指标和后端明细过滤字段
- [x] 调整 `statistics_views.py`，为明细补充光缆属性分组、历时分布、有效历时、发生时段、成因分组等过滤字段
- [x] 调整 `statistics_dashboard.html`，给静态主指标和平均历时分项补充统一点击过滤属性
- [x] 调整 `statistics_dashboard.js`，让动态分项指标统一渲染为可点击过滤项，并扩展过滤标签显示
- [x] 运行定向测试、JS 语法检查和源码语法校验，确认所有指标均可点击过滤明细

## 故障统计卡片文字不可选中

- [x] 为统计页卡片文字不可选中增加源码级测试，约束卡片禁选且表格仍可选中
- [x] 调整 `statistics_dashboard.css`，将故障统计页面卡片统一设置为不可选中文本
- [x] 运行定向测试和 CSS 差异检查

## 故障统计页面新增光缆中断地图模态方案

### 目标
- [ ] 在故障统计页面的“光缆中断概览”区域增加一个地图按钮，点击后以模态窗口展示当前选择时间范围内的光缆中断故障。
- [ ] 地图统计口径必须与现有“光缆中断概览”一致：`fault_category == FaultCategoryChoices.FIBER_BREAK`，且 `fault_status != FaultStatusChoices.SUSPENDED`。
- [ ] 地图底层复用现有统一地图体系：`unified_map.html`、`unified_map_core.js`、`maplibregl_base.js` 和模式插件机制。
- [ ] 新增独立地图模式，避免改动或干扰现有 `fault`、`location`、`path`、`pathgroup`、`route_editor` 模式。

### 现有实现依据
- [ ] 故障统计页面入口：`netbox_otnfaults/statistics_views.py` 的 `FaultStatisticsPageView`、`FaultStatisticsDataAPI`，模板与脚本为 `statistics_dashboard.html`、`statistics_dashboard.js`、`statistics_dashboard.css`。
- [ ] 时间范围解析：复用 `statistics_views.py` 中 `_parse_time_range(request)`，确保年、半年、季度、月、周的开始/结束时间与统计卡片完全一致。
- [ ] 光缆中断概览口径：抽取底层 QuerySet 构造函数，避免在聚合统计与地图数据接口中分别手写过滤条件。
- [ ] 统一地图入口：`views.py` 中 `OtnFaultGlobeMapView`、`LocationMapView` 共同渲染 `unified_map.html`，地图模式由 `map_modes.py` 配置，前端由 `unified_map_core.js` 加载对应 `modes/*.js` 插件。
- [ ] 故障分布图样式：`modes/fault_mode.js` 使用 `FaultDataService.convertToFeatures()`、`utils/fault_icons.js`、`FAULT_CATEGORY_COLORS`、`PopupTemplates.js` 和 `fault_popup_animations.css` 生成故障图标、悬停/点击弹窗与高亮效果。
- [ ] 模态参考：`otnfault_edit.html` 的地图选点定位通过 Bootstrap 模态 + iframe 打开 `/plugins/otnfaults/map/location/?picker=true`，关闭时清空 iframe。

### 推荐方案
- [ ] 新增地图模式 `statistics_cable_break`，在 `map_modes.py` 中配置为独立模式：
  - `title`: `光缆中断故障地图`
  - `plugin_file`: 建议新增 `statistics_cable_break_mode.js`
  - `projection`: 建议沿用故障分布图的 `globe`
  - `controls`: 保留 `navigation`、`fullscreen`、`scale`
  - `js_files`: 复用 `utils/fault_icons.js`、`services/FaultDataService.js`、`controls/FaultLegendControl.js`，不加载 `LayerToggleControl.js` 和 `FaultStatisticsControl.js`，避免用户在模态内再次改变时间范围或统计口径。
- [ ] 新增页面视图 `StatisticsCableBreakMapView`，渲染 `unified_map.html`：
  - URL 建议：`statistics/cable-break-map/`
  - 读取统计页同一组时间参数：`filter_type`、`year`、`half`、`quarter`、`month`、`week`
  - 将 `map_data_url` 指向新的地图数据接口，并原样带上时间参数。
  - 支持 `modal=true` 或 `embedded=true` 参数，让 `unified_map.html` 进入无外层卡片/满容器模式；如果复用现有 `is_picker` 的最小布局语义不合适，建议新增 `is_embedded_map`，不要把统计地图伪装成 picker。
- [ ] 在 `statistics_views.py` 中先抽取 `get_cable_break_base_queryset(start_date, end_date)`：
  - 返回基础 Django QuerySet，而不是已物化的 list。
  - 基础过滤包含 `fault_occurrence_time__gte=start_date`、`fault_occurrence_time__lt=end_date`、`fault_category=FaultCategoryChoices.FIBER_BREAK`，并排除 `fault_status=FaultStatusChoices.SUSPENDED`。
  - `_compute_cable_break_overview()` 改为接收该 QuerySet 或由调用方传入该 QuerySet 物化后的对象集合，聚合统计不再重复维护口径。
  - `StatisticsCableBreakMapDataAPI` 在该 QuerySet 后继续链式追加坐标校验、`select_related()`、`prefetch_related()` 和字段提取。
- [ ] 新增数据接口 `StatisticsCableBreakMapDataAPI`：
  - URL 建议：`statistics/cable-break-map-data/`
  - 使用 `_parse_time_range(request)` 获取当前选择周期。
  - 通过 `get_cable_break_base_queryset(start_date, end_date)` 获取统一口径基础数据。
  - 仅返回具备 `interruption_latitude` 和 `interruption_longitude` 的故障点；同时返回 `skipped_count`，用于前端提示“有 N 条故障缺少坐标未展示”。
  - 返回结构尽量与 `OtnFaultMapDataView` 的 `marker_data` / `heatmap_data` 保持兼容，使 `FaultDataService.convertToFeatures()` 可直接复用。
  - 数据字段至少包含 `id`、`fault_number`、`fault_category`、`fault_status`、`fault_occurrence_time`、`fault_recovery_time`、`duration`、`province`、`reason`、`site_a`、`site_z`、`url`、`lat`、`lng`。
- [ ] 新增前端模式插件 `statistics_cable_break_mode.js`：
  - 以 `fault_mode.js` 的故障点图层、图标加载、弹窗模板和鼠标悬停交互为蓝本。
  - 只保留统计地图需要的点图层、可选热力图/图例、自动缩放到点位范围。
  - 使用独立 source/layer id，例如 `statistics-cable-break-points`、`statistics-cable-break-points-layer`，避免与故障分布图 `fault-points` 等 id 冲突。
  - 不挂载故障分布图中的时间范围控件和统计控件；当前时间范围由统计页按钮 URL 决定。
  - 对无数据场景显示轻量提示，不改变底图和共享图层。
  - Popup 中指向故障详情页的 `<a>` 必须增加 `target="_parent"` 或 `target="_blank"`，防止在 iframe 内加载完整 NetBox UI 形成页面嵌套。
  - 当接口返回 `skipped_count > 0` 时，使用极简 MapLibre Control 在地图左下角显示非阻塞提示，例如“本期另有 N 条光缆中断缺失经纬度，未在地图绘制”；禁止使用 `alert()` 或阻塞遮罩。
- [ ] 在 `statistics_dashboard.html` 中增加地图按钮和模态容器：
  - 按钮位置建议放在“光缆中断概览”标题右侧，使用 `btn btn-sm btn-outline-primary` 和 `mdi-map-marker-radius` 图标。
  - 模态结构参考 `otnfault_edit.html`，使用 `modal-xl` 或 `modal-fullscreen-lg-down`，iframe 高度建议 `72vh`。
  - iframe 外层增加 Skeleton Loading 或 Spinner，打开模态后立即显示，iframe `load` 事件触发后隐藏，避免 MapLibre 和瓦片加载前出现白屏。
  - iframe URL 由前端根据当前 `buildTimeParams()` 生成，保证用户切换统计周期后打开的是同一周期地图。
- [ ] 在 `statistics_dashboard.js` 中增加模态控制：
  - 复用已有 `buildTimeParams()` 构造查询参数。
  - 点击地图按钮时打开 `/plugins/otnfaults/statistics/cable-break-map/?modal=true&${buildTimeParams()}`。
  - 关闭模态时将 iframe `src` 置为 `about:blank`，释放 MapLibre / Deck.gl 资源。
  - 绑定 iframe `load` 事件或模态显示后的兜底定时器，控制 Loading 显隐；关闭模态时同步复位 Loading 状态。
  - 不改变现有统计数据加载、图表下钻、明细表过滤逻辑。
- [ ] 在 `statistics_dashboard.css` 中补充模态地图尺寸与小屏适配：
  - 确保 iframe 容器有稳定高度，避免地图初始化时容器高度为 0。
  - 移动端使用接近全屏的模态高度。

### 测试方案
- [ ] 新增或扩展源代码级测试，覆盖 `statistics_dashboard.html` 中存在地图按钮、模态 iframe 容器和必要的静态资源入口。
- [ ] 新增 `statistics_dashboard.js` 源码测试，覆盖按钮事件使用 `buildTimeParams()` 构造地图 URL，且关闭模态会清空 iframe。
- [ ] 新增 `statistics_dashboard.html` / `statistics_dashboard.js` 源码测试，覆盖模态地图存在 Loading 容器，iframe `load` 后隐藏 Loading，关闭模态后复位 Loading 并清空 iframe。
- [ ] 新增后端测试，验证 `StatisticsCableBreakMapDataAPI` 与 `_compute_cable_break_overview()` 口径一致：
  - 包含光缆中断且非挂起的故障会返回。
  - 挂起状态故障不会返回。
  - 非光缆中断故障不会返回。
  - 时间范围外故障不会返回。
  - 缺少经纬度故障不进入点位列表，但计入 `skipped_count`。
- [ ] 新增底层口径复用测试，验证 `get_cable_break_base_queryset(start_date, end_date)` 同时被统计概览与统计地图数据接口使用，且后续坐标过滤只发生在地图接口层。
- [ ] 新增统计地图模式源码测试，验证 Popup 链接包含 `target="_parent"` 或 `target="_blank"`，`skipped_count` 提示通过 MapLibre Control 渲染且代码中不出现 `alert(`。
- [ ] 新增地图模式配置测试，验证 `statistics_cable_break` 不复用 `fault` 模式名、不加载 `LayerToggleControl.js` / `FaultStatisticsControl.js`，并使用独立插件文件。
- [ ] 运行定向测试与语法检查：
  - `python -m py_compile .\netbox_otnfaults\statistics_views.py .\netbox_otnfaults\views.py .\netbox_otnfaults\map_modes.py`
  - `python -m pytest tests/test_statistics_cable_break_overview.py tests/test_statistics_dashboard_assets.py`
  - 如新增 JS 源码测试，运行对应测试文件。

### 风险与约束
- [ ] 不新增或猜测 NetBox 核心 API；仅新增插件内页面 URL 与 JSON 数据接口。
- [ ] 不修改 `netbox/` 核心目录。
- [ ] 现有 `OtnFaultMapDataView` 默认取最近 12 个月，不适合直接作为统计页地图数据源，否则会与当前选择周期不一致。
- [ ] 复用 `fault_mode.js` 代码时要避免复制过多控制逻辑；如果图标/弹窗逻辑无法直接复用，应先抽取小型共享 helper，再让故障分布图和统计地图共同调用。
- [ ] 地图模态内不做二次统计筛选，统计页的图表下钻过滤与本需求的“当前选择时间范围内光缆中断故障”保持独立。
- [ ] iframe 内的任何详情跳转都必须跳出 iframe；否则用户会看到完整 NetBox 页面嵌套在地图模态内。
- [ ] 必须坚持关闭模态时将 iframe `src` 置为 `about:blank`，避免反复打开后累积 WebGL contexts 导致地图黑屏。

### 当前实现状态
- [x] 已抽取 `get_cable_break_base_queryset(start_date, end_date)`，统计概览与地图数据接口共用同一基础口径。
- [x] 已新增 `statistics_cable_break` 独立地图模式、页面视图、数据 API 与 URL，不加载故障分布图的时间范围控件和统计控件。
- [x] 已在故障统计页“光缆中断概览”标题右侧增加地图按钮，并通过 Bootstrap 模态 + iframe 加载统一地图。
- [x] 已实现 iframe loading 覆盖层，iframe `load` 后隐藏；模态关闭时将 iframe `src` 置为 `about:blank`。
- [x] 已新增 `statistics_cable_break_mode.js`，使用独立 source/layer id，复用 `FaultDataService`、故障颜色、图例和故障 popup 模板。
- [x] 已强制地图 popup 内链接使用 `target="_parent"`，避免在 iframe 内嵌套完整 NetBox 页面。
- [x] 已实现 `skipped_count` 非阻塞 MapLibre Control，在地图左下角提示缺少经纬度未绘制的故障数量。
- [x] 已运行定向 unittest 和只读语法检查；本地无 pytest，且 `py_compile` 写 `.pyc` 被现有 `__pycache__` 权限阻止。

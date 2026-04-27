## 2026-04-26 调整中断时长分布图 tooltip 命中区域
### 实施步骤
- [x] 补充故障统计页源码级回归测试，锁定盒线图 tooltip 使用 `axis` 触发、全天 `shadow` 选中，并从 boxplot series 参数读取五数。
- [x] 先运行定向测试，确认当前 `item` tooltip 只命中盒线导致测试失败。
- [x] 调整 `statistics_dashboard.js` 的中断时长分布盒线图 tooltip 配置，复用物理故障数图的全天矩形阴影交互。
- [x] 运行定向 unittest 和 `node --check` 验证前端语法。

## 2026-04-26 修正移动端统计页顶层垂直间距叠加
### 实施步骤
- [x] 定位移动端仍不一致的根因：`#tab-physical` 直接子块仍保留各自 `mb-4`，与 section 内部 gap 叠加。
- [x] 将 active 的物理故障 Tab 设为纵向 flex 容器，用 `--statistics-section-gap` 控制直接子块间距。
- [x] 清除总体情况、光缆中断、图表 row、过滤提示和明细卡片作为直接子块时的上下 margin。
- [x] 运行定向测试、JS 语法检查和统计页相关测试。

## 2026-04-26 统一故障统计页面卡片与图表间距
### 实施步骤
- [x] 审计总体情况、光缆中断卡片区和图表区的 `mb-*`/`mt-*`/row gutter 混用问题。
- [x] 增加统一间距变量 `--statistics-block-gap` 和 `--statistics-section-gap`。
- [x] 将总体情况、光缆中断卡片区和 ECharts 图表区接入统一间距，并清除直接子块自身上下外边距叠加。
- [x] 运行定向测试、JS 语法检查和统计页相关测试。

## 2026-04-26 统一总体情况卡片与两张图间距
### 实施步骤
- [x] 补源码级回归测试，锁定总体情况卡片组、物理故障数图和盒须图使用同一垂直间距。
- [x] 在总体情况 section 内使用统一 `gap: 1rem`，并清除卡片组和图卡片自身 Bootstrap 上下外边距。
- [x] 运行定向测试、JS 语法检查和统计页相关测试。

## 2026-04-26 恢复故障历时频数图直方图形态
### 实施步骤
- [x] 补源码级回归测试，要求历时频数图保持连续直方图柱形，同时 X 轴名称不再右侧裁切。
- [x] 恢复 `barCategoryGap: '0%'` 和 `barGap: '0%'`，移除最大柱宽限制。
- [x] 将 `历时(小时)` 调整为 X 轴下方居中显示，并增加底部空间。
- [x] 运行定向测试、JS 语法检查和统计页相关测试。

## 2026-04-26 修复故障历时频数图右侧轴名裁切
### 实施步骤
- [x] 补源码级回归测试，锁定直方图使用更窄柱宽并为右侧轴名称保留空间。
- [x] 将直方图右侧 grid 留白从 4% 增加到 9%，柱间距改为 40%，并限制最大柱宽。
- [x] 运行定向测试、JS 语法检查和统计页相关测试。

## 2026-04-26 统一物理故障图和盒须图上下边距
### 实施步骤
- [x] 调整两张图的 ECharts grid，上方统一留出图例/筛选控件空间，下方压缩多余空白。
- [x] 更新源码级回归断言，锁定两张图一致的 top/bottom 边距。
- [x] 运行定向测试、JS 语法检查和统计页相关测试。

## 2026-04-26 盒须图增加滤除短时和整改选项
### 实施步骤
- [x] 补源码级回归测试，锁定盒须图上方居中显示“滤除短时”“滤除整改”两个选项。
- [x] 后端为每日中断时长盒须图返回全量、滤除短时、滤除整改、同时滤除四组五数数据。
- [x] 前端根据两个选项组合切换盒须图数据，保持横坐标和图形高度不变。
- [x] 运行定向测试、JS 语法检查和统计页相关测试。

## 2026-04-26 调整物理故障 tooltip 中断时长展示
### 实施步骤
- [x] 补源码级回归测试，要求物理故障每日图 tooltip 只在底部显示“中断时长合计”。
- [x] 调整 tooltip 明细行仅展示柱状故障分类，避免折线“中断时长”与底部合计重复。
- [x] 运行定向测试、JS 语法检查和统计页相关测试。

## 2026-04-26 修复盒须图 tooltip 五数错位
### 实施步骤
- [x] 补源码级回归测试，锁定 boxplot tooltip 从 ECharts value/data 中剥离类目索引后读取五数。
- [x] 定位根因：ECharts boxplot tooltip 的数组中可能包含前置类目索引，旧代码直接从第 0 项读取导致最小值错位。
- [x] 修正前端 tooltip 取值，避免把类目索引显示为最小值。
- [x] 运行定向测试和 JS 语法检查。

## 2026-04-25 统一统计卡片与 ECharts 图卡片立体效果
### 实施步骤
- [x] 补源码级回归测试，锁定指标卡片、业务卡片使用与 ECharts 图卡片一致的边框、阴影和 hover 阴影。
- [x] 调整统计页 CSS，去除指标卡片专用边框/悬浮偏移差异，统一卡片 3D 效果。
- [x] 运行统计页定向测试。

## 2026-04-25 物理故障每日图下方增加盒线图
### 实施步骤
- [x] 补源码级回归测试，锁定盒线图容器、后端每日盒线数据和前端渲染入口。
- [x] 后端按与物理每日图相同日期范围，计算每日物理故障中断时长样本的 min/Q1/median/Q3/max。
- [x] 前端新增 ECharts 盒线图实例，复用相同 X 轴标签策略并随筛选周期重绘。
- [x] 运行统计页定向测试、JS 语法检查和 Python 语法校验。

## 2026-04-25 物理故障每日图按周期调整坐标和柱线形态
### 实施步骤
- [x] 补源码级回归测试，锁定周/月/季度使用柱状、半年/年使用细竖线，并按周期格式化 X 轴标签。
- [x] 调整前端每日物理故障图配置，根据当前筛选类型选择柱宽、坐标轴指针和标签显示密度。
- [x] 运行统计页定向测试和 JS 语法检查。

## 2026-04-25 物理故障每日图横坐标跟随筛选范围
### 实施步骤
- [x] 补源码级回归测试，锁定周视图横坐标为当前周前后各 5 天，月/季度/半年/年视图为当前周期完整天。
- [x] 将后端每日物理故障图范围从固定全年改为基于 `_parse_time_range()` 的当前周期范围。
- [x] 调整每日故障数与中断时长查询窗口，按图表横坐标范围筛选并保留跨日/跨范围故障的时长重叠计算。
- [x] 运行统计页定向测试、JS 语法检查和 Python 语法校验。

## 2026-04-25 总体情况物理故障每日中断时长折线
### 实施步骤
- [x] 先补源码级回归测试，锁定年度每日物理故障图包含中断时长折线、右侧 Y 轴和按自然日重叠拆分时长的后端 helper。
- [x] 扩展后端 `physical_daily` 响应，返回每日累计中断时长数组，时长按故障发生至恢复时间与每个自然日的重叠小时数累计。
- [x] 扩展前端 ECharts 配置，在现有每日故障数堆叠竖线图上叠加中断时长折线并使用双 Y 轴。
- [x] 运行定向源码测试、JS 语法检查和 Python 语法校验。

## 2026-04-25 总体情况物理故障按天竖线图
### 实施步骤
- [x] 先补源码级回归测试，锁定总体情况卡片下方年度每日物理故障分类竖线图容器、后端响应字段和前端渲染入口。
- [x] 在统计 API 中按所选年份生成 1 月 1 日至 12 月 31 日每日物理故障分类计数，仅包含光缆中断、供电故障、空调故障、设备故障。
- [x] 在总体情况指标卡片下方新增图表卡片，使用 ECharts 堆叠细柱表现每日每类故障数量。
- [x] 补充图表样式、主题色和资源版本号。
- [x] 运行定向源码测试与 JS 语法检查。

## 2026-04-25 平均历时有效平均说明图标恢复
### 实施步骤
- [x] 在动态指标渲染 helper 中支持单个指标标签内展示说明图标。
- [x] 为“有效平均”指标恢复 `i` 说明图标，并保留 `<=30分钟` 提示。
- [x] 保持平均历时卡片 6 等分指标布局不回退到旧分组结构。
### 测试方案
- [x] 更新故障统计页源代码级回归测试，锁定有效平均说明图标配置和样式。
- [x] 运行故障统计页相关单元测试与 JS 语法检查。

## 2026-04-25 故障统计卡片指标一位小数精度
### 实施步骤
- [x] 在前端渲染层新增统一卡片指标格式化函数，所有卡片指标显示值统一为一位小数。
- [x] 将总体情况、光缆中断概览动态指标、平均历时指标和业务故障卡片指标接入统一格式化。
- [x] 将卡片趋势差值同步调整为一位小数显示，保留原始数值参与比较和下钻过滤。
### 测试方案
- [x] 更新源代码级回归测试，锁定卡片指标和趋势差值的一位小数格式化入口。
- [x] 运行故障统计页相关单元测试与 JS 语法检查。

## 2026-04-25 光缆中断平均历时卡片扁平化
### 实施步骤
- [x] 将“平均历时”卡片改为单行 6 个等宽指标：全口径平均、有效平均、日间平均、夜间平均、施工类、非施工类。
- [x] 移除原“滤除短时”“按时段”“按成因”分组标题和说明图标，统一使用原因TOP3类卡片的指标文字、单位、标签和箭头右置样式。
- [x] 平均历时指标改为通过通用 `buildFlexGroup()` 动态渲染，并保留原有下钻字段及有效历时附加过滤语义。
### 测试方案
- [x] 更新平均历时卡片源代码级回归测试，锁定 6 等分指标结构和动态渲染入口。
- [x] 运行故障统计页相关单元测试与 JS 语法检查。

## 2026-04-25 光缆中断历时卡片四卡同排
### 实施步骤
- [x] 将原“中断历时”“长时历时”两张混合卡片拆分为“中断历时”“原因TOP3”“光缆属性”“长时历时”四张卡片。
- [x] 四张历时卡片复用起数首行的 4 列加权布局，保持同排展示。
- [x] “中断历时”展示总历时，“原因TOP3”和“光缆属性”展示对应历时统计，“长时历时”展示总历时、6-8小时、8-10小时、10-12小时、12小时以上。
- [x] 保持指标等宽、统一字号、竖线分隔和红绿箭头右置。
### 测试方案
- [x] 更新光缆中断概览源代码级回归测试，锁定历时卡片拆分后的 DOM、JS 渲染入口和下钻字段。
- [x] 运行故障统计页相关单元测试与 JS 语法检查。

## 2026-04-25 光缆中断首行四卡片同排
### 实施步骤
- [x] 将“中断起数”“原因TOP3”“光缆属性”“长时起数”四张卡片放入同一个首行 grid。
- [x] 将首行 grid 从 3 列改为 4 列加权布局，前 3 张卡片保持紧凑，“长时起数”卡片按 5 个指标分配更宽列。
- [x] 保留每张卡片内部指标等宽、竖线分隔、统一字号和箭头右置规则。
### 测试方案
- [x] 补充源代码级回归测试，锁定前四张光缆中断卡片处于同一个 grid。
- [x] 运行故障统计页相关单元测试与 JS 语法检查。

## 2026-04-25 光缆中断长时起数卡片样式统一
### 实施步骤
- [x] 将原“长时情况”卡片改名为“长时起数”。
- [x] 将卡片指标改为同一行 5 个等宽指标：起数、6-8小时、8-10小时、10-12小时、12小时以上。
- [x] 去除原左侧主指标与右侧“历时分布”分组标题结构，统一使用与原因TOP3卡片一致的指标字号、单位字号、标签字号、箭头右置和竖线分隔。
- [x] 扩展前端指标渲染 helper，支持单个指标自定义下钻字段、下钻值、标签和指标 id。
### 测试方案
- [x] 补充光缆中断长时起数卡片源代码级回归测试。
- [x] 运行故障统计页相关单元测试与 JS 语法检查。

## 2026-04-25 光缆中断概览三卡片拆分
### 实施步骤
- [x] 将光缆中断首张合并卡片拆分为“中断起数”“原因TOP3”“光缆属性”三张等宽指标卡片。
- [x] “中断起数”卡片仅保留总起数、重复起数，重复起数趋势改为指标右侧箭头。
- [x] “原因TOP3”固定渲染 3 个原因指标，“光缆属性”固定渲染自控、第三方、其他/未填。
- [x] 三张卡片复用总体情况页卡片样式，统一指标字号、单位字号、标签字号、红绿箭头位置和等宽指标列。
### 测试方案
- [x] 补充光缆中断概览源代码级回归测试，锁定三卡片名称、指标名称、DOM id、等宽布局和箭头右置逻辑。
- [x] 运行故障统计页相关单元测试与 JS 语法检查。

# PLAN

## 2026-04-24 故障统计页面卡片改为参考图样式方案

### 目标
- [ ] 现有统计指标、统计分类、下钻筛选逻辑和后端数据口径全部保持不变，图片仅作为视觉样式参考。
- [ ] 将故障统计页面现有卡片调整为参考图样式：白底、细蓝色边框、底部蓝绿色标题条、卡内横向指标分栏、短竖线分隔、趋势百分比与对比值同排展示。
- [ ] 按“把现有指标分类套入参考图视觉结构”的原则改造，不新增“隐患排查/整改推进/局方整改项/局方预落实”等图片示例分类。
- [ ] 保持 NetBox/Bootstrap 5 原生风格，不引入 React/Vue，不修改 NetBox 核心目录。

### 当前代码落点
- [ ] 模板入口：`netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`，业务 Tab 当前只有 `#service-cards-container` 容器，物理概览卡片为静态 HTML + JS 填数。
- [ ] 样式入口：`netbox_otnfaults/static/netbox_otnfaults/css/statistics_dashboard.css`，已有 `.svc-card` 和 `.statistics-cable-break-*` 两套卡片样式。
- [ ] 渲染入口：`netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`，业务卡片由 `renderServiceCards()` 动态生成。
- [ ] 数据入口：`netbox_otnfaults/statistics_views.py` 继续使用现有统计响应；本次只调整前端结构与样式，不改变后端统计口径。

### 推荐方案
- [ ] 新增一套通用统计卡片样式类，例如 `.statistics-strip-card`、`.statistics-strip-card-body`、`.statistics-strip-card-metrics`、`.statistics-strip-card-metric`、`.statistics-strip-card-footer`。
- [ ] 卡片结构采用：上半部分白底指标区，固定最小高度，横向等分 2-3 个指标组；指标组内使用“大数字 + 趋势/对比值 + 小标签”层级；指标组之间使用短竖线分隔；下半部分使用蓝绿色实心标题条展示卡片名称。
- [ ] 现有每个统计分类继续作为一张卡片标题，放入底部蓝绿色标题条；现有分类下的指标作为上半部分横向指标组。
- [ ] 物理故障统计中的“总体情况”“光缆中断概览”等现有卡片，按当前指标组自然套入：主指标放左侧首个指标组，分类/原因/来源/长时等子指标放后续指标组。
- [ ] 业务故障统计中的现有服务卡片，继续按当前 `services` 数据逐张渲染：服务名称作为标题条，故障总数、累计时长、平均时长、长时故障、重复故障、SLA 等作为指标组，不新增后端字段。
- [ ] `renderServiceCards()` 可拆分为小函数：`formatTrendPercent(current, previous)`、`renderStripMetric(metric)`、`renderStripCard(card)`；若当前数据没有同比/环比值，对应趋势位置留空或展示现有 SLA/分类补充信息。

### 指标映射原则
- [ ] 不新增图片中的四个示例分类名称，不把“隐患排查/整改推进/局方整改项/局方预落实”写入业务逻辑。
- [ ] 不新增 `summary_cards` 等新的后端聚合响应字段；前端只消费当前 `kpis`、`charts`、`cable_break_overview`、`services` 等既有数据。
- [ ] 已有下钻字段、`data-filter-field`、`data-filter-value` 和图表过滤行为保持不变，只调整承载这些元素的 HTML 结构和 CSS。
- [ ] 指标过多的现有分类允许拆成多行卡片区域或横向滚动，但卡片内部文本不能重叠。

### 实施步骤
- [x] 增加源代码级测试，覆盖现有统计卡片使用新的 strip-card 结构、底部标题条、横向指标分隔、响应式布局，且不出现图片示例分类名称。
- [x] 调整 `statistics_dashboard.html` 中物理统计卡片结构，为总体情况和光缆中断概览套用新视觉类，同时保留现有 DOM id 与下钻属性。
- [x] 调整 `statistics_dashboard.html` 中业务 Tab 容器 class，为新卡片布局预留语义类。
- [x] 调整 `statistics_dashboard.js` 的 `renderServiceCards()`，用现有 `services` 字段生成参考图样式卡片，不新增 API 字段依赖。
- [x] 调整 `statistics_dashboard.css`，实现参考图边框、标题条、指标排版、趋势颜色、移动端换行和深色主题变量。
- [x] 若新增或修改静态资源版本号，同步更新 `statistics_dashboard.css/js` 的 query version，并更新测试断言。
- [x] 运行定向验证：`python -m unittest tests.test_statistics_cable_break_overview`、`python -m unittest tests.test_statistics_dashboard_assets tests.test_statistics_service_sorting`，以及 `node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`。

### 2026-04-24 总体情况卡片紧凑化补充
- [x] 保持只调整“总体情况”卡片，其它卡片暂不跟随修改。
- [x] 总指标和所有分项指标使用同一套数字、单位、标签字号，避免左侧总指标视觉上偏大。
- [x] 底部“总体情况”标题条字号调整为与“物理故障”标签一致，并显著压缩标题条高度。
- [x] 指标行整体改为狭窄紧凑高度，减少顶部白底区域留白，同时保留竖线分隔和箭头右置。
- [x] 补充源代码级测试后再修改 CSS/模板，并运行统计页面相关测试和 JS 语法检查。

### 2026-04-24 总体情况指标固定宽度补充
- [x] 总体情况卡片内所有指标项使用固定等宽槽位，包括左侧总指标和右侧分类指标。
- [x] 指标数值、单位、趋势箭头作为一行整体居中，标签也居中，避免有箭头与无箭头项目视觉中心不一致。
- [x] 保持箭头仍位于指标右侧，保持竖线分隔。
- [x] 先补测试再修改 CSS/模板，并回归统计页面测试与 JS 语法检查。

### 2026-04-24 总体情况指标错位修正
- [x] 定位错位根因：总指标和分类指标分属两个 flex 区域，趋势箭头内容溢出固定槽位后会挤到相邻指标。
- [x] 将总体情况指标行改为 7 列等分 grid，总指标和 6 个分类指标共享同一列轨道。
- [x] 分类容器和分组容器在总体情况卡片内使用 `display: contents`，避免额外 flex 包装影响列宽。
- [x] 保留总指标后和分类指标之间的竖线分隔，并保持数值行居中。

### 2026-04-24 光缆中断内容独立 Tab
- [x] 在主 Tab 导航中新增“光缆中断”Tab，位于“物理故障统计”和“业务故障统计”之间。
- [x] 物理故障统计 Tab 仅保留“总体情况”区域。
- [x] 从“光缆中断概览”开始，到历时频数、图表、过滤汇总和故障明细，整体移入“光缆中断”Tab。
- [x] 保留现有 DOM id、按钮、图表容器、下钻表格和 JS 绑定，不改后端接口。
- [x] 先补测试，再调整模板，并运行统计页面模板测试、资源测试和 JS 语法检查。

### 2026-04-24 总体情况 Tab 与卡片文案调整
- [x] 将原“物理故障统计”Tab 名称改为“总体情况”。
- [x] 移除总体情况卡片外部的“总体情况”标题。
- [x] 将总体情况卡片底部标题从“总体情况”改为“物理故障”。
- [x] 将总体情况卡片左侧指标标签从“物理故障”改为“故障总数”。
- [x] 保留现有 DOM id、统计口径、箭头位置和卡片布局。

### 2026-04-24 物理故障总数口径与其他卡片拆分
- [x] 故障总数在当前时间范围统计约束下排除光缆劣化和光缆抖动。
- [x] 物理故障卡片的分类指标不再显示光缆劣化和光缆抖动。
- [x] 新增第二张“其他”卡片，包含光缆劣化、光缆抖动、挂起的故障三个指标。
- [x] 三个“其他”指标单位均为“起”，并支持与上一周期对比箭头。
- [x] 保留光缆中断 Tab 和现有下钻/图表接口行为。

### 2026-04-24 总体情况双卡片布局修正
- [x] 左侧物理故障卡片从旧 7 列调整为当前 5 个指标的 5 列等分布局。
- [x] 右侧“其他”卡片调整为 3 个指标的 3 列等分布局，和左侧卡片使用一致的居中与竖线规则。
- [x] 两张卡片统一白底指标区和底部标题条高度，减少垂直方向留白。
- [x] 保留左侧、右侧指标的红绿箭头右置逻辑。

### 风险与约束
- [ ] 不修改 `netbox/` 核心目录。
- [ ] 不凭空新增 NetBox API，也不新增本次视觉改造不需要的插件 API 字段。
- [ ] 卡片文本必须在窄屏不重叠，指标数量过多时允许换行或压缩字号，但不使用随视口宽度缩放的字体。
- [ ] 当前仓库显示部分历史文件中文在 PowerShell 输出中有乱码，实施时应保持文件 UTF-8 内容，不做无关编码重写。

## 2026-04-23 地图样式个人偏好实施计划

- [x] 完成中文设计规格：`docs/superpowers/specs/2026-04-23-map-style-preferences-design.md`。
- [x] 编写实施计划：`docs/superpowers/plans/2026-04-23-map-style-preferences.md`。
- [ ] 按计划先补充源码级回归测试，再实现偏好模型、服务、API、模板注入和前端控制面板。
- [ ] 运行定向源码测试、Python 语法检查和 JavaScript 语法检查。
- [ ] 如有真实 NetBox 环境，运行 `makemigrations` 后紧接着运行 `migrate`。

## 2026-04-23 Fat Views refactor for map data APIs

- [x] Add source regression coverage requiring shared color helpers and extracted map serializers/services.
- [x] Move `_get_hex_color` and shared map color config generation into `netbox_otnfaults/utils.py`.
- [x] Move site and fault marker serialization out of `views.py` into a dedicated map data module.
- [x] Update `OtnFaultMapDataView` and `StatisticsCableBreakMapDataAPI` to orchestrate querysets only.
- [x] Run focused source tests and Python syntax checks.

## 2026-04-23 故障编号并发生成修复

### 实施步骤
- [x] 补充源码级回归测试，覆盖 `OtnFault.save()` 自动生成 `fault_number` 时必须使用事务、行锁和唯一冲突重试。
- [x] 修改 `OtnFault.save()`，在数据库事务中通过 `select_for_update()` 锁定同日前缀编号记录后生成新编号。
- [x] 对自动生成编号保存时的 `IntegrityError` 做有限重试，覆盖当天首条记录无可锁行和并发快照竞争场景。
- [x] 运行定向测试与 Python 语法检查。

## Statistics cable-break map in-map quick filters

- [x] Add source regression assertions for a MapLibre in-map quick filter control
- [x] Add map marker metadata for self-controlled, long, repeat, and valid-duration filtering
- [x] Filter the existing GeoJSON source in the map plugin without reloading the iframe
- [x] Run focused source tests and syntax checks

## Statistics cable-break map quick filter visual polish

- [x] Add source regression assertions for icon-and-text MapLibre-style buttons
- [x] Style quick filters to match existing white map controls with blue selected text
- [x] Run focused source tests and JavaScript syntax checks

## Statistics cable-break map separated quick filter buttons

- [x] Add source regression assertions for separated map quick filter buttons
- [x] Split visual styling so each filter button has independent radius and shadow
- [x] Run focused source tests and JavaScript syntax checks

## Statistics cable-break map quick filter hover background

- [x] Add source regression assertion that quick filter hover keeps an opaque white background
- [x] Override MapLibre button hover/active background for quick filter buttons
- [x] Run focused source tests and JavaScript syntax checks

## Statistics cable-break map coordinate fallback audit

- [x] Trace `skipped_count` from the statistics map API through `FaultDataService` and the MapLibre control
- [x] Identify that current fallback uses fault coordinates, then only the A-side site coordinates
- [x] Add a regression assertion that Z-side site coordinates are also considered before skipping a fault
- [x] Update the map data API to return source metadata for A-side and Z-side coordinate fallbacks
- [x] Run the focused source test and Python syntax check

## Statistics cable-break map modal width hardening

- [x] Inspect modal CSS and screenshot symptom for width override/caching issues
- [x] Add a source regression assertion for a stronger dialog width selector
- [x] Harden the modal width rules against Bootstrap/Tabler defaults on desktop and small screens
- [x] Run the focused statistics dashboard source test

## Statistics cable-break map fixed viewport

- [x] Trace the apparent narrow map symptom to data-driven `fitBounds()`
- [x] Add a regression assertion that the statistics map uses a stable center/zoom instead of fitting fault data bounds
- [x] Replace data-driven initial viewport fitting with fixed map center/zoom and resize after iframe layout settles
- [x] Bump the statistics map plugin asset version
- [x] Run focused tests

## Statistics cable-break map modal period navigation

- [x] Inspect existing statistics period label and main previous/next period controls
- [x] Add source regression assertions for modal period label, navigation buttons, iframe refresh, and asset version bump
- [x] Add modal title controls and period label markup using the existing period label visual style
- [x] Add independent modal period state so changing the map period reloads only the iframe
- [x] Run focused tests

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
## 2026-04-22 地图帧率调试开关

### 实施步骤
- [x] 将 `mapbox/mapbox-gl-framerate` v0.1.2 发布文件作为本地静态资源纳入插件，避免运行时依赖外网。
- [x] 新增共享前端控制器 `map_framerate_toggle.js`，默认不显示帧率控件，仅在复杂热键 `Ctrl+Alt+Shift+F` 触发时打开/关闭。
- [x] 兼容当前项目使用的 MapLibre 全局对象：加载库前提供 `window.mapboxgl = window.maplibregl` 兼容别名，控制器优先使用 `window.FrameRateControl`，再回退到 `mapboxgl.FrameRateControl`。
- [x] 在 `unified_map.html` 覆盖的所有地图窗口加载帧率库和控制器，并在 `OTNMapCore` 地图创建后注册热键。
- [x] 在大屏地图 `dashboard.html` / `dashboard/map_engine.js` 加载并注册同一控制器，覆盖独立地图入口。
- [x] 增加源码级测试，验证默认关闭、热键组合、资源加载入口和大屏/统一地图都接入。

### 测试方案
- [x] 运行新增帧率静态资源测试。
- [x] 运行涉及统一地图资源加载的既有测试。
- [x] 对修改的 JS 文件运行语法检查；本次未修改生产 Python。

## 2026-04-22 故障统计页面主题适配
### 实施步骤
- [x] 统一 `statistics_dashboard.css` 的浅色/深色主题变量，覆盖页面背景、筛选控件、卡片、KPI 标签、分隔线、表格和地图弹窗 loading。
- [x] 消除统计页内硬编码文本色造成的深色模式低对比问题，重点覆盖指标名称、分组标题、日期选择区域和筛选摘要。
- [x] 调整 `statistics_dashboard.js` 中 ECharts 配色，按当前 `data-bs-theme` 生成坐标轴、图例、tooltip、标签、网格线和柱状/饼图色板。
- [x] 监听主题属性变化并重新渲染已加载图表，避免用户切换 NetBox 主题后图表仍停留在旧主题颜色。
- [x] 增加静态测试，验证主题 CSS 选择器、图表主题 helper 和静态资源版本号已接入。

### 测试方案
- [x] 运行 `python -m unittest tests.test_statistics_dashboard_assets`。
- [x] 运行 `node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`。
## 2026-04-22 本地时区日期时间一致性审计

### 实施步骤
- [x] 审计插件生产代码中的 `timezone.now()`、`datetime.now()`、`date.today()`、前端 `Date.UTC()` 等当前时间用法。
- [x] 将业务日期边界、默认年份、前端“当前/未来”判断、展示格式化改为本地时区口径。
- [x] 将持续时长计算中的当前时间统一改为 `timezone.localtime()`，保证插件运行时代码不直接读取 UTC 当前时间。
- [x] 补充源码级回归测试，覆盖业务代码中不得直接用 UTC 当前日期做日期边界、年份或格式化。
- [x] 运行定向测试、语法检查和最终差异审查。

### 风险约束
- [x] 不修改 NetBox 核心目录。
- [x] 不改变已有查询业务口径，只修正“当前日期时间”的时区来源。
- [x] 不把持续时长计算改成 naive datetime。
## 2026-04-23 ImportOtnPaths 导入参数增强
### 实施步骤
- [x] 为 `ImportOtnPaths` 增加 ArcGIS 线图层 URL 脚本参数，默认保持当前 `FeatureServer/1`。
- [x] 为 `ImportOtnPaths` 增加允许重复端点入库开关，默认保持现有查重跳过行为。
- [x] 补充单元测试覆盖自定义 ArcGIS URL、默认重复端点跳过、开启开关后重复端点入库。
- [x] 运行定向测试和语法检查。

## 2026-04-23 路径组地图网络拓扑开关
### 实施步骤
- [x] 扩展 `LayerToggleControl`，支持通过配置隐藏故障分布图专属的视图模式、时间范围和故障类型筛选，仅保留“显示网络拓扑”图层开关。
- [x] 在 `pathgroup` 地图模式加载 `controls/LayerToggleControl.js`，并在 `location_mode.js` 中仅为路径组地图初始化拓扑图层开关。
- [x] 保持故障分布图现有控件默认行为不变，避免影响故障点/热力图/故障类型筛选。
- [x] 增加源码级回归测试，覆盖路径组地图加载并初始化拓扑开关、拓扑专用配置不渲染故障筛选区。

### 测试方案
- [x] 运行 `python -m unittest tests.test_pathgroup_topology_toggle`。
- [x] `python -m py_compile .\netbox_otnfaults\map_modes.py` 受当前 `.pyc` 写入权限阻断；已改用 `ast.parse` 对 `map_modes.py` 做只读语法检查。
- [x] 运行 `node --check netbox_otnfaults/static/netbox_otnfaults/js/controls/LayerToggleControl.js` 和 `node --check netbox_otnfaults/static/netbox_otnfaults/js/modes/location_mode.js`。
## 2026-04-24 取消 ImportOtnPaths 自动写长度
### 实施步骤
- [x] 为 `ImportOtnPaths` 增加回归测试，确认导入时不再自动写入 `calculated_length`。
- [x] 移除 `ImportOtnPaths` 中基于几何自动计算长度并写入 `calculated_length` 的逻辑。
- [x] 调整导入日志，不再输出脚本自动计算出的长度值。
- [x] 运行定向测试和只读语法检查。

## 2026-04-24 自控/第三方口径全局统一
### 实施步骤
- [x] 先补源码级回归测试，覆盖统计页分组函数、光缆中断统计地图快捷筛选依赖字段，以及周报视图/脚本中的自控与第三方计数、时长口径。
- [x] 统一资源分组规则：`self_built` 与 `coordinated` 归为“自控”，`leased` 归为“第三方”，其他或未填归为“其他/未填”。
- [x] 收敛所有手写分组逻辑到共享 helper，避免统计页、地图、周报再次出现分叉口径。
- [x] 运行定向测试与必要的语法校验，确认统计页、地图与周报相关链路一致生效。
## 2026-04-25 故障日历日期跳转故障列表

- [x] 增加源码级测试，要求日历日期单元格生成故障列表筛选 URL
- [x] 在日历小组件中为每天构造 `fault_occurrence_time_after` / `fault_occurrence_time_before` 查询参数
- [x] 调整日历模板，使日期单元格可点击并跳转到筛选后的故障列表
- [x] 运行定向测试确认日历小组件源码约束通过

## 2026-04-24 总体情况指标字号修正
### 实施步骤
- [x] 总体情况双卡片内的 compact 分组不再缩小数字、标签和趋势箭头字号。
- [x] 保持其它统计卡片的 compact 缩小规则不变，避免扩大视觉改动范围。
- [x] 以“其他”卡片为基准，统一物理故障与其他两张卡片的数值、单位、标签字号选择器。

### 测试方案
- [x] 运行总体情况字号定向回归测试。
- [x] 运行故障统计页相关单元测试与 JS 语法检查。

## 2026-04-25 光缆中断 Tab 卡片统一总体情况样式
### 实施步骤
- [x] 将光缆中断 Tab 概览卡片改为总体情况 Tab 的窄条卡片样式。
- [x] 卡片名称收敛为“中断情况、长时情况、中断历时、长时历时、平均历时”。
- [x] 主指标和分项指标统一使用 `statistics-overall-kpi-*` 字号、单位、标签和趋势箭头样式。
- [x] 保留现有统计口径、DOM id、下钻字段、地图按钮和图表区域。
- [x] 移除独立“光缆中断”Tab，将概览、图表、过滤汇总和明细整体并入“总体情况”Tab。

### 测试方案
- [x] 新增源码级回归测试锁定光缆中断卡片样式和文案。
- [x] 运行故障统计页相关单元测试与 JS 语法检查。
## 2026-04-25 Statistics dashboard wide layout
### Steps
- [x] Override the statistics page wrapper width only under `.page-statistics`.
- [x] Keep mobile width at 100% to avoid horizontal overflow on small screens.
- [x] Add a source-level regression check for the wide container CSS.
- [x] Run the targeted statistics dashboard tests and JS syntax check.

## 2026-04-25 Statistics dashboard horizontal overflow fix
### Steps
- [x] Identify `100vw` wrapper sizing as the source of page-level horizontal overflow.
- [x] Replace viewport-based sizing with natural parent-width sizing while keeping the removed `container-xl` max width.
- [x] Update the regression check to reject the overflowing `100vw` width rule.
- [x] Run the targeted statistics dashboard tests and JS syntax check.

## 2026-04-25 Cable break duration row width balance
### Steps
- [x] Split the cable-break duration row from the count-row grid sizing.
- [x] Reduce the first duration card column to half of the previous proportional width.
- [x] Distribute the saved width across the remaining three cards in the row.
- [x] Add source-level assertions for the dedicated duration-row grid.

## 2026-04-25 Fault duration histogram style
### Steps
- [x] Add a failing source-level regression test for contiguous histogram bars and Y-axis horizontal grid lines.
- [x] Update the cable-break duration frequency chart ECharts options.
- [x] Run the targeted regression test and JS syntax check.

## 2026-04-25 Hide fault duration histogram Y-axis grid lines
### Steps
- [x] Update the histogram regression test to require hidden Y-axis horizontal grid lines.
- [x] Set the histogram Y-axis `splitLine` to `show: false` while preserving contiguous bars.
- [x] Run the targeted statistics dashboard tests and JS syntax check.

## 2026-04-25 Separate repeat interruption metric card
### Steps
- [x] Add failing source-level assertions for moving repeat count out of the interruption count card.
- [x] Move the repeat count metric into an independent `重复中断` card to the right of average duration.
- [x] Align the interruption count row column widths with the interruption duration row.

## 2026-04-25 Split average duration cards
### Steps
- [x] Add failing source-level assertions for splitting the average duration card into overall and short-filtered cards.
- [x] Move the short-duration info icon from the removed valid-average metric to the filtered-average card footer.
- [x] Render overall average separately from daytime, nighttime, construction, and non-construction filtered averages.

## 2026-04-25 Move duration histogram into chart row
### Steps
- [x] Add a failing source-level assertion that histogram, reason, and resource charts share one row.
- [x] Move the duration histogram card from the cable-break overview section into the ECharts chart section.
- [x] Change the histogram, reason, and resource chart columns to three equal `col-md-4` cards.

## 2026-04-25 Duration histogram click filtering
### Steps
- [x] Add source-level regression coverage for duration histogram click filtering.
- [x] Add a detail-list histogram bucket field matching the chart labels.
- [x] Bind histogram bar clicks to the same local detail filtering flow as other charts.
- [x] Run the targeted dashboard tests and syntax checks.

## 2026-04-25 Restore filtered average valid metric
### Steps
- [x] Add source-level regression coverage requiring the filtered-average card to include valid average first.
- [x] Restore the valid average metric in the filtered-average card while keeping the footer info icon.
- [x] Switch the filtered-average card layout from four to five equal metric columns.
- [x] Run the targeted dashboard tests and JS syntax check.

## 2026-04-25 Count metrics integer formatting
### Steps
- [x] Add source-level regression coverage requiring count metrics and count deltas to use integer formatting.
- [x] Split count formatting from duration/percent formatting in the dashboard script.
- [x] Apply integer formatting to `起`/`次` metrics, top-level count KPIs, and service count details.
- [x] Run the targeted dashboard tests and JS syntax check.

## 2026-04-25 Split service fault statistics tabs
### Steps
- [x] Add source-level regression coverage for separate bare-fiber and circuit service fault tabs.
- [x] Rename the existing service tab to bare-fiber service fault statistics and add a circuit service fault statistics tab.
- [x] Render bare-fiber and circuit service cards into separate containers by service type.
- [x] Load service statistics data when either service tab is selected.
- [x] Run the targeted dashboard tests and JS syntax check.

## 2026-04-25 Rename fault statistics tabs
### Steps
- [x] Rename the overall tab display text to physical faults.
- [x] Shorten bare-fiber and circuit service tab display text by removing the statistics suffix.
- [x] Update source-level assertions for the new tab labels.

## 2026-04-25 Polish cable break overview heading
### Steps
- [x] Replace the compact Bootstrap title/button pairing with dedicated dashboard heading classes.
- [x] Increase the cable-break overview title and map action text size while keeping the existing theme colors.
- [x] Rename the map action text to `定位地图` and update source-level assertions.

## 2026-04-25 Refine cable break overview section title
### Steps
- [x] Keep the map action button unchanged.
- [x] Reduce the section title below the page title hierarchy.
- [x] Add a subtle teal accent marker so the title reads as a designed section header.
- [x] Update source-level assertions for the refined title style.

## 2026-04-25 Add overall section heading
### Steps
- [x] Add a `总体情况` section heading above the physical fault cards using the same refined section title style.
- [x] Rename the cable-break section heading from `光缆中断概览` to `光缆中断情况`.
- [x] Update source-level assertions for the new and renamed section headings.

## 2026-04-26 Restore histogram axis label and spacing regressions
### Steps
- [x] Restore the duration histogram x-axis name positioning and bump the dashboard JS cache version.
- [x] Keep the duration histogram as contiguous histogram bars while preventing the axis name from clipping.
- [x] Restore source-level template spacing classes and CSS selector formatting used by regression tests.
- [x] Re-verify the statistics dashboard tests and JavaScript syntax.
## 2026-04-26 增加物理故障图与盒须图底部留白
### 实施步骤
- [x] 更新源码级回归测试，锁定两张图继续共享 grid 且底部留白增加。
- [x] 调整共享 ECharts grid bottom，保持 X 轴对齐同时改善下边距。
- [x] 运行统计页定向测试与 JS 语法检查。

## 2026-04-26 对齐物理故障图与中断时长盒须图 X 轴
### 实施步骤
- [x] 定位两张 ECharts 图的 grid/containLabel 差异，确认右侧 Y 轴导致绘图区宽度不一致。
- [x] 将物理故障数图和中断时长分布盒须图改为共享固定 grid，避免各自 Y 轴标签重新压缩 X 轴。
- [x] 更新统计页源码级回归测试并运行 JS 语法检查、定向测试。

## 2026-04-26 Cable break cluster status color
### Steps
- [x] Add regression coverage requiring cable-break map clusters to aggregate processing status.
- [x] Change cable-break cluster color to prioritize processing status instead of point count.
- [x] Re-run the targeted statistics dashboard test and JavaScript syntax check.
## 2026-04-27 故障统计页面增加指标说明
### 实施步骤
- [x] 梳理 `statistics_views.py`、`statistics_dashboard.html`、`statistics_dashboard.js` 中现有统计指标和口径。
- [x] 增加源码级回归测试，锁定指标说明按钮、模态窗口和主要统计逻辑文案。
- [x] 在统计页头部增加“指标说明”按钮，并使用 Bootstrap 5 模态窗口展示说明。
- [x] 在模态窗口中覆盖总体情况、光缆中断、图表下钻和业务故障统计口径。
- [x] 运行统计页定向测试、统计页相关测试和前端脚本语法检查。

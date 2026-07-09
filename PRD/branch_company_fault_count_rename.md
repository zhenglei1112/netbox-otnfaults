# 子公司故障统计页面字段重命名 PRD

## 1. 业务背景
在网络运维和故障管理体系中，故障的具体发生次数通常用“起”作为单位来表示。
在当前的 OTN 故障统计系统的“子公司故障”分析板块中，图表和卡片的标签文字使用了“故障数”，这在口语和书面语中不够精确。为了使系统中的术语表达更为规范和专业，现需要将此页面下的相关文案由“故障数”统一修改为“故障起数”。

## 2. 需求范围
本次修改仅限“子公司故障”模块的图表、卡片以及提示框文案。具体涉及：
1. **子公司故障数柱状图卡片标题**：
   - 现名称：“故障数”
   - 建议修改为：“故障起数”
2. **年初至今周趋势切换按钮标签**：
   - 现名称：“故障数量”
   - 建议修改为：“故障起数”
3. **图表悬浮提示框 (Tooltip)**：
   - 月度统计柱状图及运行月历柱状图等 tooltip 提示中的“故障数：”修改为“故障起数：”。
4. **图表图例/系列名称 (Series Name)**：
   - 图表配置中的 `name`（例如 `'故障数'`）统一修改为 `'故障起数'`，相应的千公里指标 `'千公里故障数'` 修改为 `'千公里故障起数'`。

## 3. 详细设计与对应修改点

### 3.1 模板文案修改
- 文件：[statistics_dashboard.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html)
  - 第 1035 行：`<h3 class="card-title mb-0" style="font-size: 1rem;">故障数</h3>` -> 修改为 `故障起数`
  - 第 1097 行：`<label class="btn btn-outline-primary" for="branch-company-weekly-count">故障数量</label>` -> 修改为 `故障起数`

### 3.2 脚本渲染逻辑修改
- 文件：[statistics_dashboard.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js)
  - 运行月历提示框格式化（第 2503 行）：`故障数：` -> 修改为 `故障起数：`
  - 运行月历系列名称（第 2594 行）：`name: '故障数'` -> 修改为 `name: '故障起数'`
  - 子公司省份对比图表提示框格式化（第 2874 行）：`故障数: ` -> 修改为 `故障起数: `
  - 子公司省份对比图表系列名称（第 2915 行）：`countMetric === 'count' ? '故障数' : '千公里故障数'` -> 修改为 `'故障起数' : '千公里故障起数'`

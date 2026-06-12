# 子公司绩效卡片指标数据部分UI重构方案

此文档定义了子公司绩效卡片中三个表格数据板块（“裸纤业务”、“光缆中断”、“供电故障”）的 UI 重构方案，使用裸纤业务卡片的年度累计板块样式重新设计，以统一系统的仪表盘视觉风格。

## 1. 业务背景与改动意图
当前子公司绩效卡片中的三个主要数据板块（裸纤业务、光缆中断、供电故障）在展现各分公司的年度累计考核指标时，采用了基于灰色缝隙背景（`#e8edf5`）及两列排布的表格网格。
这种呈现方式存在以下问题：
1. **视觉割裂**：与“一张图”看板中裸纤卡片/电路卡片现代且精致的年度累计网格风格（纯白背景、值在上标签在下、垂直实线分隔）不一致。
2. **排版局限**：每个指标项目均为“左标签右数值”，在指标较多（如光缆中断有7个指标）时，导致纵向空间被拉长，界面重复感强，不够美观。

为了提高系统界面的一致性和专业度，需要使用裸纤业务卡片的 UI 来重新设计这三个表格数据板块。

---

## 2. 优化方案核心设计

### 2.1 整体网格与排版升级
废弃原有基于 1px gap 灰色分隔线的左右排布网格，改用类似裸纤/电路业务卡片年度累计板块的平铺网格：
* **数据对齐**：统一改为 **“数值在上（醒目大字+小字单位），指标标签在下（小字灰色加粗）”** 的垂直对齐结构。
* **背景与分隔线**：网格背景全部为纯白，删除原有的生硬灰色底色。移除模块外框线及行间水平分割线，但**指标格与格之间使用垂直细实线（`1px solid var(--statistics-divider)`）进行分割**，类似于裸纤/电路业务看板的分组指标样式，确保极简现代的同时结构清晰。
* **板块外部框线与背景剥离（卡片级精简）**：取消原“裸纤业务”、“光缆中断”、“供电故障”这三个子板块各自的独立小卡片框线、白色背景、圆角与阴影。它们将直接作为平铺内容融入分公司绩效大卡片中，降低卡片嵌套的视觉层级。
* **分组横向分割（仿照裸纤卡片）**：仿照裸纤业务卡片不同功能模块的设计，各子板块之间使用极简的横向底分割线（`border-bottom: 1px solid var(--statistics-divider)`）进行视觉上的分组隔离，且最后一个子板块的底分割线自动清除，杜绝多重边框重叠。
* **多列响应式网格**：
  * **裸纤业务**（4项）：**1 行 4 列**。
  * **光缆中断**（7项）：**2 行 4 列**（第一行排4项，第二行排3项，最后一格留白占位），行间通过合理的 grid gap 进行自然过渡。
  * **供电故障**（2项）：**1 行 2 列**。

### 2.2 板块标题头部图标化与对齐 (Header Accent)
在各板块 Heading 引入裸纤卡片式的高清标题 UI，将小图标与文字以 flex 水平居中对齐，并赋予相应的主题色彩：
* **结构组装**：标题由外层 `.branch-performance-annual-heading` 容器、内层 `.branch-performance-annual-icon` 图标容器和 `.branch-performance-annual-title` 标题文本三部分组成，并保留 `gap: 0.62rem`。
* **主题色渲染**：
  * **裸纤业务**：引入 `<i class="mdi mdi-server-network"></i>`，图标颜色设定为 `#078087`。
  * **光缆中断**：引入 `<i class="mdi mdi-transit-connection-horizontal"></i>`，图标颜色设定为 `#7c4a03`。
  * **供电故障**：引入 `<i class="mdi mdi-flash"></i>`，图标颜色设定为 `#53389e`。
* **文字规格**：字体大小设为 `1rem`，颜色为主题字色 `var(--statistics-heading)`，字重设为高亮的 `700`，彻底消除原有小标题的单薄感。

---

## 3. 技术实现细节

### 3.1 JS 模板层重构 (`statistics_dashboard.js`)
* 修改 `renderBranchPerformanceMetricItem` 方法：
  将原本的左右排布 HTML 替换为垂直的“值+单位”在上、“标签”在下的新 HTML 结构。
* 修改 `renderBranchPerformanceAnnualSection` 方法：
  根据 `modifier` 传入的板块类别，在标题中动态拼接相应的 MDI 图标与包裹 span，满足新标题容器的层次结构。

### 3.2 CSS 样式层定义 (`statistics_dashboard.css`)
* 重构 `.branch-performance-annual-stats` 容器，将其变更为 `flex` 纵向流式排布，`gap` 置零，使板块衔接更紧凑。
* 重构 `.branch-performance-annual-section` 样式，将其 `background`、`border`、`box-shadow` 和 `border-radius` 全部剔除，统一设置底边框 `border-bottom: 1px solid var(--statistics-divider)` 及适当的上下内边距，实现无卡片感的分组横线分割。
* 特殊过滤：为 `.branch-performance-annual-stats .branch-performance-annual-section:last-child` 过滤掉底边框以防与月历图双重边框冲突。
* 将 `.branch-performance-annual-heading` 头部背景和底边框移除，重写为 `display: flex; align-items: center; gap: 0.62rem` 且背景透明。
* 新增 `.branch-performance-annual-icon`，字号为 `1.15rem`，并根据不同板块类名为其赋予相应的核心高亮色。
* 新增 `.branch-performance-annual-title`，字号为 `1rem` 粗体，文字颜色继承系统主标题色。
* 新增 `.branch-performance-annual-grid-v2` 样式，指定为白色背景，设置适当的行间距 `gap: 0.65rem 0`，并清除多余边框。
* 通过子类修饰符，分别为 `--bare-fiber`、`--cable-break` 和 `--power` 设置对应的 `grid-template-columns` 属性。
* 在 `.branch-performance-annual-metric-v2` 单元格间添加 `border-left`，并使用 `:nth-child(4n+1)` / `:nth-child(2n+1)` 过滤首列左边框。
* 定义新版数值（大字、加粗、特殊高亮色彩）及标签（小字、置底、灰色加粗）的文字格式。

# 分公司绩效卡片 UI 优化方案 PRD

## 1. 业务背景与改动意图
当前分公司绩效卡片展示了分公司的责任得分、全量得分、核心KPI、责任扣分情况以及主导故障原因。在现有的 UI 呈现中，存在以下几个痛点：
1. **评价标签不够醒目**：原有的“优秀”、“良好”、“关注”等评价信息以普通细字文本形式排版在公司名称下方，不够引人瞩目，无法一眼辨识绩效等级。
2. **“责任扣分”标题缺乏样式**：该标题使用了浏览器默认字体风格，显得与整体商务风格格格不入。
3. **责任扣分项的警告层级单一**：无论是否有扣分，所有扣分按钮一律使用相同的灰色边框与结构，这增加了用户的阅读心智负担。我们需要让有扣分的项目产生柔和的警示红，而 0 扣分的项目处于弱化灰色，突出视觉重点。
4. **整体布局拥挤重复**：右上角已经呈现了大字体的责任得分，但在左侧又重复显示了“责任得分 XX”，这部分信息可以进行整合与重组，使头部看起来更具商务高级感。

---

## 2. 优化方案核心设计

### 2.1 头部与评价标签优化
* **新布局**：将“优秀”、“良好”、“关注”、“待整改”等评价转化为**精致且高亮的旗标（Badge/徽章）**，并放置在右上角责任评分的下方，与其形成一个右对齐的整体区域。
* **旗标颜色处理**：
  * **优秀 (stable)**：淡绿色背景 + 醒目绿字 + 极淡绿边框。
  * **良好 (good)**：淡蓝色背景 + 醒目蓝字 + 极淡蓝边框。
  * **关注 (warning)**：淡黄色背景 + 醒目黄字 + 极淡黄边框。
  * **待整改 (danger)**：淡红色背景 + 醒目红字 + 极淡红边框。
* **左侧清爽化**：左侧仅显示大字号、粗体的分公司名称，去掉原公司名下方多余的小号评级文本。

### 2.2 责任扣分标题与内容区精致化
* **标题引入商务修饰线**：在“责任扣分”字样左侧增加一条**高度适中的主题色圆角竖条 (Accent Bar)**，瞬间提升商务报表的整体质感。
* **扣分网格视觉分级（微交互）**：
  * **无扣分项（扣分为 0）**：维持基础灰色背景和弱化文字，降低干扰，代表这一项指标十分优异。
  * **有扣分项（扣分 > 0）**：按钮背景自动呈现极淡的警告粉红（`rgba(214, 57, 57, 0.02)`），边框微调为淡粉红（`rgba(214, 57, 57, 0.15)`），且扣分数值高亮加粗为警示红（`#d63939`）。
  * **悬浮交互**：增加平滑的过渡动画，鼠标悬浮在任何扣分按钮上时高亮显示主题蓝边框，提示可点击下钻。

### 2.3 原因 TOP3 标签（Pill）层级区分
* **责任原因**：采用浅蓝色的精致胶囊 Pill，体现核心业务的重要度。
* **全量原因**：采用淡灰色偏低调的胶囊 Pill，在视觉上作为辅助参考，主次极其分明。

---

## 3. 技术实现细节

### 3.1 JS 修改细节 (`statistics_dashboard.js`)
* 修改 `renderBranchCompanyPerformanceCard` 方法：
  1. 在 `deductions` 的 `map` 渲染中，判断 `item.value > 0`。若大于 0，为 `button` 元素追加 `branch-performance-deduction--active` 样式类。
  2. 重构返回的 HTML 结构，去除左侧公司名下的 `<small>${escapeHtml(card.grade || '-')}</small>`。
  3. 将评分与级徽组合在右侧容器 `.branch-performance-header-right` 中，引入 `.branch-performance-grade-badge` 级徽。
  4. 为 `responsibility_reason_top3` 和 `overall_reason_top3` 分别传入类型参数，使 `renderBranchPerformanceReasonList` 生成不同样式的 Pill。

### 3.2 CSS 修改细节 (`statistics_dashboard.css`)
* 增加 `.branch-performance-header-right`：负责右上角大分值和级徽的垂直对齐与右贴紧。
* 增加 `.branch-performance-grade-badge` 及其四个子类：`--stable`, `--good`, `--warning`, `--danger`。
* 增加 `.branch-performance-deduction-heading` 的伪元素 `::before`，绘制左侧 3px 圆角竖线。
* 修改 `.branch-performance-deduction` 以支持无扣分下的轻量灰度，以及 `.branch-performance-deduction--active` 下的警告淡粉红。
* 增加胶囊标签的细分样式 `.branch-performance-reason-pill--responsibility` 与 `.branch-performance-reason-pill--overall`。

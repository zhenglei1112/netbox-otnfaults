# 态势大屏 85寸 4K 分辨率字体与布局优化方案

本文档为“中交信通网络运行态势图”大屏在 85寸 4K 物理大屏幕展示下的字体与布局自适应优化方案。通过第一性原理分析，在 4K 分辨率（3840x2160）下，传统像素单位（px）定义的字号和固定面板宽度会显得极小，必须对字体大小、布局尺寸和地图标注进行等比例自适应缩放。

---

## 方案设计

### 1. CSS 变量接管与大屏自适应 (KISS 原则)
当前页面样式中有大量写死的物理像素字号（如 `font-size: 11px;`, `12px;`, `13px;`）。为保证可维护性且避免大范围修改现有代码结构，我们采用 **CSS 变量统一声明与媒体查询局部覆写** 的策略：
1. **定义全局字体大小变量**：
   在 `dashboard.css` 的 `:root` 中统一定义各个层级的字体变量（从 `--fs-xxs` 到 `--fs-6xl`）。
2. **在现有规则中引用变量**：
   将现有的 `font-size: XXpx;` 替换为对应的 `font-size: var(--fs-XX);`。
3. **针对大分辨率（宽 >= 2560px）媒体查询**：
   在大屏媒体查询下，不改变现有 CSS 规则的选择器，而是直接 **重新声明这些 CSS 变量的值**。
   - 所有字体变量放大 **1.8 至 2 倍**；
   - 核心布局的尺寸参数进行同比例放大：
     - 面板宽度 `--panel-w` 由 `320px` 调整为 `600px`；
     - 头部高度 `--header-h` 由 `56px` 调整为 `110px`；
     - 底部高度 `--footer-h` 调整为 `70px`；
     - 卡片圆角及间距进行相应放大；
   - 对部分特定的容器、间距也通过 CSS 变量形式在大屏媒体查询下覆写，保证布局舒展，没有溢出。

### 2. 地图引擎标注字号放大
地图使用 MapLibre GL 渲染。在 4K 大屏下，如果不放大地图标注（站点名、省份名、路径信息等），地图上的标签将微缩得无法看清。
- 在 `map_engine.js` 初始化时，检测屏幕宽度 `window.innerWidth`：
  - 当宽度大于等于 `3400px` (4K 屏幕) 时，设置地图标签缩放因子 `mapTextScale = 1.8`；
  - 当宽度在 `2000px` 至 `3400px` 之间时，设置缩放因子 `mapTextScale = 1.4`；
  - 常规分辨率下，缩放因子为 `1.0`。
- 将 `map_engine.js` 中所有 `text-size` 的字号数值与该缩放因子相乘，实现地图文本的自适应放大。

### 3. 24H 趋势图 Canvas 模糊与字号优化
Canvas 在高分屏（如 4K 屏）下，若其 CSS 样式宽度大于 Canvas 本身的 `width` 属性，会导致严重的拉伸模糊。
- **动态高清像素适配**：
  在 `panels.js` 中的 `_updateTrendChart` 方法内，使用 `getBoundingClientRect()` 动态获取 Canvas 的呈现宽高，并结合 `window.devicePixelRatio` 重新设置 Canvas 的实际物理像素宽和高，最后在 Canvas 的 2D 绘图上下文中应用 `scale(dpr, dpr)`。
- **绘制元素等比放大**：
  根据画布当前的实际呈现宽度与基准宽度（`320px`）的比值，计算出缩放比例因子 `chartScale`。
  将 Canvas 中绘制的线条宽度（`lineWidth`）、散点半径（`arc`）、文字字号（`ctx.font`）、线条模糊半径及各个边距都乘以 `chartScale`，确保在 4K 屏宽大侧边栏中渲染出细腻、清晰的曲线 and 标签。

---

## 拟修改文件

### 1. [MODIFY] [dashboard.css](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/css/dashboard.css)
- 在 `:root` 中声明全局字体大小 CSS 变量和关键间距变量。
- 替换现有的字号定义为变量。
- 增加大屏媒体查询（`@media (min-width: 2500px)`），修改所有变量值。

### 2. [MODIFY] [map_engine.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/dashboard/map_engine.js)
- 在引擎开头或初始化处增加根据视口宽度动态计算 `mapTextScale` 缩放因子的逻辑。
- 在各图层（`province-labels`, `sites-label`, `sites-focus-label`, `paths-label`, `paths-detail`）声明 `text-size` 时，乘以该缩放因子。

### 3. [MODIFY] [panels.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/dashboard/panels.js)
- 修改 `_updateTrendChart` 方法，使用 `getBoundingClientRect()` 和 `window.devicePixelRatio` 做高清化画布重建。
- 根据 `chartScale` 动态调节线条和文字大小。

---

## 验证计划

### 1. 自动化验证（构建/测试）
- 运行代码检查，确保无 JS 语法错误。

### 2. 模拟器大屏测试与人工确认
- 由于没有真实的物理 85寸 4K 屏幕环境，将使用 Antigravity 中的 `browser_subagent` 在模拟的 `3840x2160` (4K) 视口下运行大屏页面。
- 传入 `?debug=true` 参数，在调试面板中切换不同的布局场景，对大屏各界面的组件表现、字体清晰度、图表清晰度进行全面排查。
- 截取 4K 渲染下的界面效果图，生成 WebP 动画和截图，供人工审核与验证。

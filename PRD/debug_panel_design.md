# 运行态势大屏调试控制台（Debug Panel）设计需求文档

## 1. 建设背景
在网络运行大屏（Dashboard）的弹性自适应布局改造中，为实现不同数据量下的五种布局状态自动缩放与组件弹性展示。由于当前开发环境缺乏真实的 Netbox 运行态数据，为了支持敏捷调试和用户体验体验验证，有必要开发一个前端“调试面板”（Debug Panel），以便一键切换不同的场景数据，验证自适应表现和过渡动画。

## 2. 核心原则
- **对生产无侵入**：调试面板仅在 URL 包含 `?debug=true` 时被激活和加载。常规生产环境不执行且不渲染任何调试代码。
- **KISS 架构**：将调试面板的所有逻辑、样式和 mock 数据独立封装在 `debug_helper.js` 中，主应用仅提供一个简单的接口以供在数据就绪时接收注入。
- **现代化视觉**：采用与大屏风格契合的暗色系玻璃拟物化（Glassmorphism）悬浮框设计，支持一键折叠，操作友好。

## 3. 五种布局状态与 Mock 数据集

| 状态标识 | 名称 | 割接数据量 | 重保数据量 | 视觉呈现重点 |
| :--- | :--- | :--- | :--- | :--- |
| **STATE_FULL** | 1. 标准满屏 | 2 个（标准卡片） | 1 个（横向小卡） | 标准左右三栏，底部展示重保条，各组件比例均衡 |
| **STATE_NO_CUTOVER** | 2. 无割接 | 0 个（空状态卡片） | 1 个（横向小卡） | 割接卡片收缩为 80px，释放右翼空间，显示“网络运行概况”辅助卡片 |
| **STATE_NO_HEAVY** | 3. 有割接，无重保 | 2 个（标准卡片） | 0 个（安静提示） | 底部重保条收缩，高度自动调为 0，大屏底侧间隙缩小，地图高度微调 |
| **STATE_OVERVIEW** | 4. 运行总览 | 0 个（空状态卡片） | 0 个（安静提示） | 割接卡片收缩，底部重保条收缩，右翼大块空间显示“网络运行概况” |
| **STATE_FULL_MAX** | 5. 数据过多 | 9 个（分组滚动） | 6 个（轮播分组） | 右翼割接计划采用紧凑分组滚动展示；底部重保信息采用滚动轮播图 |

---

## 4. 前端组件设计

### 4.1 调试面板 HTML 结构
面板自动注入在 `<body>` 末尾：
```html
<div id="dashboard-debug-panel" class="debug-panel folded">
    <div class="debug-panel-toggle">🔧 调试</div>
    <div class="debug-panel-body">
        <div class="debug-panel-title">布局与数据调试</div>
        <div class="debug-btn-group">
            <button class="debug-btn" data-state="full">1. 标准满屏</button>
            <button class="debug-btn" data-state="no_cutover">2. 无割接计划</button>
            <button class="debug-btn" data-state="no_heavy">3. 无重保任务</button>
            <button class="debug-btn" data-state="overview">4. 运行总览模式</button>
            <button class="debug-btn" data-state="max_data">5. 极限数据模式</button>
        </div>
        <hr class="debug-divider"/>
        <div class="debug-btn-group">
            <button class="debug-btn debug-btn-danger" data-state="realtime">🔌 恢复实时数据</button>
        </div>
    </div>
</div>
```

### 4.2 调试面板 CSS 样式 (融入 `debug_helper.js` 或注入 DOM)
- 悬浮于 `left: 20px; bottom: 50px;` (避开 Ticker，便于操作)。
- 背景：`background: rgba(10, 25, 50, 0.85); backdrop-filter: blur(10px);`
- 边框：`border: 1px solid rgba(0, 210, 255, 0.3);`
- 阴影：`box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5), inset 0 0 10px rgba(0, 210, 255, 0.1);`
- 文字颜色：`color: #e2e8f0;`

---

## 5. 验证计划与测试方法

1. **宿主集成**：在 `dashboard_app.js` 的 `DOMContentLoaded` 中检测 `?debug=true`，若存在则引入调试模块，并暂时阻断正常的轮询刷新。
2. **交互验证**：
   - 依次点击调试面板的 1-5 按钮。
   - 观察右侧面板的布局高度、卡片是否动态折叠/展开、辅助信息卡片是否按需显示/隐藏。
   - 观察底部信息条是否伸缩（高度由 36px 扩充至 80px 再收回为 36px）。
   - 观察割接卡片内的数据是否在不同数量下展现 4 种模板状态。
   - 观察重保信息条内的数据是否在不同数量下展现 4 种模板状态。
3. **断联/恢复测试**：点击“恢复实时数据”按钮，定时器重开，数据流重新由 API接管。

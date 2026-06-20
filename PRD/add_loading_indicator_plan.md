# 故障统计模块增加 Loading 提示实施计划

为故障统计模块在首次加载、切换统计时间、切换页面（Tab）、以及下钻过滤等耗时数据拉取操作时提供更流畅的交互设计，增加全局/局部的 Loading 提示。

## 用户审核

> [!NOTE]
> 1. **全局加载遮罩 (Global Loading Overlay)**：采用 `fixed` 窗口定位、磨砂玻璃背景 (`backdrop-filter`)、并在中央呈现 MDI 旋转图标及提示卡片。适用于全屏级别的数据重绘（首次进入、切换统计时间、切换 Tab 页面、切换省份过滤条件）。
> 2. **局部加载状态**：针对物理故障明细、电路/裸纤明细等下钻或排序操作，将原本纯文字的“加载中...”替换为带旋转 Spinner 图标的局部表格行，实现渐进式局部加载，以提供更优质的交互视觉。

## 涉及文件

* **`[MODIFY]` [statistics_dashboard.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html)**：在页面底部或合适结构处注入全局 Loading 遮罩的 HTML 节点。
* **`[MODIFY]` [statistics_dashboard.css](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/css/statistics_dashboard.css)**：添加全局 Loading 遮罩的 CSS 样式，并适配黑暗模式。
* **`[MODIFY]` [statistics_dashboard.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js)**：
  - 增加全局 Loading 控制方法 `showGlobalLoading()` 与 `hideGlobalLoading()`。
  - 在 `loadData()` 和 `loadServiceData()` 请求的开始和结束阶段进行全局 Loading 控制。
  - 优化局部表格加载，将 `loadFaultDetails()`, `loadBranchDetails()`, `loadServiceDetails()`, `setServiceDetailsLoading()` 中的简易文本替换为带 MDI 旋转图标的 HTML。

---

## 详细变更方案

### 1. 样式与样式表 (CSS)
在 [statistics_dashboard.css](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/css/statistics_dashboard.css) 尾部追加以下样式：

```css
/* 全局加载遮罩 */
.statistics-global-loading {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background-color: rgba(244, 246, 250, 0.6); /* 适配亮色主题背景 */
    z-index: 9999;
    display: flex;
    justify-content: center;
    align-items: center;
    backdrop-filter: blur(3px); /* 现代毛玻璃效果 */
    transition: opacity 0.15s ease-in-out;
    opacity: 0;
}

[data-bs-theme="dark"] .statistics-global-loading {
    background-color: rgba(21, 25, 34, 0.6); /* 适配暗色主题背景 */
}

.statistics-loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background-color: var(--statistics-surface, #ffffff);
    padding: 2rem 3rem;
    border-radius: 8px;
    box-shadow: var(--statistics-card-shadow, 0 10px 24px rgba(0, 0, 0, 0.1));
    border: 1px solid var(--statistics-border, #d9dee7);
}

.statistics-loading-content .loading-text {
    color: var(--statistics-text, #182433);
    font-size: 1rem;
    margin-top: 1rem;
}
```

### 2. 结构 (HTML)
在 [statistics_dashboard.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html) 文件的适当位置（例如最下方的模态弹窗后，闭合 `{% endblock %}` 标签前）注入：

```html
<!-- 全局加载遮罩 -->
<div id="statistics-global-loading" class="statistics-global-loading d-none">
    <div class="statistics-loading-content">
        <i class="mdi mdi-loading mdi-spin text-primary" style="font-size: 3rem; display: inline-block;"></i>
        <div class="loading-text fw-semibold">数据加载中，请稍候...</div>
    </div>
</div>
```

### 3. 逻辑控制 (JS)
在 [statistics_dashboard.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js) 中进行如下重构：

#### 3.1 控制方法声明
在 `document.addEventListener("DOMContentLoaded", function() {` 作用域内声明控制函数：

```javascript
    function showGlobalLoading() {
        const loading = document.getElementById('statistics-global-loading');
        if (loading) {
            loading.classList.remove('d-none');
            // 触发重绘
            void loading.offsetWidth;
            loading.style.opacity = '1';
        }
    }

    function hideGlobalLoading() {
        const loading = document.getElementById('statistics-global-loading');
        if (loading) {
            loading.style.opacity = '0';
            setTimeout(() => {
                loading.classList.add('d-none');
            }, 150);
        }
    }
```

#### 3.2 耗时操作关联 (调用 `showGlobalLoading` 与 `hideGlobalLoading`)
* **修改 `loadData()`**
  在 `try` 块的 API 请求发起前调用 `showGlobalLoading()`，并在 `finally` 或 `try/catch` 结构中确保 `hideGlobalLoading()` 被触发。

* **修改 `loadServiceData()`**
  在 API 请求发起前调用 `showGlobalLoading()`，并在请求返回或出错后确保 `hideGlobalLoading()` 被触发。

#### 3.3 局部加载 Spinner 化
* **修改 `loadFaultDetails()`**
  将 `tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4">加载中...</td></tr>';`
  替换为：
  `tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted py-4"><i class="mdi mdi-loading mdi-spin me-1"></i> 数据加载中...</td></tr>';`

* **修改 `loadBranchDetails()`**
  将 `tbody.innerHTML = '<tr><td colspan="11" class="text-center py-4">加载中...</td></tr>';`
  替换为：
  `tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted py-4"><i class="mdi mdi-loading mdi-spin me-1"></i> 数据加载中...</td></tr>';`

* **修改 `loadServiceDetails()`**
  将 `tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4">加载中...</td></tr>';`
  替换为：
  `tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4"><i class="mdi mdi-loading mdi-spin me-1"></i> 数据加载中...</td></tr>';`

* **修改 `setServiceDetailsLoading()`**
  将 `tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">数据加载中...</td></tr>';`
  替换为：
  `tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4"><i class="mdi mdi-loading mdi-spin me-1"></i> 数据加载中...</td></tr>';`

---

## 验证计划

### 手动验证步骤
1. **首次进入**：刷新页面，验证有无出现居中的磨砂玻璃加载遮罩，并在数据加载完成后消失。
2. **切换统计时间**：点击上一周期、下一周期、修改日期选择或切换统计粒度（年、月、周等），验证加载遮罩是否正常显隐。
3. **切换页面 (Tab)**：切换物理故障、子公司、电路/裸纤等 Tab 页，确认加载遮罩是否在每次页面重绘时展示。
4. **下钻与耗时操作**：点击任意物理卡片（如“I类和II类”或“光缆中断总起数”），验证下方的明细表格是否展示带旋转 Spinner 图标的局部加载提示。
5. **暗黑模式兼容**：切换系统为暗黑模式，验证全局 Loading 遮罩及提示框 of 颜色是否正确适配且无刺眼强光。

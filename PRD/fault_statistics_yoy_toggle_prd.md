# 故障统计模块 - 增加同比选项需求与设计文档 (PRD)

## 1. 需求背景与目标
当前故障统计模块在展示各指标对比趋势时，同时并排显示了“环比”和“同比”的数据。但在某些日常分析场景下，用户希望界面更加简洁，主要关注环比数据；或者在特定的年终汇报时，才需要同时关注同比数据。

为了提升用户体验并简化默认界面，需要增加一个“显示同比”选项：
1. 该选项默认处于**关闭**状态。
2. 放置在右上角设置工具条的最左侧。
3. 关闭状态下，各项统计指标隐藏所有同比（YoY）相关的对比内容。
4. 开启状态下，显示原有的同比内容。

---

## 2. 界面设计要求
### 2.1 控件位置与样式
- **位置**：右上角设置工具条（`filter-controls`）的最左侧。
- **控件类型**：Bootstrap 5 形式的 Switch 开关（`.form-check.form-switch`）。
- **文字说明**：开关右侧显示“显示同比”文本标签。
- **默认状态**：未勾选（即关闭状态）。

---

## 3. 功能交互与实现逻辑
### 3.1 数据加载与性能要求
- 后端 API 依然正常返回同比和环比数据，不作修改，以避免产生额外的网络请求开销。
- 前端在首次拉取数据或切换时间筛选时，在内存中将后端返回的所有 KPI 指标、分类指标、汇总数据进行全局变量缓存。
- 当用户手动切换“显示同比”开关时，前端直接利用内存中缓存的数据，重新渲染各统计指标组件，实现**毫秒级无感知切换**。

### 3.2 不同统计粒度下的展示逻辑
1. **非“按年”统计（如按半年/季度/月/周）**：
   - **开关关闭**：在指标下方/行内，仅展示“环比 +/-X.X%”。
   - **开关开启**：展示“环比 +/-X.X% 同比 +/-Y.Y%”。
2. **“按年”统计**：
   - **开关关闭**：不展示任何趋势指标（隐藏“较去年”）。
   - **开关开启**：展示“较去年 +/-X.X%”。

---

## 4. 拟改动文件与伪代码

### 4.1 模板改动
文件：`netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`
在 `filter-controls` 容器最左侧注入：
```html
<label class="form-check form-switch mb-0 me-2" id="statistics-yoy-toggle-container">
    <input class="form-check-input" type="checkbox" id="statistics-yoy-toggle">
    <span class="form-check-label text-muted small text-nowrap">显示同比</span>
</label>
```

### 4.2 交互逻辑改动
文件：`netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
- 声明以下全局缓存变量：
  ```javascript
  let currentKPIs = null;
  let currentPrevKPIs = null;
  let currentYoyKPIs = null;
  let currentImpactLevelSummary = null;
  let currentPrevImpactLevelSummary = null;
  let currentYoyImpactLevelSummary = null;
  let currentOtherOverview = null;
  let currentPrevOtherOverview = null;
  let currentYoyOtherOverview = null;
  let currentPrevChartsData = null;
  let currentYoyChartsData = null;
  ```
- 在数据获取（`loadData()`）成功后更新上述全局缓存变量。
- 给开关 `#statistics-yoy-toggle` 绑定 `change` 监听器，并在其触发时调用 `reRenderAllMetrics()` 重新渲染前端各组件：
  ```javascript
  function reRenderAllMetrics() {
      // 重新执行渲染函数更新文本
  }
  ```
- 在趋势 HTML 渲染辅助方法 `buildComparisonTrendHtml` 中，读取 `#statistics-yoy-toggle` 的勾选状态，若未勾选则过滤/隐藏同比数据。

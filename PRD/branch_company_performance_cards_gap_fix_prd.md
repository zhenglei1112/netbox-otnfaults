# 子公司绩效卡片间空白消除需求与设计文档 (PRD)

此文档针对子公司绩效卡片在不同屏幕宽度下列宽增加时，因为限制了最大卡片宽度而导致卡片之间出现多余空白的问题进行修复。通过解除该卡片的最大宽度限制，使其能够自适应填满网格单元。

## 1. 背景与问题描述
子公司绩效卡片在不同屏幕分辨率下支持自适应列数：
- 大屏下默认展示 6 列。
- 中屏及以下展示 3 列或 2 列。

在大卡片上，为了复用裸纤业务卡片的精美样式，我们添加了原生的 `.service-strip-card` 类。
然而，`.service-strip-card` 类（位于 `statistics_dashboard.css` 的 541 行左右）拥有全局的 `max-width: 22.5rem;`（即 360px）限制。
这导致当页面宽度改变（例如在 3 列排版下，每个网格单元的宽度大于 360px 时），子公司卡片无法横向拉伸撑满整个网格单元，最终在各个卡片之间或右侧产生了极不协调的白色背景空洞（如下图所示）。

## 2. 改进方案与设计
在 `.statistics-branch-performance-card` 的样式定义中，显式重写 `max-width` 属性为 `none !important`：

```css
.statistics-branch-performance-card {
    padding: 0 !important;
    overflow: hidden !important;
    max-width: none !important;
    border-radius: 8px !important;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06) !important;
}
```

这样可以达到以下效果：
1. 覆盖 `.service-strip-card` 原本的 `22.5rem` 的最大宽度限制。
2. 允许卡片随着其所在的 CSS Grid 网格单元（`.statistics-branch-performance-grid` 中的 `grid-template-columns: repeat(3, minmax(0, 1fr))` 等）自由拉伸。
3. 卡片之间仅保留网格自身定义的 `gap` 间距（`0.75rem` 或 `1rem`），卡片间不会出现巨大的白色无用空白，排版视觉体验大幅提升。

## 3. 影响范围与回归测试
- **影响代码**：`statistics_dashboard.css`
- **影响范围**：子公司绩效面板展示页面。裸纤业务卡片原本就是自适应或受各自容器包裹，不受本修改影响。
- **回归要求**：
  1. 验证在 6 列大屏展示下，子公司绩效卡片紧凑排列且无溢出；
  2. 验证在中屏 3 列展示下，子公司绩效卡片自动填满网格单元，消除卡片之间的不规则空白。

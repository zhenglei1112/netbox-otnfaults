# 重保通告栏居中与播控状态指示器动态避让需求设计

## 1. 需求背景
在大屏页面中，重保通告栏（`#heavy-duty-bar`）已被移至中央地图演播区（`#map-stage`）的顶部。
由于中央地图上原先悬浮着“播控状态指示器”（`#directing-indicator`），这导致在有重保活动时，重保通告栏与播控状态指示器在纵向上发生了物理重叠。
此外，重保通告栏的内容（即具体重保事件卡片）应当居中显示以提升值班大屏的整体美学效果。

## 2. 详细设计

### 2.1 重保内容居中
- **目标元素**：`.heavy-duty-bar-content`
- **样式改动**：添加 `justify-content: center;`。
- **效果**：使重保卡片（无论是单张卡片、列表还是多张时的走马灯轮播）在整个横向通告栏中保持水平居中。

### 2.2 播控指示器动态避让
因为重保通告栏的高度是固定的（标准屏下约 `32px`，85寸4K大屏下约 `64px`），因此播控指示器 `#directing-indicator`（采用 `position: absolute`）在有重保和无重保时的 `top` 偏移量应该动态改变：
1. **常规屏幕**
   - **默认状态（有重保）**：`top` 设置为 `50px`（`32px` 重保条高度 + `18px` 留白）。
   - **无重保状态**（Body 存在 `.layout-no-heavy` 或 `.layout-overview` 类）：`top` 恢复为原先的 `12px`。
2. **85寸 4K 大屏**
   - **默认状态（有重保）**：`top` 放大为 `90px`（`64px` 重保条高度 + `26px` 留白）。
   - **无重保状态**（Body 存在 `.layout-no-heavy` 或 `.layout-overview` 类）：`top` 恢复为 `24px`。

为提升视觉连贯性，在 `#directing-indicator` 上增加 `transition: top 0.4s ease;` 动画，使得在有无重保状态切换时，播控指示器能够平滑地上下滑动避让。

## 3. 修改文件
- `netbox_otnfaults/static/netbox_otnfaults/css/dashboard.css`

# 修复方案：态势大屏站点图标在故障聚焦后消失

## 问题描述

态势大屏中，当播控引擎自动聚焦到某个故障后，站点图标（圆点 + 标签）有时会消失。

## 环境信息

- MapLibre GL: **v5.4.0**（本地 vendor 文件）
- 页面：`dashboard.html`
- 核心模块：`map_engine.js`、`directing_engine.js`、`dashboard_app.js`

## 根因分析

经代码审查，确认 **3 个可修复的根因** 和 **1 个可优化项**。

---

## 修复任务

### 任务 1：修复 `_applyRegularSiteLabelFilter` 排除过滤器仅作用于标签层

**文件**：`map_engine.js`

**问题**：`focusFaultSites` 调用时，`_applyRegularSiteLabelFilter` 对 `sites-label` 图层设置了排除过滤器，但 `sites-glow` 和 `sites-core` 图层没有同步排除。这导致聚焦站点在常规层和聚焦层中**双重渲染**圆点，视觉上看起来正常但逻辑不一致。

同时，`clearFaultSiteFocus` 恢复时 `setFilter('sites-label', null)` 清除过滤器，但如果此前 `sites-label` 已经因为碰撞检测关闭而处于异常状态，`null` filter 可能无法正确恢复。

**修复**：对 `sites-glow` 和 `sites-core` 也应用排除过滤器，保持聚焦/普通层的完全分离。

```javascript
// 修改 _applyRegularSiteLabelFilter → _applyRegularSiteFilter
function _applyRegularSiteFilter() {
    if (!map) return;

    if (!focusedSiteIds || focusedSiteIds.length === 0) {
        // 清除所有普通站点层的过滤器
        if (map.getLayer('sites-label')) map.setFilter('sites-label', null);
        if (map.getLayer('sites-glow'))  map.setFilter('sites-glow', null);
        if (map.getLayer('sites-core'))  map.setFilter('sites-core', null);
        return;
    }

    // 排除聚焦站点 —— 使用 match 表达式替代 in（更稳定）
    var excludeFilter = ['!', ['in', ['get', 'id'], ['literal', focusedSiteIds]]];
    if (map.getLayer('sites-label')) map.setFilter('sites-label', excludeFilter);
    if (map.getLayer('sites-glow'))  map.setFilter('sites-glow', excludeFilter);
    if (map.getLayer('sites-core'))  map.setFilter('sites-core', excludeFilter);
}
```

---

### 任务 2：减少 `_restackDashboardLayers` 的不必要调用

**文件**：`map_engine.js`

**问题**：`focusFaultSites` 和 `clearFaultSiteFocus` 每次调用都执行 `_restackDashboardLayers()`，对 21 个图层逐一调用 `moveLayer()`。在动画帧(`_startFlowAnimation` 的 RAF)期间执行此操作会导致渲染竞态和短暂闪烁。

**修复**：`focusFaultSites` 和 `clearFaultSiteFocus` 仅修改 filter 和 layout 属性，**不应** 重排图层。图层堆叠顺序只在图层**首次创建**时需要确定。

```javascript
function focusFaultSites(fault) {
    focusedSiteIds = _extractFaultSiteIds(fault);
    _applyFocusedSiteFilter();
    _applyRegularSiteFilter();        // 重命名
    _setRegularSiteLabelCollision(false);
    // 移除 _restackDashboardLayers() 调用
}

function clearFaultSiteFocus() {
    focusedSiteIds = [];
    _applyFocusedSiteFilter();
    _applyRegularSiteFilter();        // 重命名
    _setRegularSiteLabelCollision(true);
    // 移除 _restackDashboardLayers() 调用
}
```

---

### 任务 3：修复 `clearFaultSiteFocus` 与 `flyTo` 动画的竞态

**文件**：`directing_engine.js`、`dashboard_app.js`

**问题**：播控流程如下：
1. `FAULT_ANALYSIS` 超时 → 调用 `onFaultLeave` → `clearFaultSiteFocus()`
2. 同时 → `_setState(GLOBAL_CRUISE)` → `MapEngine.resetView()` → `flyTo()`

`clearFaultSiteFocus()` 中的 filter 修改和 `flyTo` 的摄像机动画在**同一帧或相邻帧**执行，MapLibre 在高速缩放动画中批量处理 filter + paint 属性变更时可能出现一帧空白。

**修复**：将 `clearFaultSiteFocus` 延迟到 `resetView` 的 `flyTo` 启动后的短暂延迟执行，或在 `onFaultLeave` 回调中使用 `requestAnimationFrame` 延迟。

```javascript
// dashboard_app.js - onFaultLeave 回调
onFaultLeave: function (fault) {
    console.log('[Directing] 离开故障:', fault.fault_number);
    Panels.clearFaultFocus();

    // 延迟清除地图聚焦，避免与 flyTo 动画竞态
    requestAnimationFrame(function () {
        MapEngine.clearFaultSiteFocus();
    });

    if (lastData) {
        Panels.updateFaultQueue(lastData.active_faults || [], null);
    }
}
```

---

### 任务 4（优化）：修复 `_applyFocusedSiteFilter` 中空数组 `['literal', []]` 的潜在问题

**文件**：`map_engine.js`

**问题**：`_applyFocusedSiteFilter` 中使用 `['in', ['get', 'id'], ['literal', []]]` 作为空匹配过滤器。在 MapLibre v5 中，`['in', value, ['literal', []]]` 始终返回 `false`（即隐藏所有 feature），这是正确行为。但如果 `focusedSiteIds` 偶尔包含 `undefined` 或 `null`（来自 `_extractFaultSiteIds` 中 `fault.site_z_ids` 包含空值），会导致 `['literal', [undefined]]`，可能产生表达式求值异常。

**修复**：在 `_extractFaultSiteIds` 中增加更严格的过滤。

```javascript
function _extractFaultSiteIds(fault) {
    var ids = [];
    if (!fault) return ids;

    if (fault.site_a_id) ids.push(String(fault.site_a_id));
    (fault.site_z_ids || []).forEach(function (siteId) {
        if (siteId != null && siteId !== '') ids.push(String(siteId));
    });

    // 去重 + 确保全部为字符串
    return ids.filter(function (siteId, index) {
        return typeof siteId === 'string' && siteId.length > 0 && ids.indexOf(siteId) === index;
    });
}
```

---

## 变更摘要

| 任务 | 文件 | 变更类型 | 风险等级 |
|------|------|----------|----------|
| 1 | `map_engine.js` | 扩展排除过滤器到所有站点层 | 🟢 低 |
| 2 | `map_engine.js` | 移除不必要的图层重排 | 🟢 低 |
| 3 | `dashboard_app.js` | 延迟清除聚焦避免竞态 | 🟢 低 |
| 4 | `map_engine.js` | 加强 ID 过滤防御 | 🟢 低 |

## 影响范围

- 仅涉及 **态势大屏**（`dashboard.html`），不影响故障分布图或其他地图模式
- 无后端变更，无数据库迁移
- 所有修改均为 JavaScript 层面的逻辑优化

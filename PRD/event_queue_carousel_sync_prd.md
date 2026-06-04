# 综合事件队列轮播与焦点详情同步需求与设计文档 (PRD)

## 1. 业务需求
在大屏展示中，右翼的“综合事件队列”包含了故障、割接、重保三种事件类型，且已经基于重要程度/紧迫程度完成了混合排序展示。
目前系统存在两个交互硬伤：
1. **自动播控与队列高亮脱节**：自动播控轮播到某个故障时，页面右下角的“焦点详情”展示该故障，但综合事件队列没有将当前播放项设为高亮，导致左侧/右侧高亮状态停留在别处，页面状态脱节。
2. **割接/重保事件没有自动轮播**：原先的播控只获取了 `active_faults` 队列进行轮播。综合事件队列中的割接和重保计划在无人手动干预时无法自动呈现在“焦点详情”里。
3. **轮播方向无序**：轮转顺序不是自上而下顺次进行，导致大屏展示显得杂乱。
4. **手动点击与自动轮播冲突**：手动点击某项后，后台的故障自动轮播并没有重置计时，很快就会被播控切走。

本需求要求对智能播控与事件队列进行重构，实现**以综合事件队列为轴心，自上而下的顺次自动轮播，且高亮、详情、地图全过程实时同步，并允许手动点击精准切入接管。**

---

## 2. 方案与逻辑设计

### 2.1 播控引擎重构为综合事件状态机
修改 `directing_engine.js`，重构为以下逻辑：
1. **数据输入**：将原有只接收故障的 `updateFaultQueue(faults)` 改为接收综合事件队列 `updateEventQueue(events)`。
2. **队列轮询与定位**：
   - 记录 `currentIndex`（当前轮播索引），按 `(currentIndex + 1) % eventQueue.length` 的顺序自上而下依次进行轮播。
   - 当数据更新时，遍历新队列，通过 `key` (如 `fault-1`, `cutover-2`) 重新定位 `currentIndex`，防止轮播状态被打断或归零。
3. **播放行为分流处理**：
   - **故障（`event.type === 'fault'`）**：
     - 执行摄像头飞行定位至故障站点 `MapEngine.focusFaultSites(fault)`。
     - 切换播控状态为 `FAULT_ANALYSIS`，播控指示器显示 `◎ 故障聚焦 · [故障编号]`。
     - 触发 Shockwave 特效与 critical 故障红闪特效。
   - **割接与重保（`event.type === 'cutover'` 或 `'heavy_duty'`）**：
     - 重置地图视角为全国大视图并保持巡航偏转 `MapEngine.resetView()`。
     - 切换播控状态为 `GLOBAL_CRUISE`（自定义状态显示名，如 `割接播控` 或 `重保播控`），指示器显示 `⟳ [类别]播控 · [编号/名称]`。
4. **统一手动聚焦方法**：
   - 暴露 `focusOnEvent(event)` 接口。
   - 用户手动点击综合事件队列中的某一项时，直接向播控引擎发送该事件。
   - 播控引擎接收后立即清空当前切换定时器，设置 `currentIndex` 切换到该项，执行对应的飞行或全国巡航，并在停留完毕后再顺次向后轮播。

### 2.2 UI 状态单向流与联动
为了彻底避免高亮冲突，大屏将采用**单向状态流**：
```
[自动定时器触发 / 手动点击事件项] 
       ↓
[DirectingEngine.focusOnEvent] (播控引擎接管，执行地图动作并更新状态)
       ↓
[onEventFocus(event) 回调触发] (数据分发)
       ↓
├── 1. Panels.highlightEventItem (高亮左侧队列，滑动确保可见)
├── 2. Panels.showEventFocus (更新右下角详情卡片)
└── 3. Effects.triggerShockwave (非故障则重置地图，故障则执行特效)
```

1. **队列项高亮方法**：在 `panels.js` 中开发 `highlightEventItem(eventKey)` 方法，利用 `querySelectorAll` 精准操纵对应 DOM 的 `active` 类，并使用 `scrollIntoView` 保证高亮项处于可视区中。
2. **点击事件重定向**：修改 `panels.js` 中的 `updateEventQueue` 点击逻辑，点击队列项时仅调用 `DirectingEngine.focusOnEvent(event)`，不再内部修改 DOM 高亮及单独触发 `showEventFocus`。
3. **初次高亮剔除**：移除 `updateEventQueue` 中初次数据渲染时强制高亮第一项的硬编码。

### 2.3 播控状态指示器扩展 (effects.js)
- 修改 `Effects.updateDirectingIndicator(stateInfo)`，当 `stateInfo.event` 存在时，文本框信息优先展示为：
  `stateInfo.name + ' · ' + stateInfo.event.title`

---

## 3. 修改文件清单
- `netbox_otnfaults/static/netbox_otnfaults/js/dashboard/directing_engine.js` (播控机核心重构)
- `netbox_otnfaults/static/netbox_otnfaults/js/dashboard/panels.js` (综合事件高亮及点击处理逻辑)
- `netbox_otnfaults/static/netbox_otnfaults/js/dashboard/dashboard_app.js` (统一回调驱动与单向流注入)
- `netbox_otnfaults/static/netbox_otnfaults/js/dashboard/effects.js` (播控指示器大屏文本适配)

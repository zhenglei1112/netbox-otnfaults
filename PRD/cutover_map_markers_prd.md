# 地图渲染割接标记需求与设计文档 (PRD)

## 1. 业务背景
在大屏演播地图上，目前能够通过常驻层展现站点拓扑，并在发生故障时显示闪烁红色告警圈与飞越特效。
割接（Cutover）计划对网络运行同样有重要影响，值班大屏需要直观反映今日或近期即将实施的割接项目。
本需求要求：**在大屏地图上渲染割接任务所在的站点，设计一套符合大屏科技风的黄色发光扳手图标标识。**

---

## 2. 详细设计

### 2.1 经纬度位置动态定位
后端 `cutovers` 列表中目前不包含直接的 `lat`/`lng` 经纬度属性，但包含了割接的 `site_a` 字段。
- 逻辑：前端在渲染割接时，遍历割接数组。若当前项含有 `lat` 属性，则直接读取；
- 否则，通过其 `site_a` 名字，在已加载的站点列表 `data.sites` 中通过 `find` 匹配对应站点的 `lat` 和 `lng` 坐标。
- 若匹配失败，则在地图上忽略此割接任务的呈现。

### 2.2 黄色发光与扳手 WebGL 图层配置
采用三层 WebGL 嵌套图层实现高性能渲染：
1. **`cutovers-glow`**：黄色圆型光晕层。`circle-color: '#F59E0B'`，半径 `16`，模糊度 `1.2`，不透明度 `0.18`。
2. **`cutovers-core`**：亮点圆芯层。`circle-color: '#F59E0B'`，半径 `6`，白色细描边提高反差。
3. **`cutovers-icon`**：扳手标志图层。`text-field: '🔧'`（直接渲染 Emoji / 扳手字符）。
   - 适配大屏缩放系数：`text-size: 12 * mapTextScale`。
   - 科技发光渲染：`text-halo-color: 'rgba(245, 158, 11, 0.45)'`，发光厚度 `3`，模拟荧光发光罩。

### 2.3 图层层叠顺序 (Layer Stack)
新图层插在大屏地图图层栈 `DASHBOARD_LAYER_STACK` 中，位于 `paths-detail` 与 `faults-pulse` 之间：
```javascript
'paths-detail',
'cutovers-glow',
'cutovers-core',
'cutovers-icon',
'faults-pulse',
...
```

---

## 3. 修改文件
- `netbox_otnfaults/static/netbox_otnfaults/js/dashboard/map_engine.js`
- `netbox_otnfaults/static/netbox_otnfaults/js/dashboard/dashboard_app.js`

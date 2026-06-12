# 路径元数据非全量加载性能优化方案

目前系统在初始化一张图时，会通过 `/api/plugins/otnfaults/paths/?limit=0` 全量拉取所有的路径元数据。由于路径中包含了详细的空间地理坐标数组（`geometry` 字段），在大数据量下（数十甚至数百条精细光缆路径），这会导致：
1. **网络传输瓶颈**：一次性下载数 MB 甚至十数 MB 的 JSON 数据。
2. **CPU 计算阻塞**：前端在页面刚加载时，需要使用海格辛公式对全量路径的几何点进行循环计算以补全长度，造成浏览器短暂卡顿。
3. **交互卡顿**：点击 TOP5 故障路径时，如果元数据 Promise 尚未解决，会产生明显的二次异步等待。

本方案旨在将**路径属性**（用于搜索、统计和关联）与**空间几何**（用于地图渲染、定位和高亮）进行**动静分离**与**按需拉取**，从而解决上述瓶颈。

---

## 方案设计

### 1. 后端：提供轻量级路径接口
* 新增自定义 API 端点 `/api/plugins/otnfaults/paths/lightweight/`。
* 仅查询和序列化必要字段（如 `id`、`name`、`site_a`、`site_z`、`calculated_length` 等），**排除了体积巨大的 `geometry` 地理坐标字段**。
* 使用 Django 的 `.only(...)` 查询优化，减少数据库读取开销。

### 2. 前端初始化：加载轻量元数据
* 页面首次加载时，改为调用轻量级接口获取路径属性，存入缓存 `window.OTNPathsMetadata`。
* 这样，全局搜索（模糊匹配路径）、故障统计（生成 TOP5 路径名列表）依然能瞬时完成，且免去了对全量路径进行 Haversine 几何距离计算的 CPU 开销。

### 3. 前端交互：按需拉取空间几何 (Lazy Loading & Cache)
* 当用户执行以下交互时：
  - **点击 TOP5 故障路径**进行漫游定位。
  - **鼠标悬停割接点**进行联动高亮关联路径与流光。
* 此时根据关联的路径 ID，检查本地缓存中该路径是否已经下载了 `geometry` 坐标：
  - **若已存在**：直接开始缩放与高亮。
  - **若不存在**：通过批量接口 `/api/plugins/otnfaults/paths/?id=xx&id=yy` 异步拉取这几条路径的完整几何坐标，更新回 `window.OTNPathsMetadata` 缓存，再执行缩放与高亮。

---

## 变更文件明细

### 后端层

#### [views.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/api/views.py)
* 新增 `lightweight_paths_view` 视图，只吐出除 `geometry` 外的基本路径元数据。

#### [urls.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/api/urls.py)
* 注册轻量级路径 API 路由 `/api/plugins/netbox_otnfaults/paths/lightweight/`。

---

### 前端层

#### [api.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/utils/api.js)
* 修改 `OTNFaultMapAPI`，新增以下方法：
  - `fetchLightweightPaths()`：获取不带 `geometry` 的轻量级路径属性。
  - `fetchPathsGeometry(pathIds)`：根据 ID 列表批量拉取包含 `geometry` 空间坐标的完整路径数据。

#### [fault_mode.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/modes/fault_mode.js)
* 修改 `_loadPathMetadata()`：将 API 请求替换为 `fetchLightweightPaths` 轻量加载，并直接解决 Promise，不进行海格辛距离计算。
* 在 `window.faultMapPlugin` 上提供公共的方法 `ensurePathsGeometry(pathIds)`，用来批量补全指定路径的 geometry 坐标并存入缓存。
* **全局变量绑定**：在 `init(core)` 中增加 `window.faultMapPlugin = this;`。这确保了外部控制面板可以访问到地图交互插件实例的补拉接口。
* 将鼠标悬停割接点事件处理器及相关联函数（如 `_showCutoverPopup`、`_highlightCutoverImpacts`）改为 `async/await`，在启动流光前，先调用 `ensurePathsGeometry` 确保关联的几何数据已拉取。同时对要高亮的路径特征列表增加 `geometry.coordinates` 存在性过滤，防止地图渲染出错。

#### [FaultStatisticsControl.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/controls/FaultStatisticsControl.js)
* 修改 `flyToPath(pathName)` 方法：
  - 在解析出匹配的路径 ID 后，若其在缓存中缺失 `geometry` 数据，通过 `await window.faultMapPlugin.ensurePathsGeometry([id])` 进行补充，加载完毕后再执行地图的飞行动画及高亮渲染。
* **防御性过滤**：对计算定位外接边界框（`bounds`）的循环过程，以及装填高亮图层的数据结构 `highlightData`，对 `geometry` 及其 `coordinates` 属性进行非空校验，屏蔽潜在的接口空值错误（`TypeError`）。

---

## 验证计划

### 自动化验证
* 在测试环境中执行 Django 单元测试，确保轻量级接口 `/api/plugins/otnfaults/paths/lightweight/` 状态码正常，返回的数据结构正确且不含 `geometry` 键值。
* 执行 `python -m py_compile` 静态语法检查。

### 手动验证
1. 打开“一张图”页面，通过浏览器开发者工具网络面板（Network）检查页面首次加载拉取的 `/lightweight/` 接口大小。
2. 验证搜索框模糊搜索路径、故障统计面板中的 Top5 路径能够正常展示，且加载时间相比优化前有质的提升。
3. 点击 Top5 路径中的某一条，验证是否在 Network 面板能捕获到按需发起的路径 geometry 获取请求。
4. 确认定位、高亮流光和弹窗显示一切功能正常。

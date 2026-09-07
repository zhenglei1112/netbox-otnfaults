# blueglobe.js 深度技术研究

研究日期：2026-08-30  
面向：NetBox OTN 态势大屏 V2 技术决策

## 结论先行

`blueglobe.js` 不是一个通用“地图框架”，而是一套针对卫星实时可视化垂直优化的专用引擎：用 **TWGL + 原生 WebGL** 掌控渲染，用 **satellite.js/SGP4** 计算轨道，用独立 Worker 隔离计算负载，再通过插值让画面持续平滑。其炫酷效果来自整套专用渲染管线、镜头语言、动态光照和数据组织，而不是某个可以直接替换 MapLibre 的单一库。[官方介绍](https://docs.satellitemap.space/intro/)明确说明它不使用 Cesium、Three.js 等重型引擎；[官方 credits](https://satellitemap.space/info/credits)则确认底层图形辅助库是 TWGL.js。

对当前 OTN 大屏，**不建议直接接入 blueglobe.js**：它不是开源库、不能自托管或离线运行、运行时强依赖对方的 API 和素材服务，而且商业使用需要事先协商。更合适的路线是保留当前 MapLibre/GeoJSON/PMTiles 架构，借鉴它的计算与渲染分层，并用 MapLibre Custom Layer + TWGL（或 deck.gl）实现站点光效、路径流光、故障脉冲和镜头过渡。

## 1. 它到底是什么

从产品形态看，BlueGlobe 是一个传入 `<canvas>` 后自行接管渲染、交互、相机、时钟和数据加载的 ES module。公开 API 暴露了卫星装载、轨道/覆盖区、三种相机模式、时间倍率、视觉层、事件、过境计算和性能控制等能力，说明它实际上是一个“小型领域引擎”，而非单纯的地球组件。[公开 API 参考](https://docs.satellitemap.space/llms.txt)

它的职责边界大致为：

```text
Astro 页面 / SPA UI
        │  BlueGlobe API + events
        ▼
BlueGlobe 主线程控制器
  ├─ 相机、输入、时钟、状态机
  ├─ 资源管理：纹理、模型、瓦片、星表
  ├─ 渲染管线：地球、天空、对象、轨迹、标签、特效
  └─ Picking / UI 事件
        │ postMessage
        ▼
Calculation Worker
  ├─ TLE 解析与 SGP4/SDP4 传播
  ├─ 坐标转换与可见性/过境相关计算
  └─ 批量返回位置状态
        │
        ▼
satellitemap.space API / 资产服务
  ├─ 卫星 TLE 与元数据
  ├─ 地球纹理、云、星表和 GLB/glTF 模型
  └─ 地图/地形瓦片
```

其中“独立 Calculation Worker”是基于 2026-08-30 公开构建产物的直接观察：`blueglobe.js` 引用了可公开访问的 `calculation-worker.js`，后者包含消息收发、satellite.js、SGP4 和传播计算特征。这说明轨道计算与主渲染线程至少在一个主要路径上已经分离；精确消息结构与调度策略未公开。

## 2. 前端和服务端技术栈

### 2.1 图形层：原生 WebGL + TWGL

[TWGL 官方说明](https://twgljs.org/)把自己定义为让 WebGL API 更简洁的薄辅助层：它帮助创建 program、buffer、texture、uniform 和 draw call，但不替开发者管理场景图、材质系统或 GLSL。换句话说，BlueGlobe 的球体网格、shader、相机、深度/混合状态、拾取、标签和资源生命周期基本都需要自己设计。

这也是它能够形成鲜明视觉风格的原因：

- 不受通用引擎材质和场景图约束，可以围绕卫星点、轨迹线、地球和天空做极窄的优化。
- 可以精确安排透明层、深度测试、混合模式、光晕和后处理。
- 代价是维护成本高，浏览器兼容、GPU 状态泄漏、资源释放和 shader 变体都由项目自己承担。

官方要求最低 WebGL 1，并强烈推荐 WebGL 2。WebGL 2 才启用实例化标签、卫星轨迹、罗盘标签和星表渲染；同时要求创建带深度缓冲的 context。[安装与能力矩阵](https://docs.satellitemap.space/getting-started/installation/)

### 2.2 页面层：Astro + Vite

官方说明首页是围绕 BlueGlobe 构建的 SPA，而卫星详情、星座等 Astro 页面会以 compact mode 嵌入引擎；credits 同时列出 Astro 和 Vite。[官方介绍](https://docs.satellitemap.space/intro/) [技术栈 credits](https://satellitemap.space/info/credits)

合理的职责划分是：

- Astro 负责内容页、路由、SEO 和初始 HTML。
- 首页进入后由客户端 UI 控制 BlueGlobe，形成高交互 SPA。
- Vite 负责 ES module 构建与资产打包。

这里前两点有官方依据；更细的组件树和状态管理方案未公开。

### 2.3 服务层：OpenResty + Node.js/Express

credits 列出 OpenResty、Node.js 和 Express；公开资源响应头也显示 OpenResty。较可信的部署形态是 OpenResty/Nginx 位于边缘层，负责 TLS、静态文件、缓存、CORS 白名单和限流，Node/Express 提供业务 API。具体反向代理拓扑和数据库不可从公开资料确认。[官方 credits](https://satellitemap.space/info/credits)

## 3. 坐标、轨道与时间系统

### 3.1 轨道数据链

卫星的基础数据来自 Space-Track，CelesTrak 用作补充来源；TLE/OMM 经过 satellite.js 的 SGP4/SDP4 传播得到 ECI 坐标，再根据恒星时转换为 ECF/地理坐标。satellite.js 官方示例明确展示了 `twoline2satrec → sgp4/propagate → ECI → ECF/geodetic/look angles` 的标准链路。[satellite.js 官方仓库](https://github.com/shashwatak/satellite-js)

BlueGlobe 官方还披露：

- 使用 64 位 SGP4 结果计算卫星位置。
- 将位置连续转换为 XYZ，并用插值启发式降低 CPU 开销。
- 相比 WebGPU 上的 32 位 SGP4，更看重 64 位精度与兼容性。
- 短间隔使用球面线性插值，较长间隔可使用 Hermite 插值。
- 非地球轨道目标使用 JPL 数据及插值。

这些信息来自[官方精度说明](https://satellitemap.space/info/accuracy)。它揭示了一个关键设计：**物理计算时钟不等于渲染帧时钟**。SGP4 提供若干高精度锚点，60/120fps 的画面位置在锚点之间连续求值，从而避免对两万多个对象每帧执行完整传播。

### 3.2 地球不是简单单位球

官方说明地面视角使用地球椭球体，地形会抬升观察相机，地平线也按曲率正确显示；太阳向量驱动地球与月球明暗，星空和天体使用独立天文计算。[官方精度说明](https://satellitemap.space/info/accuracy)

因此它的“真实感”不只是贴一张 Blue Marble：相机坐标、太阳光照、天空参考系、地形高度和时间系统必须保持一致。对于 OTN 全国大屏，这些天文学精度没有业务价值，不应照搬其复杂度。

## 4. 推测的渲染管线

以下是由公开能力、WebGL 要求和构建特征推导出的高概率管线，**不是官方公开的源码结构**：

1. 天空/星表 pass：绘制银河纹理或星表点，按恒星参考系旋转。
2. 地球不透明 pass：球体/椭球体、日夜纹理、边界与地图瓦片。
3. 大气和云层 pass：深度测试下的透明混合与边缘光。
4. 轨道、地面轨迹和覆盖区 pass：线带、扇形或透明 footprint。
5. 卫星点/模型 pass：大量对象批量绘制，重点对象切换 GLB/glTF 模型。
6. 标签与罗盘 pass：WebGL2 下使用实例化绘制控制 draw call。
7. 选择/交互 pass：很可能将对象 ID 写入离屏 framebuffer，再用 `readPixels` 完成拾取；公开构建确有 framebuffer 与 readPixels 路径，但是否所有对象都采用此法未知。

公开构建中还可观察到 instanced draw、vertex divisor、framebuffer、readPixels、OffscreenCanvas、纹理和 TWGL program/buffer 等特征，支持上述判断，但不能据此断言具体 shader 和每个 pass 的准确顺序。

## 5. 它如何维持流畅

BlueGlobe 的性能策略不是单点优化，而是分层控制：

| 层级 | 已确认做法 | 作用 |
|---|---|---|
| 计算 | 64 位 SGP4 + 帧间插值 | 降低每帧传播成本，同时保持精度 |
| 并发 | 独立 calculation Worker | 避免轨道计算阻塞输入和绘制 |
| GPU | WebGL2 实例化标签与轨迹能力 | 减少大量对象的 draw call 与状态切换 |
| 显示 | `maxLabels`、标签密度优化 | 控制最昂贵且最易遮挡的文字层 |
| 帧率 | 60/30/15fps API，站点还提供 120fps 选项 | 按设备能力降级 |
| 空闲 | pause/resume CPU、暂停和无交互时 CPU saver | 大屏隐藏或静止时避免空转 |
| 资源 | 地形/地图 LOD、按需模型与瓦片 | 控制网络、显存和几何量 |
| 兼容 | WebGL1 fallback | 牺牲轨迹/地面视图等高级特性换覆盖面 |

帧率和 CPU 控制可从[公开 API](https://docs.satellitemap.space/llms.txt)确认；WebGL 分级来自[安装文档](https://docs.satellitemap.space/getting-started/installation/)；LOD、CPU saver 和慢设备优化记录在[站点更新与说明](https://satellitemap.space/info/credits)。

## 6. API 设计透露的内部状态机

公开方法不是零散工具，而是暴露了清晰的领域边界：

- 数据域：按 NORAD、星座、类型和 selector 装载对象。
- 场景域：轨道、覆盖区、波束、卫星列车、云、边界、天空和色彩过滤。
- 相机域：轨道视角、地面 standing、卫星 riding/POV、AR 与平滑镜头。
- 时间域：暂停、倍率、历史时刻、日出日落和太阳高度。
- 交互域：pick、cameraUpdate、loading、FOV 与 longpress 事件。
- 生命周期域：初始化、状态保存/恢复、CPU 暂停和帧率切换。

这意味着 BlueGlobe 不是“每个页面自己操作 WebGL”，而是由一个中央控制器维护场景状态，并通过命令式方法和事件与 UI 解耦。这一 API 组织方式很适合 OTN V2 借鉴。

## 7. 为什么它看起来比普通地图更“炫”

视觉差异主要来自六项组合：

1. 深色空间背景与地球边缘形成非常强的明暗层级。
2. 太阳驱动的日夜面、云层和大气边缘光提供体积感。
3. 大量运动点与细轨迹形成持续、但方向明确的动态纹理。
4. 相机不是简单平移缩放，而是在轨道、地面、追踪和 POV 状态间切换。
5. 标签受密度和优先级约束，不会把整个画布铺满文字。
6. 数据、时钟、镜头与光照共享同一坐标和时间基准，因此运动没有“贴图动画感”。

所以复刻其效果的正确问题不是“换成哪个地图框架”，而是“是否建立统一场景状态、GPU 图层、动画时钟与镜头系统”。

## 8. 授权与工程可用性

BlueGlobe 本身不开源；插件从 satellitemap.space 直接加载，依赖其卫星 API、纹理、模型和瓦片，不提供离线或自托管模式。域名还需加入 CORS 白名单。官方只允许非商业教育用途，商业集成要事先协商，个人 dashboard 目前也未开放。[托管与授权说明](https://docs.satellitemap.space/intro/) [CORS 要求](https://docs.satellitemap.space/getting-started/installation/)

这对 NetBox 插件有四个直接风险：

- 内网或离线部署不可用。
- 外部服务中断、接口变化或白名单调整会直接影响大屏。
- 数据和视觉资产存在外部依赖，不满足完全可控部署。
- 商业/企业内部应用的授权状态不明确，不能默认可用。

结论是：除非取得明确商业授权并接受在线依赖，否则不应把它作为生产依赖；也不应复制其专有 bundle。可以合法借鉴公开的架构思想，并使用各自许可清晰的 TWGL、MapLibre、deck.gl 等组件重新实现 OTN 领域效果。

## 9. 对 OTN 态势大屏 V2 的可迁移设计

### 推荐方案：MapLibre 保持地理底座，TWGL Custom Layer 提供专用特效

当前 V2 已有省界、站点和路径，地理范围是中国平面态势图，不需要卫星级三维轨道与天文系统。建议架构如下：

```text
Django / GraphQL 或现有数据接口
          │ 站点、路径、告警快照
          ▼
Dashboard Scene Store
  ├─ 业务状态：正常/告警/中断/恢复
  ├─ 视图状态：中心点、zoom、pitch、bearing
  └─ 动画状态：路径相位、脉冲、过渡时间
          │
    ┌─────┴─────────┐
    ▼               ▼
MapLibre 图层       TWGL Custom Layer
省界/底图/文字       站点光晕/路径流光/故障脉冲
    └─────共享同一相机矩阵─────┘
```

### BlueGlobe 能力到 OTN 的映射

| BlueGlobe 思想 | OTN V2 对应实现 |
|---|---|
| 卫星实例化点 | 站点 GPU 实例化图标/光点 |
| 轨道与 trail | 光缆/业务路径的方向流光 |
| 计算时钟与渲染时钟分离 | 后端数据低频刷新，前端 60fps 插值与相位动画 |
| 自动标签密度 | 按 zoom、故障级别、选择状态决定标签优先级 |
| focus/track/POV 状态机 | 全国、区域、故障定位、路径巡航镜头模式 |
| Color filter / legend | 按状态、专业、等级、承载业务着色 |
| CPU saver | 页面隐藏、无动画、数据静止时降低至 15fps 或暂停 |
| save/restore state | URL 参数和 debug 面板保存视野/图层配置 |
| Worker 计算 | 大批路径几何预处理、粒子采样或聚合放入 Worker |

### 为什么优先 TWGL Custom Layer，而不是整页改成三维地球

- 可以复用现有 MapLibre 地理投影、交互、GeoJSON 与省界成果。
- 特效层与业务图层共享相机矩阵，不会出现两个 canvas 对不齐。
- 只为需要高性能的站点/路径写 shader，控制实现范围。
- V1 保持不动，V2 可逐层替换，符合当前渐进重构策略。
- 后续若需要真正的三维全球视图，可新增独立模式，而不迫使全国二维大屏承担地球引擎复杂度。

## 10. 建议的验证顺序

1. 在 V2 增加一个独立的 WebGL2/TWGL 实验层，不改变现有站点和路径数据接口。
2. 首先实现站点实例化：位置、大小、颜色、告警脉冲四个 per-instance 属性。
3. 再实现路径流光：基础线仍由 MapLibre 保底，TWGL 只画动画高光，关闭动画时视觉仍完整。
4. 把 `dataTime` 与 `renderTime` 分开，数据刷新不重建每帧对象，只更新 GPU buffer 的变化部分。
5. 扩展现有 `?debug=true` 面板，增加 FPS、frame time、draw calls、站点数、线段数、GPU 图层开关和动画速度。
6. 用目标大屏硬件验证 1k/10k 站点和不同路径规模，建立 WebGL2 与降级路径。
7. 最后再增加镜头巡航、故障聚焦和氛围光效，避免视觉特效先于性能基线。

## 11. 最终判断

BlueGlobe 最值得借鉴的不是地球模型，而是四条工程原则：

- 用专用 GPU 图层处理高密度动态对象。
- 让业务/物理计算、渲染插值和 UI 交互相互解耦。
- 把相机、时间、图层和选择状态统一放进场景控制器。
- 为低性能设备和静止场景设计明确的降级与停帧机制。

对当前项目，最稳妥且视觉上限较高的技术路线是：**MapLibre 负责地图语义，TWGL 负责 BlueGlobe 风格的专用动态渲染，Django/GraphQL 负责可控的数据供应**。这能保留已有成果，也避开 BlueGlobe 的授权、联网和不可自托管限制。

## 主要来源

- [BlueGlobe.js 官方介绍与授权说明](https://docs.satellitemap.space/intro/)
- [BlueGlobe.js 单页 API 参考](https://docs.satellitemap.space/llms.txt)
- [BlueGlobe.js 安装、WebGL 与 CORS 要求](https://docs.satellitemap.space/getting-started/installation/)
- [SatelliteMap.space 技术栈、数据源与精度说明](https://satellitemap.space/info/credits)
- [TWGL 官方说明](https://twgljs.org/)
- [satellite.js 官方仓库与坐标转换示例](https://github.com/shashwatak/satellite-js)
- [公开 BlueGlobe ES module（仅用于构建元数据核对）](https://satellitemap.space/blueglobe.js)
- [公开 Calculation Worker（仅用于计算分线程特征核对）](https://satellitemap.space/calculation-worker.js)

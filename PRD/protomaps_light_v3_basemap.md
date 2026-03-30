# 切换底图为 Protomaps 官方 Style JSON

## 概述
将底图从 Alidade Smooth 硬编码样式切换为 Protomaps 官方 Style JSON，需要重新生成 PMTiles 瓦片数据。

## 实施阶段

### 第一阶段：运维（服务器端）
1. 使用 `pmtiles extract` 从 Protomaps 全球底图裁剪中国区域
2. 通过 `@protomaps/basemaps` NPM 包生成 light/dark 两套 Style JSON
3. 部署字体、Sprite 图标资源到 Nginx
4. 修改 Style JSON 中的资源路径指向本地服务器

### 第二阶段：代码修改
1. `maplibregl_base.js`：将硬编码样式替换为加载外部 Style JSON URL
2. `map_engine.js`：大屏底图同步更新
3. `test.html`：测试文件同步更新
4. 插件配置和视图：新增 `local_light_style_url` / `local_dark_style_url` 配置项

## 关键风险
- Protomaps 使用不同的 source-layer 名称（`roads`/`boundaries`/`places`），需确保新数据兼容
- 主题切换改为 `setStyle()` 后，业务图层需在 `style.load` 事件后重新挂载

详细方案见 Antigravity 实施计划文档。

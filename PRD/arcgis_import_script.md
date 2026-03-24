# ArcGIS 点服务数据导入 NetBox 站点脚本需求文档

## 1. 需求背景
现有 ArcGIS 中的一个点服务图层（服务地址：`http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN2026/FeatureServer/0`），其中包含站点相关的地理分布数据。为实现网络资源可视化与管理，需编写自定义脚本，将该服务中的点数据自动导入为 NetBox 系统中的站点（Site）对象。

## 2. 功能需求
- **数据获取**：调用 ArcGIS REST API 的 `/query` 接口获取所有点特征数据。
- **字段映射**：
  - 将 ArcGIS 属性 `O_NAME` 填入 NetBox 站点的 `name` 字段；
  - 根据 `name` 自动生成 NetBox 必需的 URL 友好标识符（`slug`）；
  - 将 ArcGIS 点几何数据的 `x` 和 `y`（确保按照 EPSG:4326 返回），分别对应填入 NetBox 站点的 `longitude` 和 `latitude` 字段；
  - 设置站点的默认状态为“操作中（Active）”。
- **操作逻辑**：
  - 如果同名站点在 NetBox 中不存在，则创建新站点。
  - 如果同名站点已存在，则更新其经纬度坐标（如果坐标有变更）。
  - 跳过缺少 `O_NAME` 或坐标数据无效的记录，并在日志中给出警告提示。

## 3. 技术环境
- **NetBox 版本**：4.x 系列
- **脚本实现方式**：作为 NetBox 原生的自定义脚本（`extras.scripts.Script`），可通过 Web UI 触发或 CLI 调用。利用 `requests` 库实现 HTTP 通信。
- **运行要求**：无需复杂的外部认证或额外的库依赖，需提供超时保护和基础的错误处理体系。

## 4. 交付物
- 脚本文件：`scripts/import_arcgis_sites.py`，可以直接部署到 NetBox 的 `SCRIPTS_ROOT` 目录运行。

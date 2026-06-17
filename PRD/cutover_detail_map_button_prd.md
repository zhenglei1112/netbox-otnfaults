# 割接详情页地图按钮无条件展示及位置估算需求文档

本需求旨在解决：在割接详情页面中，即使割接记录没有设置具体的经纬度坐标，依然可以展示“地图”按钮，并基于割接所关联的 A 端和 Z 端站点来进行位置的估算和展示。

## 详细功能设计

- 参照故障详情页（`otnfault.html`）的相同逻辑，割接详情页中“地图”按钮不应该受到“必须有经纬度”的条件约束。
- 移除 `cutovertask.html` 中地图按钮外层的 `{% if object.cutover_longitude and object.cutover_latitude %}` 条件。
- 当用户点击该地图按钮时：
  - 若有割接具体的经纬度，依然将经纬度通过 `q` 参数传给地图视图进行精确点位高亮。
  - 若无经纬度，地图视图（`LocationMapView`）会自动提取 URL 参数中的 `a_site` 和 `z_sites` 中拥有坐标的站点，并计算它们的中心点，作为地图的默认定位中心。

## 拟修改文件列表

- **详情页模板**：[netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html)

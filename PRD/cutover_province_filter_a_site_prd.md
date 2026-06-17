# 割接编辑页面基于省份过滤A端站点需求文档

本需求旨在实现：在割接信息编辑页面中，当用户选择了“省份”时，A 端站点下拉框能够基于所选省份动态联动过滤，仅展现该省份下的站点列表。

## 详细功能设计

- 参照故障编辑表单的相同逻辑，割接管理编辑表单中，`interruption_location_a` 字段应当基于所选的 `province` 进行过滤。
- 实现方式：利用 Netbox 提供的 `DynamicModelChoiceField` 字段的 `query_params` 特性，在 `interruption_location_a` 声明中设置 `query_params = {'region_id': '$province'}`。
- 效果：用户在编辑页面选择省份后，A端站点下拉框的数据在重新拉取时，会自动带上 `region_id` 过滤参数。

## 拟修改文件列表

- **表单定义**：[netbox_otnfaults/forms.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/forms.py)

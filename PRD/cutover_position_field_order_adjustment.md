# 割接位置组字段顺序调整需求文档

本需求旨在调整割接（CutoverTask）模型中“割接位置”字段组的显示顺序及字段显示名称，使之符合“省份、割接具体地点、割接位置A端站点、割接位置Z端站点、割接位置经度、割接位置维度”的顺序，并同时应用于割接详情页和信息维护（编辑）页。

## 需求详情

### 1. 字段名称统一
- 将原本的“割接影响Z端站点”字段显示名称统一变更为**“割接位置Z端站点”**。

### 2. 割接信息维护页（编辑表单）字段顺序调整
在“割接位置”分组下的字段渲染顺序调整为：
1. **省份** (`province`)
2. **割接具体地点** (`cutover_location`)
3. **割接位置A端站点** (`interruption_location_a`)
4. **割接位置Z端站点** (`interruption_location`)
5. **割接位置经度** (`cutover_longitude`)
6. **割接位置纬度** (`cutover_latitude`)

### 3. 割接详情页（Detail Page）属性顺序调整
在详情页的“割接位置”卡片中，字段的展示顺序亦需要同步上述顺序，并由原先的合并展示拆分为独立的行进行展示：
- 第一行：**省份**
- 第二行：**割接具体地点**
- 第三行：**割接位置A端站点**
- 第四行：**割接位置Z端站点**
- 第五行：**割接位置经度**
- 第六行：**割接位置纬度**（右侧保留原有“地图”快捷定位按钮）

## 拟修改文件列表

- **模型定义**：[netbox_otnfaults/models.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/models.py)
- **表单定义**：[netbox_otnfaults/forms.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/forms.py)
- **编辑模板**：[netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html)
- **详情页模板**：[netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html)

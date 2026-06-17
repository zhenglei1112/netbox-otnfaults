# 割接编辑页面资源信息组位置调整需求文档

本需求旨在重新规划割接新建和编辑信息维护表单页面的视觉布局和分组顺序。通过将“资源信息”分组移动到“计划割接时间”分组之后，使得维护页的填写流更符合业务操作顺序。

## 详细布局规划

在割接表单的渲染卡片中，各分组的渲染顺序调整为：
1. **割接信息**
2. **割接位置**
3. **组织联系人**
4. **计划割接时间**
5. **资源信息**（移至此处）
6. **实施时间线**
7. **考核与闭环**
8. **整改信息**
9. **其他**

## 拟修改文件列表

- **表单定义**：[netbox_otnfaults/forms.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/forms.py)
- **编辑模板**：[netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html)
- **单元测试**：[tests/test_cutover_management_scaffold.py](file:///d:/Src/netbox-otnfaults/tests/test_cutover_management_scaffold.py)

# Implementation Plan - 插件菜单权限控制

为 Netbox OTN 可视化插件的菜单设置权限控制，确保无权限用户无法看到菜单项。

## 任务列表

- [x] 修改 `netbox_otnfaults/navigation.py`，为每个菜单项和按钮添加 `permissions` 属性。

## 详细步骤

### 1. 修改 `navigation.py`
为 `PluginMenuItem` 和 `PluginMenuButton` 添加 `permissions` 参数。权限格式为 `{app_label}.{action}_{model_name}`。

#### 故障登记
- 菜单项权限：`['netbox_otnfaults.view_otnfault']`
- 添加按钮权限：`['netbox_otnfaults.add_otnfault']`

#### 故障影响业务
- 菜单项权限：`['netbox_otnfaults.view_otnfaultimpact']`
- 添加按钮权限：`['netbox_otnfaults.add_otnfaultimpact']`

#### 裸纤业务
- 菜单项权限：`['netbox_otnfaults.view_barefiberservice']`
- 添加按钮权限：`['netbox_otnfaults.add_barefiberservice']`

#### 电路业务
- 菜单项权限：`['netbox_otnfaults.view_circuitservice']`
- 添加按钮权限：`['netbox_otnfaults.add_circuitservice']`

#### 路径组
- 菜单项权限：`['netbox_otnfaults.view_otnpathgroup']`
- 添加按钮权限：`['netbox_otnfaults.add_otnpathgroup']`

#### 路径管理
- 菜单项权限：`['netbox_otnfaults.view_otnpath']`
- 添加按钮权限：`['netbox_otnfaults.add_otnpath']`

#### 地图与可视化
- 故障分布图：`['netbox_otnfaults.view_otnfault']` (复用故障查看权限)
- 线路设计器：`['netbox_otnfaults.view_otnpath']` (复用路径查看权限)
- 态势大屏：`['netbox_otnfaults.view_otnfault']` (复用故障查看权限)

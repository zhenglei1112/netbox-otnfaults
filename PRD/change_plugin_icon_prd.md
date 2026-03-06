# 需求文档：故障管理插件菜单图标更新

## 1. 需求背景
当前 NetBox 插件 `netbox-otnfaults` 在左侧菜单“故障管理”中使用的图标为 `mdi-alert-circle-outline`（外加圆圈的感叹号），显得较为普通。用户希望更换一个更加形象、有特点的图标，以提升交互体验和辨识度。

## 2. 需求描述
- 将原有的 `mdi-alert-circle-outline` 图标替换为一个更符合“故障诊断与修复”含义的图标。
- 考虑到“故障处理”的特性，采用类似急救、维修等易于联想的元素。

## 3. 实施方案 (Implementation Plan)
**步骤：**
1. 目标文件：修改项目的主目录中的 `navigation.py` 文件。
2. 配置项：找到 `PluginMenu` 定义中的 `icon_class` 参数。
3. 图标更新：将 `icon_class='mdi mdi-alert-circle-outline'` 变更为 `icon_class='mdi mdi-tools'`（维修工具图标），寓意故障的排查与处理。

**备选图标：**
- `mdi-tools`（工具/维修，当前选择）
- `mdi-medical-bag`（急救包）
- `mdi-flash-alert`（闪电报警）
- `mdi-stethoscope`（听诊器/诊断）

## 4. 影响评估
- 该修改只涉及前端图标的类名变更，不会对后端业务逻辑和数据库状态造成任何影响。
- 无需额外的包安装或依赖更新，只需重启 NetBox 乃至重新加载静态资源即可生效。

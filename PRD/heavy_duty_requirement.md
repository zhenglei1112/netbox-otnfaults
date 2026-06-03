# 重保信息模块需求与设计文档

## 1. 业务背景
在网络运维和光传送网（OTN）管理中，经常会有特定时期（如全国会议、重大节日、保障期）的重要安全保障要求（简称“重保”）。在此期间，特定网络专线、电路或站点需处于高级别监控和保障状态。
系统需要能够登记并管理这些重保通知，同时在重保时间段内，自动将该通知显示在“中交信通网络运行态势图”（态势大屏）上，以提醒大屏值守人员。

## 2. 功能范围
1. **重保登记管理**：在 Netbox 插件的管理后台中提供重保信息的登记和增删改查。
2. **时效性过滤**：重保信息具备开始与结束时间，只有当前时间在重保时段内的通知才会激活。
3. **大屏态势展示**：在大屏顶部悬浮高科技感的暗黑风横幅跑马灯，展示当前生效的重保通知内容。

## 3. 模型定义（HeavyDuty）

重保模型 `HeavyDuty` 继承自 Netbox 的 `NetBoxModel`：

| 字段名 | Django 字段类型 | 属性与约束 | 说明 / 样例 |
| :--- | :--- | :--- | :--- |
| `name` | `CharField` | max_length=200, verbose_name='重保标题' | 5月13日部海事局召开全国海事工作会议重保 |
| `start_time` | `DateTimeField` | verbose_name='开始时间' | 2026-05-13 00:00:00 |
| `end_time` | `DateTimeField` | verbose_name='结束时间' | 2026-05-13 23:59:59 |
| `description` | `TextField` | verbose_name='重保描述/通知' | 【重保通知】5月13日部海事局召开全国海事工作会议，期间海事局所有专线实施重保 |
| `sites` | `ManyToManyField` | to='dcim.Site', blank=True, verbose_name='保障站点' | 地面站-13直属海事局、部-和平里、部-地面站 |
| `circuit_services` | `ManyToManyField` | to='CircuitService', blank=True, verbose_name='保障电路' | 关联的电路专线（可选） |
| `bare_fiber_services` | `ManyToManyField` | to='BareFiberService', blank=True, verbose_name='保障裸纤' | 关联的裸纤专线（可选） |

### 业务规则校验：
- 重保的结束时间 `end_time` 必须晚于开始时间 `start_time`。

---

## 4. UI 界面与操作

### 4.1 Netbox 插件后台管理
- **列表展示 (HeavyDutyTable)**：
  - 显示字段：重保标题、开始时间、结束时间、重保描述。
  - **分页规范**：禁止使用 django_tables2 默认分页，需隐藏默认分页并使用项目自定义分页结构（页码导航、显示信息、每页下拉选择）。
  - **操作按钮**：编辑、删除按钮列（`actions`）作为表格的最后一列。
- **添加/编辑表单 (HeavyDutyForm)**：
  - 使用 Netbox 标准表单，字段支持动态联想多选（站点、业务）。
- **过滤与检索**：
  - 支持按时间范围、关联站点、关联业务进行筛选。

### 4.2 大屏动态滚动展示
- **数据推送**：
  - 大屏后端 API `DashboardDataAPI` 自动查询当前时间在 `[start_time, end_time]` 范围内的重保通知，通过 JSON 响应中的 `heavy_duties` 数组返回。
- **前端动效**：
  - 在大屏正上方（地图容器 `#map-stage` 顶部）悬浮显示红发光边框、半透明暗红背景的跑马灯横幅 (`.heavy-duty-banner`)。
  - 如果有多条重保，文本中间用 ` | ` 分隔，无缝循环滚动。
  - 当无活跃重保时，横幅自动淡出/隐藏。

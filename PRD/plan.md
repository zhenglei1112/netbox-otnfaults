# 今明割接任务小组件需求与技术方案

## 1. 需求背景
割接管理是 OTN 故障管理系统中的核心环节。为了让用户在仪表盘首页即可直观获取当前（今日）和下一自然日（明日）即将进行的割接任务，需要开发一个全新的 Dashboard 小组件（今明割接任务）。
当且仅当割接任务的“线路主管”为当前登录用户时，在列表中进行重点高亮显示，以便相关主管快速定位自身责任范围内的割接。

## 2. 功能要求
1. **今明割接过滤**：自动获取本地时区的今日和明日日期，只展示此时间段内的割接任务。
2. **列表分栏/分组**：将今日与明日割接分别进行分组展示，无割接任务时显示友好的占位说明（如“今日无割接计划”）。
3. **关键信息透显**：列表中显示割接计划时间（显示小时和分钟，如 14:30）、省份、具体地点、割接编号以及割接类型。
4. **状态及类型彩色标签**：使用系统中配置好的割接状态与类型色彩对标签进行染色渲染。
5. **当前用户主管任务高亮**：
   - 逻辑：割接任务的 `line_supervisor`（线路主管）为当前 `request.user`。
   - 视觉效果：
     - 在普通模式下，应用淡黄色背景底色（`bg-warning-subtle` 或 `#fffbeb`），左侧竖向指示条加宽并变为金黄色（`#eab308`）。
     - 在深色模式下（通过 NetBox 的 `html[data-bs-theme="dark"]` 适配），显示为暗金黄色背景，保持优秀的色彩对比度。
     - 在主管的名字前或卡片中添加特殊的“⭐ 我主管”或徽章标志。
6. **可跳转交互**：列表项整体可点击，并跳转到割接详情页。

## 3. 技术实现方案

### 3.1 模型字段引用
在 `CutoverTask` 模型中，我们将查询并引用以下字段：
- `planned_cutover_time`: 计划割接时间（`DateTimeField`）
- `line_supervisor`: 线路主管（外键，指向用户模型）
- `cutover_no`: 割接编号（`CharField`）
- `cutover_type`: 割接类型（使用 `CutoverTypeChoices` 颜色及显示名称）
- `cutover_location`: 割接具体地点（`TextField`）
- `status`: 状态（使用 `CutoverStatusChoices` 颜色及显示名称）
- `province`: 省份（外键，指向 `dcim.Region`）

### 3.2 后端逻辑设计 (`netbox_otnfaults/dashboard.py`)
定义 `OtnTodayTomorrowCutoverWidget` 类并注册：
```python
@register_widget
class OtnTodayTomorrowCutoverWidget(DashboardWidget):
    default_title = "今明割接任务"
    description = "展示今日与明日的计划割接，当前用户为主管的任务高亮显示。"
    width = 4
    height = 4

    def render(self, request) -> str:
        # 获取本地时间
        # 计算 today 和 tomorrow 的 date
        # 查询并过滤 CutoverTask 列表
        # 对今天和明天割接进行分组
        # 针对每一项判定 is_my_task
        # 渲染渲染模板 'netbox_otnfaults/inc/dashboard_today_tomorrow_cutover_widget.html'
```

### 3.3 前端样式设计 (`netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_today_tomorrow_cutover_widget.html`)
- 列表式布局，使用 Flex 弹性盒，外边框加圆角。
- 单条割接的悬浮及交互效果。
- 区分线路主管是否为当前用户的 CSS 高亮样式（分别适配亮色/暗色主题）。
- 当日无割接时显示简洁优雅的文字占位。

## 4. 验收标准
1. 小组件可在 Netbox 首页的配置面板中选择并添加到仪表盘中。
2. 过滤得到且仅显示今天和明天的割接任务（按计划割接时间判断）。
3. 若某割接任务的主管（`line_supervisor`）与当前登录用户一致，该行割接会有显著的亮色或深色黄色背景高亮，且带有一颗“我主管”的醒目标签。
4. 点击列表中任一任务均能正常跳转至该割接详情页面。

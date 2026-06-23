# 割接申请中状态下隐藏三组信息需求文档 (PRD)

## 1. 需求说明
在割接任务的状态为“申请中”（`applying`）时，界面不需要展示或者填写“实施时间线”、“考核与闭环”、“整改信息”这三组信息。

这些信息应当在：
- 详情展示页
- 编辑表单页
均做隐藏处理。

其中，在**编辑表单页**，隐藏逻辑需支持**前端动态联动**。即用户如果在表单中手动将状态下拉菜单从“申请中”切换为其他状态（如“待实施”），这三组字段需能够立即显现供用户填写；若重新切换回“申请中”，则应重新隐去。

---

## 2. 拟做出的变更

### 2.1 详情页变更 (netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html)
- 用 `{% if object.status != 'applying' %}` 条件标签包裹以下三组卡片：
  - 实施时间线 card
  - 考核与闭环 card
  - 整改信息 card

### 2.2 编辑页变更 (netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html)
- 为以下三组 `<div class="field-group my-5">` 分别分配 `id` 以便于前端控制：
  - 实施时间线：`id="group_implementation_timeline"`
  - 考核与闭环：`id="group_assessment_closure"`
  - 整改信息：`id="group_rectification_info"`
- 在底部的 script 部分添加 `initStatusSectionToggle` 方法：
  - 获取 `id_status` 节点以及上述三个组容器节点。
  - 监听状态节点上的 `change` 事件。
  - 根据其当前值是否等于 `'applying'`，设置上述三个组容器的 `style.display` 为 `'none'`（申请中状态）或 `'block'`（其他状态）。
  - 页面初次加载完毕后，由加载程序自动运行一次该逻辑。

### 2.3 单元测试更新 (tests/test_cutover_status_auto_set.py)
- 新增静态代码检测，验证详情页以及编辑页的条件判定和 ID 声明已正确添加。

---

## 3. 验证计划
- **自动检查**：运行 `python -m unittest tests/test_cutover_status_auto_set.py`，确认所有测试均通过。
- **手动检查**：
  1. 验证状态为“申请中”的割接任务详情页中，这三组卡片是否已不见。
  2. 验证割接任务编辑页中，当状态选择“申请中”时，三组字段是否被隐去。
  3. 在编辑页将状态切换为“待实施”或“已完成”时，验证三组字段是否自动显现。

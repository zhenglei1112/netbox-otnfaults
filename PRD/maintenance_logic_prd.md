# PRD - Maintenance Mode Logic & Choice Update

## 变更背景
针对租赁场景，需要增加特定的维护方式选项，并实现表单输入时的自动化联动，减少用户重复操作。

## 变更详情
1.  **选项增加**:
    *   在“维护方式” (`maintenance_mode`) 字段中增加选项：**租赁自带** (Key: `leased_owned`)。
2.  **联动逻辑**:
    *   在编辑或创建故障记录时，如果用户选择“光纤来源”为 **租赁纤芯** (`leased`)，系统应自动将“维护方式”设置为 **租赁自带**。

## 修改范围
1.  **后端模型 (`models.py`)**: 
    *   更新 `MaintenanceModeChoices` 枚举类。
2.  **前端模板 (`otnfault_edit.html`)**:
    *   新增 `initFiberLogic` JavaScript 函数。
    *   绑定 `resource_type` 的 `change` 事件。
3.  **脚本同步**:
    *   `weekly_fault_report.py`: 增加选项显示映射。
    *   `generate_fault_data.py`: 在随机池中加入新选项。

## 操作指南
1.  **更新元数据**: 运行 `python manage.py makemigrations`。
2.  **测试联动**: 进入故障编辑页，修改“光纤来源”为“租赁纤芯”，观察“维护方式”是否自动跳转为“租赁自带”。

# 裸纤业务模块新增字段需求文档 (PRD)

## 1. 需求背景
根据用户需求，需要在“裸纤业务” (BareFiberService) 模型中增加三个字段，以满足业务管理和计费周期的记录需求。

## 2. 需求详情
新增以下三个字段：
1. **业务主管 (business_manager)**
   - 数据类型：外键 (引用系统用户表 `settings.AUTH_USER_MODEL`)
   - 展现形式：下拉选择框
   - 必填：否
2. **计费起始时间 (billing_start_time)**
   - 数据类型：日期时间 (DateTimeField)
   - 展现形式：日期时间选择器
   - 必填：否
3. **计费结束时间 (billing_end_time)**
   - 数据类型：日期时间 (DateTimeField)
   - 展现形式：日期时间选择器
   - 必填：否

## 3. 影响范围
- **数据模型 (models.py)**：修改 `BareFiberService` 模型，增加上述三个字段。
- **表单 (forms.py)**：修改 `BareFiberServiceForm`, `BareFiberServiceFilterForm`, `BareFiberServiceBulkEditForm`, `BareFiberServiceImportForm` 以支持新字段。
- **数据表渲染 (tables.py)**：修改 `BareFiberServiceTable`，将新字段添加为列并可显示。
- **模板前端 (templates)**：修改 `barefiberservice.html`，在详情页展示新字段。
- **REST API (api/serializers.py)**：修改 `BareFiberServiceSerializer` 将新字段暴露给接口。
- **过滤系统 (filtersets.py)**：修改 `BareFiberServiceFilterSet` 允许新字段的筛选。
- **数据库迁移**：运行 makemigrations 和 migrate。

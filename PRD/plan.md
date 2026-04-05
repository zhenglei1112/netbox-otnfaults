# OTN故障模型增加运维主管字段实施计划

## 需求说明
为 `OtnFault` （OTN故障）模型增加一个“运维主管”字段（`operations_manager`）。该字段为可多选的用户模型字段。同时，在创建或编辑故障时，根据选择的“故障类型”(`fault_category`)自动设置运维主管：
- **电源故障** (`power_fault`) -> 设置为：**赵应**
- **设备故障** (`device_fault`) -> 设置为：**刘家良**
- **其他类型故障** (`fiber_break`, `fiber_degradation`, `fiber_jitter`, `ac_fault` 等) -> 设置为：**刘家良、何志宏、李旭**

## 1. 数据库模型变更 (`models.py`)
在 `netbox_otnfaults/models.py` 的 `OtnFault` 类中添加 `operations_manager` 字段。
```python
operations_manager = models.ManyToManyField(
    to=settings.AUTH_USER_MODEL,
    related_name='managed_otn_faults_operations',
    verbose_name='运维主管',
    blank=True
)
```

## 2. API 序列化器变更 (`api/serializers.py`)
在 `OtnFaultSerializer` 类中添加字段序列化。
```python
operations_manager = NestedUserSerializer(many=True, required=False)
```
并在 `Meta.fields` 和 `Meta.brief_fields`（视情况）中包含该字段。

## 3. 表单层变更 (`forms.py`)
更新涉及故障的四个主要表单，将 `operations_manager` 放入布局中：
- `OtnFaultForm`：添加 `DynamicModelMultipleChoiceField` 并更新 `Meta.fields` 和 `fieldsets`。在 `OtnFaultForm` 的布局中，把 `operations_manager` 放入“故障信息”的同一块区域。
- `OtnFaultBulkEditForm`：同上。
- `OtnFaultFilterForm`：同上。
- `OtnFaultImportForm`：添加 `CSVModelMultipleChoiceField` 并更新 `Meta.fields`。

## 4. 表格视图与过滤器变更 (`tables.py`, `filtersets.py`)
- **`tables.py`**: 在 `OtnFaultTable` 中添加 `operations_manager = columns.ManyToManyColumn(linkify_item=True, verbose_name='运维主管')` 并加入 `Meta.fields`。
- **`filtersets.py`**: 在 `OtnFaultFilterSet` 中补充按运维主管进行查找的过滤器。

## 5. 前端交互与视图变更 (`templates`)
- **`otnfault_edit.html`**:
  1. 将 `{% render_field form.operations_manager %}` 放置在基础信息（故障信息）区块的最末尾，即在 `{% render_field form.tags %}` 之后。
  2. 新增 JavaScript `initOperationsManagerLogic()`：
     监听 `fault_category` 字段的变更，通过映射规则查找相应的人名。结合通过 `fetch('/api/users/users/?q=...')` 搜索对应的用户，将寻找到的 User IDs 添加到 `operations_manager` 的 TomSelect 组件中实现自动多选填充。
- **`otnfault.html`** (详情页面): 补充运维主管信息的展示行。

## 6. 数据库迁移与应用
生成并应用数据库迁移脚本：
```bash
python manage.py makemigrations netbox_otnfaults
python manage.py migrate
```

# 电路业务扩展信息筛选、导出与列设置支持需求文档 (PRD)

本需求文档详细说明了如何使电路业务模型的“扩展信息”字段（存储在 `extra_fields` JSONField 中）在 NetBox 列表中支持列设置勾选、支持导出以及支持筛选过滤的实现方案。

## 1. 业务背景与问题描述
在 NetBox OTN 可视化插件中，电路业务模型 (`CircuitService`) 包含许多动态定义的扩展字段（如需求单号、服务开通时间、互联信息等），这些字段目前以 `JSONField` 形式存储在数据库的 `extra_fields` 列中。
然而，当前的设计存在以下限制：
- **无法自定义列显示**：在电路业务列表的“列设置”中，看不到这些扩展字段，无法勾选使其显示在表格中。
- **不支持导出**：当导出电路业务列表数据（CSV/Excel）时，扩展信息字段无法一并导出。
- **不支持筛选**：用户在列表页面的过滤面板中，无法通过扩展信息字段对电路业务进行过滤筛选。

## 2. 需求范围与改进方案

### 2.1 列表及列设置支持 (tables.py)
1. 动态生成 django-tables2 列：根据 `CircuitService.EXTRA_FIELD_DEFINITIONS` 中的字段定义，为每个扩展字段在类加载时动态注入一个自定义列类 `ExtraFieldColumn`。
2. 数据安全提取：在 `ExtraFieldColumn` 中指定数据访问器 `accessor='extra_fields'`，并重写 `render` 和 `value` 方法。在渲染及导出值提取时，直接且安全地从行的 `extra_fields` 属性（即 JSON 字典）中取出对应键的值。
3. 允许用户配置：将所有扩展字段列名注册到 `CircuitServiceTable.Meta.fields` 中，使 NetBox 列自定义面板（Configure Table）能够展示这些列并支持用户勾选。

### 2.2 过滤筛选支持 (filtersets.py & forms.py)
1. 后端过滤 (API/GraphQL/View)：在 `CircuitServiceFilterSet` 过滤器集中，动态为每个扩展字段注入 `django_filters.CharFilter`，指定数据库映射字段为 `extra_fields__<field_name>`，并使用 `icontains` 实现模糊匹配筛选。
2. 前端过滤面板 (UI)：在 `CircuitServiceFilterForm` 过滤表单中，动态生成对应的 `forms.CharField` 字段。
3. 表单布局优化：在 `CircuitServiceFilterForm.fieldsets` 中，专门新增一个名为“扩展信息”的 `FieldSet`，将所有扩展过滤输入框统一收纳展示，保持前端 UI 整洁。

---

## 3. 实现技术细节

### 3.1 tables.py 变更细节
- 新增 `ExtraFieldColumn` 类，继承自 `django_tables2.Column`：
  ```python
  class ExtraFieldColumn(tables.Column):
      def __init__(self, field_name, *args, **kwargs):
          self.field_name = field_name
          kwargs['accessor'] = 'extra_fields'
          super().__init__(*args, **kwargs)

      def render(self, value, record):
          if isinstance(value, dict):
              return value.get(self.field_name, '')
          return ''

      def value(self, value, record):
          if isinstance(value, dict):
              return value.get(self.field_name, '')
          return ''
  ```
- 在 `CircuitServiceTable` 类体内动态注入列：
  ```python
  class CircuitServiceTable(NetBoxTable):
      # ... 原有字段定义 ...
      
      # 动态声明扩展列
      for field_name, verbose_name in CircuitService.EXTRA_FIELD_DEFINITIONS:
          locals()[field_name] = ExtraFieldColumn(
              field_name=field_name,
              verbose_name=verbose_name,
              orderable=False
          )
  ```
- 更新 `Meta.fields`，将 `*dict(CircuitService.EXTRA_FIELD_DEFINITIONS).keys()` 动态解包解入字段列表。

### 3.2 filtersets.py 变更细节
- 在 `CircuitServiceFilterSet` 类体内注入过滤器：
  ```python
  class CircuitServiceFilterSet(NetBoxModelFilterSet):
      # ... 原有过滤器 ...
      
      for field_name, verbose_name in CircuitService.EXTRA_FIELD_DEFINITIONS:
          locals()[field_name] = django_filters.CharFilter(
              field_name=f'extra_fields__{field_name}',
              lookup_expr='icontains',
              label=verbose_name
          )
  ```
- 更新 `Meta.fields` 包含解包后的所有扩展字段名。

### 3.3 forms.py 变更细节
- 在 `CircuitServiceFilterForm` 中动态注入表单字段：
  ```python
  class CircuitServiceFilterForm(NetBoxModelFilterSetForm):
      # ... 原有表单字段 ...
      
      for field_name, verbose_name in CircuitService.EXTRA_FIELD_DEFINITIONS:
          locals()[field_name] = forms.CharField(
              required=False,
              label=verbose_name
          )
  ```
- 更新 `fieldsets` 属性，添加：
  ```python
  FieldSet(*dict(CircuitService.EXTRA_FIELD_DEFINITIONS).keys(), name='扩展信息')
  ```

---

## 4. 验证与测试方案
1. 编写离线测试脚本：通过加载 Django 环境或直接在模拟环境下反射检查 `CircuitServiceTable`、`CircuitServiceFilterSet` 以及 `CircuitServiceFilterForm` 的属性。
2. 确认：
   - 包含 `request_number` 等动态列，且其 `accessor` 均为 `extra_fields`。
   - `CircuitServiceFilterSet.base_filters` 中有对应的模糊匹配过滤器。
   - `CircuitServiceFilterForm.base_fields` 中包含所有的输入框，且 `fieldsets` 分组渲染正确。

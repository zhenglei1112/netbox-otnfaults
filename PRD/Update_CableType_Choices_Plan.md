# 更新光缆类型选项 - 执行计划

## 目标
更新 `OtnPath` 模型中的“光缆类型”（Cable Type）选项，以符合新的业务需求：
- 自建 (Self-built)
- 协调 (Coordinated)
- 租赁 (Leased)
同时将“描述”字段的高度调整为 2 行。

## 拟议变更

### 1. 模型层 (`netbox_otnfaults/models.py`)
更新 `CableTypeChoices` 类：
```python
class CableTypeChoices(ChoiceSet):
    key = 'OtnPath.cable_type'

    SELF_BUILT = 'self_built'
    COORDINATED = 'coordinated'
    LEASED = 'leased'

    CHOICES = [
        (SELF_BUILT, '自建', 'green'),
        (COORDINATED, '协调', 'blue'),
        (LEASED, '租赁', 'purple'),
    ]
```

### 2. 表单层 (`netbox_otnfaults/forms.py`)
- 更新 `OtnPathForm`：设置 `description` 字段的 `widgets` 属性，使高度为 2 行。
- 更新 `OtnPathBulkEditForm`：同步将 `description` 字段的文本框高度设置为 2 行。

### 3. 脚本层 (`netbox_otnfaults/scripts/import_otn_paths.py`)
更新 ArcGIS 导入脚本中的随机选择逻辑，使用新的常量值（`SELF_BUILT`, `COORDINATED`, `LEASED`）。

### 4. 数据库
- 需要生成并运行迁移：
  ```bash
  python manage.py makemigrations netbox_otnfaults
  python manage.py migrate netbox_otnfaults
  ```

## 任务清单
- [x] 创建执行计划
- [x] 修改 `netbox_otnfaults/models.py`
- [x] 检查并更新 `netbox_otnfaults/scripts/import_otn_paths.py`
- [x] 修改 `netbox_otnfaults/forms.py` 以调整描述字段高度
- [ ] 运行数据库迁移（请用户在 Netbox 运行环境下执行）


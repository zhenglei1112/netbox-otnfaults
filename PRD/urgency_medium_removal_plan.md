# 故障模型紧急程度字段取消“中”选项需求与执行计划

## 1. 需求说明
* **背景**：当前故障模型（`OtnFault`）的紧急程度（`urgency`）字段有高、中、低三个选项。
* **需求**：取消紧急程度字段的“中”选项，仅保留“高”和“低”。
* **目标文件**：
  - `netbox_otnfaults/models.py`
  - 其他可能引用 `UrgencyChoices.MEDIUM` 或是写死 `'medium'` 的代码文件（如测试脚本、视图层等）。
  - 需要生成 Django Migration 以确保数据库 Schema 的 choices 被更新。

## 2. 计划步骤
1. **清理代码引用**：
   - 检查并修改 `models.py` 中的 `UrgencyChoices`，删除 `MEDIUM = 'medium'` 和 `(MEDIUM, '中', 'orange')`。
   - 检查其他业务层代码（如 `dashboard_views.py` 和 `scripts/generate_fault_data.py`），如果有生成或使用 'medium' 的地方，则替换或删除。
2. **生成与应用迁移**：
   - 使用 `python manage.py makemigrations netbox_otnfaults` 生成数据迁移文件。
   - 使用 `python manage.py migrate netbox_otnfaults` 应用到数据库。
3. **验证**：
   - 确认无语法错误。
   - 保证服务重启/运行正常。

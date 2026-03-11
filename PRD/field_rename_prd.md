# 故障模型字段更名需求文档

## 1. 需求背景
根据用户反馈及业务术语规范，需要对 `OtnFault` 模型中的两个关键字段进行更名，以更准确地反映其业务含义。

## 2. 修改内容
| 原字段名 (Internal) | 原显示名 (Verbose) | 新显示名 (Verbose) | 备注 |
| :--- | :--- | :--- | :--- |
| `handling_unit` | 处理单位 | **代维方** | 对应代维或租赁的公司 |
| `resource_type` | 资源类型 | **光纤来源** | 描述光纤的来源属性 |

> [!NOTE]
> 本次修改仅针对显示名称（`verbose_name`），暂不修改数据库字段名，以最大程度减少对现有代码逻辑和 API 的破坏。如果后续需要重构数据库字段，请另行通知。

## 3. 影响范围
- `models.py`: 修改字段定义及 ChoiceSet 中的 key。
- `forms.py`: 确认表单显示。
- `tables.py`: 确认表格列头显示。
- `filtersets.py`: 确认过滤器显示。
- 全局搜索并确保没有硬编码的“处理单位”和“资源类型”字符串。

## 4. 任务列表
1. 修改 `models.py` 中 `OtnFault` 模型的 `handling_unit` 和 `resource_type` 字段的 `verbose_name`。
2. 修改 `ResourceTypeChoices` 的 `verbose_name` 相关显示（如果有）。
3. 检查并更新 `forms.py` 中的字段标签（若有显式定义）。
4. 运行 `makemigrations` 和 `migrate` 生成数据库元数据更新。
5. 验证 UI 显示效果。

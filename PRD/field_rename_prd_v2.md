# PRD - Field Renaming (Round 2)

## 变更背景
为了更准确地描述业务逻辑，包含租赁业务场景，需要对原有的两个字段进行精细化更名。

## 变更详情
| 原始字段名 (模型名) | 上一轮名称 | 本轮更新名称 | 备注 |
| :--- | :--- | :--- | :--- |
| `handling_unit` | 代维方 | **代维方/租赁方** | |
| `contract` | 代维合同 | **代维/租赁合同** | |

## 修改范围
1.  **后端模型**: `models.py` 中的 `verbose_name`。
2.  **表单系统**: `forms.py` 中的所有 `label` 和 `help_text`。
3.  **前端页面**:
    *   故障详情页 (`otnfault.html`) 的数据表格表头。
    *   可视化大屏 (`panels.js`) 的焦点详情卡片。
4.  **自动化脚本**:
    *   统计报告 (`weekly_fault_report.py`) 的描述文字。
    *   数据生成脚本 (`generate_fault_data.py`) 的日志与注释。

## 开发者提示
1.  **迁移同步**: 请在 Netbox 环境运行 `python manage.py makemigrations netbox_otnfaults` 生成迁移文件。
2.  **缓存刷新**: 修改 `static/js` 后，若大屏显示未更新，请清理浏览器缓存或强制刷新 (Ctrl+F5)。

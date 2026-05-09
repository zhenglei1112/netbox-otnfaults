from __future__ import annotations

from typing import Any

from extras.scripts import FileVar, Script, StringVar

from netbox_otnfaults.models import CircuitService
from netbox_otnfaults.services.circuit_service_excel_import import read_circuit_service_excel_rows


class ImportCircuitServiceExtraFields(Script):
    class Meta:
        name = "导入电路业务扩展信息"
        description = "从 Excel 读取扩展字段，并按专线名称 + 电路编号更新现有电路业务的扩展信息。"
        commit_default = True

    excel_file = FileVar(
        description="上传 Excel 文件"
    )
    sheet_name = StringVar(
        default="最终数据",
        description="工作表名称"
    )

    def run(self, data: dict[str, Any], commit: bool) -> None:
        excel_file = data["excel_file"]
        sheet_name = data.get("sheet_name") or "最终数据"

        if not commit:
            self.log_warning("模拟运行：本次不会写入数据库。")

        rows = read_circuit_service_excel_rows(excel_file, sheet_name=sheet_name)
        self.log_info(f"已读取 {len(rows)} 行 Excel 记录。")

        updated_count = 0
        skipped_count = 0
        unmatched_count = 0

        for row in rows:
            extra_fields = row.extra_fields or {}
            if not extra_fields:
                skipped_count += 1
                self.log_info(f"第 {row.row_number} 行跳过：没有可导入的扩展字段。")
                continue

            try:
                service = CircuitService.objects.get(
                    special_line_name=row.special_line_name,
                    name=row.circuit_number,
                )
            except CircuitService.DoesNotExist:
                unmatched_count += 1
                self.log_warning(
                    f"第 {row.row_number} 行未找到电路业务："
                    f"{row.special_line_name} / {row.circuit_number}"
                )
                continue

            merged_extra_fields = {
                **(service.extra_fields or {}),
                **extra_fields,
            }
            if merged_extra_fields == (service.extra_fields or {}):
                skipped_count += 1
                self.log_info(f"第 {row.row_number} 行跳过：扩展信息无变化。")
                continue

            if commit:
                service.extra_fields = merged_extra_fields
                service.save(update_fields=["extra_fields"])
            updated_count += 1
            self.log_info(
                f"第 {row.row_number} 行{'更新' if commit else '计划更新'}："
                f"{row.special_line_name} / {row.circuit_number}"
            )

        self.log_success(
            f"处理完成：更新 {updated_count} 条，跳过 {skipped_count} 条，未匹配 {unmatched_count} 条。"
        )

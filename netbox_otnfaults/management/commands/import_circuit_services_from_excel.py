from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import BusinessCategoryChoices, CircuitService, ServiceGroupChoices
from ...services.circuit_service_excel_import import (
    normalize_business_category_label,
    read_circuit_service_excel_rows,
)


class Command(BaseCommand):
    help = "从 Excel 导入电路业务数据"

    def add_arguments(self, parser) -> None:
        parser.add_argument("excel_path", help="Excel 文件路径")
        parser.add_argument("--sheet", default="最终数据", help="工作表名称，默认使用 最终数据")
        parser.add_argument("--dry-run", action="store_true", help="仅校验和预览，不写入数据库")

    def handle(self, *args, **options) -> None:
        excel_path = Path(options["excel_path"]).expanduser()
        sheet_name = options["sheet"]
        dry_run = options["dry_run"]

        if not excel_path.exists():
            raise CommandError(f"Excel 文件不存在: {excel_path}")

        try:
            rows = read_circuit_service_excel_rows(excel_path, sheet_name=sheet_name)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        category_label_map = {
            label: value
            for value, label, *_ in BusinessCategoryChoices.CHOICES
        }
        service_group_label_map = {
            label: value
            for value, label, *_ in ServiceGroupChoices.CHOICES
        }
        slug_max_length = CircuitService._meta.get_field("slug").max_length

        create_count = 0
        skip_count = 0
        errors: list[str] = []
        logger_lines: list[str] = []
        created_numbers: list[str] = []
        skipped_numbers: list[str] = []

        with transaction.atomic():
            for row in rows:
                category_label = normalize_business_category_label(row.business_category)
                category_value = category_label_map.get(category_label)
                service_group_value = service_group_label_map.get(row.service_group)

                if not category_value:
                    message = f"第 {row.row_number} 行跳过: 业务门类无法识别: {row.business_category}"
                    errors.append(message)
                    logger_lines.append(message)
                    skip_count += 1
                    skipped_numbers.append(row.circuit_number or f"row-{row.row_number}")
                    continue
                if not service_group_value:
                    message = f"第 {row.row_number} 行跳过: 业务组无法识别: {row.service_group}"
                    errors.append(message)
                    logger_lines.append(message)
                    skip_count += 1
                    skipped_numbers.append(row.circuit_number or f"row-{row.row_number}")
                    continue
                if not row.special_line_name:
                    message = f"第 {row.row_number} 行跳过: 缺少专线名称"
                    errors.append(message)
                    logger_lines.append(message)
                    skip_count += 1
                    skipped_numbers.append(row.circuit_number or f"row-{row.row_number}")
                    continue
                if not row.circuit_number:
                    message = f"第 {row.row_number} 行跳过: 缺少电路编号"
                    errors.append(message)
                    logger_lines.append(message)
                    skip_count += 1
                    skipped_numbers.append(f"row-{row.row_number}")
                    continue
                if len(row.circuit_number) > slug_max_length:
                    message = (
                        f"第 {row.row_number} 行跳过: 电路编号超过缩写长度限制 {slug_max_length}: {row.circuit_number}"
                    )
                    errors.append(message)
                    logger_lines.append(message)
                    skip_count += 1
                    skipped_numbers.append(row.circuit_number)
                    continue

                expected_category = CircuitService.SERVICE_GROUP_CATEGORY_MAP.get(service_group_value)
                if expected_category and expected_category != category_value:
                    message = (
                        f"第 {row.row_number} 行跳过: 业务门类与业务组不匹配: {category_label} / {row.service_group}"
                    )
                    errors.append(message)
                    logger_lines.append(message)
                    skip_count += 1
                    skipped_numbers.append(row.circuit_number)
                    continue

                instance = CircuitService()
                instance.special_line_name = row.special_line_name
                instance.name = row.circuit_number
                instance.slug = row.circuit_number
                instance.business_category = category_value
                instance.service_group = service_group_value
                instance.full_clean()

                create_count += 1
                created_numbers.append(row.circuit_number)
                logger_lines.append(
                    f"第 {row.row_number} 行新增: 电路编号={row.circuit_number}, 业务门类={category_label}, "
                    f"业务组={row.service_group}, 专线名称={row.special_line_name}"
                )

                if not dry_run:
                    instance.save()

            for line in logger_lines:
                self.stdout.write(line)

            if errors:
                raise CommandError("\n".join(errors))

            if dry_run:
                transaction.set_rollback(True)

        summary = (
            f"已解析 {len(rows)} 条记录，"
            f"{'计划' if dry_run else '实际'}新增 {create_count} 条，"
            f"{'计划' if dry_run else '实际'}跳过 {skip_count} 条。"
        )
        self.stdout.write(self.style.SUCCESS(summary))
        self.stdout.write(f"新增名单: {', '.join(created_numbers) if created_numbers else '无'}")
        self.stdout.write(f"跳过名单: {', '.join(skipped_numbers) if skipped_numbers else '无'}")

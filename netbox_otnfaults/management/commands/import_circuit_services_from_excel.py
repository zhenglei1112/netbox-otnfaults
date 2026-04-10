from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import (
    BusinessCategoryChoices, CircuitOperationStatusChoices, CircuitService,
    SLALevelChoices, ServiceGroupChoices,
)
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

        existing_services = {
            (svc.special_line_name, svc.name): svc
            for svc in CircuitService.objects.all()
        }

        User = get_user_model()
        user_map = {
            u.get_full_name(): u for u in User.objects.all() if u.get_full_name()
        }
        user_map.update({u.username: u for u in User.objects.all()})

        create_count = 0
        update_count = 0
        skip_count = 0
        errors: list[str] = []
        created_numbers: list[str] = []
        updated_numbers: list[str] = []
        skipped_numbers: list[str] = []

        with transaction.atomic():
            for row in rows:
                category_label = normalize_business_category_label(row.business_category)
                category_value = category_label_map.get(category_label)
                service_group_value = service_group_label_map.get(row.service_group)

                if not category_value:
                    message = f"第 {row.row_number} 行跳过: 业务门类无法识别: {row.business_category}"
                    errors.append(message)
                    skip_count += 1
                    skipped_numbers.append(row.circuit_number or f"row-{row.row_number}")
                    continue
                if not service_group_value:
                    message = f"第 {row.row_number} 行跳过: 业务组无法识别: {row.service_group}"
                    errors.append(message)
                    skip_count += 1
                    skipped_numbers.append(row.circuit_number or f"row-{row.row_number}")
                    continue
                if not row.special_line_name:
                    message = f"第 {row.row_number} 行跳过: 缺少专线名称"
                    errors.append(message)
                    skip_count += 1
                    skipped_numbers.append(row.circuit_number or f"row-{row.row_number}")
                    continue
                if not row.circuit_number:
                    message = f"第 {row.row_number} 行跳过: 缺少电路编号"
                    errors.append(message)
                    skip_count += 1
                    skipped_numbers.append(f"row-{row.row_number}")
                    continue
                if len(row.circuit_number) > slug_max_length:
                    message = (
                        f"第 {row.row_number} 行跳过: 电路编号超过缩写长度限制 {slug_max_length}: {row.circuit_number}"
                    )
                    errors.append(message)
                    skip_count += 1
                    skipped_numbers.append(row.circuit_number)
                    continue

                expected_category = CircuitService.SERVICE_GROUP_CATEGORY_MAP.get(service_group_value)
                if expected_category and expected_category != category_value:
                    message = (
                        f"第 {row.row_number} 行跳过: 业务门类与业务组不匹配: {category_label} / {row.service_group}"
                    )
                    errors.append(message)
                    skip_count += 1
                    skipped_numbers.append(row.circuit_number)
                    continue

                key = (row.special_line_name, row.circuit_number)
                instance = existing_services.get(key)
                is_new = instance is None

                if is_new:
                    instance = CircuitService()
                    instance.special_line_name = row.special_line_name
                    instance.name = row.circuit_number
                    instance.slug = row.circuit_number
                else:
                    message = f"第 {row.row_number} 行更新: 发现重复记录执行更新 (专线名称: {row.special_line_name}, 电路编号: {row.circuit_number})"
                    self.stdout.write(self.style.WARNING(message))

                instance.business_category = category_value
                instance.service_group = service_group_value

                if row.bandwidth:
                    bw_str = row.bandwidth.strip().upper()
                    is_g = False
                    if bw_str.endswith("G"):
                        is_g = True
                        bw_str = bw_str[:-1]
                    elif bw_str.endswith("GBPS"):
                        is_g = True
                        bw_str = bw_str[:-4]
                    elif bw_str.endswith("M") or bw_str.endswith("MBPS"):
                        bw_str = bw_str.replace("MBPS", "").replace("M", "")

                    try:
                        val = float(bw_str)
                        instance.bandwidth = int(val * 1000) if is_g else int(val)
                    except ValueError:
                        pass

                if row.business_manager:
                    user = user_map.get(row.business_manager.strip())
                    if user:
                        instance.business_manager = user
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"第 {row.row_number} 行提示: 业务主管无法识别: {row.business_manager}"
                        ))

                if row.sla_level:
                    sla_cleaned = row.sla_level.strip()
                    sla_valid_values = {v for v, *_ in SLALevelChoices.CHOICES}
                    if sla_cleaned in sla_valid_values:
                        instance.sla_level = sla_cleaned
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"第 {row.row_number} 行提示: SLA等级无法识别: {row.sla_level}"
                        ))

                if row.operation_status:
                    op_label_map = {label: value for value, label, *_ in CircuitOperationStatusChoices.CHOICES}
                    op_value = op_label_map.get(row.operation_status.strip())
                    if op_value:
                        instance.operation_status = op_value
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"第 {row.row_number} 行提示: 运行状态无法识别: {row.operation_status}"
                        ))

                # 环网保护: 仅 '是' 为 True, 其余均设为 False
                instance.ring_protection = (row.ring_protection.strip() == "是") if row.ring_protection else False

                # 对部服务: 仅 '是' 为 True, 其余均设为 False
                instance.is_external_business = (row.is_external_business.strip() == "是") if row.is_external_business else False

                instance.full_clean()

                if is_new:
                    create_count += 1
                    created_numbers.append(row.circuit_number)
                    existing_services[key] = instance
                else:
                    update_count += 1
                    updated_numbers.append(row.circuit_number)

                if not dry_run:
                    instance.save()

            if errors:
                raise CommandError("\n".join(errors))

            if dry_run:
                transaction.set_rollback(True)

        summary = (
            f"已解析 {len(rows)} 条记录，"
            f"{'计划' if dry_run else '实际'}新增 {create_count} 条，"
            f"{'计划' if dry_run else '实际'}更新 {update_count} 条，"
            f"{'计划' if dry_run else '实际'}跳过 {skip_count} 条。"
        )
        self.stdout.write(self.style.SUCCESS(summary))

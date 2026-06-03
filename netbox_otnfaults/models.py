from django.db import models
from typing import Any

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from netbox.models import NetBoxModel
from netbox.models.features import ImageAttachmentsMixin
from dcim.models import Site
from tenancy.models import Tenant
from utilities.choices import ChoiceSet
import taggit.managers
from django.core.exceptions import ValidationError


def _format_duration_units(days: int, hours: int, minutes: int, seconds: int) -> str:
    units: list[tuple[int, str]] = [
        (days, "天"),
        (hours, "小时"),
        (minutes, "分"),
        (seconds, "秒"),
    ]
    for index, (value, _) in enumerate(units):
        if value > 0:
            return "".join(f"{amount}{label}" for amount, label in units[index:])
    return "0秒"


class FaultCategoryChoices(ChoiceSet):
    key = 'OtnFault.fault_category'

    FIBER_BREAK = 'fiber_break'
    AC_FAULT = 'ac_fault'
    FIBER_DEGRADATION = 'fiber_degradation'
    FIBER_JITTER = 'fiber_jitter'
    DEVICE_FAULT = 'device_fault'
    POWER_FAULT = 'power_fault'

    CHOICES = [
        (FIBER_BREAK, '光缆中断', 'purple'),
        (AC_FAULT, '空调故障', 'teal'),
        (FIBER_DEGRADATION, '光缆劣化', 'orange'),
        (FIBER_JITTER, '光缆抖动', 'cyan'),
        (DEVICE_FAULT, '设备故障', 'pink'),
        (POWER_FAULT, '供电故障', 'indigo'),
    ]


class UrgencyChoices(ChoiceSet):
    key = 'OtnFault.urgency'

    HIGH = 'high'
    LOW = 'low'

    CHOICES = [
        (HIGH, '高', 'red'),
        (LOW, '低', 'yellow'),
    ]


class MaintenanceModeChoices(ChoiceSet):
    key = 'OtnFault.maintenance_mode'

    OUTSOURCED = 'outsourced'
    COORDINATED = 'coordinated'
    SELF_MAINTAINED = 'self_maintained'
    LEASED_OWNED = 'leased_owned'

    CHOICES = [
        (OUTSOURCED, '代维', 'blue'),
        (COORDINATED, '协调', 'green'),
        (SELF_MAINTAINED, '自维', 'purple'),
        (LEASED_OWNED, '租赁自带', 'cyan'),
    ]


class PowerDataTypeChoices(ChoiceSet):
    key = 'OtnFault.power_data_type'

    OWNED = 'owned_equipment'
    PHASE_ONE_SUPPORTING = 'phase_one_supporting'
    THIRD_PARTY = 'third_party_provided'

    CHOICES = [
        (OWNED, '自有设备', 'green'),
        (PHASE_ONE_SUPPORTING, '一期配套', 'blue'),
        (THIRD_PARTY, '三方提供', 'orange'),
    ]


class PowerRootCauseAnalysisChoices(ChoiceSet):
    key = 'OtnFault.root_cause_analysis'

    SWITCHING_POWER_FAULT = 'switching_power_fault'
    RECTIFIER_MODULE_FAULT = 'rectifier_module_fault'
    BATTERY_DEPLETED = 'battery_depleted'
    NO_BATTERY = 'no_battery'
    INSUFFICIENT_BATTERY_BACKUP_TIME = 'insufficient_battery_backup_time'
    ROOM_POWER_TEST = 'room_power_test'
    GRID_POWER_MAINTENANCE = 'grid_power_maintenance'
    BREAKER_TRIP = 'breaker_trip'
    UPS_FAULT = 'ups_fault'
    MAINS_POWER_OUTAGE = 'mains_power_outage'
    NATURAL_DISASTER = 'natural_disaster'
    HUMAN_MISOPERATION = 'human_misoperation'
    OTHER = 'other'

    CHOICES = [
        (SWITCHING_POWER_FAULT, '开关电源故障', 'red'),
        (RECTIFIER_MODULE_FAULT, '整流模块故障', 'orange'),
        (BATTERY_DEPLETED, '电池耗尽', 'yellow'),
        (NO_BATTERY, '无电池', 'gray'),
        (INSUFFICIENT_BATTERY_BACKUP_TIME, '电池备电时间不足', 'yellow'),
        (ROOM_POWER_TEST, '机房供电测试', 'blue'),
        (GRID_POWER_MAINTENANCE, '国网供电检修', 'cyan'),
        (BREAKER_TRIP, '空开跳闸', 'orange'),
        (UPS_FAULT, 'UPS故障', 'red'),
        (MAINS_POWER_OUTAGE, '市电停电', 'purple'),
        (NATURAL_DISASTER, '自然灾害', 'brown'),
        (HUMAN_MISOPERATION, '人为误操作', 'pink'),
        (OTHER, '其他', 'gray'),
    ]


class PowerRectificationStatusChoices(ChoiceSet):
    key = 'OtnFault.rectification_status'

    NOT_REQUIRED = 'not_required'
    REQUIRED = 'required'
    DUPLICATE_MERGED = 'duplicate_merged'

    CHOICES = [
        (NOT_REQUIRED, '无需整改', 'gray'),
        (REQUIRED, '需要整改', 'orange'),
        (DUPLICATE_MERGED, '重复合并', 'blue'),
    ]


class PowerRectificationMeasureChoices(ChoiceSet):
    key = 'OtnFault.rectification_measures'

    REPLACE_POWER = 'replace_power'
    REPLACE_BATTERY = 'replace_battery'
    BATTERY_EXPANSION = 'battery_expansion'
    POWER_EXPANSION = 'power_expansion'
    ADD_MONITORING = 'add_monitoring'
    OTHER = 'other'

    CHOICES = [
        (REPLACE_POWER, '更换电源', 'red'),
        (REPLACE_BATTERY, '更换电池', 'orange'),
        (BATTERY_EXPANSION, '电池扩容', 'yellow'),
        (POWER_EXPANSION, '电源扩容', 'purple'),
        (ADD_MONITORING, '增加动环', 'cyan'),
        (OTHER, '其他', 'gray'),
    ]


class PowerRectificationSubjectChoices(ChoiceSet):
    key = 'OtnFault.rectification_subject'

    HEADQUARTERS = 'headquarters'
    SUBSIDIARY = 'subsidiary'
    EXTERNAL = 'external'

    CHOICES = [
        (HEADQUARTERS, '本部', 'blue'),
        (SUBSIDIARY, '子公司', 'green'),
        (EXTERNAL, '外单位', 'orange'),
    ]


class PowerRectificationProgressChoices(ChoiceSet):
    key = 'OtnFault.rectification_progress'

    NOT_STARTED = 'not_started'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    SUSPENDED = 'suspended'

    CHOICES = [
        (NOT_STARTED, '未实施', 'gray'),
        (IN_PROGRESS, '进行中', 'blue'),
        (COMPLETED, '已完成', 'green'),
        (SUSPENDED, '挂起', 'yellow'),
    ]


class PowerRecoveryModeChoices(ChoiceSet):
    key = 'OtnFault.power_recovery_mode'

    GENERATOR = 'generator_power'
    MAINS = 'mains_recovery'
    SWITCH_ON = 'switch_on_recovery'

    CHOICES = [
        (GENERATOR, '发电机供电', 'orange'),
        (MAINS, '市电恢复', 'green'),
        (SWITCH_ON, '合闸恢复', 'blue'),
    ]


class PowerMaintenanceModeChoices(ChoiceSet):
    key = 'OtnFault.power_maintenance_mode'

    OUTSOURCED = 'outsourced'
    COORDINATED = 'coordinated'
    SELF_MAINTAINED = 'self_maintained'
    FACTORY_MAINTENANCE = 'factory_maintenance'

    CHOICES = [
        (OUTSOURCED, '代维', 'blue'),
        (COORDINATED, '协调', 'green'),
        (SELF_MAINTAINED, '自维', 'purple'),
        (FACTORY_MAINTENANCE, '厂家维保', 'cyan'),
    ]


class PowerFaultPhenomenonChoices(ChoiceSet):
    key = 'OtnFault.power_fault_phenomenon'

    ALL_INTERRUPTED = 'all_interrupted'
    PARTIAL_INTERRUPTED = 'partial_interrupted'

    CHOICES = [
        (ALL_INTERRUPTED, '全中断', 'red'),
        (PARTIAL_INTERRUPTED, '部分中断', 'orange'),
    ]


class PowerFaultImpactChoices(ChoiceSet):
    key = 'OtnFault.power_fault_impact'

    HOSTED = 'hosted'
    NOT_HOSTED = 'not_hosted'

    CHOICES = [
        (HOSTED, '设备脱管', 'blue'),
        (NOT_HOSTED, '设备未脱管', 'gray'),
    ]


class CutoverReportStatusChoices(ChoiceSet):
    key = 'OtnFault.cutover_report_status'

    UNREPORTED = 'unreported'
    REPORTED = 'reported'

    CHOICES = [
        (UNREPORTED, '未报备', 'red'),
        (REPORTED, '已报备', 'green'),
    ]


class CutoverStatusChoices(ChoiceSet):
    key = 'CutoverTask.status'

    APPLYING = 'applying'
    PENDING_IMPLEMENTATION = 'pending_implementation'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

    CHOICES = [
        (APPLYING, '申请中', 'blue'),
        (PENDING_IMPLEMENTATION, '待实施', 'orange'),
        (COMPLETED, '已完成', 'green'),
        (CANCELLED, '被取消', 'gray'),
    ]


class CutoverTimeoutStatusChoices(ChoiceSet):
    key = 'CutoverTask.is_timeout'

    YES = 'yes'
    NO = 'no'
    PENDING = 'pending'

    CHOICES = [
        (YES, '是', 'red'),
        (NO, '否', 'green'),
        (PENDING, '待判定', 'gray'),
    ]


class CutoverResultChoices(ChoiceSet):
    key = 'CutoverTask.cutover_result'

    COMPLETED = 'completed'
    INCOMPLETE = 'incomplete'
    UNSATISFACTORY = 'unsatisfactory'

    CHOICES = [
        (COMPLETED, '完成', 'green'),
        (INCOMPLETE, '未完成', 'red'),
        (UNSATISFACTORY, '不理想', 'orange'),
    ]


class CutoverManagementUnitChoices(ChoiceSet):
    key = 'CutoverTask.management_unit'

    HEADQUARTERS = 'headquarters'
    ZHEJIANG = 'zhejiang'
    SHAANXI = 'shaanxi'
    SICHUAN = 'sichuan'
    INNER_MONGOLIA = 'inner_mongolia'
    JIANGXI = 'jiangxi'
    SHANDONG = 'shandong'
    THIRD_PARTY = 'third_party'

    CHOICES = [
        (HEADQUARTERS, '本部', 'blue'),
        (ZHEJIANG, '浙江子公司', 'green'),
        (SHAANXI, '陕西子公司', 'orange'),
        (SICHUAN, '四川子公司', 'purple'),
        (INNER_MONGOLIA, '内蒙古子公司', 'teal'),
        (JIANGXI, '江西子公司', 'yellow'),
        (SHANDONG, '山东子公司', 'cyan'),
        (THIRD_PARTY, '第三方', 'gray'),
    ]


class ResourceTypeChoices(ChoiceSet):
    key = 'OtnFault.resource_type'

    SELF_BUILT = 'self_built'
    COORDINATED = 'coordinated'
    LEASED = 'leased'

    CHOICES = [
        (SELF_BUILT, '自建光缆', 'green'),
        (COORDINATED, '协调资源', 'blue'),
        (LEASED, '租赁纤芯', 'purple'),
    ]


class ResourceOwnerChoices(ChoiceSet):
    key = 'OtnFault.resource_owner'

    HEADQUARTERS = 'headquarters'
    ZHEJIANG = 'zhejiang'
    SHAANXI = 'shaanxi'
    SICHUAN = 'sichuan'
    INNER_MONGOLIA = 'inner_mongolia'
    JIANGXI = 'jiangxi'
    SHANDONG = 'shandong'

    CHOICES = [
        (HEADQUARTERS, '本部', 'blue'),
        (ZHEJIANG, '浙江子公司', 'green'),
        (SHAANXI, '陕西子公司', 'orange'),
        (SICHUAN, '四川子公司', 'purple'),
        (INNER_MONGOLIA, '内蒙古子公司', 'teal'),
        (JIANGXI, '江西子公司', 'yellow'),
        (SHANDONG, '山东子公司', 'cyan'),
    ]


class CableRouteChoices(ChoiceSet):
    key = 'OtnFault.cable_route'

    HIGHWAY = 'highway'
    NON_HIGHWAY = 'non_highway'

    CHOICES = [
        (HIGHWAY, '高速公路', 'green'),
        (NON_HIGHWAY, '非高速', 'orange'),
    ]


class FaultStatusChoices(ChoiceSet):
    key = 'OtnFault.fault_status'

    PROCESSING = 'processing'
    TEMPORARY_RECOVERY = 'temporary_recovery'
    SUSPENDED = 'suspended'
    CLOSED = 'closed'

    CHOICES = [
        (PROCESSING, '处理中', 'red'),
        (TEMPORARY_RECOVERY, '临时恢复', 'blue'),
        (SUSPENDED, '延后处置', 'yellow'),
        (CLOSED, '已关闭', 'green'),
    ]


class CableBreakLocationChoices(ChoiceSet):
    key = 'OtnFault.cable_break_location'

    PIGTAIL = 'pigtail'
    LOCAL_CABLE = 'local_cable'
    LONG_HAUL_CABLE = 'long_haul_cable'

    CHOICES = [
        (PIGTAIL, '尾纤', 'yellow'),
        (LOCAL_CABLE, '出局缆', 'orange'),
        (LONG_HAUL_CABLE, '长途光缆', 'red'),
    ]


class RecoveryModeChoices(ChoiceSet):
    key = 'OtnFault.recovery_mode'

    EMERGENCY_GENERATION = 'emergency_generation'
    BATTERY_POWER = 'battery_power'
    UTILITY_POWER_RESTORED = 'utility_power_restored'
    ONSITE_HANDLING = 'onsite_handling'

    CHOICES = [
        (EMERGENCY_GENERATION, '应急发电', 'orange'),
        (BATTERY_POWER, '电池供电', 'yellow'),
        (UTILITY_POWER_RESTORED, '市电恢复', 'green'),
        (ONSITE_HANDLING, '现场处置', 'blue'),
    ]


class CutoverTask(NetBoxModel, ImageAttachmentsMixin):
    cutover_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='割接编号',
        blank=True,
        help_text='系统自动生成，格式为CYYYYNNNN'
    )
    status = models.CharField(
        max_length=32,
        choices=CutoverStatusChoices,
        default=CutoverStatusChoices.APPLYING,
        verbose_name='状态'
    )
    registered_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='登记时间'
    )
    registrant = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='registered_cutover_tasks',
        verbose_name='登记人'
    )
    planned_cutover_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='计划割接时间',
        help_text='列表筛选和排序使用的主计划时间。多次计划时间可记录在计划割接时间记录中。'
    )
    planned_cutover_times = models.JSONField(
        default=list,
        blank=True,
        verbose_name='计划割接时间记录'
    )
    province = models.ForeignKey(
        to='dcim.Region',
        on_delete=models.PROTECT,
        related_name='cutover_tasks',
        verbose_name='省份',
        blank=True,
        null=True
    )
    cutover_location = models.TextField(
        verbose_name='割接具体地点'
    )
    cutover_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='割接位置经度'
    )
    cutover_latitude = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='割接位置纬度'
    )
    interruption_location_a = models.ForeignKey(
        to=Site,
        on_delete=models.PROTECT,
        related_name='cutover_tasks_a',
        verbose_name='割接位置A端站点'
    )
    interruption_location = models.ManyToManyField(
        to=Site,
        related_name='cutover_tasks_z',
        verbose_name='割接影响Z端站点',
        blank=True
    )
    related_customers = models.JSONField(
        default=list,
        blank=True,
        verbose_name='关联用户'
    )
    cutover_reason = models.TextField(
        verbose_name='割接原因'
    )
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceTypeChoices,
        blank=True,
        verbose_name='光纤来源'
    )
    cable_route = models.CharField(
        max_length=20,
        choices=CableRouteChoices,
        blank=True,
        verbose_name='光缆路由属性'
    )
    resource_owner = models.CharField(
        max_length=30,
        choices=ResourceOwnerChoices,
        blank=True,
        verbose_name='资源所有者'
    )
    maintenance_mode = models.CharField(
        max_length=20,
        choices=MaintenanceModeChoices,
        blank=True,
        verbose_name='维护方式'
    )
    handling_unit = models.ForeignKey(
        to='netbox_contract.ServiceProvider',
        on_delete=models.PROTECT,
        related_name='handled_cutover_tasks',
        verbose_name='代维方/租赁方',
        blank=True,
        null=True
    )
    contract = models.ForeignKey(
        to='netbox_contract.Contract',
        on_delete=models.PROTECT,
        related_name='cutover_tasks',
        verbose_name='代维/租赁合同',
        blank=True,
        null=True
    )
    management_unit = models.CharField(
        max_length=30,
        choices=CutoverManagementUnitChoices,
        verbose_name='割接管理单位'
    )
    management_unit_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='割接管理单位名称'
    )
    implementation_unit = models.CharField(
        max_length=100,
        verbose_name='割接实施单位'
    )
    cutover_contact = models.CharField(
        max_length=100,
        verbose_name='割接联系人'
    )
    cutover_contact_phone = models.CharField(
        max_length=50,
        verbose_name='割接联系人电话'
    )
    customer_approval_detail = models.JSONField(
        default=list,
        blank=True,
        verbose_name='客户审核明细'
    )
    started_at = models.DateTimeField(blank=True, null=True, verbose_name='割接开始时间')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='割接完成时间')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='割接封包时间')
    is_timeout = models.CharField(
        max_length=20,
        choices=CutoverTimeoutStatusChoices,
        default=CutoverTimeoutStatusChoices.PENDING,
        verbose_name='割接是否超时'
    )
    timeout_reason = models.TextField(blank=True, verbose_name='超时原因')
    cutover_result = models.CharField(
        max_length=32,
        choices=CutoverResultChoices,
        blank=True,
        verbose_name='割接效果'
    )
    remaining_issues = models.TextField(blank=True, verbose_name='遗留问题')
    rectification_status = models.CharField(
        max_length=20,
        choices=PowerRectificationStatusChoices,
        blank=True,
        verbose_name='是否整改'
    )
    rectification_measures = ArrayField(
        models.CharField(max_length=30, choices=PowerRectificationMeasureChoices),
        blank=True,
        default=list,
        verbose_name='整改措施'
    )
    rectification_description = models.TextField(blank=True, verbose_name='措施描述')
    rectification_subject = models.CharField(
        max_length=20,
        choices=PowerRectificationSubjectChoices,
        blank=True,
        verbose_name='整改主体'
    )
    rectification_progress = models.CharField(
        max_length=20,
        choices=PowerRectificationProgressChoices,
        blank=True,
        verbose_name='整改进度'
    )
    planned_completion_time = models.DateTimeField(blank=True, null=True, verbose_name='计划完成时间')
    actual_completion_time = models.DateTimeField(blank=True, null=True, verbose_name='实际完成时间')
    rectification_completion_description = models.TextField(blank=True, verbose_name='整改完成情况描述')
    line_supervisor = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='supervised_cutover_tasks',
        verbose_name='线路主管',
        blank=True,
        null=True
    )
    planned_impact_minutes = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='预计影响时长（分钟）'
    )
    # remarks field removed
    tags = taggit.managers.TaggableManager(
        through='extras.TaggedItem',
        to='extras.Tag',
        blank=True
    )
    comments = models.TextField(blank=True, verbose_name='评论')

    class Meta:
        ordering = ('-registered_at', '-pk')
        verbose_name = '割接'
        verbose_name_plural = '割接'

    def __str__(self) -> str:
        return self.cutover_no

    def get_absolute_url(self) -> str:
        return reverse('plugins:netbox_otnfaults:cutovertask', args=[self.pk])

    def get_status_color(self) -> str | None:
        return CutoverStatusChoices.colors.get(self.status)

    def get_is_timeout_color(self) -> str | None:
        return CutoverTimeoutStatusChoices.colors.get(self.is_timeout)

    def get_cutover_result_color(self) -> str | None:
        return CutoverResultChoices.colors.get(self.cutover_result)

    @property
    def cutover_duration(self) -> str | None:
        if self.started_at:
            is_ongoing = not bool(self.completed_at)
            end_time = self.completed_at if self.completed_at else timezone.localtime()
            duration = end_time - self.started_at
            days = duration.days
            seconds = duration.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            total_hours = duration.total_seconds() / 3600
            ongoing_marker = " (未完成)" if is_ongoing else ""
            duration_text = _format_duration_units(days, hours, minutes, seconds)
            return f"{duration_text}（{total_hours:.2f}小时）{ongoing_marker}"
        return None

    def _normalize_json_list_fields(self) -> None:
        for field_name in ('planned_cutover_times', 'related_customers', 'customer_approval_detail'):
            if getattr(self, field_name) is None:
                setattr(self, field_name, [])

    def clean(self) -> None:
        self._normalize_json_list_fields()
        super().clean()
        errors: dict[str, str] = {}
        if self.is_timeout == CutoverTimeoutStatusChoices.YES and not self.timeout_reason:
            errors['timeout_reason'] = '割接超时时必须填写超时原因。'
        if self.status == CutoverStatusChoices.COMPLETED:
            if not self.completed_at:
                errors['completed_at'] = '割接完成时必须填写割接完成时间。'
            if not self.cutover_result:
                errors['cutover_result'] = '割接完成时必须填写割接效果。'
        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.cutover_no:
            super().save(*args, **kwargs)
            return

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                with transaction.atomic():
                    year = timezone.localdate().strftime('%Y')
                    prefix = f'C{year}'
                    last_cutover = (
                        CutoverTask.objects.select_for_update()
                        .filter(cutover_no__startswith=prefix)
                        .order_by('-cutover_no')
                        .first()
                    )
                    if last_cutover:
                        last_number = int(last_cutover.cutover_no[5:])
                        new_number = last_number + 1
                    else:
                        new_number = 1
                    self.cutover_no = f'{prefix}{new_number:04d}'

                    if kwargs.get('update_fields') is not None:
                        kwargs['update_fields'] = {
                            *kwargs['update_fields'],
                            'cutover_no',
                        }

                    super().save(*args, **kwargs)
                return
            except IntegrityError:
                self.cutover_no = ''
                if attempt == max_attempts - 1:
                    raise


class OtnFault(NetBoxModel, ImageAttachmentsMixin):
    fault_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='故障编号',
        help_text='系统自动生成，格式为FYYYYMMDDNNN',
        error_messages={
            'unique': '已存在相同编号的故障记录。'
        }
    )
    source_cutover_task = models.ForeignKey(
        to='CutoverTask',
        on_delete=models.SET_NULL,
        related_name='generated_faults',
        verbose_name='来源割接',
        blank=True,
        null=True,
    )
    duty_officer = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='otn_faults',
        verbose_name='值守人员'
    )
    interruption_location_a = models.ForeignKey(
        to=Site,
        on_delete=models.PROTECT,
        related_name='otn_faults_a',
        verbose_name='故障位置A端站点'
    )
    interruption_location = models.ManyToManyField(
        to=Site,
        related_name='otn_faults',
        verbose_name='故障位置Z端站点',
        blank=True
    )
    fault_occurrence_time = models.DateTimeField(
        verbose_name='故障起始时间'
    )
    fault_recovery_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='故障恢复时间'
    )
    
    fault_category = models.CharField(
        max_length=20,
        choices=FaultCategoryChoices,
        default=FaultCategoryChoices.FIBER_BREAK,
        verbose_name='故障分类',
    )
    power_fault_phenomenon = models.CharField(
        max_length=20,
        choices=PowerFaultPhenomenonChoices,
        blank=True,
        null=True,
        verbose_name='供电故障现象'
    )
    power_fault_impact = models.CharField(
        max_length=20,
        choices=PowerFaultImpactChoices,
        blank=True,
        null=True,
        verbose_name='影响情况'
    )
    
    # 一级原因选项
    INTERRUPTION_REASON_CHOICES = (
        # 光缆类故障（中断、劣化、抖动）共用的一级原因
        ('construction', '施工'),
        ('human_factor', '人为'),
        ('traffic_accident', '交通事故'),
        ('animal_damage', '动物破坏'),
        ('natural_disaster', '自然灾害'),
        ('fire', '火灾故障'),
        ('unknown', '无法查明'),
        ('cable_rectification', '光缆整改'),
        # 空调故障专用的一级原因
        ('ac_refrigerant', '空调缺氟'),
        ('ac_mainunit', '主机故障'),
        ('ac_overload', '过载保护'),
        ('ac_outdoor_blocked', '室外机堵塞'),
        ('ac_no_autostart', '来电不自启'),
        # 设备故障专用的一级原因
        ('optical_module', '光模块故障'),
        ('software_fault', '软件故障'),
        ('branch_card', '支路板卡'),
        ('line_card', '线路板卡'),
        ('main_control_card', '主控板卡'),
        ('cross_card', '交叉板卡'),
        ('auxiliary_card', '辅助板卡'),
        ('power_card', '电源板卡'),
        ('optical_layer_card', '光层单板'),
        ('chassis_fault', '机框故障'),
        ('misoperation_device', '误操作'),
        ('device_relocation', '设备搬迁'),
        ('other_device', '其他'),
        # 供电故障专用的一级原因
        ('ac_fault_power', '交流故障'),
        ('power_equipment_fault', '电源设备故障'),
        ('misoperation_power', '误操作'),
        ('natural_disaster_power', '自然灾害'),
        ('unknown_power', '不详'),
        ('power_equipment_rectification', '电源设备整改'),
    )
    
    # 二级原因选项
    INTERRUPTION_REASON_DETAIL_CHOICES = (
        # 施工二级原因
        ('municipal_construction', '市政施工'),
        ('greening_construction', '绿化施工'),
        ('expansion_construction', '改扩建施工'),
        ('piling_construction', '打桩施工'),
        ('ramp_construction', '匝道施工'),
        ('station_renovation', '站内翻修'),
        ('room_renovation', '机房装修'),
        # 人为二级原因
        ('sabotage', '人为破坏'),
        ('misoperation', '误操作'),
        # 交通事故二级原因
        ('vehicle_collision', '车辆撞断或刮断'),
        ('vehicle_fire', '车辆起火'),
        # 动物破坏二级原因
        ('bird_peck', '鸟啄'),
        ('rodent_damage', '鼠害'),
        ('dog_bite', '狗咬'),
        ('ant_damage', '蚂蚁'),
        # 自然灾害二级原因
        ('flood', '洪水'),
        ('earthquake', '地震'),
        ('storm', '暴风'),
        ('mudslide', '泥石流'),
        ('road_collapse', '路面塌方'),
        # 火灾故障二级原因
        ('burning_straw', '烧荒'),
        ('well_fire', '管井起火'),
        ('cigarette', '烟头'),
        # 线路整改二级原因
        ('planned_reporting', '计划报备'),
        ('unplanned_reporting', '非报备'),
        # 供电故障二级原因
        ('room_power_test', '机房供电测试'),
        ('grid_power_maintenance', '国网供电检修'),
        ('breaker_trip', '空开跳闸'),
        ('ups_fault', 'UPS故障'),
        ('mains_power_outage', '市电停电'),
        ('natural_disaster_power_detail', '自然灾害'),
        ('manual_misoperation', '人为误操作'),
        ('other_power', '其他'),
        ('switching_power_fault', '开关电源故障'),
        ('rectifier_module_fault', '整流模块故障'),
        ('human_caused', '人为导致'),
        ('power_flood', '洪水'),
        ('power_rainstorm', '暴雨'),
        ('power_lightning', '雷击'),
        ('power_relocation', '搬迁'),
        ('switching_power_rectification', '开关电源整改'),
        ('battery_rectification', '电池整改'),
        ('owner_unit_rectification', '业主单位整改'),
    )
    
    # 故障分类 -> 一级原因映射
    CATEGORY_TO_REASON_MAP = {
        'fiber_break': ['construction', 'human_factor', 'traffic_accident', 
                        'animal_damage', 'natural_disaster', 'fire', 
                        'unknown', 'cable_rectification'],
        'fiber_degradation': ['construction', 'human_factor', 'traffic_accident', 
                              'animal_damage', 'natural_disaster', 'fire', 
                              'unknown', 'cable_rectification'],
        'fiber_jitter': ['construction', 'human_factor', 'traffic_accident', 
                         'animal_damage', 'natural_disaster', 'fire', 
                         'unknown', 'cable_rectification'],
        'ac_fault': ['ac_refrigerant', 'ac_mainunit', 'ac_overload', 
                     'ac_outdoor_blocked', 'ac_no_autostart'],
        'device_fault': ['optical_module', 'software_fault', 'branch_card', 
                         'line_card', 'main_control_card', 'cross_card', 
                         'auxiliary_card', 'power_card', 'optical_layer_card',
                         'chassis_fault', 'misoperation_device', 'device_relocation', 
                         'other_device'],
        'power_fault': ['ac_fault_power', 'power_equipment_fault',
                        'misoperation_power', 'natural_disaster_power',
                        'unknown_power', 'power_equipment_rectification'],
    }
    
    # 一级原因 -> 二级原因映射
    REASON_TO_DETAIL_MAP = {
        'construction': ['municipal_construction', 'greening_construction', 
                         'expansion_construction', 'piling_construction', 
                         'ramp_construction', 'station_renovation', 'room_renovation'],
        'human_factor': ['sabotage', 'misoperation'],
        'traffic_accident': ['vehicle_collision', 'vehicle_fire'],
        'animal_damage': ['bird_peck', 'rodent_damage', 'dog_bite', 'ant_damage'],
        'natural_disaster': ['flood', 'earthquake', 'storm', 'mudslide', 'road_collapse'],
        'fire': ['burning_straw', 'well_fire', 'cigarette'],
        # 以下一级原因没有二级原因
        'unknown': [],
        'cable_rectification': ['planned_reporting', 'unplanned_reporting'],
        'ac_refrigerant': [],
        'ac_mainunit': [],
        'ac_overload': [],
        'ac_outdoor_blocked': [],
        'ac_no_autostart': [],
        # 设备故障的一级原因（无二级原因）
        'optical_module': [],
        'software_fault': [],
        'branch_card': [],
        'line_card': [],
        'main_control_card': [],
        'cross_card': [],
        'auxiliary_card': [],
        'power_card': [],
        'optical_layer_card': [],
        'chassis_fault': [],
        'misoperation_device': [],
        'device_relocation': [],
        'other_device': [],
        # 供电故障的一级原因
        'ac_fault_power': ['room_power_test', 'grid_power_maintenance',
                           'breaker_trip', 'ups_fault', 'mains_power_outage',
                           'natural_disaster_power_detail', 'manual_misoperation',
                           'other_power'],
        'power_equipment_fault': ['switching_power_fault', 'rectifier_module_fault'],
        'misoperation_power': ['human_caused'],
        'natural_disaster_power': ['power_flood', 'power_rainstorm', 'power_lightning'],
        'unknown_power': [],
        'power_equipment_rectification': ['power_relocation', 'grid_power_maintenance',
                                          'switching_power_rectification',
                                          'battery_rectification',
                                          'owner_unit_rectification',
                                          'mains_power_outage'],
    }
    
    interruption_reason = models.CharField(
        max_length=30,
        choices=INTERRUPTION_REASON_CHOICES,
        verbose_name='一级原因',
        blank=True,
        null=True
    )
    
    interruption_reason_detail = models.CharField(
        max_length=30,
        choices=INTERRUPTION_REASON_DETAIL_CHOICES,
        verbose_name='二级原因',
        blank=True,
        null=True
    )
    cutover_report_status = models.CharField(
        max_length=20,
        choices=CutoverReportStatusChoices,
        verbose_name='割接报备情况',
        blank=True,
        null=True
    )
    cutover_report_time = models.DateTimeField(
        verbose_name='报备时间',
        blank=True,
        null=True
    )

    @property
    def is_fiber_fault(self):
        """判断是否为光缆相关故障（中断、劣化、抖动）"""
        return self.fault_category in [
            FaultCategoryChoices.FIBER_BREAK, 
            FaultCategoryChoices.FIBER_DEGRADATION, 
            FaultCategoryChoices.FIBER_JITTER
        ]

    @property
    def is_power_fault(self):
        """判断是否为供电故障"""
        return self.fault_category == FaultCategoryChoices.POWER_FAULT

    fault_details = models.TextField(
        verbose_name='故障详情和处理过程',
        blank=True,
        null=True
    )
    interruption_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='故障位置经度',
        help_text='GPS坐标（十进制格式, xx.yyyyyy）'
    )
    interruption_latitude = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='故障位置纬度',
        help_text='GPS坐标（十进制格式, xx.yyyyyy）'
    )
    
    # 新增字段
    # 1) 省份，引用netbox组织机构中的地区
    province = models.ForeignKey(
        to='dcim.Region',
        on_delete=models.PROTECT,
        related_name='otn_faults',
        verbose_name='省份',
        blank=True,
        null=True
    )
    
    # 2) 紧急程度，为选择型字段，分为高、中、低，按照颜色显示，高为红色，中为橙色，低为黄色，默认值为低，必填
    urgency = models.CharField(
        max_length=10,
        choices=UrgencyChoices,
        default=UrgencyChoices.LOW,
        verbose_name='紧急程度'
    )
    
    # 3) 第一报障来源，为选择性字段，分为客户报障（含未来网络报障）、网管自查、动环报警、其他来源，可空
    FIRST_REPORT_SOURCE_CHOICES = (
        ('customer_support', '客户报障（含未来网络报障）'),
        ('nms_self_check', '网管自查'),
        ('env_alarm', '动环报警'),
        ('other', '其他来源'),
    )
    first_report_source = models.CharField(
        max_length=20,
        choices=FIRST_REPORT_SOURCE_CHOICES,
        blank=True,
        null=True,
        verbose_name='第一报障来源'
    )
    
    # 5) 线路主管，为选择性字段，选择系统用户
    line_manager = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='managed_otn_faults',
        verbose_name='线路主管',
        blank=True,
        null=True
    )
    
    # 5.1) 运维主管，为可多选的用户字段
    operations_manager = models.ManyToManyField(
        to=settings.AUTH_USER_MODEL,
        related_name='managed_otn_faults_operations',
        verbose_name='运维主管',
        blank=True
    )
    
    # 6) 维护方式，为选择型字段，分为代维、协调、自维
    maintenance_mode = models.CharField(
        max_length=20,
        choices=MaintenanceModeChoices,
        blank=True,
        null=True,
        verbose_name='维护方式'
    )
    
    # 7) 处理单位，引用netbox-contract中的服务提供商
    handling_unit = models.ForeignKey(
        to='netbox_contract.ServiceProvider',
        on_delete=models.PROTECT,
        related_name='handled_otn_faults',
        verbose_name='代维方/租赁方',
        blank=True,
        null=True
    )

    # 7.1) 代维合同，引用netbox-contract中的合同
    contract = models.ForeignKey(
        to='netbox_contract.Contract',
        on_delete=models.PROTECT,
        related_name='otn_faults',
        verbose_name='代维/租赁合同',
        blank=True,
        null=True
    )
    
    # 8) 处理派发时间，格式为2024/11/17  10:23:34，包括列表，详细信息，编辑页
    dispatch_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='处理派发时间'
    )
    
    # 9) 维修出发时间，格式为2024/11/17  10:23:34，包括列表，详细信息，编辑页
    departure_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='维修出发时间'
    )
    
    # 10) 到达现场时间，格式为2024/11/17  10:23:34，包括列表，详细信息，编辑页
    arrival_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='到达现场时间'
    )
    
    # 11) 故障修复时间，格式为2024/11/17  10:23:34，包括列表，详细信息，编辑页
    repair_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='故障修复时间'
    )
    
    # 12) 修复用时，自动计算字段，使用故障修复时间-处理派发时间，格式为9.65小时
    # 这是一个计算属性，不在数据库中存储
    
    # 13) 规定时间内完成修复，布尔型字段
    timeout = models.BooleanField(
        default=True,
        verbose_name='规定时间内完成修复'
    )
    
    # 14) 超时原因，文本型字段
    timeout_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='超时原因'
    )
    
    # 15) 资源类型，为选择性字段，分为自建光缆、协调资源、租赁纤芯三类
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceTypeChoices,
        blank=True,
        null=True,
        verbose_name='光纤来源'
    )
    
    # 15.1) 资源所有者
    resource_owner = models.CharField(
        max_length=20,
        choices=ResourceOwnerChoices,
        blank=True,
        null=True,
        verbose_name='资源所有者'
    )
    
    # 16) 光缆路由属性，为选择性字段，分为高速公路、非高速两类，默认值为高速公路，可空
    cable_route = models.CharField(
        max_length=20,
        choices=CableRouteChoices,
        default=CableRouteChoices.HIGHWAY,
        blank=True,
        null=True,
        verbose_name='光缆路由属性'
    )
    
    # 17) 故障处理人，文本字段
    handler = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='故障处理人',
        help_text='用于填写处理故障的本公司内部员工、代维单位处理人员或协调纤芯处理方的具体人员或单位名称'
    )
    
    # 18) 处理状态，为选择型字段，分为处理中、临时恢复、延后处置、关闭
    fault_status = models.CharField(
        max_length=20,
        choices=FaultStatusChoices,
        default=FaultStatusChoices.PROCESSING,
        blank=True,
        null=True,
        verbose_name='处理状态'
    )

    is_suspended = models.BooleanField(
        default=False,
        verbose_name='挂起',
        help_text='该故障为挂起故障，不计入故障时长统计'
    )
    
    # 19) 光缆中断部位，为选择型字段，分为尾纤、出局缆、长途光缆
    cable_break_location = models.CharField(
        max_length=20,
        choices=CableBreakLocationChoices,
        blank=True,
        null=True,
        verbose_name='光缆中断部位'
    )
    
    # 20) 应对措施，保存在 recovery_mode 字段中，支持多选。
    recovery_mode = ArrayField(
        base_field=models.CharField(
            max_length=40,
            choices=RecoveryModeChoices,
        ),
        blank=True,
        default=list,
        verbose_name='应对措施'
    )
    
    # 21) 封包完成时间，格式为2024/11/17  10:23:34
    closure_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='封包完成时间'
    )
    
    # 供电故障补充信息
    power_data_type = models.CharField(
        max_length=20,
        choices=PowerDataTypeChoices,
        blank=True,
        null=True,
        verbose_name='供电设备提供方'
    )
    root_cause_analysis = ArrayField(
        base_field=models.CharField(
            max_length=40,
            choices=PowerRootCauseAnalysisChoices,
        ),
        blank=True,
        default=list,
        verbose_name='根因分析'
    )
    rectification_status = models.CharField(
        max_length=20,
        choices=PowerRectificationStatusChoices,
        blank=True,
        null=True,
        verbose_name='是否整改'
    )
    rectification_measures = ArrayField(
        base_field=models.CharField(
            max_length=40,
            choices=PowerRectificationMeasureChoices,
        ),
        blank=True,
        default=list,
        verbose_name='整改措施'
    )
    rectification_description = models.TextField(
        blank=True,
        verbose_name='措施描述'
    )
    rectification_subject = models.CharField(
        max_length=20,
        choices=PowerRectificationSubjectChoices,
        blank=True,
        null=True,
        verbose_name='整改主体'
    )
    rectification_progress = models.CharField(
        max_length=20,
        choices=PowerRectificationProgressChoices,
        blank=True,
        null=True,
        verbose_name='整改进度'
    )
    planned_completion_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='计划完成时间'
    )
    actual_completion_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='实际完成时间'
    )
    rectification_completion_description = models.TextField(
        blank=True,
        verbose_name='整改完成情况描述'
    )
    power_recovery_mode = models.CharField(
        max_length=30,
        choices=PowerRecoveryModeChoices,
        blank=True,
        null=True,
        verbose_name='恢复方式'
    )
    power_maintenance_mode = models.CharField(
        max_length=20,
        choices=PowerMaintenanceModeChoices,
        blank=True,
        null=True,
        verbose_name='供电维护方式'
    )
    
    # 故障复核信息
    manager_reviewed = models.BooleanField(
        default=False,
        verbose_name='线路主管复核'
    )
    manager_reviewer = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='线路主管复核人'
    )
    manager_review_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='线路主管复核时间'
    )
    noc_reviewed = models.BooleanField(
        default=False,
        verbose_name='网管人员复核'
    )
    noc_reviewer = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='网管人员复核人'
    )
    noc_review_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='网管人员复核时间'
    )
    
    tags = taggit.managers.TaggableManager(
        through='extras.TaggedItem',
        to='extras.Tag',
        blank=True
    )
    comments = models.TextField(blank=True, verbose_name='评论')

    class Meta:
        ordering = ('-fault_occurrence_time',)
        indexes = [
            GinIndex(fields=['recovery_mode']),
            GinIndex(fields=['root_cause_analysis']),
            GinIndex(fields=['rectification_measures']),
        ]
        verbose_name = '故障'
        verbose_name_plural = '故障'

    def __str__(self):
        parts = [self.fault_number]
        
        # 添加故障类型
        if self.fault_category:
            parts.append(self.get_fault_category_display())
            
        # 添加A端站点
        if self.interruption_location_a:
            parts.append(f"{self.interruption_location_a}")
            
        # 添加Z端站点信息
        if self.pk:
            z_count = self.interruption_location.count()
            if z_count > 0:
                first_z = self.interruption_location.first()
                parts.append(f"-> {first_z}")
                if z_count > 1:
                    parts.append(f"(+{z_count-1}站点)")
                    
        return " ".join(parts)

    def get_absolute_url(self):
        return reverse('plugins:netbox_otnfaults:otnfault', args=[self.pk])

    @property
    def formatted_fault_number(self) -> str:
        fault_number = self.fault_number or ""
        if len(fault_number) >= 9 and fault_number.startswith("F") and fault_number[1:9].isdigit():
            year = fault_number[1:5]
            month = str(int(fault_number[5:7]))
            day = str(int(fault_number[7:9]))
            return f"{fault_number}（{year}年{month}月{day}日）"
        return fault_number

    def get_fault_category_color(self):
        return FaultCategoryChoices.colors.get(self.fault_category)

    def _format_duration(self, start, end):
        if start:
            is_ongoing = not bool(end)
            end_time = end if end else timezone.localtime()
            duration = end_time - start
            days = duration.days
            seconds = duration.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            
            total_hours = duration.total_seconds() / 3600
            
            ongoing_marker = " (未恢复)" if is_ongoing else ""
            duration_text = _format_duration_units(days, hours, minutes, secs)
            return f"{duration_text}（{total_hours:.2f}小时）{ongoing_marker}"
        return None

    @property
    def fault_duration(self):
        return self._format_duration(self.fault_occurrence_time, self.fault_recovery_time)

    @property
    def processing_duration(self):
        """处理历时：从处理派发到故障恢复之间的时间"""
        return self._format_duration(self.dispatch_time, self.fault_recovery_time)

    @property
    def fault_duration_info(self):
        """
        返回故障历时的结构化信息，用于可视化渲染
        返回: {
            'total_hours': float,       # 总小时数
            'display': str,             # 简短显示文本（如 "2.35小时"）
            'full_text': str,           # 完整文本（如 "2小时21分0秒"）
            'color': str,               # 颜色类名
            'percentage': float         # 进度百分比（0-100）
        }
        """
        if self.fault_occurrence_time:
            is_ongoing = not bool(self.fault_recovery_time)
            end_time = self.fault_recovery_time if self.fault_recovery_time else timezone.localtime()
            duration = end_time - self.fault_occurrence_time
            total_seconds = duration.total_seconds()
            total_hours = total_seconds / 3600
            
            days = duration.days
            seconds = duration.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            
            # 颜色编码规则
            if total_hours < 0.5:
                color = 'green'
            elif total_hours < 1:
                color = 'yellow'
            elif total_hours < 4:
                color = 'orange'
            else:
                color = 'red'
            
            # 进度百分比（最大8小时）
            max_hours = 8
            percentage = min(100, (total_hours / max_hours) * 100)
            
            ongoing_marker_display = " (持续中)" if is_ongoing else ""
            ongoing_marker_full = " [未恢复，计算至当前时间]" if is_ongoing else ""
            
            return {
                'total_hours': total_hours,
                'display': f"{total_hours:.2f}小时{ongoing_marker_display}",
                'full_text': f"{_format_duration_units(days, hours, minutes, secs)}{ongoing_marker_full}",
                'color': color,
                'percentage': percentage,
            }
        return None

    @property
    def timeline_data(self):
        """
        返回时间轴需要的数据
        """
        def format_td(td):
            if td is None:
                return ""
            total_seconds = int(td.total_seconds())
            if total_seconds < 0:
                return "0秒"
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            parts = []
            if days > 0:
                parts.append(f"{days}天")
            if hours > 0:
                parts.append(f"{hours}小时")
            if minutes > 0:
                parts.append(f"{minutes}分")
            if seconds > 0 or not parts:
                parts.append(f"{seconds}秒")
                
            return "".join(parts)

        # 基础时间点（前5个为必选）
        times = [
            self.fault_occurrence_time,
            self.dispatch_time,
            self.departure_time,
            self.arrival_time,
            self.fault_recovery_time
        ]
        labels = ['故障起始', '处理派发', '维修出发', '到达现场', '故障恢复']

        # 仅当故障类型为光纤类时，才在末尾显示封包完成时间（不参与历时计算）
        if self.is_fiber_fault:
            times.append(self.closure_time)
            labels.append('封包完成时间')
        
        steps = []
        for i in range(len(times)):
            t = times[i]
            active = t is not None
            
            # Django 时区处理
            dt_local = timezone.localtime(t) if t else None
            time_str = dt_local.strftime('%H:%M:%S') if dt_local else ''
            highlight_date = ''
            highlight_time = time_str

            # 首尾高亮节点单独拆分日期行与时间行，避免依赖空白占位在宽屏下失效
            if dt_local and self.fault_occurrence_time and i in (0, 4):
                occur_local = timezone.localtime(self.fault_occurrence_time)
                if i == 0 or dt_local.date() != occur_local.date():
                    highlight_date = f"{dt_local.month}月{dt_local.day}日"
            
            # 历时计算仅限前 4 个间隔（即截止到“故障恢复”前）
            duration_to_next = ""
            if i < 4 and t and times[i+1]:
                duration_to_next = format_td(times[i+1] - t)
                
            steps.append({
                'label': labels[i],
                'time': time_str,
                'highlight_date': highlight_date,
                'highlight_time': highlight_time,
                'active': active,
                'duration_to_next': duration_to_next,
                'is_connected_to_next': i < len(times) - 1 and times[i+1] is not None
            })
            
        # 总处理时长 & 日期
        start_t = self.fault_occurrence_time
        end_t = self.fault_recovery_time
        
        date_str = timezone.localtime(start_t).strftime('%Y-%m-%d') if start_t else ''
        calc_end_t = end_t if end_t else timezone.localtime()
        
        total_duration = ""
        if start_t:
            total_duration = format_td(calc_end_t - start_t)
            if not end_t:
                total_duration += " (未恢复)"

        return {
            'date': date_str,
            'total_duration': total_duration,
            'steps': steps
        }

    def get_urgency_color(self):
        """获取紧急程度的颜色"""
        return UrgencyChoices.colors.get(self.urgency)

    def get_maintenance_mode_color(self):
        """获取维护方式的颜色"""
        return MaintenanceModeChoices.colors.get(self.maintenance_mode)

    def get_cable_break_location_color(self):
        """获取光缆中断部位的颜色"""
        return CableBreakLocationChoices.colors.get(self.cable_break_location)

    def get_recovery_mode_values(self) -> list[str]:
        """返回 recovery_mode 中保存的应对措施值。"""
        if not self.recovery_mode:
            return []
        if isinstance(self.recovery_mode, str):
            return [value.strip() for value in self.recovery_mode.split(',') if value.strip()]
        return [value for value in self.recovery_mode if value]

    def get_recovery_mode_display(self) -> str:
        """显示多个应对措施。"""
        labels = {
            value: label
            for value, label, *_ in RecoveryModeChoices.CHOICES
        }
        return '、'.join(
            labels.get(value, value)
            for value in self.get_recovery_mode_values()
        )

    def get_recovery_mode_color(self) -> str | None:
        """获取应对措施的颜色；多选时使用首个选项颜色。"""
        values = self.get_recovery_mode_values()
        if not values:
            return None
        return RecoveryModeChoices.colors.get(values[0])

    def get_resource_type_color(self):
        """获取资源类型的颜色"""
        return ResourceTypeChoices.colors.get(self.resource_type)

    def get_resource_owner_color(self):
        """获取资源所有者的颜色"""
        return ResourceOwnerChoices.colors.get(self.resource_owner)

    def get_cable_route_color(self):
        """获取光缆路由属性的颜色"""
        return CableRouteChoices.colors.get(self.cable_route)

    def get_fault_status_color(self):
        """获取处理状态的颜色"""
        return FaultStatusChoices.colors.get(self.fault_status)

    def get_power_data_type_color(self):
        """获取供电设备提供方的颜色"""
        return PowerDataTypeChoices.colors.get(self.power_data_type)

    def get_root_cause_analysis_values(self) -> list[str]:
        """返回 root_cause_analysis 中保存的根因分析值。"""
        if not self.root_cause_analysis:
            return []
        if isinstance(self.root_cause_analysis, str):
            return [value.strip() for value in self.root_cause_analysis.split(',') if value.strip()]
        return [value for value in self.root_cause_analysis if value]

    def get_root_cause_analysis_display(self) -> str:
        """显示多个根因分析。"""
        labels = {
            value: label
            for value, label, *_ in PowerRootCauseAnalysisChoices.CHOICES
        }
        return '、'.join(
            labels.get(value, value)
            for value in self.get_root_cause_analysis_values()
        )

    def get_root_cause_analysis_color(self) -> str | None:
        """获取根因分析的颜色；多选时使用首个选项颜色。"""
        values = self.get_root_cause_analysis_values()
        if not values:
            return None
        return PowerRootCauseAnalysisChoices.colors.get(values[0])

    def get_rectification_status_color(self):
        """获取是否整改的颜色"""
        return PowerRectificationStatusChoices.colors.get(self.rectification_status)

    def get_rectification_measures_values(self) -> list[str]:
        """返回 rectification_measures 中保存的整改措施值。"""
        if not self.rectification_measures:
            return []
        if isinstance(self.rectification_measures, str):
            return [value.strip() for value in self.rectification_measures.split(',') if value.strip()]
        return [value for value in self.rectification_measures if value]

    def get_rectification_measures_display(self) -> str:
        """显示多个整改措施。"""
        labels = {
            value: label
            for value, label, *_ in PowerRectificationMeasureChoices.CHOICES
        }
        return '、'.join(
            labels.get(value, value)
            for value in self.get_rectification_measures_values()
        )

    def get_rectification_measures_color(self) -> str | None:
        """获取整改措施的颜色；多选时使用首个选项颜色。"""
        values = self.get_rectification_measures_values()
        if not values:
            return None
        return PowerRectificationMeasureChoices.colors.get(values[0])

    def get_rectification_subject_color(self):
        """获取整改主体的颜色"""
        return PowerRectificationSubjectChoices.colors.get(self.rectification_subject)

    def get_rectification_progress_color(self):
        """获取整改进度的颜色"""
        return PowerRectificationProgressChoices.colors.get(self.rectification_progress)

    def get_power_recovery_mode_color(self):
        """获取供电恢复方式的颜色"""
        return PowerRecoveryModeChoices.colors.get(self.power_recovery_mode)

    def get_power_maintenance_mode_color(self):
        """获取供电维护方式的颜色"""
        return PowerMaintenanceModeChoices.colors.get(self.power_maintenance_mode)

    def get_power_fault_phenomenon_color(self):
        """获取供电故障现象的颜色"""
        return PowerFaultPhenomenonChoices.colors.get(self.power_fault_phenomenon)

    def get_power_fault_impact_color(self):
        """获取影响情况的颜色"""
        return PowerFaultImpactChoices.colors.get(self.power_fault_impact)

    def clean(self):
        super().clean()
        
        # 现场处理链路时间顺序验证
        sequence_time_fields = [
            ('fault_occurrence_time', '故障起始时间'),
            ('dispatch_time', '处理派发时间'),
            ('departure_time', '维修出发时间'),
            ('arrival_time', '到达现场时间'),
        ]
        
        # 收集现场处理链路中的非空时间字段
        times = []
        for field_name, field_label in sequence_time_fields:
            time_value = getattr(self, field_name)
            if time_value:
                times.append((field_name, field_label, time_value))
        
        errors = {}

        # 检查现场处理链路时间顺序：后续时间不应早于前面的任何时间
        for i in range(len(times)):
            for j in range(i + 1, len(times)):
                field_name_i, field_label_i, time_i = times[i]
                field_name_j, field_label_j, time_j = times[j]
                
                if time_j < time_i:
                    if field_name_j not in errors:
                        errors[field_name_j] = []
                    errors[field_name_j].append(f'{field_label_j}需晚于{field_label_i}')

        # 故障恢复时间只需晚于故障起始时间，无需晚于派发/出发/到场时间
        if self.fault_recovery_time:
            field_name_j = 'fault_recovery_time'
            time_j = self.fault_recovery_time
            if self.fault_occurrence_time and time_j < self.fault_occurrence_time:
                if field_name_j not in errors:
                    errors[field_name_j] = []
                errors[field_name_j].append('故障恢复时间需晚于故障起始时间')
        
        # 如果有错误，抛出 ValidationError 但将错误关联到具体字段
        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.fault_status == FaultStatusChoices.SUSPENDED:
            self.is_suspended = True
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = {
                    *kwargs['update_fields'],
                    'is_suspended',
                }

        if self.fault_number:
            super().save(*args, **kwargs)
            return

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                with transaction.atomic():
                    today = timezone.localdate().strftime('%Y%m%d')
                    prefix = f'F{today}'
                    last_fault = (
                        OtnFault.objects.select_for_update()
                        .filter(fault_number__startswith=prefix)
                        .order_by('-fault_number')
                        .first()
                    )
                    if last_fault:
                        last_number = int(last_fault.fault_number[9:])
                        new_number = last_number + 1
                    else:
                        new_number = 1
                    self.fault_number = f'{prefix}{new_number:03d}'

                    if kwargs.get('update_fields') is not None:
                        kwargs['update_fields'] = {
                            *kwargs['update_fields'],
                            'fault_number',
                        }

                    super().save(*args, **kwargs)
                return
            except IntegrityError:
                self.fault_number = ''
                if attempt == max_attempts - 1:
                    raise

class ServiceTypeChoices(ChoiceSet):
    key = 'OtnFaultImpact.service_type'

    BARE_FIBER = 'bare_fiber'
    CIRCUIT = 'circuit'

    CHOICES = [
        (BARE_FIBER, '裸纤业务', 'blue'),
        (CIRCUIT, '电路业务', 'green'),
    ]


class BusinessImpactChoices(ChoiceSet):
    key = 'OtnFaultImpact.business_impact'

    INTERRUPTED = 'interrupted'
    NOT_INTERRUPTED = 'not_interrupted'

    CHOICES = [
        (INTERRUPTED, '业务中断', 'red'),
        (NOT_INTERRUPTED, '业务未中断', 'blue'),
    ]


class OtnFaultImpact(NetBoxModel, ImageAttachmentsMixin):
    otn_fault = models.ForeignKey(
        to=OtnFault,
        on_delete=models.CASCADE,
        related_name='impacts',
        verbose_name='直接故障'
    )
    service_type = models.CharField(
        max_length=20,
        choices=ServiceTypeChoices,
        default=ServiceTypeChoices.BARE_FIBER,
        verbose_name='业务类型'
    )
    bare_fiber_service = models.ForeignKey(
        to='BareFiberService',
        on_delete=models.PROTECT,
        related_name='fault_impacts',
        verbose_name='裸纤业务',
        blank=True,
        null=True
    )
    circuit_service = models.ForeignKey(
        to='CircuitService',
        on_delete=models.PROTECT,
        related_name='fault_impacts',
        verbose_name='电路业务',
        blank=True,
        null=True
    )
    service_site_a = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.SET_NULL,
        related_name='impact_service_site_a',
        verbose_name='业务站点A',
        blank=True,
        null=True,
        help_text='仅裸纤业务时使用'
    )
    service_site_z = models.ManyToManyField(
        to='dcim.Site',
        related_name='impact_service_site_z',
        verbose_name='业务站点Z',
        blank=True,
        help_text='仅裸纤业务时使用，可选择多个Z端站点'
    )
    business_impact = models.CharField(
        max_length=20,
        choices=BusinessImpactChoices,
        default=BusinessImpactChoices.INTERRUPTED,
        verbose_name='业务影响'
    )
    service_interruption_time = models.DateTimeField(
        verbose_name='业务故障时间'
    )
    service_recovery_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='业务恢复时间'
    )
    secondary_faults = models.ManyToManyField(
        to=OtnFault,
        related_name='secondary_impacts',
        verbose_name='其他关联故障',
        blank=True
    )
    tags = taggit.managers.TaggableManager(
        through='extras.TaggedItem',
        to='extras.Tag',
        blank=True
    )
    comments = models.TextField(blank=True, verbose_name='评论')

    class Meta:
        ordering = ('-service_interruption_time',)
        verbose_name = '故障影响业务'
        verbose_name_plural = '故障影响业务'
        constraints = [
            models.UniqueConstraint(
                fields=['otn_fault', 'bare_fiber_service'],
                condition=models.Q(bare_fiber_service__isnull=False),
                name='unique_otn_fault_bare_fiber',
                violation_error_message='此故障下已经有该裸纤业务，不能重复添加。'
            ),
            models.UniqueConstraint(
                fields=['otn_fault', 'circuit_service'],
                condition=models.Q(circuit_service__isnull=False),
                name='unique_otn_fault_circuit',
                violation_error_message='此故障下已经有该电路业务，不能重复添加。'
            )
        ]

    def __str__(self):
        service = self.bare_fiber_service if self.service_type == ServiceTypeChoices.BARE_FIBER else self.circuit_service
        return f"{self.otn_fault} - {service}"

    def clean(self):
        super().clean()
        
        if self.service_type == ServiceTypeChoices.BARE_FIBER and not self.bare_fiber_service:
            raise ValidationError({'bare_fiber_service': '选择裸纤业务类型时必须指定具体的裸纤业务。'})
            
        if self.service_type == ServiceTypeChoices.CIRCUIT and not self.circuit_service:
            raise ValidationError({'circuit_service': '选择电路业务类型时必须指定具体的电路业务。'})
            
        # 清除未选中类型的数据
        if self.service_type == ServiceTypeChoices.BARE_FIBER:
            self.circuit_service = None
        elif self.service_type == ServiceTypeChoices.CIRCUIT:
            self.bare_fiber_service = None
            self.service_site_a = None
            # service_site_z 是 M2M 字段，需要在 save 之后清除
            
        # 防止重复添加相同的业务
        if hasattr(self, 'otn_fault_id') and self.otn_fault_id:
            if self.service_type == ServiceTypeChoices.BARE_FIBER and self.bare_fiber_service:
                qs = OtnFaultImpact.objects.filter(otn_fault_id=self.otn_fault_id, bare_fiber_service=self.bare_fiber_service)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                if qs.exists():
                    raise ValidationError({'bare_fiber_service': '此故障下已经有该裸纤业务，不能重复添加。'})
            elif self.service_type == ServiceTypeChoices.CIRCUIT and self.circuit_service:
                qs = OtnFaultImpact.objects.filter(otn_fault_id=self.otn_fault_id, circuit_service=self.circuit_service)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                if qs.exists():
                    raise ValidationError({'circuit_service': '此故障下已经有该电路业务，不能重复添加。'})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # 电路业务时清除 M2M 站点数据
        if self.service_type == ServiceTypeChoices.CIRCUIT:
            self.service_site_z.clear()

    def get_service_type_color(self):
        return ServiceTypeChoices.colors.get(self.service_type)

    def get_business_impact_color(self):
        return BusinessImpactChoices.colors.get(self.business_impact)

    def get_absolute_url(self):
        return reverse('plugins:netbox_otnfaults:otnfaultimpact', args=[self.pk])

    @property
    def service_duration(self):
        if self.service_interruption_time:
            is_ongoing = not bool(self.service_recovery_time)
            end_time = self.service_recovery_time if self.service_recovery_time else timezone.localtime()
            duration = end_time - self.service_interruption_time
            days = duration.days
            seconds = duration.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            
            # 计算总小时数（包括天数转换的小时数）
            total_seconds = duration.total_seconds()
            total_hours = total_seconds / 3600
            
            ongoing_marker = " (未恢复)" if is_ongoing else ""
            duration_text = _format_duration_units(days, hours, minutes, seconds)
            return f"{duration_text}（{total_hours:.2f}小时）{ongoing_marker}"
        return None

    @property
    def service_duration_hours(self):
        """返回业务中断历时的小时数，格式为 xx.xx"""
        if self.service_interruption_time:
            is_ongoing = not bool(self.service_recovery_time)
            end_time = self.service_recovery_time if self.service_recovery_time else timezone.localtime()
            duration = end_time - self.service_interruption_time
            total_hours = duration.total_seconds() / 3600
            ongoing_marker = " (未恢复)" if is_ongoing else ""
            return f"{total_hours:.2f}{ongoing_marker}"
        return None

    @property
    def service_duration_info(self):
        """
        返回业务中断历时的结构化信息，用于可视化渲染
        """
        if self.service_interruption_time:
            is_ongoing = not bool(self.service_recovery_time)
            end_time = self.service_recovery_time if self.service_recovery_time else timezone.localtime()
            duration = end_time - self.service_interruption_time
            total_seconds = duration.total_seconds()
            total_hours = total_seconds / 3600
            
            days = duration.days
            seconds = duration.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            
            # 颜色编码规则
            if total_hours < 0.5:
                color = 'green'
            elif total_hours < 1:
                color = 'yellow'
            elif total_hours < 4:
                color = 'orange'
            else:
                color = 'red'
            
            # 进度百分比（最大8小时）
            max_hours = 8
            percentage = min(100, (total_hours / max_hours) * 100)
            
            ongoing_marker_display = " (持续中)" if is_ongoing else ""
            ongoing_marker_full = " [未恢复，计算至当前时间]" if is_ongoing else ""
            
            return {
                'total_hours': total_hours,
                'display': f"{total_hours:.2f}小时{ongoing_marker_display}",
                'full_text': f"{_format_duration_units(days, hours, minutes, secs)}{ongoing_marker_full}",
                'color': color,
                'percentage': percentage,
            }
        return None


class PathGroupSiteRoleChoices(ChoiceSet):
    key = 'OtnPathGroupSite.role'

    OLA = 'ola'
    OADM = 'oadm'
    OTM = 'otm'

    CHOICES = [
        (OLA, '光放站 (OLA)', 'teal'),
        (OADM, '光分插复用站 (OADM)', 'blue'),
        (OTM, '终端站 (OTM)', 'red'),
    ]


class OtnPathGroup(NetBoxModel):
    """路径组模型，用于对光缆路径进行分组管理"""
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='名称',
        error_messages={
            'unique': '已存在相同名称的路径组。'
        }
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='缩写',
        error_messages={
            'unique': '已存在相同缩写的路径组。'
        }
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='描述'
    )
    paths = models.ManyToManyField(
        to='OtnPath',
        related_name='groups',
        blank=True,
        verbose_name='包含路径'
    )
    sites = models.ManyToManyField(
        to=Site,
        through='OtnPathGroupSite',
        related_name='path_groups',
        blank=True,
        verbose_name='包含站点'
    )
    comments = models.TextField(
        blank=True,
        verbose_name='评论'
    )

    class Meta:
        ordering = ('name',)
        verbose_name = '路径组'
        verbose_name_plural = '路径组'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_otnfaults:otnpathgroup', args=[self.pk])


class OtnPathGroupSite(NetBoxModel):
    """路径组与站点的中间关系模型，包含站点角色和排序"""
    path_group = models.ForeignKey(
        to=OtnPathGroup,
        on_delete=models.CASCADE,
        related_name='group_sites'
    )
    site = models.ForeignKey(
        to=Site,
        on_delete=models.CASCADE,
        related_name='+'
    )
    role = models.CharField(
        max_length=20,
        choices=PathGroupSiteRoleChoices,
        verbose_name='角色'
    )
    position = models.PositiveIntegerField(
        default=0,
        verbose_name='排序'
    )
    tags = taggit.managers.TaggableManager(
        through='extras.TaggedItem',
        to='extras.Tag',
        blank=True
    )
    comments = models.TextField(blank=True, verbose_name='评论')

    class Meta:
        ordering = ('path_group', 'position', 'pk')
        constraints = [
            models.UniqueConstraint(
                fields=['path_group', 'site'],
                name='unique_path_group_site',
                violation_error_message='该路径组已包含选定的站点。'
            )
        ]
        verbose_name = '路径组站点'
        verbose_name_plural = '路径组站点'

    def __str__(self):
        return f"{self.path_group} - {self.site} ({self.get_role_display()})"

    def get_absolute_url(self):
        return reverse('plugins:netbox_otnfaults:otnpathgroupsite_edit', args=[self.pk])

    def get_role_color(self):
        """获取角色的颜色"""
        return PathGroupSiteRoleChoices.colors.get(self.role)


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


class OtnPath(NetBoxModel):
    name = models.CharField(
        max_length=100,
        verbose_name='名称'
    )
    cable_type = models.CharField(
        max_length=20,
        choices=CableTypeChoices,
        verbose_name='光缆类型'
    )
    site_a = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.PROTECT,
        related_name='otn_paths_a',
        verbose_name='A端站点'
    )
    site_z = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.PROTECT,
        related_name='otn_paths_z',
        verbose_name='Z端站点'
    )
    geometry = models.JSONField(
        blank=True,
        null=True,
        verbose_name='空间几何数据',
        help_text='符合 GeoJSON LineString 格式的坐标数组'
    )
    calculated_length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='长度',
        help_text='单位: 公里 (km)'
    )
    description = models.TextField(
        blank=True,
        verbose_name='描述'
    )
    comments = models.TextField(blank=True, verbose_name='评论')

    class Meta:
        ordering = ('name',)
        verbose_name = '光缆路径'
        verbose_name_plural = '光缆路径'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_otnfaults:otnpath', args=[self.pk])

    def get_cable_type_color(self):
        return CableTypeChoices.colors.get(self.cable_type)


class OtnMapPreference(NetBoxModel):
    """Per-user style preferences for unified map modes."""

    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='otn_map_preferences',
        verbose_name='用户'
    )
    map_mode = models.CharField(max_length=64, verbose_name='地图模式')
    style_config = models.JSONField(default=dict, blank=True, verbose_name='样式配置')
    schema_version = models.PositiveSmallIntegerField(default=1)
    tags = models.JSONField(default=list, blank=True)
    comments = models.TextField(blank=True, verbose_name='评论')

    class Meta:
        ordering = ('user', 'map_mode')
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'map_mode'),
                name='unique_otn_map_preference_user_mode',
            )
        ]
        verbose_name = '地图偏好'
        verbose_name_plural = '地图偏好'

    def __str__(self) -> str:
        return f"{self.user} / {self.map_mode}"

    def save(self, *args, **kwargs) -> None:
        if self.tags is None:
            self.tags = []
        if self.custom_field_data is None:
            self.custom_field_data = {}
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse('plugins:netbox_otnfaults:otnfault_map_globe')


class BareFiberService(NetBoxModel):
    """裸纤业务模型"""
    name = models.CharField(
        max_length=200,
        verbose_name='名称'
    )
    slug = models.CharField(
        max_length=50,
        verbose_name='缩写'
    )
    tenant_group = models.ForeignKey(
        to='tenancy.TenantGroup',
        on_delete=models.PROTECT,
        related_name='bare_fiber_services',
        verbose_name='租户组',
        blank=True,
        null=True
    )
    business_manager = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='managed_bare_fiber_services',
        verbose_name='业务主管',
        blank=True,
        null=True
    )
    billing_start_time = models.DateField(
        blank=True,
        null=True,
        verbose_name='计费起始时间'
    )
    billing_end_time = models.DateField(
        blank=True,
        null=True,
        verbose_name='计费结束时间'
    )
    tags = taggit.managers.TaggableManager(
        through='extras.TaggedItem',
        to='extras.Tag',
        blank=True
    )
    comments = models.TextField(blank=True, verbose_name='评论')

    def clean(self):
        super().clean()
        if self.billing_start_time and self.billing_end_time:
            if self.billing_end_time < self.billing_start_time:
                raise ValidationError({
                    'billing_end_time': '计费结束时间需晚于计费起始时间'
                })

    class Meta:
        ordering = ('name',)
        verbose_name = '裸纤业务'
        verbose_name_plural = '裸纤业务'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_otnfaults:barefiberservice', args=[self.pk])


class ServiceGroupChoices(ChoiceSet):
    key = 'CircuitService.service_group'

    MARKET = 'market'
    MINISTRY_BACKBONE = 'ministry_backbone'
    BEIJING_METRO = 'beijing_metro'
    INDUSTRY_NETWORK = 'industry_network'
    INDUSTRY_SERVICE = 'industry_service'
    TRANSPORT_INDUSTRY = 'transport_industry'
    FINANCE_LINE = 'finance_line'
    MARITIME_CORE = 'maritime_core'
    MARITIME_INTEGRATED_OM = 'maritime_int_om'
    MARITIME_OTHER = 'maritime_other'
    ETC_MINISTRY_PROVINCE = 'etc_ministry'
    ETC_STATION = 'etc_station'
    ETC_DUAL_ACTIVE = 'etc_dual_active'
    INDUSTRY_NETWORK_RUIJIE = 'industry_ruijie'
    TRAVELSKY_PRODUCTION = 'travelsky_prod'
    TRAVELSKY_OFFICE = 'travelsky_office'
    TRAVELSKY_JIAXING_SHANGHAI = 'travelsky_jxsh'
    JINHANG_CORE = 'jinhang_core'
    JINHANG_AGGREGATION = 'jinhang_agg'
    JINHANG_BACKUP = 'jinhang_backup'
    JINHANG_OTHER = 'jinhang_other'
    LANXUN_100G = 'lanxun_100g'
    LANXUN_NETWORK_10G = 'lanxun_net_10g'
    LANXUN_NETWORK_100G = 'lanxun_net_100g'
    JINSHAN = 'jinshan'
    CHANGHANG_SERVICE = 'changhang_srv'
    CHANGHANG_BACKUP = 'changhang_backup'

    CHOICES = [
        (MINISTRY_BACKBONE, '部省主线', 'blue'),
        (BEIJING_METRO, '北京城域网', 'blue'),
        (INDUSTRY_NETWORK, '行业专网', 'blue'),
        (INDUSTRY_SERVICE, '行业服务', 'blue'),
        (TRANSPORT_INDUSTRY, '交通行业', 'blue'),
        (MARKET, '市场', 'green'),
        (FINANCE_LINE, '金融专线', 'green'),
        (MARITIME_CORE, '海事核心网', 'yellow'),
        (MARITIME_INTEGRATED_OM, '海事一体化运维', 'yellow'),
        (MARITIME_OTHER, '海事其他', 'yellow'),
        (ETC_MINISTRY_PROVINCE, 'ETC部省', 'orange'),
        (ETC_STATION, 'ETC部站', 'orange'),
        (ETC_DUAL_ACTIVE, 'ETC双活', 'orange'),
        (INDUSTRY_NETWORK_RUIJIE, '行业专网锐捷', 'red'),
        (TRAVELSKY_PRODUCTION, '航信生产', 'purple'),
        (TRAVELSKY_OFFICE, '航信办公', 'purple'),
        (TRAVELSKY_JIAXING_SHANGHAI, '航信嘉兴上海', 'purple'),
        (JINHANG_CORE, '金航核心', 'brown'),
        (JINHANG_AGGREGATION, '金航汇聚', 'brown'),
        (JINHANG_BACKUP, '金航备线', 'brown'),
        (JINHANG_OTHER, '金航其他', 'brown'),
        (LANXUN_100G, '缆讯100G', 'black'),
        (LANXUN_NETWORK_10G, '缆讯组网-10G', 'black'),
        (LANXUN_NETWORK_100G, '缆讯组网-百G', 'black'),
        (JINSHAN, '金山', 'white'),
        (CHANGHANG_SERVICE, '长航业务', 'green'),
        (CHANGHANG_BACKUP, '长航备线', 'green'),
    ]


class BusinessCategoryChoices(ChoiceSet):
    key = 'CircuitService.business_category'

    MINISTRY_PROVINCE_TRANSPORT = '01_ministry_province_transport'
    COMMERCIAL_OTHER = '02_commercial_other'
    MARITIME_SERVICE = '03_maritime_service'
    ROAD_NETWORK_SERVICE = '04_road_network_service'
    LEGACY_RUIJIE_SERVICE = '05_legacy_ruijie_service'
    TRAVELSKY = '06_travelsky'
    JINHANG = '07_jinhang'
    LANXUN = '08_lanxun'
    COMMERCIAL_100G = '09_commercial_100g'
    CHANGHANG = '10_changhang'
    MINISTRY_ORGAN = '11_ministry_organ'

    CHOICES = [
        (MINISTRY_PROVINCE_TRANSPORT, '部省传输', 'blue'),
        (COMMERCIAL_OTHER, '商业其他', 'gray'),
        (MARITIME_SERVICE, '海事业务', 'teal'),
        (ROAD_NETWORK_SERVICE, '路网业务', 'indigo'),
        (LEGACY_RUIJIE_SERVICE, '老锐捷业务', 'purple'),
        (TRAVELSKY, '中航信', 'cyan'),
        (JINHANG, '金航', 'green'),
        (LANXUN, '缆讯', 'orange'),
        (COMMERCIAL_100G, '商业百G', 'red'),
        (CHANGHANG, '长航', 'yellow'),
        (MINISTRY_ORGAN, '部机关', 'dark'),
    ]


class CircuitOperationStatusChoices(ChoiceSet):
    key = 'CircuitService.operation_status'

    PENDING = 'pending'
    CONFIGURED = 'configured'
    OPERATING = 'operating'
    TESTING = 'testing'
    CLOSED = 'closed'

    CHOICES = [
        (PENDING, '待开通', 'orange'),
        (CONFIGURED, '已配置', 'cyan'),
        (OPERATING, '运营中', 'green'),
        (TESTING, '测试中', 'purple'),
        (CLOSED, '已关闭', 'red'),
    ]


class SLALevelChoices(ChoiceSet):
    key = 'CircuitService.sla_level'

    SLA_728 = '728'
    SLA_729 = '729'
    SLA_730 = '730'
    SLA_731 = '731'

    CHOICES = [
        (SLA_728, '728', 'blue'),
        (SLA_729, '729', 'blue'),
        (SLA_730, '730', 'blue'),
        (SLA_731, '731', 'blue'),
    ]


class CircuitService(NetBoxModel):
    """?????????"""
    EXTRA_FIELD_DEFINITIONS: tuple[tuple[str, str], ...] = (
        ('request_number', '需求单号'),
        ('request_attachment', '需求单扫描件（上传）'),
        ('configuration_completed_date', '配置完成日期'),
        ('configuration_person', '配置人'),
        ('service_test_start_date', '服务测试开始日期'),
        ('service_open_time', '服务开通时间'),
        ('opening_order_attachment', '历年开通单附件（上传）'),
        ('service_test_end_time', '服务测试结束时间'),
        ('service_end_time', '服务结束时间'),
        ('resource_recycle_time', '资源回收时间（专线关闭）'),
        ('resource_recycle_person', '资源回收实施人'),
        ('change_number', '变更单号'),
        ('change_date', '变更日期'),
        ('change_person', '变更实施人'),
        ('change_order_attachment', '历次变更单（上传）'),
        ('interconnection_info', '互联信息'),
        ('carrier_system', '承载系统（多选）'),
        ('contracting_party', '签约主体'),
        ('customer_object', '客户对象'),
        ('customer_a_end', '客户A端'),
        ('trunk_a_site', '干线A端-站点'),
        ('trunk_a_site_attribute', '干线A端-站点属性'),
        ('trunk_a_ne', '干线A端-A网元'),
        ('trunk_a_board', '干线A端-A单板'),
        ('trunk_a_port', '干线A端-A端口'),
        ('customer_z_end', '客户Z端'),
        ('trunk_z_site', '干线Z端-站点'),
        ('trunk_z_site_attribute', '干线Z端-站点属性'),
        ('trunk_z_ne', '干线Z端-Z网元'),
        ('trunk_z_board', '干线Z端-Z单板'),
        ('trunk_z_port', '干线Z端-Z端口'),
        ('charge_attribute', '收费属性'),
        ('sales_person', '销售人员'),
        ('contract_open_time', '合同开通时间'),
        ('contract_end_time', '合同结束时间'),
        ('contract_number', '合同编号'),
        ('contract_name', '合同名称'),
        ('project_approval_number', '立项项目编号'),
        ('project_name', '项目名称'),
        ('execution_exception', '执行是否异常'),
        ('execution_exception_reason', '执行异常原因'),
    )
    SERVICE_GROUP_CATEGORY_MAP = {
        ServiceGroupChoices.MINISTRY_BACKBONE: BusinessCategoryChoices.MINISTRY_PROVINCE_TRANSPORT,
        ServiceGroupChoices.BEIJING_METRO: BusinessCategoryChoices.MINISTRY_PROVINCE_TRANSPORT,
        ServiceGroupChoices.INDUSTRY_NETWORK: BusinessCategoryChoices.MINISTRY_PROVINCE_TRANSPORT,
        ServiceGroupChoices.INDUSTRY_SERVICE: BusinessCategoryChoices.MINISTRY_PROVINCE_TRANSPORT,
        ServiceGroupChoices.TRANSPORT_INDUSTRY: BusinessCategoryChoices.MINISTRY_PROVINCE_TRANSPORT,
        ServiceGroupChoices.MARKET: BusinessCategoryChoices.COMMERCIAL_OTHER,
        ServiceGroupChoices.FINANCE_LINE: BusinessCategoryChoices.COMMERCIAL_OTHER,
        ServiceGroupChoices.MARITIME_CORE: BusinessCategoryChoices.MARITIME_SERVICE,
        ServiceGroupChoices.MARITIME_INTEGRATED_OM: BusinessCategoryChoices.MARITIME_SERVICE,
        ServiceGroupChoices.MARITIME_OTHER: BusinessCategoryChoices.MARITIME_SERVICE,
        ServiceGroupChoices.ETC_MINISTRY_PROVINCE: BusinessCategoryChoices.ROAD_NETWORK_SERVICE,
        ServiceGroupChoices.ETC_STATION: BusinessCategoryChoices.ROAD_NETWORK_SERVICE,
        ServiceGroupChoices.ETC_DUAL_ACTIVE: BusinessCategoryChoices.ROAD_NETWORK_SERVICE,
        ServiceGroupChoices.INDUSTRY_NETWORK_RUIJIE: BusinessCategoryChoices.LEGACY_RUIJIE_SERVICE,
        ServiceGroupChoices.TRAVELSKY_PRODUCTION: BusinessCategoryChoices.TRAVELSKY,
        ServiceGroupChoices.TRAVELSKY_OFFICE: BusinessCategoryChoices.TRAVELSKY,
        ServiceGroupChoices.TRAVELSKY_JIAXING_SHANGHAI: BusinessCategoryChoices.TRAVELSKY,
        ServiceGroupChoices.JINHANG_CORE: BusinessCategoryChoices.JINHANG,
        ServiceGroupChoices.JINHANG_AGGREGATION: BusinessCategoryChoices.JINHANG,
        ServiceGroupChoices.JINHANG_BACKUP: BusinessCategoryChoices.JINHANG,
        ServiceGroupChoices.JINHANG_OTHER: BusinessCategoryChoices.JINHANG,
        ServiceGroupChoices.LANXUN_100G: BusinessCategoryChoices.LANXUN,
        ServiceGroupChoices.LANXUN_NETWORK_10G: BusinessCategoryChoices.LANXUN,
        ServiceGroupChoices.LANXUN_NETWORK_100G: BusinessCategoryChoices.LANXUN,
        ServiceGroupChoices.JINSHAN: BusinessCategoryChoices.COMMERCIAL_100G,
        ServiceGroupChoices.CHANGHANG_SERVICE: BusinessCategoryChoices.CHANGHANG,
        ServiceGroupChoices.CHANGHANG_BACKUP: BusinessCategoryChoices.CHANGHANG,
    }
    special_line_name = models.CharField(
        max_length=100,
        verbose_name='专线名称'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='电路编号'
    )
    slug = models.CharField(
        max_length=50,
        verbose_name='缩写'
    )
    service_group = models.CharField(
        max_length=20,
        choices=ServiceGroupChoices,
        verbose_name='业务组',
        blank=True
    )
    bandwidth = models.PositiveIntegerField(
        verbose_name='带宽(Mbps)',
        blank=True,
        null=True
    )
    business_category = models.CharField(
        max_length=40,
        choices=BusinessCategoryChoices,
        verbose_name='业务门类',
        blank=True
    )
    business_manager = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='managed_circuit_services',
        verbose_name='业务主管',
        blank=True,
        null=True
    )
    is_external_business = models.BooleanField(
        default=False,
        verbose_name='对部服务'
    )
    ring_protection = models.BooleanField(
        default=False,
        verbose_name='环网保护'
    )
    operation_status = models.CharField(
        max_length=20,
        choices=CircuitOperationStatusChoices,
        default=CircuitOperationStatusChoices.OPERATING,
        verbose_name='运行状态',
        blank=True
    )
    sla_level = models.CharField(
        max_length=10,
        choices=SLALevelChoices,
        verbose_name='SLA等级',
        blank=True,
        null=True
    )
    billing_start_time = models.DateField(
        blank=True,
        null=True,
        verbose_name='计费起始时间'
    )
    billing_end_time = models.DateField(
        blank=True,
        null=True,
        verbose_name='计费结束时间'
    )
    extra_fields = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='扩展信息'
    )
    tags = taggit.managers.TaggableManager(
        through='extras.TaggedItem',
        to='extras.Tag',
        blank=True
    )
    comments = models.TextField(blank=True, verbose_name='评论')

    def clean(self):
        super().clean()
        if self.billing_start_time and self.billing_end_time:
            if self.billing_end_time < self.billing_start_time:
                raise ValidationError({
                    'billing_end_time': '???????????????????????'
                })
        if self.service_group and self.business_category:
            expected_category = self.SERVICE_GROUP_CATEGORY_MAP.get(self.service_group)
            if expected_category and expected_category != self.business_category:
                raise ValidationError({
                    'service_group': '??????????????'
                })

    class Meta:
        ordering = ('business_category', 'service_group', 'special_line_name')
        verbose_name = '电路业务'
        verbose_name_plural = '电路业务'

    def __str__(self):
        service_group = self.get_service_group_display() if self.service_group else ''
        if service_group:
            return f"{service_group} / {self.special_line_name}"
        return self.special_line_name

    def get_absolute_url(self):
        return reverse('plugins:netbox_otnfaults:circuitservice', args=[self.pk])

    def get_service_group_color(self):
        return ServiceGroupChoices.colors.get(self.service_group)


    def get_business_category_color(self):
        return BusinessCategoryChoices.colors.get(self.business_category)

    def get_operation_status_color(self):
        return CircuitOperationStatusChoices.colors.get(self.operation_status)

    def get_sla_level_color(self):
        return SLALevelChoices.colors.get(self.sla_level)

    @property
    def extra_field_items(self) -> list[dict[str, str]]:
        values = self.extra_fields or {}
        return [
            {
                'key': key,
                'label': label,
                'value': str(values.get(key, '') or ''),
            }
            for key, label in self.EXTRA_FIELD_DEFINITIONS
        ]


class CutoverImpact(NetBoxModel, ImageAttachmentsMixin):
    """割接影响业务模型 — 记录割接任务关联的受影响裸纤/电路业务"""
    cutover_task = models.ForeignKey(
        to='CutoverTask',
        on_delete=models.CASCADE,
        related_name='impacts',
        verbose_name='割接任务'
    )
    service_type = models.CharField(
        max_length=20,
        choices=ServiceTypeChoices,
        default=ServiceTypeChoices.BARE_FIBER,
        verbose_name='业务类型'
    )
    bare_fiber_service = models.ForeignKey(
        to='BareFiberService',
        on_delete=models.PROTECT,
        related_name='cutover_impacts',
        verbose_name='裸纤业务',
        blank=True,
        null=True
    )
    circuit_service = models.ForeignKey(
        to='CircuitService',
        on_delete=models.PROTECT,
        related_name='cutover_impacts',
        verbose_name='电路业务',
        blank=True,
        null=True
    )
    service_site_a = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.SET_NULL,
        related_name='cutover_impact_service_site_a',
        verbose_name='业务站点A',
        blank=True,
        null=True,
        help_text='仅裸纤业务时使用'
    )
    service_site_z = models.ManyToManyField(
        to='dcim.Site',
        related_name='cutover_impact_service_site_z',
        verbose_name='业务站点Z',
        blank=True,
        help_text='仅裸纤业务时使用，可选择多个Z端站点'
    )
    business_impact = models.CharField(
        max_length=20,
        choices=BusinessImpactChoices,
        default=BusinessImpactChoices.INTERRUPTED,
        verbose_name='业务影响'
    )
    service_interruption_time = models.DateTimeField(
        verbose_name='业务中断时间'
    )
    service_recovery_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='业务恢复时间'
    )

    tags = taggit.managers.TaggableManager(
        through='extras.TaggedItem',
        to='extras.Tag',
        blank=True
    )
    comments = models.TextField(blank=True, verbose_name='评论')

    class Meta:
        ordering = ('-service_interruption_time',)
        verbose_name = '割接影响业务'
        verbose_name_plural = '割接影响业务'
        constraints = [
            models.UniqueConstraint(
                fields=['cutover_task', 'bare_fiber_service'],
                condition=models.Q(bare_fiber_service__isnull=False),
                name='unique_cutover_bare_fiber',
                violation_error_message='此割接任务下已经有该裸纤业务，不能重复添加。'
            ),
            models.UniqueConstraint(
                fields=['cutover_task', 'circuit_service'],
                condition=models.Q(circuit_service__isnull=False),
                name='unique_cutover_circuit',
                violation_error_message='此割接任务下已经有该电路业务，不能重复添加。'
            )
        ]

    def __str__(self) -> str:
        service = self.bare_fiber_service if self.service_type == ServiceTypeChoices.BARE_FIBER else self.circuit_service
        return f"{self.cutover_task} - {service}"

    def clean(self) -> None:
        super().clean()

        if self.service_type == ServiceTypeChoices.BARE_FIBER and not self.bare_fiber_service:
            raise ValidationError({'bare_fiber_service': '选择裸纤业务类型时必须指定具体的裸纤业务。'})

        if self.service_type == ServiceTypeChoices.CIRCUIT and not self.circuit_service:
            raise ValidationError({'circuit_service': '选择电路业务类型时必须指定具体的电路业务。'})

        # 清除未选中类型的数据
        if self.service_type == ServiceTypeChoices.BARE_FIBER:
            self.circuit_service = None
        elif self.service_type == ServiceTypeChoices.CIRCUIT:
            self.bare_fiber_service = None
            self.service_site_a = None
            # service_site_z 是 M2M 字段，需要在 save 之后清除

        # 防止重复添加相同的业务
        if hasattr(self, 'cutover_task_id') and self.cutover_task_id:
            if self.service_type == ServiceTypeChoices.BARE_FIBER and self.bare_fiber_service:
                qs = CutoverImpact.objects.filter(cutover_task_id=self.cutover_task_id, bare_fiber_service=self.bare_fiber_service)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                if qs.exists():
                    raise ValidationError({'bare_fiber_service': '此割接任务下已经有该裸纤业务，不能重复添加。'})
            elif self.service_type == ServiceTypeChoices.CIRCUIT and self.circuit_service:
                qs = CutoverImpact.objects.filter(cutover_task_id=self.cutover_task_id, circuit_service=self.circuit_service)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                if qs.exists():
                    raise ValidationError({'circuit_service': '此割接任务下已经有该电路业务，不能重复添加。'})

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        # 电路业务时清除 M2M 站点数据
        if self.service_type == ServiceTypeChoices.CIRCUIT:
            self.service_site_z.clear()

    def get_service_type_color(self) -> str | None:
        return ServiceTypeChoices.colors.get(self.service_type)

    def get_business_impact_color(self) -> str | None:
        return BusinessImpactChoices.colors.get(self.business_impact)

    def get_absolute_url(self) -> str:
        return reverse('plugins:netbox_otnfaults:cutoverimpact', args=[self.pk])

    @property
    def service_duration(self) -> str | None:
        if self.service_interruption_time:
            is_ongoing = not bool(self.service_recovery_time)
            end_time = self.service_recovery_time if self.service_recovery_time else timezone.localtime()
            duration = end_time - self.service_interruption_time
            days = duration.days
            seconds = duration.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            total_seconds = duration.total_seconds()
            total_hours = total_seconds / 3600
            ongoing_marker = " (未恢复)" if is_ongoing else ""
            duration_text = _format_duration_units(days, hours, minutes, seconds)
            return f"{duration_text}（{total_hours:.2f}小时）{ongoing_marker}"
        return None

    @property
    def service_duration_hours(self) -> str | None:
        """返回业务中断历时的小时数，格式为 xx.xx"""
        if self.service_interruption_time:
            is_ongoing = not bool(self.service_recovery_time)
            end_time = self.service_recovery_time if self.service_recovery_time else timezone.localtime()
            duration = end_time - self.service_interruption_time
            total_hours = duration.total_seconds() / 3600
            ongoing_marker = " (未恢复)" if is_ongoing else ""
            return f"{total_hours:.2f}{ongoing_marker}"
        return None

    @property
    def service_duration_info(self) -> dict[str, Any] | None:
        """返回业务中断历时的结构化信息，用于可视化渲染"""
        if self.service_interruption_time:
            is_ongoing = not bool(self.service_recovery_time)
            end_time = self.service_recovery_time if self.service_recovery_time else timezone.localtime()
            duration = end_time - self.service_interruption_time
            total_seconds = duration.total_seconds()
            total_hours = total_seconds / 3600

            days = duration.days
            seconds = duration.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60

            if total_hours < 0.5:
                color = 'green'
            elif total_hours < 1:
                color = 'yellow'
            elif total_hours < 4:
                color = 'orange'
            else:
                color = 'red'

            max_hours = 8
            percentage = min(100, (total_hours / max_hours) * 100)

            ongoing_marker_display = " (持续中)" if is_ongoing else ""
            ongoing_marker_full = " [未恢复，计算至当前时间]" if is_ongoing else ""

            return {
                'total_hours': total_hours,
                'display': f"{total_hours:.2f}小时{ongoing_marker_display}",
                'full_text': f"{_format_duration_units(days, hours, minutes, secs)}{ongoing_marker_full}",
                'color': color,
                'percentage': percentage,
            }
        return None


class HeavyDuty(NetBoxModel):
    """重要保障信息模型"""
    name = models.CharField(
        max_length=200,
        verbose_name='重保标题'
    )
    start_time = models.DateTimeField(
        verbose_name='开始时间'
    )
    end_time = models.DateTimeField(
        verbose_name='结束时间'
    )
    description = models.TextField(
        verbose_name='重保描述/通知'
    )
    comments = models.TextField(
        blank=True,
        verbose_name='评论'
    )
    sites = models.ManyToManyField(
        to='dcim.Site',
        blank=True,
        related_name='heavy_duties',
        verbose_name='保障站点'
    )
    circuit_services = models.ManyToManyField(
        to='CircuitService',
        blank=True,
        related_name='heavy_duties',
        verbose_name='保障电路'
    )
    bare_fiber_services = models.ManyToManyField(
        to='BareFiberService',
        blank=True,
        related_name='heavy_duties',
        verbose_name='保障裸纤'
    )

    class Meta:
        ordering = ('-start_time', '-pk')
        verbose_name = '重要保障'
        verbose_name_plural = '重要保障'

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse('plugins:netbox_otnfaults:heavyduty', args=[self.pk])

    def clean(self) -> None:
        super().clean()
        if self.start_time and self.end_time:
            if self.end_time < self.start_time:
                raise ValidationError({
                    'end_time': '结束时间需晚于开始时间。'
                })

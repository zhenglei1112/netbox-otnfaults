from django.db import models
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


class FaultCategoryChoices(ChoiceSet):
    key = 'OtnFault.fault_category'

    CATEGORY_POWER = 'power'
    CATEGORY_FIBER = 'fiber'
    CATEGORY_PIGTAIL = 'pigtail'
    CATEGORY_DEVICE = 'device'
    CATEGORY_OTHER = 'other'


    CHOICES = [
        (CATEGORY_POWER, '电力故障', 'orange'),
        (CATEGORY_FIBER, '光缆故障', 'red'),
        (CATEGORY_PIGTAIL, '空调故障', 'blue'),
        (CATEGORY_DEVICE, '设备故障', 'green'),
        (CATEGORY_OTHER, '其他故障', 'gray'),
    ]


class UrgencyChoices(ChoiceSet):
    key = 'OtnFault.urgency'

    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'

    CHOICES = [
        (HIGH, '高', 'red'),
        (MEDIUM, '中', 'orange'),
        (LOW, '低', 'yellow'),
    ]


class MaintenanceModeChoices(ChoiceSet):
    key = 'OtnFault.maintenance_mode'

    OUTSOURCED = 'outsourced'
    COORDINATED = 'coordinated'
    SELF_MAINTAINED = 'self_maintained'

    CHOICES = [
        (OUTSOURCED, '代维', 'blue'),
        (COORDINATED, '协调', 'green'),
        (SELF_MAINTAINED, '自维', 'purple'),
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
        (SUSPENDED, '挂起', 'yellow'),
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

    FUSION_SPLICING = 'fusion_splicing'
    TAIL_FIBER_REPLACEMENT = 'tail_fiber_replacement'
    PROCESSING = 'processing'
    FIBER_ADJUSTMENT = 'fiber_adjustment'
    AUTOMATIC = 'automatic'
    UNKNOWN = 'unknown'
    NOT_PROVIDED = 'not_provided'

    CHOICES = [
        (FUSION_SPLICING, '熔接恢复', 'red'),
        (TAIL_FIBER_REPLACEMENT, '更换尾纤恢复', 'orange'),
        (PROCESSING, '处理恢复', 'yellow'),
        (FIBER_ADJUSTMENT, '调纤恢复', 'green'),
        (AUTOMATIC, '自动恢复', 'blue'),
        (UNKNOWN, '无法查明', 'gray'),
        (NOT_PROVIDED, '未提供', 'light-gray'),
    ]


class OtnFault(NetBoxModel, ImageAttachmentsMixin):
    fault_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='故障编号',
        help_text='系统自动生成，格式为FYYYYMMDDNNN'
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
        verbose_name='故障中断时间'
    )
    fault_recovery_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='故障恢复时间'
    )
    
    fault_category = models.CharField(
        max_length=20,
        choices=FaultCategoryChoices,
        verbose_name='故障分类',
        blank=True,
        null=True
    )
    
    INTERRUPTION_REASON_CHOICES = (
        ('road_construction', '道路施工'),
        ('sabotage', '人为破坏'),
        ('line_rectification', '线路整改'),
        ('misoperation', '误操作'),
        ('power_supply', '供电故障'),
        ('municipal_construction', '市政施工'),
        ('rodent_damage', '鼠害'),
        ('natural_disaster', '自然灾害'),
    )
    interruption_reason = models.CharField(
        max_length=30,
        choices=INTERRUPTION_REASON_CHOICES,
        verbose_name='故障原因',
        blank=True,
        null=True
    )
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
    # 2) 紧急程度，为选择型字段，分为高、中、低，按照颜色显示，高为红色，中为橙色，低为黄色，默认值为低，必填
    urgency = models.CharField(
        max_length=10,
        choices=UrgencyChoices,
        default=UrgencyChoices.LOW,
        verbose_name='紧急程度'
    )
    
    # 3) 第一报障来源，为选择性字段，分为国干网网管、未来网络网管、客户保障、其他，可空
    FIRST_REPORT_SOURCE_CHOICES = (
        ('national_backbone', '国干网网管'),
        ('future_network', '未来网络网管'),
        ('customer_support', '客户报障'),
        ('other', '其他'),
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
    
    # 6) 维护方式，为选择型字段，分为代维、协调、自维
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
        verbose_name='处理单位',
        blank=True,
        null=True
    )

    # 7.1) 代维合同，引用netbox-contract中的合同
    contract = models.ForeignKey(
        to='netbox_contract.Contract',
        on_delete=models.PROTECT,
        related_name='otn_faults',
        verbose_name='代维合同',
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
        default=False,
        verbose_name='规定时间内完成修复'
    )
    
    # 14) 超时原因，文本型字段
    timeout_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='超时原因'
    )
    
    # 15) 资源类型，为选择性字段，分为自建光缆、协调资源、租赁纤芯三类
    # 15) 资源类型，为选择性字段，分为自建光缆、协调资源、租赁纤芯三类
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceTypeChoices,
        blank=True,
        null=True,
        verbose_name='资源类型'
    )
    
    # 16) 光缆路由属性，为选择性字段，分为高速公路、非高速两类，默认值为高速公路，可空
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
        verbose_name='故障处理人'
    )
    
    # 18) 处理状态，为选择型字段，分为处理中、临时恢复、挂起、关闭
    # 18) 处理状态，为选择型字段，分为处理中、临时恢复、挂起、关闭
    fault_status = models.CharField(
        max_length=20,
        choices=FaultStatusChoices,
        default=FaultStatusChoices.PROCESSING,
        blank=True,
        null=True,
        verbose_name='处理状态'
    )
    
    # 19) 光缆中断部位，为选择型字段，分为尾纤、出局缆、长途光缆
    # 19) 光缆中断部位，为选择型字段，分为尾纤、出局缆、长途光缆
    cable_break_location = models.CharField(
        max_length=20,
        choices=CableBreakLocationChoices,
        blank=True,
        null=True,
        verbose_name='光缆中断部位'
    )
    
    # 20) 恢复方式，为选择型字段，分为熔接恢复、更换尾纤恢复、处理恢复、调纤恢复、自动恢复、无法查明、未提供
    # 20) 恢复方式，为选择型字段，分为熔接恢复、更换尾纤恢复、处理恢复、调纤恢复、自动恢复、无法查明、未提供
    recovery_mode = models.CharField(
        max_length=30,
        choices=RecoveryModeChoices,
        blank=True,
        null=True,
        verbose_name='恢复方式'
    )
    
    tags = taggit.managers.TaggableManager(
        through='extras.TaggedItem',
        to='extras.Tag',
        blank=True
    )
    comments = models.TextField(blank=True, verbose_name='评论')

    class Meta:
        ordering = ('-fault_occurrence_time',)
        verbose_name = '故障'
        verbose_name_plural = '故障'

    def __str__(self):
        return self.fault_number

    def get_absolute_url(self):
        return reverse('plugins:netbox_otnfaults:otnfault', args=[self.pk])

    def get_fault_category_color(self):
        return FaultCategoryChoices.colors.get(self.fault_category)

    @property
    def fault_duration(self):
        if self.fault_occurrence_time and self.fault_recovery_time:
            duration = self.fault_recovery_time - self.fault_occurrence_time
            days = duration.days
            seconds = duration.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            
            # 计算总小时数（包括天数转换的小时数）
            total_seconds = duration.total_seconds()
            total_hours = total_seconds / 3600
            
            return f"{days}天{hours}小时{minutes}分{seconds}秒（{total_hours:.2f}小时）"
        return None

    @property
    def repair_duration(self):
        """修复用时，自动计算字段，使用故障修复时间-处理派发时间，格式为9.65小时"""
        if self.dispatch_time and self.repair_time:
            duration = self.repair_time - self.dispatch_time
            total_hours = duration.total_seconds() / 3600
            return f"{total_hours:.2f}小时"
        return None

    def get_urgency_color(self):
        """获取紧急程度的颜色"""
        return UrgencyChoices.colors.get(self.urgency)

    def get_maintenance_mode_color(self):
        """获取维护方式的颜色"""
        return MaintenanceModeChoices.colors.get(self.maintenance_mode)

    def get_cable_break_location_color(self):
        """获取光缆中断部位的颜色"""
        return CableBreakLocationChoices.colors.get(self.cable_break_location)

    def get_recovery_mode_color(self):
        """获取恢复方式的颜色"""
        return RecoveryModeChoices.colors.get(self.recovery_mode)

    def get_resource_type_color(self):
        """获取资源类型的颜色"""
        return ResourceTypeChoices.colors.get(self.resource_type)

    def get_cable_route_color(self):
        """获取光缆路由属性的颜色"""
        return CableRouteChoices.colors.get(self.cable_route)

    def get_fault_status_color(self):
        """获取处理状态的颜色"""
        return FaultStatusChoices.colors.get(self.fault_status)

    def clean(self):
        super().clean()
        
        # 时间字段顺序验证
        time_fields = [
            ('fault_occurrence_time', '故障中断时间'),
            ('dispatch_time', '处理派发时间'),
            ('departure_time', '维修出发时间'),
            ('arrival_time', '到达现场时间'),
            ('fault_recovery_time', '故障恢复时间')
        ]
        
        # 收集所有非空时间字段
        times = []
        for field_name, field_label in time_fields:
            time_value = getattr(self, field_name)
            if time_value:
                times.append((field_name, field_label, time_value))
        
        # 检查时间顺序：后续时间不应早于前面的任何时间
        errors = {}
        for i in range(len(times)):
            for j in range(i + 1, len(times)):
                field_name_i, field_label_i, time_i = times[i]
                field_name_j, field_label_j, time_j = times[j]
                
                if time_j < time_i:
                    if field_name_j not in errors:
                        errors[field_name_j] = []
                    errors[field_name_j].append(f'{field_label_j}需晚于{field_label_i}')
        
        # 如果有错误，抛出 ValidationError 但将错误关联到具体字段
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.fault_number:
            today = timezone.now().strftime('%Y%m%d')
            prefix = f'F{today}'
            last_fault = OtnFault.objects.filter(fault_number__startswith=prefix).order_by('fault_number').last()
            if last_fault:
                last_number = int(last_fault.fault_number[9:])
                new_number = last_number + 1
            else:
                new_number = 1
            self.fault_number = f'{prefix}{new_number:03d}'
        super().save(*args, **kwargs)

class OtnFaultImpact(NetBoxModel, ImageAttachmentsMixin):
    otn_fault = models.ForeignKey(
        to=OtnFault,
        on_delete=models.CASCADE,
        related_name='impacts',
        verbose_name='关联故障'
    )
    impacted_service = models.ForeignKey(
        to=Tenant,
        on_delete=models.PROTECT,
        related_name='otn_fault_impacts',
        verbose_name='影响业务'
    )
    service_interruption_time = models.DateTimeField(
        verbose_name='业务故障时间'
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
        verbose_name = '故障影响业务'
        verbose_name_plural = '故障影响业务'
        unique_together = ('otn_fault', 'impacted_service')

    def __str__(self):
        return f"{self.otn_fault} - {self.impacted_service}"

    def get_absolute_url(self):
        return reverse('plugins:netbox_otnfaults:otnfaultimpact', args=[self.pk])

    @property
    def service_duration(self):
        if self.service_interruption_time and self.service_recovery_time:
            duration = self.service_recovery_time - self.service_interruption_time
            days = duration.days
            seconds = duration.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            
            # 计算总小时数（包括天数转换的小时数）
            total_seconds = duration.total_seconds()
            total_hours = total_seconds / 3600
            
            return f"{days}天{hours}小时{minutes}分{seconds}秒（{total_hours:.2f}小时）"
        return None


class CableTypeChoices(ChoiceSet):
    key = 'OtnPath.cable_type'

    TYPE_96 = '96'
    TYPE_114 = '114'

    CHOICES = [
        (TYPE_96, '96芯', 'blue'),
        (TYPE_114, '144芯', 'green'),
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
        verbose_name='计算长度',
        help_text='单位: 米'
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

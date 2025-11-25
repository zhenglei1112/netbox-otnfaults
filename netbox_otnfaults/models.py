from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from netbox.models import NetBoxModel
from dcim.models import Site
from tenancy.models import Tenant
from utilities.choices import ChoiceSet


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
        (CATEGORY_PIGTAIL, '尾纤故障', 'blue'),
        (CATEGORY_DEVICE, '设备故障', 'green'),
        (CATEGORY_OTHER, '其他故障', 'gray'),
    ]


class OtnFault(NetBoxModel):
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
    interruption_location = models.ManyToManyField(
        to=Site,
        related_name='otn_faults',
        verbose_name='中断位置'
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
        verbose_name='故障分类'
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
        verbose_name='中断原因'
    )
    fault_details = models.TextField(
        verbose_name='故障详细情况'
    )

    class Meta:
        ordering = ('-fault_occurrence_time',)
        verbose_name = 'OTN故障'
        verbose_name_plural = 'OTN故障'

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
            return f"{days}天{hours}小时{minutes}分{seconds}秒"
        return None

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

class OtnFaultImpact(NetBoxModel):
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
        verbose_name='业务中断时间'
    )
    service_recovery_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='业务恢复时间'
    )

    class Meta:
        ordering = ('-service_interruption_time',)
        verbose_name = '故障影响业务'
        verbose_name_plural = '故障影响业务'

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
            return f"{days}天{hours}小时{minutes}分{seconds}秒"
        return None

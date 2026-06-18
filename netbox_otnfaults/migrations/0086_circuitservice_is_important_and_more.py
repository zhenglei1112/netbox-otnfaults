# Generated manually on 2026-06-17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0085_alter_cutovertask_interruption_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='circuitservice',
            name='is_important',
            field=models.BooleanField(default=False, help_text='标识该电路业务是否属于重要电路业务，用于影响程度等级划分统计。', verbose_name='是否重要业务'),
        ),
        migrations.AddField(
            model_name='otnfault',
            name='ac_fault_is_class_i',
            field=models.BooleanField(default=False, help_text='仅空调故障时有效。标识空调故障是否引发网络设备不能正常工作。', verbose_name='空调故障是否为I类'),
        ),
        migrations.AddField(
            model_name='otnfault',
            name='device_fault_is_class_i',
            field=models.BooleanField(default=False, help_text='仅设备故障时有效。标识该设备故障是否产生实际影响，不属于设备部件冗余配置未产生任何影响的情况。', verbose_name='设备故障是否为I类'),
        ),
    ]

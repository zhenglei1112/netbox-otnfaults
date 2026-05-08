import django.contrib.postgres.fields
from django.contrib.postgres.indexes import GinIndex
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0058_alter_otnfault_power_data_type_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfault',
            name='root_cause_analysis',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ('switching_power_fault', '开关电源故障'),
                        ('rectifier_module_fault', '整流模块故障'),
                        ('battery_depleted', '电池耗尽'),
                        ('no_battery', '无电池'),
                        ('insufficient_battery_backup_time', '电池备电时间不足'),
                        ('room_power_test', '机房供电测试'),
                        ('grid_power_maintenance', '国网供电检修'),
                        ('breaker_trip', '空开跳闸'),
                        ('ups_fault', 'UPS故障'),
                        ('mains_power_outage', '市电停电'),
                        ('natural_disaster', '自然灾害'),
                        ('human_misoperation', '人为误操作'),
                        ('other', '其他'),
                    ],
                    max_length=40,
                ),
                blank=True,
                default=list,
                size=None,
                verbose_name='根因分析',
            ),
        ),
        migrations.AddIndex(
            model_name='otnfault',
            index=GinIndex(fields=['root_cause_analysis'], name='netbox_otnf_root_ca_5b58bf_gin'),
        ),
    ]

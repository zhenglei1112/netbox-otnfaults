import django.contrib.postgres.fields
from django.contrib.postgres.indexes import GinIndex
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0059_otnfault_power_root_cause_analysis'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfault',
            name='rectification_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('not_required', '无需整改'),
                    ('required', '需要整改'),
                    ('duplicate_merged', '重复合并'),
                ],
                max_length=20,
                null=True,
                verbose_name='是否整改',
            ),
        ),
        migrations.AddField(
            model_name='otnfault',
            name='rectification_measures',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ('replace_power', '更换电源'),
                        ('replace_battery', '更换电池'),
                        ('battery_expansion', '电池扩容'),
                        ('power_expansion', '电源扩容'),
                        ('add_monitoring', '增加动环'),
                        ('other', '其他'),
                    ],
                    max_length=40,
                ),
                blank=True,
                default=list,
                size=None,
                verbose_name='整改措施',
            ),
        ),
        migrations.AddField(
            model_name='otnfault',
            name='rectification_description',
            field=models.TextField(blank=True, verbose_name='措施描述'),
        ),
        migrations.AddField(
            model_name='otnfault',
            name='rectification_subject',
            field=models.CharField(
                blank=True,
                choices=[
                    ('headquarters', '本部'),
                    ('subsidiary', '子公司'),
                    ('external', '外单位'),
                ],
                max_length=20,
                null=True,
                verbose_name='整改主体',
            ),
        ),
        migrations.AddField(
            model_name='otnfault',
            name='rectification_progress',
            field=models.CharField(
                blank=True,
                choices=[
                    ('not_started', '未实施'),
                    ('in_progress', '进行中'),
                    ('completed', '已完成'),
                    ('suspended', '挂起'),
                ],
                max_length=20,
                null=True,
                verbose_name='整改进度',
            ),
        ),
        migrations.AddField(
            model_name='otnfault',
            name='planned_completion_date',
            field=models.DateField(blank=True, null=True, verbose_name='计划完成时间'),
        ),
        migrations.AddField(
            model_name='otnfault',
            name='actual_completion_date',
            field=models.DateField(blank=True, null=True, verbose_name='实际完成时间'),
        ),
        migrations.AddField(
            model_name='otnfault',
            name='rectification_completion_description',
            field=models.TextField(blank=True, verbose_name='整改完成情况描述'),
        ),
        migrations.AddIndex(
            model_name='otnfault',
            index=GinIndex(fields=['rectification_measures'], name='netbox_otnf_rectifi_bac8cb_gin'),
        ),
    ]

# Generated manually for netbox_otnfaults

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0018_modify_interruption_location_constraints'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otnfault',
            name='first_report_source',
            field=models.CharField(
                blank=True,
                null=True,
                choices=[
                    ('national_backbone', '国干网网管'),
                    ('future_network', '未来网络网管'),
                    ('customer_support', '客户报障'),
                    ('other', '其他'),
                ],
                max_length=20,
                verbose_name='第一报障来源'
            ),
        ),
        migrations.AlterField(
            model_name='otnfault',
            name='cable_route',
            field=models.CharField(
                blank=True,
                null=True,
                choices=[
                    ('highway', '高速公路'),
                    ('non_highway', '非高速'),
                ],
                default='highway',
                max_length=20,
                verbose_name='光缆路由属性'
            ),
        ),
    ]

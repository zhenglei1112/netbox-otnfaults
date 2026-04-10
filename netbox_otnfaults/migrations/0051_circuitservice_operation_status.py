from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0050_circuitservice_ring_protection'),
    ]

    operations = [
        migrations.AddField(
            model_name='circuitservice',
            name='operation_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('pending', '待开通'),
                    ('configured', '已配置'),
                    ('operating', '运营中'),
                    ('testing', '测试中'),
                    ('closed', '已关闭'),
                ],
                default='operating',
                max_length=20,
                verbose_name='运行状态',
            ),
        ),
    ]

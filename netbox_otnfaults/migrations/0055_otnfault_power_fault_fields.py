from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0054_otnmappreference'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfault',
            name='power_fault_phenomenon',
            field=models.CharField(
                blank=True,
                choices=[
                    ('all_interrupted', '全中断'),
                    ('partial_interrupted', '部分中断'),
                ],
                max_length=20,
                null=True,
                verbose_name='供电故障现象',
            ),
        ),
        migrations.AddField(
            model_name='otnfault',
            name='power_fault_impact',
            field=models.CharField(
                blank=True,
                choices=[
                    ('hosted', '设备托管'),
                    ('not_hosted', '设备未托管'),
                ],
                max_length=20,
                null=True,
                verbose_name='影响情况',
            ),
        ),
    ]

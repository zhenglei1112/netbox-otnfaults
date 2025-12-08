# Generated manually for netbox_otnfaults

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0015_otnfault_contract'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfault',
            name='cable_break_location',
            field=models.CharField(
                blank=True,
                choices=[
                    ('pigtail', '尾纤'),
                    ('local_cable', '出局缆'),
                    ('long_haul_cable', '长途光缆')
                ],
                max_length=20,
                null=True,
                verbose_name='光缆中断部位'
            ),
        ),
    ]

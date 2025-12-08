# Generated manually for netbox_otnfaults

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0016_add_cable_break_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfault',
            name='interruption_location_a',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='otn_faults_a',
                to='dcim.site',
                verbose_name='故障位置A端站点'
            ),
        ),
    ]

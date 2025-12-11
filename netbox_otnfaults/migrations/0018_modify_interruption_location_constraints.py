# Generated manually for netbox_otnfaults

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0017_add_interruption_location_a'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otnfault',
            name='interruption_location_a',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='otn_faults_a',
                to='dcim.site',
                verbose_name='故障位置A端站点'
            ),
        ),
    ]

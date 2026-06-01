from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('netbox_otnfaults', '0074_drop_legacy_cutovertask_maintenance_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfault',
            name='source_cutover_task',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='generated_faults',
                to='netbox_otnfaults.cutovertask',
                verbose_name='来源割接',
            ),
        ),
    ]

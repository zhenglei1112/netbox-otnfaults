from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0062_otnfault_is_suspended'),
    ]

    operations = [
        migrations.AddField(
            model_name='circuitservice',
            name='extra_fields',
            field=models.JSONField(blank=True, default=dict, verbose_name='扩展信息'),
        ),
    ]

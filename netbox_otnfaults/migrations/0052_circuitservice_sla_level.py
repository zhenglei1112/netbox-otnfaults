from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0051_circuitservice_operation_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='circuitservice',
            name='sla_level',
            field=models.CharField(
                blank=True,
                choices=[
                    ('728', '728'),
                    ('729', '729'),
                    ('730', '730'),
                    ('731', '731'),
                ],
                max_length=10,
                null=True,
                verbose_name='SLA等级',
            ),
        ),
    ]

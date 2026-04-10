from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0049_alter_circuitservice_bandwidth'),
    ]

    operations = [
        migrations.AddField(
            model_name='circuitservice',
            name='ring_protection',
            field=models.BooleanField(default=False, verbose_name='环网保护'),
        ),
    ]

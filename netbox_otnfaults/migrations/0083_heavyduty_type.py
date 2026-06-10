from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0082_otnfaultimpact_coordination_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='heavyduty',
            name='type',
            field=models.CharField(
                max_length=50,
                default='important',
                verbose_name='类型'
            ),
        ),
    ]

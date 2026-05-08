from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0060_otnfault_power_rectification_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfaultimpact',
            name='business_impact',
            field=models.CharField(
                choices=[
                    ('interrupted', '业务中断'),
                    ('not_interrupted', '业务未中断'),
                ],
                default='interrupted',
                max_length=20,
                verbose_name='业务影响',
            ),
        ),
    ]

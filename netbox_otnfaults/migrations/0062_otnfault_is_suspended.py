from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0061_otnfaultimpact_business_impact'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfault',
            name='is_suspended',
            field=models.BooleanField(
                default=False,
                help_text='该故障为挂起故障，不计入故障时长统计',
                verbose_name='挂起',
            ),
        ),
    ]

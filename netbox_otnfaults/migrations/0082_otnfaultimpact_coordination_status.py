from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0081_cutovertask_re_cutover'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfaultimpact',
            name='coordination_status',
            field=models.CharField(
                max_length=32,
                default='approved',
                verbose_name='协调状态'
            ),
        ),
    ]

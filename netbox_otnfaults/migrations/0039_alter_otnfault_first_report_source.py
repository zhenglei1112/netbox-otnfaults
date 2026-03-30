from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0038_circuitservice_billing_end_time_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otnfault',
            name='first_report_source',
            field=models.CharField(
                blank=True,
                choices=[
                    ('customer_support', '客户报障（含未来网络报障）'),
                    ('nms_self_check', '网管自查'),
                    ('env_alarm', '动环报警'),
                    ('other', '其他来源'),
                ],
                max_length=20,
                null=True,
                verbose_name='第一报障来源',
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0055_otnfault_power_fault_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfault',
            name='cutover_report_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('unreported', '未报备'),
                    ('reported', '已报备'),
                ],
                max_length=20,
                null=True,
                verbose_name='割接报备情况',
            ),
        ),
        migrations.AddField(
            model_name='otnfault',
            name='cutover_report_time',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='报备时间',
            ),
        ),
    ]

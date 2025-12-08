# Generated manually for adding fault_status field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0012_alter_otnfault_first_report_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='otnfault',
            name='fault_status',
            field=models.CharField(blank=True, choices=[('processing', '处理中'), ('temporary_recovery', '临时恢复'), ('suspended', '挂起'), ('closed', '关闭')], default='processing', max_length=20, null=True, verbose_name='处理状态'),
        ),
    ]

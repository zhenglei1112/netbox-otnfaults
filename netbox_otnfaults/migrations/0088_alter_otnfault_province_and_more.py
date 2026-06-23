# Generated manually on 2026-06-23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_otnfaults', '0087_statistics_query_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otnfault',
            name='province',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='otn_faults',
                to='dcim.region',
                verbose_name='省份'
            ),
        ),
        migrations.AlterField(
            model_name='cutovertask',
            name='is_timeout',
            field=models.CharField(
                blank=True,
                choices=[('yes', '是'), ('no', '否'), ('pending', '待判定')],
                default='pending',
                max_length=20,
                verbose_name='割接是否超时'
            ),
        ),
        migrations.AlterField(
            model_name='cutoverimpact',
            name='business_impact',
            field=models.CharField(
                blank=True,
                choices=[('interrupted', '业务中断'), ('not_interrupted', '业务未中断')],
                default='interrupted',
                max_length=20,
                verbose_name='业务影响'
            ),
        ),
        migrations.AlterField(
            model_name='cutoverimpact',
            name='service_interruption_time',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='业务故障时间'
            ),
        ),
        migrations.AlterField(
            model_name='cutoverimpact',
            name='coordination_status',
            field=models.CharField(
                choices=[('pending', '待协调'), ('approved', '已批准'), ('unapproved', '未批准'), ('forced', '强制割接')],
                default='pending',
                max_length=32,
                verbose_name='协调状态'
            ),
        ),
    ]

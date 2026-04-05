from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0001_initial'),
        ('netbox_otnfaults', '0041_otnfault_resource_owner'),
    ]

    operations = [
        # 1. 删除旧的 ForeignKey 字段
        migrations.RemoveField(
            model_name='otnfaultimpact',
            name='service_site_z',
        ),
        # 2. 添加新的 ManyToManyField
        migrations.AddField(
            model_name='otnfaultimpact',
            name='service_site_z',
            field=models.ManyToManyField(
                blank=True,
                help_text='仅裸纤业务时使用，可选择多个Z端站点',
                related_name='impact_service_site_z',
                to='dcim.site',
                verbose_name='业务站点Z',
            ),
        ),
    ]
